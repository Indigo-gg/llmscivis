import faiss
import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings
import pymongo
import os
import hashlib
import json
import re

# Import MongoDBManager class (please ensure this path is correct, or you have defined it in the current file)
from RAG.mongodb import MongoDBManager

# Create an instance of MongoDB connection manager
mongo_manager = MongoDBManager(
    host='localhost',
    port=27017,
    db_name='code_database',
    collection_name='code_snippets'
)

# Load embedding model
model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Initialize FAISS vector database (in global scope)
embedding_dim = 384
nlist = 100

# Quantizer: Index used for precise search in subspaces.
quantizer = faiss.IndexFlatIP(embedding_dim)

# Create IndexIVFFlat index
base_index = faiss.IndexIVFFlat(quantizer, embedding_dim, nlist, faiss.METRIC_INNER_PRODUCT)
index = faiss.IndexIDMap(base_index)

# Define data directory
DATA_DIR = 'd:\\Pcode\\LLM4VIS\\llmscivis\\data\\vtkjs-examples\\prompt-sample'

def load_code(file_path):
    """Read file content from relative path."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if file_path.endswith('.json'):
                return json.loads(content)
            return content
    except Exception as e:
        return None

def embed_text(text):
    """Convert text to vector (returns a 2D numpy array for FAISS)."""
    embedding = model.embed_query(text)
    return np.array(embedding).reshape(1, -1)

def analyze_query(query: str):
    """
    Analyze user query to extract potential VTK.js modules.
    """
    analyzed_data = {
        "modules": []
    }

    lower_query = query.lower()

    # 1. Extract VTK.js module names (more precise matching)
    module_patterns = [
        r"vtk\.?[\w\.]*?vtk([A-Z]\w+)", # 匹配 vtk.Namespace.vtkClassName 或 vtkClassName
        r"vtk\.[a-z]+\.[a-z]+\.[a-zA-Z]+" # 匹配 vtk.Rendering.Core.vtkActor 这种完整路径
    ]
    for pattern in module_patterns:
        matches = re.findall(pattern, query, re.IGNORECASE)
        for match in matches:
            if match.startswith('vtk'):
                analyzed_data['modules'].append(match)
            else: 
                pass 
    
    # Simply extract common modules if shorthand forms are directly mentioned in the query
    common_modules_short = ["vtkXMLPolyDataReader", "vtkActor", "vtkMapper", "vtkRenderer", 
                            "vtkImageReslice", "vtkMatrix4x4", "vtkColorTransferFunction",
                            "vtkPiecewiseFunction", "vtkOrientationMarkerWidget", "vtkAxesActor",
                            "vtkRenderWindowInteractor", "vtkImageData", "vtkPointData",
                            "vtkPolyDataMapper", "vtkOpenGLRenderWindow"]
    for mod in common_modules_short:
        if mod.lower() in lower_query and mod not in analyzed_data['modules']:
            analyzed_data['modules'].append(mod)
            
    # Remove duplicates
    analyzed_data['modules'] = list(set(analyzed_data['modules']))

    return analyzed_data


def rerank_results(raw_results, analyzed_query):
    """
    Rerank preliminary recall results, combine metadata information, and reorder vtkjs_modules list.
    Args:
        raw_results (list): Preliminary recalled document list containing 'faiss_similarity' and 'meta_info'.
        analyzed_query (dict): Query analysis results obtained through the analyze_query function.
    Returns:
        list: Document list reranked and sorted by score in descending order.
    """
    reranked_results = []
    
    # Define weights for different matching types
    WEIGHT_BASE_SIMILARITY = 1.0 # Base semantic similarity weight
    WEIGHT_EXACT_MODULE_MATCH_IN_DESCRIPTION = 0.8 # Additional weight for exact module matching in description
    WEIGHT_PARTIAL_MODULE_MATCH_IN_VTKJSM = 0.2 # Additional weight for partial module or class name matching in vtkjs_modules

    for doc in raw_results:
        # 确保 meta_info 和 description 存在
        meta = doc.get("meta_info", {})
        doc_description = meta.get('description', '').lower() # 获取文档描述并转为小写

        if not meta:
            doc['rerank_score'] = doc['faiss_similarity'] * WEIGHT_BASE_SIMILARITY
            reranked_results.append(doc)
            continue

        score = doc['faiss_similarity'] * WEIGHT_BASE_SIMILARITY
        doc_modules_from_meta = meta.get('vtkjs_modules', [])
        reordered_doc_modules = []
        
        # --- 优先处理查询中明确提到的模块，并在文档 description 中进行精确匹配 ---
        for q_module in analyzed_query['modules']:
            # Check if query module appears exactly in document description
            # 这里我们查找完整的模块名（例如 vtkActor）或其完整路径的最后部分（例如 vtk.Rendering.Core.vtkActor 中的 vtkActor）
            # 确保不匹配像 "nvtkActor" 这样的词
            module_name_pattern = r'\b' + re.escape(q_module.lower()) + r'\b'
            
            # Also check for full path class name matching, e.g.: vtk.Rendering.Core.vtkActor
            # 这里提取 vtkActor 的 "Actor" 部分，然后在 description 中查找 "vtkActor"
            if q_module.lower().startswith('vtk') and len(q_module) > 3:
                class_name_only = q_module[3:] # 例如 "Actor"
                full_path_class_name_pattern = r'\bvtk\.\w+\.\w+\.' + re.escape(class_name_only.lower()) + r'\b'
            else:
                full_path_class_name_pattern = None

            found_in_description = False
            if re.search(module_name_pattern, doc_description) or \
               (full_path_class_name_pattern and re.search(full_path_class_name_pattern, doc_description)):
                score += WEIGHT_EXACT_MODULE_MATCH_IN_DESCRIPTION
                found_in_description = True
                
            # --- Now process vtkjs_modules list, only perform partial matching and sorting ---
            # 检查查询模块是否与 doc_modules_from_meta 中的模块有精确或部分匹配，并进行重新排序
            exact_match_found_in_vtkjs_meta = False
            for dm in doc_modules_from_meta:
                # 检查精确匹配（例如 "vtkActor" == "vtkActor"）
                # 或完整路径类名匹配（例如 "vtkActor" 匹配 "vtk.Rendering.Core.vtkActor"）
                if q_module.lower() == dm.lower() or dm.lower().endswith("." + q_module.lower().replace("vtk", "")):
                    if dm not in reordered_doc_modules:
                        reordered_doc_modules.append(dm)
                    exact_match_found_in_vtkjs_meta = True
                    # 注意：这里不再加分数，分数加权已在 description 匹配时完成
                    break
            
            # 如果在 vtkjs_modules 中没有找到精确匹配，但短名称出现（作为后缀）
            if not exact_match_found_in_vtkjs_meta and q_module.startswith("vtk") and len(q_module) > 3:
                for dm in doc_modules_from_meta:
                    if dm.lower().endswith(q_module.lower()):
                        if dm not in reordered_doc_modules:
                            reordered_doc_modules.append(dm)
                        # 这里加分数，因为这是新的“部分匹配”逻辑
                        score += WEIGHT_PARTIAL_MODULE_MATCH_IN_VTKJSM
                        break

        # 添加原始列表中所有未被明确匹配和重新排序的剩余模块
        for dm in doc_modules_from_meta:
            if dm not in reordered_doc_modules:
                reordered_doc_modules.append(dm)
        
        # 更新文档元信息中的 vtkjs_modules
        doc['meta_info']['vtkjs_modules'] = reordered_doc_modules
        doc['rerank_score'] = score
        reranked_results.append(doc)

    # 按重排分数降序排序
    reranked_results.sort(key=lambda x: x.get('rerank_score', 0), reverse=True)
    return reranked_results

def search_code_optimized(query, k=3, similarity_threshold=0.3, recall_k_multiplier=5):
    """
    优化后的检索阶段：根据用户查询获取匹配的代码块，并结合元数据进行重排。
    Args:
        query (str): 用户查询文本。
        k (int): 返回最终前 k 个最相关的结果。
        similarity_threshold (float, optional): 基础余弦相似度阈值。只召回高于此阈值的结果。
        recall_k_multiplier (int): 初始召回阶段返回的文档数量是 k 的倍数。
    """
    global index
    
    # --- 阶段1: 查询分析 ---
    analyzed_query = analyze_query(query)
    print(f"查询分析结果: {analyzed_query}")

    # --- 阶段2: 粗粒度召回 (FAISS 语义搜索) ---
    query_vector = embed_text(query)
    if query_vector.shape[1] != embedding_dim:
        print(f"错误: 查询向量维度不匹配 ({query_vector.shape[1]} != {embedding_dim})")
        return []

    if not index.is_trained:
        print("警告: FAISS 索引未训练，无法执行搜索。")
        return []
    
    if not hasattr(index, 'nprobe'):
        print("警告: index.nprobe 未设置，使用默认值 1。")
    index.nprobe = max(1, nlist // 5) if nlist > 0 else 1 # 确保 nprobe 不为0
    print(f"FAISS IndexIVFFlat nprobe 设置为: {index.nprobe}")

    recall_k = k * recall_k_multiplier
    distances, faiss_ids = index.search(query_vector, recall_k)

    raw_results = []
    for i, faiss_id in enumerate(faiss_ids[0]):
        if faiss_id == -1:
            continue

        similarity = distances[0][i]
        
        if similarity_threshold is not None and similarity < similarity_threshold:
            continue 
        
        matched_document = mongo_manager.find_code_snippet({"faiss_id": int(faiss_id)})
        if matched_document:
            matched_document['faiss_similarity'] = similarity
            raw_results.append(matched_document)

    # --- 阶段3: 精细化重排 ---
    if not raw_results:
        print("初始召回阶段未找到结果。")
        return []

    reranked_results = rerank_results(raw_results, analyzed_query)
    
    # --- 阶段4: 最终选择与返回 ---
    final_results = []
    for doc in reranked_results:
        final_results.append(doc)
        if len(final_results) >= k: 
            break

    return final_results

def load_data_from_directory(directory):
    """从指定目录读取所有文件并添加到数据库."""
    global index, nlist, quantizer, base_index 

    if not os.path.isdir(directory):
        print(f"错误: 目录不存在或不是一个有效目录: {directory}")
        return

    # 检查 FAISS 和 MongoDB 是否已加载，避免重复操作
    if index.is_trained and mongo_manager.collection.count_documents({}) > 0 and \
       index.ntotal == mongo_manager.collection.count_documents({}):
        print(f"FAISS 索引已训练，包含 {index.ntotal} 个向量。MongoDB 集合中已有 {mongo_manager.collection.count_documents({})} 个文档。数据一致，跳过数据加载。")
        return 

    print(f"开始从目录加载数据: {directory}")
    
    all_vectors = [] 
    documents_for_faiss_and_mongo = [] 

    for root, _, files in os.walk(directory):
        for filename in files:
            if filename == 'code.html':
                file_path = os.path.join(root, filename)
                example_dir = os.path.dirname(file_path)
                meta_info_path = os.path.join(example_dir, "code_meta.json")
                description_path = os.path.join(example_dir, "description.txt")
                
                meta_info = load_code(meta_info_path)
                description = load_code(description_path)
                code_content = load_code(file_path) 
                
                if meta_info is None or description is None or code_content is None:
                    continue
                
                # 将 description 存储到 meta_info 中，方便 rerank_results 访问
                if meta_info is not None:
                    meta_info['description'] = description
                else:
                    meta_info = {'description': description}

                vector = embed_text(description)[0] 
                if vector.shape[0] != embedding_dim:
                    print(f"警告: 向量维度不匹配 ({vector.shape[0]} != {embedding_dim})，跳过文件 {file_path}")
                    continue

                snippet_faiss_id = int(hashlib.sha1(file_path.encode("utf-8")).hexdigest(), 16) % (2**31 - 1)
                if snippet_faiss_id < 0:
                    snippet_faiss_id *= -1
                
                mongo_document = {
                    "faiss_id": snippet_faiss_id,
                    "file_path": file_path, 
                    "code": code_content,
                    "meta_info": meta_info, # meta_info 包含了 description
                    "embedding": vector.tolist() 
                }

                all_vectors.append(vector)
                documents_for_faiss_and_mongo.append((snippet_faiss_id, vector, mongo_document))
    
    if not all_vectors:
        print("未找到任何符合条件的向量用于训练和添加。")
        return

    if not index.is_trained:
        print(f"开始训练 FAISS 索引，使用 {len(all_vectors)} 个向量...")
        training_data = np.array(all_vectors).astype('float32')
        
        if training_data.shape[0] < nlist:
            nlist_old = nlist
            nlist = max(1, training_data.shape[0] // 2 if training_data.shape[0] > 1 else 1) 
            print(f"警告: 训练数据量 ({training_data.shape[0]}) 小于当前 nlist ({nlist_old})。nlist 已自动调整为 {nlist}。")
            
            # 重新初始化 FAISS 索引 with adjusted nlist
            quantizer = faiss.IndexFlatIP(embedding_dim)
            base_index = faiss.IndexIVFFlat(quantizer, embedding_dim, nlist, faiss.METRIC_INNER_PRODUCT)
            index = faiss.IndexIDMap(base_index)
            
        index.train(training_data)
        print("FAISS 索引训练完成。")

    if index.ntotal == 0: # 只有在索引为空时才添加
        faiss_ids_array = np.array([item[0] for item in documents_for_faiss_and_mongo]).astype('int64')
        vectors_array = np.array([item[1] for item in documents_for_faiss_and_mongo]).astype('float32')
        
        if vectors_array.shape[0] > 0:
            index.add_with_ids(vectors_array, faiss_ids_array)
            print(f"批量添加到 FAISS 成功，共添加 {vectors_array.shape[0]} 个向量。")
        else:
            print("没有向量可以添加到 FAISS。")

    if mongo_manager.collection.count_documents({}) == 0: # 只有在集合为空时才插入
        mongo_documents_to_insert = [item[2] for item in documents_for_faiss_and_mongo]
        if mongo_documents_to_insert:
            try:
                mongo_manager.collection.insert_many(mongo_documents_to_insert)
            except Exception as e:
                print(f"批量插入到 MongoDB 失败: {e}")
        else:
            print("没有文档可以插入到 MongoDB。")
    
    print("数据加载完成。")
def process_nested_queries_and_log(splited_queries_nested, output_filename="output2.txt"):
    """
    执行优化查询，并将结果同时打印到控制台和写入到指定文件。
    此版本支持嵌套的查询列表结构。

    Args:
        splited_queries_nested (list): 包含嵌套查询字典列表的列表。
        output_filename (str): 要写入输出的文件名。
    """
    with open(output_filename, 'w', encoding='utf-8') as f:
        # 写入并打印开始信息
        start_message = "\n--- 开始执行优化查询 ---\n"
        print(start_message, end='')
        f.write(start_message)

        # Iterate through each inner list of queries
        for group_idx, query_group in enumerate(splited_queries_nested):
            group_header = f"\n=== 查询组 {group_idx + 1} ===\n"
            print(group_header, end='')
            f.write(group_header)

            for query_idx, query_item in enumerate(query_group):
                query_description = query_item['description']
                query_header = f"\n===== 查询 {query_idx + 1}: '{query_description}' =====\n"
                print(query_header, end='')
                f.write(query_header)

                # Assume search_code_optimized is defined elsewhere and works with a single description string
                current_results = search_code_optimized(query_description, k=2, similarity_threshold=0.3)

                if current_results:
                    for j, result in enumerate(current_results):
                        result_start = f'\n--- 结果 {j+1} ---\n'
                        print(result_start, end='')
                        f.write(result_start)

                        faiss_id = f'FAISS ID: {result.get("faiss_id", "N/A")}\n'
                        print(faiss_id, end='')
                        f.write(faiss_id)

                        faiss_similarity = f'基础相似度 (Cosine): {result.get("faiss_similarity", "N/A"):.4f}\n'
                        print(faiss_similarity, end='')
                        f.write(faiss_similarity)

                        rerank_score = f'重排分数: {result.get("rerank_score", "N/A"):.4f}\n'
                        print(rerank_score, end='')
                        f.write(rerank_score)

                        meta = result.get("meta_info", {})
                        file_path = f'文件路径: {meta.get("file_path", "N/A")}\n'
                        print(file_path, end='')
                        f.write(file_path)

                        description_meta = f'描述: {meta.get("description", "N/A")}\n' # Renamed to avoid conflict
                        print(description_meta, end='')
                        f.write(description_meta)

                        vtkjs_modules = f'VTK.js 模块 (排序后): {meta.get("vtkjs_modules", "N/A")}\n'
                        print(vtkjs_modules, end='')
                        f.write(vtkjs_modules)

                        separator = f'\n--------------------------------------------------------------------------------------------------------------\n'
                        print(separator, end='')
                        f.write(separator)
                else:
                    no_results_message = f"查询 '{query_description}' 未找到结果或结果低于阈值。\n"
                    print(no_results_message, end='')
                    f.write(no_results_message)

        # 写入并打印结束信息
        end_message = "\n--- 所有查询执行完毕 ---\n"
        print(end_message, end='')
        f.write(end_message)


if __name__ == '__main__':
    mongo_manager.clear_collection()
    
    def reset_faiss_index():
        global index, quantizer, base_index, nlist # 确保使用全局变量
        nlist = 100 # 重置 nlist
        new_quantizer = faiss.IndexFlatIP(embedding_dim)
        new_base_index = faiss.IndexIVFFlat(new_quantizer, embedding_dim, nlist, faiss.METRIC_INNER_PRODUCT)
        index = faiss.IndexIDMap(new_base_index)

    reset_faiss_index()
    print("已重置 FAISS 索引和清空 MongoDB 集合。")

    load_data_from_directory(DATA_DIR)
    
    print(f"FAISS 索引中当前有 {index.ntotal} 个向量。")
    print(f"MongoDB 集合中当前有 {mongo_manager.collection.count_documents({})} 个文档。")

    if index.is_trained:
        index.nprobe = max(1, nlist // 5) 
        print(f"FAISS IndexIVFFlat nprobe 设置为: {index.nprobe}")
    else:
        print("警告: FAISS 索引尚未训练，nprobe 未设置。搜索可能不会按预期工作。")


    splited_queries=[
        [
        {"description": "Introduce necessary VTK.js modules via the CDN link: https://unpkg.com/vtk.js"},
        {"description": "Data Loading — Load the VTK dataset from http://127.0.0.1:5000/dataset/rotor.vti"},
        {"description": "Data Processing — Set 'Pressure' as the active scalar and apply a slice at 80% /depth along the Y-axis"},
        {"description": "Visualization Setup — Map pressure values to a blue→white→red color gradient and set full opacity"},
        {"description": "Add UI Element — Integrate an XYZ axes orientation marker for spatial reference"},
        {"description": "Integrate all components and render the visualization without GUI controls"}
        ],
        [ 
            {
                "description": "Data Loading — Load the rotor_simplified.vti dataset using VTK.js data reader functions"
            },
            {
                "description": "Data Processing — Calculate the velocity magnitude from vector components (vx, vy, vz) using vtkImageMagnitude or similar VTK.js functionality to derive √(vx²+vy²+vz²)"   
            },
            {
                "description": "Feature Extraction — Apply the Marching Cubes algorithm to extract isosurfaces from the processed velocity magnitude data"
            },
            {
                "description": "Visualization Setup — Map the extracted isosurface values to a rainbow colormap (blue→cyan→white→orange→red) and configure surface rendering with lighting parameters: ambient(0.3), diffuse(0.7), specular(0.4)"
            },
            {
                "description": "Add UI Element — Integrate an interactive 3D view with an orientation axes widget for spatial reference"  
            },
            {
                "description": "Responsive UI Implementation — Ensure the visualization is responsive and integrates seamlessly within the web application framework using vtk.js"
            }
    ],
    [
            {"description": "Introduce necessary VTK.js modules via the CDN link: https://unpkg.com/vtk.js"},
            {"description": "Data Loading — Load the VTK dataset from http://127.0.0.1:5000/dataset/isabel.vti"},
            {"description": "Data Processing — Set 'velocity' as the active vector field for streamline generation"},
            {"description": "Streamline Setup — Generate streamlines starting from center seeds within the dataset"},
            {"description": "Outline Visualization — Add an outline representation of the dataset to provide spatial context"},       
            {"description": "Rendering Configuration — Use vtkFullScreenRenderWindow to handle the rendering setup and display the visualization in full screen"},
            {"description": "Integrate all components and render the visualization including streamlines and outline without additional GUI controls"}
        ],
    [
            {"description": "Introduce necessary VTK.js modules via the CDN link: https://unpkg.com/vtk.js"},
            {"description": "Data Loading — Load the VTK dataset from http://127.0.0.1:5000/dataset/airfoil_oneslice.vtp"},
            {"description": "Scalar Mapping — Activate the 'p' scalar array for color encoding in the visualization"},
            {"description": "Visualization Setup — Configure volume rendering to display colors and representations based on the 'p' scalar values"},
            {"description": "Camera Positioning — Adjust the camera position to focus on the dataset bounds ensuring all data is clearly visible"},
            {"description": "Integrate all components and render the visualization"}
        ]
        
    ]
    process_nested_queries_and_log(splited_queries)
    

# 示例用法 (假设 splited_queries 和 search_code_optimized 已定义)
# splited_queries = [{"description": "query 1 description"}, {"description": "query 2 description"}]
# def search_code_optimized(description, k, similarity_threshold):
#     # 模拟搜索结果
#     if "query 1" in description:
#         return [
#             {"faiss_id": "id1", "faiss_similarity": 0.5, "rerank_score": 0.6, "meta_info": {"file_path": "/path/to/file1", "description": "desc1", "vtkjs_modules": ["mod1"]}},
#             {"faiss_id": "id2", "faiss_similarity": 0.4, "rerank_score": 0.5, "meta_info": {"file_path": "/path/to/file2", "description": "desc2", "vtkjs_modules": ["mod2"]}}
#         ]
#     return []

# process_queries_and_log(splited_queries)