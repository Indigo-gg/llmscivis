import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from RAG.retriever import VTKSearcher
from llm_agent.ollma_chat import get_llm_response

class RAGAgent:
    def __init__(self):
        self.searcher = VTKSearcher()
    
    async def get_response(self, query: str) -> str:
        """
        获取RAG增强的回答
        :param query: 用户问题
        :return: LLM的回答
        """
        # 获取相关上下文和生成prompt
        prompt = self.searcher.search(query)
        
        # 使用LLM生成回答
        response = await get_llm_response(prompt)
        return response

# 使用示例
if __name__ == "__main__":
    import asyncio
    
    async def test():
        agent = RAGAgent()
        query = "使用vtkJs实现Filter-ImageMarchingSquares"
        response = await agent.get_response(query)
        print(response)
    
    asyncio.run(test())
