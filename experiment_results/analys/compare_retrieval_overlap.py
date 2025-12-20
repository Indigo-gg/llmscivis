"""
对比检索结果重合度和时间成本分析脚本

主要功能：
1. 对比模块感知的关键词检索和LLM直接检索的结果
2. 分析时间成本差异
3. 计算检索结果重合度（相似度）
4. 绘制对比图表（时间、重合度、模块分布）
"""

import json
import os
from pickle import GLOBAL
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as mpatches
from collections import defaultdict, Counter

# 中文字体设置
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

GLOBAL_VARIABLE = 'deepseek_v3_12-19'
class RetrievalComparisonAnalyzer:
    """检索结果对比分析器
    
    对比【模块感知的关键词检索】vs【LLM直接检索】的结果
    - 模块感知的关键词检索（keyword-aware）：从 case_export_data.json 的 retrieval_results 字段提取
    - LLM直接检索：从 retrieval_results_with_time.json 的 retrieved_modules 字段提取
    """
    
    def __init__(self):
        """初始化分析器"""
        self.keyword_aware_results = {}  # 模块感知的关键词检索结果
        self.llm_results = {}            # LLM直接检索结果
        self.comparison_data = {}
        
    def parse_llm_retrieval_results(self, json_path: str = None) -> Dict:
        """
        从retrieval_results_with_time.json文件中解析【LLM直接检索结果】
        
        JSON结构示例：
        {
          "results": [
            {
              "task": "slice",
              "query": "...",
              "retrieved_modules": ["Filter-ImageSlice", ...],
              "elapsed_time": 15.85,
              "timestamp": "2025-12-19 14:26:22"
            },
            ...
          ]
        }
        """
        results = {}
        
        # 如果没有提供路径，使用默认路径
        if json_path is None:
            json_path = Path(__file__).parent.parent.parent / 'retrieval_results_with_time.json'
        else:
            json_path = Path(json_path)
        
        if not json_path.exists():
            print(f"⚠️ 文件不存在: {json_path}")
            return results
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 遍历results中的每个查询结果
            query_results = data.get('results', [])
            
            for idx, result in enumerate(query_results):
                # 直接从task字段获取任务名称
                task_name = result.get('task', f'task_{idx}')
                query = result.get('query', '')
                modules = result.get('retrieved_modules', [])
                elapsed_time = result.get('elapsed_time', 0)
                
                results[task_name] = {
                    'time': elapsed_time,
                    'modules': modules,
                    'module_count': len(modules),
                    'query': query[:100]  # 保存query前100个字符
                }
            
            print(f"✓ 成功从 {json_path} 加载了 {len(results)} 个任务的检索结果")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析错误: {e}")
        except Exception as e:
            print(f"❌ 读取文件错误: {e}")
        
        return results
    
    def parse_keyword_aware_retrieval_results(self, export_dir: Path) -> Dict:
        """
        从generated_code_without_rag\gpt_5_with_rag目录中解析【模块感知的关键词检索结果】
        
        遍历各个任务目录，读取case_export_data.json中的retrieval_results字段
        这是基于关键词和模块信息的结构化检索结果
        支持从title字段和metadata中的retrieval_time_seconds提取信息
        """
        results = {}
        
        # 遍历各个任务目录（与JSON中的task字段保持一致）
        task_dirs = ['slice', 'isosurface', 'streamline', 'volume_rendering', 
                     'cutter', 'stream_tracing', 'streamtracing']
        
        for task_dir_name in task_dirs:
            task_path = export_dir / task_dir_name
            
            if not task_path.exists():
                continue
            
            # 尝试读取case_export_data.json
            json_path = task_path / 'case_export_data.json'
            
            if json_path.exists():
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    # 解析retrieval_results中的模块信息
                    retrieval_results = data.get('retrieval_results', [])
                    modules = []
                    titles = []  # 新增：提取title字段
                    
                    # 确保retrieval_results是列表
                    if not isinstance(retrieval_results, list):
                        print(f"⚠️ retrieval_results不是列表类型，在{task_path}中")
                        retrieval_results = []
                    
                    # 从retrieval_results提取模块信息
                    for item in retrieval_results:
                        if isinstance(item, dict):
                            # 优先使用 title 字段（新增逻辑）
                            title = item.get('title', '')
                            if title:
                                modules.append(title)
                                titles.append(title)
                            else:
                                # 降级方案：从file_path提取
                                file_path = item.get('file_path', '')
                                if file_path:
                                    import re
                                    match = re.search(r'([A-Z][a-zA-Z]+-[A-Za-z]+)', file_path)
                                    if match:
                                        module_name = match.group(1)
                                        modules.append(module_name)
                    
                    # 使用直接的任务名称（与JSON中的task字段一致）
                    task_name = task_dir_name
                    
                    # 去重和清理
                    modules = list(set([m.strip() for m in modules if isinstance(m, str) and m.strip()]))
                    
                    # 新增：从metadata中提取检索耗时
                    retrieval_time = None
                    metadata = data.get('metadata', {})
                    if isinstance(metadata, dict):
                        retrieval_time = metadata.get('retrieval_time_seconds')
                    
                    results[task_name] = {
                        'time': retrieval_time,  # 从metadata中提取的实际耗时
                        'modules': modules,  # 去重后的模块列表
                        'module_count': len(modules),
                        'retrieval_count': len(retrieval_results),
                        'titles': titles,  # 新增：保存所有title
                        'raw_retrieval_results': retrieval_results  # 保存原始数据供后续分析
                    }
                    
                    # 打印调试信息
                    time_str = f" (耗时: {retrieval_time}s)" if retrieval_time else ""
                    if modules:
                        print(f"  从{task_name}中找到{len(modules)}个模块（总计{len(retrieval_results)}条检索结果）{time_str}")
                    
                except Exception as e:
                    print(f"❌ 解析{json_path}失败: {e}")
                    import traceback
                    traceback.print_exc()
        
        return results
    
    def calculate_overlap(self, keyword_aware_modules: List[str], llm_modules: List[str]) -> Dict:
        """
        计算两个模块列表的重合度
        
        返回：
        - overlap: 重合的模块
        - overlap_rate: 重合率 (重合数 / 并集数)
        - similarity: 相似度 (重合数 / keyword_aware检索数)
        """
        keyword_aware_set = set([m.lower().strip() for m in keyword_aware_modules])
        llm_set = set([m.lower().strip() for m in llm_modules])
        
        if not keyword_aware_set or not llm_set:
            return {
                'overlap': [],
                'overlap_count': 0,
                'overlap_rate': 0.0,
                'keyword_aware_only': list(keyword_aware_set),
                'llm_only': list(llm_set),
                'similarity': 0.0
            }
        
        overlap = keyword_aware_set & llm_set
        union = keyword_aware_set | llm_set
        keyword_aware_only = keyword_aware_set - llm_set
        llm_only = llm_set - keyword_aware_set
        
        # 重合率 (Jaccard相似度)
        overlap_rate = len(overlap) / len(union) if union else 0.0
        # 相似度 (keyword_aware检索结果中被LLM覆盖的比例)
        similarity = len(overlap) / len(keyword_aware_set) if keyword_aware_set else 0.0
        
        return {
            'overlap': list(overlap),
            'overlap_count': len(overlap),
            'overlap_rate': overlap_rate,
            'keyword_aware_only': list(keyword_aware_only),
            'llm_only': list(llm_only),
            'similarity': similarity,
            'keyword_aware_count': len(keyword_aware_set),
            'llm_count': len(llm_set),
            'union_count': len(union)
        }
    
    def analyze(self, json_path: str = None, export_dir: Path = None) -> Dict:
        """执行完整的对比分析
        
        Args:
            json_path: retrieval_results_with_time.json 路径（LLM直接检索）
            export_dir: case_export_data.json 所在目录（模块感知的关键词检索）
        """
        
        # 解析两个数据源
        self.llm_results = self.parse_llm_retrieval_results(json_path)
        if export_dir:
            self.keyword_aware_results = self.parse_keyword_aware_retrieval_results(export_dir)
        
        # 对比分析
        self.comparison_data = {}
        
        # 规范化任务名称用于匹配
        def normalize_name(name):
            return name.lower().replace('_', '').replace('-', '').replace(' ', '')
        
        keyword_aware_norm = {normalize_name(k): k for k in self.keyword_aware_results.keys()}
        llm_norm = {normalize_name(k): k for k in self.llm_results.keys()}
        
        # 合并所有任务
        all_tasks = set(keyword_aware_norm.keys()) | set(llm_norm.keys())
        
        for task_norm in all_tasks:
            task_key = task_norm
            
            keyword_aware_key = keyword_aware_norm.get(task_norm)
            llm_key = llm_norm.get(task_norm)
            
            keyword_aware_data = self.keyword_aware_results.get(keyword_aware_key, {}) if keyword_aware_key else {}
            llm_data = self.llm_results.get(llm_key, {}) if llm_key else {}
            
            # 计算重合度
            keyword_aware_modules = keyword_aware_data.get('modules', [])
            llm_modules = llm_data.get('modules', [])
            
            overlap_analysis = self.calculate_overlap(keyword_aware_modules, llm_modules)
            
            self.comparison_data[task_key] = {
                'keyword_aware': keyword_aware_data,
                'llm': llm_data,
                'overlap': overlap_analysis,
                'display_name': keyword_aware_key or llm_key or task_key
            }
        
        return self.comparison_data
    
    def print_summary(self):
        """打印对比摘要"""
        print("\n" + "="*80)
        print("【检索结果对比分析摘要】")
        print("对比：模块感知的关键词检索(keyword-aware) vs LLM直接检索")
        print("="*80)
        
        for task_key, data in self.comparison_data.items():
            display_name = data['display_name']
            keyword_aware = data['keyword_aware']
            llm = data['llm']
            overlap = data['overlap']
            
            print(f"\n📌 {display_name.upper()}")
            print("-" * 60)
            
            # 时间对比（包括新提取的耗时数据）
            keyword_aware_time = keyword_aware.get('time')
            llm_time = llm.get('time')
            
            print(f"\n  ⏱️  时间成本对比:")
            if keyword_aware_time:
                print(f"     • 关键词检索（keyword-aware）: {keyword_aware_time:.2f}s")
            else:
                print(f"     • 关键词检索（keyword-aware）: N/A")
            if llm_time:
                print(f"     • LLM直接检索: {llm_time:.2f}s")
            else:
                print(f"     • LLM直接检索: N/A")
            
            # 时间对比分析
            if keyword_aware_time and llm_time:
                diff = abs(llm_time - keyword_aware_time)
                percent = (diff / min(keyword_aware_time, llm_time)) * 100 if min(keyword_aware_time, llm_time) > 0 else 0
                if llm_time > keyword_aware_time:
                    print(f"     • LLM方法慢 {diff:.2f}s ({percent:.1f}%)")
                else:
                    print(f"     • 关键词方法慢 {diff:.2f}s ({percent:.1f}%)")
            
            # 模块对比
            keyword_aware_count = keyword_aware.get('module_count', 0)
            llm_count = llm.get('module_count', 0)
            overlap_count = overlap.get('overlap_count', 0)
            similarity = overlap.get('similarity', 0.0)
            overlap_rate = overlap.get('overlap_rate', 0.0)
            
            print(f"\n  🧩 模块统计:")
            print(f"     • 关键词检索: {keyword_aware_count} 个模块")
            print(f"     • LLM直接检索: {llm_count} 个模块")
            print(f"     • 重合模块: {overlap_count} 个")
            print(f"     • 覆盖率: {similarity*100:.1f}% (LLM覆盖关键词结果的比例)")
            print(f"     • 重合率: {overlap_rate*100:.1f}% (Jaccard相似度)")
            
            # 独有模块
            keyword_aware_only = overlap.get('keyword_aware_only', [])
            llm_only = overlap.get('llm_only', [])
            
            if keyword_aware_only:
                print(f"\n  🔴 关键词检索独有模块 ({len(keyword_aware_only)}):")
                for m in keyword_aware_only[:5]:
                    print(f"     - {m}")
                if len(keyword_aware_only) > 5:
                    print(f"     ... 还有 {len(keyword_aware_only)-5} 个")
            
            if llm_only:
                print(f"\n  🟢 LLM检索独有模块 ({len(llm_only)}):")
                for m in llm_only[:5]:
                    print(f"     - {m}")
                if len(llm_only) > 5:
                    print(f"     ... 还有 {len(llm_only)-5} 个")
    
    def plot_time_comparison(self, output_file='retrieval_time_comparison.png'):
        """绘制时间成本对比图 - 包括两种检索方法的耗时对比和效率分析"""
        
        # 注入全局变量到文件名
        if not output_file.startswith(GLOBAL_VARIABLE):
            base_name = Path(output_file).name
            output_file = str(Path(output_file).parent / f"{GLOBAL_VARIABLE}_{base_name}")
        
        # 提取有时间数据的任务
        tasks = []
        keyword_aware_times = []
        llm_times = []
        speedup_ratios = []
        
        for task_key, data in self.comparison_data.items():
            display_name = data['display_name']
            keyword_aware_time = data['keyword_aware'].get('time')
            llm_time = data['llm'].get('time')
            
            if keyword_aware_time or llm_time:
                tasks.append(display_name)
                kw_time = keyword_aware_time if keyword_aware_time else 0
                llm_t = llm_time if llm_time else 0
                
                keyword_aware_times.append(kw_time)
                llm_times.append(llm_t)
                
                # 计算加速比
                if kw_time > 0 and llm_t > 0:
                    speedup = llm_t / kw_time
                    speedup_ratios.append(speedup)
                else:
                    speedup_ratios.append(0)
        
        if not tasks:
            print("⚠️ 没有足够的时间数据用于绘图")
            return
        
        # 创建双Y轴图表：左边是时间，右边是加速比
        fig, ax1 = plt.subplots(figsize=(12, 6), dpi=100)
        
        x = np.arange(len(tasks))
        width = 0.35
        
        # 左Y轴：时间成本
        bars1 = ax1.bar(x - width/2, keyword_aware_times, width, label='关键词检索(keyword-aware)', 
                        color='#4E79A7', alpha=0.8, edgecolor='black', linewidth=1.5)
        bars2 = ax1.bar(x + width/2, llm_times, width, label='LLM直接检索', 
                        color='#F28E2B', alpha=0.8, edgecolor='black', linewidth=1.5)
        
        # 在柱子上添加数值标签
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax1.text(bar.get_x() + bar.get_width()/2., height,
                            f'{height:.2f}s',
                            ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        ax1.set_xlabel('任务名称', fontsize=12, fontweight='bold')
        ax1.set_ylabel('时间成本 (秒)', fontsize=12, fontweight='bold', color='black')
        ax1.tick_params(axis='y', labelcolor='black')
        ax1.set_xticks(x)
        ax1.set_xticklabels(tasks, rotation=45, ha='right')
        ax1.grid(axis='y', alpha=0.3, linestyle='--')
        
        # 右Y轴：加速比
        ax2 = ax1.twinx()
        if any(speedup_ratios):
            line = ax2.plot(x, speedup_ratios, 'ro-', linewidth=2.5, markersize=10,
                           label='LLM相对加速比', markerfacecolor='white', markeredgewidth=2)
            
            # 在线上添加数值标签
            for i, (xi, yi) in enumerate(zip(x, speedup_ratios)):
                if yi > 0:
                    ax2.text(xi, yi + 0.05, f'{yi:.2f}x', ha='center', va='bottom', 
                            fontsize=9, fontweight='bold', color='red')
            
            ax2.set_ylabel('加速比 (LLM时间/关键词时间)', fontsize=12, fontweight='bold', color='red')
            ax2.tick_params(axis='y', labelcolor='red')
            ax2.axhline(y=1, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='相等线')
        
        ax1.set_title('检索时间成本对比分析 (关键词检索 vs LLM检索)', fontsize=14, fontweight='bold', pad=20)
        
        # 合并图例
        lines1, labels1 = ax1.get_legend_handles_labels()
        if any(speedup_ratios):
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=11, loc='upper left', framealpha=0.95)
        else:
            ax1.legend(fontsize=11, loc='upper left')
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=100, bbox_inches='tight')
        print(f"✓ 时间对比图已保存到: {output_file}")
        plt.close()
    
    def plot_overlap_comparison(self, output_file='retrieval_overlap_comparison.png'):
        """绘制检索结果覆盖率和模块占比对比图"""
            
        # 注入全局变量到文件名
        if not output_file.startswith(GLOBAL_VARIABLE):
            base_name = Path(output_file).name
            output_file = str(Path(output_file).parent / f"{GLOBAL_VARIABLE}_{base_name}")
            
        tasks = []
        similarities = []
        keyword_aware_ratios = []  # 新增：模块感知占LLM的比例
        keyword_aware_counts = []
        llm_counts = []
            
        for task_key, data in self.comparison_data.items():
            display_name = data['display_name']
            overlap = data['overlap']
                
            tasks.append(display_name)
            similarities.append(overlap.get('similarity', 0.0) * 100)
            
            # 新增：计算模块感知占LLM的比例
            keyword_aware_count = overlap.get('keyword_aware_count', 0)
            llm_count = overlap.get('llm_count', 0)
            if llm_count > 0:
                ratio = (keyword_aware_count / llm_count) * 100
            else:
                ratio = 0
            keyword_aware_ratios.append(ratio)
            
            keyword_aware_counts.append(keyword_aware_count)
            llm_counts.append(llm_count)
            
        if not tasks:
            print("⚠️ 没有足够的数据用于绘制覆盖率对比图")
            return
            
        # 创建双 Y 轴图表
        try:
            fig, ax1 = plt.subplots(figsize=(12, 6), dpi=100)
                
            x = np.arange(len(tasks))
            width = 0.35
                
            # 左 Y 轴：覆盖率和模块感知占LLM的比例
            bars1 = ax1.bar(x - width/2, similarities, width, label='覆盖率 (LLM覆盖关键词)', 
                            color='#59A14F', alpha=0.8, edgecolor='black', linewidth=1.5)
            bars2 = ax1.bar(x + width/2, keyword_aware_ratios, width, label='模块感知占LLM的比例', 
                            color='#E15759', alpha=0.8, edgecolor='black', linewidth=1.5)
                
            ax1.set_xlabel('任务名称', fontsize=12, fontweight='bold')
            ax1.set_ylabel('比例 (%)', fontsize=12, fontweight='bold', color='black')
            ax1.set_xticks(x)
            ax1.set_xticklabels(tasks, rotation=45, ha='right')
            ax1.tick_params(axis='y', labelcolor='black')
            ax1.set_ylim(0, 105)
            ax1.grid(axis='y', alpha=0.3, linestyle='--')
                
            # 添加数值标签
            for bars in [bars1, bars2]:
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:
                        ax1.text(bar.get_x() + bar.get_width()/2., height + 2,
                                f'{height:.0f}%',
                                ha='center', va='bottom', fontsize=9, fontweight='bold')
                
            # 右 Y 轴：模块计数
            ax2 = ax1.twinx()
            line1 = ax2.plot(x, keyword_aware_counts, 'o-', linewidth=2.5, markersize=8,
                            label='模块感知模块数', color='#4E79A7', markerfacecolor='white', markeredgewidth=2)
            line2 = ax2.plot(x, llm_counts, 's-', linewidth=2.5, markersize=8,
                            label='LLM模块数', color='#F28E2B', markerfacecolor='white', markeredgewidth=2)
                
            ax2.set_ylabel('模块数量', fontsize=12, fontweight='bold', color='black')
            ax2.tick_params(axis='y', labelcolor='black')
                
            ax1.set_title('检索结果覆盖率和模块占比对比分析', fontsize=14, fontweight='bold', pad=20)
                
            # 合并图例（仅当有有效句柄时）
            bars_labels = [b.get_label() for b in [bars1, bars2]]
            bars_handles = [bars1, bars2]
                
            lines_labels = ['模块感知模块数', 'LLM模块数']
            lines_handles = [l for l in line1 + line2 if l is not None]  # 过滤有效的句柄
                
            if lines_handles:
                ax1.legend(bars_handles + lines_handles, bars_labels + lines_labels,
                          loc='upper left', fontsize=10, framealpha=0.95)
            else:
                ax1.legend(bars_handles, bars_labels, loc='upper left', fontsize=10, framealpha=0.95)
                
            plt.tight_layout()
            plt.savefig(output_file, dpi=100, bbox_inches='tight')
            print(f"✓ 覆盖率对比图已保存到: {output_file}")
            plt.close()
        except Exception as e:
            print(f"⚠️ 绘制覆盖率对比图失败: {e}")
            plt.close()
    
    def plot_module_distribution(self, output_file='module_distribution_comparison.png'):
        """绘制模块分布对比图"""
            
        # 注入全局变量到文件名
        if not output_file.startswith(GLOBAL_VARIABLE):
            base_name = Path(output_file).name
            output_file = str(Path(output_file).parent / f"{GLOBAL_VARIABLE}_{base_name}")
            
        # 收集所有模块及其在各任务中的出现频率
        keyword_aware_module_freq = Counter()
        llm_module_freq = Counter()
            
        for task_key, data in self.comparison_data.items():
            for module in data['keyword_aware'].get('modules', []):
                keyword_aware_module_freq[module] += 1
            for module in data['llm'].get('modules', []):
                llm_module_freq[module] += 1
            
        # 获取Top 10模块
        top_keyword_aware = keyword_aware_module_freq.most_common(10)
        top_llm = llm_module_freq.most_common(10)
            
        # 创建并行氱状图
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=100)
            
        # 模块感知检索模块分布
        if top_keyword_aware:
            modules1, counts1 = zip(*top_keyword_aware)
            y_pos = np.arange(len(modules1))
            ax1.barh(y_pos, counts1, color='#4E79A7', alpha=0.8, edgecolor='black', linewidth=1.5)
            ax1.set_yticks(y_pos)
            ax1.set_yticklabels([m[:30] for m in modules1], fontsize=10)
            ax1.set_xlabel('出现频率', fontsize=11, fontweight='bold')
            ax1.set_title('模块感知检索 - 高频模块 TOP 10', fontsize=12, fontweight='bold')
            ax1.grid(axis='x', alpha=0.3, linestyle='--')
                
            # 添加数值标签
            for i, (m, c) in enumerate(top_keyword_aware):
                ax1.text(c + 0.1, i, f'{c}', va='center', fontsize=9, fontweight='bold')
            
        # LLM直接检索模块分布
        if top_llm:
            modules2, counts2 = zip(*top_llm)
            y_pos = np.arange(len(modules2))
            ax2.barh(y_pos, counts2, color='#F28E2B', alpha=0.8, edgecolor='black', linewidth=1.5)
            ax2.set_yticks(y_pos)
            ax2.set_yticklabels([m[:30] for m in modules2], fontsize=10)
            ax2.set_xlabel('出现频率', fontsize=11, fontweight='bold')
            ax2.set_title('LLM直接检索 - 高频模块 TOP 10', fontsize=12, fontweight='bold')
            ax2.grid(axis='x', alpha=0.3, linestyle='--')
            
            # 添加数值标签
            for i, (m, c) in enumerate(top_llm):
                ax2.text(c + 0.1, i, f'{c}', va='center', fontsize=9, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=100, bbox_inches='tight')
        print(f"✓ 模块分布对比图已保存到: {output_file}")
        plt.close()
    
    def export_to_json(self, output_dir=None, output_file='retrieval_comparison_result.json'):
        """导出分析结果为JSON - 包含完整的时间和标题信息"""
        
        # 注入全局变量到文件名
        if not output_file.startswith(GLOBAL_VARIABLE):
            base_name = Path(output_file).name
            output_file = f"{GLOBAL_VARIABLE}_{base_name}"
        
        export_data = {
            'summary': {
                'analysis_timestamp': str(__import__('datetime').datetime.now()),
                'comparison_type': 'keyword-aware(关键词检索) vs LLM(LLM直接检索)',
                'total_tasks': len(self.comparison_data)
            },
            'detailed_results': {}
        }
        
        # 统计数据
        total_keyword_aware_time = 0
        total_llm_time = 0
        total_tasks_with_time = 0
        
        for task_key, data in self.comparison_data.items():
            overlap = data['overlap']
            keyword_aware = data['keyword_aware']
            llm = data['llm']
            keyword_aware_modules = keyword_aware.get('modules', [])
            llm_modules = llm.get('modules', [])
            
            kw_time = keyword_aware.get('time')
            llm_time = llm.get('time')
            
            # 累计有效时间数据
            if kw_time:
                total_keyword_aware_time += kw_time
            if llm_time:
                total_llm_time += llm_time
            if kw_time or llm_time:
                total_tasks_with_time += 1
            
            # 计算加速比
            speedup_ratio = None
            if kw_time and llm_time and kw_time > 0:
                speedup_ratio = round(llm_time / kw_time, 2)
            
            export_data['detailed_results'][data['display_name']] = {
                'time_analysis': {
                    'keyword_aware_time_seconds': kw_time,
                    'llm_time_seconds': llm_time,
                    'speedup_ratio': speedup_ratio,  # 新增：加速比
                    'time_faster_method': 'keyword-aware' if (kw_time and llm_time and kw_time < llm_time) else ('llm' if (kw_time and llm_time and llm_time < kw_time) else None)
                },
                'module_analysis': {
                    'keyword_aware_modules_count': overlap.get('keyword_aware_count', 0),
                    'keyword_aware_modules': [m.lower() for m in keyword_aware_modules],
                    'keyword_aware_titles': keyword_aware.get('titles', []),  # 新增：title字段
                    'llm_modules_count': overlap.get('llm_count', 0),
                    'llm_modules': [m.lower() for m in llm_modules],
                    'overlap_count': overlap.get('overlap_count', 0),
                    'overlap_modules': overlap.get('overlap', []),
                },
                'similarity_metrics': {
                    'coverage_rate': round(overlap.get('similarity', 0.0) * 100, 2),  # LLM覆盖关键词结果的比例
                    'keyword_aware_to_llm_ratio': round((overlap.get('keyword_aware_count', 0) / overlap.get('llm_count', 1)) * 100, 2),  # 模块感知模块数占LLM模块数的比例
                },
                'unique_modules': {
                    'keyword_aware_only': overlap.get('keyword_aware_only', [])[:10],
                    'llm_only': overlap.get('llm_only', [])[:10],
                }
            }
        
        # 添加总体统计
        export_data['summary']['total_keyword_aware_time_seconds'] = round(total_keyword_aware_time, 2)
        export_data['summary']['total_llm_time_seconds'] = round(total_llm_time, 2)
        export_data['summary']['average_speedup_ratio'] = round(total_llm_time / total_keyword_aware_time, 2) if total_keyword_aware_time > 0 else None
        
        if output_dir is None:
            output_dir = Path.cwd()
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 分析结果已导出到: {output_path}")


