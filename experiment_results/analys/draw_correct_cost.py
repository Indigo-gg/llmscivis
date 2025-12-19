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

# ============================= 全局配置 =============================
GLOBAL_NAME = "12-15-without-rag"

# 模型配置
GLOBAL_DEFAULT_MODELS_WITH_RAG = ['claude_sonnet_4', 'deepseek-v3', 'gpt_5_with_rag', 'qwen3_max_with_rag']
GLOBAL_DEFAULT_MODELS_WITHOUT_RAG = [ 'gpt_5_with_rag', 'qwen3_max_with_rag', 'qwen3_max_without_rag', 'gpt_5_without_rag']

# 任务（子文件夹）配置 - 可手动指定读取顺序
# 设置为 None 表示自动识别所有子文件夹
GLOBAL_TASK_ORDER = ['slice', 'isosurface', 'stream_tracing', 'volume_rendering']  # 例如: ['slice', 'isosurface', 'stream_tracing', 'volume_rendering']

# WITH-RAG 模型顺序和名称映射
GLOBAL_MODEL_ORDER_WITH_RAG = ['gpt_5_with_rag', 'claude_sonnet_4', 'qwen3_max_with_rag', 'deepseek-v3']
GLOBAL_MODEL_DISPLAY_NAMES_WITH_RAG = {
    'claude_sonnet_4': 'CLAUDE_SONNET_4',
    'gpt_5_with_rag': 'GPT_5',
    'deepseek-v3': 'DEEPSEEK_V3',
    'qwen3_max_with_rag': 'QWEN3_MAX'
}

# WITHOUT-RAG 模型顺序和名称映射
# 按模型类型分组，同个模型的 with_rag 和 without_rag 挨在一起
GLOBAL_MODEL_ORDER_WITHOUT_RAG = ['gpt_5_with_rag', 'gpt_5_without_rag', 'qwen3_max_with_rag', 'qwen3_max_without_rag']
GLOBAL_MODEL_DISPLAY_NAMES_WITHOUT_RAG = {
    'gpt_5_with_rag': 'GPT-5 (with RAG)',
    'gpt_5_without_rag': 'GPT-5 (no RAG)',
    'qwen3_max_with_rag': 'Qwen3-Max (with RAG)',
    'qwen3_max_without_rag': 'Qwen3-Max (no RAG)'
}

# 模型颜色配置 - 同个模型用相近颜色，不同模型用不同颜色
GLOBAL_MODEL_COLORS_WITHOUT_RAG = {
    'gpt_5_with_rag': '#FF6B6B',      # 鲜红
    'gpt_5_without_rag': '#FF9999',   # 浅红（同组，相近色）
    'qwen3_max_with_rag': '#4DBBD5',  # 鲜青
    'qwen3_max_without_rag': '#7DD3E8' # 浅青（同组，相近色）
}

# 数据源路径配置
GLOBAL_DATA_SOURCE_WITH_RAG = 'generated_code_without_rag'
GLOBAL_DATA_SOURCE_WITHOUT_RAG = 'generated_code_without_rag'

# 图表配置
GLOBAL_CHART_COLORS = [
    "#FF8080",  # 柔和红
    "#4DBBD5",  # 柔和青
    "#F4A582",  # 柔和橙
    "#9575CD"   # 柔和紫
]

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

def scan_all_models(root_folder, target_models=None):
    """
    扫描指定的模型文件夹及其任务子文件夹，计算 generated_code.html 与 modified_code.html 的差异统计
    参数：
        root_folder: 根文件夹路径
        target_models: 目标模型列表（如果为 None 则使用默认列表）
    返回：{model_name: {task_name: stats_dict}}
    """
    all_results = {}
    
    if not os.path.isdir(root_folder):
        print(f"错误：文件夹 {root_folder} 不存在")
        return all_results
    
    # 如果没有指定目标模型，使用默认列表
    if target_models is None:
        target_models = GLOBAL_DEFAULT_MODELS_WITH_RAG
    
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

