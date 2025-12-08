import faiss
import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings
import pymongo
import os
import hashlib
import json
import re
from config.app_config import app_config
import pandas as pd
import time
# 第一阶段召回的k
K=4
Similarity_Threshold=0.1


# 定义不同匹配类型的权重
WEIGHT_BASE_SIMILARITY = 1 # 基础语义相似度权重
WEIGHT_MODULE_MATCH_IN_DESCRIPTION = 0.25 # 描述中模块匹配的额外权重
WEIGHT_MODULE_PARTIAL_MATCH_IN_VTKJSM = 0.15 # vtkjs_modules 列表中模块部分匹配的额外权重

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

index = faiss.IndexFlatIP(embedding_dim)  # 使用精确搜索


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
        r"vtk\.[a-z]+\.[a-z]+\.[a-zA-Z]+", # 匹配 vtk.Rendering.Core.vtkActor 这种完整路径
        r"(vtk[A-Z]\w+)" # 匹配独立的 vtkClassName 如 vtkImageSlice
    ]
    for pattern in module_patterns:
        matches = re.findall(pattern, query, re.IGNORECASE)
        for match in matches:
            # 对于如 vtk.Rendering.Core.vtkActor，我们需要提取 vtkActor
            if isinstance(match, str) and match.lower().startswith('vtk.'): # 完整路径，提取最后一个部分
                last_part = match.split('.')[-1]
                if last_part.lower().startswith('vtk'):
                    analyzed_data['modules'].append(last_part)
            elif isinstance(match, str) and match.lower().startswith('vtk'): # 已经是 vtkClassName 形式
                analyzed_data['modules'].append(match)

    # 简单提取常用模块，如果查询中直接提到了简写形式
    common_modules_short = app_config.VTKJS_COMMON_APIS
    for mod in common_modules_short:
        # 确保不会重复添加已经通过正则匹配到的模块
        if mod.lower() in lower_query and mod not in analyzed_data['modules']:
            # 检查是否是独立单词或后跟非字母数字字符
            if re.search(r'\b' + re.escape(mod.lower()) + r'\b', lower_query):
                 analyzed_data['modules'].append(mod)

    # 移除重复项并保持原始大小写 (如果需要)
    # 这里为了匹配方便，通常会转小写处理，但存储时可以保留原始形式
    analyzed_data['modules'] = list(set([mod for mod in analyzed_data['modules']]))

    print(f"Analyzed query: {analyzed_data}")
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
    
    # 计算每个模块的权重（如果查询中有模块的话）
    num_modules = len(analyzed_query['modules'])
    if num_modules > 0:
        per_module_description_weight = WEIGHT_MODULE_MATCH_IN_DESCRIPTION / num_modules
        per_module_vtkjs_weight = WEIGHT_MODULE_PARTIAL_MATCH_IN_VTKJSM / num_modules
    else:
        per_module_description_weight = 0
        per_module_vtkjs_weight = 0

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
        description_matches = 0  # 记录匹配到的模块数量
        vtkjs_matches = 0  # 记录在vtkjs_modules中匹配到的模块数量
        
        for q_module in analyzed_query['modules']:
            q_module_lower = q_module.lower()
            
            # 1. 检查查询模块是否在文档的 description 中出现
            # 使用部分匹配而不是精确匹配
            if q_module_lower in doc_description:
                if q_module not in matched_modules_in_doc: # 避免对同一个 q_module 因 description 匹配多次加分
                    description_matches += 1
                    matched_modules_in_doc.add(q_module)
            
            # 2. 检查查询模块是否在文档的 vtkjs_modules 列表中部分匹配
            # 这里的目的是将匹配到的模块移到 reordered_doc_modules 的前面
            matched_in_vtkjs_list = []
            for dm in doc_modules_from_meta:
                dm_lower = dm.lower()
                
                # 部分匹配 (例如 "Actor" 匹配 "vtkActor" 或 "RenderingCoreActor")
                if q_module_lower in dm_lower or dm_lower.endswith(q_module_lower.replace('vtk', '')):
                    matched_in_vtkjs_list.append(dm)
                    
                    if q_module not in matched_modules_in_doc: # 如果这个查询模块还没加过分
                        vtkjs_matches += 1
                        matched_modules_in_doc.add(q_module)

            # 将匹配到的模块添加到 reordered_doc_modules 的前面
            for dm in matched_in_vtkjs_list:
                if dm not in reordered_doc_modules:
                    reordered_doc_modules.append(dm)

        # 应用权重：按匹配到的模块数量乘以每个模块的权重
        score += description_matches * per_module_description_weight
        score += vtkjs_matches * per_module_vtkjs_weight

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


