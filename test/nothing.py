import matplotlib.pyplot as plt
import numpy as np

tasks = ['Task 1', 'Task 2', 'Task 3', 'Task 4']
sim_method = [0.19, 0.18, 0.10, 0.17]
lm_method  = [7.90, 7.45, 7.90, 7.46]

x = np.arange(len(tasks))
width = 0.35

fig, ax = plt.subplots(figsize=(8, 5))
bars1 = ax.bar(x - width/2, sim_method, width, label='Semantic Similarity Matching', color='#4C72B0')
bars2 = ax.bar(x + width/2, lm_method,  width, label='LLM-based Semantic Retrieval', color='#55A868')

ax.set_xticks(x)
ax.set_xticklabels(tasks)
ax.set_ylabel('Time (seconds)')
ax.set_title('Time Comparison of Two Methods on Four Tasks')

# 调整图例位置到右上角
ax.legend(loc='upper right')

# 为基于语义相似度匹配的方法添加数值标注
for bar in bars1:
    ax.annotate(f'{bar.get_height():.2f}',
                (bar.get_x() + bar.get_width()/2, bar.get_height()),
                ha='center', va='bottom', fontsize=9)

# 为大模型直接语义检索的方法添加数值标注
for bar in bars2:
    ax.annotate(f'{bar.get_height():.2f}',
                (bar.get_x() + bar.get_width()/2, bar.get_height()),
                ha='center', va='bottom', fontsize=9)

# 调整y轴范围，使柱体高度更协调
ax.set_ylim(0, 10)

plt.tight_layout()
plt.savefig('task_time_comparison.png')
plt.show()