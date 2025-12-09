# Mock Generation Pipeline 集成指南

## 概述

`MockGenerationPipeline` 是一个完整的代码生成和评估流程，用于模拟前端页面在检索结果后的后续操作。它复用了 `app.py` 中的核心逻辑，并支持批量处理 Excel 文件。

## 文件结构

```
d:\Pcode\LLM4VIS\llmscivis\
├── test/
│   ├── __init__.py
│   └── mock_generation/
│       ├── __init__.py
│       ├── mock_generation.py           # 主模块
│       ├── README.md                    # 详细文档
│       └── test_example.py              # 使用示例
├── RAG/
│   └── retriever_v3.py                  # 新增函数: process_benchmark_prompts_for_generation()
├── app.py
├── llm_agent/
│   ├── prompt_agent.py                  # analyze_query() 提示词拓展
│   ├── rag_agent.py                     # RAGAgent 检索
│   ├── ollma_chat.py                    # get_llm_response() 代码生成
│   └── evaluator_agent.py               # evaluate() 代码评估
└── config/
    └── ollama_config.py                 # 模型配置
```

## 完整流程

### Step 1: 提示词拓展 + RAG 检索

**功能**: 读取 Excel 的 "Benchmark prompt" 列，执行提示词拓展和 RAG 检索

**位置**: `RAG/retriever_v3.py` 的 `process_benchmark_prompts_for_generation()`

**工作原理**:

```python
# 1. 读取 Excel 中的 "Benchmark prompt"
benchmark_prompt = "render a cone"

# 2. 执行提示词拓展 (来自 app.py 的逻辑)
analysis = analyze_query(
    benchmark_prompt,
    model_name=ollama_config.inquiry_expansion_model
)

# 3. 执行 RAG 检索 (来自 app.py 的逻辑)
rag_agent = RAGAgent(use_v3=True)
final_prompt = rag_agent.search(analysis, benchmark_prompt)

# 4. 保存结果到 Excel
# - analysis_result: 拓展结果
# - final_prompt: 检索后的提示词
# - retrieval_results: 检索结果元数据
```

**对应的 app.py 代码**:

```python
# app.py 第 98-121 行
if obj['workflow']['inquiryExpansion']:
    analysis = analyze_query(obj['prompt'], ...)

if obj['workflow']['rag']:
    rag_agent = RAGAgent(use_v3=True)
    final_prompt = rag_agent.search(analysis, obj['prompt'])
    retrieval_results = rag_agent.get_retrieval_metadata()
```

### Step 2: 代码生成

**功能**: 使用生成模型根据拓展后的提示词生成 VTK.js 代码

**工作原理**:

```python
# 1. 获取生成器提示词
generator_prompt = row.get('generatorPrompt', '')
if not generator_prompt:
    generator_prompt = "你是 VTK.js 专家，只输出 HTML 代码..."

# 2. 调用 LLM 生成代码 (来自 app.py 的逻辑)
generated_code = get_llm_response(
    final_prompt,
    generator_model,
    system=generator_prompt
)

# 3. 保存到 Excel
# - generated_code: 生成的代码
# - generation_time: 生成耗时
```

**对应的 app.py 代码**:

```python
# app.py 第 123 行
response = get_llm_response(
    final_prompt,
    obj['generator'],
    system=obj['generatorPrompt']
)
```

### Step 3: 代码评估

**功能**: 评估生成的代码与标准代码的相似度和正确性

**工作原理**:

```python
# 1. 获取评估器提示词
evaluator_prompt = row.get('evaluatorPrompt', '')
if not evaluator_prompt:
    evaluator_prompt = "你是评估专家，使用 XML 格式返回评估结果..."

# 2. 调用评估器 (来自 evaluator_agent.py)
eval_result = evaluator_agent.evaluate(
    generated_code,
    ground_truth,
    evaluator_prompt,
    evaluator_model
)

# 3. 保存结果到 Excel
# - score: 评估分数
# - evaluation_time: 评估耗时
# - evaluation_result: 详细评估结果
```

**对应的 app.py 代码**:

```python
# app.py 第 277-294 行
eval_result = evaluator_agent.evaluate(
    obj['generatedCode'],
    obj["groundTruth"],
    obj['evaluatorPrompt'],
    obj['evaluator']
)
```

## 核心函数总结

### retriever_v3.py 中的新函数