# def search_code_optimized(query, k, similarity_threshold, recall_k_multiplier=5):
#     """
#     优化后的检索阶段：根据用户查询获取匹配的代码块，并结合元数据进行重排。
#     Args:
#         query (str): 用户查询文本。
#         k (int): 返回最终前 k 个最相关的结果。
#         similarity_threshold (float, optional): 基础余弦相似度阈值。只召回高于此阈值的结果。
#         recall_k_multiplier (int): 初始召回阶段返回的文档数量是 k 的倍数。
#     """
#     global index
    
#     # 确保索引已训练
#     if not index.is_trained:
#         print("警告: FAISS 索引未训练，尝试重新加载数据...")
#         load_data_from_directory(DATA_DIR)
        
#         # 如果仍然未训练，则返回空结果
#         if not index.is_trained:
#             print("错误: FAISS 索引无法训练，请检查数据目录和文件")
#             return []
    
#     # --- 阶段1: 查询分析 ---
#     analyzed_query = analyze_query(query)
#     print(f"查询分析结果: {analyzed_query}")

#     # --- 阶段2: 粗粒度召回 (FAISS 语义搜索) ---
#     query_vector = embed_text(query)
#     if query_vector.shape[1] != embedding_dim:
#         print(f"错误: 查询向量维度不匹配 ({query_vector.shape[1]} != {embedding_dim})")
#         return []

#     # 确保 nprobe 设置合理，避免除以零
#     if nlist > 0:
#         index.nprobe = max(1, nlist // 5)
#     else:
#         index.nprobe = 1 # Fallback for nlist = 0 or invalid

#     print(f"FAISS IndexIVFFlat nprobe 设置为: {index.nprobe}")

#     recall_k = k * recall_k_multiplier
#     distances, faiss_ids = index.search(query_vector, recall_k)

#     raw_results = []
#     for i, faiss_id in enumerate(faiss_ids[0]):
#         if faiss_id == -1:
#             continue

#         similarity = distances[0][i]
        
#         if similarity_threshold is not None and similarity < similarity_threshold:
#             continue 
        
#         matched_document = mongo_manager.find_code_snippet({"faiss_id": int(faiss_id)})
#         if matched_document:
#             matched_document['faiss_similarity'] = similarity
#             raw_results.append(matched_document)
#             print(f"找到匹配的文档: {matched_document.get('file_path')}\n{similarity:.4f} (FAISS ID: {faiss_id})")

#     # --- 阶段3: 精细化重排 ---
#     if not raw_results:
#         print("初始召回阶段未找到结果。")
#         return []

#     reranked_results = rerank_results(raw_results, analyzed_query)
    
#     # --- 阶段4: 最终选择与返回 ---
#     final_results = []
#     for doc in reranked_results:
#         final_results.append(doc)
#         if len(final_results) >= k: 
#             break

#     return final_results

