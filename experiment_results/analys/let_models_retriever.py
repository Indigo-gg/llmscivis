# 让模型根据下面的提示词和语料库检索出最相关的语料，并记录整个过程需要的时间。

import time
import os
import sys
import json
import argparse
from pathlib import Path

# 添加项目根目录到sys.path
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..')))

from llm_agent.ollma_chat import get_llm_response


tasks = [
    """Generate an HTML page using vtk.js to visualize the rotor dataset.
- Load the dataset from: http://127.0.0.1:5000/dataset/rotor.vti
- Set the active scalar array to "Pressure".
- Apply a slice along the Y axis at 95% depth of the dataset (convert percentage to slice index).
- Use a blue → white → red color map for pressure values, spanning from the minimum to maximum scalar range.
- Set opacity to fully opaque (no transparency variation).
- Add an orientation marker with XYZ axes in the bottom-right corner.
- No interactive GUI controls are required.""",
    """
 
Generate an HTML page using vtk.js to visualize the Deepwater dataset with isosurface rendering.

Load the dataset from: http://127.0.0.1:5000/dataset/deepwater.vti

Compute velocity magnitude from arrays v02 and v03; if not available, use prs as the scalar

Generate an isosurface at the mid-value of the scalar range

Use a blue → white → red color map spanning the scalar range (min to max)

Set the isosurface to fully opaque with smooth shading

Add an XYZ orientation marker in the bottom-right corner""",
    """

Generate an HTML page using vtk.js to visualize the Isabel dataset with streamline rendering.

Load the dataset from: http://127.0.0.1:5000/dataset/isabel.vti

Use the 'Velocity' array as the vector field for streamlines

Generate seed points at the center of the dataset with sufficient density to cover the domain

Compute streamlines following the velocity field

Render streamlines in cyan ([0, 1, 1]) with a specified line width

Render a dataset outline in red ([1, 0, 0]) with a specified line width""",
    """
Generate an HTML page using vtk.js to visualize the Redsea dataset with volume rendering.

Load the dataset from: http://127.0.0.1:5000/dataset/redsea.vti

Compute velocity magnitude from the 'velocity' array and set it as the active scalar

Apply volume rendering using a blue → white → red color map spanning the scalar range (min to max)

Apply a piecewise opacity function to control transparency across scalar values

Set shading, ambient, diffuse, and specular properties for realistic volume appearance

Adjust the camera to look along +Z and center on the dataset"""
]


