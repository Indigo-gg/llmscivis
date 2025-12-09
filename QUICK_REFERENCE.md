# 🚀 快速参考卡片 - analyze_query 新格式

## 修改了什么？

| 组件 | 原逻辑 | 新逻辑 |
|------|-------|--------|
| analyze_query返回值 | 一个查询拓展文本列表 | **结构化步骤数组** (含phase/vtk_modules) |
| app.py处理 | 直接拼接提示词 | **提取description** + 传递完整分析结果 |
| RAGAgent.search() | 直接传递analysis | **转换为query_list** 并保留元信息 |
| VTKSearcherV2.search() | 简单提取description | **提取所有元信息** 并记录到结果 |

## 新数据格式示例

```json
[
  {
    \"phase\": \"Data Loading\",
    \"step_name\": \"Load Dataset\",
    \"vtk_modules\": [\"vtkXMLImageDataReader\"],
    \"description\": \"使用vtkXMLImageDataReader从URL加载VTI格式数据...\"
  },
  {
    \"phase\": \"Data Processing\",
    \"step_name\": \"Slice Data\",
    \"vtk_modules\": [\"vtkImageSlice\", \"vtkPlane\"],
    \"description\": \"沿Y轴在80%深度处应用切片...\"
  }
]
```

## 三行代码理解流程

```python
# 1. 后端分析
analysis = analyze_query(prompt)  # 返回 list[dict]

# 2. RAG检索
final_prompt = rag_agent.search(analysis, prompt)  # 转换为query_list

# 3. 代码生成
code = llm.generate(final_prompt)  # LLM生成最终代码
```

## 关键改动位置

```
app.py (line 99)
    ↓
    analyze_query() 返回 [dict, dict, ...]
    ↓
RAGAgent.search() (line 31)
    ↓
    转换为 query_list with metadata
    ↓
VTKSearcherV2.search() (line 320)
    ↓
    执行检索，保存元信息
```

## 验证清单

- [x] analyze_query 返回正确格式
- [x] RAGAgent 正确转换
- [x] VTKSearcherV2 记录元信息
- [x] 无语法错误
- [x] 向后兼容

## 前端何时需要改动

**现在**: 无需改动，已支持现有 API  
**下一步**: 显示分析步骤可视化（流程图）  
**后续**: 利用vtk_modules进行优化

## 常见问题

**Q: 分析失败会怎样？**  
A: 自动回退到原始查询，检索和生成照常进行

**Q: 为什么需要新格式？**  
A: 为前端提供流程图数据，为检索提供模块信息

**Q: 性能会受影响吗？**  
A: 不会，只是多了数据结构，检索逻辑不变

## 下一步行动

1. ✅ 后端已适配（完成）
2. ⏳ 前端显示分析步骤文本
3. ⏳ 前端渲染流程图（使用phase/step_name）
4. ⏳ 利用vtk_modules优化检索
"