def search_code_optimized_with_stages(query, k, similarity_threshold, recall_k_multiplier=5):
    """
    优化后的检索阶段：根据用户查询获取匹配的代码块，并返回两个阶段的结果。
    
    Args:
        query (str): 用户查询文本。
        k (int): 返回最终前 k 个最相关的结果。
        similarity_threshold (float, optional): 基础余弦相似度阈值。只召回高于此阈值的结果。
        recall_k_multiplier (int): 初始召回阶段返回的文档数量是 k 的倍数。
        
    Returns:
        tuple: (raw_results, reranked_results)
            - raw_results: 初筛结果（第一阶段 - FAISS 语义搜索）
            - reranked_results: 重排序结果（第二阶段 - 重排）
    """
    global index
    
    # 确保索引已加载
    if index.ntotal == 0:
        print("警告: FAISS 索引为空，尝试加载数据...")
        # 尝试加载索引
        if not load_faiss_index("faiss_index.index"):
            # 如果加载失败，重新加载数据
            load_data_from_directory(DATA_DIR, "faiss_index.index")
        
        # 如果仍然未训练，则返回空结果
        if index.ntotal == 0:
            print("错误: FAISS 索引无法加载，请检查数据目录和文件")
            return [], []
    
    # --- 阶段1: 查询分析 ---
    analyzed_query = analyze_query(query)
    print(f"查询分析结果: {analyzed_query}")

    # --- 阶段2: 粗粒度召回 (FAISS 语义搜索) ---
    query_vector = embed_text(query)
    if query_vector.shape[1] != embedding_dim:
        print(f"错误: 查询向量维度不匹配 ({query_vector.shape[1]} != {embedding_dim})")
        return [], []

    recall_k = k * recall_k_multiplier
    distances, indices = index.search(query_vector, recall_k)

    raw_results = []
    for i, idx in enumerate(indices[0]):
        if idx == -1:
            continue

        similarity = distances[0][i]
        
        if similarity_threshold is not None and similarity < similarity_threshold:
            continue 
        
        # 由于我们不再使用 IDs，需要通过其他方式找到匹配的文档
        # 这里我们获取所有文档并按索引匹配
        all_documents = list(mongo_manager.collection.find({}))
        if idx < len(all_documents):
            matched_document = all_documents[idx]
            matched_document['faiss_similarity'] = similarity
            raw_results.append(matched_document)
            print(f"找到匹配的文档: {matched_document.get('file_path')}\n{similarity:.4f} (Index: {idx})")

    # --- 阶段3: 精细化重排 ---
    if not raw_results:
        print("初始召回阶段未找到结果。")
        return raw_results, []

    reranked_results = rerank_results(raw_results, analyzed_query)
    
    # 返回两个阶段的所有结果（不再截断）
    return raw_results, reranked_results


def search_code_optimized(query, k, similarity_threshold, recall_k_multiplier=5):
    """
    优化后的检索阶段：根据用户查询获取匹配的代码块，并结合元数据进行重排。
    只返回最终的 k 个结果（向后兼容）。
    
    Args:
        query (str): 用户查询文本。
        k (int): 返回最终前 k 个最相关的结果。
        similarity_threshold (float, optional): 基础余弦相似度阈值。只召回高于此阈值的结果。
        recall_k_multiplier (int): 初始召回阶段返回的文档数量是 k 的倍数。
    """
    # 调用新的函数获取两个阶段的结果
    raw_results, reranked_results = search_code_optimized_with_stages(query, k, similarity_threshold, recall_k_multiplier)
    
    # --- 阶段4: 最终选择与返回 ---
    final_results = []
    for doc in reranked_results:
        final_results.append(doc)
        if len(final_results) >= k: 
            break

    return final_results


def search_code_with_topk_analysis(query, k, similarity_threshold, recall_k_multiplier=5):
    """
    优化后的检索阶段：返回前K个选中结果和剩余结果的对比分析数据。
    
    Args:
        query (str): 用户查询文本。
        k (int): 选中的前K个结果数。
        similarity_threshold (float, optional): 基础余弦相似度阈值。
        recall_k_multiplier (int): 初始召回阶段返回的文档数量是 k 的倍数。
    
    Returns:
        dict: 包含以下字段的分析数据
            - 'query': 查询文本
            - 'raw_results': 初筛结果列表
            - 'reranked_results': 重排序结果列表
            - 'top_k_results': 前K个选中的结果
            - 'remaining_results': 剩余的其他结果
            - 'analysis': 统计分析数据
    """
    # 获取两个阶段的所有结果
    raw_results, reranked_results = search_code_optimized_with_stages(query, k, similarity_threshold, recall_k_multiplier)
    
    # 分割前K个和剩余结果
    top_k_results = reranked_results[:k]
    remaining_results = reranked_results[k:]
    
    # 生成分析数据
    analysis = {
        'query': query,
        'total_raw_count': len(raw_results),
        'total_reranked_count': len(reranked_results),
        'top_k_count': len(top_k_results),
        'remaining_count': len(remaining_results),
        'top_k_stats': _analyze_result_group(top_k_results),
        'remaining_stats': _analyze_result_group(remaining_results),
        'comparison': _compare_result_groups(top_k_results, remaining_results)
    }
    
    return {
        'query': query,
        'raw_results': raw_results,
        'reranked_results': reranked_results,
        'top_k_results': top_k_results,
        'remaining_results': remaining_results,
        'analysis': analysis
    }


