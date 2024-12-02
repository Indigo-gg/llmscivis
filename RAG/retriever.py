from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
import os

class VTKSearcher:
    def __init__(self):
        # 获取当前脚本的绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建缓存目录的路径
        self.cache_dir = os.path.join(current_dir, "..", "data", "faiss_cache")
        
        # 初始化embedding模型
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': False}
        )
        
        # 加载向量数据库
        self.db = FAISS.load_local(
            self.cache_dir, 
            self.embeddings,
            allow_dangerous_deserialization=True
        )

    def _analyze_query(self, query: str) -> dict:
        """分析用户查询，将其分解为具体需求"""
        analysis_prompt = PromptTemplate.from_template("""
作为VTK.js专家，请分析以下用户查询，将其分解为具体的实现步骤和关键点：

用户查询: {query}

请按以下格式输出分析结果：
1. 主要目标：(用一句话描述用户想要实现什么)
2. 实现步骤：(列出实现这个功能需要的具体步骤)
3. 关键API：(可能需要用到的VTK.js API)
4. 注意事项：(实现过程中需要注意的点)

分析结果：
""")
        
        # 这里可以调用LLM进行分析，暂时用简单的字符串处理
        return {
            "main_goal": query,
            "steps": ["理解用户需求", "查找相关示例", "整合代码"],
            "key_apis": [],
            "notes": []
        }

    def search(self, query: str, k: int = 3) -> str:
        """搜索相关的VTK示例"""
        # 首先分析查询
        analysis = self._analyze_query(query)
        
        # 对每个步骤和API进行相关性搜索
        all_docs = []
        search_terms = [analysis["main_goal"]] + analysis["steps"] + analysis["key_apis"]
        
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
2. 实现步骤：
{chr(10).join(f"   - {step}" for step in analysis["steps"])}
3. 关键API：{', '.join(analysis["key_apis"]) if analysis["key_apis"] else '待确定'}
4. 注意事项：{', '.join(analysis["notes"]) if analysis["notes"] else '待补充'}

请遵循以下规则：
1. 使用中文回答问题
2. 如果示例代码与用户需求相关，基于示例代码实现用户的需求
3. 如果需要修改代码，请给出完整的修改建议
4. 回答要基于提供的示例信息，不要编造不存在的功能

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