import pandas as pd
import matplotlib.pyplot as plt
import json
from matplotlib.patches import Rectangle, ConnectionPatch
import numpy as np

import matplotlib.pyplot as plt
import numpy as np

import os
from upsetplot import from_contents, UpSet
import matplotlib.patches as mpatches  # 1. 导入模块并设置别名为 mpatches
import io
from PIL import Image, ImageDraw, ImageFont
from matplotlib.patches import Rectangle


# 保持你原有的数据读取函数不变
def read_data(file_path, sheet_name='第二期实验数据'):
    """
    读取Excel数据并解析多行数据
    """
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
    except FileNotFoundError:
        print(f"错误：找不到文件 '{file_path}'。请确保文件名和路径正确。")
        return None, None, None
    except ValueError as e:
        print(f"错误: 工作表 '{sheet_name}' 可能不存在于Excel文件中。 {e}")
        return None, None, None

    # 处理每列的多行数据
    def parse_multiline_column(series):
        parsed_data = []
        for cell in series:
            if pd.isna(cell):
                parsed_data.append([])
            else:
                # 按换行符分割，并过滤空行
                items = [item.strip() for item in str(cell).split('\n') if item.strip()]
                parsed_data.append(items)
        return parsed_data
    
    # 检查列是否存在
    required_columns = ['llm_qwen2.5_14b', 'embedding', 'ground_truth']
    for col in required_columns:
        if col not in df.columns:
            print(f"错误：Excel文件中缺少列 '{col}'。")
            return None, None, None

    # 解析三列数据
    llm_data = parse_multiline_column(df['llm_qwen2.5_14b'])
    embedding_data = parse_multiline_column(df['embedding'])
    ground_truth_data = parse_multiline_column(df['ground_truth'])
    
    # 将数据保存为JSON文件
    data_to_save = {
        'llm_qwen2.5_14b': llm_data,
        'embedding': embedding_data,
        'ground_truth': ground_truth_data
    }
    
    with open('retrieval_results.json', 'w', encoding='utf-8') as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    
    print("数据已保存到 retrieval_results.json 文件中")
    
    return llm_data, embedding_data, ground_truth_data
# ==============================================================================
# 最终方案：合并图表 + 层次化共享图例
# ==============================================================================
def create_combined_enhanced_upset_plot(llm_data, embedding_data, ground_truth_data):
    """
    将最多4个任务的Upset Plot绘制在一个2x2的大图中，并使用一个共享的、
    具有层次化颜色体系的图例。
    """
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    
    num_tasks = min(len(llm_data), 4) # 最多显示4个任务

    # --- 1. 定义新的层次化颜色体系 ---
    color_map = {
        'both_hit': '#28a745',       # 深绿: GT被两个模型共同命中
        'single_hit': '#82d99f',     # 浅绿: GT仅被一个模型命中
        'missed_gt': '#dc3545',      # 红色: GT完全未被命中
        'model_exclusive': '#6c757d' # 灰色: 模型们自己的发现 (非GT)
    }
    
    # --- 2. 创建2x2的子图网格 ---
    # figsize可以根据需要调整
    fig, axes = plt.subplots(2, 2, figsize=(20, 14))
    axes = axes.flatten() # 将2x2的axes数组展平为一维，方便遍历

    for i in range(num_tasks):
        ax = axes[i]
        contents = {
            'LLM': set(llm_data[i]),
            'Embedding': set(embedding_data[i]),
            'Ground Truth': set(ground_truth_data[i])
        }
        
        try:
            upset_data = from_contents(contents)
            if upset_data.empty:
                ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=15)
                ax.set_title(f'任务 {i+1}')
                ax.axis('off')
                continue
        except ValueError:
            ax.text(0.5, 0.5, '数据为空', ha='center', va='center', fontsize=15)
            ax.set_title(f'任务 {i+1}')
            ax.axis('off')
            continue

        # 使用UpSet类进行绘制，并指定在哪个子图(ax)上
        up = UpSet(upset_data, orientation='horizontal', sort_by='cardinality', show_counts=True)
        
        # --- 3. 根据新逻辑应用颜色 ---
        # 命中正确结果 (绿色系)
        up.style_subsets(present=["Ground Truth", "LLM", "Embedding"], facecolor=color_map['both_hit'])
        up.style_subsets(present=["Ground Truth", "LLM"], absent="Embedding", facecolor=color_map['single_hit'])
        up.style_subsets(present=["Ground Truth", "Embedding"], absent="LLM", facecolor=color_map['single_hit'])
        
        # 未命中结果 (红色)
        up.style_subsets(present="Ground Truth", absent=["LLM", "Embedding"], facecolor=color_map['missed_gt'])
        
        # 模型独有结果 (灰色)
        # 新的、修正后的代码
        # 1. 只有LLM和Embedding的交集 (不含GT)
        up.style_subsets(present=["LLM", "Embedding"], absent="Ground Truth", facecolor=color_map['model_exclusive'])
        # 2. 只有LLM (不含GT和Embedding)
        up.style_subsets(present="LLM", absent=["Embedding", "Ground Truth"], facecolor=color_map['model_exclusive'])
        # 3. 只有Embedding (不含GT和LLM)
        up.style_subsets(present="Embedding", absent=["LLM", "Ground Truth"], facecolor=color_map['model_exclusive'])

        
        # 在指定的子图上绘制
        plot_dict = up.plot(fig=fig, axes={'matrix': ax}) # 注意这里的用法
        
        # 隐藏每个子图的左侧总数条形图
        plot_dict['totals'].axis('off') 
        ax.set_title(f'任务 {i+1}')

    # 如果任务数少于4，隐藏多余的子图
    for j in range(num_tasks, 4):
        axes[j].axis('off')

    # --- 4. 创建并添加共享图例 ---
    legend_labels = {
        '共同命中 (GT)': color_map['both_hit'],
        '单独命中 (GT)': color_map['single_hit'],
        '模型独有结果 (非GT)': color_map['model_exclusive'],
        '完全未命中 (GT)': color_map['missed_gt']
    }
    patches = [mpatches.Patch(color=color, label=label) for label, color in legend_labels.items()]
    fig.legend(handles=patches, loc='upper right', bbox_to_anchor=(0.95, 0.98), title="检索结果类别", fontsize=14, title_fontsize=16)

    fig.suptitle('检索结果重叠分布对比', fontsize=24, y=1.02)
    plt.tight_layout(rect=[0, 0, 1, 0.96]) # 调整布局为总标题和图例留出空间
    
    plt.savefig('combined_retrieval_overlap.png', dpi=300, bbox_inches='tight')
    plt.show()