def _analyze_result_group(results):
    """
    对一组结果进行统计分析。
    
    Args:
        results: 结果列表
    
    Returns:
        dict: 统计数据
    """
    if not results:
        return {
            'count': 0,
            'avg_faiss_similarity': 0,
            'avg_rerank_score': 0,
            'modules': [],
            'module_count': 0
        }
    
    faiss_sims = [r.get('faiss_similarity', 0) for r in results]
    rerank_scores = [r.get('rerank_score', 0) for r in results]
    
    # 收集所有模块
    all_modules = []
    for r in results:
        meta = r.get('meta_info', {})
        modules = meta.get('vtkjs_modules', [])
        if isinstance(modules, list):
            all_modules.extend(modules)
    
    return {
        'count': len(results),
        'avg_faiss_similarity': sum(faiss_sims) / len(faiss_sims) if faiss_sims else 0,
        'min_faiss_similarity': min(faiss_sims) if faiss_sims else 0,
        'max_faiss_similarity': max(faiss_sims) if faiss_sims else 0,
        'avg_rerank_score': sum(rerank_scores) / len(rerank_scores) if rerank_scores else 0,
        'min_rerank_score': min(rerank_scores) if rerank_scores else 0,
        'max_rerank_score': max(rerank_scores) if rerank_scores else 0,
        'total_modules': len(all_modules),
        'unique_modules': len(set(all_modules)),
        'top_modules': _get_top_modules(all_modules, n=10)
    }


def _compare_result_groups(top_k, remaining):
    """
    对两组结果进行对比分析。
    
    Returns:
        dict: 对比数据
    """
    top_k_stats = _analyze_result_group(top_k)
    remaining_stats = _analyze_result_group(remaining)
    
    return {
        'faiss_similarity_diff': top_k_stats['avg_faiss_similarity'] - remaining_stats['avg_faiss_similarity'],
        'rerank_score_diff': top_k_stats['avg_rerank_score'] - remaining_stats['avg_rerank_score'],
        'top_k_avg_faiss': top_k_stats['avg_faiss_similarity'],
        'remaining_avg_faiss': remaining_stats['avg_faiss_similarity'],
        'top_k_avg_rerank': top_k_stats['avg_rerank_score'],
        'remaining_avg_rerank': remaining_stats['avg_rerank_score']
    }


def _get_top_modules(modules, n=10):
    """
    获取出现最频繁的前N个模块。
    
    Args:
        modules: 模块列表
        n: 返回的模块数量
    
    Returns:
        list: 排序的模块列表（降序）
    """
    from collections import Counter
    if not modules:
        return []
    module_counts = Counter(modules)
    return [item[0] for item in module_counts.most_common(n)]


