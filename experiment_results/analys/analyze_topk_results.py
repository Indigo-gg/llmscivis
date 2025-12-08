"""
前K选中结果 vs 剩余结果分析脚本

这个脚本演示如何使用新的分析功能来对比：
- 重排序后前K个选中的结果
- 剩余的其他结果

包括对比它们的：
- FAISS相似度
- 重排序分数
- VTK.js模块分布
"""

import os
import sys
from pathlib import Path

# 设置工作目录
work_dir = Path(__file__).parent.parent.parent
os.chdir(work_dir)

# 添加项目路径
sys.path.insert(0, str(work_dir))

from experiment_results.analys.retriever_res_analys import RetrieverAnalyzer


def main():
    """主函数"""
    
    print("="*80)
    print("🎯 RAG 两阶段检索结果分析 - 前K选中 vs 剩余结果对比")
    print("="*80)
    
    # 文件路径
    json_file = "retrieval_results_12_2.json"
    excel_file = "retrieval_results_detailed_12_2_15.xlsx"
    
    # 创建分析器
    analyzer = RetrieverAnalyzer(json_file=json_file, excel_file=excel_file)
    
    # 示例查询列表（这里使用一些测试查询）
    test_queries = [
        "vtk sphere render",
        "image processing vtk",
        "mesh visualization",
        "3D animation",
        "volume rendering"
    ]
    
    # 1. 分析前K选中 vs 剩余结果
    print("\n【步骤1】分析前K选中 vs 剩余结果的差异")
    print("-" * 80)
    
    # 这里使用K=4（对应retriever_v2中的默认k值）
    topk_analysis = analyzer.analyze_topk_vs_remaining(
        queries_list=test_queries,
        k=4,
        similarity_threshold=0.1
    )
    
    # 2. 导出分析结果到Excel
    print("\n【步骤2】导出分析结果到Excel")
    print("-" * 80)
    
    output_excel = "experiment_results/analys/topk_vs_remaining_analysis.xlsx"
    analyzer.export_topk_analysis_to_excel(output_excel)
    
    # 3. 打印聚合统计摘要
    print("\n【步骤3】聚合统计摘要")
    print("-" * 80)
    
    agg_stats = topk_analysis['aggregate_stats']
    
    print(f"\n📊 总体统计:")
    print(f"  • 分析的查询数: {topk_analysis['queries_analyzed']}")
    print(f"  • 前K总数: {topk_analysis['total_topk_count']}")
    print(f"  • 剩余总数: {topk_analysis['total_remaining_count']}")
    
    if agg_stats.get('topk_avg_faiss_sim_mean'):
        topk_sim = agg_stats['topk_avg_faiss_sim_mean']
        remaining_sim = agg_stats.get('remaining_avg_faiss_sim_mean', 0)
        avg_diff = agg_stats.get('avg_similarity_diff', 0)
        
        print(f"\n📈 FAISS相似度对比:")
        print(f"  • 前K平均相似度: {topk_sim:.4f}")
        print(f"  • 剩余平均相似度: {remaining_sim:.4f}")
        print(f"  • 平均差异: {avg_diff:.4f}")
        
        if avg_diff > 0:
            print(f"  ✓ 前K结果的FAISS相似度平均高于剩余结果")
        else:
            print(f"  ⚠ 前K结果的FAISS相似度平均低于或等于剩余结果")
    
    topk_rerank = agg_stats.get('topk_avg_rerank_score')
    remaining_rerank = agg_stats.get('remaining_avg_rerank_score')
    if topk_rerank and remaining_rerank:
        topk_avg = sum(topk_rerank) / len(topk_rerank)
        remaining_avg = sum(remaining_rerank) / len(remaining_rerank)
        rerank_diff = agg_stats.get('avg_rerank_diff', 0)
        
        print(f"\n🔄 重排序分数对比:")
        print(f"  • 前K平均重排分: {topk_avg:.4f}")
        print(f"  • 剩余平均重排分: {remaining_avg:.4f}")
        print(f"  • 平均差异: {rerank_diff:.4f}")
        
        if rerank_diff > 0:
            print(f"  ✓ 前K结果的重排分数平均高于剩余结果")
        else:
            print(f"  ⚠ 前K结果的重排分数平均低于或等于剩余结果")
    
    print("\n" + "="*80)
    print(f"✅ 分析完成！详细结果已保存到: {output_excel}")
    print("="*80)
    
    return topk_analysis


if __name__ == '__main__':
    main()
