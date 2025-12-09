# analyze_query 函数升级说明

## 概述

`analyze_query()` 函数已升级为返回**结构化的可视化管道步骤**，而不是简单的文本扩展。新格式包含丰富的元信息，能更好地支持RAG检索和前端可视化。

## 新返回格式

### analyze_query 返回值

```python
List[Dict]  # 步骤列表
```

每个步骤包含以下字段：

```json
{
    "phase": "Data Loading",                    // 阶段类型
    "step_name": "Load Dataset",                // 步骤简称（用于流程图节点）
    "vtk_modules": ["vtkXMLImageDataReader"],   // 所需的VTK.js模块列表
    "description": "Detailed instruction..."    // 完整的步骤描述（用于代码生成）
}
```

### 阶段类型（phase）

- `Data Loading` - 数据加载
- `Data Processing` - 数据处理
- `Visualization Setup` - 可视化设置
- `UI Configuration` - UI配置
- `Rendering & Interaction` - 渲染与交互

## 核心流程变化

### 1. app.py 的 /generate 路由

**修改内容：**
- ✅ `analyze_query()` 现在返回 `list[dict]` 格式
- ✅ 提取 `description` 字段用于前端显示（analysis_text）
- ✅ 直接传递整个分析结果列表给 `RAGAgent.search()`

**代码流程：**
```python
if obj['workflow']['inquiryExpansion']:
    analysis = analyze_query(obj['prompt'], ...)  # 返回 list[dict]
    # 提取description用于显示
    analysis_text = '\n'.join([item.get('description', '') for item in analysis])

if obj['workflow']['rag']:
    final_prompt = rag_agent.search(analysis, obj['prompt'])  # 传递分析结果
```

### 2. RAGAgent.search() 方法

**修改内容：**
- ✅ 接收新格式的 `analysis: list[dict]`
- ✅ 自动转换为 VTKSearcherV2 兼容的格式
- ✅ 保留所有元信息供后续使用

**转换逻辑：**
```python
# 将新格式转换为检索兼容格式
query_list = []
for item in analysis:
    query_item = {
        'description': item.get('description', ''),      # 用于检索
        'phase': item.get('phase', ''),                  # 元信息
        'step_name': item.get('step_name', ''),          # 元信息
        'vtk_modules': item.get('vtk_modules', []),      # 可用于优化检索
        'weight': 5
    }
    query_list.append(query_item)

result = self.searcher.search(prompt, query_list)
```

### 3. VTKSearcherV2.search() 方法

**修改内容：**
- ✅ 支持新格式的 query_item（包含 phase, step_name, vtk_modules）
- ✅ 提取并记录所有元信息
- ✅ 保持向后兼容（仅使用 description 进行检索）

**新增记录：**
```python
for result in raw_results:
    result['query_phase'] = phase           # 记录来源阶段
    result['query_step_name'] = step_name   # 记录来源步骤
    result['query_vtk_modules'] = vtk_modules # 记录所需模块
```

## 完整工作流

```
用户输入: "生成渲染圆锥体和改变背景色的代码"
    ↓
[inquiryExpansion] analyze_query()
    ↓
返回: [
    {
        "phase": "Data Loading",
        "step_name": "Load Dataset",
        "vtk_modules": ["vtkConeSource"],
        "description": "使用vtkConeSource创建圆锥体..."
    },
    {
        "phase": "Visualization Setup",
        "step_name": "Set Background",
        "vtk_modules": ["vtkRenderer"],
        "description": "使用vtkRenderer设置背景色..."
    }
]
    ↓
[RAG检索] RAGAgent.search(analysis, prompt)
    ↓
转换query_list:
[
    {"description": "使用vtkConeSource创建圆锥体...", "phase": "Data Loading", ...},
    {"description": "使用vtkRenderer设置背景色...", "phase": "Visualization Setup", ...}
]
    ↓
VTKSearcherV2.search(prompt, query_list)
    ↓
检索结果 + 上下文 + final_prompt
    ↓
LLM生成代码
```

## 前端集成预留

### 已准备好的数据结构

新的分析结果包含：
- `phase`: 用于分类和流程图渲染
- `step_name`: 用于流程图节点标题
- `vtk_modules`: 用于显示所需模块列表
- `description`: 用于详细说明或工具提示

### 前端修改建议（后续）

1. **可视化管道显示**：使用 `phase` 和 `step_name` 绘制流程图
2. **模块依赖展示**：使用 `vtk_modules` 显示所需API列表
3. **详情面板**：使用 `description` 显示步骤详情

## 后向兼容性

✅ 如果 `inquiryExpansion` 为false，系统正常工作
✅ 如果 analysis 为空或None，自动创建默认query_list
✅ VTKSearcherV2 仍然只使用 description 进行检索（向后兼容）

## 测试检查项

- [x] analyze_query 返回格式正确
- [x] RAGAgent 正确转换新格式
- [x] VTKSearcherV2 处理新格式的 query_item
- [x] 检索结果正确传递给LLM
- [x] 代码生成流程完整

## 需要验证的项目

1. **后端测试**: 运行完整流程，确认生成代码质量
2. **前端集成**: 在前端显示分析结果的可视化管道（新步骤）
3. **性能**: 检查新增元信息是否影响检索速度

## 关键文件修改

- `app.py` (lines 93-121): /generate 路由修改
- `llm_agent/rag_agent.py` (lines 24-54): RAGAgent.search() 修改
- `RAG/retriever_v2.py` (lines 303-404): VTKSearcherV2.search() 修改
