"""
快速绘制检索对比图表
根据JSON文件直接生成两个关键图表：
1. 覆盖率对比图（覆盖率 + 模块占比）
2. 时间成本对比图（关键词检索 vs LLM检索）
"""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 中文字体设置
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def load_json_data(json_file):
    """加载JSON数据"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except UnicodeDecodeError:
        with open(json_file, 'r', encoding='gbk') as f:
            return json.load(f)

def plot_coverage_and_ratio(data, output_file):
    """绘制交集占并集的比例 (Jaccard 相似度)"""
    detailed_results = data['detailed_results']
    
    # 按照指定顺序排列任务
    task_order = ['slice', 'isosurface', 'streamline', 'volume_rendering']
    
    tasks = []
    jaccard_scores = []
    
    for task_name in task_order:
        if task_name not in detailed_results:
            continue
        task_data = detailed_results[task_name]
        tasks.append(task_name.upper())
        module_analysis = task_data['module_analysis']
        # Jaccard 相似度 = 交集 / 并集
        overlap_count = module_analysis['overlap_count']
        keyword_aware_count = module_analysis['keyword_aware_modules_count']
        llm_count = module_analysis['llm_modules_count']
        union_count = keyword_aware_count + llm_count - overlap_count
        jaccard = (overlap_count / union_count * 100) if union_count > 0 else 0
        jaccard_scores.append(jaccard)
    
    fig, ax = plt.subplots(figsize=(12, 6), dpi=100)
    x = np.arange(len(tasks))
    width = 0.6
    
    bars = ax.bar(x, jaccard_scores, width, label='Jaccard 相似度 (交集/并集)', 
                   color='#4E79A7', alpha=0.8, edgecolor='black', linewidth=1.5)
    
    # 添加数值标签
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height + 1.5,
                   f'{height:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    ax.set_xlabel('任务名称', fontsize=12, fontweight='bold')
    ax.set_ylabel('相似度 (%)', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.set_ylim(0, 80)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.legend(fontsize=11, loc='upper right')
    ax.set_title('检索结果重合度对比 (Jaccard 相似度)', fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.show()
    plt.savefig(output_file, dpi=100, bbox_inches='tight')
    print(f"✓ 重合度对比图已保存：{output_file}")
    plt.close()

def plot_time_comparison(data, output_file):
    """绘制时间成本对比图（只保留时间对比，无加速比）"""
    detailed_results = data['detailed_results']
    
    # 按照指定顺序排列任务
    task_order = ['slice', 'isosurface', 'streamline', 'volume_rendering']
    
    tasks = []
    kw_times = []
    llm_times = []
    
    for task_name in task_order:
        if task_name not in detailed_results:
            continue
        task_data = detailed_results[task_name]
        tasks.append(task_name.upper())
        time_analysis = task_data['time_analysis']
        kw_times.append(time_analysis['keyword_aware_time_seconds'] or 0)
        llm_times.append(time_analysis['llm_time_seconds'] or 0)
    
    fig, ax = plt.subplots(figsize=(12, 6), dpi=100)
    x = np.arange(len(tasks))
    width = 0.35
    
    # 柱状图：时间成本对比
    bars1 = ax.bar(x - width/2, kw_times, width, label='关键词检索(keyword-aware)', 
                   color='#4E79A7', alpha=0.8, edgecolor='black', linewidth=1.5)
    bars2 = ax.bar(x + width/2, llm_times, width, label='LLM直接检索', 
                   color='#F28E2B', alpha=0.8, edgecolor='black', linewidth=1.5)
    
    # 添加数值标签
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.2f}s', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    ax.set_xlabel('任务名称', fontsize=12, fontweight='bold')
    ax.set_ylabel('时间成本 (秒)', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.legend(fontsize=11, loc='upper left')
    ax.set_title('检索时间成本对比分析', fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.show()
    plt.savefig(output_file, dpi=100, bbox_inches='tight')
    print(f"✓ 时间对比图已保存：{output_file}")
    plt.close()

def generate_comparison_table(data, output_file):
    """生成对比表格：大模型检索、模块检索、共同结果及耗时"""
    detailed_results = data['detailed_results']
    
    # 按照指定顺序排列任务
    task_order = ['slice', 'isosurface', 'streamline', 'volume_rendering']
    
    table_data = []
    
    for task_name in task_order:
        if task_name not in detailed_results:
            continue
        task_data = detailed_results[task_name]
        module_analysis = task_data['module_analysis']
        time_analysis = task_data['time_analysis']
        
        llm_modules = module_analysis.get('llm_modules', [])
        keyword_aware_modules = module_analysis.get('keyword_aware_modules', [])
        overlap_modules = module_analysis.get('overlap_modules', [])
        kw_time = time_analysis['keyword_aware_time_seconds']
        llm_time = time_analysis['llm_time_seconds']
        
        # 计算 Jaccard 相似度
        overlap_count = module_analysis['overlap_count']
        keyword_aware_count = module_analysis['keyword_aware_modules_count']
        llm_count = module_analysis['llm_modules_count']
        union_count = keyword_aware_count + llm_count - overlap_count
        jaccard = (overlap_count / union_count * 100) if union_count > 0 else 0
        
        table_data.append({
            '任务名称': task_name.upper(),
            'LLM耗时(s)': f"{llm_time:.2f}" if llm_time else 'N/A',
            '大模型检索结果': ', '.join(llm_modules) if llm_modules else '',
            '关键词耗时(s)': f"{kw_time:.3f}" if kw_time else 'N/A',
            '模块感知检索结果': ', '.join(keyword_aware_modules) if keyword_aware_modules else '',
            '共同模块': ', '.join(overlap_modules) if overlap_modules else '',
            'Jaccard相似度(%)': f"{jaccard:.2f}"
        })
    
    df = pd.DataFrame(table_data)
    
    print("\n📋 检索对比表格预览（按照顺序 [SLICE, ISOSURFACE, STREAMLINE, VOLUME_RENDERING]）：")
    print("="*150)
    print(df.to_string(index=False))
    print("="*150)
    
    # 保存为CSV
    csv_file = str(output_file).replace('.csv', '')
    df.to_csv(f"{csv_file}.csv", index=False, encoding='utf-8-sig')
    print(f"✓ 对比表格已保存（CSV）：{csv_file}.csv")
    
    # 保存为Excel
    try:
        df.to_excel(f"{csv_file}.xlsx", index=False, sheet_name='检索对比')
        print(f"✓ 对比表格已保存（Excel）：{csv_file}.xlsx")
    except Exception as e:
        print(f"⚠️  Excel保存失败: {e}")

def main():
    """主函数"""
    # 定位JSON文件
    analys_dir = Path(__file__).parent
    json_file = analys_dir / 'deepseek_v3_12-19_retrieval_comparison_result_detailed.json'
    
    if not json_file.exists():
        print(f"❌ 找不到JSON文件: {json_file}")
        return
    
    print("📊 开始生成检索对比结果...\n")
    
    # 加载数据
    data = load_json_data(json_file)
    
    # 绘制覆盖率对比图
    plot_coverage_and_ratio(data, str(analys_dir / 'coverage_comparison.png'))
    
    # 绘制时间成本对比图
    plot_time_comparison(data, str(analys_dir / 'time_cost_comparison.png'))
    
    # 生成对比表格
    generate_comparison_table(data, str(analys_dir / 'retrieval_comparison_table'))
    
    print("\n✅ 所有输出已生成完成！")
    print(f"   • coverage_comparison.png - 重合度对比图（Jaccard相似度：交集/并集）")
    print(f"   • time_cost_comparison.png - 时间成本对比图")

    print(f"   • retrieval_comparison_table.csv - 对比表格（CSV格式）")
    print(f"   • retrieval_comparison_table.xlsx - 对比表格（Excel格式）")

if __name__ == '__main__':
    main()
