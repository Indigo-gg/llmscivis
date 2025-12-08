import pymongo
import json
import re
import numpy as np
import time
import pandas as pd
import os
from config.app_config import app_config

# --- 配置区域 ---
# 由于不再使用语义相似度，我们可以调整权重策略
# 基础分默认为0，主要靠关键词命中得分
WEIGHT_BASE_SIMILARITY = 0.0 
WEIGHT_MODULE_MATCH_IN_DESCRIPTION = 1.0  # 提高描述匹配的权重
WEIGHT_MODULE_PARTIAL_MATCH_IN_VTKJSM = 2.0  # 提高模块列表匹配的权重

# 数据库配置
DB_HOST = 'localhost'
DB_PORT = 27017
DB_NAME = 'code_database'
COLLECTION_NAME = 'code_snippets'

class MongoDBManager:
    def __init__(self, host, port, db_name, collection_name):
        self.client = pymongo.MongoClient(host, port)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        print(f"MongoDBManager initialized. Connected to DB: {db_name}, Collection: {collection_name}")

    def find_docs_by_modules(self, modules):
        """
        根据模块列表查找包含任意一个模块的文档。
        由于数据库存储的是 "vtk.Rendering.Core.vtkActor" 这种全路径，
        而查询提取的是 "vtkActor"，所以必须使用正则后缀匹配。
        """
        if not modules or self.collection is None:
            return []
        
        # 构造正则查询列表
        # 逻辑：匹配字符串结尾是该模块名的情况 (忽略大小写)
        # 例如: 匹配 "vtkImageSlice" 或 "...vtkImageSlice"
        regex_list = []
        for m in modules:
            # re.escape 用于防止模块名中包含特殊字符（虽然 vtk 类名通常没有）
            # $ 表示匹配字符串结尾
            regex_list.append(re.compile(f"{re.escape(m)}$", re.IGNORECASE))

        # 使用 $in 配合正则对象，MongoDB 会匹配列表中满足任意正则的项
        query = {
            "meta_info.vtkjs_modules": {
                "$in": regex_list
            }
        }
        
        try:
            cursor = self.collection.find(query)
            return list(cursor)
        except Exception as e:
            print(f"MongoDB Query Error: {e}")
            return []

# 初始化 MongoDB 管理器
mongo_manager = MongoDBManager(DB_HOST, DB_PORT, DB_NAME, COLLECTION_NAME)


# --- 不需要的功能置空或保留接口 ---

def embed_text(text):
    """(已废弃) 不需要向量化"""
    return None

def load_data_from_directory(directory, index_file=None):
    """(已保留接口但不再构建FAISS) 仅用于查看或调试"""
    print("Log: load_data_from_directory called but FAISS logic is disabled in this new scheme.")
    pass

# --- 核心逻辑 ---

def analyze_query(query: str):
    """
    分析用户查询，提取潜在的 VTK.js 模块。
    """
    analyzed_data = {
        "modules": []
    }

    lower_query = query.lower()

    # 1. 正则提取 VTK.js 模块名称
    module_patterns = [
        r"vtk\.?[\w\.]*?vtk([A-Z]\w+)", # 匹配 vtk.Namespace.vtkClassName 或 vtkClassName
        r"vtk\.[a-z]+\.[a-z]+\.[a-zA-Z]+", # 匹配完整路径
        r"(vtk[A-Z]\w+)" # 匹配独立 vtkClassName
    ]
    for pattern in module_patterns:
        matches = re.findall(pattern, query, re.IGNORECASE)
        for match in matches:
            if isinstance(match, str) and match.lower().startswith('vtk.'): 
                last_part = match.split('.')[-1]
                if last_part.lower().startswith('vtk'):
                    analyzed_data['modules'].append(last_part)
            elif isinstance(match, str) and match.lower().startswith('vtk'):
                analyzed_data['modules'].append(match)

    # 2. 常用模块简写匹配
    common_modules_short = app_config.VTKJS_COMMON_APIS if hasattr(app_config, 'VTKJS_COMMON_APIS') else []
    for mod in common_modules_short:
        if mod.lower() in lower_query and mod not in analyzed_data['modules']:
            if re.search(r'\b' + re.escape(mod.lower()) + r'\b', lower_query):
                 analyzed_data['modules'].append(mod)

    # 去重
    analyzed_data['modules'] = list(set([mod for mod in analyzed_data['modules']]))

    print(f"Analyzed query modules: {analyzed_data['modules']}")
    return analyzed_data