def load_corpus(corpus_path: str) -> dict:
    """
    从指定路径读取所有description.txt文件，组成(文件夹名, description内容)的字典

    Args:
        corpus_path: 语料库文件夹路径

    Returns:
        dict: {"folder_name": "description content", ...}
    """
    corpus = {}
    corpus_dir = Path(corpus_path)

    if not corpus_dir.exists():
        print(f"警告: 语料库路径不存在: {corpus_path}")
        return corpus

    # 遍历所有子文件夹
    for folder in corpus_dir.iterdir():
        if folder.is_dir():
            description_file = folder / "description.txt"
            if description_file.exists():
                try:
                    with open(description_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        corpus[folder.name] = content
                        print(f"✓ 已读取: {folder.name}")
                except Exception as e:
                    print(f"✗ 读取失败 {folder.name}: {e}")

    return corpus


def save_corpus_json(corpus: dict, output_path: str):
    """
    将语料库保存为JSON文件

    Args:
        corpus: 语料库字典
        output_path: 输出JSON文件路径
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(corpus, f, ensure_ascii=False, indent=2)
        print(f"✓ 语料库已保存到: {output_path}")
    except Exception as e:
        print(f"✗ 保存语料库失败: {e}")


def create_retrieval_prompt(corpus: dict, query: str) -> str:
    """
    创建用于模型检索的提示词，要求返回结构化JSON

    Args:
        corpus: 语料库字典
        query: 用户查询

    Returns:
        str: 完整的提示词
    """
    corpus_text = "\n\n".join(
        [f"【{name}】\n{content}" for name, content in corpus.items()])

    prompt = f"""你是一个VTK.js可视化代码生成助手。你的任务是根据给定的用户需求，从语料库中找出最相关的示例或模式。

【用户需求】
{query}

【语料库】
{corpus_text}

【任务】
1. 理解用户的需求意图
2. 从上述语料库中找出最相关的部分（3-6个）
3. 返回结构化的JSON格式结果

【输出格式】
请以下面的JSON格式返回结果，不要包含任何其他文本、markdown或代码块标记：
{{
  "understanding": "用户需求的简短总结（一句话）",
  "retrieved_items": [
    {{
      "title": "Filter-ImageSlice",
      "relevance_score": 0.95,
      "reason": "为什么这项相关的简短说明（一句话）"
    }},
    {{
      "title": "IO-HttpdatasetReader",
      "relevance_score": 0.90,
      "reason": "为什么这项相关的简短说明（一句话）"
    }}
  ]
}}

重要：返回有效的JSON格式，不要包含任何额外文本。"""

    return prompt


def parse_retrieval_response(response: str) -> dict:
    """
    解析LLM的结构化JSON响应
    
    Args:
        response: LLM返回的响应文本
    
    Returns:
        dict: 解析后的结构化数据
    """
    try:
        # 尝试直接解析JSON
        result = json.loads(response)
        return result
    except json.JSONDecodeError:
        # 如果直接解析失败，尝试提取JSON部分
        try:
            # 查找JSON的开始和结束位置
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                return result
        except (json.JSONDecodeError, ValueError):
            pass
        
        # 如果无法解析，返回错误标记
        return {
            "understanding": "无法解析响应",
            "retrieved_items": [],
            "raw_response": response[:500]  # 保留前500字符用于调试
        }


def perform_retrieval(query: str, corpus: dict, model_name: str = "deepseek-v3") -> dict:
    """
    使用LLM进行检索

    Args:
        query: 查询文本
        corpus: 语料库字典
        model_name: 使用的模型名称

    Returns:
        dict: 包含查询、结果、耗时等信息
    """
    print(f"\n开始检索 [{model_name}]: {query[:50]}...")

    start_time = time.time()

    try:
        prompt = create_retrieval_prompt(corpus, query)

        system_prompt = """你是一个专业的VTK.js可视化专家。
你的职责是：
1. 理解用户的可视化需求
2. 从现有示例和语料库中找出最相关的内容
3. 返回结构化的JSON格式响应
4. 不包含任何markdown或代码块标记"""

        response = get_llm_response(prompt, model_name, system_prompt)
        
        # 解析结构化响应
        parsed_response = parse_retrieval_response(response)

        elapsed_time = time.time() - start_time
        
        # 提取检索到的模块名称列表
        retrieved_modules = []
        if "retrieved_items" in parsed_response:
            for item in parsed_response["retrieved_items"]:
                if isinstance(item, dict) and "title" in item:
                    retrieved_modules.append(item["title"])

        result = {
            "query": query,
            "model": model_name,
            "response": response,
            "parsed_response": parsed_response,
            "retrieved_modules": retrieved_modules,
            "elapsed_time": elapsed_time,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        print(f"✓ 检索完成，耗时: {elapsed_time:.2f}秒，检索到 {len(retrieved_modules)} 个模块")
        return result

    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"✗ 检索失败: {e}")

        return {
            "query": query,
            "model": model_name,
            "error": str(e),
            "elapsed_time": elapsed_time,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }


def main():
    """
    主函数：执行完整的检索流程
    """
    parser = argparse.ArgumentParser(description="LLM模型检索语料库")
    parser.add_argument("--corpus-path", type=str,
                        default="data/vtkjs-examples/prompt-sample",
                        help="语料库路径")
    parser.add_argument("--model", type=str, default="deepseek-v3",
                        help="使用的模型")
    parser.add_argument("--output", type=str, default="retrieval_results_with_time.json",
                        help="输出文件路径")
    parser.add_argument("--corpus-output", type=str, default="corpus.json",
                        help="语料库JSON输出路径")

    args = parser.parse_args()

    print("="*60)
    print("LLM模型检索系统 - 结构化输出版本")
    print("="*60)

    # 第1步：加载语料库
    print("\n[步骤1] 加载语料库...")
    corpus = load_corpus(args.corpus_path)

    if not corpus:
        print("⚠ 警告: 没有找到任何语料库文件")
        print(f"  预期位置: {args.corpus_path}")
        # 使用演示语料库
        corpus = {
            "image_slice": "处理2D图像切片的示例",
            "polygon_loading": "加载3D多边形数据的示例",
            "volume_rendering": "体积渲染的示例",
            "streamline": "流线渲染的示例"
        }
        print("  已使用演示语料库")
    else:
        print(f"✓ 成功加载 {len(corpus)} 个语料库项")

    # 第2步：保存语料库为JSON
    print("\n[步骤2] 保存语料库...")
    save_corpus_json(corpus, args.corpus_output)

    # 第3步：执行检索
    print("\n[步骤3] 执行检索任务...")
    all_results = []

    for i, task in enumerate(tasks, 1):
        print(f"\n--- 任务 {i}/{len(tasks)} ---")
        result = perform_retrieval(task, corpus, args.model)
        all_results.append(result)

        # 添加延迟以避免API限流
        if i < len(tasks):
            time.sleep(2)

    # 第4步：保存结果
    print("\n[步骤4] 保存结果...")
    output_data = {
        "summary": {
            "total_queries": len(all_results),
            "total_time": sum(r.get("elapsed_time", 0) for r in all_results),
            "model_used": args.model,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "corpus_info": {
            "total_items": len(corpus),
            "items": list(corpus.keys())
        },
        "results": all_results
    }

    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"✓ 结果已保存到: {args.output}")
    except Exception as e:
        print(f"✗ 保存结果失败: {e}")

    # 第5步：打印统计信息
    print("\n" + "="*60)
    print("检索统计")
    print("="*60)
    print(f"总查询数: {len(all_results)}")
    total_time = sum(r.get("elapsed_time", 0) for r in all_results)
    print(f"总耗时: {total_time:.2f}秒")
    print(f"平均耗时: {total_time/len(all_results):.2f}秒" if all_results else "N/A")

    # 统计错误
    errors = [r for r in all_results if "error" in r]
    if errors:
        print(f"\n⚠ 失败查询: {len(errors)}")
        for error_result in errors:
            print(f"  - {error_result['error']}")
    
    # 统计检索到的模块
    total_modules = sum(len(r.get("retrieved_modules", [])) for r in all_results if "retrieved_modules" in r)
    print(f"\n📊 总检索模块数: {total_modules}")

    print("\n" + "="*60)
    print("完成！")
    print("="*60)


if __name__ == "__main__":
    main()
