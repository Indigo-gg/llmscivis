import sys
import os
from RAG.retriever import VTKSearcher
from llm_agent.ollma_chat import get_qwen_response,get_llm_response
from RAG.retriever_v2 import get_data_from_excel
import json
# from RAG.retriever_v2 import VTKSearcherV2
# 引入 retriever_v3 的搜索器
from RAG.retriever_v3 import VTKSearcherV3
from config.ollama_config import ollama_config 
import json
from llm_agent.ollma_chat import get_llm_response
import time
import pandas as pd
from openpyxl import load_workbook
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

'''实现RAG，检索数据并生成回答'''


class RAGAgent:
    def __init__(self, use_v3=True):
        """
        初始化 RAG Agent
        :param use_v3: 是否使用 retriever_v3（纯关键词检索），默认为 True
        """
        self.use_v3 = use_v3
        if use_v3:
            self.searcher = VTKSearcherV3()
            print("[RAGAgent] 使用 VTKSearcherV3 (关键词检索)")
        self.last_retrieval_results = []

    def search(self, analysis: list, prompt: str) -> str:
        """
        检索数据,支持元数据过滤。
        :param analysis: 查询分析结果，格式为 list[dict]，每个 dict 包含: phase, step_name, vtk_modules, description
        :param prompt: 原始用户查询
        :return: 结合了上下文信息的最终提示
        """
        # 如果 analysis 为空或为 None，使用原始 prompt 创建默认的查询列表
        if not analysis:
            query_list = [{'description': prompt, 'weight': 5}]
        else:
            # 将新格式的分析结果转换为检索兼容的格式
            # 从每个分析步骤中提取 description，并添加权重
            query_list = []
            for item in analysis:
                if isinstance(item, dict) and 'description' in item:
                    # 保留所有原始字段，但重点使用 description 进行检索
                    query_item = {
                        'description': item.get('description', ''),
                        'phase': item.get('phase', ''),
                        'step_name': item.get('step_name', ''),
                        'vtk_modules': item.get('vtk_modules', []),
                        'weight': 5  # 默认权重
                    }
                    query_list.append(query_item)
        
        print(f'[RAGAgent] 转换后的查询列表：{query_list}')
        
        # 执行检索
        result = self.searcher.search(prompt, query_list)
        
        # 根据不同的检索器提取元数据
        if self.use_v3:
            # retriever_v3 没有 last_retrieval_metadata 属性，需要从 reranked_results_history 中提取
            self._extract_metadata_from_v3()
        else:
            # retriever_v2 有 last_retrieval_metadata 属性
            self.last_retrieval_results = getattr(self.searcher, 'last_retrieval_metadata', [])
        
        return result
    
    def _get_thumbnail_url(self, file_path: str) -> str:
        """
        根据文件路径生成缩略图 URL
        临时使用测试图片路径
        """
        # 临时测试：使用固定的测试图片
        test_image_path = "vtkjs-examples/benchmark/data/dataset/test.png"
        return f"/get_image/{test_image_path}"
    
    def _extract_metadata_from_v3(self):
        """
        从 retriever_v3 的检索结果中提取元数据用于前端展示
        """
        self.last_retrieval_results = []
        
        # 从最后一次检索的 reranked_results_history 中提取
        if hasattr(self.searcher, 'reranked_results_history') and self.searcher.reranked_results_history:
            last_results = self.searcher.reranked_results_history[-1]
            
            # 提取所有分数用于归一化
            all_scores = [r.get("rerank_score", 0.0) for r in last_results]
            
            if not all_scores:
                print(f"[RAGAgent] 无有效分数")
                return
            
            # 使用最小-最大归一化方法：normalized = (score - min) / (max - min)
            # 这样最低分变为0%，最高分变为100%，中间分数线性分布
            max_score = max(all_scores)
            min_score = min(all_scores)
            score_range = max_score - min_score if max_score > min_score else 1.0
            
            for idx, result in enumerate(last_results[:10]):  # Top 10 results
                meta = result.get("meta_info", {})
                raw_score = result.get("rerank_score", 0.0)
                
                # 使用最小-最大归一化
                if score_range > 0:
                    normalized_relevance = (raw_score - min_score) / score_range
                else:
                    normalized_relevance = 1.0 if raw_score > 0 else 0.0
                
                # 确保在0-1范围内
                normalized_relevance = min(max(normalized_relevance, 0.0), 1.0)
                
                self.last_retrieval_results.append({
                    "id": result.get("faiss_id") or result.get("file_path") or idx,
                    "title": meta.get("file_name") or meta.get("file_path", f"Example {idx+1}"),
                    "description": meta.get("description", "N/A")[:200],
                    "relevance": normalized_relevance,
                    "raw_score": raw_score,  # 保留原始分数供调试
                    "vtkjs_modules": meta.get("vtkjs_modules", []),  # 添加模块信息
                    "matched_keywords": result.get("matched_keywords", []),
                    "file_path": meta.get("file_path", ""),  # 添加文件路径供参考
                    "thumbnail_url": self._get_thumbnail_url(meta.get("file_path", ""))
                })


    
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
        searcher (VTKSearcherV3): 搜索器实例。
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
    searcher = VTKSearcherV3()
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
    # json_to_excel(output_file, excel_output_path)![1766231455900](image/rag_agent/1766231455900.png)![1766231456154](image/rag_agent/1766231456154.png)![1766231456389](image/rag_agent/1766231456389.png)![1766231456544](image/rag_agent/1766231456544.png)![1766231456723](image/rag_agent/1766231456723.png)![1766231457570](image/rag_agent/1766231457570.png)![1766231458075](image/rag_agent/1766231458075.png)![1766231458928](image/rag_agent/1766231458928.png)![1766231460243](image/rag_agent/1766231460243.png)![1766231460643](image/rag_agent/1766231460643.png)![1766231461220](image/rag_agent/1766231461220.png)![1766231461623](image/rag_agent/1766231461623.png)![1766231461956](image/rag_agent/1766231461956.png)![1766231467051](image/rag_agent/1766231467051.png)![1766231467408](image/rag_agent/1766231467408.png)![1766231467641](image/rag_agent/1766231467641.png)![1766231467821](image/rag_agent/1766231467821.png)![1766231474831](image/rag_agent/1766231474831.png)![1766231475139](image/rag_agent/1766231475139.png)![1766231475361](image/rag_agent/1766231475361.png)![1766231475541](image/rag_agent/1766231475541.png)![1766231475697](image/rag_agent/1766231475697.png)![1766231475871](image/rag_agent/1766231475871.png)