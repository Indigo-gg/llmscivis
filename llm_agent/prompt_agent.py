import json
import re
from llm_agent.ollma_chat import get_deepseek_response
from langchain_ollama import OllamaLLM
from config import app_config
from config import ollama_config

'''
提示词分析，将用户input进行拓展，返回一个更详细的prompt
'''


def analyze_query(query: str,model_name, system) -> dict:
    """分析用户查询"""

    system=f"""
    You are a question expansion assistant. You need to expand on the user's question based on vtkjs. Requirements: Provide
1. Main goal
2. Data source
3. VTK.js interfaces (separated by ",") 
    """
    analysis_prompt = f"""The query to be expanded:{query}"""
    # 从LLM回答提取检索参数 TODO：LLM回答具有不稳定性，如果没有按照格式回答怎么处理
    try:
        response = get_deepseek_response(analysis_prompt,model_name, system)
        print('prompt analysis',response)

        # 提取主要目标
        main_goal_match = re.search(r"Main goal?(.*)", response)
        main_goal = main_goal_match.group(1).strip() if main_goal_match else query

        # 提取数据来源
        data_source_match = re.search(r"Data source?(.*)", response)
        data_source = data_source_match.group(1).strip() if data_source_match else ""

        # 提取可能需要的vtkjs接口
        key_apis_match = re.search(r"VTK.js interfaces?(.*)", response) or \
                         re.search(r"vtkjs interfaces?(.*)", response) or \
                         re.search(r"vtkJs interfaces?(.*)", response)
        key_apis = key_apis_match.group(1).split(",") if key_apis_match else []

    except Exception as e:
        print(f"Error in analyze_query: {e}")
        return {
            "main_goal": query,
            "data_source": "",
            "key_apis": []
        }

    return {
        "main_goal": main_goal,
        "data_source": data_source,
        "key_apis": key_apis
    }


def merge_analysis(analysis: dict) -> str:
    return f"""
    用户需求分析：
    1. 主要目标：{analysis["main_goal"]}
    2.数据来源：{analysis['data_source']}
    3. 关键API：{', '.join(analysis["key_apis"]) if analysis["key_apis"] else '待确定'}
    
    """


if __name__ == "__main__":
    analyze_query('使用vtkjs生成锥形')