#### `process_benchmark_prompts_for_generation(input_file, output_file=None, sheet_name='第二期实验数据')`

**功能**: 读取 Excel → 提示词拓展 → RAG 检索 → 写回 Excel

**参数**:
- `input_file` (str): 输入 Excel 文件路径
- `output_file` (str): 输出 Excel 文件路径，默认覆盖原文件
- `sheet_name` (str): 工作表名称

**返回**:
```python
{
    'success': True/False,
    'total_rows': 总行数,
    'processed': 成功处理的行数,
    'errors': 失败的行数,
    'output_file': 输出文件路径
}
```

**使用示例**:

```python
from RAG.retriever_v3 import process_benchmark_prompts_for_generation

result = process_benchmark_prompts_for_generation(
    'experiment_results/retrieval_results_v3_output.xlsx'
)
print(f"处理成功: {result['processed']}/{result['total_rows']}")
```

### mock_generation.py 中的 MockGenerationPipeline 类

#### `MockGenerationPipeline(excel_path)`

**初始化参数**:
- `excel_path` (str): 输入 Excel 文件路径

#### `run_complete_pipeline(generator='deepseek-v3', evaluator='deepseek-v3')`

**执行完整的生成和评估流程**

**参数**:
- `generator` (str): 代码生成模型名称
- `evaluator` (str): 代码评估模型名称

**返回**:
```python
{
    'success': True/False,
    'total_rows': 总行数,
    'processed': 成功处理的行数,
    'errors': 失败的行数,
    'output_file': 输出 Excel 文件路径,
    'results': [结果列表]
}
```

**使用示例**:

```python
from test.mock_generation.mock_generation import MockGenerationPipeline

pipeline = MockGenerationPipeline('your_excel.xlsx')
result = pipeline.run_complete_pipeline(
    generator='deepseek-v3',
    evaluator='deepseek-v3'
)

if result['success']:
    print(f"成功处理 {result['processed']} 行")
    pipeline.print_results_summary()
```

## 与 app.py 的关系

### 共享的逻辑

| 功能 | app.py 端点 | mock_generation.py |
|------|-----------|------------------|
| 提示词拓展 | `/expand` | `analyze_query()` |
| RAG 检索 | `/retrieval` | `RAGAgent.search()` |
| 代码生成 | `/generate` | `get_llm_response()` |
| 代码评估 | `/evaluate` | `evaluator_agent.evaluate()` |

### 主要区别

| 方面 | app.py | mock_generation.py |
|------|--------|-----------------|
| 工作模式 | REST API (实时) | 批处理 (离线) |
| 数据来源 | 前端请求 | Excel 文件 |
| 处理方式 | 单个案例 | 批量处理 |
| 用途 | 生产环境 | 实验/测试 |

## 快速开始

### 方式一：命令行运行

```bash
cd d:\Pcode\LLM4VIS\llmscivis

# 执行完整流程
python test/mock_generation/mock_generation.py \
    --excel experiment_results/retrieval_results_v3_output.xlsx \
    --generator deepseek-v3 \
    --evaluator deepseek-v3
```

### 方式二：Python 代码调用

```python
from test.mock_generation.mock_generation import MockGenerationPipeline

# 创建并运行管道
pipeline = MockGenerationPipeline('your_excel.xlsx')
result = pipeline.run_complete_pipeline()

# 查看结果
if result['success']:
    pipeline.print_results_summary()
```

### 方式三：分步执行

```python
from RAG.retriever_v3 import process_benchmark_prompts_for_generation
from llm_agent.ollma_chat import get_llm_response
from llm_agent import evaluator_agent

# Step 1: 检索
retrieval_result = process_benchmark_prompts_for_generation('input.xlsx')

# Step 2: 读取检索结果，执行生成和评估
import pandas as pd
df = pd.read_excel(retrieval_result['output_file'])

for index, row in df.iterrows():
    final_prompt = row.get('final_prompt', '')
    
    # Step 2a: 生成
    code = get_llm_response(final_prompt, 'deepseek-v3')
    
    # Step 2b: 评估
    eval_result = evaluator_agent.evaluate(
        code,
        row.get('groundTruth', ''),
        'evaluator_prompt',
        'deepseek-v3'
    )
```

## Excel 文件格式

### 输入列