def search_code_optimized_with_analysis(query, k, similarity_threshold, recall_k_multiplier=5):
    """
    优化后的检索阶段（带分析）：返回前K个选中结果和剩余结果的对比分析数据。
    
    Args:
        query (str): 用户查询文本。
        k (int): 返回最终前 k 个最相关的结果。
        similarity_threshold (float, optional): 基础余弦相似度阈值。
        recall_k_multiplier (int): 初始召回阶段返回的文档数量是 k 的倍数。
        
    Returns:
        dict: 包含以下信息的字典
            - 'selected_top_k': 前K个选中的结果列表
            - 'remaining': 剩余的未选中结果列表
            - 'analysis': 选中结果和剩余结果的对比分析
                - 'top_k_count': 选中结果数
                - 'remaining_count': 剩余结果数
                - 'top_k_avg_rerank_score': 选中结果平均重排分数
                - 'remaining_avg_rerank_score': 剩余结果平均重排分数
                - 'top_k_avg_faiss_sim': 选中结果平均FAISS相似度
                - 'remaining_avg_faiss_sim': 剩余结果平均FAISS相似度
                - 'score_gap': 选中和剩余的重排分数差距
                - 'top_k_module_distribution': 选中结果的模块分布
                - 'remaining_module_distribution': 剩余结果的模块分布
                - 'details': 详细对比信息
    """
    # 调用新的函数获取两个阶段的结果
    raw_results, reranked_results = search_code_optimized_with_stages(query, k, similarity_threshold, recall_k_multiplier)
    
    # --- 分割选中和剩余的结果 ---
    selected_top_k = []
    remaining = []
    
    for i, doc in enumerate(reranked_results):
        if i < k:
            selected_top_k.append(doc)
        else:
            remaining.append(doc)
    
    # --- 分析数据 ---
    analysis = {}
    
    # 基本统计
    analysis['top_k_count'] = len(selected_top_k)
    analysis['remaining_count'] = len(remaining)
    
    # 重排分数统计
    if selected_top_k:
        top_k_scores = [doc.get('rerank_score', 0) for doc in selected_top_k]
        analysis['top_k_avg_rerank_score'] = np.mean(top_k_scores)
        analysis['top_k_min_rerank_score'] = np.min(top_k_scores)
        analysis['top_k_max_rerank_score'] = np.max(top_k_scores)
        analysis['top_k_std_rerank_score'] = np.std(top_k_scores) if len(top_k_scores) > 1 else 0
    else:
        analysis['top_k_avg_rerank_score'] = 0
        analysis['top_k_min_rerank_score'] = 0
        analysis['top_k_max_rerank_score'] = 0
        analysis['top_k_std_rerank_score'] = 0
    
    if remaining:
        remaining_scores = [doc.get('rerank_score', 0) for doc in remaining]
        analysis['remaining_avg_rerank_score'] = np.mean(remaining_scores)
        analysis['remaining_min_rerank_score'] = np.min(remaining_scores)
        analysis['remaining_max_rerank_score'] = np.max(remaining_scores)
        analysis['remaining_std_rerank_score'] = np.std(remaining_scores) if len(remaining_scores) > 1 else 0
        
        # 计算分数差距
        if analysis['top_k_count'] > 0 and analysis['remaining_count'] > 0:
            analysis['score_gap'] = analysis['top_k_avg_rerank_score'] - analysis['remaining_avg_rerank_score']
            analysis['score_gap_ratio'] = (analysis['top_k_avg_rerank_score'] / analysis['remaining_avg_rerank_score']) if analysis['remaining_avg_rerank_score'] != 0 else 0
    else:
        analysis['remaining_avg_rerank_score'] = 0
        analysis['remaining_min_rerank_score'] = 0
        analysis['remaining_max_rerank_score'] = 0
        analysis['remaining_std_rerank_score'] = 0
        analysis['score_gap'] = 0
        analysis['score_gap_ratio'] = 0
    
    # FAISS相似度统计
    if selected_top_k:
        top_k_faiss_sims = [doc.get('faiss_similarity', 0) for doc in selected_top_k]
        analysis['top_k_avg_faiss_sim'] = np.mean(top_k_faiss_sims)
        analysis['top_k_min_faiss_sim'] = np.min(top_k_faiss_sims)
        analysis['top_k_max_faiss_sim'] = np.max(top_k_faiss_sims)
    else:
        analysis['top_k_avg_faiss_sim'] = 0
        analysis['top_k_min_faiss_sim'] = 0
        analysis['top_k_max_faiss_sim'] = 0
    
    if remaining:
        remaining_faiss_sims = [doc.get('faiss_similarity', 0) for doc in remaining]
        analysis['remaining_avg_faiss_sim'] = np.mean(remaining_faiss_sims)
        analysis['remaining_min_faiss_sim'] = np.min(remaining_faiss_sims)
        analysis['remaining_max_faiss_sim'] = np.max(remaining_faiss_sims)
    else:
        analysis['remaining_avg_faiss_sim'] = 0
        analysis['remaining_min_faiss_sim'] = 0
        analysis['remaining_max_faiss_sim'] = 0
    
    # 模块分布统计
    def count_modules(docs):
        """统计文档列表中的模块分布"""
        module_dist = {}
        total_modules = 0
        for doc in docs:
            meta = doc.get('meta_info', {})
            modules = meta.get('vtkjs_modules', [])
            total_modules += len(modules)
            for module in modules:
                module_dist[module] = module_dist.get(module, 0) + 1
        return module_dist, total_modules
    
    top_k_modules, top_k_total_modules = count_modules(selected_top_k)
    remaining_modules, remaining_total_modules = count_modules(remaining)
    
    analysis['top_k_module_distribution'] = top_k_modules
    analysis['remaining_module_distribution'] = remaining_modules
    analysis['top_k_avg_modules_per_doc'] = top_k_total_modules / len(selected_top_k) if selected_top_k else 0
    analysis['remaining_avg_modules_per_doc'] = remaining_total_modules / len(remaining) if remaining else 0
    
    # 计算两组之间的不同模块
    all_top_k_modules = set(top_k_modules.keys())
    all_remaining_modules = set(remaining_modules.keys())
    analysis['unique_to_selected'] = list(all_top_k_modules - all_remaining_modules)
    analysis['unique_to_remaining'] = list(all_remaining_modules - all_top_k_modules)
    analysis['common_modules'] = list(all_top_k_modules & all_remaining_modules)
    
    # 详细对比信息
    analysis['details'] = {
        'query': query,
        'k_value': k,
        'threshold': similarity_threshold,
        'recall_multiplier': recall_k_multiplier
    }
    
    return {
        'selected_top_k': selected_top_k,
        'remaining': remaining,
        'analysis': analysis
    }



