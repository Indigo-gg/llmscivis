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
        self.searcher = VTKSearcher()

    def search(self, analysis: dict, prompt: str, metadata_filters: dict = None) -> str:
        """
        检索数据，支持元数据过滤。
        :param analysis: 查询分析结果
        :param prompt: 原始用户查询
        :param metadata_filters: 用于过滤的元数据字典 (可选)
        :return: 结合了上下文信息的最终提示
        """
        return self.searcher.search(analysis, prompt, metadata_filters=metadata_filters)
# 使用示例
def main():
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
        
        # 记录开始时间
        start_time = time.time()
        
        # 进行搜索
        final_prompt = searcher.search(original_query, query_list)
        
        # 记录检索时间
        retrieval_time = time.time() - start_time
        print(f"检索耗时: {retrieval_time:.2f}秒")
        
        # 使用LLM生成代码
        generated_code = ""
        llm_start_time = time.time()
        try:
            generated_code = get_llm_response(final_prompt, model_name="qwen3-plus",system=ollama_config.code_sytstem)
            print(f"代码生成成功")
        except Exception as e:
            print(f"代码生成失败: {e}")
            generated_code = f"代码生成失败: {e}"
        
        # 记录LLM生成时间
        llm_time = time.time() - llm_start_time
        total_time = time.time() - start_time
        
        # 输出结果到控制台
        print(f"最终提示:\n{final_prompt}\n")
        print(f"生成的代码:\n{generated_code}\n")
        print(f"LLM生成耗时: {llm_time:.2f}秒")
        print(f"总耗时: {total_time:.2f}秒")
        
        # 保存结果到列表
        result_entry = {
            "index": i+1,
            "original_query": original_query,
            "splited_queries": query_list,
            "final_prompt": final_prompt,
            "generated_code": generated_code,
            "retrieval_time": round(retrieval_time, 2),
            "llm_generation_time": round(llm_time, 2),
            "total_time": round(total_time, 2),
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

def json_to_excel(json_file_path, excel_file_path):
    """
    读取JSON文件并将结果保存到Excel文件
    
    Args:
        json_file_path: JSON文件路径
        excel_file_path: 输出Excel文件路径
    """
    # 读取JSON文件
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"成功读取JSON文件: {json_file_path}")
    except Exception as e:
        print(f"读取JSON文件时出错: {e}")
        return
    
    # 转换数据为DataFrame
    try:
        df = pd.DataFrame(data)
        print("数据转换为DataFrame成功")
    except Exception as e:
        print(f"数据转换时出错: {e}")
        return
    
    # 保存到Excel文件
    try:
        with pd.ExcelWriter(excel_file_path, engine='openpyxl', mode='w') as writer:
            df.to_excel(writer, sheet_name='第二期实验结果备份', index=False)
        print(f"处理完成，结果已保存到 {excel_file_path}")
    except Exception as e:
        print(f"保存文件时出错: {e}")
        # 尝试另存为新文件
        backup_file = excel_file_path.replace('.xlsx', '_backup.xlsx')
        try:
            with pd.ExcelWriter(backup_file, engine='openpyxl', mode='w') as writer:
                df.to_excel(writer, sheet_name='检索结果', index=False)
            print(f"已保存到备份文件: {backup_file}")
        except Exception as backup_e:
            print(f"保存备份文件时也出错: {backup_e}")
            # 最后尝试直接保存为CSV作为备用方案
            csv_file = excel_file_path.replace('.xlsx', '_result.csv')
            try:
                df.to_csv(csv_file, index=False, encoding='utf-8-sig')
                print(f"已保存为CSV文件: {csv_file}")
            except Exception as csv_e:
                print(f"保存CSV文件也失败: {csv_e}")
  

if __name__ == "__main__":
    # main()
    #尝试读取excel文件，并把json结果写入excel文件中
    json_file_path = "D:\\Pcode\\LLM4VIS\\llmscivis\\retrieval_results.json"
    excel_file_path = "D:\\Pcode\\LLM4VIS\\llmscivis\\data\\recoreds\\res2.xlsx"
    json_to_excel(json_file_path, excel_file_path)
    
    
    
   