| 列名 | 类型 | 是否必需 | 说明 |
|------|------|--------|------|
| Benchmark prompt | str | ✓ | 用户原始需求 |
| groundTruth | str | ✗ | 标准代码 |
| generatorPrompt | str | ✗ | 生成器系统提示词 |
| evaluatorPrompt | str | ✗ | 评估器系统提示词 |

### 输出列 (自动添加)

| 列名 | 类型 | 说明 |
|------|------|------|
| analysis_result | str (JSON) | 提示词拓展结果 |
| final_prompt | str | RAG 检索后的最终提示词 |
| retrieval_time | float | 检索耗时 (秒) |
| retrieval_results | str (JSON) | 检索结果元数据 |
| generated_code | str | 生成的 VTK.js 代码 |
| generation_time | float | 代码生成耗时 (秒) |
| score | str | 代码评估分数 |
| evaluation_time | float | 评估耗时 (秒) |
| evaluation_result | str | 评估结果详情 |

## 配置说明

### 模型配置

在 `config/ollama_config.py` 中配置可用的模型：

```python
ollama_config.models_cst = {
    'deepseek-v3': '...',
    'claude-sonnet-4': '...',
    # ... 其他模型
}

# 提示词拓展模型
ollama_config.inquiry_expansion_model = 'deepseek-v3'
```

### 数据库配置

RAG 检索需要 MongoDB，配置在 `RAG/retriever_v3.py` 的顶部：

```python
DB_HOST = 'localhost'
DB_PORT = 27017
DB_NAME = 'code_database'
COLLECTION_NAME = 'code_snippets'
```

## 常见问题

### Q1: 如何处理 MongoDB 连接失败？

A: 确保 MongoDB 已启动：

```bash
mongod --dbpath /path/to/db
```

或使用本地 MongoDB：

```bash
# Windows
mongod

# Linux/Mac
brew services start mongodb-community
```

### Q2: 如何只执行 Step 1 (检索) 而跳过 Step 2/3 (生成和评估)？

A: 直接调用 `process_benchmark_prompts_for_generation()`:

```python
from RAG.retriever_v3 import process_benchmark_prompts_for_generation

result = process_benchmark_prompts_for_generation('input.xlsx')
```

### Q3: 如何处理大规模数据 (几千行)?

A: 分批处理，每批 100-500 行：

```python
import pandas as pd

df = pd.read_excel('large_file.xlsx')
batch_size = 100

for i in range(0, len(df), batch_size):
    batch_df = df.iloc[i:i+batch_size]
    batch_df.to_excel(f'batch_{i}.xlsx', index=False)
    
    # 处理每一批
    pipeline = MockGenerationPipeline(f'batch_{i}.xlsx')
    pipeline.run_complete_pipeline()
```

### Q4: 如何获得更详细的日志信息？

A: 添加日志配置：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 性能优化建议

1. **减少网络往返**: 使用本地 LLM 而不是远程 API
2. **并行处理**: 对于大规模数据，考虑使用多进程处理
3. **缓存检索结果**: 避免重复检索相同的查询
4. **减少提示词长度**: 使用精简的系统提示词

## 故障排除

### 错误：`ModuleNotFoundError: No module named 'RAG'`

**解决方案**: 确保在项目根目录运行脚本，或添加项目路径：

```python
import sys
sys.path.insert(0, '/path/to/llmscivis')
```

### 错误：`KeyError: 'Benchmark prompt'`

**解决方案**: 检查 Excel 文件是否有 "Benchmark prompt" 列（大小写敏感）

### 错误：`Connection refused: 27017`

**解决方案**: 启动 MongoDB 服务，或检查配置是否正确

## 扩展说明

### 自定义流程

如果需要修改流程（例如只生成不评估），可以继承 `MockGenerationPipeline`：

```python
class CustomPipeline(MockGenerationPipeline):
    def run_complete_pipeline(self, **kwargs):
        # 自定义逻辑
        pass
```

### 添加中间步骤

在流程中插入额外的处理步骤：

```python
# 在生成后、评估前添加验证
if not self.validate_code(generated_code):
    print("代码验证失败")
    continue
```

## 相关文档

- [mock_generation/README.md](test/mock_generation/README.md) - 详细功能文档
- [test/mock_generation/test_example.py](test/mock_generation/test_example.py) - 使用示例
- [RAG/README_retriever_v3.md](RAG/README_retriever_v3.md) - 检索器文档

## 贡献指南

如有改进建议，欢迎提出 Issue 或 Pull Request！
