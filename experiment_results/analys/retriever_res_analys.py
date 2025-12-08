"""
RAG 两阶段检索结果统计分析脚本

主要功能：
1. 分析第一阶段初筛结果和第二阶段重排序结果
2. 统计在初筛中发现但在重排序中丢失的结果
3. 分析丢失结果的模块信息和相似度
4. 生成详细的统计报告
"""

import json
import pandas as pd
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Set
import matplotlib.pyplot as plt
import numpy as np

# 中文字体设置
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class RetrieverAnalyzer:
    """检索结果分析器"""
    
    def __init__(self, json_file: str = None, excel_file: str = None):
        """
        初始化分析器
        
        Args:
            json_file: 包含检索结果的JSON文件路径
            excel_file: 包含两阶段结果的Excel文件路径
        """
        self.json_file = json_file
        self.excel_file = excel_file
        self.json_data = None
        self.stage1_df = None  # 初筛结果
        self.stage2_df = None  # 重排序结果
        self.analysis_results = {}
        
        self._load_data()
    
    def _load_data(self):
        """加载JSON和Excel数据"""
        # 加载JSON文件
        if self.json_file and Path(self.json_file).exists():
            try:
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    self.json_data = json.load(f)
                print(f"✓ 已加载JSON文件: {self.json_file}")
                print(f"  - 包含 {len(self.json_data)} 个查询结果")
            except Exception as e:
                print(f"✗ 加载JSON文件失败: {e}")
        
        # 加载Excel文件
        if self.excel_file and Path(self.excel_file).exists():
            try:
                xls = pd.ExcelFile(self.excel_file)
                print(f"✓ 已加载Excel文件: {self.excel_file}")
                print(f"  - Sheet列表: {xls.sheet_names}")
                
                # 读取两个sheet
                for sheet_name in xls.sheet_names:
                    if 'Initial' in sheet_name or 'Stage 1' in sheet_name:
                        self.stage1_df = pd.read_excel(self.excel_file, sheet_name=sheet_name)
                        print(f"  - {sheet_name}: {len(self.stage1_df)} 行")
                    elif 'Reranked' in sheet_name or 'Stage 2' in sheet_name:
                        self.stage2_df = pd.read_excel(self.excel_file, sheet_name=sheet_name)
                        print(f"  - {sheet_name}: {len(self.stage2_df)} 行")
            except Exception as e:
                print(f"✗ 加载Excel文件失败: {e}")
    
    def analyze_loss_between_stages(self) -> Dict:
        """
        分析初筛阶段中发现但重排序阶段丢失的结果
        
        Returns:
            Dict: 包含丢失统计的字典
        """
        if self.stage1_df is None or self.stage2_df is None:
            print("✗ 缺少Excel数据")
            return {}
        
        result = {
            'total_stage1': 0,
            'total_stage2': 0,
            'lost_items': [],
            'lost_count_by_query': defaultdict(int),
            'module_analysis': defaultdict(lambda: {'count': 0, 'avg_similarity': 0, 'examples': []}),
            'similarity_distribution': []
        }
        
        # 按查询分组统计
        stage1_by_query = self.stage1_df.groupby('Query Index')
        stage2_by_query = self.stage2_df.groupby('Query Index')
        
        for query_idx in stage1_by_query.groups.keys():
            stage1_group = stage1_by_query.get_group(query_idx)
            stage2_group = stage2_by_query.get_group(query_idx) if query_idx in stage2_by_query.groups else pd.DataFrame()
            
            result['total_stage1'] += len(stage1_group)
            result['total_stage2'] += len(stage2_group)
            
            # 获取文件路径集合
            stage1_files = set(stage1_group['File Path'].dropna().unique())
            stage2_files = set(stage2_group['File Path'].dropna().unique()) if not stage2_group.empty else set()
            
            # 找出丢失的文件
            lost_files = stage1_files - stage2_files
            result['lost_count_by_query'][query_idx] = len(lost_files)
            
            # 详细分析丢失的结果
            for _, row in stage1_group.iterrows():
                if row['File Path'] in lost_files:
                    lost_item = {
                        'query_index': query_idx,
                        'query_description': row.get('Query Description', 'N/A'),
                        'file_path': row['File Path'],
                        'faiss_similarity': row.get('FAISS Similarity', 0),
                        'vtkjs_modules': row.get('VTK.js Modules', 'N/A'),
                        'rank_in_stage1': len(result['lost_items']) + 1
                    }
                    result['lost_items'].append(lost_item)
                    result['similarity_distribution'].append(row.get('FAISS Similarity', 0))
                    
                    # 统计模块信息
                    modules_str = row.get('VTK.js Modules', 'N/A')
                    if modules_str and modules_str != 'N/A':
                        modules = [m.strip() for m in str(modules_str).split(',')]
                        for module in modules:
                            result['module_analysis'][module]['count'] += 1
                            result['module_analysis'][module]['avg_similarity'] += row.get('FAISS Similarity', 0)
                            if len(result['module_analysis'][module]['examples']) < 3:
                                result['module_analysis'][module]['examples'].append({
                                    'file': row['File Path'],
                                    'similarity': row.get('FAISS Similarity', 0)
                                })
        
        # 计算平均相似度
        for module in result['module_analysis']:
            count = result['module_analysis'][module]['count']
            if count > 0:
                result['module_analysis'][module]['avg_similarity'] = \
                    result['module_analysis'][module]['avg_similarity'] / count
        
        self.analysis_results['loss_analysis'] = result
        return result
    
    def print_loss_summary(self):
        """打印丢失结果的摘要"""
        if 'loss_analysis' not in self.analysis_results:
            self.analyze_loss_between_stages()
        
        result = self.analysis_results.get('loss_analysis', {})
        
        print("\n" + "="*80)
        print("【两阶段检索对比分析】")
        print("="*80)
        
        total_stage1 = result.get('total_stage1', 0)
        total_stage2 = result.get('total_stage2', 0)
        lost_count = len(result.get('lost_items', []))
        
        print(f"\n📊 基本统计:")
        print(f"  • 第一阶段（初筛）总结果数: {total_stage1}")
        print(f"  • 第二阶段（重排序）总结果数: {total_stage2}")
        print(f"  • 丢失的结果数: {lost_count}")
        if total_stage1 > 0:
            loss_rate = (lost_count / total_stage1) * 100
            print(f"  • 丢失率: {loss_rate:.2f}%")
        
        print(f"\n📈 按查询统计丢失结果:")
        lost_by_query = result.get('lost_count_by_query', {})
        for query_idx in sorted(lost_by_query.keys()):
            count = lost_by_query[query_idx]
            if count > 0:
                print(f"  • Query {query_idx}: 丢失 {count} 个结果")
        
        print(f"\n🔍 相似度分布:")
        similarities = result.get('similarity_distribution', [])
        if similarities:
            print(f"  • 最小相似度: {min(similarities):.4f}")
            print(f"  • 最大相似度: {max(similarities):.4f}")
            print(f"  • 平均相似度: {np.mean(similarities):.4f}")
            print(f"  • 中位数相似度: {np.median(similarities):.4f}")
        
        print(f"\n🧩 按VTK.js模块统计丢失结果:")
        module_analysis = result.get('module_analysis', {})
        sorted_modules = sorted(module_analysis.items(), 
                                key=lambda x: x[1]['count'], 
                                reverse=True)
        
        if sorted_modules:
            print(f"  Top 10 模块丢失情况:")
            for idx, (module, stats) in enumerate(sorted_modules[:10], 1):
                print(f"  {idx}. {module}")
                print(f"     - 丢失次数: {stats['count']}")
                print(f"     - 平均相似度: {stats['avg_similarity']:.4f}")
        else:
            print("  暂无模块信息")
    
    def print_lost_details(self, top_n: int = 20):
        """打印详细的丢失结果"""
        if 'loss_analysis' not in self.analysis_results:
            self.analyze_loss_between_stages()
        
        lost_items = self.analysis_results.get('loss_analysis', {}).get('lost_items', [])
        
        print(f"\n" + "="*80)
        print(f"【丢失结果详细列表】(展示前 {min(top_n, len(lost_items))} 个)")
        print("="*80 + "\n")
        
        # 按相似度排序（降序）
        sorted_items = sorted(lost_items, key=lambda x: x['faiss_similarity'], reverse=True)
        
        for idx, item in enumerate(sorted_items[:top_n], 1):
            print(f"[{idx}] 丢失项目")
            print(f"  • 所属查询: Query {item['query_index']}")
            print(f"  • 查询描述: {item['query_description']}")
            print(f"  • 文件路径: {item['file_path']}")
            print(f"  • FAISS相似度: {item['faiss_similarity']:.6f}")
            print(f"  • VTK.js模块: {item['vtkjs_modules']}")
            print()
    
    def analyze_stage_comparison(self) -> Dict:
        """
        进行两阶段的详细对比分析
        
        Returns:
            Dict: 对比分析结果
        """
        if self.stage1_df is None or self.stage2_df is None:
            return {}
        
        result = {
            'query_count': len(self.stage1_df['Query Index'].unique()),
            'stage1_stats': self._calculate_stage_stats(self.stage1_df),
            'stage2_stats': self._calculate_stage_stats(self.stage2_df),
            'similarity_threshold_analysis': {}
        }
        
        # 相似度阈值分析
        stage1_sims = self.stage1_df['FAISS Similarity'].dropna()
        for threshold in [0.5, 0.6, 0.7, 0.8, 0.9]:
            stage1_above = len(stage1_sims[stage1_sims >= threshold])
            stage2_above = len(self.stage2_df['FAISS Similarity'].dropna()[
                self.stage2_df['FAISS Similarity'].dropna() >= threshold])
            
            result['similarity_threshold_analysis'][threshold] = {
                'stage1': stage1_above,
                'stage2': stage2_above,
                'lost': stage1_above - stage2_above
            }
        
        self.analysis_results['stage_comparison'] = result
        return result
    
    def _calculate_stage_stats(self, df: pd.DataFrame) -> Dict:
        """计算单个阶段的统计数据"""
        sims = df['FAISS Similarity'].dropna()
        return {
            'total_items': len(df),
            'avg_similarity': float(sims.mean()) if len(sims) > 0 else 0,
            'median_similarity': float(sims.median()) if len(sims) > 0 else 0,
            'min_similarity': float(sims.min()) if len(sims) > 0 else 0,
            'max_similarity': float(sims.max()) if len(sims) > 0 else 0,
            'std_similarity': float(sims.std()) if len(sims) > 0 else 0
        }
    
    def print_stage_comparison(self):
        """打印阶段对比报告"""
        if 'stage_comparison' not in self.analysis_results:
            self.analyze_stage_comparison()
        
        result = self.analysis_results.get('stage_comparison', {})
        
        print(f"\n" + "="*80)
        print("【阶段对比统计】")
        print("="*80)
        
        print(f"\n📋 查询总数: {result.get('query_count', 0)}")
        
        stage1_stats = result.get('stage1_stats', {})
        stage2_stats = result.get('stage2_stats', {})
        
        print(f"\n🔷 第一阶段（初筛）统计:")
        print(f"  • 总结果数: {stage1_stats.get('total_items', 0)}")
        print(f"  • 平均相似度: {stage1_stats.get('avg_similarity', 0):.6f}")
        print(f"  • 中位数相似度: {stage1_stats.get('median_similarity', 0):.6f}")
        print(f"  • 相似度范围: [{stage1_stats.get('min_similarity', 0):.6f}, {stage1_stats.get('max_similarity', 0):.6f}]")
        print(f"  • 标准差: {stage1_stats.get('std_similarity', 0):.6f}")
        
        print(f"\n🔶 第二阶段（重排序）统计:")
        print(f"  • 总结果数: {stage2_stats.get('total_items', 0)}")
        print(f"  • 平均相似度: {stage2_stats.get('avg_similarity', 0):.6f}")
        print(f"  • 中位数相似度: {stage2_stats.get('median_similarity', 0):.6f}")
        print(f"  • 相似度范围: [{stage2_stats.get('min_similarity', 0):.6f}, {stage2_stats.get('max_similarity', 0):.6f}]")
        print(f"  • 标准差: {stage2_stats.get('std_similarity', 0):.6f}")
        
        print(f"\n📊 按相似度阈值统计:")
        threshold_analysis = result.get('similarity_threshold_analysis', {})
        print(f"  {'阈值':<8} {'第一阶段':<12} {'第二阶段':<12} {'丢失':<8}")
        print(f"  {'-'*40}")
        for threshold in sorted(threshold_analysis.keys()):
            stats = threshold_analysis[threshold]
            print(f"  {threshold:<8.1f} {stats['stage1']:<12} {stats['stage2']:<12} {stats['lost']:<8}")
    
    def export_analysis_to_excel(self, output_file: str):
        """
        将分析结果导出到Excel文件
        
        Args:
            output_file: 输出文件路径
        """
        if 'loss_analysis' not in self.analysis_results:
            self.analyze_loss_between_stages()
        
        lost_items = self.analysis_results.get('loss_analysis', {}).get('lost_items', [])
        
        # 如果没有丢失的项目，创建一个说明文件
        if not lost_items:
            summary_data = {
                '分析项': ['总结果数(初筛)', '总结果数(重排序)', '丢失数', '丢失率(%)'],
                '数值': [
                    self.analysis_results.get('loss_analysis', {}).get('total_stage1', 0),
                    self.analysis_results.get('loss_analysis', {}).get('total_stage2', 0),
                    0,
                    0.0
                ]
            }
            df_summary = pd.DataFrame(summary_data)
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df_summary.to_excel(writer, sheet_name='统计摘要', index=False)
                # 添加空白的丢失结果sheet
                empty_df = pd.DataFrame(columns=['Note'])
                empty_df.loc[0] = ['在本次分析中，初筛和重排序阶段的结果完全相同，没有丢失的项目']
                empty_df.to_excel(writer, sheet_name='丢失结果', index=False)
            print(f"✓ 分析结果已导出到: {output_file}（无丢失项目）")
            return
        
        # 创建DataFrame
        df_lost = pd.DataFrame(lost_items)
        
        # 重新排列列顺序
        column_order = ['query_index', 'query_description', 'file_path', 'faiss_similarity', 
                        'vtkjs_modules', 'rank_in_stage1']
        df_lost = df_lost[[col for col in column_order if col in df_lost.columns]]
        
        # 按相似度排序
        if 'faiss_similarity' in df_lost.columns:
            df_lost = df_lost.sort_values('faiss_similarity', ascending=False)
        
        # 导出到Excel
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df_lost.to_excel(writer, sheet_name='丢失结果', index=False)
            
            # 添加统计摘要Sheet
            summary_data = {
                '指标': [
                    '第一阶段总结果数',
                    '第二阶段总结果数',
                    '丢失结果数',
                    '丢失率(%)',
                    '平均相似度',
                    '最小相似度',
                    '最大相似度'
                ],
                '数值': [
                    self.analysis_results['loss_analysis'].get('total_stage1', 0),
                    self.analysis_results['loss_analysis'].get('total_stage2', 0),
                    len(lost_items),
                    (len(lost_items) / max(self.analysis_results['loss_analysis'].get('total_stage1', 1), 1)) * 100,
                    np.mean(self.analysis_results['loss_analysis'].get('similarity_distribution', [0])),
                    min(self.analysis_results['loss_analysis'].get('similarity_distribution', [0])),
                    max(self.analysis_results['loss_analysis'].get('similarity_distribution', [0]))
                ]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='统计摘要', index=False)
        
        print(f"✓ 分析结果已导出到: {output_file}")
    
    def plot_similarity_distribution(self, output_file: str = None):
        """
        绘制相似度分布图
        
        Args:
            output_file: 输出文件路径（如果为None则显示图表）
        """
        if 'loss_analysis' not in self.analysis_results:
            self.analyze_loss_between_stages()
        
        similarities = self.analysis_results.get('loss_analysis', {}).get('similarity_distribution', [])
        
        if not similarities:
            print("暂无丢失项目，无需绘制相似度分布图")
            return
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # 直方图
        axes[0].hist(similarities, bins=30, color='steelblue', edgecolor='black', alpha=0.7)
        axes[0].set_xlabel('FAISS 相似度', fontsize=12)
        axes[0].set_ylabel('频数', fontsize=12)
        axes[0].set_title('丢失结果的相似度分布', fontsize=14, fontweight='bold')
        axes[0].grid(True, alpha=0.3)
        
        # 箱线图
        axes[1].boxplot(similarities, vert=True)
        axes[1].set_ylabel('FAISS 相似度', fontsize=12)
        axes[1].set_title('丢失结果的相似度箱线图', fontsize=14, fontweight='bold')
        axes[1].grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"✓ 图表已保存到: {output_file}")
        else:
            plt.show()
    
    def analyze_vtkjs_modules(self) -> Dict:
        """
        分析所有VTK.js模块的使用情况
        
        Returns:
            Dict: 模块使用统计
        """
        if self.stage1_df is None:
            return {}
        
        result = {
            'total_modules': {},
            'modules_per_result': [],
            'most_common_modules': []
        }
        
        # 统计所有模块
        all_modules = defaultdict(int)
        
        for _, row in self.stage1_df.iterrows():
            modules_str = row.get('VTK.js Modules', 'N/A')
            if modules_str and modules_str != 'N/A':
                modules = [m.strip() for m in str(modules_str).split(',')]
                result['modules_per_result'].append(len(modules))
                for module in modules:
                    all_modules[module] += 1
        
        # 排序
        result['total_modules'] = dict(sorted(all_modules.items(), 
                                             key=lambda x: x[1], 
                                             reverse=True))
        result['most_common_modules'] = list(result['total_modules'].items())[:20]
        
        self.analysis_results['module_analysis'] = result
        return result
    
    def print_module_statistics(self):
        """
        打印模块统计信息
        """
        if 'module_analysis' not in self.analysis_results:
            self.analyze_vtkjs_modules()
        
        result = self.analysis_results.get('module_analysis', {})
        total_modules = result.get('total_modules', {})
        modules_per_result = result.get('modules_per_result', [])
        
        print(f"\n" + "="*80)
        print("【VTK.js 模块统计分析】")
        print("="*80)
        
        print(f"\n📊 总体统计:")
        print(f"  • 不同模块总数: {len(total_modules)}")
        if modules_per_result:
            print(f"  • 平均每个结果包含的模块数: {np.mean(modules_per_result):.2f}")
            print(f"  • 最多模块数: {max(modules_per_result)}")
            print(f"  • 最少模块数: {min(modules_per_result)}")
        
        print(f"\n🔝 使用最频繁的 15 个模块:")
        for idx, (module, count) in enumerate(list(total_modules.items())[:15], 1):
            percentage = (count / sum(total_modules.values())) * 100
            bar_length = int(percentage / 2)
            bar = '█' * bar_length
            print(f"  {idx:2}. {module[:50]:<50} {count:>4} 次 ({percentage:>5.1f}%) {bar}")
    
    def analyze_query_effectiveness(self) -> Dict:
        """
        分析每个查询的检索效果
        
        Returns:
            Dict: 查询效果统计
        """
        if self.stage1_df is None:
            return {}
        
        result = {
            'query_stats': {},
            'best_queries': [],
            'worst_queries': []
        }
        
        stage1_by_query = self.stage1_df.groupby('Query Index')
        
        for query_idx in stage1_by_query.groups.keys():
            group = stage1_by_query.get_group(query_idx)
            sims = group['FAISS Similarity'].dropna()
            
            stats = {
                'query_index': query_idx,
                'result_count': len(group),
                'avg_similarity': float(sims.mean()) if len(sims) > 0 else 0,
                'max_similarity': float(sims.max()) if len(sims) > 0 else 0,
                'min_similarity': float(sims.min()) if len(sims) > 0 else 0,
                'high_quality_count': len(sims[sims >= 0.5])  # 高质量结果
            }
            result['query_stats'][query_idx] = stats
        
        # 排序找出最好和最差的查询
        sorted_queries = sorted(result['query_stats'].items(), 
                               key=lambda x: x[1]['avg_similarity'], 
                               reverse=True)
        result['best_queries'] = sorted_queries[:5]
        result['worst_queries'] = sorted_queries[-5:]
        
        self.analysis_results['query_effectiveness'] = result
        return result
    
    def print_query_effectiveness(self):
        """
        打印查询效果分析
        """
        if 'query_effectiveness' not in self.analysis_results:
            self.analyze_query_effectiveness()
        
        result = self.analysis_results.get('query_effectiveness', {})
        best_queries = result.get('best_queries', [])
        worst_queries = result.get('worst_queries', [])
        query_stats = result.get('query_stats', {})
        
        print(f"\n" + "="*80)
        print("【查询效果分析】")
        print("="*80)
        
        print(f"\n🏆 效果最好的 5 个查询:")
        for idx, (query_id, stats) in enumerate(best_queries, 1):
            print(f"  {idx}. Query {query_id}")
            print(f"     - 结果数: {stats['result_count']}")
            print(f"     - 平均相似度: {stats['avg_similarity']:.6f}")
            print(f"     - 相似度范围: [{stats['min_similarity']:.6f}, {stats['max_similarity']:.6f}]")
            print(f"     - 高质量结果数(≥0.5): {stats['high_quality_count']}\n")
        
        print(f"\n📉 效果最差的 5 个查询:")
        for idx, (query_id, stats) in enumerate(reversed(worst_queries), 1):
            print(f"  {idx}. Query {query_id}")
            print(f"     - 结果数: {stats['result_count']}")
            print(f"     - 平均相似度: {stats['avg_similarity']:.6f}")
            print(f"     - 相似度范围: [{stats['min_similarity']:.6f}, {stats['max_similarity']:.6f}]")
            print(f"     - 高质量结果数(≥0.5): {stats['high_quality_count']}\n")
    
    def analyze_topk_vs_remaining(self, queries_list: List[str], k: int = 4, similarity_threshold: float = 0.1):
        """
        分析重排序后的前K个选中结果 vs 剩余结果的差异。
        
        Args:
            queries_list: 查询文本列表
            k: 前K个结果的数量
            similarity_threshold: 相似度阈值
        
        Returns:
            dict: 包含对比分析的数据
        """
        from RAG.embedding_v3_1 import search_code_with_topk_analysis
        
        print(f"\n开始分析前K个选中结果 vs 剩余结果的差异 (K={k})...\n")
        
        all_analysis = {
            'queries_analyzed': 0,
            'total_topk_count': 0,
            'total_remaining_count': 0,
            'query_analyses': [],
            'aggregate_stats': {
                'topk_avg_faiss_sim': [],
                'remaining_avg_faiss_sim': [],
                'topk_avg_rerank_score': [],
                'remaining_avg_rerank_score': [],
                'similarity_diffs': [],
                'rerank_diffs': []
            }
        }
        
        for query in queries_list:
            if not query or query.strip() == '':
                continue
            
            try:
                result = search_code_with_topk_analysis(query, k, similarity_threshold)
                analysis = result['analysis']
                
                all_analysis['queries_analyzed'] += 1
                all_analysis['total_topk_count'] += analysis['top_k_count']
                all_analysis['total_remaining_count'] += analysis['remaining_count']
                
                # 收集聚合统计
                if analysis['top_k_stats']['count'] > 0:
                    all_analysis['aggregate_stats']['topk_avg_faiss_sim'].append(
                        analysis['top_k_stats']['avg_faiss_similarity']
                    )
                    all_analysis['aggregate_stats']['topk_avg_rerank_score'].append(
                        analysis['top_k_stats']['avg_rerank_score']
                    )
                
                if analysis['remaining_stats']['count'] > 0:
                    all_analysis['aggregate_stats']['remaining_avg_faiss_sim'].append(
                        analysis['remaining_stats']['avg_faiss_similarity']
                    )
                    all_analysis['aggregate_stats']['remaining_avg_rerank_score'].append(
                        analysis['remaining_stats']['avg_rerank_score']
                    )
                
                # 收集差异数据
                all_analysis['aggregate_stats']['similarity_diffs'].append(
                    analysis['comparison']['faiss_similarity_diff']
                )
                all_analysis['aggregate_stats']['rerank_diffs'].append(
                    analysis['comparison']['rerank_score_diff']
                )
                
                # 保存单个查询的分析
                all_analysis['query_analyses'].append(analysis)
                
                # 打印单个查询的结果
                print(f"查询: {query}")
                print(f"  初筛结果数: {analysis['total_raw_count']}")
                print(f"  重排序结果数: {analysis['total_reranked_count']}")
                print(f"  前K个选中: {analysis['top_k_count']}, 剩余: {analysis['remaining_count']}")
                print(f"  前K相似度: {analysis['top_k_stats']['avg_faiss_similarity']:.4f} (范围: {analysis['top_k_stats']['min_faiss_similarity']:.4f}-{analysis['top_k_stats']['max_faiss_similarity']:.4f})")
                print(f"  剩余相似度: {analysis['remaining_stats']['avg_faiss_similarity']:.4f} (范围: {analysis['remaining_stats']['min_faiss_similarity']:.4f}-{analysis['remaining_stats']['max_faiss_similarity']:.4f})")
                print(f"  前K重排分数: {analysis['top_k_stats']['avg_rerank_score']:.4f}")
                print(f"  剩余重排分数: {analysis['remaining_stats']['avg_rerank_score']:.4f}")
                print(f"  相似度差异: {analysis['comparison']['faiss_similarity_diff']:.4f}")
                print(f"  重排分数差异: {analysis['comparison']['rerank_score_diff']:.4f}\n")
                
            except Exception as e:
                print(f"  分析查询失败: {e}")
        
        # 计算聚合统计
        if all_analysis['aggregate_stats']['topk_avg_faiss_sim']:
            avg_vals = all_analysis['aggregate_stats']['topk_avg_faiss_sim']
            all_analysis['aggregate_stats']['topk_avg_faiss_sim_mean'] = sum(avg_vals) / len(avg_vals)
        
        if all_analysis['aggregate_stats']['remaining_avg_faiss_sim']:
            avg_vals = all_analysis['aggregate_stats']['remaining_avg_faiss_sim']
            all_analysis['aggregate_stats']['remaining_avg_faiss_sim_mean'] = sum(avg_vals) / len(avg_vals)
        
        if all_analysis['aggregate_stats']['similarity_diffs']:
            diffs = all_analysis['aggregate_stats']['similarity_diffs']
            all_analysis['aggregate_stats']['avg_similarity_diff'] = sum(diffs) / len(diffs)
        
        if all_analysis['aggregate_stats']['rerank_diffs']:
            diffs = all_analysis['aggregate_stats']['rerank_diffs']
            all_analysis['aggregate_stats']['avg_rerank_diff'] = sum(diffs) / len(diffs)
        
        self.topk_analysis_results = all_analysis
        return all_analysis
    
    def export_topk_analysis_to_excel(self, output_file: str):
        """
        将前K vs 剩余结果的分析导出到Excel。
        """
        if not hasattr(self, 'topk_analysis_results') or not self.topk_analysis_results:
            print("没有顶K分析数据，请先运行 analyze_topk_vs_remaining()")
            return
        
        analysis = self.topk_analysis_results
        
        # 创建聚合统计Sheet
        summary_data = {
            '指标': [
                '查询总数',
                '前K总数',
                '剩余总数',
                '前K平均相似度',
                '剩余平均相似度',
                '平均相似度差异',
                '前K平均重排分数',
                '剩余平均重排分数',
                '平均重排分数差异'
            ],
            '数值': [
                analysis['queries_analyzed'],
                analysis['total_topk_count'],
                analysis['total_remaining_count'],
                analysis['aggregate_stats'].get('topk_avg_faiss_sim_mean', 0),
                analysis['aggregate_stats'].get('remaining_avg_faiss_sim_mean', 0),
                analysis['aggregate_stats'].get('avg_similarity_diff', 0),
                sum(analysis['aggregate_stats']['topk_avg_rerank_score']) / len(analysis['aggregate_stats']['topk_avg_rerank_score']) if analysis['aggregate_stats']['topk_avg_rerank_score'] else 0,
                sum(analysis['aggregate_stats']['remaining_avg_rerank_score']) / len(analysis['aggregate_stats']['remaining_avg_rerank_score']) if analysis['aggregate_stats']['remaining_avg_rerank_score'] else 0,
                analysis['aggregate_stats'].get('avg_rerank_diff', 0)
            ]
        }
        
        # 创建查询详情Sheet
        query_details = []
        for qa in analysis['query_analyses']:
            query_details.append({
                '查询': qa['query'],
                '初筛数': qa['total_raw_count'],
                '重排数': qa['total_reranked_count'],
                '前K数': qa['top_k_count'],
                '剩余数': qa['remaining_count'],
                '前K_avg相似度': qa['top_k_stats']['avg_faiss_similarity'],
                '前K_min相似度': qa['top_k_stats']['min_faiss_similarity'],
                '前K_max相似度': qa['top_k_stats']['max_faiss_similarity'],
                '剩余_avg相似度': qa['remaining_stats']['avg_faiss_similarity'],
                '剩余_min相似度': qa['remaining_stats']['min_faiss_similarity'],
                '剩余_max相似度': qa['remaining_stats']['max_faiss_similarity'],
                '前K_avg重排分': qa['top_k_stats']['avg_rerank_score'],
                '剩余_avg重排分': qa['remaining_stats']['avg_rerank_score'],
                '相似度差异': qa['comparison']['faiss_similarity_diff'],
                '重排分差异': qa['comparison']['rerank_score_diff']
            })
        
        try:
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # 写入聚合统计
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='聚合统计', index=False)
                
                # 写入查询详情
                df_details = pd.DataFrame(query_details)
                df_details.to_excel(writer, sheet_name='查询详情', index=False)
            
            print(f"\n✓ 顶K分析结果已导出到: {output_file}")
        except Exception as e:
            print(f"✗ 导出Excel失败: {e}")
    
    def generate_comprehensive_report(self, output_file: str):
        """
        生成综合分析报告
        
        Args:
            output_file: 输出文件路径
        """
        # 执行所有分析
        self.analyze_loss_between_stages()
        self.analyze_stage_comparison()
        self.analyze_vtkjs_modules()
        self.analyze_query_effectiveness()
        
        # 创建多个Sheet的Excel报告
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Sheet 1: 统计摘要
            summary_data = {
                '指标': [
                    '第一阶段总结果数',
                    '第二阶段总结果数',
                    '丢失结果数',
                    '丢失率(%)',
                    '平均相似度(第一阶段)',
                    '中位数相似度(第一阶段)',
                    '标准差(第一阶段)',
                    '不同VTK.js模块总数',
                    '平均每结果模块数',
                    '总查询数'
                ],
                '数值': [
                    self.analysis_results.get('loss_analysis', {}).get('total_stage1', 0),
                    self.analysis_results.get('loss_analysis', {}).get('total_stage2', 0),
                    len(self.analysis_results.get('loss_analysis', {}).get('lost_items', [])),
                    (len(self.analysis_results.get('loss_analysis', {}).get('lost_items', [])) / 
                     max(self.analysis_results.get('loss_analysis', {}).get('total_stage1', 1), 1)) * 100,
                    self.analysis_results.get('stage_comparison', {}).get('stage1_stats', {}).get('avg_similarity', 0),
                    self.analysis_results.get('stage_comparison', {}).get('stage1_stats', {}).get('median_similarity', 0),
                    self.analysis_results.get('stage_comparison', {}).get('stage1_stats', {}).get('std_similarity', 0),
                    len(self.analysis_results.get('module_analysis', {}).get('total_modules', {})),
                    np.mean(self.analysis_results.get('module_analysis', {}).get('modules_per_result', [0])),
                    len(self.analysis_results.get('query_effectiveness', {}).get('query_stats', {}))
                ]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='统计摘要', index=False)
            
            # Sheet 2: 按相似度阈值统计
            threshold_data = []
            for threshold, stats in self.analysis_results.get('stage_comparison', {}).get('similarity_threshold_analysis', {}).items():
                threshold_data.append({
                    '相似度阈值': threshold,
                    '第一阶段结果数': stats['stage1'],
                    '第二阶段结果数': stats['stage2'],
                    '丢失数': stats['lost']
                })
            if threshold_data:
                df_threshold = pd.DataFrame(threshold_data)
                df_threshold.to_excel(writer, sheet_name='阈值分析', index=False)
            
            # Sheet 3: VTK.js 模块统计
            module_data = []
            for module, count in list(self.analysis_results.get('module_analysis', {}).get('total_modules', {}).items())[:50]:
                module_data.append({
                    '模块名称': module,
                    '使用次数': count,
                    '使用比例(%)': (count / sum(self.analysis_results.get('module_analysis', {}).get('total_modules', {}).values())) * 100
                })
            if module_data:
                df_modules = pd.DataFrame(module_data)
                df_modules.to_excel(writer, sheet_name='模块统计', index=False)
            
            # Sheet 4: 查询效果分析
            query_data = []
            for query_id, stats in self.analysis_results.get('query_effectiveness', {}).get('query_stats', {}).items():
                query_data.append({
                    '查询ID': query_id,
                    '结果数': stats['result_count'],
                    '平均相似度': stats['avg_similarity'],
                    '最大相似度': stats['max_similarity'],
                    '最小相似度': stats['min_similarity'],
                    '高质量结果数': stats['high_quality_count']
                })
            if query_data:
                df_queries = pd.DataFrame(query_data)
                df_queries.to_excel(writer, sheet_name='查询效果', index=False)
        
        print(f"✓ 综合报告已导出到: {output_file}")
        """
        绘制模块丢失分析图
        
        Args:
            output_file: 输出文件路径
            top_n: 显示前N个模块
        """
        if 'loss_analysis' not in self.analysis_results:
            self.analyze_loss_between_stages()
        
        module_analysis = self.analysis_results.get('loss_analysis', {}).get('module_analysis', {})
        
        if not module_analysis:
            print("暂无模块数据，无需绘制模块分析图")
            return
        
        # 排序
        sorted_modules = sorted(module_analysis.items(), 
                                key=lambda x: x[1]['count'], 
                                reverse=True)[:top_n]
        
        modules = [m[0] for m in sorted_modules]
        counts = [m[1]['count'] for m in sorted_modules]
        similarities = [m[1]['avg_similarity'] for m in sorted_modules]
        
        fig, ax1 = plt.subplots(figsize=(14, 8))
        
        # 柱状图：丢失次数
        x = np.arange(len(modules))
        bars = ax1.bar(x, counts, color='coral', alpha=0.7, label='丢失次数')
        ax1.set_xlabel('VTK.js 模块', fontsize=12, fontweight='bold')
        ax1.set_ylabel('丢失次数', fontsize=12, fontweight='bold', color='coral')
        ax1.tick_params(axis='y', labelcolor='coral')
        ax1.set_xticks(x)
        ax1.set_xticklabels(modules, rotation=45, ha='right', fontsize=10)
        
        # 双Y轴：平均相似度
        ax2 = ax1.twinx()
        line = ax2.plot(x, similarities, color='steelblue', marker='o', linewidth=2, 
                       markersize=8, label='平均相似度')
        ax2.set_ylabel('平均相似度', fontsize=12, fontweight='bold', color='steelblue')
        ax2.tick_params(axis='y', labelcolor='steelblue')
        
        plt.title('VTK.js 模块丢失分析（丢失次数 vs 平均相似度）', 
                 fontsize=14, fontweight='bold', pad=20)
        
        # 添加图例
        bars_label = [bars]
        lines_label = line
        all_labels = [b.get_label() for b in bars_label] + [l.get_label() for l in lines_label]
        ax1.legend(bars_label + lines_label, all_labels, loc='upper right')
        
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"✓ 模块分析图已保存到: {output_file}")
        else:
            plt.show()


