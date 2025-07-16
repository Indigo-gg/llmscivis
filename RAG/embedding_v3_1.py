import faiss
import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings
import pymongo
import os
import hashlib
import json
import re

# 导入 MongoDBManager 类（请确保此路径正确，或者您已将其定义在当前文件中）
# from RAG.mongodb import MongoDBManager # 假设 RAG.mongodb 存在，或者将其 MongoDBManager 定义放在此处

# 为了让代码在此处可运行，我们假设 MongoDBManager 如下定义
class MongoDBManager:
    def __init__(self, host, port, db_name, collection_name):
        self.client = pymongo.MongoClient(host, port)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        print(f"MongoDBManager initialized. Connected to DB: {db_name}, Collection: {collection_name}")

    def clear_collection(self):
        self.collection.delete_many({})
        print(f"Collection '{self.collection.name}' cleared.")

    def find_code_snippet(self, query):
        return self.collection.find_one(query)

    def insert_many(self, documents):
        if documents:
            try:
                self.collection.insert_many(documents)
                print(f"Successfully inserted {len(documents)} documents.")
            except pymongo.errors.BulkWriteError as bwe:
                print(f"BulkWriteError occurred: {bwe.details}")
            except Exception as e:
                print(f"Error inserting documents: {e}")
        else:
            print("No documents to insert.")

# 创建 MongoDB 连接管理器的实例
mongo_manager = MongoDBManager(
    host='localhost',
    port=27017,
    db_name='code_database',
    collection_name='code_snippets'
)

# 加载嵌入模型
model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 初始化 FAISS 向量数据库（在全局作用域中）
embedding_dim = 384
nlist = 100

# 量化器：用于在子空间中进行精确搜索的索引。
quantizer = faiss.IndexFlatIP(embedding_dim)

# 创建 IndexIVFFlat 索引
base_index = faiss.IndexIVFFlat(quantizer, embedding_dim, nlist, faiss.METRIC_INNER_PRODUCT)
index = faiss.IndexIDMap(base_index)

# 定义数据目录
DATA_DIR = 'd:\\Pcode\\LLM4VIS\\llmscivis\\data\\vtkjs-examples\\prompt-sample'

