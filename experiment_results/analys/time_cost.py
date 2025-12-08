import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import ScalarFormatter

def plot_log_scale_time():
    # 数据与配置保持不变...
    task_labels = ['Cutter', 'Isosurface', 'Stream Tracing', 'Volume Render']
    sim_method = [0.19, 0.18, 0.10, 0.17]
    lm_method  = [7.90, 7.45, 7.90, 7.46]
    colors = ['#4E79A7', '#F28E2B'] 
    labels = ['Vector-based Approach', 'LLM-driven Approach']
    
    x = np.arange(len(task_labels))
    width = 0.35

    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'SimHei']
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

    # --- 关键修改：设置 Y 轴为对数刻度 ---
    ax.set_yscale('log')
    
    bars1 = ax.bar(x - width/2, sim_method, width, label=labels[0], color=colors[0], edgecolor='white', zorder=3)
    bars2 = ax.bar(x + width/2, lm_method,  width, label=labels[1], color=colors[1], edgecolor='white', zorder=3)

    # --- 美化细节 ---
    ax.set_title('Time Efficiency (Logarithmic Scale)', fontsize=16, fontweight='bold', pad=20)
    ax.set_ylabel('Time (seconds) - Log Scale', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(task_labels, fontsize=12)
    
    # 强制设置对数刻度的显示方式，使其更易读
    ax.set_yticks([0.1, 1, 10])
    ax.get_yaxis().set_major_formatter(ScalarFormatter()) # 显示数字而不是 10^0
    ax.set_ylim(0.05, 15) # 调整范围以适应标签

    ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.05), ncol=2, frameon=False, fontsize=12)

    # 数值标注 (不用改，直接标)
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.1, # 稍微高一点
                f'{bar.get_height():.2f}s', ha='center', va='bottom', fontsize=10)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.05,
                f'{bar.get_height():.2f}s', ha='center', va='bottom', fontsize=10)

    plt.savefig('time_comparison_log.png', bbox_inches='tight', dpi=300)
    plt.show()

plot_log_scale_time()