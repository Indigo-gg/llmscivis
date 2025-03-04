import sys
import os
from RAG.retriever import VTKSearcher
from llm_agent.ollma_chat import get_deepseek_response,get_deepseek_response_stream

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

'''实现RAG，检索数据并生成回答'''


class RAGAgent:
    def __init__(self):
        self.searcher = VTKSearcher()

    def search(self, analysis,prompt) -> str:
        """
        检索数据
        :param prompt:
        :param analysis:
        :return:
        """
        return self.searcher.search(analysis,prompt)
# 使用示例


if __name__ == "__main__":
    pass