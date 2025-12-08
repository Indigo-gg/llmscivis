"""

iosurface:
qwen-plus:总差异行数: 71,  新增行数: 38,  删除行数: 33			
chatgpt-4o  总差异行数: 56
  新增行数: 28
  删除行数: 28			 
  
  chatgpt-4o-without-rag   
总差异行数: 94
  新增行数: 38
  删除行数: 56		



qwen-plus:总差异行数: 46,新增行数: 21,  删除行数: 25			chatgpt-4o  总差异行数: 3
  新增行数: 2
  删除行数: 1			 chatgpt-4o-without-rag 
 总差异行数: 29
  新增行数: 13
  删除行数: 16		

																	

"""


import matplotlib.pyplot as plt
import numpy as np

# 设置全局字体，防止中文乱码 (如果是在Windows上运行，通常用SimHei; Mac/Linux可能需要调整)
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial', 'sans-serif'] 
plt.rcParams['axes.unicode_minus'] = False

def plot_rag_impact_comparison():
    """
    生成第一张图：RAG 工作流对代码修正成本（行数差异）的影响
    """
    # 1. 准备数据 (根据原图图片上的数字提取)
    tasks = ["Cutter", "Isosurface", "Stream Tracing", "Volume Rendering"]
    
    # 数据格式：[Task1, Task2, Task3, Task4]
    data = {
        "ChatGPT-4o":               [3, 56, 21, 3],
        "ChatGPT-4o (No RAG)":      [29, 94, 76, 7],
        "DeepSeek-v3.1":            [4, 26, 23, 3],
        "DeepSeek-v3.1 (No RAG)":   [47, 31, 20, 41]
    }

    # 2. 设置配色 (优化版：同色系对比)
    # 使用 Teals (青色系) 代表 ChatGPT, Oranges (橙色系) 代表 DeepSeek
    # 深色代表 "No RAG" (通常成本高，警示色)，浅色代表 "With RAG" (优化后)
    colors = {
        "ChatGPT-4o":             "#4DBBD5", # 较亮青色
        "ChatGPT-4o (No RAG)":    "#296D7D", # 深青色
        "DeepSeek-v3.1":          "#F4A582", # 较亮橙色
        "DeepSeek-v3.1 (No RAG)": "#CA5D2A"  # 深橙色
    }

    # 3. 绘图参数设置
    x = np.arange(len(tasks))
    width = 0.18  # 每个柱子的宽度
    multiplier = 0 # 用于计算偏移量

    fig, ax = plt.subplots(figsize=(14, 7), dpi=120)

    # 4. 循环绘制柱状图
    for attribute, measurement in data.items():
        offset = width * multiplier
        rects = ax.bar(x + offset, measurement, width, label=attribute, color=colors[attribute], edgecolor='white', linewidth=0.5)
        
        # 添加柱子顶部的数值标签
        ax.bar_label(rects, padding=3, fontsize=9, color='#333333')
        multiplier += 1

    # 5. 装饰图表
    # 调整 X 轴标签位置居中
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(tasks, fontsize=11)
    
    # 标题和标签
    ax.set_ylabel('Total Lines of Difference (Correction Cost)', fontsize=12, labelpad=10)
    ax.set_xlabel('Task Type', fontsize=12, labelpad=10)
    ax.set_title('Impact of RAG Workflow on Code Correction Costs', fontsize=16, pad=20, weight='bold')

    # 图例设置
    ax.legend(loc='upper left', frameon=True, fancybox=True, shadow=True, fontsize=10)
    
    # 设置Y轴网格线
    ax.yaxis.grid(True, linestyle='--', which='major', color='grey', alpha=0.25)
    ax.set_axisbelow(True) # 让网格线在柱子后面

    # 调整Y轴上限，留出空间给标签
    ax.set_ylim(0, 110)

    plt.tight_layout()
    plt.show()

def plot_model_cost_comparison():
    """
    生成第二张图：不同模型在四个任务下的修正成本对比
    """
    # 1. 准备数据
    tasks = ["Cutter", "Isosurface", "Stream Tracing", "Volume Rendering"]
    
    data = {
        "Qwen-Plus":       [46, 71, 87, 20],
        "ChatGPT-4o":      [3, 56, 21, 3],
        "DeepSeek-v3.1":   [4, 26, 23, 3],
        "Claude-Sonnet-4": [11, 48, 30, 1]
    }

    # 2. 设置配色 (优化版：现代柔和对比色)
    # 选用区分度高但视觉舒适的颜色
    colors = [
        "#FF8080", # Qwen: 柔和红
        "#4DBBD5", # GPT: 柔和青 (保持与上一张图一致的识别度)
        "#F4A582", # DeepSeek: 柔和橙 (保持一致)
        "#9575CD"  # Claude: 柔和紫
    ]

    # 3. 绘图参数
    x = np.arange(len(tasks))
    width = 0.18
    multiplier = 0

    fig, ax = plt.subplots(figsize=(14, 7), dpi=120)

    # 4. 循环绘制
    for i, (attribute, measurement) in enumerate(data.items()):
        offset = width * multiplier
        rects = ax.bar(x + offset, measurement, width, label=attribute, color=colors[i], edgecolor='white', linewidth=0.5)
        ax.bar_label(rects, padding=3, fontsize=9, color='#333333')
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
    
    ax.set_ylim(0, 100)

    plt.tight_layout()
    plt.show()

# 运行绘图函数
if __name__ == "__main__":
    print("生成 RAG 影响对比图...")
    plot_rag_impact_comparison()
    
    print("生成模型成本对比图...")
    plot_model_cost_comparison()