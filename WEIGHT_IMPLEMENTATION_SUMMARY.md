# 权重计算实现总结 (Weight Implementation Summary)

## 问题背景
用户发现在提示词拓展流程中**缺少权重计算**，导致 RAG 检索时无法识别哪些步骤更重要。这会影响检索的关联性评分。

## 修改内容

### 1. ✅ `llm_agent/prompt_agent.py` (第 38-103 行)
**目标：** 让 LLM 输出包含权重字段的结构化数据

**改动：**
- 添加 `"weight": 5` 字段到 JSON schema 说明（第 51 行）
- 修改注释：`"增加了 phase, step_name, vtk_modules, weight"` (第 38 行)
- 在示例输出中为每个 step 分配权重：
  - `Data Loading`: 权重 8
  - `Data Processing`: 权重 9
  - `Visualization Setup`: 权重 9（**最关键**）
  - `Rendering & Interaction`: 权重 6

**验证逻辑：** (第 145-149 行, 159-163 行)
```python
# 为缺少权重的项自动补充默认值
for item in result:
    if 'weight' not in item:
        item['weight'] = 5  # 默认权重值
```

---

### 2. ✅ `test/mock_generation/mock_generation.py` (第 279-315 行)
**目标：** 将分析结果转换为可被 RAG 引擎识别的格式，加入动态权重计算

**改动：**
- 从硬编码的 `'weight': 5` 改为 **动态权重计算**
- 优先级 1：使用 LLM 返回的权重值
- 优先级 2：根据 phase 类型计算权重的倍数因子

**权重映射逻辑：**
```python
phase_weight_map = {
    "Data Loading": 1.0,           # 基础性，乘以 5 = 5
    "Data Processing": 1.2,        # 中等重要，乘以 5 = 6
    "Visualization Setup": 1.5,    # 最关键！乘以 5 = 7.5
    "UI Configuration": 0.8,       # 可选，乘以 5 = 4
    "Rendering & Interaction": 1.0 # 基础性，乘以 5 = 5
}
```

**关键改动：**
```python
# 第 285 行（原）
final_prompt = rag_agent.search(search_analysis, obj['prompt'])

# 第 312 行（新）
final_prompt = rag_agent.search(search_analysis, query_list_for_search)
```

---

### 3. ✅ `RAG/retriever_v3.py` (第 145-212 行)
**状态：** ✅ 已完整实现

**功能：**
- `WeightedRanker` 类已支持基于权重的打分算法
- 在 `calculate_scores()` 方法中使用公式：
  ```
  得分 = 命中关键词数量 × 该查询的原始权重
  ```

---

## 流程图：权重如何流转

```
┌─────────────────────────────────────────────────┐
│ 1. prompt_agent.py (analyze_query)              │
│    LLM 返回结构化分析，包含 weight 字段          │
│    返回格式: [{phase, step_name, weight, ...}] │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 2. mock_generation.py (权重动态计算)            │
│    - 优先级 1: 使用 LLM 返回的 weight           │
│    - 优先级 2: 基于 phase 计算倍数因子          │
│    构造 query_list_for_search                  │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 3. retriever_v3.py (WeightedRanker)            │
│    使用权重进行打分: score = hits × weight     │
│    返回排序后的检索结果                         │
└─────────────────────────────────────────────────┘
```

---

## 工作原理说明

### 权重在 RAG 中的作用

假设用户查询：**"生成蓝色椎体"**

LLM 拆解为 3 个步骤：
1. `Data Processing` (weight=9) - 需要加载数据
2. `Visualization Setup` (weight=9) - 设置蓝色颜色
3. `Rendering & Interaction` (weight=6) - 渲染球体

当 RAG 检索时：
- 包含 "vtkColorTransferFunction" 的文档会获得更高分数（因为 weight=9）
- 包含 "vtkRenderWindow" 的文档会获得较低分数（因为 weight=6）
- 最终排序优先返回颜色映射相关的示例代码

### 两层权重体系

| 来源 | 优先级 | 说明 |
|------|-------|------|
| LLM 返回的 weight | 1️⃣ **最高** | 直接使用，表达 LLM 对重要性的理解 |
| Phase 倍数因子 | 2️⃣ **次级** | 当 LLM 权重无效时使用，确保最少有基础权重 |
| 硬编码默认值 | 3️⃣ **兜底** | 完全失败时使用 weight=5 |

---

## 验证清单

- ✅ `prompt_agent.py` schema 包含 weight 字段
- ✅ `prompt_agent.py` 示例输出包含具体权重值
- ✅ `prompt_agent.py` 验证逻辑补充默认权重
- ✅ `mock_generation.py` 实现动态权重计算
- ✅ `mock_generation.py` 将权重传递给 retriever_v3
- ✅ `retriever_v3.py` 已支持权重计算（无需修改）
- ✅ JSON 格式验证通过

---

## 使用示例

### 前端调用流程
```python
# 1. 获取分析结果（带权重）
analysis = analyze_query(
    "Generate visualization with blue color mapping",
    model_name=ollama_config.inquiry_expansion_model
)
# 返回: [
#   {phase: "Visualization Setup", weight: 9, ...},
#   {phase: "Rendering & Interaction", weight: 6, ...}
# ]

# 2. RAG 检索（使用权重）
rag_agent = RAGAgent(use_v3=True)
final_prompt = rag_agent.search(original_query, analysis)
# 内部自动计算权重并排序结果

# 3. 代码生成
response = get_llm_response(final_prompt, model_name, system)
```

---

## 后续建议

1. **权重阈值调优：** 根据实际效果调整 `phase_weight_map` 中的倍数因子
2. **权重可视化：** 在前端流程图中显示每个步骤的权重分数
3. **权重学习：** 可考虑基于评估结果反向调整权重（机器学习）
4. **权重持久化：** 保存优化后的权重配置到数据库

---

## 相关文件位置

| 文件 | 行号 | 功能 |
|-----|------|------|
| `llm_agent/prompt_agent.py` | 38-103 | 定义权重 schema |
| `test/mock_generation/mock_generation.py` | 279-315 | 权重计算和传递 |
| `RAG/retriever_v3.py` | 145-212 | 权重打分算法 |

