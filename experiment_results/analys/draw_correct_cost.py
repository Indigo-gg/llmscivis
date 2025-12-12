import os
import sys
import difflib
import json
from collections import defaultdict
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# 设置全局字体，防止中文乱码
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial', 'sans-serif'] 
plt.rcParams['axes.unicode_minus'] = False

# ============================= 差异检测函数 =============================

def calculate_diff_stats(file1_path, file2_path):
    """
    计算两个文件的差异统计（不写入输出文件）
    返回：{"added": int, "deleted": int, "total": int, "changed": int}
    """
    try:
        with open(file1_path, 'r', encoding='utf-8') as f1, \
             open(file2_path, 'r', encoding='utf-8') as f2:
            file1_lines = f1.readlines()
            file2_lines = f2.readlines()
    except (FileNotFoundError, Exception) as e:
        print(f"错误: {e}")
        return None

    # 去除每行的空白符和缩进
    file1_lines_stripped = [line.strip() for line in file1_lines]
    file2_lines_stripped = [line.strip() for line in file2_lines]
    
    # 使用 difflib.SequenceMatcher 来分析差异
    matcher = difflib.SequenceMatcher(None, file1_lines_stripped, file2_lines_stripped)
    
    added_lines = 0
    deleted_lines = 0
    changed_lines = 0
    
    # 遍历操作码来统计差异
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue
        elif tag == 'delete':
            deleted_lines += (i2 - i1)
        elif tag == 'insert':
            added_lines += (j2 - j1)
        elif tag == 'replace':
            deleted_lines += (i2 - i1)
            added_lines += (j2 - j1)
            changed_lines += sum(1 for line1, line2 in zip(file1_lines[i1:i2], file2_lines[j1:j2]) if line1.strip() != line2.strip())

    total_differences = added_lines + deleted_lines
    
    return {
        "added": added_lines,
        "deleted": deleted_lines,
        "total": total_differences,
        "changed": changed_lines
    }

def find_file_pairs(folder_path):
    """
    在文件夹中查找文件对（generated_code.html 和 modified_code.html）
    """
    try:
        files = os.listdir(folder_path)
    except FileNotFoundError:
        return []
    
    # 查找 generated_code.html 和 modified_code.html
    generated_file = os.path.join(folder_path, 'generated_code.html')
    modified_file = os.path.join(folder_path, 'modified_code.html')
    
    pairs = []
    if os.path.exists(generated_file) and os.path.exists(modified_file):
        pairs.append((generated_file, modified_file))
    
    return pairs

def scan_all_models(root_folder):
    """
    扫描指定的模型文件夹及其任务子文件夹，计算 generated_code.html 与 modified_code.html 的差异统计
    返回：{model_name: {task_name: stats_dict}}
    """
    all_results = {}
    
    if not os.path.isdir(root_folder):
        print(f"错误：文件夹 {root_folder} 不存在")
        return all_results
    
    # 指定要扫描的模型
    target_models = ['claude_sonnet_4', 'deepseek-v3', 'gpt_5_with_rag', 'qwen3_max_with_rag']
    
    for model_name in target_models:
        model_path = os.path.join(root_folder, model_name)
        
        if not os.path.isdir(model_path):
            print(f"警告：模型文件夹 {model_path} 不存在，跳过")
            continue
        
        # 扫描模型下的任务子文件夹
        task_folders = [d for d in os.listdir(model_path)
                        if os.path.isdir(os.path.join(model_path, d))]
        
        if task_folders:
            model_stats = {}
            for task_name in sorted(task_folders):
                task_path = os.path.join(model_path, task_name)
                file_pairs = find_file_pairs(task_path)
                
                if file_pairs:
                    for generated, modified in file_pairs:
                        stats = calculate_diff_stats(generated, modified)
                        if stats:
                            model_stats[task_name] = stats
            
            if model_stats:
                all_results[model_name] = model_stats
    
    return all_results