def main():
    """主函数
    
    对比两种检索方式：
    1. 模块感知的关键词检索（keyword-aware retrieval）：从 generated_code_without_rag/gpt_5_with_rag/{task}/case_export_data.json 的 retrieval_results 字段
       - 基于关键词和模块信息的结构化检索
       - 支持从title和metadata中提取信息
    2. LLM直接检索（LLM direct retrieval）：从 retrieval_results_with_time.json 的 retrieved_modules 字段
       - 由大模型进行语义理解和检索
    
    输出内容：
    - 时间成本对比（含加速比分析）
    - 检索结果重合度分析
    - 模块分布对比
    - 详细的JSON报告
    """
    
    # 工作目录
    work_dir = Path(__file__).parent.parent.parent
    os.chdir(work_dir)
    
    print("🚀 开始检索结果对比分析...")
    print("对比：模块感知的关键词检索 vs LLM直接检索\n")
    
    # 读取LLM直接检索结果JSON
    json_file = work_dir / 'retrieval_results_with_time.json'
    if not json_file.exists():
        print(f"❌ 找不到文件: {json_file}")
        return
    
    # 读取模块感知检索结果目录
    export_dir = work_dir / "experiment_results" / "generated_code_without_rag" / "gpt_5_with_rag"
    if not export_dir.exists():
        print(f"⚠️ 模块感知检索结果目录不存在: {export_dir}")
        export_dir = None
    
    # 执行分析
    analyzer = RetrievalComparisonAnalyzer()
    
    # 解析LLM直接检索结果
    analyzer.llm_results = analyzer.parse_llm_retrieval_results(str(json_file))
    print(f"\n✅ 成功加载LLM直接检索结果：{len(analyzer.llm_results)} 个任务")
    
    # 解析模块感知检索结果
    if export_dir:
        print(f"\n正在从模块感知检索结果中提取模块信息（包括title和耗时）...")
        analyzer.keyword_aware_results = analyzer.parse_keyword_aware_retrieval_results(export_dir)
        print(f"✅ 成功加载模块感知检索结果：{len(analyzer.keyword_aware_results)} 个任务")
        # 统计耗时信息
        time_available = sum(1 for r in analyzer.keyword_aware_results.values() if r.get('time'))
        print(f"   其中 {time_available} 个任务包含耗时数据\n")
    else:
        analyzer.keyword_aware_results = {}
    
    # 执行对比分析（合并结果）
    analyzer.comparison_data = {}
    
    # 规范化任务名称用于匹配
    def normalize_name(name):
        return name.lower().replace('_', '').replace('-', '').replace(' ', '')
    
    keyword_aware_norm = {normalize_name(k): k for k in analyzer.keyword_aware_results.keys()}
    llm_norm = {normalize_name(k): k for k in analyzer.llm_results.keys()}
    
    # 合并所有任务
    all_tasks = set(keyword_aware_norm.keys()) | set(llm_norm.keys())
    
    for task_norm in all_tasks:
        task_key = task_norm
        
        keyword_aware_key = keyword_aware_norm.get(task_norm)
        llm_key = llm_norm.get(task_norm)
        
        keyword_aware_data = analyzer.keyword_aware_results.get(keyword_aware_key, {}) if keyword_aware_key else {}
        llm_data = analyzer.llm_results.get(llm_key, {}) if llm_key else {}
        
        # 计算重合度
        keyword_aware_modules = keyword_aware_data.get('modules', [])
        llm_modules = llm_data.get('modules', [])
        
        overlap_analysis = analyzer.calculate_overlap(keyword_aware_modules, llm_modules)
        
        analyzer.comparison_data[task_key] = {
            'keyword_aware': keyword_aware_data,
            'llm': llm_data,
            'overlap': overlap_analysis,
            'display_name': keyword_aware_key or llm_key or task_key
        }
    
    # 打印摘要
    analyzer.print_summary()
    
    # 生成图表
    print("\n📊 生成对比图表...")
    
    # 获取analys目录路径
    analys_dir = Path(__file__).parent
    
    analyzer.plot_time_comparison(str(analys_dir / 'retrieval_time_comparison_with_speedup.png'))
    analyzer.plot_overlap_comparison(str(analys_dir / 'retrieval_overlap_comparison.png'))
    analyzer.plot_module_distribution(str(analys_dir / 'module_distribution_comparison.png'))
    analyzer.export_to_json(analys_dir, 'retrieval_comparison_result_detailed.json')
    
    print("\n✅ 分析完成！")
    print("\n📊 生成的输出文件：")
    print(f"   • 时间成本对比图（含加速比）: retrieval_time_comparison_with_speedup.png")
    print(f"   • 重合度对比图: retrieval_overlap_comparison.png")
    print(f"   • 模块分布对比图: module_distribution_comparison.png")
    print(f"   • 详细分析结果（JSON）: retrieval_comparison_result_detailed.json")
    print(f"\n💡 说明：")
    print(f"   • 关键词检索（keyword-aware）：基于VTK.js模块的结构化检索")
    print(f"   • LLM直接检索：由大模型进行语义理解和检索")
    print(f"   • 加速比 > 1.0：LLM方法更快")
    print(f"   • 加速比 < 1.0：关键词方法更快")


if __name__ == '__main__':
    main()