def create_llm_embedding_overlap_chart(llm_data, embedding_data, ground_truth_data, style_config=None):
    """
    绘制 LLM 和 Embedding 检索结果重叠分布图 (Paper Ready Version)
    配色逻辑与召回率、耗时图保持统一：
    - LLM -> 橙色系
    - Embedding -> 蓝色系
    - Both -> 绿色系 (表示最佳结果)
    """
    
    # --- 1. 样式配置 (统一主题) ---
    if style_config is None:
        style_config = {
            # 顺序: [LLM独有, Embedding独有, 共同命中, 都未命中]
            # 对应: [橙色, 深蓝, 森林绿, 浅灰]
            'colors': ['#F28E2B', '#4E79A7', '#59A14F', '#E0E0E0'], 
            'figsize': (10, 7),
            'bar_width': 0.6,
            'font_family': 'sans-serif',
            'dpi': 300
        }
    
    colors = style_config['colors']
    
    # --- 2. 数据处理 (保持不变) ---
    task_labels = ['Cutter', 'Isosurface', 'Stream Tracing', 'Volume Render']
    # 论文中的规范图例名称
    category_labels = [
        'LLM-only Hit',       # 原名: LLM-retrieval-only hit
        'Vector-only Hit',    # 原名: Similarity-retrieval-only hit
        'Both Hit',           # 原名: Both hit
        'Missed'              # 原名: Missed by both
    ]
    
    num_tasks = min(len(llm_data), len(embedding_data), len(ground_truth_data), len(task_labels))
    stats = {lab: [] for lab in category_labels}

    for i in range(num_tasks):
        llm_set = set(llm_data[i])
        emb_set = set(embedding_data[i])
        gt_set  = set(ground_truth_data[i])

        both_hits     = gt_set & llm_set & emb_set
        llm_hits      = gt_set & llm_set
        emb_hits      = gt_set & emb_set
        
        llm_only_hits = llm_hits - both_hits
        emb_only_hits = emb_hits - both_hits
        missed        = gt_set - (llm_hits | emb_hits)

        total = len(gt_set)
        if total == 0:
            for key in stats: stats[key].append(0.0)
            continue

        stats[category_labels[0]].append(len(llm_only_hits) / total * 100) # LLM only
        stats[category_labels[1]].append(len(emb_only_hits) / total * 100) # Vector only
        stats[category_labels[2]].append(len(both_hits) / total * 100)     # Both
        stats[category_labels[3]].append(len(missed) / total * 100)        # Missed

    # --- 3. 绘图 ---
    plt.rcParams['font.family'] = style_config['font_family']
    plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'SimHei']
    
    fig, ax = plt.subplots(figsize=style_config['figsize'], dpi=style_config['dpi'])
    
    indices = np.arange(num_tasks)
    width = style_config['bar_width']
    bottom = np.zeros(num_tasks)

    # 循环绘制堆叠柱
    for idx, (lab, color) in enumerate(zip(category_labels, colors)):
        vals = np.array(stats[lab])
        
        # zorder=3 确保柱子盖住网格线
        bars = ax.bar(indices, vals, width, bottom=bottom, 
                      color=color, label=lab, 
                      edgecolor='white', linewidth=0.8, zorder=3)
        
        # 添加百分比标签
        for rect, v in zip(bars, vals):
            if v >= 4.0:  # 只有大于4%才显示，避免太拥挤
                height = rect.get_height()
                # 自动调整文字颜色：深色背景用白字，浅色背景用黑字
                text_color = 'white' if idx in [1, 2] else '#333333' # 蓝色和绿色背景用白字
                if idx == 0: text_color = 'black' # 橙色背景有时候黑字更清晰，或者根据需要改白
                
                ax.text(
                    rect.get_x() + rect.get_width() / 2, 
                    rect.get_y() + height / 2,
                    f'{v:.1f}%', 
                    ha='center', va='center', 
                    fontsize=10, color=text_color, fontweight='medium'
                )
        
        bottom += vals

    # --- 4. 样式美化 (Clean Layout) ---
    
    # 标题
    ax.set_title('Distribution of Retrieval Results on Ground Truth', 
                 fontsize=16, fontweight='bold', pad=25)
    
    # X轴
    ax.set_xticks(indices)
    ax.set_xticklabels(task_labels, fontsize=12, fontweight='medium')
    
    # Y轴
    ax.set_ylabel('Percentage of Ground Truth (%)', fontsize=12)
    ax.set_ylim(0, 100)
    ax.tick_params(axis='y', labelsize=11)
    
    # 网格线 (底层虚线)
    ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
    
    # 去除多余边框
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(1.0)
    ax.spines['bottom'].set_linewidth(1.0)

    # 图例 (顶部一排)
    # 调整图例顺序使其符合逻辑 (可选)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels,
              loc='upper center', 
              bbox_to_anchor=(0.5, 1.1), # 在标题下方，图表上方
              ncol=4,                    # 一行显示
              frameon=False, 
              fontsize=11)

    plt.tight_layout()
    plt.savefig('overlap_distribution_unified.png', bbox_inches='tight', dpi=300)
    plt.show()