def rerank_results(raw_results, analyzed_query):
    """
    对召回结果进行重排。
    由于没有了向量相似度，这里的排序完全依赖于 Query 中的模块在 Document 中的命中情况。
    """
    reranked_results = []
    
    # 获取查询中提取出的模块数量
    query_modules = analyzed_query.get('modules', [])
    num_query_modules = len(query_modules)

    # 如果查询没提取出模块，这套逻辑基本失效，只能返回原始顺序
    if num_query_modules == 0:
        for doc in raw_results:
            doc['rerank_score'] = 0
            reranked_results.append(doc)
        return reranked_results

    # 动态计算权重（为了归一化，可选）
    # 这里直接使用固定权重即可，因为我们只关心相对顺序
    
    for doc in raw_results:
        meta = doc.get("meta_info", {})
        doc_description = meta.get('description', '').lower()
        doc_modules_from_meta = meta.get('vtkjs_modules', [])
        
        # 确保 doc_modules_from_meta 是列表
        if isinstance(doc_modules_from_meta, str):
            doc_modules_from_meta = doc_modules_from_meta.split(',')

        # 基础分（此处为0，因为没有向量相似度）
        base_score = doc.get('faiss_similarity', 0.0) * WEIGHT_BASE_SIMILARITY
        score = base_score
        
        reordered_doc_modules = []
        matched_modules_in_doc = set()
        
        description_matches = 0
        vtkjs_list_matches = 0
        
        # --- 遍历查询模块进行打分 ---
        for q_module in query_modules:
            q_module_lower = q_module.lower()
            q_module_clean = q_module_lower.replace('vtk', '') # 处理 vtkActor -> Actor
            
            # 1. 检查 Description 匹配
            if q_module_lower in doc_description:
                if q_module not in matched_modules_in_doc:
                    description_matches += 1
                    matched_modules_in_doc.add(q_module)
            
            # 2. 检查 vtkjs_modules 列表匹配 (支持 "Actor" 匹配 "vtkActor")
            matched_in_list = False
            for dm in doc_modules_from_meta:
                dm_lower = dm.lower()
                # 匹配逻辑：完全相等 或 后缀匹配 (例如 Query是Actor, Doc有vtkActor)
                if q_module_lower == dm_lower or dm_lower.endswith(q_module_clean):
                    if dm not in reordered_doc_modules:
                        reordered_doc_modules.append(dm)
                    matched_in_list = True
            
            if matched_in_list:
                # 只有当该模块还没有贡献过分数时才加分（避免同一个模块在描述和列表中重复加分，或者根据需求叠加）
                # 这里策略是：只要在列表中出现了，就加分
                vtkjs_list_matches += 1

        # 计算总分
        # score = (匹配到的描述关键词数 * 权重) + (匹配到的模块列表数 * 权重)
        score += (description_matches * WEIGHT_MODULE_MATCH_IN_DESCRIPTION)
        score += (vtkjs_list_matches * WEIGHT_MODULE_PARTIAL_MATCH_IN_VTKJSM)

        # 补充未匹配的模块到排序后的列表尾部
        for dm in doc_modules_from_meta:
            if dm not in reordered_doc_modules:
                reordered_doc_modules.append(dm)
        
        doc['meta_info']['vtkjs_modules'] = reordered_doc_modules
        doc['rerank_score'] = score
        
        # 仅保留分数大于0的结果（可选，防止无关文档混入，但既然是精确查找，查出来的肯定有关）
        reranked_results.append(doc)

    # 按重排分数降序排序
    reranked_results.sort(key=lambda x: x.get('rerank_score', 0), reverse=True)
    return reranked_results

def search_code_optimized(query, k, similarity_threshold=None, recall_k_multiplier=5):
    """
    新版检索接口：
    1. 解析 Query 提取 VTK 模块关键词。
    2. 直接查询 MongoDB (跳过 Vector Search)。
    3. 进行重排序。
    """
    
    # --- 阶段1: 查询分析 ---
    analyzed_query = analyze_query(query)
    modules = analyzed_query.get('modules', [])
    
    if not modules:
        print(f"Warning: No VTK modules extracted from query: '{query}'. Skipping search.")
        # 如果没有提取到关键词，直接返回空，因为我们不做相似度检索了
        return []

    # --- 阶段2: 数据库精确匹配 (替代原 FAISS 召回) ---
    print(f"Searching DB for modules: {modules}")
    raw_results = mongo_manager.find_docs_by_modules(modules)
    
    print(f"Found {len(raw_results)} documents containing at least one of the modules.")
    
    if not raw_results:
        return []
    
    # 填充假的 similarity 以兼容 rerank_results 逻辑 (如果有用到)
    for doc in raw_results:
        doc['faiss_similarity'] = 0.0

    # --- 阶段3: 精细化重排 ---
    reranked_results = rerank_results(raw_results, analyzed_query)
    
    # --- 阶段4: 截取 Top K ---
    final_results = reranked_results[:k]
    
    return final_results

