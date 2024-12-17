import json
import re
from langchain_ollama import OllamaLLM
from config import app_config
from config import ollama_config

'''
提示词分析，将用户input进行拓展，返回一个更详细的prompt
'''


def analyze_query(query: str) -> dict:
    """分析用户查询"""
    model = OllamaLLM(
        base_url=app_config.ollama_url,
        model=ollama_config.modals[0]
    )

    analysis_prompt = f"""分析以下VTK.js相关查询，提供实现步骤：
    
查询：{query}

请提供：
1. 主要目标
2. 数据来源（文件或 Source）及格式
3. 可能需要的vtkjs接口
    """
    # 从LLM回答提取检索参数 TODO：LLM回答具有不稳定性，如果没有按照格式回答怎么处理
    response = model.invoke(analysis_prompt)
    main_goal_match = re.search(r"主要目标：(.*)", response)
    main_goal = main_goal_match.group(1).strip() if main_goal_match else query
    data_source_match = re.search(r"数据来源：(.*)", response)
    data_source = data_source_match.group(1).strip() if data_source_match else ""
    key_apis_match = re.search(r"可能需要的vtkjs接口：(.*)", response)
    key_apis = key_apis_match.group(1).split("、")
    # TODO:增加思维链的提示
    return {
        "main_goal": main_goal,
        "data_source": data_source,
        "key_apis": key_apis
    }


if __name__ == "__main__":
    analyze_query('使用vtkjs生成锥形')
