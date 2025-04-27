import sys
import os
from RAG.retriever import VTKSearcher
from llm_agent.ollma_chat import get_deepseek_response,get_deepseek_response_stream

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


if __name__ == "__main__":
    pass