def main():
    """主函数"""
    import os
    
    # 工作目录
    work_dir = Path(__file__).parent.parent.parent
    os.chdir(work_dir)
    
    # 文件路径
    json_file = "retrieval_results_12_2.json"
    excel_file = "retrieval_results_detailed_12_2_15.xlsx"
    
    print("🚀 开始分析检索结果...\n")
    print(f"工作目录: {os.getcwd()}")
    print(f"JSON文件: {json_file} - 存在: {Path(json_file).exists()}")
    print(f"Excel文件: {excel_file} - 存在: {Path(excel_file).exists()}\n")
    
    # 创建分析器
    analyzer = RetrieverAnalyzer(json_file=json_file, excel_file=excel_file)
    
    # 执行分析
    print("\n" + "="*80)
    analyzer.print_loss_summary()
    analyzer.print_stage_comparison()
    analyzer.print_module_statistics()
    analyzer.print_query_effectiveness()
    
    # 导出结果
    output_excel = "experiment_results/analys/retrieval_comprehensive_analysis.xlsx"
    print(f"\n正在生成综合分析报告: {output_excel}")
    analyzer.generate_comprehensive_report(output_excel)
    
    # 导出丢失项目分析
    output_excel_lost = "experiment_results/analys/lost_items_detailed_analysis.xlsx"
    print(f"\n正在导出丢失项目分析: {output_excel_lost}")
    analyzer.export_analysis_to_excel(output_excel_lost)
    
    print("\n✅ 分析完成！")


if __name__ == '__main__':
    main()
