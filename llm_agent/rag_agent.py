import sys
import os
from RAG.retriever import VTKSearcher
from llm_agent.ollma_chat import get_qwen_response,get_llm_response
from RAG.retriever_v2 import get_data_from_excel
import json
from RAG.retriever_v2 import VTKSearcherV2
from config.ollama_config import ollama_config 
import json
from llm_agent.ollma_chat import get_llm_response
import time
import pandas as pd
from openpyxl import load_workbook
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

'''实现RAG，检索数据并生成回答'''


class RAGAgent:
    def __init__(self):
        self.searcher = VTKSearcherV2()
        self.last_retrieval_results = []

    def search(self, analysis: list, prompt: str) -> str:
        """
        检索数据,支持元数据过滤。
        :param analysis: 查询分析结果
        :param prompt: 原始用户查询
        :return: 结合了上下文信息的最终提示
        """
        result = self.searcher.search(prompt,analysis)
        # Capture retrieval metadata from searcher
        self.last_retrieval_results = self.searcher.last_retrieval_metadata
        return result
    
    def get_retrieval_metadata(self) -> list:
        """
        获取最近一次检索的元数据用于前端展示
        :return: 检索结果列表，包含title, description, relevance等字段
        """
        return self.last_retrieval_results

def retrieval_step(searcher, excel_path):
    """
    负责从Excel读取查询并执行检索过程，将检索结果保存到列表中。

    Args:
        searcher (VTKSearcherV2): 搜索器实例。
        excel_path (str): 包含查询的Excel文件路径。

    Returns:
        list: 包含每个查询检索结果的字典列表。
    """
    benchmark_prompts, splited_queries = get_data_from_excel(excel_path)
    all_retrieval_results = []

    for i, query_list in enumerate(splited_queries):
        original_query = benchmark_prompts[i] if i < len(benchmark_prompts) else "N/A"
        
        # 准备检索结果的初始字典
        result_entry = {
            "index": i + 1,
            "original_query": original_query,
            "splited_queries": query_list,
            "final_prompt": "",
            "retrieval_time": 0.0,
            "status": "success"
        }

        if not query_list:
            print(f"跳过第{i+1}行：空的或无效的splited_prompt")
            result_entry.update({"status": "skipped", "reason": "空的或无效的splited_prompt"})
            all_retrieval_results.append(result_entry)
            continue

        print(f"\n处理第{i+1}行，原始查询: {original_query}")
        
        start_time = time.time()
        final_prompt = searcher.search(original_query, query_list)
        retrieval_time = time.time() - start_time
        
        print(f"检索耗时: {retrieval_time:.2f}秒")
        
        result_entry.update({
            "final_prompt": final_prompt,
            "retrieval_time": round(retrieval_time, 2)
        })
        all_retrieval_results.append(result_entry)

    return all_retrieval_results

def generation_step(retrieval_results, output_file="generation_results.json"):
    """
    负责利用检索结果调用LLM生成代码，并将最终结果保存到JSON文件。

    Args:
        retrieval_results (list): 包含检索结果的字典列表。
        output_file (str): 保存最终结果的JSON文件路径。
    """
    for result_entry in retrieval_results:
        # 跳过已标记为“跳过”的结果
        if result_entry.get("status") == "skipped":
            continue
        
        final_prompt = result_entry["final_prompt"]
        generated_code = ""
        llm_start_time = time.time()

        print(f"\n为第{result_entry['index']}行生成代码...")
        
        try:
            generated_code = get_llm_response(final_prompt, model_name="qwen3-plus", system=ollama_config.code_sytstem)
            print(f"代码生成成功")
        except Exception as e:
            print(f"代码生成失败: {e}")
            generated_code = f"代码生成失败: {e}"
            result_entry["status"] = "failed"
        
        llm_time = time.time() - llm_start_time
        total_time = result_entry["retrieval_time"] + llm_time
        
        # 更新字典，添加生成结果
        result_entry.update({
            "generated_code": generated_code,
            "llm_generation_time": round(llm_time, 2),
            "total_time": round(total_time, 2)
        })

        print(f"最终提示:\n{final_prompt}\n")
        print(f"生成的代码:\n{generated_code}\n")
        print(f"LLM生成耗时: {llm_time:.2f}秒")
        print(f"总耗时: {total_time:.2f}秒")

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(retrieval_results, f, ensure_ascii=False, indent=2)
        print(f"\n所有结果已保存到 {output_file} 文件中")
    except Exception as e:
        print(f"保存结果到JSON文件时出错: {e}")

# ----------------------------------------------------------------------------

def main():
    """
    主函数，调用拆分后的检索和生成步骤。
    """
    # 初始化搜索器
    searcher = VTKSearcherV2()
    excel_path = "D://Pcode//LLM4VIS//llmscivis//data//recoreds//res2.xlsx"
    output_file = "retrieval_results.json"
    
    # 步骤1：执行检索
    all_retrieval_results = retrieval_step(searcher, excel_path)
    
    # 步骤2：执行生成
    generation_step(all_retrieval_results, output_file)

if __name__ == "__main__":
    main()
    
    # 以下代码用于将JSON结果转换为Excel，可以根据需要独立运行
    # excel_output_path = "D://Pcode//LLM4VIS//llmscivis//data//recoreds//experiment_results.xlsx"
    # json_to_excel(output_file, excel_output_path)