def prepare_plotting_data(results, model_order=None, model_display_names=None, task_order=None):
    """
    从扫描结果提取绘图数据，按指定顺序排列模型和任务，并映射模型名称
    参数：
        results: 扫描结果
        model_order: 模型顺序列表（如果为 None 则使用默认）
        model_display_names: 模型名称映射（如果为 None 则使用默认）
        task_order: 任务顺序列表（如果为 None 则自动排序）
    返回：{display_name: [task1_value, task2_value, ...]}, task_list
    """
    # 定义模型顺序和名称映射（默认值）
    if model_order is None:
        model_order = GLOBAL_MODEL_ORDER_WITH_RAG
    
    if model_display_names is None:
        model_display_names = GLOBAL_MODEL_DISPLAY_NAMES_WITH_RAG
    
    # 确定任务顺序
    all_tasks = set()
    for model_data in results.values():
        all_tasks.update(model_data.keys())
    
    # 如果指定了任务顺序，按照指定顺序排列；否则自动排序
    if task_order is None:
        task_list = sorted(all_tasks)
    else:
        # 使用指定的任务顺序，但只包含实际存在的任务
        task_list = [task for task in task_order if task in all_tasks]
        # 添加任何未在 task_order 中指定但存在于数据中的任务（追加到末尾）
        remaining_tasks = [task for task in sorted(all_tasks) if task not in task_list]
        task_list.extend(remaining_tasks)
    
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

def plot_rag_impact_comparison(data=None, fontsize_config=None):
    """
    生成第一张图：RAG 工作流对代码修正成本（行数差异）的影响
    如果 data 为 None，则使用硬编码的示例数据
    参数：
        fontsize_config: 字号配置字典 {title, label, tick, legend, value}
                        例：{'title': 20, 'label': 16, 'tick': 14, 'legend': 12, 'value': 11}
    """
    # 设置默认字号
    if fontsize_config is None:
        fontsize_config = {}
    
    fs_title = fontsize_config.get('title', 18)
    fs_label = fontsize_config.get('label', 15)
    fs_tick = fontsize_config.get('tick', 14)
    fs_legend = fontsize_config.get('legend', 12)
    fs_value = fontsize_config.get('value', 11)
    if data is None:
        # 1. 准备数据 (根据原图图片上的数字提取)
        tasks = ["Slice", "Isosurface", "Stream Tracing", "Volume Rendering"]
        
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
                    ha='center', va='bottom', fontsize=fs_value, color='#333333')
        
        multiplier += 1

    # 5. 装饰图表
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(tasks, fontsize=fs_tick)
    
    ax.set_ylabel('Correction Cost', fontsize=fs_label, labelpad=10)
    ax.set_xlabel('Task Type', fontsize=fs_label, labelpad=10)
    # 去掉标题
    # ax.set_title('Impact of RAG Workflow on Code Correction Costs', fontsize=fs_title, pad=20, weight='bold')

    ax.legend(loc='upper left', frameon=True, fancybox=True, shadow=True, fontsize=fs_legend)
    
    # 调整左侧刻度数字大小
    ax.tick_params(axis='y', labelsize=fs_tick)
    ax.yaxis.grid(True, linestyle='--', which='major', color='grey', alpha=0.25)
    ax.set_axisbelow(True)

    ax.set_ylim(0, max([max(v) for v in data.values()]) * 1.15)

    plt.tight_layout()
    plt.show()

