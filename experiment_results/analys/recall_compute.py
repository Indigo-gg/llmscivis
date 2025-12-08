import json
import matplotlib.pyplot as plt
import numpy as np
import os

# ==========================================
# 1. 核心计算逻辑 (保持不变)
# ==========================================
def calculate_recall(retrieved_list, ground_truth_list):
    """计算单个任务的召回率"""
    retrieved_set = set(retrieved_list)
    ground_truth_set = set(ground_truth_list)
    
    if not ground_truth_set:
        return 0.0
        
    retrieved_relevant = len(retrieved_set.intersection(ground_truth_set))
    total_relevant = len(ground_truth_set)
    
    return retrieved_relevant / total_relevant

def get_recall_data(json_file_path):
    """从JSON读取数据并计算所有召回率"""
    if not os.path.exists(json_file_path):
        print(f"Error: File {json_file_path} not found.")
        return None

    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    ground_truth = data.get('ground_truth', [])
    methods_data = {}
    
    # 遍历JSON中的键，排除ground_truth
    for key, val in data.items():
        if key != 'ground_truth':
            recalls = []
            for i in range(len(ground_truth)):
                # 容错处理：防止索引越界
                gt_item = ground_truth[i] if i < len(ground_truth) else []
                res_item = val[i] if i < len(val) else []
                recalls.append(calculate_recall(res_item, gt_item))
            methods_data[key] = recalls
            
    return methods_data

# ==========================================
# 2. 论文级可视化函数 (重构部分)
# ==========================================
def plot_paper_ready_recall(json_file_path='retrieval_results.json'):
    
    # --- 配置参数 ---
    # 定义显示名称映射 (将代码变量名转换为论文术语)
    name_mapping = {
        'llm_qwen2.5_14b': 'LLM-driven',
        'embedding': 'Vector-based',
        'ground_truth': 'Ground Truth'
    }
    
    # 定义任务名称 (X轴)
    task_labels = ['Cutter', 'Isosurface', 'Stream Tracing', 'Volume Render']
    
    # 学术配色方案 (稳重风格)
    # 方案 A (蓝/红): ['#4E79A7', '#F28E2B'] 
    # 方案 B (蓝/灰): ['#2C3E50', '#95A5A6']
    # 这里使用方案 A，对比度好且经典
    colors = ['#F28E2B', '#4E79A7']  
    
    # --- 数据准备 ---
    methods_data = get_recall_data(json_file_path)
    if not methods_data:
        return

    # 提取方法名称（排序以确保每次运行颜色一致）
    method_keys = sorted(methods_data.keys()) 
    # 确保 'embedding' (Vector-based) 在后，或者根据你论文想强调的顺序调整
    # 这里我们强制把 'embedding' 放在后面作为对比优胜者
    if 'llm_qwen2.5_14b' in method_keys and 'embedding' in method_keys:
        method_keys = ['llm_qwen2.5_14b', 'embedding']

    num_tasks = len(task_labels)
    x = np.arange(num_tasks)
    
    # 设置柱状图宽度
    total_width = 0.7
    bar_width = total_width / len(method_keys)

    # --- 开始绘图 ---
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'SimHei'] # 兼顾中英文
    
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

    for i, method in enumerate(method_keys):
        recalls = methods_data[method]
        # 截断或填充数据以匹配任务数
        recalls = recalls[:num_tasks] + [0]*(num_tasks - len(recalls))
        
        # 计算偏移量
        offset = (i - len(method_keys)/2 + 0.5) * bar_width
        
        # 获取显示名称
        display_name = name_mapping.get(method, method)
        
        # 绘制柱子
        bars = ax.bar(x + offset, recalls, bar_width, 
                      label=display_name, 
                      color=colors[i % len(colors)], 
                      edgecolor='white', linewidth=0.8,
                      zorder=3) # zorder=3 保证柱子在网格线之上
        
        # 添加数值标签
        for rect in bars:
            height = rect.get_height()
            if height > 0:
                ax.text(rect.get_x() + rect.get_width()/2., height + 0.01,
                        f'{height:.2f}',
                        ha='center', va='bottom', fontsize=10, color='#333333')

    # --- 样式美化 (关键步骤) ---
    
    # 1. 标题与轴标签
    ax.set_title('Recall Comparison across Visualization Tasks', fontsize=16, fontweight='bold', pad=20)
    ax.set_ylabel('Recall Rate', fontsize=14)
    # ax.set_xlabel('Tasks', fontsize=14) # X轴标签有时可以省略，因为刻度已经很清楚
    
    # 2. X轴刻度
    ax.set_xticks(x)
    ax.set_xticklabels(task_labels, fontsize=12, fontweight='medium')
    
    # 3. Y轴范围与网格
    ax.set_ylim(0, 1.15) # 留出空间给标签
    ax.set_yticks(np.arange(0, 1.1, 0.2))
    ax.tick_params(axis='y', labelsize=11)
    ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0) # 网格线虚化并置于底层
    
    # 4. 去除多余边框 (Clean Layout)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(1.0)
    ax.spines['bottom'].set_linewidth(1.0)
    
    # 5. 图例设置 (顶部居中，无边框)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.0), 
              ncol=len(method_keys), frameon=False, fontsize=12)

    plt.tight_layout()
    
    # 保存与显示
    output_filename = 'recall_comparison_paper.png'
    plt.savefig(output_filename, bbox_inches='tight', dpi=300)
    print(f"图表已生成: {output_filename}")
    plt.show()

# ==========================================
# 3. 主程序入口
# ==========================================
if __name__ == "__main__":
    # 确保当前目录下有 retrieval_results.json
    # 如果没有，你可以先运行之前的 read_data 函数生成该文件
    plot_paper_ready_recall()