# 调用示例
if __name__ == "__main__":
    # 假设你已经读取了数据
    # create_llm_embedding_overlap_chart(llm_data, embedding_data, ground_truth_data)
    pass

def main():
    # 确保中文字体能正确显示
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False

    import os
    file_path = os.path.join(os.path.dirname(__file__), "res2.xlsx")
    if not os.path.exists(file_path):
        print(f"错误: 文件 '{file_path}' 不在当前目录中。")
        return

    llm_data, embedding_data, ground_truth_data = read_data(file_path)
    
    # 检查数据是否成功加载
    if llm_data is None:
        print("数据加载失败，程序终止。")
        return

    print("数据加载成功，开始生成图表...")

    create_llm_embedding_overlap_chart(llm_data, embedding_data, ground_truth_data)

    # =========================================================
    # 调用新的可视化函数，你可以选择性地注释掉不想用的那个
    # =========================================================

    # 方案一：生成Upset Plot (推荐)
    # print("\n正在生成 Upset Plots...")
    # create_upset_plots(llm_data, embedding_data, ground_truth_data)
    # create_enhanced_upset_plots(llm_data, embedding_data, ground_truth_data)
    # create_combined_enhanced_upset_plot(llm_data, embedding_data, ground_truth_data) 
    # create_individual_hierarchical_plots(llm_data, embedding_data, ground_truth_data)
    # create_composite_upset_plot(llm_data, embedding_data, ground_truth_data)
    # create_partition_plots(llm_data, embedding_data, ground_truth_data)
    
    # 方案二：生成分组条形图
    # print("\n正在生成分组条形图...")
    # create_grouped_bar_chart(llm_data, embedding_data, ground_truth_data)
    
    print("\n图表已生成并保存到当前目录。")

if __name__ == "__main__":
    main()