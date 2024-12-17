from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from llm_agent.prompt_agent import analyze_query
from config.ollama_config import embedding_modals
from config.ollama_config import faissDB_path
import os

'''
检索器，用于在vectorDB中检索prompt相关的知识
'''


class VTKSearcher:
    def __init__(self):
        # 设置fassi数据库的路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.cache_dir = os.path.join(current_dir, "..", faissDB_path)

        # 初始化embedding模型
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_modals[0],
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': False}
        )

        # 加载向量数据库
        self.db = FAISS.load_local(
            self.cache_dir,
            self.embeddings,
            allow_dangerous_deserialization=True
        )

    def search(self, query: str, k: int = 3) -> str:
        """搜索相关的VTK示例"""
        # 首先分析查询，分析方法在prompt_analyze中
        analysis = analyze_query(query)

        print('返回分析结果',analysis)
        # 对查询和函数API进行相关性搜索
        all_docs = []
        search_terms = [analysis["main_goal"]]  + analysis["key_apis"]

        for term in search_terms:
            docs = self.db.similarity_search(term, k=1)  # 每个方面找一个最相关的
            all_docs.extend(docs)

        # 去重
        seen = set()
        unique_docs = []
        for doc in all_docs:
            if doc.metadata["source"] not in seen:
                seen.add(doc.metadata["source"])
                unique_docs.append(doc)

        # 构建上下文信息
        context_parts = []
        for doc in unique_docs[:k]:  # 限制最终使用的示例数量
            metadata = doc.metadata
            example_name = metadata["example_name"]
            file_type = metadata["file_type"]

            if file_type == "description":
                context_parts.append(f"示例 '{example_name}' 的描述:\n{doc.page_content}\n")
            else:  # code
                context_parts.append(f"示例 '{example_name}' 的代码:\n{doc.page_content}\n")

        context = "\n".join(context_parts)
        # 构建完整的prompt
        prompt = f"""你是一个VTK.js专家，精通科学可视化和VTK.js编程。

用户需求分析：
1. 主要目标：{analysis["main_goal"]}
2.数据来源：{analysis['data_source']}
3. 关键API：{', '.join(analysis["key_apis"]) if analysis["key_apis"] else '待确定'}
请遵循以下规则：
1. 回答的内容是带有vtkjs脚本的html代码，如有说明以注释形式给出
2. 如果示例代码与用户需求相关，基于示例代码实现用户的需求
3. 回答要基于提供的示例信息，不要编造不存在的功能

相关的VTK.js示例信息如下：

{context}

用户问题: {query}

请根据上述分析和示例信息，提供详细的解答。在注释中重点说明如何实现用户的具体需求。
"""
        return prompt


# 使用示例
if __name__ == "__main__":
    searcher = VTKSearcher()
    query = "使用vtkJs实现Filter-ImageMarchingSquares"
    prompt = searcher.search(query)
    print(prompt)