def plot_model_cost_comparison(data=None, tasks=None, model_colors=None, fontsize_config=None):
    """
    生成第二张图：不同模型在四个任务下的修正成本对比
    如果 data 为 None，则使用硬编码的示例数据
    参数：
        data: 绘图数据字典
        tasks: 任务列表
        model_colors: 模型颜色映射（可选）
        fontsize_config: 字号配置字典 {title, label, tick, legend, value}
                        例：{'title': 20, 'label': 16, 'tick': 14, 'legend': 12, 'value': 11}
    """
    # 设置默认字号
    if fontsize_config is None:
        fontsize_config = {}
    
    fs_title = fontsize_config.get('title', 18)
    fs_label = fontsize_config.get('label', 15)
    fs_tick = fontsize_config.get('tick', 14)
    fs_legend = fontsize_config.get('legend', 12)
    fs_value = fontsize_config.get('value', 11)
    if data is None:
        # 1. 准备数据
        tasks = ["Slice", "Isosurface", "Stream Tracing", "Volume Rendering"]
        
        data = {
        }

    # 2. 设置配色
    # 尝试从 model_colors 参数获取颜色，否则使用默认颜色
    if model_colors is None:
        colors = GLOBAL_CHART_COLORS.copy()
        # 扩展颜色列表以适应更多模型
        while len(colors) < len(data):
            colors.extend(colors)
        color_dict = {list(data.keys())[i]: colors[i] for i in range(len(data))}
    else:
        color_dict = model_colors

    # 3. 绘图参数
    x = np.arange(len(tasks))
    width = 0.18
    multiplier = 0

    fig, ax = plt.subplots(figsize=(14, 7), dpi=120)

    # 4. 循环绘制
    for i, (attribute, measurement) in enumerate(data.items()):
        offset = width * multiplier
        color = color_dict.get(attribute, GLOBAL_CHART_COLORS[i % len(GLOBAL_CHART_COLORS)])
        rects = ax.bar(x + offset, measurement, width, label=attribute, color=color, edgecolor='white', linewidth=0.5)
        
        # 在柱子顶部添加标签（兼容旧版 matplotlib）
        for rect in rects:
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontsize=fs_value, color='#333333')
        
        multiplier += 1

    # 5. 装饰图表
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(tasks, fontsize=fs_tick)
    
    ax.set_ylabel('Correction Cost', fontsize=fs_label, labelpad=10)
    ax.set_xlabel('Task Type', fontsize=fs_label, labelpad=10)
    # 去掉标题
    # ax.set_title('Correction Cost Comparison Across Different Models', fontsize=fs_title, pad=20, weight='bold')
    
    ax.legend(loc='upper left', frameon=True, fancybox=True, shadow=False, fontsize=fs_legend)
    
    # 调整左侧刻度数字大小
    ax.tick_params(axis='y', labelsize=fs_tick)
    ax.yaxis.grid(True, linestyle='--', which='major', color='grey', alpha=0.25)
    ax.set_axisbelow(True)
    
    ax.set_ylim(0, max([max(v) for v in data.values()]) * 1.15)

    plt.tight_layout()
    plt.show()

