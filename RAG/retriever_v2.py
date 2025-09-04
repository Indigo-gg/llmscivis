# 调用embedding_v3_1.py中的函数，进行检索，输入和输出与retiever.py一致

from typing import Dict, List, Optional
import sys
import os
import json
import pandas as pd
from RAG.embedding_v3_1 import index, load_faiss_index

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入embedding_v3_1.py中的函数
from RAG.embedding_v3_1 import search_code_optimized
from config.app_config import app_config

class VTKSearcherV2:
    def __init__(self):
        """
        初始化 VTKSearcherV2 类。
        与 VTKSearcher 类似，但使用 embedding_v3_1.py 中的检索逻辑。
        """
        # 这里不需要加载FAISS索引，因为embedding_v3_1.py已经处理了
        pass

    def search(self, query:str, query_list: List) -> str:
        """
        使用 embedding_v3_1.py 中的函数进行搜索，输入输出格式与 retriever.py 一致。
        """
        # 检查FAISS索引是否已加载
        if index.ntotal == 0:
            print("检测到FAISS索引未加载，正在尝试加载...")
            load_faiss_index("faiss_index.index")
            
        # 使用 embedding_v3_1.py 中的优化检索函数
        all_search_results = []
        for query_item in query_list:
            # 从每个查询项中提取描述文本
            query_text = query_item['description']
            # 调用 search_code_optimized 函数处理单个查询
            print(f"Processing query: {query_text}")
            single_query_results = search_code_optimized(query_text, k=4, similarity_threshold=0.1)
            all_search_results.extend(single_query_results)

        # ... 其余代码保持不变
            unique_results = {}
            for result in all_search_results:
                faiss_id = result.get("faiss_id")
                rerank_score = result.get("rerank_score", 0)
                
                if faiss_id not in unique_results or unique_results[faiss_id].get("rerank_score", 0) < rerank_score:
                    unique_results[faiss_id] = result

            # 使用去重后的结果
            search_results = list(unique_results.values())
            search_results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            # 构建上下文信息
            context_parts = []
            
            # 从检索结果中提取相关信息并格式化
            if all_search_results:
                for j, result in enumerate(all_search_results):
                    meta = result.get("meta_info", {})
                    code= result.get("code", "N/A")
                    description = meta.get("description", "N/A")
                    vtkjs_modules = meta.get("vtkjs_modules", "N/A")
                    # 构建单个结果的上下文信息
                    result_context = f"示例 {j+1}:\n"
                    result_context += f"描述: {description}\n"
                    result_context += f"VTK.js 模块: {vtkjs_modules}\n"
                    result_context += f"代码:\n{code}\n"
                    context_parts.append(result_context)
            else:
                context_parts.append("未找到相关示例")
                
            # 组合上下文片段
            if not context_parts:
                context = "No relevant VTK examples found matching the criteria."
            else:
                context = "\n--------------------------------------------------------------------------------------------------------------\n".join(context_parts)
            
            # 构建最终的提示，整合分析结果、上下文和用户问题
            final_prompt =  f"""
    Generate only the HTML code without any additional text or markdown formatting.
    User Requirements:
    {query}

    Relevant VTK.js Examples:
    {context}
            """
            
            return final_prompt


def read_benchmark_prompts(input_file="res2.xlsx"):
    """
    读取Excel文件中的Benchmark prompt列，返回所有prompt的列表
    
    Args:
        input_file: 输入Excel文件路径
        
    Returns:
        list: 包含所有Benchmark prompt的列表
    """
    try:
        # 读取Excel文件
        df = pd.read_excel(input_file, sheet_name='第二期实验数据')
        
        # 检查是否存在Benchmark prompt列
        if 'Benchmark prompt' not in df.columns:
            raise ValueError("Excel文件中必须包含'Benchmark prompt'列")
        
        benchmark_prompts_list = []
        
        # 处理每个Benchmark prompt
        for index, row in df.iterrows():
            benchmark_prompt = row['Benchmark prompt']
            
            if pd.isna(benchmark_prompt) or benchmark_prompt == '':
                print(f"跳过第{index+1}行：空的Benchmark prompt")
                benchmark_prompts_list.append("")  # 添加空字符串
                continue
                
            benchmark_prompts_list.append(benchmark_prompt)
        
        return benchmark_prompts_list
        
    except Exception as e:
        print(f"读取Benchmark prompt时出错: {e}")
        return []
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


def process_splited_prompts_for_excel(input_file="res2.xlsx"):
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


def get_data_from_excel(input_file="res2.xlsx"):
    """
    读取Excel文件中的Benchmark prompt和splited_prompt列，返回两个列表
    """
    benchmark_prompts = read_benchmark_prompts(input_file)
    splited_prompts = process_splited_prompts_for_excel(input_file)
    
    return benchmark_prompts, splited_prompts

if __name__ == "__main__":
    # 导入必要的模块
    
    
    # 初始化搜索器
    searcher = VTKSearcherV2()
    
    # 文件路径
    excel_path = "D://Pcode//LLM4VIS//llmscivis//data//recoreds//res2.xlsx"
    benchmark_prompts,splited_queries,=get_data_from_excel(excel_path)

    # 创建结果文件
    output_file = "retrieval_results.json"
    
    # 准备存储所有结果的列表
    all_results = []
    
    for i, query_list in enumerate(splited_queries):
        if not query_list:
            print(f"跳过第{i+1}行：空的或无效的splited_prompt")
            all_results.append({
                "index": i+1,
                "status": "skipped",
                "reason": "空的或无效的splited_prompt"
            })
            continue
        
        # 获取对应的原始查询
        original_query = benchmark_prompts[i] if i < len(benchmark_prompts) else "N/A"
        print(f"\n处理第{i+1}行，原始查询: {original_query}")
        
        # 进行搜索
        final_prompt = searcher.search(original_query, query_list)
        
        # 输出结果到控制台
        print(f"最终提示:\n{final_prompt}\n")
        
        # 保存结果到列表
        result_entry = {
            "index": i+1,
            "original_query": original_query,
            "splited_queries": query_list,
            "final_prompt": final_prompt,
            "status": "success"
        }
        all_results.append(result_entry)
    
    # 将结果写入JSON文件
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n所有结果已保存到 {output_file} 文件中")
    except Exception as e:
        print(f"保存结果到JSON文件时出错: {e}")
   