def load_data_from_directory(directory, index_file="faiss_index.index"):
    """从指定目录读取所有文件并添加到数据库."""
    global index

    if not os.path.isdir(directory):
        print(f"错误: 目录不存在或不是一个有效目录: {directory}")
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

    # 重新创建索引以确保它是空的
    index = faiss.IndexFlatIP(embedding_dim)
    print("已重置为新的 FAISS 精确搜索索引")
    
    # 添加向量到索引（不使用 IDs）
    if len(all_vectors) > 0:
        vectors_array = np.array(all_vectors).astype('float32')
        index.add(vectors_array)
        print(f"批量添加到 FAISS 成功，共添加 {vectors_array.shape[0]} 个向量。")
        
        # 保存索引到文件
        faiss.write_index(index, index_file)
        print(f"FAISS 索引已保存到 {index_file}")
    else:
        print("没有向量可以添加到 FAISS。")

    # 清空 MongoDB 集合并重新插入数据
    mongo_manager.collection.delete_many({})
    mongo_documents_to_insert = [item[2] for item in documents_for_faiss_and_mongo]
    if mongo_documents_to_insert:
        try:
            mongo_manager.collection.insert_many(mongo_documents_to_insert)
        except Exception as e:
            print(f"批量插入到 MongoDB 失败: {e}")
    else:
        print("没有文档可以插入到 MongoDB。")
    
    print("数据加载完成。")


def load_faiss_index(index_file="faiss_index.index"):
    """从文件加载FAISS索引"""
    global index
    try:
        if os.path.exists(index_file):
            index = faiss.read_index(index_file)
            print(f"FAISS 索引已从 {index_file} 加载")
            return True
        else:
            print(f"FAISS 索引文件 {index_file} 不存在")
            return False
    except Exception as e:
        print(f"加载 FAISS 索引时出错: {e}")
        return False

def save_faiss_index(index_file="faiss_index.index"):
    """保存FAISS索引到文件"""
    global index
    try:
        faiss.write_index(index, index_file)
        print(f"FAISS 索引已保存到 {index_file}")
    except Exception as e:
        print(f"保存 FAISS 索引时出错: {e}")

def process_nested_queries_and_log(splited_queries_nested, output_filename="output2.txt"):
    """
    执行优化查询，并将结果同时打印到控制台和写入到指定文件。
    此版本支持嵌套的查询列表结构，并且每组查询只选取重排分数最高的6个结果。

    Args:
        splited_queries_nested (list): 包含嵌套查询字典列表的列表。
        output_filename (str): 要写入输出的文件名。
    """
    all_results = []  # 用于收集所有结果
    
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

            group_results = []  # 用于收集当前组的结果
            
            # 记录查询组开始时间
            group_start_time = time.time()
            
            # 收集当前组所有查询的结果
            all_current_group_results = []
            for query_idx, query_item in enumerate(query_group):
                query_description = query_item['description']
                query_header = f"\n===== 查询 {query_idx + 1}: '{query_description}' =====\n"
                print(query_header, end='')
                f.write(query_header)

                # Assume search_code_optimized is defined elsewhere and works with a single description string
                current_results = search_code_optimized(query_description, K, similarity_threshold=Similarity_Threshold)
                all_current_group_results.extend(current_results)

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
                        # print(file_path, end='')
                        f.write(file_path)

                        description_meta = f'描述: {meta.get("description", "N/A")}\n' # Renamed to avoid conflict
                        # print(description_meta, end='')
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
                
            # 对当前组的所有结果进行去重和排序，选取重排分数最高的6个
            unique_results = {}
            for result in all_current_group_results:
                faiss_id = result.get("faiss_id")
                rerank_score = result.get("rerank_score", 0)
                
                # 如果这是第一次遇到该文档，或者找到了更高分数的相同文档
                if faiss_id not in unique_results or unique_results[faiss_id].get("rerank_score", 0) < rerank_score:
                    unique_results[faiss_id] = result
            
            # 转换为列表并按重排分数降序排序
            deduplicated_results = list(unique_results.values())
            deduplicated_results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            
            # 选取重排分数最高的6个结果
            top_6_results = deduplicated_results[:6]
            
            # 记录查询组结束时间并计算耗时
            group_end_time = time.time()
            group_duration = group_end_time - group_start_time
            
            # 写入每组查询中重排分数最高的6个结果到文件
            top_results_header = f"\n--- 查询组 {group_idx + 1} 中重排分数最高的6个结果 (耗时: {group_duration:.2f}秒) ---\n"
            print(top_results_header, end='')
            f.write(top_results_header)
            
            if top_6_results:
                for j, result in enumerate(top_6_results):
                    result_start = f'\n--- 顶级结果 {j+1} ---\n'
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
                    f.write(file_path)

                    description_meta = f'描述: {meta.get("description", "N/A")}\n'
                    f.write(description_meta)

                    vtkjs_modules = f'VTK.js 模块 (排序后): {meta.get("vtkjs_modules", "N/A")}\n'
                    print(vtkjs_modules, end='')
                    f.write(vtkjs_modules)

                    separator = f'\n--------------------------------------------------------------------------------------------------------------\n'
                    print(separator, end='')
                    f.write(separator)
            else:
                no_results_message = f"查询组 {group_idx + 1} 未找到结果。\n"
                print(no_results_message, end='')
                f.write(no_results_message)
            
            # 将当前组的结果添加到组结果中
            group_results.append({
                'query_group': group_idx + 1,
                'top_results': top_6_results,
                'duration': group_duration
            })

            # 将组结果添加到所有结果中
            all_results.append(group_results)

        # 写入并打印结束信息
        end_message = "\n--- 所有查询执行完毕 ---\n"
        print(end_message, end='')
        f.write(end_message)
    
    # 返回所有结果
    return all_results
    
