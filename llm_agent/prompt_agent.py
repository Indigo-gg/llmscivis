from config.ollama_config import ollama_config
from config.app_config import app_config
from langchain_ollama import OllamaLLM
from llm_agent.ollma_chat import get_qwen_response
import pandas as pd
import time
import json
import sys
import os
import demjson3
import re

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


'''
提示词分析，将用户input进行拓展，返回一个更详细的prompt
'''

# VTK.js常用API列表，用于提示词中的知识注入
VTKJS_COMMON_APIS = app_config.VTKJS_COMMON_APIS


def analyze_query(query: str, model_name, system=None) -> list[dict]:
    """分析用户查询，返回结构化的提示词拓展，用于构建可视化管道流程图

    Args:
        query: 用户输入的查询
        model_name: 使用的LLM模型名称
        system: 可选的系统提示词，若不提供则使用默认提示词

    Returns:
        list[dict]: 包含分割后的查询结果，支持流程图渲染
    """

    # 默认系统提示词，结构化输出格式
    # 关键修改点：定义了更丰富的JSON结构，增加了 phase, step_name, vtk_modules, weight
    default_system = f"""
    You are a professional VTK.js visualization pipeline architect. Your goal is to break down the user's request into a structured visualization pipeline.
    
    # Output Format Requirements (Strict JSON)
    1. Your response must contain only one valid JSON object, which is a list of steps.
    2. Each step object must strictly follow this schema:
    
    [
        {{
            "phase": "Data Loading",       // Choose one: "Data Loading", "Data Processing", "Visualization Setup", "UI Configuration", "Rendering & Interaction"
            "step_name": "Short Title",    // Max 5 words, for the flowchart node title (e.g., "Load VTI Dataset")
            "vtk_modules": ["vtkClass"],   // List of key VTK.js classes used in this step (e.g., ["vtkXMLImageDataReader"])
            "weight": 5,                   // Importance weight (1-10): higher = more critical to user request
            "description": "Full prompt..." // Detailed instruction for the code generation model
        }},
        ...
    ]

    3. No markdown, no code blocks, no explanations. Just the raw JSON list.
    4. Ensure the logical flow allows the output of one step to be the input of the next.
    5. Perform the core thinking process silently and do not output it. Only output the final JSON.
    """

    # Construct the analysis prompt
    analysis_prompt = f"""Please analyze the following user query and construct a VTK.js visualization pipeline:

    # Available API Knowledge Base
    {VTKJS_COMMON_APIS}

    # User Query
    {query}

    # Example 
    Input: "Generate HTML with vtk.js to visualize sliced rotor data, map pressure to blue-red color, and add a slice at 80%."

    Output:
    [
        {{
            "phase": "Data Loading",
            "step_name": "Load Dataset",
            "vtk_modules": ["vtkXMLImageDataReader", "vtkHttpDataSetReader"],
            "weight":3,
            "description": "Load the rotor dataset from 'http://127.0.0.1:5000/dataset/rotor.vti' using vtkXMLImageDataReader."
        }},
        {{
            "phase": "Data Processing",
            "step_name": "Slice Data",
            "vtk_modules": ["vtkImageSlice", "vtkPlane"],
            "weight": 10,
            "description": "Set 'Pressure' as the active scalar. Apply a slice along the Y-axis at 80% depth using vtkImageSlice logic."
        }},
        {{
            "phase": "Visualization Setup",
            "step_name": "Color Mapping",
            "vtk_modules": ["vtkColorTransferFunction", "vtkImageMapper"],
            "weight": 6,
            "description": "Map the 'Pressure' scalar values to a Blue-White-Red color gradient using vtkColorTransferFunction."
        }},
        {{
            "phase": "Rendering & Interaction",
            "step_name": "Render Scene",
            "vtk_modules": ["vtkRenderWindow", "vtkRenderer", "vtkRenderWindowInteractor"],
            "weight": 2,
            "description": "Initialize the render window, renderer, and interactor to display the visualization."
        }}
    ]

    Warning: You must output the result in the specified JSON format strictly. Do not output any other content.
    Output only one valid JSON object.""" 





    default_system_v1 = f"""
You are a professional VTK.js visualization pipeline architect. Your goal is to break down the user's request into a structured visualization pipeline.

# Output Format Requirements (Strict JSON)
1. Your response must contain only one valid JSON object, which is a list of steps.
2. Each step object must strictly follow this schema:

[
    {{
        "weight": 5,                   // Importance weight (1-10): higher = more critical to user request
        "description": "Full prompt..." // Detailed instruction for the code generation model
    }},
    ...
]

3. No markdown, no code blocks, no explanations. Just the raw JSON list.
4. Ensure the logical flow allows the output of one step to be the input of the next.
5. Perform the core thinking process silently and do not output it. Only output the final JSON.
"""

