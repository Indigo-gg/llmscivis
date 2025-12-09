# Mock Generation Pipeline - 快速开始指南

## 🎯 30秒快速上手

### 最简方式：一行命令执行

```bash
cd d:\Pcode\LLM4VIS\llmscivis
python test/mock_generation/mock_generation.py --excel your_excel_file.xlsx
```

### 最快方式：5行 Python 代码

```python
from test.mock_generation.mock_generation import MockGenerationPipeline

pipeline = MockGenerationPipeline('your_excel.xlsx')
result = pipeline.run_complete_pipeline()
print(f"完成！输出文件: {result['output_file']}")
```

---

## 📋 Excel 文件格式

### 最小必需列

| Benchmark prompt |
|------------------|
| render a cone    |
| draw a sphere    |

### 完整可选列

| Benchmark prompt | groundTruth | generatorPrompt | evaluatorPrompt |
|------------------|------------|-----------------|-----------------|
| render a cone | `<html>...</html>` | （可选） | （可选） |

---

## 🔄 三步工作流

### Step 1: 拓展 → 检索
```python
# 自动执行：analyze_query() → RAGAgent.search()
# 输出：analysis_result, final_prompt, retrieval_results
```

### Step 2: 代码生成
```python
# 自动执行：get_llm_response()
# 输出：generated_code, generation_time
```

### Step 3: 代码评估
```python
# 自动执行：evaluator_agent.evaluate()
# 输出：score, evaluation_result, evaluation_time
```

---

## 💡 常见用法

### 用法 1：基础处理

```python
from test.mock_generation.mock_generation import MockGenerationPipeline

pipeline = MockGenerationPipeline('data.xlsx')
result = pipeline.run_complete_pipeline()
```

### 用法 2：自定义模型

```python
result = pipeline.run_complete_pipeline(
    generator='claude-sonnet-4',
    evaluator='deepseek-v3'
)
```

### 用法 3：仅执行检索

```python
from RAG.retriever_v3 import process_benchmark_prompts_for_generation

process_benchmark_prompts_for_generation('data.xlsx')
```

### 用法 4：查看结果摘要

```python
pipeline = MockGenerationPipeline('data.xlsx')
result = pipeline.run_complete_pipeline()

if result['success']:
    pipeline.print_results_summary()
    print(f"处理了 {result['processed']} 行，失败 {result['errors']} 行")
```

---

## 📊 输出示例

### 控制台输出

```
================================================================================
开始执行完整的代码生成和评估流程
================================================================================

[Step 1] 从 Excel 读取数据并执行检索...
[Processing] 加载 5 行数据

[Row 1/5] 处理: render a cone...
[Row 1] 成功处理，耗时: 0.45s

...

[Step 2] 执行代码生成和评估...
[Row 1/5] 执行代码生成和评估...
  - 生成代码... ✓ 代码生成成功 (2.3s)
  - 评估代码... ✓ 评估完成 (1.2s)
  - 结果: 分数=8.5

...

================================================================================
处理完成统计
================================================================================
  - 总行数: 5
  - 成功处理: 5
  - 失败: 0
  - 输出文件: data_output.xlsx
```

### 输出 Excel 文件

包含所有原始列 + 新增列：
- `analysis_result` - 提示词拓展结果
- `final_prompt` - 最终提示词
- `retrieval_time` - 检索耗时
- `generated_code` - 生成的代码
- `generation_time` - 生成耗时
- `score` - 评估分数
- `evaluation_time` - 评估耗时

---

## 🔗 相关命令

### 命令行参数

```bash
# 完整流程
python test/mock_generation/mock_generation.py \
    --excel input.xlsx \
    --generator deepseek-v3 \
    --evaluator deepseek-v3

# 仅检索
python -c "from RAG.retriever_v3 import process_benchmark_prompts_for_generation; process_benchmark_prompts_for_generation('input.xlsx')"

# 验证依赖
python test_mock_generation_import.py
```

---

## 🚀 三种运行方式对比

