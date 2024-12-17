import sys
import os
from RAG.retriever import VTKSearcher
from llm_agent.ollma_chat import get_llm_response

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

'''实现RAG，检索数据并生成回答'''


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
        print('最终的prompt\n', prompt)

        # 使用LLM生成回答
        response = await get_llm_response(prompt)
        return response


# 使用示例
if __name__ == "__main__":
    import asyncio


    async def test():
        agent = RAGAgent()
        query = "Create sphere via sphere source, render, and save rendered 512*512 image as IO-Screenshot.png.(Display it in the form of web page code with vtkJs)"
        # response = await agent.get_response(query) # 使用agent，拓展prompt，并生成回答
        response= await get_llm_response(query) # 不使用agent 直接调用大模型
        print('最终的response', response)
        # print(response)


    asyncio.run(test())
