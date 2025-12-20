import pymongo
import json
import re
import time
import pandas as pd
import os
from typing import List, Dict, Any
# from config.app_config import app_config # 如果本地没有 config 文件，请注释掉这一行，使用下方的默认配置

# --- 配置区域 ---
DB_HOST = 'localhost'
DB_PORT = 27017
DB_NAME = 'code_database'
COLLECTION_NAME = 'code_snippets'

# 默认配置，防止缺少 config 文件报错


class AppConfig:
    VTKJS_COMMON_APIS = [
        "vtkActor", "vtkMapper", "vtkSphereSource", "vtkConeSource",
        "vtkCylinderSource", "vtkRenderer", "vtkRenderWindow",
        "vtkRenderWindowInteractor", "vtkLookupTable", "vtkColorTransferFunction"
    ]


try:
    from config.app_config import app_config
except ImportError:
    app_config = AppConfig()

# --- 导入必要的模块 ---
from RAG.vtk_code_meta_extract import extract_vtkjs_meta, get_project_root

# --- 数据库管理类 ---


class MongoDBManager:
    def __init__(self, host, port, db_name, collection_name):
        try:
            self.client = pymongo.MongoClient(
                host, port, serverSelectionTimeoutMS=2000)
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]
            # 测试连接
            self.client.server_info()
            print(
                f"MongoDBManager initialized. Connected to DB: {db_name}, Collection: {collection_name}")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            self.collection = None

    def find_docs_by_modules(self, modules):
        """
        根据模块列表查找包含任意一个模块的文档。
        [修复版] 使用正则后缀匹配，解决 vtkActor 无法匹配 vtk.Rendering.Core.vtkActor 的问题。
        """
        if not modules or self.collection is None:
            return []

        # 构造正则查询列表
        # 逻辑：匹配字符串结尾是该模块名的情况 (忽略大小写)
        # 例如: 匹配 "vtkImageSlice" 或 "...vtkImageSlice"
        regex_list = []
        for m in modules:
            # re.escape 用于防止模块名中包含特殊字符
            # $ 表示匹配字符串结尾
            regex_list.append(re.compile(f"{re.escape(m)}$", re.IGNORECASE))

        # 使用 $in 配合正则对象
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


# 初始化全局 MongoDB 管理器
mongo_manager = MongoDBManager(DB_HOST, DB_PORT, DB_NAME, COLLECTION_NAME)

# --- 核心辅助函数 ---


