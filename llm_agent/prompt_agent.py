import json
import re
import sys
import os
import demjson3

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_agent.ollma_chat import get_qwen_response
from langchain_ollama import OllamaLLM
from config.app_config import app_config
from config.ollama_config import ollama_config

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
    default_system = """
    你是一个专业的VTK.js可视化需求分析助手。你需要基于用户的问题，分析并扩展为结构化的可视化需求。

    # 输出格式要求（必须严格遵守）
    1. 你的回答必须只包含一个有效的JSON对象，且结构如下：
    <OUTPUT>{"visualization": {"type": "可视化类型", "description": "详细描述", "components": [{"name": "组件名称", "description": "组件描述"}], "dataSources": [{"name": "数据源名称", "type": "数据类型", "description": "数据源描述"}]}}</OUTPUT>
    2. 只允许输出上述JSON对象，不允许有任何多余内容，包括但不限于：解释、注释、markdown代码块、代码标记、HTML、额外文本、标签、空行等。
    3. 输出内容必须严格为纯JSON，不能有任何markdown格式、代码块标记、<Output>标签或其他包裹内容。
    4. 字段必须完整、格式必须正确，所有key和value都要用英文双引号，逗号、括号等符号必须符合JSON语法。
    5. 只允许输出visualization字段，不允许输出其他字段。

    # 错误示例（绝对禁止）
    - 输出包含任何额外文本、解释、注释、markdown代码块、HTML、标签等。
    - 输出格式为：
      以下是分析结果：
      {"visualization": {...}}
    - 输出格式为：
      <Output>{"visualization": {...}}</Output>
    - 输出格式为：
      <html>...</html>

    # 正确示例
    用户输入: "使用vtkjs生成一个球体"
    正确输出：
    {"visualization": {"type": "三维球体可视化", "description": "使用VTK.js创建一个3D球体并在场景中渲染显示", "components": [{"name": "vtkSphereSource", "description": "生成球体几何"}, {"name": "vtkMapper", "description": "几何到图形的映射"}, {"name": "vtkActor", "description": "场景中的可渲染对象"}, {"name": "vtkRenderer", "description": "渲染器"}, {"name": "vtkRenderWindow", "description": "渲染窗口"}], "dataSources": [{"name": "vtkSphereSource", "type": "模拟数据", "description": "生成球体数据"}]}}
    # VTK.js常用API参考
    以下是VTK.js中常用的API，可以参考这些API进行推荐：
    {', '.join(VTKJS_COMMON_APIS)}

    # 重要提示
    - 只输出一个有效的JSON对象，且仅包含visualization字段
    - 不允许有任何多余内容、格式、标签、代码块、解释或注释
    - 输出内容必须严格符合JSON语法，否则会导致解析失败
    """
    

    
    # 构建分析提示词，包含用户查询
    analysis_prompt = f"""请分析并扩展以下用户查询，提供结构化的可视化需求：
    
    {query}
    
    警告：你必须严格按照指定的JSON格式输出结果，不要输出任何其他内容。你的回答将被直接解析为JSON，任何额外的文本、解释或代码都会导致解析失败。
    
    只输出一个有效的JSON对象，不要使用markdown格式，不要添加代码块标记，不要添加任何解释或注释。"""
    
    # 从LLM获取回答
    try:
        response = get_qwen_response(analysis_prompt, model_name, default_system)
        print('prompt analysis (raw):\n', response,'\n')
        
        # 尝试从回答中提取JSON，使用更健壮的方法
        
        # 1. 首先尝试从markdown代码块中提取
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            print('从markdown代码块中提取到JSON')
        else:
            # 2. 尝试提取最外层的花括号包含的内容（贪婪匹配）
            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                print('从文本中提取到完整JSON对象')
            else:
                # 3. 尝试非贪婪匹配，可能提取到第一个有效的JSON对象
                json_match = re.search(r'(\{.*?\})', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    print('从文本中提取到第一个JSON对象')
                else:
                    # 4. 如果没有找到JSON对象，尝试直接解析整个回答
                    json_str = response.strip()
                    print('未找到JSON对象，尝试直接解析整个回答')
        
        # 记录提取到的JSON字符串
        print('提取的JSON字符串:\n', json_str)
        
        # 解析JSON - 使用更健壮的方法
        try:
            try:
                result = json.loads(json_str)
                print('使用标准JSON解析器成功解析')
            except json.JSONDecodeError as e:
                # 4. 如果标准解析失败，尝试使用内置的更宽松的解析方法
                print(f'标准JSON解析失败: {e}')
                # 使用demjson3进行更宽松的JSON解析
                print('尝试使用demjson3进行解析')
                try:
                    result = demjson3.decode(json_str)
                    print('使用demjson3成功解析')
                except demjson3.JSONDecodeError as e:
                    print(f'demjson3解析失败: {e}')
                    # 如果demjson3也失败了，返回默认结果
                    return {
                        "main_goal": query,
                        "data_source": "",
                        "key_apis": []
                    }
            
            # 只处理visualization结构
            if "visualization" in result:
                vis = result["visualization"]
                # 从visualization对象中提取信息
                main_goal = f"{vis.get('type', '')} - {vis.get('description', '')}".strip(' -')
                
                # 提取数据源信息
                data_sources = vis.get("dataSources", [])
                data_source = ", ".join([f"{ds.get('name', '')} ({ds.get('type', '')})" 
                                        for ds in data_sources]) if data_sources else ""
                
                # 提取API信息
                components = vis.get("components", [])
                key_apis = [comp.get("name") for comp in components if comp.get("name")]
                
                result = {
                    "main_goal": main_goal or query,
                    "data_source": data_source,
                    "key_apis": key_apis
                }
            else:
                # 如果没有visualization字段，直接返回默认
                result = {
                    "main_goal": query,
                    "data_source": "",
                    "key_apis": []
                }
            
            # 验证JSON结构并尝试修复
            required_fields = ["main_goal", "data_source", "key_apis"]
            for field in required_fields:
                if field not in result:
                    # 如果缺少字段，设置默认值
                    if field == "main_goal":
                        result[field] = query
                    elif field == "data_source":
                        result[field] = ""
                    elif field == "key_apis":
                        result[field] = []
                    print(f"警告: JSON缺少{field}字段，已设置默认值")
            
            # 确保key_apis是列表
            if not isinstance(result["key_apis"], list):
                if isinstance(result["key_apis"], str):
                    # 如果是字符串，尝试分割成列表
                    result["key_apis"] = [api.strip() for api in result["key_apis"].split(",")]
                else:
                    # 如果是其他类型，转换为字符串后再处理
                    result["key_apis"] = [str(result["key_apis"])]
                print("警告: key_apis不是列表格式，已转换为列表")
            
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

    res={
        "main_goal": main_goal,
        "data_source": data_source,
        "key_apis": key_apis
    }
    print('prompt analysis (res): \n', res,'\n')
    return res


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