def read_splited_prompts(input_file="res2.xlsx"):
    """
    读取Excel文件中的splited_prompt列，解析其中的JSON列表数据
    
    Args:
        input_file: 输入Excel文件路径
        
    Returns:
        list: 包含所有解析后的splited_prompt列表的列表
    """
    try:
        # 读取Excel文件
        df = pd.read_excel(input_file, sheet_name='第二期实验数据')
        
        # 检查是否存在splited_prompt列
        if 'splited_prompt' not in df.columns:
            raise ValueError("Excel文件中必须包含'splited_prompt'列")
        
        splited_prompts_list = []
        
        # 处理每个splited_prompt
        for index, row in df.iterrows():
            splited_prompt_str = row['splited_prompt']
            
            if pd.isna(splited_prompt_str) or splited_prompt_str == '' or splited_prompt_str == '分析失败':
                print(f"跳过第{index+1}行：空的或无效的splited_prompt")
                splited_prompts_list.append([])  # 添加空列表
                continue
                
            try:
                # 解析JSON字符串
                splited_prompt = json.loads(splited_prompt_str)
                if isinstance(splited_prompt, list):
                    splited_prompts_list.append(splited_prompt)
                    print(f"第{index+1}行解析成功，包含{len(splited_prompt)}个元素")
                else:
                    print(f"第{index+1}行解析结果不是列表格式")
                    splited_prompts_list.append([])
            except json.JSONDecodeError as e:
                print(f"第{index+1}行JSON解析失败: {e}")
                splited_prompts_list.append([])
            except Exception as e:
                print(f"第{index+1}行处理出错: {e}")
                splited_prompts_list.append([])
        
        return splited_prompts_list
        
    except Exception as e:
        print(f"读取文件时出错: {e}")
        return []

def process_splited_prompts_for_rag(input_file="res2.xlsx"):
    """
    读取splited_prompt数据并为RAG检索做准备
    """
    try:
        # 读取分割后的提示词
        splited_prompts = read_splited_prompts(input_file)
        
        if not splited_prompts:
            print("未读取到有效的splited_prompt数据")
            return []
        
        print(f"成功读取到{len(splited_prompts)}组分割后的提示词")
        
        # 处理数据以适应RAG的输入格式
        rag_input_data = []
        for i, prompt_list in enumerate(splited_prompts):
            if prompt_list and isinstance(prompt_list, list):
                # 确保每个元素都是字典且包含description字段
                valid_prompts = []
                for item in prompt_list:
                    if isinstance(item, dict) and 'description' in item:
                        valid_prompts.append(item)
                    elif isinstance(item, str):
                        # 如果是字符串，转换为标准格式
                        valid_prompts.append({'description': item})
                
                if valid_prompts:
                    rag_input_data.append(valid_prompts)
                    print(f"第{i+1}组提示词包含{len(valid_prompts)}个有效项")
                else:
                    rag_input_data.append([])
                    print(f"第{i+1}组没有有效提示词")
            else:
                rag_input_data.append([])
                print(f"第{i+1}组不是有效的提示词列表")
        
        return rag_input_data
        
    except Exception as e:
        print(f"处理splited_prompt数据时出错: {e}")
        return []

