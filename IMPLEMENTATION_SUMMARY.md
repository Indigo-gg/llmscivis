# Mock Generation Pipeline 实现总结

## 📋 项目概述

完成了模拟前端页面检索后完整流程的实现，包括：**提示词拓展 → RAG 检索 → 代码生成 → 代码评估**

所有功能均复用了 `app.py` 和其他核心模块的逻辑，支持批量处理 Excel 文件。

## 🎯 实现内容

### 1. **RAG 检索模块增强** (`RAG/retriever_v3.py`)

#### 新增函数：`process_benchmark_prompts_for_generation()`

**功能**：从 Excel 读取 "Benchmark prompt" 字段，执行完整的提示词拓展和 RAG 检索流程

**核心参数**：
```python
def process_benchmark_prompts_for_generation(
    input_file: str,                    # 输入 Excel 文件
    output_file: str = None,            # 输出文件（可选）
    sheet_name: str = '第二期实验数据'  # 工作表名称
) -> dict
```

**实现步骤**：
1. 读取 Excel 中的 "Benchmark prompt" 列
2. 逐行执行提示词拓展 (`analyze_query()`)
3. 基于拓展结果执行 RAG 检索 (`VTKSearcherV3.search()`)
4. 提取检索结果元数据
5. 将所有中间结果写回 Excel

**输出列**：
- `analysis_result` - 拓展结果 (JSON)
- `final_prompt` - 最终提示词
- `retrieval_time` - 检索耗时
- `retrieval_results` - 检索结果元数据 (JSON)

