import json
import re
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_agent.ollma_chat import get_deepseek_response
from langchain_ollama import OllamaLLM
from config import app_config
from config import ollama_config

'''
提示词分析，将用户input进行拓展，返回一个更详细的prompt
'''

# VTK.js常用API列表，用于提示词中的知识注入
VTKJS_COMMON_APIS = app_config.VTKJS_COMMON_APIS

def analyze_query(query: str, model_name, system=None) -> dict:
    """分析用户查询，返回结构化的需求分析结果
    
    Args:
        query: 用户输入的查询
        model_name: 使用的LLM模型名称
        system: 可选的系统提示词，若不提供则使用默认提示词
        
    Returns:
        dict: 包含main_goal, data_source, key_apis的字典
    """
    
    # 默认系统提示词，结构化输出格式，增加领域知识和示例
    default_system = f"""
    你是一个专业的VTK.js可视化需求分析助手。你需要基于用户的问题，分析并扩展为结构化的可视化需求。

    ## 输出格式要求
    你必须严格按照以下JSON格式输出，不要添加任何其他内容：
    ```json
    {{
        "main_goal": "用户的主要目标，详细描述用户想要实现的可视化效果",
        "data_source": "数据来源，如文件类型、数据格式、是否需要生成模拟数据等",
        "key_apis": ["可能需要用到的VTK.js API列表，以数组形式列出"]
    }}
    ```

    ## VTK.js常用API参考
    以下是VTK.js中常用的API，可以参考这些API进行推荐：
    {', '.join(VTKJS_COMMON_APIS)}

    ## 示例
    用户输入: "使用vtkjs生成一个球体"
    你应该输出:
    ```json
    {{
        "main_goal": "使用VTK.js创建一个3D球体并在场景中渲染显示",
        "data_source": "使用vtkSphereSource生成的模拟数据",
        "key_apis": ["vtkSphereSource", "vtkMapper", "vtkActor", "vtkRenderer", "vtkRenderWindow"]
    }}
    ```
    
    记住，你的回答必须是有效的JSON格式，不要包含任何其他文本。
    """
    
    # 使用提供的system或默认system
    system_prompt = system if system else default_system
    
    # 构建分析提示词，包含用户查询
    analysis_prompt = f"""请分析并扩展以下用户查询，提供结构化的可视化需求：
    
    {query}
    
    请记住，你必须按照指定的JSON格式输出结果。"""
    
    # 从LLM获取回答
    try:
        response = get_deepseek_response(analysis_prompt, model_name, system_prompt)
        print('prompt analysis (raw):', response)
        
        # 尝试从回答中提取JSON
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析整个回答作为JSON
            json_str = response.strip()
        
        # 解析JSON
        try:
            result = json.loads(json_str)
            # 验证JSON结构
            if not all(k in result for k in ["main_goal", "data_source", "key_apis"]):
                raise ValueError("JSON缺少必要字段")
                
            # 确保key_apis是列表
            if not isinstance(result["key_apis"], list):
                result["key_apis"] = [api.strip() for api in result["key_apis"].split(",")]
                
            return result
            
        except json.JSONDecodeError:
            # JSON解析失败，尝试使用正则表达式提取
            print("JSON解析失败，尝试使用正则表达式提取")
            
            # 提取主要目标
            main_goal_match = re.search(r"main_goal\"?\s*:\s*\"([^\"]+)", response) or \
                             re.search(r"Main goal:?\s*(.*?)(?:\n|$)", response)
            main_goal = main_goal_match.group(1).strip() if main_goal_match else query

            # 提取数据来源
            data_source_match = re.search(r"data_source\"?\s*:\s*\"([^\"]+)", response) or \
                               re.search(r"Data source:?\s*(.*?)(?:\n|$)", response)
            data_source = data_source_match.group(1).strip() if data_source_match else ""

            # 提取可能需要的vtkjs接口
            key_apis_match = re.search(r"key_apis\"?\s*:\s*\[(.*?)\]", response, re.DOTALL) or \
                            re.search(r"VTK\.js interfaces:?\s*(.*?)(?:\n|$)", response)
            
            if key_apis_match:
                apis_text = key_apis_match.group(1)
                # 处理数组格式或逗号分隔的文本
                if '"' in apis_text or "'" in apis_text:
                    # 可能是JSON数组格式
                    key_apis = re.findall(r'\"([^\"]+)\"', apis_text) or re.findall(r'\'([^\']+)\'', apis_text)
                else:
                    # 可能是逗号分隔的文本
                    key_apis = [api.strip() for api in apis_text.split(",")]
            else:
                key_apis = []
            
            # 二次尝试：如果没有提取到API，尝试从整个文本中查找VTK.js API
            if not key_apis:
                for api in VTKJS_COMMON_APIS:
                    if api.lower() in response.lower():
                        key_apis.append(api)
            
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
    """将分析结果合并为格式化的提示词
    
    Args:
        analysis: 包含main_goal, data_source, key_apis的字典
        
    Returns:
        str: 格式化的提示词
    """
    return f"""
    用户需求分析：
    1. 主要目标：{analysis["main_goal"]}
    2. 数据来源：{analysis['data_source']}
    3. 关键API：{', '.join(analysis["key_apis"]) if analysis["key_apis"] else '待确定'}
    
    """


if __name__ == "__main__":
    test_query = """
    Generate an HTML file using vtk.js from CDN to visualize streamlines for a .vti dataset with a velocity field.

Requirements:

Load .vti file from path ../../../vtkjs-benchmark-datasets/redsea.vti using vtkXMLImageDataReader

Set active vector field as "velocity"

Generate 1000 random seed points inside dataset bounds using vtkPoints and vtkPolyData

Trace streamlines using vtkImageStreamline from these seeds

Set streamline properties: RK4, maximum number of steps 1000, forward direction

Add dataset outline using vtkOutlineFilter

Visualize:

Streamlines in cyan color with line width 1

Outline in red color with line width 3

Use vtkFullScreenRenderWindow for rendering and reset camera after adding actors

Load vtk.js via CDN link https://unpkg.com/vtk.js

No UI controls are required
    """
    result = analyze_query(test_query,ollama_config.models_deepseek['deepseek-v3'])
    # print(json.dumps(result, ensure_ascii=False, indent=2))
    print(merge_analysis(result))