| 方式 | 命令 | 适用场景 |
|------|------|--------|
| **命令行** | `python test/mock_generation/mock_generation.py --excel ...` | 快速批处理 |
| **Python API** | `MockGenerationPipeline('file.xlsx').run_complete_pipeline()` | 代码集成 |
| **分步执行** | `process_benchmark_prompts_for_generation()` + 自定义逻辑 | 高度定制 |

---

## ⚡ 性能参考

| 操作 | 耗时 |
|------|------|
| 单行检索 | ~0.3-0.5s |
| 单行生成 | ~2-5s |
| 单行评估 | ~1-3s |
| **单行总耗时** | **~3.3-8.5s** |
| **10行总耗时** | **~33-85s** |
| **100行总耗时** | **~5-14分钟** |

---

## ✅ 检查清单

在使用前验证：

- [ ] Excel 文件存在且包含 "Benchmark prompt" 列
- [ ] MongoDB 服务已启动 (localhost:27017)
- [ ] 所需的 Python 包已安装 (pandas, openpyxl)
- [ ] 模型已在 `config/ollama_config.py` 中配置
- [ ] 有网络连接（如果使用远程 LLM）

---

## 🐛 常见问题速查

### Q: 找不到模块错误

```
ModuleNotFoundError: No module named 'RAG'
```

**A**: 从项目根目录运行，或添加路径：
```python
import sys
sys.path.insert(0, '/path/to/llmscivis')
```

### Q: MongoDB 连接失败

```
Connection refused: 27017
```

**A**: 启动 MongoDB：
```bash
mongod
```

### Q: Excel 列找不到

```
KeyError: 'Benchmark prompt'
```

**A**: 检查 Excel 文件是否有 "Benchmark prompt" 列（区分大小写）

### Q: 代码生成超时

**A**: 增加超时时间或使用更快的本地模型

---

## 📚 文档导航

| 文档 | 用途 |
|------|------|
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | 实现细节 |
| [MOCK_GENERATION_INTEGRATION.md](MOCK_GENERATION_INTEGRATION.md) | 集成指南 |
| [test/mock_generation/README.md](test/mock_generation/README.md) | API 参考 |
| [test/mock_generation/test_example.py](test/mock_generation/test_example.py) | 代码示例 |

---

## 🎓 工作流图

```
输入 Excel
  ↓
[MockGenerationPipeline]
  ├─→ [Step 1] 检索阶段
  │    └─→ process_benchmark_prompts_for_generation()
  │         ├─ analyze_query()    [提示词拓展]
  │         └─ RAGAgent.search()   [RAG 检索]
  │
  ├─→ [Step 2] 生成阶段
  │    └─→ get_llm_response()     [代码生成]
  │
  └─→ [Step 3] 评估阶段
       └─→ evaluator_agent.evaluate()  [代码评估]
  ↓
输出 Excel (_output.xlsx)
```

---

## 💻 快速示例

### 示例 1：基础使用

```python
from test.mock_generation.mock_generation import MockGenerationPipeline

pipeline = MockGenerationPipeline('experiment_results/data.xlsx')
result = pipeline.run_complete_pipeline()

print(f"成功处理 {result['processed']} 行")
print(f"输出文件: {result['output_file']}")
```

### 示例 2：查看结果

```python
# ... 执行流程 ...

# 打印摘要
pipeline.print_results_summary()

# 查看详细结果
for r in result['results']:
    print(f"行 {r['row_index']}: 分数={r['score']}, 耗时={r['generation_time']}s")
```

### 示例 3：错误处理

```python
result = pipeline.run_complete_pipeline()

if not result['success']:
    print(f"错误: {result['error']}")
else:
    print(f"成功! 处理了 {result['processed']}/{result['total_rows']} 行")
    if result['errors'] > 0:
        print(f"警告: 有 {result['errors']} 行处理失败")
```

---

## 🔐 配置指南

### 1. 配置模型 (`config/ollama_config.py`)

```python
ollama_config.models_cst = {
    'deepseek-v3': '...',
    'claude-sonnet-4': '...',
}
```

### 2. 配置数据库 (`RAG/retriever_v3.py`)

```python
DB_HOST = 'localhost'
DB_PORT = 27017
DB_NAME = 'code_database'
```

---

**就这么简单！现在你可以开始使用 Mock Generation Pipeline 了！** 🚀