def save_rag_results_to_excel(input_file="res2.xlsx", output_file="res2.xlsx", rag_results=None):
    """
    将RAG检索结果保存到Excel文件中
    
    Args:
        input_file: 输入Excel文件路径
        output_file: 输出Excel文件路径
        rag_results: RAG检索结果列表
    """
    try:
        # 读取原始Excel文件
        df = pd.read_excel(input_file, sheet_name='第二期实验数据')
        
        # 确保必要的列存在
        if 'rag_retrieval_result' not in df.columns:
            df['rag_retrieval_result'] = ''
        if 'time_spend_rag' not in df.columns:
            df['time_spend_rag'] = ''
        
        # 强制将这两列转换为字符串类型
        df['rag_retrieval_result'] = df['rag_retrieval_result'].astype(str)
        df['time_spend_rag'] = df['time_spend_rag'].astype(str)
        
        # 如果提供了RAG结果，则写入
        if rag_results and isinstance(rag_results, list):
            for index, result in enumerate(rag_results):
                if index < len(df) and result is not None:
                    # 将结果转换为字符串保存
                    if isinstance(result, list):
                        df.at[index, 'rag_retrieval_result'] = str(json.dumps(result, ensure_ascii=False, indent=2))
                    else:
                        df.at[index, 'rag_retrieval_result'] = str(result)
        
        # 保存到Excel文件
        with pd.ExcelWriter(output_file, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df.to_excel(writer, sheet_name='第二期实验数据', index=False)
        
        print(f"RAG结果已保存到 {output_file}")
        return df
        
    except Exception as e:
        print(f"保存RAG结果时出错: {e}")
        return None




if __name__ == '__main__':
    index_file = "faiss_index.index"
    
    # 尝试加载已存在的索引
    if not load_faiss_index(index_file) or index.ntotal == 0:
        if mongo_manager.collection.count_documents({}) == 0 or index.ntotal == 0:
            print("检测到数据库为空，正在初始化数据...")
            mongo_manager.clear_collection()
            
            # 重置 FAISS 索引（使用精确搜索）
            index = faiss.IndexFlatIP(embedding_dim)
            print("已重置为 FAISS 精确搜索索引并清空 MongoDB 集合。")

            # 确保 DATA_DIR 存在且指向包含你的 vtkjs-examples 的路径
            load_data_from_directory(DATA_DIR, index_file)
            print("数据初始化完成。")
        else:
            print("检测到已有数据，直接使用现有数据库...")
    else:
        print("检测到已有FAISS索引，直接使用现有索引...")
        
    print(f"FAISS 索引中当前有 {index.ntotal} 个向量。")
    print(f"MongoDB 集合中当前有 {mongo_manager.collection.count_documents({})} 个文档。")

     # 文件路径
    path = "D://Pcode//LLM4VIS//llmscivis//data//recoreds//res2.xlsx"
    
    # 读取并处理splited_prompt数据
    splited_queries = process_splited_prompts_for_rag(path)
    
    
    process_nested_queries_and_log(splited_queries)
    if mongo_manager.collection.count_documents({}) == 0 or index.ntotal == 0:
        print("检测到数据库为空，正在初始化数据...")
        mongo_manager.clear_collection()
        
        # 重置 FAISS 索引（使用精确搜索）
        index = faiss.IndexFlatIP(embedding_dim)
        print("已重置为 FAISS 精确搜索索引并清空 MongoDB 集合。")

        # 确保 DATA_DIR 存在且指向包含你的 vtkjs-examples 的路径
        load_data_from_directory(DATA_DIR)
        print("数据初始化完成。")
    else:
        print("检测到已有数据，直接使用现有数据库...")
        
    print(f"FAISS 索引中当前有 {index.ntotal} 个向量。")
    print(f"MongoDB 集合中当前有 {mongo_manager.collection.count_documents({})} 个文档。")

     # 文件路径
    path = "D://Pcode//LLM4VIS//llmscivis//data//recoreds//res2.xlsx"
    
    # 读取并处理splited_prompt数据
    splited_queries = process_splited_prompts_for_rag(path)
    
    
    process_nested_queries_and_log(splited_queries)