def load_code(file_path):
    """从相对路径读取文件内容."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if file_path.endswith('.json'):
                return json.loads(content)
            return content
    except Exception as e:
        # print(f"Error loading file {file_path}: {e}") # Debugging
        return None

def embed_text(text):
    """将文本转换为向量（返回 FAISS 的二维 numpy 数组）。"""
    embedding = model.embed_query(text)
    return np.array(embedding).reshape(1, -1)

def analyze_query(query: str):
    """
    分析用户查询，提取潜在的 VTK.js 模块。
    """
    analyzed_data = {
        "modules": []
    }

    lower_query = query.lower()

    # 1. 提取 VTK.js 模块名称 (更精确的匹配)
    # 匹配 vtk.Namespace.vtkClassName 或 vtkClassName
    module_patterns = [
        r"vtk\.?[\w\.]*?vtk([A-Z]\w+)", # 匹配 vtk.Namespace.vtkClassName 或 vtkClassName
        r"vtk\.[a-z]+\.[a-z]+\.[a-zA-Z]+" # 匹配 vtk.Rendering.Core.vtkActor 这种完整路径
    ]
    for pattern in module_patterns:
        matches = re.findall(pattern, query, re.IGNORECASE)
        for match in matches:
            # 对于如 vtk.Rendering.Core.vtkActor，我们需要提取 vtkActor
            if match.lower().startswith('vtk.'): # 完整路径，提取最后一个部分
                last_part = match.split('.')[-1]
                if last_part.lower().startswith('vtk'):
                    analyzed_data['modules'].append(last_part)
            elif match.lower().startswith('vtk'): # 已经是 vtkClassName 形式
                analyzed_data['modules'].append(match)
            # else: # Non-vtk prefixed matches are generally ignored here, unless explicitly added later

    # 简单提取常用模块，如果查询中直接提到了简写形式
    common_modules_short = ["vtkXMLPolyDataReader", "vtkActor", "vtkMapper", "vtkRenderer",
                            "vtkImageReslice", "vtkMatrix4x4", "vtkColorTransferFunction",
                            "vtkPiecewiseFunction", "vtkOrientationMarkerWidget", "vtkAxesActor",
                            "vtkRenderWindowInteractor", "vtkImageData", "vtkPointData",
                            "vtkPolyDataMapper", "vtkOpenGLRenderWindow", "vtkFullScreenRenderWindow",
                            "vtkImageMagnitude", "vtkMarchingCubes", "vtkDataSetReader"] # Added more based on query examples
    for mod in common_modules_short:
        # 确保不会重复添加已经通过正则匹配到的模块
        if mod.lower() in lower_query and mod not in analyzed_data['modules']:
            # 检查是否是独立单词或后跟非字母数字字符
            if re.search(r'\b' + re.escape(mod.lower()) + r'\b', lower_query):
                 analyzed_data['modules'].append(mod)

    # 移除重复项并保持原始大小写 (如果需要)
    # 这里为了匹配方便，通常会转小写处理，但存储时可以保留原始形式
    analyzed_data['modules'] = list(set([mod for mod in analyzed_data['modules']]))

    return analyzed_data


def rerank_results(raw_results, analyzed_query):
    """
    对初步召回的结果进行重排，结合元数据信息，并重排 vtkjs_modules 列表。
    Args:
        raw_results (list): 包含 'faiss_similarity' 和 'meta_info' 的初步召回文档列表。
        analyzed_query (dict): 通过 analyze_query 函数得到的查询分析结果。
    Returns:
        list: 经过重排并按分数降序排列的文档列表。
    """
    reranked_results = []
    
    # 定义不同匹配类型的权重
    WEIGHT_BASE_SIMILARITY = 1.0 # 基础语义相似度权重
    WEIGHT_EXACT_MODULE_MATCH_IN_DESCRIPTION = 0.8 # 描述中精确模块匹配的额外权重
    WEIGHT_EXACT_MODULE_MATCH_IN_VTKJSM_LIST = 0.6 # vtkjs_modules 列表中精确模块匹配的额外权重 (新增加权)
    WEIGHT_PARTIAL_MODULE_MATCH_IN_VTKJSM = 0.2 # vtkjs_modules 中部分模块或类名匹配的额外权重

    for doc in raw_results:
        # 确保 meta_info 和 description 存在
        meta = doc.get("meta_info", {})
        doc_description = meta.get('description', '').lower() # 获取文档描述并转为小写
        doc_modules_from_meta = meta.get('vtkjs_modules', []) # 获取文档的 vtkjs_modules 列表

        if not meta:
            doc['rerank_score'] = doc['faiss_similarity'] * WEIGHT_BASE_SIMILARITY
            reranked_results.append(doc)
            continue

        score = doc['faiss_similarity'] * WEIGHT_BASE_SIMILARITY
        reordered_doc_modules = [] # 用于构建重新排序的 vtkjs_modules 列表
        matched_modules_in_doc = set() # 跟踪已匹配的模块，避免重复加分和重复添加

        # --- 遍历查询中提取的模块 ---
        for q_module in analyzed_query['modules']:
            q_module_lower = q_module.lower()
            
            # 1. 检查查询模块是否在文档的 description 中精确出现
            # 这里我们查找完整的模块名（例如 vtkActor）或其完整路径的最后部分（例如 vtk.Rendering.Core.vtkActor 中的 vtkActor）
            # 确保不匹配像 "nvtkActor" 这样的词
            desc_match_pattern = r'\b' + re.escape(q_module_lower) + r'\b'
            
            # 同时检查完整路径形式的类名匹配，例如：vtk.Rendering.Core.vtkActor
            # 这里提取 vtkActor 的 "Actor" 部分，然后在 description 中查找 "vtkActor"
            full_path_class_name_pattern = None
            if q_module_lower.startswith('vtk') and len(q_module_lower) > 3:
                class_name_only = q_module_lower[3:] # 例如 "actor"
                # 匹配如 vtk.rendering.core.vtkactor, vtk.filters.general.vtktransform 等
                full_path_class_name_pattern = r'\bvtk\.[a-z]+\.[a-z]+\.' + re.escape(class_name_only) + r'\b'

            description_matched = False
            if re.search(desc_match_pattern, doc_description) or \
               (full_path_class_name_pattern and re.search(full_path_class_name_pattern, doc_description)):
                if q_module not in matched_modules_in_doc: # 避免对同一个 q_module 因 description 匹配多次加分
                    score += WEIGHT_EXACT_MODULE_MATCH_IN_DESCRIPTION
                    matched_modules_in_doc.add(q_module)
                    description_matched = True

            # 2. 检查查询模块是否在文档的 vtkjs_modules 列表中精确或部分匹配
            # 这里的目的是将匹配到的模块移到 reordered_doc_modules 的前面
            found_in_vtkjs_list = False
            for dm in doc_modules_from_meta:
                dm_lower = dm.lower()
                
                # 精确匹配 (例如 "vtkActor" == "vtkActor")
                # 或完整路径类名匹配 (例如 "vtkActor" 匹配 "vtk.Rendering.Core.vtkActor")
                if q_module_lower == dm_lower or \
                   (dm_lower.startswith('vtk.') and dm_lower.endswith('.' + q_module_lower.replace('vtk', ''))):
                    
                    if dm not in reordered_doc_modules: # 如果还没添加过，则添加
                        reordered_doc_modules.append(dm)
                    
                    if q_module not in matched_modules_in_doc: # 如果这个查询模块还没加过分
                        score += WEIGHT_EXACT_MODULE_MATCH_IN_VTKJSM_LIST # 新的权重
                        matched_modules_in_doc.add(q_module)
                    found_in_vtkjs_list = True
                    break # 这个查询模块在当前文档的 vtkjs_modules 列表中找到了一个匹配

            # 如果在 vtkjs_modules 中没有找到精确匹配，但短名称出现（作为后缀）
            # 这个逻辑是用来捕获像 "RenderingCore" (如果 q_module 是 "vtkRenderingCore") 这种情况
            # 或者当 q_module 是 "vtkActor" 而 dm 是 "RenderingCoreActor" (不理想，但根据现有正则分析是可能的)
            if not found_in_vtkjs_list and q_module_lower.startswith("vtk") and len(q_module_lower) > 3:
                for dm in doc_modules_from_meta:
                    dm_lower = dm.lower()
                    if dm_lower.endswith(q_module_lower.replace('vtk', '')): # 例如 dm="RenderingCoreActor", q_module="vtkActor"
                        if dm not in reordered_doc_modules:
                            reordered_doc_modules.append(dm)
                        if q_module not in matched_modules_in_doc: # 避免重复加分
                            score += WEIGHT_PARTIAL_MODULE_MATCH_IN_VTKJSM
                            matched_modules_in_doc.add(q_module)
                        break # Found a partial match, move to next q_module

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
    
    # 确保 nprobe 设置合理，避免除以零
    if nlist > 0:
        index.nprobe = max(1, nlist // 5)
    else:
        index.nprobe = 1 # Fallback for nlist = 0 or invalid

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
                    # print(f"Skipping {file_path}: Missing meta_info, description, or code_content.") # Debugging
                    continue
                
                # 将 description 存储到 meta_info 中，方便 rerank_results 访问
                if meta_info is not None:
                    meta_info['description'] = description
                else:
                    meta_info = {'description': description}

                # 提取 vtkjs_modules 并确保其是列表，即使是单个字符串
                if 'vtkjs_modules' in meta_info and isinstance(meta_info['vtkjs_modules'], str):
                    # 如果是逗号分隔的字符串，尝试分割
                    meta_info['vtkjs_modules'] = [m.strip() for m in meta_info['vtkjs_modules'].split(',') if m.strip()]
                elif 'vtkjs_modules' not in meta_info or not isinstance(meta_info['vtkjs_modules'], list):
                    meta_info['vtkjs_modules'] = [] # 确保是一个列表


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
                    "meta_info": meta_info, # meta_info 包含了 description 和处理后的 vtkjs_modules
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

    # 确保 DATA_DIR 存在且指向包含你的 vtkjs-examples 的路径
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
    {
        "description": "Introduce necessary VTK.js modules via the CDN link: https://unpkg.com/vtk.js;"
    },
    {
        "description": "Data Loading — Load the VTK dataset from http://127.0.0.1:5000/dataset/rotor.vti using vtkXMLImageDataReader;"
    },
    {
        "description": "Data Processing — Set 'Pressure' as the active scalar and apply a slice at 80% /depth along the Y-axis using vtkImageSlice;"
    },
    {
        "description": "Visualization Setup — Map pressure values to a blue→white→red color gradient and set full opacity using vtkColorTransferFunction, vtkPiecewiseFunction, vtkMapper;"
    },
    {
        "description": "Add UI Element — Integrate an XYZ axes orientation marker for spatial reference using vtkOrientationMarkerWidget, vtkAxesActor;"
    },
    {
        "description": "Integrate all components and render the visualization without GUI controls using vtkRenderWindow, vtkRenderer, vtkActor;"
    }
],[
    {
        "description": "Introduce necessary VTK.js modules via the CDN link: https://unpkg.com/vtk.js;"
    },
    {
        "description": "Data Loading — Load the VTK dataset from rotor_simplified.vti using vtkXMLImageDataReader;"
    },
    {
        "description": "Data Processing — Calculate the velocity magnitude from vector components (vx, vy, vz) by computing √(vx²+vy²+vz²) and set it as an active scalar array;"
    },
    {
        "description": "Feature Extraction — Use the Marching Cubes algorithm (vtkContourFilter) to extract isosurfaces based on the calculated velocity magnitude;"
    },
    {
        "description": "Visualization Setup — Apply a rainbow colormap (blue→cyan→white→orange→red) using vtkColorTransferFunction. Set surface lighting properties with ambient(0.3), diffuse(0.7), specular(0.4) using vtkProperty;"
    },
    {
        "description": "Add UI Element — Integrate an interactive 3D view with orientation axes widget for spatial reference using vtkOrientationMarkerWidget, vtkAxesActor;"
    },
    {
        "description": "Responsive Implementation — Ensure the visualization is responsive and integrates all components using vtkRenderWindow, vtkRenderer, vtkActor. Render the scene without additional GUI controls but ensure interaction capabilities such as rotation and zoom are enabled;"
    }
],
     [
    {
        "description": "Introduce necessary VTK.js modules via the CDN link: https://unpkg.com/vtk.js;"
    },
    {
        "description": "Data Loading — Load the VTK dataset from http://127.0.0.1:5000/dataset/isabel.vti using vtkXMLImageDataReader;"
    },
    {
        "description": "Data Processing — Extract the velocity field from the dataset and prepare seed points at the center of the dataset for generating streamlines using vtkStreamTracer or similar classes;"
    },
    {
        "description": "Visualization Setup — Generate streamlines based on the velocity field starting from the central seed points; adjust streamline parameters such as step size and integration direction;"
    },
    {
        "description": "Outline Display — Add an outline representation of the dataset to provide context to the streamlines using vtkOutlineFilter and vtkPolyDataMapper;"
    },
    {
        "description": "Rendering Configuration — Use vtkFullScreenRenderWindow to set up the rendering environment ensuring full-screen display capability; integrate all components (streamlines and outline) into the vtkRenderer;"
    },
    {
        "description": "Integrate all components and render the visualization using vtkRenderWindow, vtkRenderer, and vtkActor without additional GUI controls unless specified;"
    }
],
    [
    {
        "description": "Introduce necessary VTK.js modules via the CDN link: https://unpkg.com/vtk.js;"
    },
    {
        "description": "Data Loading — Load the VTK dataset from http://127.0.0.1:5000/dataset/airfoil_oneslice.vtp using vtkXMLPolyDataReader;"
    },
    {
        "description": "Data Processing — Set 'p' as the active scalar array for color encoding using setDataArray;"
    },
    {
        "description": "Visualization Setup — Create a volume mapper and connect it to the data source using vtkVolumeMapper, then set up a volume property with color and opacity mappings using vtkColorTransferFunction and vtkPiecewiseFunction;"
    },
    {
        "description": "Camera Positioning — Adjust the camera position to focus on the dataset bounds using vtkCamera's set methods (setPosition, setFocalPoint, etc.);"
    },
    {
        "description": "Integrate all components and render the visualization using vtkRenderWindow, vtkRenderer, and vtkVolume actor without additional GUI controls."
    }
]
    ]
    process_nested_queries_and_log(splited_queries)