def analyze_query(query: str):
    """
    分析查询文本，提取潜在的 VTK.js 模块关键词。
    """
    analyzed_data = {
        "modules": []
    }

    lower_query = query.lower()

    # 1. 正则提取 VTK.js 模块名称
    module_patterns = [
        # 匹配 vtk.Namespace.vtkClassName 或 vtkClassName
        r"vtk\.?[\w\.]*?vtk([A-Z]\w+)",
        r"vtk\.[a-z]+\.[a-z]+\.[a-zA-Z]+",  # 匹配完整路径
        r"(vtk[A-Z]\w+)"  # 匹配独立 vtkClassName
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
    common_modules_short = app_config.VTKJS_COMMON_APIS
    for mod in common_modules_short:
        if mod.lower() in lower_query and mod not in analyzed_data['modules']:
            # 完整单词匹配
            if re.search(r'\b' + re.escape(mod.lower()) + r'\b', lower_query):
                analyzed_data['modules'].append(mod)

    # 去重
    analyzed_data['modules'] = list(
        set([mod for mod in analyzed_data['modules']]))
    return analyzed_data

# --- 重排序核心逻辑类 ---


class WeightedRanker:
    """
    专门负责利用带权重的查询对候选文档进行打分和排序的类。
    是对【语料】进行排序，依据是文档解决了多少高权重的子查询需求。
    """

    def __init__(self, raw_docs):
        self.raw_docs = raw_docs  # 候选文档池（去重后的）
        self.doc_scores = {}      # 记录每个文档的得分 {doc_id: score}
        self.doc_details = {}     # 记录每个文档的匹配详情（用于解释/调试）

    def calculate_scores(self, query_list_with_weights):
        """
        核心逻辑：遍历每一个带有权重的子查询，给文档加分。
        """
        # 1. 计算总权重用于归一化
        total_weight = 0
        valid_queries = []

        for q in query_list_with_weights:
            # 兼容处理：确保 weight 存在且为数字
            w = q.get('weight', 5)
            try:
                w = float(w)
            except:
                w = 5.0

            # 标记解析后的权重
            q['parsed_weight'] = w
            total_weight += w
            valid_queries.append(q)

        if total_weight == 0:
            total_weight = 1

        # 2. 遍历每个子查询（作为评分标准）
        for query_item in valid_queries:
            q_text = query_item.get('description', '')
            q_weight = query_item.get('parsed_weight')

            # 提取关键词
            analyzed = analyze_query(q_text)
            q_modules = analyzed.get('modules', [])

            if not q_modules:
                continue

            # 3. 遍历所有候选文档，计算得分
            for doc in self.raw_docs:
                # 获取唯一ID，优先 FAISS ID，其次 File Path
                doc_id = doc.get("faiss_id")
                if doc_id is None:
                    doc_id = doc.get("file_path") or doc.get(
                        "meta_info", {}).get("file_path")

                # 计算该文档对当前查询的命中数 (Keywords Hit)
                hits, matched_keywords = self._count_hits(doc, q_modules)

                if hits > 0:
                    # --- 打分公式 ---
                    # 得分 = 命中关键词数量 * 该查询的原始权重
                    # 这是一个累加过程：文档能解决的问题越多，总分越高
                    score_increment = hits * q_weight

                    self.doc_scores[doc_id] = self.doc_scores.get(
                        doc_id, 0) + score_increment

                    # 记录详情
                    if doc_id not in self.doc_details:
                        self.doc_details[doc_id] = {
                            "doc_obj": doc,
                            "matches": [],
                            "all_matched_keywords": set()
                        }

                    self.doc_details[doc_id]["matches"].append(
                        f"Query: '{q_text}' (w={q_weight}) -> Hit {hits} keys"
                    )
                    self.doc_details[doc_id]["all_matched_keywords"].update(
                        matched_keywords)

    def _count_hits(self, doc, query_modules):
        """辅助函数：计算文档命中了多少个关键词"""
        meta = doc.get("meta_info", {})
        doc_modules = meta.get('vtkjs_modules', [])
        if isinstance(doc_modules, str):
            doc_modules = doc_modules.split(',')
        doc_desc = meta.get('description', '').lower()

        doc_modules_lower = set([m.lower().strip() for m in doc_modules])
        count = 0
        matched = []

        for qm in query_modules:
            qm_lower = qm.lower()
            qm_clean = qm_lower.replace('vtk', '')  # 处理 vtkActor -> Actor

            # 匹配逻辑：模块名精确/后缀匹配 OR 描述包含
            hit = False
            # A. 检查模块列表
            for dm in doc_modules_lower:
                if qm_lower == dm or dm.endswith(qm_clean):
                    hit = True
                    break
            # B. 检查描述 (如果模块没匹配到)
            if not hit and qm_lower in doc_desc:
                hit = True

            if hit:
                count += 1
                matched.append(qm)

        return count, matched

    def get_ranked_results(self, top_k=6):
        """
        返回排序后的文档列表
        """
        ranked_list = []
        for doc_id, score in self.doc_scores.items():
            details = self.doc_details[doc_id]
            doc = details["doc_obj"]

            # 将计算数据写入文档对象，方便前端展示
            doc['rerank_score'] = score
            doc['match_explanation'] = details["matches"]
            doc['matched_keywords'] = list(details["all_matched_keywords"])

            ranked_list.append(doc)

        # --- 对语料进行排序 ---
        # 依据：累加后的相关性总分
        ranked_list.sort(key=lambda x: x['rerank_score'], reverse=True)

        return ranked_list[:top_k]

# --- 数据库初始化函数 ---


def initialize_database(data_dir=None, force_reinit=False):
    """
    初始化 MongoDB 数据库，从指定目录加载 VTK.js 代码示例。
    
    Args:
        data_dir (str): 数据目录路径。如果为 None，使用默认路径。
        force_reinit (bool): 是否强制重新初始化数据库（清空现有数据）。
    
    Returns:
        bool: 初始化是否成功。
    """
    import os
    import hashlib
    
    if data_dir is None:
        # 默认数据目录
        project_root = get_project_root()
        data_dir = os.path.join(project_root, 'data', 'vtkjs-examples', 'prompt-sample')
    
    print(f"\n--- 数据库初始化 ---")
    print(f"检查数据库连接...")
    
    # 检查集合是否为空
    if mongo_manager.collection is None:
        print(f"✗ 无法连接到 MongoDB")
        return False
    
    doc_count = mongo_manager.collection.count_documents({})
    
    if doc_count > 0 and not force_reinit:
        print(f"✓ 数据库已初始化，包含 {doc_count} 个文档")
        return True
    
    # 验证数据目录
    if not os.path.isdir(data_dir):
        print(f"✗ 数据目录不存在: {data_dir}")
        return False
    
    print(f"开始从目录加载数据: {data_dir}")
    
    # 清空现有数据
    if doc_count > 0:
        print(f"清空现有 {doc_count} 个文档...")
        mongo_manager.collection.delete_many({})
    
    # 遍历目录并加载数据
    documents_to_insert = []
    processed_count = 0
    
    for root, dirs, files in os.walk(data_dir):
        for filename in files:
            if filename == 'code.html':
                file_path = os.path.join(root, filename)
                
                try:
                    # 提取元信息
                    meta_info = extract_vtkjs_meta(file_path)
                    
                    # 加载代码内容
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            code_content = f.read()
                    except:
                        continue
                    
                    # 生成 FAISS ID
                    faiss_id = int(hashlib.sha1(file_path.encode("utf-8")).hexdigest(), 16) % (2**31 - 1)
                    if faiss_id < 0:
                        faiss_id *= -1
                    
                    # 构建文档
                    mongo_document = {
                        "faiss_id": faiss_id,
                        "file_path": file_path,
                        "code": code_content,
                        "meta_info": meta_info
                    }
                    
                    documents_to_insert.append(mongo_document)
                    processed_count += 1
                    
                except Exception as e:
                    print(f"  警告: 处理文件时出错 {file_path}: {e}")
                    continue
    
    if not documents_to_insert:
        print(f"✗ 未找到任何数据文件")
        return False
    
    # 插入数据
    try:
        mongo_manager.collection.insert_many(documents_to_insert)
        print(f"✓ 成功导入 {len(documents_to_insert)} 个文档")
        return True
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        return False


# --- 检索控制器类 ---


class VTKSearcherV3:
    def __init__(self):
        """
        初始化 VTKSearcherV3。
        纯关键词检索 + 基于子查询权重的重排序。
        """
        self.raw_results_history = []
        self.reranked_results_history = []
        self.retrieval_time_history = []  # 新增：记录每次检索的时间
        print("VTKSearcherV3 initialized (Weighted Keyword Logic).")

    def search(self, query: str, query_list: List[Dict]) -> str:
        """
        执行检索并生成 Prompt。

        Args:
            query (str): 原始用户完整请求。
            query_list (List[Dict]): 分割后的子查询列表，需包含 'description' 和 'weight'。
                                     例如: [{'description': '画球', 'weight': 8}]
        """

        # 记录检索开始时间
        search_start_time = time.time()

        # --- 阶段 1: 广度召回 (Recall) ---
        # 目标：找出所有可能相关的候选文档，不论权重高低，只要沾边就捞出来
        all_candidate_docs = {}

        # 用于记录每个子查询分别召回了啥（为了兼容历史记录格式）
        temp_raw_history = []

        print(f"\n--- Processing Query with {len(query_list)} sub-queries ---")

        for q_item in query_list:
            # 兼容处理
            if isinstance(q_item, str):
                q_text = q_item
                q_item = {'description': q_text, 'weight': 5}
            else:
                q_text = q_item.get('description', '')

            analyzed = analyze_query(q_text)

            # 数据库查询
            docs = mongo_manager.find_docs_by_modules(
                analyzed.get('modules', []))

            # 记录 Raw History
            # 注意：这里我们给 doc 标记一下它是由哪个 query 召回的
            docs_copy = []
            for d in docs:
                # 浅拷贝避免修改原始字典影响后续逻辑
                d_copy = d.copy()
                d_copy['query_description'] = q_text
                docs_copy.append(d_copy)

                # 放入去重候选池 (使用原对象引用以节省内存，或者copy)
                # 使用唯一ID去重
                did = d.get("faiss_id")
                if did is None:
                    did = d.get("file_path") or d.get(
                        "meta_info", {}).get("file_path")

                if did and did not in all_candidate_docs:
                    all_candidate_docs[did] = d

            temp_raw_history.append(docs_copy)

        candidate_list = list(all_candidate_docs.values())
        print(f"Total unique candidates recalled: {len(candidate_list)}")

        # --- 阶段 2: 深度精排 (Rerank) ---
        # 目标：根据权重对候选文档进行打分排序

        # 初始化打分器
        ranker = WeightedRanker(candidate_list)

        # 传入带有权重的查询列表，开始考试打分
        ranker.calculate_scores(query_list)

        # 获取最终排好序的文档 (Top 6)
        final_results = ranker.get_ranked_results(top_k=6)

        # 填充 history 结构
        # 由于我们现在是整体排序，不再是针对每个 query 单独排序，
        # 为了兼容 raw_results_history 的结构（List[List]），
        # 我们这里将最终结果复制一份放入 rerank history，或者也可以按需调整结构。
        # 这里为了保持 VTKSearcherV1 的 Excel 导出逻辑，我们将最终结果作为"整体结果"存入。
        self.raw_results_history.append(temp_raw_history)
        self.reranked_results_history.append(
            final_results)  # 注意：这里结构稍有变化，变为 List[Doc]
        
        # 记录检索耗时
        search_duration = time.time() - search_start_time
        self.retrieval_time_history.append(search_duration)
        
        # --- 阶段 3: 构建 Prompt (Context) ---
        prompt = self._build_prompt(query, final_results)
        return prompt

    def _build_prompt(self, user_query, results):
        context_parts = []
        if results:
            for j, result in enumerate(results):
                meta = result.get("meta_info", {})
                code = result.get("code", "N/A")
                desc = meta.get("description", "N/A")
                mods = meta.get("vtkjs_modules", [])
                score = result.get("rerank_score", 0)
                matched_keys = result.get("matched_keywords", [])

                mods_str = ", ".join(mods) if isinstance(
                    mods, list) else str(mods)
                keys_str = ", ".join(matched_keys)

                context_parts.append(
                    f"Example {j+1} (Score: {score:.2f}, Matches: {keys_str}):\n"
                    f"Description: {desc}\n"
                    f"Modules: {mods_str}\n"
                    f"Code:\n{code}\n"
                )
        else:
            context_parts.append("No relevant VTK.js examples found.")

        context_str = "\n" + "-"*80 + "\n".join(context_parts)

        final_prompt = f"""
Generate only the HTML code without any additional text.
User Requirements:
{user_query}

Relevant VTK.js Examples:
{context_str}
"""
        return final_prompt

# --- Excel 处理逻辑 (保持兼容) ---


def process_splited_prompts_for_rag(input_file):
    """读取 Excel 中的 splited_prompt 列并解析 JSON"""
    try:
        df = pd.read_excel(input_file, sheet_name='第二期实验数据')
        splited_prompts_list = []

        for index, row in df.iterrows():
            splited_prompt_str = row.get('splited_prompt', '')
            try:
                # 尝试解析 JSON
                if pd.isna(splited_prompt_str) or splited_prompt_str == '':
                    splited_prompts_list.append([])
                    continue

                data = json.loads(splited_prompt_str)

                # 数据清洗：确保包含 description 和 weight
                valid_items = []
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'description' in item:
                            # 确保有 weight，如果没有默认给 5
                            if 'weight' not in item:
                                item['weight'] = 5
                            valid_items.append(item)
                        elif isinstance(item, str):
                            valid_items.append(
                                {'description': item, 'weight': 5})

                splited_prompts_list.append(valid_items)

            except Exception as e:
                print(f"Row {index} parse error: {e}")
                splited_prompts_list.append([])

        return splited_prompts_list
    except Exception as e:
        print(f"File read error: {e}")
        return []


def save_results_to_excel(searcher, input_file, output_file="retrieval_results_v3.xlsx"):
    """
    将检索结果保存到Excel文件中

    Args:
        searcher: VTKSearcherV3 实例，包含检索历史
        input_file: 原始输入Excel文件路径
        output_file: 输出Excel文件路径
    """
    try:
        # 读取原始Excel文件
        df = pd.read_excel(input_file, sheet_name='第二期实验数据')

        # 确保输出列存在
        if 'raw_results' not in df.columns:
            df['raw_results'] = ''
        if 'reranked_results' not in df.columns:
            df['reranked_results'] = ''
        if 'retrieval_time' not in df.columns:
            df['retrieval_time'] = ''

        # 填充结果数据
        for i, (raw_group, reranked_group) in enumerate(zip(searcher.raw_results_history, searcher.reranked_results_history)):
            if i >= len(df):
                break

            # 保存初筛结果
            try:
                # 将每个子查询的召回结果分别保存
                raw_data = []
                for j, raw_results in enumerate(raw_group):
                    for doc in raw_results:
                        # 移除代码和embedding等大字段以减小文件大小
                        doc_copy = doc.copy()
                        doc_copy.pop('code', None)
                        doc_copy.pop('embedding', None)
                        doc_copy.pop('query_description', None)
                        raw_data.append({
                            'sub_query_index': j,
                            'file_path': doc_copy.get('meta_info', {}).get('file_path', ''),
                            'faiss_id': doc_copy.get('faiss_id', ''),
                            'description': doc_copy.get('meta_info', {}).get('description', ''),
                            'vtkjs_modules': str(doc_copy.get('meta_info', {}).get('vtkjs_modules', []))
                        })

                df.at[i, 'raw_results'] = json.dumps(
                    raw_data, ensure_ascii=False, indent=2)
            except Exception as e:
                df.at[i,
                      'raw_results'] = f"Error serializing raw results: {str(e)}"

            # 保存重排序结果
            try:
                reranked_data = []
                for doc in reranked_group:
                    # 移除代码和embedding等大字段以减小文件大小
                    doc_copy = doc.copy()
                    doc_copy.pop('code', None)
                    doc_copy.pop('embedding', None)
                    reranked_data.append({
                        'file_path': doc_copy.get('meta_info', {}).get('file_path', ''),
                        'faiss_id': doc_copy.get('faiss_id', ''),
                        'description': doc_copy.get('meta_info', {}).get('description', ''),
                        'vtkjs_modules': str(doc_copy.get('meta_info', {}).get('vtkjs_modules', [])),
                        'rerank_score': doc_copy.get('rerank_score', 0),
                        'matched_keywords': str(doc_copy.get('matched_keywords', [])),
                        'match_explanation': str(doc_copy.get('match_explanation', []))
                    })

                df.at[i, 'reranked_results'] = json.dumps(
                    reranked_data, ensure_ascii=False, indent=2)
            except Exception as e:
                df.at[i,
                      'reranked_results'] = f"Error serializing reranked results: {str(e)}"

            # 保存检索时间
            retrieval_time = 0.0
            if i < len(searcher.retrieval_time_history):
                retrieval_time = searcher.retrieval_time_history[i]
            df.at[i, 'retrieval_time'] = retrieval_time

        # 保存到Excel文件
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='第二期实验数据', index=False)

        print(f"Results saved to {output_file}")
        return True

    except Exception as e:
        print(f"Error saving results to Excel: {e}")
        return False


