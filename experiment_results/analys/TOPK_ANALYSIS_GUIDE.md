## 前K选中结果 vs 剩余结果分析指南

### 📋 功能说明

本分析功能用于对比**重排序后前K个选中的结果**和**剩余其他结果**之间的差异，帮助理解重排序算法的效果。

### 🎯 主要分析维度

1. **FAISS相似度对比**
   - 前K结果的平均相似度
   - 剩余结果的平均相似度
   - 两者的差异

2. **重排序分数对比**
   - 前K结果的平均重排分
   - 剩余结果的平均重排分
   - 两者的差异

3. **VTK.js模块分布**
   - 前K结果的模块统计
   - 剩余结果的模块统计
   - 热门模块对比

4. **结果统计**
   - 初筛结果数
   - 重排序结果数
   - 前K选中数
   - 剩余结果数

### 🔧 如何使用

#### 方式1：使用分析脚本（推荐）

```bash
cd d:\Pcode\LLM4VIS\llmscivis
python experiment_results/analys/analyze_topk_results.py
```

#### 方式2：在Python代码中使用

```python
from experiment_results.analys.retriever_res_analys import RetrieverAnalyzer

# 创建分析器
analyzer = RetrieverAnalyzer(json_file="retrieval_results_12_2.json", 
                            excel_file="retrieval_results_detailed_12_2_15.xlsx")

# 定义查询列表
queries = ["vtk sphere", "image processing", "mesh visualization"]

# 执行分析
topk_analysis = analyzer.analyze_topk_vs_remaining(
    queries_list=queries,
    k=4,                          # 前K个结果的数量
    similarity_threshold=0.1       # 相似度阈值
)

# 导出结果到Excel
analyzer.export_topk_analysis_to_excel("topk_analysis.xlsx")
```

### 📊 输出结果

分析会生成两个Sheet的Excel文件：

#### Sheet 1: 聚合统计
包含以下指标的聚合汇总：
- 查询总数
- 前K总数
- 剩余总数
- 前K平均相似度
- 剩余平均相似度
- 平均相似度差异
- 前K平均重排分
- 剩余平均重排分
- 平均重排分差异

#### Sheet 2: 查询详情
包含每个查询的详细分析：
- 查询文本
- 初筛数 / 重排数
- 前K数 / 剩余数
- 相似度统计（平均/最小/最大）
- 重排分统计
- 差异数据

### 💡 解释说明

**前K平均相似度高于剩余结果** ✓
- 说明重排序算法成功地将高质量结果提升到前K
- 重排序效果好

**前K平均相似度低于剩余结果** ⚠
- 可能说明：
  1. 初筛结果中高相似度的项目较少
  2. 重排序算法更看重模块匹配而不是相似度
  3. 需要检查查询和重排序权重配置

**重排分数差异大** 
- 说明重排序算法有效地区分了结果
- 差异越大，重排效果越明显

### 🔍 实现细节

#### 关键函数

1. `search_code_with_topk_analysis(query, k, similarity_threshold, recall_k_multiplier=5)`
   - 在 `embedding_v3_1.py` 中定义
   - 返回包含前K和剩余结果的完整分析数据

2. `analyze_topk_vs_remaining(queries_list, k=4, similarity_threshold=0.1)`
   - 在 `RetrieverAnalyzer` 类中定义
   - 处理多个查询的批量分析

3. `export_topk_analysis_to_excel(output_file)`
   - 将分析结果导出到Excel

#### 数据结构

```python
{
    'query': '查询文本',
    'raw_results': [...],           # 初筛结果
    'reranked_results': [...],      # 重排序结果
    'top_k_results': [...],         # 前K选中
    'remaining_results': [...],     # 剩余结果
    'analysis': {
        'total_raw_count': 数字,
        'total_reranked_count': 数字,
        'top_k_count': 数字,
        'remaining_count': 数字,
        'top_k_stats': {
            'count': 数字,
            'avg_faiss_similarity': 浮点数,
            'min/max_faiss_similarity': 浮点数,
            'avg_rerank_score': 浮点数,
            'min/max_rerank_score': 浮点数,
            'total_modules': 数字,
            'unique_modules': 数字,
            'top_modules': [模块列表]
        },
        'remaining_stats': {...},
        'comparison': {
            'faiss_similarity_diff': 浮点数,
            'rerank_score_diff': 浮点数,
            ...其他对比数据
        }
    }
}
```

### 📈 可视化建议

从生成的Excel数据可以创建以下可视化：

1. **柱状图**：前K vs 剩余的平均相似度对比
2. **折线图**：各查询的差异趋势
3. **热力图**：模块在两个分组中的分布差异
4. **散点图**：相似度 vs 重排分的分布

### 🚀 使用场景

1. **评估重排序效果** - 检查重排序算法是否有效
2. **优化权重配置** - 根据结果调整模块匹配权重
3. **查询分析** - 理解哪些查询类型效果好/差
4. **结果质量评估** - 对比不同阈值下的效果

### ⚠️ 注意事项

1. 确保 `embedding_v3_1.py` 中的 `search_code_with_topk_analysis` 函数已正确实现
2. MongoDB 和 FAISS 索引需要已加载数据
3. 查询列表不能为空
4. K值应该小于等于重排序结果数量

### 📝 修改和扩展

如需修改分析逻辑，主要关注以下文件：

- `embedding_v3_1.py` - 检索和分析函数
- `retriever_res_analys.py` - 分析器类
- `analyze_topk_results.py` - 使用示例脚本