**代码位置**：[RAG/retriever_v3.py#L681-L825](RAG/retriever_v3.py)

---

### 2. **完整生成和评估管道** (`test/mock_generation/mock_generation.py`)

#### 核心类：`MockGenerationPipeline`

**功能**：实现前端页面检索后的完整流程（生成 + 评估）

**核心方法**：
```python
class MockGenerationPipeline:
    def __init__(self, excel_path: str)
    def run_complete_pipeline(
        self,
        generator: str = 'deepseek-v3',
        evaluator: str = 'deepseek-v3'
    ) -> dict
```

**处理流程**：

```
[Step 1] 从 Excel 读取 & RAG 检索
↓
调用 process_benchmark_prompts_for_generation()
  ├── 提示词拓展 (analyze_query)
  ├── RAG 检索 (RAGAgent.search)
  └── 保存中间结果到 Excel
↓
[Step 2] 代码生成
↓
逐行读取 Excel，获取 final_prompt
  ├── 调用 LLM (get_llm_response)
  ├── 生成 VTK.js 代码
  └── 保存生成的代码
↓
[Step 3] 代码评估
↓
逐行执行评估
  ├── 调用评估器 (evaluator_agent.evaluate)
  ├── 获取评估分数
  └── 保存评估结果
↓
[Output] 保存最终结果到 *_output.xlsx
```

**复用的核心函数**：

| 功能 | 来源 | 复用方式 |
|------|------|--------|
| 提示词拓展 | `llm_agent/prompt_agent.py` | 直接调用 `analyze_query()` |
| RAG 检索 | `llm_agent/rag_agent.py` | 创建 `RAGAgent` 实例，调用 `search()` |
| 代码生成 | `llm_agent/ollma_chat.py` | 直接调用 `get_llm_response()` |
| 代码评估 | `llm_agent/evaluator_agent.py` | 直接调用 `evaluate()` |

**代码位置**：[test/mock_generation/mock_generation.py#L1-308](test/mock_generation/mock_generation.py)

---

### 3. **使用示例和文档**

#### 📄 提供的文件

| 文件 | 描述 |
|------|------|
| [test/mock_generation/README.md](test/mock_generation/README.md) | 详细功能文档和 API 参考 |
| [test/mock_generation/test_example.py](test/mock_generation/test_example.py) | 4 个完整使用示例 |
| [MOCK_GENERATION_INTEGRATION.md](MOCK_GENERATION_INTEGRATION.md) | 集成指南和详细说明 |
| [test_mock_generation_import.py](test_mock_generation_import.py) | 导入和依赖验证脚本 |
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | 本文件 |

---

## 🚀 快速开始

### 方式一：命令行执行

```bash
cd d:\Pcode\LLM4VIS\llmscivis

# 执行完整流程（拓展 → 检索 → 生成 → 评估）
python test/mock_generation/mock_generation.py \
    --excel experiment_results/retrieval_results_v3_output.xlsx \
    --generator deepseek-v3 \
    --evaluator deepseek-v3
```

### 方式二：Python 代码调用

```python
from test.mock_generation.mock_generation import MockGenerationPipeline

# 创建管道
pipeline = MockGenerationPipeline('your_excel.xlsx')

# 执行完整流程
result = pipeline.run_complete_pipeline(
    generator='deepseek-v3',
    evaluator='deepseek-v3'
)

# 查看结果
if result['success']:
    pipeline.print_results_summary()
    print(f"输出文件: {result['output_file']}")
```

### 方式三：仅执行检索步骤

```python
from RAG.retriever_v3 import process_benchmark_prompts_for_generation

result = process_benchmark_prompts_for_generation(
    input_file='input.xlsx',
    output_file='output.xlsx'
)
```

---

## 📊 数据流示例

### 输入 Excel 格式

| Benchmark prompt | groundTruth | generatorPrompt | evaluatorPrompt |
|------------------|------------|-----------------|-----------------|
| render a cone with blue color | `<html>...</html>` | 可选 | 可选 |

### 输出 Excel 格式

| ... | analysis_result | final_prompt | retrieval_time | ... | generated_code | generation_time | score |
|-----|-----------------|--------------|-----------------|-----|-----------------|------------------|-------|
| ... | `[{phase: ..., description: ...}]` (JSON) | `Generate only HTML...` | 0.45 | ... | `<html>...</html>` | 2.3 | 8.5 |

---

## 🔄 与 app.py 的关系

### 逻辑对应

```
app.py (/generate 端点)
│
├── [流程 1] 提示词拓展
│   └── analyze_query()
│
├── [流程 2] RAG 检索
│   └── RAGAgent.search()
│
├── [流程 3] 代码生成
│   └── get_llm_response()
│
└── [流程 4] 代码评估
    └── evaluator_agent.evaluate()

        ↓ (复用)

mock_generation.py (MockGenerationPipeline)
│
├── [Step 1] 检索阶段
│   └── process_benchmark_prompts_for_generation()
│       ├── analyze_query()
│       └── RAGAgent.search()
│
├── [Step 2] 生成阶段
│   └── get_llm_response()
│
└── [Step 3] 评估阶段
    └── evaluator_agent.evaluate()
```

### 关键区别

| 维度 | app.py | mock_generation.py |
|------|--------|-----------------|
| **工作模式** | REST API (实时) | 批处理 (离线) |
| **数据来源** | 前端 HTTP 请求 | Excel 文件 |
| **处理对象** | 单个案例 | 多个案例 |
| **使用场景** | 生产环境 | 实验/测试 |
| **并发性** | 支持并发请求 | 顺序处理 |

---

## 📁 文件清单

### 新增文件

```
test/
├── __init__.py                          [新增] 包初始化
├── mock_generation/
│   ├── __init__.py                      [新增] 包初始化
│   ├── mock_generation.py               [新增] 主模块 (308 行)
│   ├── README.md                        [新增] 详细文档 (211 行)
│   └── test_example.py                  [新增] 使用示例 (274 行)
├── (其他现存文件)

MOCK_GENERATION_INTEGRATION.md           [新增] 集成指南 (471 行)
IMPLEMENTATION_SUMMARY.md                [新增] 本文件
test_mock_generation_import.py           [新增] 验证脚本 (152 行)
```

### 修改文件

```
RAG/
└── retriever_v3.py                      [修改] +147 行新增函数
```

---

## 🔧 核心函数签名

### process_benchmark_prompts_for_generation()

```python
def process_benchmark_prompts_for_generation(
    input_file: str,
    output_file: str = None,
    sheet_name: str = '第二期实验数据'
) -> dict:
    """
    读取 Excel 中的 Benchmark prompt，执行提示词拓展和检索
    
    Returns:
    {
        'success': True/False,
        'total_rows': int,
        'processed': int,
        'errors': int,
        'output_file': str
    }
    """
```

### MockGenerationPipeline.run_complete_pipeline()

```python
def run_complete_pipeline(
    self,
    generator: str = 'deepseek-v3',
    evaluator: str = 'deepseek-v3'
) -> dict:
    """
    执行完整的生成和评估流程
    
    Returns:
    {
        'success': True/False,
        'total_rows': int,
        'processed': int,
        'errors': int,
        'output_file': str,
        'results': [list of results]
    }
    """
```

---

## 📈 处理统计示例

```
[Completed] 处理完成
  - 总行数: 10
  - 成功处理: 9
  - 失败: 1
  - 输出文件: experiment_results/retrieval_results_v3_output_output.xlsx
```

---

## ✅ 验证清单

- ✅ `RAG/retriever_v3.py` 中新增 `process_benchmark_prompts_for_generation()` 函数
- ✅ 实现了完整的提示词拓展 + 检索 + 生成 + 评估流程
- ✅ 支持从 Excel 读写数据
- ✅ 完全复用了 `app.py` 和其他核心模块的逻辑
- ✅ 提供了详细的文档和使用示例
- ✅ 创建了验证脚本
- ✅ 所有 Python 代码通过语法检查

---

## 📚 文档链接

### 详细文档

1. **[test/mock_generation/README.md](test/mock_generation/README.md)** - 功能详解和 API 参考
2. **[MOCK_GENERATION_INTEGRATION.md](MOCK_GENERATION_INTEGRATION.md)** - 集成指南
3. **[test/mock_generation/test_example.py](test/mock_generation/test_example.py)** - 4 个完整示例

### 相关源文件

1. **[app.py](app.py)** - Flask 应用，包含原始的生成/评估逻辑
2. **[llm_agent/prompt_agent.py](llm_agent/prompt_agent.py)** - 提示词拓展
3. **[llm_agent/rag_agent.py](llm_agent/rag_agent.py)** - RAG 检索
4. **[llm_agent/evaluator_agent.py](llm_agent/evaluator_agent.py)** - 代码评估
5. **[RAG/retriever_v3.py](RAG/retriever_v3.py)** - 检索器 (新增函数)

---

## 🎓 关键设计决策

### 1. **完全复用现有逻辑**

- 直接调用 `app.py` 中的函数，避免代码重复
- 保持与生产环境一致的行为

### 2. **支持灵活的参数配置**

- 可指定不同的生成器和评估器模型
- 支持自定义系统提示词

### 3. **完整的错误处理**

- 单行错误不影响其他行处理
- 详细的错误日志和统计

### 4. **中间结果保存**

- 每个步骤的结果都保存到 Excel
- 便于调试和分析

---

## 🔐 依赖关系

```
mock_generation.py
├── RAG/retriever_v3.py
│   ├── llm_agent/prompt_agent.py (analyze_query)
│   ├── config/ollama_config.py
│   └── RAG/vtk_code_meta_extract.py
├── llm_agent/rag_agent.py (RAGAgent)
├── llm_agent/ollma_chat.py (get_llm_response)
├── llm_agent/evaluator_agent.py (evaluate)
├── pandas (Excel 读写)
└── openpyxl (Excel 引擎)
```

---

## 🚨 注意事项

1. **MongoDB 依赖** - RAG 检索需要 MongoDB 服务运行
2. **模型配置** - 在 `config/ollama_config.py` 中配置可用模型
3. **网络连接** - 调用远程 LLM API 需要网络连接
4. **性能** - 大规模数据处理可能需要较长时间

---

## 📞 支持

详见以下文档获取更多帮助：

- 功能问题：[test/mock_generation/README.md](test/mock_generation/README.md#常见问题)
- 集成问题：[MOCK_GENERATION_INTEGRATION.md](MOCK_GENERATION_INTEGRATION.md#故障排除)
- 使用示例：[test/mock_generation/test_example.py](test/mock_generation/test_example.py)

---

**实现完成时间**：2025-12-08

**核心代码**：
- `RAG/retriever_v3.py` - 147 行新增函数
- `test/mock_generation/mock_generation.py` - 308 行主模块
- **总计新增代码**：约 800+ 行（含文档和示例）