# --- 辅助函数：支持之前的分析逻辑接口 ---

def search_code_optimized_with_stages(query, k, similarity_threshold, recall_k_multiplier=5):
    """
    为了兼容旧接口的分析功能，模拟两个阶段的输出。
    Raw results 这里就是 MongoDB 直接查询的结果。
    """
    analyzed_query = analyze_query(query)
    modules = analyzed_query.get('modules', [])
    
    raw_results = []
    if modules:
        raw_results = mongo_manager.find_docs_by_modules(modules)
        for doc in raw_results:
            doc['faiss_similarity'] = 0.0 # Placeholder
            
    reranked_results = rerank_results(raw_results, analyzed_query) if raw_results else []
    
    return raw_results, reranked_results

def search_code_with_topk_analysis(query, k, similarity_threshold, recall_k_multiplier=5):
    """
    保持接口不变，提供分析数据
    """
    raw_results, reranked_results = search_code_optimized_with_stages(query, k, similarity_threshold, recall_k_multiplier)
    
    top_k_results = reranked_results[:k]
    remaining_results = reranked_results[k:]
    
    # 构造简化的分析对象（因为没有 faiss similarity，相关统计为 0）
    analysis = {
        'query': query,
        'total_raw_count': len(raw_results),
        'total_reranked_count': len(reranked_results),
        'top_k_count': len(top_k_results),
        'note': "Keyword-based search only (No embedding similarity)."
    }
    
    return {
        'query': query,
        'raw_results': raw_results,
        'reranked_results': reranked_results,
        'top_k_results': top_k_results,
        'remaining_results': remaining_results,
        'analysis': analysis
    }

# --- 执行入口逻辑 (保持你原有的 Excel 处理逻辑) ---
# 下面的 process_nested_queries_and_log 等函数不需要修改，直接调用上面的 search_code_optimized 即可

def process_nested_queries_and_log(splited_queries_nested, output_filename="output_keyword_only.txt"):
    # ... (保持原有的打印和文件写入逻辑不变) ...
    # 只需要确保调用的是上面新定义的 search_code_optimized
    
    all_results = []
    # 这里为了简短展示，省略具体的打印代码实现，逻辑与你提供的一致
    # 重点是 loop 内部调用 search_code_optimized(query_description, K, ...)
    
    # 此处仅作代码结构的占位，实际运行时请复制你原有的 process_nested_queries_and_log 实现
    # 确保 K 值定义
    K = 4 
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        print("Starting Keyword-Based Search Process...", file=f)
        for group_idx, query_group in enumerate(splited_queries_nested):
             for query_item in query_group:
                 desc = query_item.get('description', '')
                 # 调用新的检索接口
                 results = search_code_optimized(desc, K)
                 # ... Log results ...
    return all_results

def process_splited_prompts_for_rag(input_file):
    # ... (保持原有的 Excel 读取逻辑) ...
    try:
        df = pd.read_excel(input_file, sheet_name='第二期实验数据')
        splited_prompts_list = []
        for index, row in df.iterrows():
            splited_prompt_str = row.get('splited_prompt', '')
            try:
                if splited_prompt_str and not pd.isna(splited_prompt_str):
                    splited_prompt = json.loads(splited_prompt_str)
                    # 格式清洗
                    valid = []
                    for item in splited_prompt:
                        if isinstance(item, dict) and 'description' in item:
                            valid.append(item)
                    splited_prompts_list.append(valid)
                else:
                    splited_prompts_list.append([])
            except:
                splited_prompts_list.append([])
        return splited_prompts_list
    except Exception as e:
        print(e)
        return []

if __name__ == '__main__':
    # 文件路径
    path = "D://Pcode//LLM4VIS//llmscivis//data//recoreds//res2.xlsx"
    
    print("开始读取 Excel...")
    splited_queries = process_splited_prompts_for_rag(path)
    
    print(f"读取到 {len(splited_queries)} 组查询，开始执行检索...")
    
    # 这里你需要把原本的 process_nested_queries_and_log 完整逻辑放进来
    # 或者像下面这样简单遍历测试：
    for i, group in enumerate(splited_queries):
        if not group: continue
        print(f"\n--- Group {i+1} ---")
        for q in group:
            desc = q['description']
            print(f"Query: {desc}")
            results = search_code_optimized(desc, k=4)
            for res in results:
                print(f"  -> Match: {res['meta_info']['file_path']} | Score: {res['rerank_score']}")