# 修改总结 - analyze_query 新格式适配

## 📋 修改概览

已成功完成 `analyze_query` 函数的升级，将其返回值从简单文本扩展升级为**结构化的可视化管道步骤**。后端检索流程已完全适配，准备就绪。

## ✅ 完成的修改

### 1. app.py (/generate 路由)
**文件**: `app.py` (lines 93-121)

**修改内容**:
- ✅ 处理新格式的分析结果 (`list[dict]`)
- ✅ 提取 description 字段用于前端显示
- ✅ 直接传递分析结果列表给 RAGAgent
- ✅ 保留 analysis_text 用于向后兼容

**关键代码**:
```python
if obj['workflow']['inquiryExpansion']:
    analysis = analyze_query(obj['prompt'], ...)
    # 提取description用于显示
    analysis_text = '\n'.join([item.get('description', '') for item in analysis])

if obj['workflow']['rag']:
    # 传递完整的分析结果给RAG
    final_prompt = rag_agent.search(analysis, obj['prompt'])
```

### 2. RAGAgent.search() 方法
**文件**: `llm_agent/rag_agent.py` (lines 24-54)

**修改内容**:
- ✅ 接收新格式的 analysis: `list[dict]`
- ✅ 自动转换为 VTKSearcherV2 兼容格式
- ✅ 保留所有元信息（phase, step_name, vtk_modules）
- ✅ 处理空值情况（自动创建默认query_list）

**关键特性**:
```python
# 转换新格式为检索兼容格式
query_list = []
for item in analysis:
    query_item = {
        'description': item.get('description', ''),
        'phase': item.get('phase', ''),
        'step_name': item.get('step_name', ''),
        'vtk_modules': item.get('vtk_modules', []),
        'weight': 5
    }
    query_list.append(query_item)
```

### 3. VTKSearcherV2.search() 方法
**文件**: `RAG/retriever_v2.py` (lines 303-404)

**修改内容**:
- ✅ 支持新格式的 query_item（包含 phase, step_name, vtk_modules）
- ✅ 提取并记录所有元信息
- ✅ 增强日志输出（显示阶段和所需模块）
- ✅ 保持向后兼容（仅使用 description 进行检索）

**新增记录**:
```python
for result in raw_results:
    result['query_phase'] = phase
    result['query_step_name'] = step_name
    result['query_vtk_modules'] = vtk_modules
```

## 🔄 数据流图

```
用户查询
   ↓
[inquiryExpansion] analyze_query()
   ↓
返回: [
  {"phase": "Data Loading", "step_name": "...", "vtk_modules": [...], "description": "..."},
  {"phase": "Visualization Setup", "step_name": "...", "vtk_modules": [...], "description": "..."}
]
   ↓
[提取description] analysis_text = "..." (用于前端显示)
   ↓
[RAG检索] RAGAgent.search(analysis, prompt)
   ↓
[转换格式] query_list with phase/vtk_modules metadata
   ↓
[检索执行] VTKSearcherV2.search(prompt, query_list)
   ↓
[上下文构建] 返回 final_prompt
   ↓
[代码生成] LLM 生成 HTML/JavaScript
```

## 📊 analyze_query 新返回格式

### 返回类型
```python
List[Dict]  # 步骤数组
```

### 每个步骤的字段
```json
{
    "phase": "Data Loading|Data Processing|Visualization Setup|UI Configuration|Rendering & Interaction",
    "step_name": "简洁标题 (≤5个单词)",
    "vtk_modules": ["vtkXMLImageDataReader", "vtkImageMapper"],
    "description": "完整详细的步骤描述，用于代码生成"
}
```

## 🎯 核心优势

1. **结构化数据**: 不再是单纯的文本，包含丰富的元信息
2. **多用途**: 
   - description → 代码生成
   - phase → 流程图分类
   - step_name → 流程图节点
   - vtk_modules → 依赖关系/搜索优化