def process_nested_queries_and_log(searcher, splited_queries, output_txt="output_weighted.txt"):
    """执行批量检索并记录日志"""

    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write("--- Starting Weighted Keyword Search ---\n")

        for group_idx, query_group in enumerate(splited_queries):
            if not query_group:
                continue

            # 构造完整的用户查询字符串（模拟）
            full_query_str = " ".join([q['description'] for q in query_group])

            f.write(f"\n=== Group {group_idx + 1} ===\n")
            f.write(f"User Query: {full_query_str}\n")

            start_time = time.time()

            # 调用新版 Searcher
            # 注意：searcher 会处理整个 group，进行统一召回和重排
            final_prompt = searcher.search(full_query_str, query_group)

            duration = time.time() - start_time

            # 获取刚刚存入 history 的结果
            last_results = searcher.reranked_results_history[-1]

            f.write(f"Time: {duration:.4f}s\n")
            f.write(f"Top Results ({len(last_results)}):\n")

            for res in last_results:
                f.write(
                    f"  - File: {res.get('meta_info', {}).get('file_path')}\n")
                f.write(f"    Score: {res.get('rerank_score', 0):.4f}\n")
                f.write(f"    Explanation: {res.get('match_explanation')}\n")
                f.write("-" * 40 + "\n")

            f.write("=" * 60 + "\n")

    print(f"Log saved to {output_txt}")