# Construct the analysis prompt
    analysis_prompt_v1 = f"""Please analyze the following user query and construct a VTK.js visualization pipeline:

# Available API Knowledge Base
{VTKJS_COMMON_APIS}

# User Query
{query}

# Example 
Input: "Generate HTML with vtk.js to visualize sliced rotor data, map pressure to blue-red color, and add a slice at 80%."

Output:
[
    {{
        "weight": 8,
        "description": "Load the rotor dataset from 'http://127.0.0.1:5000/dataset/rotor.vti' using vtkXMLImageDataReader."
    }},
    {{
        "weight": 9,
        "description": "Set 'Pressure' as the active scalar. Apply a slice along the Y-axis at 80% depth using vtkImageSlice logic."
    }},
    {{
        "weight": 9,
        "description": "Map the 'Pressure' scalar values to a Blue-White-Red color gradient using vtkColorTransferFunction."
    }},
    {{
        "weight": 6,
        "description": "Initialize the render window, renderer, and interactor to display the visualization."
    }}
]

Warning: You must output the result in the specified JSON format strictly. Do not output any other content.
Output only one valid JSON object."""
    # 从LLM获取回答
    try:
        result = ''
        response = get_qwen_response(
            analysis_prompt, model_name, default_system)
        print('prompt analysis (raw):\n', response, '\n')

        # 尝试从回答中提取JSON，使用更健壮的方法

        # 1. 首先尝试从markdown代码块中提取
        json_match = re.search(
            r'```(?:json)?\s*(\[.*?\])\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            print('从markdown代码块中提取到JSON数组')
        else:
            # 2. 尝试提取最外层的方括号包含的内容（贪婪匹配）
            json_match = re.search(r'(\[.*\])', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                print('从文本中提取到完整JSON数组')
            else:
                # 3. 尝试非贪婪匹配，可能提取到第一个有效的JSON数组
                json_match = re.search(r'(\[.*?\])', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    print('从文本中提取到第一个JSON数组')
                else:
                    # 4. 如果没有找到JSON数组，尝试直接解析整个回答
                    json_str = response.strip()
                    print('未找到JSON数组，尝试直接解析整个回答')

        # 记录提取到的JSON字符串
        print('提取的JSON字符串:\n', json_str)

        # 解析JSON - 使用更健壮的方法
        try:
            try:
                result = json.loads(json_str)
                print('使用标准JSON解析器成功解析')
                # 验证结果是否为数组且每个元素都有description字段
                if isinstance(result, list) and all(isinstance(item, dict) and 'description' in item for item in result):
                    print('验证JSON格式正确：数组且每个元素都包含description字段')
                    # 为下一个处理步骤：对于不包含weight的项，使用默认值
                    for item in result:
                        if 'weight' not in item:
                            item['weight'] = 5  # 默认权重值
                else:
                    print('JSON格式不符合要求：不是数组或元素缺少description字段')
                    return None
            except json.JSONDecodeError as e:
                # 如果标准解析失败，尝试使用内置的更宽松的解析方法
                print(f'标准JSON解析失败: {e}')
                # 使用demjson3进行更宽松的JSON解析
                print('尝试使用demjson3进行解析')
                try:
                    result = demjson3.decode(json_str)
                    print('使用demjson3成功解析')
                    # 验证结果是否为数组且每个元素都有description字段
                    if isinstance(result, list) and all(isinstance(item, dict) and 'description' in item for item in result):
                        print('验证JSON格式正确：数组且每个元素都包含description字段')
                        # 为下一个处理步骤：对于不包含weight的项，使用默认值
                        for item in result:
                            if 'weight' not in item:
                                item['weight'] = 5  # 默认权重值
                    else:
                        print('JSON格式不符合要求：不是数组或元素缺少description字段')
                        return None
                except demjson3.JSONDecodeError as e:
                    print(f'demjson3解析失败: {e}')
                    # 如果demjson3也失败了，返回默认结果
                    return None

        except json.JSONDecodeError:
            # JSON解析失败，尝试使用正则表达式提取
            print('JSON解析失败')
            return None

    except Exception as e:
        print(f"Error in analyze_query: {e}")
        return None

    print('prompt analysis (res): \n', result, '\n')
    return result


def process_benchmark_prompts(input_file="res2.xlsx", output_file="res2.xlsx", model_name=None):
    """
    读取Excel文件中的Benchmark prompt列，对每个问题进行分析，
    统计分割耗时，并将结果写入Excel文件

    Args:
        input_file: 输入Excel文件路径
        output_file: 输出Excel文件路径
        model_name: 使用的LLM模型名称
    """
    if model_name is None:
        model_name = ollama_config.models_qwen["qwen3-plus"]

    # 读取Excel文件
    df = pd.read_excel(input_file, sheet_name='检索效果对比')

    # 确保必要的列存在，如果不存在则创建并初始化为空字符串
    if 'splited_prompt_plus' not in df.columns:
        df['splited_prompt_plus'] = ''
    if 'time_spend_prompt_plus' not in df.columns:
        df['time_spend_prompt_plus'] = ''

    # 强制将这两列转换为字符串类型，避免数据类型冲突
    df['splited_prompt_plus'] = df['splited_prompt_plus'].astype(str)
    df['time_spend_prompt_plus'] = df['time_spend_prompt_plus'].astype(str)

    # 处理每个问题
    for index, row in df.iterrows():
        prompt = row['Benchmark prompt']

        if pd.isna(prompt) or prompt == '':
            print(f"跳过第{index+1}行：空问题")
            # 确保空值也被转换为字符串
            df.at[index, 'splited_prompt_plus'] = str("")
            df.at[index, 'time_spend_prompt_plus'] = str("")
            continue

        print(f"正在处理第{index+1}个问题...")

        # 记录开始时间
        start_time = time.time()

        try:
            # 分析问题
            result = analyze_query(prompt, model_name)
            print(f"使用的模型{model_name}")

            # 记录结束时间
            end_time = time.time()
            time_spent = end_time - start_time

            # 将结果写入DataFrame，确保转换为字符串
            if result is not None:
                # 将结果转换为JSON字符串保存
                df.at[index, 'splited_prompt_plus'] = str(
                    json.dumps(result, ensure_ascii=False, indent=2))
                df.at[index, 'time_spend_prompt_plus'] = str(
                    f"{time_spent:.2f}")
                print(f"第{index+1}个问题处理完成，耗时: {time_spent:.2f}秒")
            else:
                df.at[index, 'splited_prompt_plus'] = str("分析失败")
                df.at[index, 'time_spend_prompt_plus'] = str(
                    f"{time_spent:.2f}")
                print(f"第{index+1}个问题分析失败，耗时: {time_spent:.2f}秒")

        except Exception as e:
            # 记录结束时间
            end_time = time.time()
            time_spent = end_time - start_time

            df.at[index, 'splited_prompt_plus'] = str(f"处理出错: {str(e)}")
            df.at[index, 'time_spend_prompt_plus'] = str(f"{time_spent:.2f}")
            print(f"第{index+1}个问题处理出错: {e}，耗时: {time_spent:.2f}秒")

    # 保存到Excel文件
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df.to_excel(writer, sheet_name='检索效果对比', index=False)
        print(f"处理完成，结果已保存到 {output_file}")
    except Exception as e:
        print(f"保存文件时出错: {e}")
        # 尝试另存为新文件
        backup_file = output_file.replace('.xlsx', '_backup.xlsx')
        df.to_excel(backup_file, sheet_name='检索效果对比', index=False)
        print(f"已保存到备份文件: {backup_file}")


def batch_process_benchmark_prompts():
    """
    批量处理基准问题的主函数
    """
    try:
        process_benchmark_prompts(input_file=path, output_file=path)
        print("所有问题处理完成！")
    except Exception as e:
        print(f"批量处理过程中出错: {e}")


if __name__ == "__main__":
    # 读取res2.xlsx文件，其中Benchmark prompt列，每个数据项都是问题
    path = "D://Pcode//LLM4VIS//llmscivis//data//recoreds//res8-19.xlsx"
    batch_process_benchmark_prompts()