# ============================= 主程序 ==============================

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
    parser.add_argument(
        '--use-without-rag',
        action='store_true',
        help='使用 generated_code_without_rag 文件夹（默认使用 backup-updates-1213）'
    )
    parser.add_argument(
        '--task-order',
        type=str,
        default=None,
        help='任务（子文件夹）的绘制顺序，用逗号分隔，例如: "slice,isosurface,stream_tracing,volume_rendering"'
    )
    parser.add_argument(
        '--fontsize-title',
        type=int,
        default=32,
        help='标题字号（默认: 18）'
    )
    parser.add_argument(
        '--fontsize-label',
        type=int,
        default=24,
        help='坐标轴标签字号（默认: 15）'
    )
    parser.add_argument(
        '--fontsize-tick',
        type=int,
        default=24,
        help='坐标轴刻度标签字号（默认: 14）'
    )
    parser.add_argument(
        '--fontsize-legend',
        type=int,
        default=20,
        help='图例字号（默认: 12）'
    )
    parser.add_argument(
        '--fontsize-value',
        type=int,
        default=20,
        help='柱子数值标签字号（默认: 11）'
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
        # 默认相对路径：当前脚本的上上级目录
        current_dir = Path(__file__).parent
        if args.use_without_rag:
            root_folder = current_dir.parent / GLOBAL_DATA_SOURCE_WITHOUT_RAG
        else:
            root_folder = current_dir.parent / GLOBAL_DATA_SOURCE_WITH_RAG
    
    output_report = output_dir / f"diff_analysis_report_{GLOBAL_NAME}.txt"
    output_json = output_dir / f"diff_analysis_data_{GLOBAL_NAME}.json"
    
    print("="*80)
    print("代码修正成本自动分析工具")
    print("="*80)
    data_source = GLOBAL_DATA_SOURCE_WITHOUT_RAG if args.use_without_rag else GLOBAL_DATA_SOURCE_WITH_RAG
    print(f"数据源: {data_source}")
    print(f"扫描路径: {root_folder.resolve()}")
    print(f"输出目录: {output_dir.resolve()}")
    print()
    
    if not args.plot_only:
        print("开始扫描所有模型的生成代码...")
        print("=" * 80)
        
        # 根据数据源选择目标模型
        if args.use_without_rag:
            # generated_code_without_rag 中的模型
            target_models = GLOBAL_DEFAULT_MODELS_WITHOUT_RAG
        else:
            # 使用默认列表（来自 backup-updates-1213）
            target_models = None
        
        # 扫描所有模型
        results = scan_all_models(str(root_folder), target_models)
        
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
                # 根据数据源选择正确的模型顺序和名称映射
                if args.use_without_rag:
                    model_order = GLOBAL_MODEL_ORDER_WITHOUT_RAG
                    model_display_names = GLOBAL_MODEL_DISPLAY_NAMES_WITHOUT_RAG
                else:
                    model_order = None
                    model_display_names = None
                
                # 解析任务顺序参数
                task_order = None
                if args.task_order:
                    task_order = [t.strip() for t in args.task_order.split(',')]
                elif GLOBAL_TASK_ORDER is not None:
                    task_order = GLOBAL_TASK_ORDER
                
                plot_data, task_list = prepare_plotting_data(results, model_order, model_display_names, task_order)
                print(f"✓ 数据已提取，包含 {len(plot_data)} 个模型和 {len(task_list)} 个任务")
                print(f"  任务顺序: {task_list}")
                print("\n生成第一张图：模型成本对比...")
                # 为 without_rag 模式使用专门的颜色配置
                colors_to_use = GLOBAL_MODEL_COLORS_WITHOUT_RAG if args.use_without_rag else None
                # 需要创建显示名称到颜色的映射
                if args.use_without_rag:
                    color_mapping = {}
                    for model_name in GLOBAL_MODEL_ORDER_WITHOUT_RAG:
                        display_name = model_display_names.get(model_name, model_name)
                        color_mapping[display_name] = GLOBAL_MODEL_COLORS_WITHOUT_RAG[model_name]
                    
                    # 构建字号配置
                    fontsize_config = {}
                    if args.fontsize_title:
                        fontsize_config['title'] = args.fontsize_title
                    if args.fontsize_label:
                        fontsize_config['label'] = args.fontsize_label
                    if args.fontsize_tick:
                        fontsize_config['tick'] = args.fontsize_tick
                    if args.fontsize_legend:
                        fontsize_config['legend'] = args.fontsize_legend
                    if args.fontsize_value:
                        fontsize_config['value'] = args.fontsize_value
                    
                    plot_model_cost_comparison(plot_data, task_list, color_mapping, fontsize_config)
                else:
                    # 构建字号配置
                    fontsize_config = {}
                    if args.fontsize_title:
                        fontsize_config['title'] = args.fontsize_title
                    if args.fontsize_label:
                        fontsize_config['label'] = args.fontsize_label
                    if args.fontsize_tick:
                        fontsize_config['tick'] = args.fontsize_tick
                    if args.fontsize_legend:
                        fontsize_config['legend'] = args.fontsize_legend
                    if args.fontsize_value:
                        fontsize_config['value'] = args.fontsize_value
                    
                    plot_model_cost_comparison(plot_data, task_list, fontsize_config=fontsize_config)
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
        
        # 根据数据源选择正确的模型顺序和名称映射
        if args.use_without_rag:
            model_order = GLOBAL_MODEL_ORDER_WITHOUT_RAG
            model_display_names = GLOBAL_MODEL_DISPLAY_NAMES_WITHOUT_RAG
        else:
            model_order = None
            model_display_names = None
        
        # 解析任务顺序参数
        task_order = None
        if args.task_order:
            task_order = [t.strip() for t in args.task_order.split(',')]
        elif GLOBAL_TASK_ORDER is not None:
            task_order = GLOBAL_TASK_ORDER
        
        plot_data, task_list = prepare_plotting_data(results, model_order, model_display_names, task_order)
        print(f"✓ 已加载 {len(plot_data)} 个模型的数据")
        print(f"  任务顺序: {task_list}")
        print("\n生成图表...")
        # 为 without_rag 模式使用专门的颜色配置
        if args.use_without_rag:
            color_mapping = {}
            for model_name in GLOBAL_MODEL_ORDER_WITHOUT_RAG:
                display_name = model_display_names.get(model_name, model_name)
                color_mapping[display_name] = GLOBAL_MODEL_COLORS_WITHOUT_RAG[model_name]
            plot_model_cost_comparison(plot_data, task_list, color_mapping)
        else:
            plot_model_cost_comparison(plot_data, task_list)
    else:
        print(f"✗ 未找到缓存数据文件: {output_json}")
        print("请先运行不带 --plot-only 的命令来生成数据")
