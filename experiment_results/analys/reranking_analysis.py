"""
重排序结果分析脚本 - 分析前K个选中结果和剩余结果的对比数据
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict


class RerankingAnalyzer:
    """重排序结果分析器"""
    
    def __init__(self, excel_file: str = None, k_value: int = 4):
        """初始化分析器"""
        self.excel_file = excel_file
        self.k_value = k_value
        self.stage2_df = None
        self.analysis_results = {}
        self._load_data()
    
    def _load_data(self):
        """加载Excel数据"""
        if self.excel_file and Path(self.excel_file).exists():
            try:
                xls = pd.ExcelFile(self.excel_file)
                for sheet_name in xls.sheet_names:
                    if 'Reranked' in sheet_name or 'Stage 2' in sheet_name:
                        self.stage2_df = pd.read_excel(self.excel_file, sheet_name=sheet_name)
                        print(f"✓ 已加载: {sheet_name} ({len(self.stage2_df)} 行)")
            except Exception as e:
                print(f"✗ 加载失败: {e}")
    
    def analyze_selected_vs_remaining(self) -> dict:
        """分析前K个选中结果与剩余结果的差异"""
        if self.stage2_df is None:
            return {}
        
        result = {'by_query': [], 'summary': {}}
        stage2_by_query = self.stage2_df.groupby('Query Index')
        
        all_selected_rerank_scores = []
        all_remaining_rerank_scores = []
        all_selected_faiss_sims = []
        all_remaining_faiss_sims = []
        selected_modules_dist = defaultdict(int)
        remaining_modules_dist = defaultdict(int)
        
        for query_idx in sorted(stage2_by_query.groups.keys()):
            group = stage2_by_query.get_group(query_idx)
            group_sorted = group.sort_values('Rerank Score', ascending=False, na_position='last')
            
            selected = group_sorted.head(self.k_value)
            remaining = group_sorted.iloc[self.k_value:]
            
            if len(selected) > 0 and len(remaining) > 0:
                selected_rerank = selected['Rerank Score'].dropna()
                remaining_rerank = remaining['Rerank Score'].dropna()
                selected_faiss = selected['FAISS Similarity'].dropna()
                remaining_faiss = remaining['FAISS Similarity'].dropna()
                
                comparison = {
                    'query_index': query_idx,
                    'selected_count': len(selected),
                    'remaining_count': len(remaining),
                    'selected_avg_rerank': float(selected_rerank.mean()),
                    'remaining_avg_rerank': float(remaining_rerank.mean()),
                    'selected_avg_faiss': float(selected_faiss.mean()),
                    'remaining_avg_faiss': float(remaining_faiss.mean()),
                    'score_gap': float(selected_rerank.mean() - remaining_rerank.mean()),
                }
                
                result['by_query'].append(comparison)
                all_selected_rerank_scores.extend(selected_rerank.tolist())
                all_remaining_rerank_scores.extend(remaining_rerank.tolist())
                all_selected_faiss_sims.extend(selected_faiss.tolist())
                all_remaining_faiss_sims.extend(remaining_faiss.tolist())
                
                # 统计模块
                for _, row in selected.iterrows():
                    modules_str = row.get('VTK.js Modules', 'N/A')
                    if modules_str and modules_str != 'N/A':
                        modules = [m.strip() for m in str(modules_str).split(',')]
                        for m in modules:
                            selected_modules_dist[m] += 1
                
                for _, row in remaining.iterrows():
                    modules_str = row.get('VTK.js Modules', 'N/A')
                    if modules_str and modules_str != 'N/A':
                        modules = [m.strip() for m in str(modules_str).split(',')]
                        for m in modules:
                            remaining_modules_dist[m] += 1
        
        # 全局统计
        if all_selected_rerank_scores and all_remaining_rerank_scores:
            result['summary'] = {
                'total_selected': len(all_selected_rerank_scores),
                'total_remaining': len(all_remaining_rerank_scores),
                'selected_avg_rerank': np.mean(all_selected_rerank_scores),
                'remaining_avg_rerank': np.mean(all_remaining_rerank_scores),
                'selected_std_rerank': np.std(all_selected_rerank_scores),
                'remaining_std_rerank': np.std(all_remaining_rerank_scores),
                'selected_avg_faiss': np.mean(all_selected_faiss_sims),
                'remaining_avg_faiss': np.mean(all_remaining_faiss_sims),
                'avg_score_gap': np.mean(all_selected_rerank_scores) - np.mean(all_remaining_rerank_scores),
                'avg_score_gap_ratio': (np.mean(all_selected_rerank_scores) / np.mean(all_remaining_rerank_scores)),
                'selected_modules_dist': dict(sorted(selected_modules_dist.items(), key=lambda x: x[1], reverse=True)),
                'remaining_modules_dist': dict(sorted(remaining_modules_dist.items(), key=lambda x: x[1], reverse=True)),
            }
        
        self.analysis_results['selected_vs_remaining'] = result
        return result
    
    def print_analysis(self):
        """打印分析结果"""
        if 'selected_vs_remaining' not in self.analysis_results:
            self.analyze_selected_vs_remaining()
        
        result = self.analysis_results.get('selected_vs_remaining', {})
        summary = result.get('summary', {})
        comparisons = result.get('by_query', [])
        
        print("\n" + "="*100)
        print(f"【前{self.k_value}个选中结果 vs 剩余结果对比分析】")
        print("="*100)
        
        print(f"\n📊 全局统计:")
        print(f"  • 选中结果总数: {summary.get('total_selected', 0)}")
        print(f"  • 剩余结果总数: {summary.get('total_remaining', 0)}")
        print(f"  • 选中平均重排分数: {summary.get('selected_avg_rerank', 0):.6f}")
        print(f"  • 剩余平均重排分数: {summary.get('remaining_avg_rerank', 0):.6f}")
        print(f"  • 分数平均差距: {summary.get('avg_score_gap', 0):.6f}")
        print(f"  • 分数差距比例: {summary.get('avg_score_gap_ratio', 0):.2f}x")
        print(f"  • 选中平均FAISS: {summary.get('selected_avg_faiss', 0):.6f}")
        print(f"  • 剩余平均FAISS: {summary.get('remaining_avg_faiss', 0):.6f}")
        
        print(f"\n📋 按查询统计:")
        print(f"  {'查询':<6} {'选中':<6} {'剩余':<6} {'选中分数':<14} {'剩余分数':<14} {'分数差距':<12}")
        print(f"  {'-'*72}")
        for comp in sorted(comparisons, key=lambda x: x['query_index']):
            print(f"  {comp['query_index']:<6} {comp['selected_count']:<6} {comp['remaining_count']:<6} "
                  f"{comp['selected_avg_rerank']:<14.6f} {comp['remaining_avg_rerank']:<14.6f} "
                  f"{comp['score_gap']:<12.6f}")
        
        # 模块分布
        selected_modules = summary.get('selected_modules_dist', {})
        remaining_modules = summary.get('remaining_modules_dist', {})
        
        print(f"\n🧩 模块分布 (Top 10):")
        print(f"\n  【选中结果的高频模块】")
        for idx, (module, count) in enumerate(list(selected_modules.items())[:10], 1):
            print(f"    {idx:2}. {module[:40]:<40} {count:>4} 次")
        
        print(f"\n  【剩余结果的高频模块】")
        for idx, (module, count) in enumerate(list(remaining_modules.items())[:10], 1):
            print(f"    {idx:2}. {module[:40]:<40} {count:>4} 次")
    
    def export_to_excel(self, output_file: str):
        """导出分析结果到Excel"""
        if 'selected_vs_remaining' not in self.analysis_results:
            self.analyze_selected_vs_remaining()
        
        result = self.analysis_results.get('selected_vs_remaining', {})
        comparisons = result.get('by_query', [])
        summary = result.get('summary', {})
        
        df_comparisons = pd.DataFrame(comparisons)
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df_comparisons.to_excel(writer, sheet_name='按查询统计', index=False)
            
            summary_data = {
                '指标': [
                    '选中结果总数',
                    '剩余结果总数',
                    '选中平均重排分数',
                    '剩余平均重排分数',
                    '分数平均差距',
                    '分数差距比例',
                ],
                '数值': [
                    summary.get('total_selected', 0),
                    summary.get('total_remaining', 0),
                    summary.get('selected_avg_rerank', 0),
                    summary.get('remaining_avg_rerank', 0),
                    summary.get('avg_score_gap', 0),
                    f"{summary.get('avg_score_gap_ratio', 0):.2f}x",
                ]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='全局统计', index=False)
        
        print(f"✓ 已导出到: {output_file}")


def main():
    """主函数"""
    import os
    work_dir = Path(__file__).parent.parent.parent
    os.chdir(work_dir)
    
    excel_file = "retrieval_results_detailed_12_2_15.xlsx"
    output_file = "experiment_results/analys/reranking_selected_vs_remaining.xlsx"
    
    print("🚀 开始重排序结果分析...\n")
    analyzer = RerankingAnalyzer(excel_file=excel_file, k_value=4)
    analyzer.print_analysis()
    analyzer.export_to_excel(output_file)
    print("\n✅ 分析完成！")


if __name__ == '__main__':
    main()
