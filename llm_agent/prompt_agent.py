from langchain_ollama import OllamaLLM
from config import app_config


'''
提示词分析，将用户input进行拓展，返回一个更详细的prompt
'''

async def analyze_query(query: str) -> dict:
    """分析用户查询"""
    model = OllamaLLM(
        base_url=app_config.ollama_url,
        model="llama3.2:1b"
    )
    
    analysis_prompt = f"""分析以下VTK.js相关查询，提供实现步骤：
    
查询：{query}

请提供：
1. 主要目标
2. 实现步骤
3. 可能需要的vtkjs接口
4. 注意事项
    """
    
    response = model.invoke(analysis_prompt)
    return {
        "main_goal": query,
        "steps": ["理解需求", "查找示例", "实现代码"],
        "key_apis": [],
        "notes": []
    } 