3. **向后兼容**: 系统可正常运行即使关闭了 inquiryExpansion
4. **可视化就绪**: 前端已有数据基础，下一步直接实现流程图显示

## 🧪 验证清单

- [x] analyze_query 返回格式正确（list[dict]）
- [x] RAGAgent 正确处理新格式
- [x] VTKSearcherV2 支持新格式 query_item
- [x] 元信息正确传递和记录
- [x] 代码语法检查通过（无错误）
- [x] 向后兼容性验证
- [x] 空值处理验证

## 📝 后续工作项

### 短期（后端）
1. ✅ **已完成**: 后端适配新格式
2. 待办: 性能测试（新增元信息对性能的影响）
3. 待办: 日志优化（记录详细的分析和检索过程）

### 中期（前端）
1. 在生成页面显示分析步骤文本
2. 修改 API 返回完整的分析步骤结构
3. 实现可视化流程图渲染
4. 显示 vtk_modules 依赖关系

### 长期（系统优化）
1. 利用 vtk_modules 优化检索（只返回相关模块的代码）
2. 模块间依赖分析和验证
3. 生成代码的正确性验证

## 📚 相关文档

- [Analyze Query 升级详细说明](llm_agent/ANALYZE_QUERY_UPGRADE.md)
- [前端集成指南](front/FRONTEND_INTEGRATION_GUIDE.md)

## 🔧 关键文件列表

| 文件 | 行数 | 修改 |
|------|------|------|
| app.py | 93-121 | /generate 路由适配新格式 |
| llm_agent/rag_agent.py | 24-54 | RAGAgent.search() 转换逻辑 |
| RAG/retriever_v2.py | 303-404 | VTKSearcherV2.search() 增强 |
| llm_agent/prompt_agent.py | (无改) | analyze_query 已返回新格式 |

## ✨ 快速开始

### 测试新流程

```bash
# 1. 启动后端
python app.py

# 2. 在前端设置
{
    "workflow": {
        "inquiryExpansion": true,  # 启用提示词拓展
        "rag": true                 # 启用 RAG 检索
    }
}

# 3. 发送查询
"生成 VTK.js 可视化圆锥体，使用蓝色到红色的颜色映射，添加在 80% 处的切片"

# 4. 观察后端日志
# [Processing] Phase: Data Loading, Step: Load Dataset
# [Processing] Query: 加载圆锥体数据集...
# [Processing] VTK Modules: ['vtkXMLImageDataReader']
```

## 🎓 理解数据流

### 从用户输入到最终代码的完整链路

```
1. 用户输入（自然语言）
   ↓
2. LLM 分析（analyze_query）
   ├─ 拆分成多个步骤
   ├─ 为每个步骤标注元信息
   └─ 返回结构化数组
   ↓
3. 信息提取
   ├─ description 用于 RAG 检索
   ├─ phase/step_name 用于流程展示
   └─ vtk_modules 用于优化
   ↓
4. RAG 检索
   ├─ 按步骤查询代码库
   ├─ 记录元信息
   └─ 返回相关示例
   ↓
5. 上下文构建
   ├─ 组织检索结果
   ├─ 添加用户原始需求
   └─ 形成最终 prompt
   ↓
6. 代码生成
   ├─ LLM 读取 final_prompt
   ├─ 参考检索到的示例
   └─ 生成最终代码
   ↓
7. 结果返回
   ├─ 生成的代码
   ├─ 分析步骤
   ├─ 检索结果
   └─ 其他元数据
```

## 🚀 系统现状

✅ **后端完全就绪**
- 提示词拓展（新格式）✅
- RAG 检索适配 ✅
- 元信息完整传递 ✅

⏳ **前端准备中**
- 基础数据结构已支持 ✅
- 可视化流程图（待实现）⏳
- 模块依赖展示（待实现）⏳

---

**上次修改**: 2025-12-08  
**状态**: 后端完成，前端就绪  
**下一步**: 前端可视化流程图实现
