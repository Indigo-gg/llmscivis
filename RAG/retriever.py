# 导入所需的库
from langchain_community.vectorstores import FAISS  # FAISS 向量存储库
from langchain_huggingface import HuggingFaceEmbeddings # Hugging Face 嵌入模型接口
import sys # 系统相关功能库
import os # 操作系统相关功能库

from llm_agent.prompt_agent import analyze_query, merge_analysis # 从其他模块导入查询分析和合并函数
from config.ollama_config import embedding_models # 从配置文件导入嵌入模型名称
from config.ollama_config import faissDB_path # 从配置文件导入 FAISS 数据库路径

'''
检索器，用于在vectorDB中检索prompt相关的知识
'''


class VTKSearcher:
    def __init__(self):
        """
        初始化 VTKSearcher 类。
        - 设置 FAISS 数据库路径。
        - 初始化嵌入模型。
        - 加载本地 FAISS 向量数据库。
        """
        # 设置fassi数据库的路径
        current_dir = os.path.dirname(os.path.abspath(__file__)) # 获取当前文件所在目录
        # 构建 FAISS 数据库的完整路径 (上一级目录 + 配置中的相对路径)
        self.cache_dir = os.path.join(current_dir, "..", faissDB_path)

        # 初始化embedding模型
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_models["bge"], # 使用配置文件中指定的 "bge" 模型
            model_kwargs={'device': 'cpu'}, # 指定模型在 CPU 上运行
            encode_kwargs={'normalize_embeddings': False} # 指定不对嵌入向量进行归一化
        )

        # 加载向量数据库
        self.db = FAISS.load_local(
            self.cache_dir, # 数据库路径
            self.embeddings, # 使用的嵌入模型
            allow_dangerous_deserialization=True # 允许加载 pickle 序列化的索引 (注意安全风险)
        )

    def search(self, analysis: dict, query: str, metadata_filters: dict = None) -> str:
        """
        搜索相关的VTK示例，支持元数据过滤（后过滤）。

        :param analysis: 查询分析结果 (字典)，包含 'main_goal', 'key_apis' 等键。
        :param query: 原始用户查询字符串。
        :param metadata_filters: 可选的元数据过滤字典，例如 {'file_type': 'code', 'language': 'python'}。
                                 如果为 None，则不进行元数据过滤。
        :return: 结合了上下文信息的最终提示字符串，用于 LLM 生成回答。
        """
        k = 5  # 最终希望返回的相关文档数量
        fetch_k = k * 3 # 初始检索时获取更多文档，以便后续过滤

        # 对查询的主要目标和关键 API 进行相关性搜索
        all_docs = [] # 用于存储所有检索到的文档
        # 结合主要目标和关键 API 作为搜索词
        search_terms = [analysis["main_goal"]] + analysis["key_apis"]

        # 遍历搜索词，执行相似度搜索
        for term in search_terms:
            # 获取更多的初始结果 (fetch_k)
            docs = self.db.similarity_search(term, k=fetch_k)
            all_docs.extend(docs) # 将结果添加到 all_docs 列表

        # 去重：移除内容和来源都相同的重复文档
        seen = set() # 用于存储已经见过的文档标识符
        unique_docs_semantic = [] # 存储去重后的文档
        for doc in all_docs:
            # 使用 page_content 和 source 元数据作为唯一标识符
            # 确保元数据中存在 "source" 键，如果不存在则可能需要处理 KeyError
            if "source" in doc.metadata:
                 doc_identifier = (doc.page_content, doc.metadata["source"])
                 if doc_identifier not in seen:
                    seen.add(doc_identifier)
                    unique_docs_semantic.append(doc)
            else:
                 # 处理缺少 source 元数据的情况，例如只用 page_content 去重或跳过
                 doc_identifier = doc.page_content
                 if doc_identifier not in seen:
                     seen.add(doc_identifier)
                     unique_docs_semantic.append(doc)


        # 应用元数据后过滤 (Post-filtering)
        filtered_docs = [] # 存储过滤后的文档
        if metadata_filters: # 检查是否提供了过滤器
            for doc in unique_docs_semantic: # 遍历去重后的语义搜索结果
                match = True # 假设当前文档匹配过滤器
                for key, value in metadata_filters.items(): # 遍历过滤器中的每个条件
                    # 检查文档元数据中是否存在该键，并且值是否匹配 (忽略大小写)
                    if key not in doc.metadata or str(doc.metadata[key]).lower() != str(value).lower():
                        match = False # 如果任何一个条件不匹配，则标记为不匹配
                        break # 无需检查其他条件，跳出内层循环
                if match: # 如果所有条件都匹配
                    filtered_docs.append(doc) # 将文档添加到过滤结果列表
        else:
            # 如果没有提供过滤器，则使用所有去重后的语义搜索结果
            filtered_docs = unique_docs_semantic

        # 构建上下文信息
        context_parts = [] # 用于存储格式化后的上下文片段
        # 从过滤后的结果中选择前 k 个文档
        for doc in filtered_docs[:k]:
            metadata = doc.metadata # 获取文档的元数据
            # 获取示例名称和文件类型，提供默认值以防元数据缺失
            example_name = metadata.get("example_name", "Unknown Example")
            file_type = metadata.get("file_type", "unknown")

            # 根据文件类型格式化上下文片段
            if file_type == "description":
                context_parts.append(f"示例 '{example_name}' 的描述:\n{doc.page_content}\n")
            else:  # code 或其他类型
                context_parts.append(f"示例 '{example_name}' ({file_type}):\n{doc.page_content}\n")

        # 组合上下文片段
        if not context_parts: # 如果没有找到相关文档
             context = "No relevant VTK examples found matching the criteria."
        else:
            context = "\n".join(context_parts) # 将所有片段用换行符连接起来

        # 构建最终的提示，整合分析结果、上下文和用户问题
        final_prompt = merge_analysis(analysis) + f"""
        The relevant VTK.js example information is as follows: {context}
        User question: {query}
        Please provide a detailed answer based on the above analysis and example information. Highlight how to meet the user's specific needs in the comments.
        """
        return final_prompt # 返回构建好的最终提示


# 使用示例 (通常用于测试或独立运行脚本)
if __name__ == "__main__":
    searcher = VTKSearcher()
    test_analysis = {"main_goal": "render a sphere", "key_apis": ["vtkSphereSource", "vtkPolyDataMapper", "vtkActor", "vtkRenderer", "vtkRenderWindow"]}
    test_query = "How to render a simple sphere using VTK?"
    result_prompt = searcher.search(test_analysis, test_query)
    print(result_prompt)