def generate_summary_report(results, output_file):
    """
    生成差异汇总报告
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("代码修正成本分析汇总报告\n")
        f.write("=" * 80 + "\n\n")
        
        # 按模型组织数据
        for model_name in sorted(results.keys()):
            f.write(f"\n{'─' * 80}\n")
            f.write(f"模型: {model_name}\n")
            f.write(f"{'─' * 80}\n")
            
            model_tasks = results[model_name]
            model_total = 0
            
            for task_name in sorted(model_tasks.keys()):
                stats = model_tasks[task_name]
                model_total += stats['total']
                f.write(f"\n  任务: {task_name}\n")
                f.write(f"    总差异行数: {stats['total']}\n")
                f.write(f"    新增行数: {stats['added']}\n")
                f.write(f"    删除行数: {stats['deleted']}\n")
            
            f.write(f"\n  模型总计: {model_total} 行\n")
        
        # 汇总统计
        f.write(f"\n{'=' * 80}\n")
        f.write("汇总统计\n")
        f.write(f"{'=' * 80}\n")
        
        # 按任务统计
        all_tasks = set()
        for model_data in results.values():
            all_tasks.update(model_data.keys())
        
        f.write("\n按任务分类：\n")
        for task_name in sorted(all_tasks):
            task_total = 0
            f.write(f"\n  {task_name}:\n")
            for model_name in sorted(results.keys()):
                if task_name in results[model_name]:
                    stats = results[model_name][task_name]
                    task_total += stats['total']
                    f.write(f"    {model_name}: {stats['total']} 行\n")
            f.write(f"    任务总计: {task_total} 行\n")
        
        # 按模型统计
        f.write(f"\n\n按模型分类：\n")
        for model_name in sorted(results.keys()):
            model_total = sum(stats['total'] for stats in results[model_name].values())
            f.write(f"  {model_name}: {model_total} 行\n")
    
    print(f"汇总报告已写入: {output_file}")

def prepare_plotting_data(results):
    """
    从扫描结果提取绘图数据，按指定顺序排列模型，并映射模型名称
    返回：{display_name: [task1_value, task2_value, ...]}
    """
    # 定义模型顺序和名称映射
    model_order = ['gpt_5_with_rag', 'claude_sonnet_4', 'qwen3_max_with_rag', 'deepseek-v3']
    model_display_names = {
        'claude_sonnet_4': 'claude_sonnet_4',
        'gpt_5_with_rag': 'gpt_5',
        'deepseek-v3': 'deepseek-v3',
        'qwen3_max_with_rag': 'qwen3_max'
    }
    
    # 确定任务顺序
    all_tasks = set()
    for model_data in results.values():
        all_tasks.update(model_data.keys())
    
    task_list = sorted(all_tasks)
    
    # 构建绘图数据，按指定顺序排列
    plot_data = {}
    for model_name in model_order:
        if model_name in results:
            display_name = model_display_names.get(model_name, model_name)
            model_values = []
            for task_name in task_list:
                if task_name in results[model_name]:
                    model_values.append(results[model_name][task_name]['total'])
                else:
                    model_values.append(0)
            plot_data[display_name] = model_values
    
    return plot_data, task_list

# ============================= 原始绘图函数 =============================

def plot_rag_impact_comparison(data=None):
    """
    生成第一张图：RAG 工作流对代码修正成本（行数差异）的影响
    如果 data 为 None，则使用硬编码的示例数据
    """
    if data is None:
        # 1. 准备数据 (根据原图图片上的数字提取)
        tasks = ["Cutter", "Isosurface", "Stream Tracing", "Volume Rendering"]
        
        # 数据格式：[Task1, Task2, Task3, Task4]
        data = {
            "ChatGPT-4o":               [3, 56, 21, 3],
            "ChatGPT-4o (No RAG)":      [29, 94, 76, 7],
            "DeepSeek-v3.1":            [4, 26, 23, 3],
            "DeepSeek-v3.1 (No RAG)":   [47, 31, 20, 41]
        }
    else:
        tasks = list(data[1]) if isinstance(data, tuple) else []
        data = data[0] if isinstance(data, tuple) else data

    # 2. 设置配色
    colors = {
        list(data.keys())[0]: "#4DBBD5",  # 较亮青色
        list(data.keys())[1] if len(data) > 1 else "": "#296D7D",  # 深青色
        list(data.keys())[2] if len(data) > 2 else "": "#F4A582",  # 较亮橙色
        list(data.keys())[3] if len(data) > 3 else "": "#CA5D2A"   # 深橙色
    }
    
    # 过滤掉空键
    colors = {k: v for k, v in colors.items() if k}

    # 3. 绘图参数设置
    x = np.arange(len(tasks))
    width = 0.18
    multiplier = 0

    fig, ax = plt.subplots(figsize=(14, 7), dpi=120)

    # 4. 循环绘制柱状图
    for attribute, measurement in data.items():
        offset = width * multiplier
        color = colors.get(attribute, "#808080")
        rects = ax.bar(x + offset, measurement, width, label=attribute, color=color, edgecolor='white', linewidth=0.5)
        
        # 在柱子顶部添加标签（兼容旧版 matplotlib）
        for rect in rects:
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontsize=9, color='#333333')
        
        multiplier += 1

    # 5. 装饰图表
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(tasks, fontsize=11)
    
    ax.set_ylabel('Total Lines of Difference (Correction Cost)', fontsize=12, labelpad=10)
    ax.set_xlabel('Task Type', fontsize=12, labelpad=10)
    ax.set_title('Impact of RAG Workflow on Code Correction Costs', fontsize=16, pad=20, weight='bold')

    ax.legend(loc='upper left', frameon=True, fancybox=True, shadow=True, fontsize=10)
    
    ax.yaxis.grid(True, linestyle='--', which='major', color='grey', alpha=0.25)
    ax.set_axisbelow(True)

    ax.set_ylim(0, max([max(v) for v in data.values()]) * 1.15)

    plt.tight_layout()
    plt.show()

def plot_model_cost_comparison(data=None, tasks=None):
    """
    生成第二张图：不同模型在四个任务下的修正成本对比
    如果 data 为 None，则使用硬编码的示例数据
    """
    if data is None:
        # 1. 准备数据
        tasks = ["Cutter", "Isosurface", "Stream Tracing", "Volume Rendering"]
        
        data = {
        }

    # 2. 设置配色
    colors = [
        "#FF8080", # 柔和红
        "#4DBBD5", # 柔和青
        "#F4A582", # 柔和橙
        "#9575CD"  # 柔和紫
    ]
    
    # 扩展颜色列表以适应更多模型
    while len(colors) < len(data):
        colors.extend(colors)

    # 3. 绘图参数
    x = np.arange(len(tasks))
    width = 0.18
    multiplier = 0

    fig, ax = plt.subplots(figsize=(14, 7), dpi=120)

    # 4. 循环绘制
    for i, (attribute, measurement) in enumerate(data.items()):
        offset = width * multiplier
        rects = ax.bar(x + offset, measurement, width, label=attribute, color=colors[i % len(colors)], edgecolor='white', linewidth=0.5)
        
        # 在柱子顶部添加标签（兼容旧版 matplotlib）
        for rect in rects:
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontsize=9, color='#333333')
        
        multiplier += 1

    # 5. 装饰图表
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(tasks, fontsize=11)
    
    ax.set_ylabel('Total Lines of Difference (Correction Cost)', fontsize=12, labelpad=10)
    ax.set_xlabel('Task Type', fontsize=12, labelpad=10)
    ax.set_title('Correction Cost Comparison Across Different Models', fontsize=16, pad=20, weight='bold')
    
    ax.legend(loc='upper left', frameon=True, fancybox=True, shadow=False, fontsize=10)
    
    ax.yaxis.grid(True, linestyle='--', which='major', color='grey', alpha=0.25)
    ax.set_axisbelow(True)
    
    ax.set_ylim(0, max([max(v) for v in data.values()]) * 1.15)

    plt.tight_layout()
    plt.show()

# ============================= 主程序 =============================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="自动扫描所有模型生成代码，计算修正成本，生成汇总报告和图表"
    )
    parser.add_argument(
        '--root-folder',
        type=str,
        default=None,
        help='generated_code 文件夹的路径（默认为相对路径）'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='输出报告的目录（默认为当前脚本所在目录）'
    )
    parser.add_argument(
        '--no-plot',
        action='store_true',
        help='不生成图表，仅生成报告和数据文件'
    )
    parser.add_argument(
        '--plot-only',
        action='store_true',
        help='仅生成图表，跳过扫描和报告生成'
    )
    
    args = parser.parse_args()
    
    # 配置路径
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        current_dir = Path(__file__).parent
        output_dir = current_dir
    
    if args.root_folder:
        root_folder = Path(args.root_folder)
    else:
        # 默认相对路径：当前脚本的上上级目录 + generated_code
        current_dir = Path(__file__).parent
        root_folder = current_dir.parent / "generated_code"
    
    output_report = output_dir / "diff_analysis_report.txt"
    output_json = output_dir / "diff_analysis_data.json"
    
    print("=" * 80)
    print("代码修正成本自动分析工具")
    print("=" * 80)
    print(f"扫描路径: {root_folder.resolve()}")
    print(f"输出目录: {output_dir.resolve()}")
    print()
    
    if not args.plot_only:
        print("开始扫描所有模型的生成代码...")
        print("=" * 80)
        
        # 扫描所有模型
        results = scan_all_models(str(root_folder))
        
        if results:
            print(f"\n✓ 成功扫描 {len(results)} 个模型")
            
            # 生成汇总报告
            generate_summary_report(results, str(output_report))
            
            # 保存原始数据为 JSON
            json_data = {}
            for model, tasks_data in results.items():
                json_data[model] = {}
                for task, stats in tasks_data.items():
                    json_data[model][task] = stats
            
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            print(f"✓ 数据已保存为 JSON: {output_json}\n")
            
            # 生成图表
            if not args.no_plot:
                print("生成图表...")
                plot_data, task_list = prepare_plotting_data(results)
                print(f"✓ 数据已提取，包含 {len(plot_data)} 个模型和 {len(task_list)} 个任务")
                print("\n生成第一张图：模型成本对比...")
                plot_model_cost_comparison(plot_data, task_list)
        else:
            print(f"\n✗ 在 {root_folder} 中未找到任何有效的文件对")
            print("请确保文件夹结构正确，且每个模型文件夹中都有 *.html 和 *_modified.html 或 *_corrt.html 文件")
    
    elif args.plot_only and output_json.exists():
        print("从缓存的 JSON 数据加载图表数据...")
        with open(output_json, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # 转换数据格式
        results = {}
        for model, tasks_data in json_data.items():
            results[model] = {}
            for task, stats in tasks_data.items():
                results[model][task] = stats
        
        plot_data, task_list = prepare_plotting_data(results)
        print(f"✓ 已加载 {len(plot_data)} 个模型的数据")
        print("\n生成图表...")
        plot_model_cost_comparison(plot_data, task_list)
    else:
        print(f"✗ 未找到缓存数据文件: {output_json}")
        print("请先运行不带 --plot-only 的命令来生成数据")