# --- 主程序入口 ---


def process_benchmark_prompts_for_generation(input_file, output_file=None, sheet_name='第二期实验数据'):
    """
    读取 Excel 中的 Benchmark prompt 字段，执行提示词拓展和检索，将结果写回 Excel
    
    Args:
        input_file (str): 输入 Excel 文件路径
        output_file (str): 输出 Excel 文件路径，如果为 None 则覆盖原文件
        sheet_name (str): Excel 工作表名称
    
    Returns:
        dict: 包含处理结果的字典
    """
    from llm_agent.prompt_agent import analyze_query
    from config.ollama_config import ollama_config
    
    if output_file is None:
        output_file = input_file
    
    try:
        # 读取 Excel 文件
        df = pd.read_excel(input_file, sheet_name=sheet_name)
        print(f"[Processing] 加载 {len(df)} 行数据")
        
        # 检查必要的列
        if 'Benchmark prompt' not in df.columns:
            print("[ERROR] Excel 文件缺少 'Benchmark prompt' 列")
            return {'success': False, 'error': 'Missing Benchmark prompt column'}
        
        # 初始化输出列
        if 'analysis_result' not in df.columns:
            df['analysis_result'] = ''
        if 'final_prompt' not in df.columns:
            df['final_prompt'] = ''
        if 'retrieval_time' not in df.columns:
            df['retrieval_time'] = 0.0
        if 'retrieval_results' not in df.columns:
            df['retrieval_results'] = ''
        
        # 初始化搜索器
        searcher = VTKSearcherV3()
        total_rows = len(df)
        processed_count = 0
        error_count = 0
        
        # 处理每一行
        for index, row in df.iterrows():
            try:
                benchmark_prompt = row.get('Benchmark prompt', '')
                
                if pd.isna(benchmark_prompt) or benchmark_prompt == '':
                    print(f"[Row {index+1}] 跳过：空的 Benchmark prompt")
                    continue
                
                print(f"\n[Row {index+1}/{total_rows}] 处理: {benchmark_prompt[:50]}...")
                
                # 第一步：提示词拓展
                start_time = time.time()
                try:
                    analysis = analyze_query(benchmark_prompt, model_name=ollama_config.inquiry_expansion_model, system=None)
                    # 确保 analysis 是列表格式
                    if not isinstance(analysis, list):
                        analysis = []
                except Exception as e:
                    print(f"[Row {index+1}] 分析失败: {e}")
                    analysis = []
                
                # 第二步：执行检索
                try:
                    # 如果分析结果为空，创建默认查询列表
                    if not analysis:
                        query_list = [{'description': benchmark_prompt, 'weight': 5}]
                    else:
                        # 将分析结果转换为检索兼容的格式
                        query_list = []
                        for item in analysis:
                            if isinstance(item, dict) and 'description' in item:
                                query_item = {
                                    'description': item.get('description', ''),
                                    'phase': item.get('phase', ''),
                                    'step_name': item.get('step_name', ''),
                                    'vtk_modules': item.get('vtk_modules', []),
                                    'weight': 5
                                }
                                query_list.append(query_item)
                    
                    # 执行检索
                    final_prompt = searcher.search(benchmark_prompt, query_list)
                    
                    # 提取检索结果元数据
                    retrieval_results = []
                    if hasattr(searcher, 'reranked_results_history') and searcher.reranked_results_history:
                        last_results = searcher.reranked_results_history[-1]
                        for idx, result in enumerate(last_results[:10]):
                            meta = result.get("meta_info", {})
                            retrieval_results.append({
                                "id": result.get("faiss_id") or result.get("file_path") or idx,
                                "title": meta.get("title") or meta.get("file_path", f"Example {idx+1}"),
                                "description": meta.get("description", "N/A")[:200],
                                "relevance": result.get("rerank_score", 0.0),
                                "matched_keywords": result.get("matched_keywords", [])
                            })
                    
                    retrieval_time = time.time() - start_time
                    
                    # 保存到 DataFrame
                    df.at[index, 'analysis_result'] = json.dumps(analysis, ensure_ascii=False, indent=2) if analysis else ''
                    df.at[index, 'final_prompt'] = final_prompt
                    df.at[index, 'retrieval_time'] = round(retrieval_time, 2)
                    df.at[index, 'retrieval_results'] = json.dumps(retrieval_results, ensure_ascii=False, indent=2)
                    
                    processed_count += 1
                    print(f"[Row {index+1}] 成功处理，耗时: {retrieval_time:.2f}s")
                    
                except Exception as e:
                    print(f"[Row {index+1}] 检索失败: {e}")
                    error_count += 1
                    df.at[index, 'retrieval_results'] = f"Error: {str(e)}"
                    
            except Exception as e:
                print(f"[Row {index+1}] 行处理失败: {e}")
                error_count += 1
        
        # 保存结果到 Excel
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        print(f"\n[Completed] 处理完成")
        print(f"  - 总行数: {total_rows}")
        print(f"  - 成功处理: {processed_count}")
        print(f"  - 失败: {error_count}")
        print(f"  - 输出文件: {output_file}")
        
        return {
            'success': True,
            'total_rows': total_rows,
            'processed': processed_count,
            'errors': error_count,
            'output_file': output_file
        }
        
    except Exception as e:
        print(f"[ERROR] 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


if __name__ == '__main__':
    # 1. 初始化数据库（如果为空）
    print("\n" + "="*60)
    print("VTK.js 检索系统 (V3)")
    print("="*60)
    
    # 检查数据库是否已初始化
    if mongo_manager.collection.count_documents({}) == 0:
        print("\n检测到数据库为空，正在初始化...")
        if not initialize_database():
            print("\n✗ 数据库初始化失败，无法继续")
            exit(1)
    
    # 2. 初始化搜索器
    print("\n初始化搜索器...")
    searcher = VTKSearcherV3()
    print("✓ 搜索器已准备就绪")

    # 3. 文件路径data\recoreds\res2_embedding4.xlsx
    excel_path = "D://Pcode//LLM4VIS//llmscivis//data//recoreds//res2_embedding4.xlsx"

    if os.path.exists(excel_path):
        # 3. 读取数据
        print("Reading Excel...")
        splited_queries = process_splited_prompts_for_rag(excel_path)
        print(f"Loaded {len(splited_queries)} query groups.")

        # 4. 执行批量检索
        print("Running Search...")
        process_nested_queries_and_log(searcher, splited_queries)

        # 5. 保存结果到Excel
        output_excel_path = "D:\\Pcode\\LLM4VIS\\llmscivis\\experiment_results\\retrieval_results_v3_output.xlsx"
        if save_results_to_excel(searcher, excel_path, output_excel_path):
            print("Results successfully saved to Excel.")
        else:
            print("Failed to save results to Excel.")

    else:
        print(f"File not found: {excel_path}")

        # 测试单条数据
        print("Running mock test...")
        mock_queries = [
            {'description': 'render a cone', 'weight': 10},
            {'description': 'set background to blue', 'weight': 3}
        ]
        prompt = searcher.search("render a blue cone", mock_queries)
        print("Prompt Generated Length:", len(prompt))
