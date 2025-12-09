# 前端集成指南 - 提示词拓展可视化

## 后端返回数据结构

当启用 `inquiryExpansion` 工作流时，后端返回的数据将包含以下字段：

```javascript
{
    "analysis": "string",                    // 连接所有description的文本（用于显示）
    "retrieval_results": [                   // RAG检索结果
        {
            "id": "xxx",
            "title": "Example Title",
            "description": "Example description",
            "relevance": 0.95
        }
    ],
    "generated_code": "...",
    "final_prompt": "..."
}
```

## 前端可用数据

### 方案1: 仅使用 analysis_text（最小改动）

当前已实现，前端可以直接显示提示词拓展结果：

```javascript
// 在生成完成后获取分析文本
const analysisText = response.analysis;  // "阶段1的描述\n阶段2的描述\n..."

// 在UI中显示
showAnalysisPanel(analysisText);
```

### 方案2: 显示完整的管道步骤（推荐，后续实现）

后端API需要修改以返回完整的分析结果结构。建议修改：

#### 修改 app.py 返回更多信息

在 `/generate` 路由中，修改返回值包含完整的分析结果：

```python
# 在构建 data_dict 时添加
if isinstance(analysis, list):
    data_dict['analysis_steps'] = analysis  # 返回完整的结构化步骤列表
else:
    data_dict['analysis_steps'] = []

# 或者保留现有的 analysis_text，同时添加新字段
data_dict['analysis_detailed'] = analysis if isinstance(analysis, list) else []
```

#### 前端展示管道流程图

```javascript
// 接收来自后端的分析步骤
const analysisSteps = response.analysis_steps || [];

// 按 phase 分组
const phaseGroups = {
    'Data Loading': [],
    'Data Processing': [],
    'Visualization Setup': [],
    'UI Configuration': [],
    'Rendering & Interaction': []
};

analysisSteps.forEach(step => {
    if (phaseGroups[step.phase]) {
        phaseGroups[step.phase].push(step);
    }
});

// 渲染流程图节点
renderPipeline(phaseGroups);

// 显示模块依赖
analysisSteps.forEach(step => {
    if (step.vtk_modules && step.vtk_modules.length > 0) {
        console.log(`${step.step_name} requires: ${step.vtk_modules.join(', ')}`);
    }
});
```

## 核心流程

### 用户交互流程

```
1. 用户输入查询 → "生成圆锥体和改变背景色"
   ↓
2. 前端发送请求（inquiryExpansion=true）
   ↓
3. 后端执行：
   - analyze_query() 返回结构化步骤
   - RAGAgent 进行检索
   - LLM 生成代码
   ↓
4. 前端接收响应
   ↓
5. 前端显示：
   a. 分析步骤（可视化流程图）
   b. 检索结果（相关代码示例）
   c. 生成的代码
```

## 数据流向示意

```
分析步骤示例：
[
    {
        "phase": "Data Loading",
        "step_name": "Create Cone",
        "vtk_modules": ["vtkConeSource"],
        "description": "创建圆锥体几何体..."
    },
    {
        "phase": "Visualization Setup",
        "step_name": "Apply Colors",
        "vtk_modules": ["vtkColorTransferFunction"],
        "description": "应用颜色映射..."
    },
    {
        "phase": "Rendering & Interaction",
        "step_name": "Render",
        "vtk_modules": ["vtkRenderWindow"],
        "description": "初始化渲染器..."
    }
]
        ↓
可视化流程图：
┌─────────────────────────────────────┐
│   Data Loading                      │
│   ┌─────────────────────────────┐   │
│   │ Create Cone                 │   │
│   │ (vtkConeSource)             │   │
│   └─────────────────────────────┘   │
└─────────────┬───────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   Visualization Setup               │
│   ┌─────────────────────────────┐   │
│   │ Apply Colors                │   │
│   │ (vtkColorTransferFunction)  │   │
│   └─────────────────────────────┘   │
└─────────────┬───────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   Rendering & Interaction           │
│   ┌─────────────────────────────┐   │
│   │ Render                      │   │
│   │ (vtkRenderWindow)           │   │
│   └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

## 建议的前端修改步骤

### Step 1: 显示分析文本（已可行）
- 在生成UI中添加"分析步骤"面板
- 显示 `response.analysis` 文本

### Step 2: 修改后端返回完整结构（需要后续实现）
- 在 app.py 返回 `analysis_steps` 字段
- 前端解析完整结构

### Step 3: 实现可视化流程图（UI层）
- 使用 Vue 组件渲染流程图
- 显示模块依赖信息
- 支持交互（点击展示详情）

## 环境变量配置

当前系统已支持：
- ✅ inquiryExpansion workflow flag
- ✅ rag workflow flag  
- ✅ 前端可配置两个工作流的启用/禁用

## 测试建议

1. **测试没有分析的情况**：
   - 设置 `inquiryExpansion: false`
   - 确认系统仍能正常生成代码

2. **测试分析 + RAG 流程**：
   - 设置 `inquiryExpansion: true` 和 `rag: true`
   - 检查检索质量是否提高

3. **测试只分析不检索**：
   - 设置 `inquiryExpansion: true` 和 `rag: false`
   - 验证分析结果是否正确

## 常见问题

### Q: 为什么 analysis 是字符串而不是结构化数据？
A: 这是为了与现有的数据存储兼容。后续可以修改 app.py 返回完整的结构化数据。

### Q: vtk_modules 何时使用？
A: 目前仅用于信息记录。未来可以用于：
1. 过滤检索结果（只返回包含所需模块的代码）
2. 可视化模块依赖关系
3. 代码验证（检查生成的代码是否使用了必需的模块）

### Q: 如果分析失败会怎样？
A: 系统会自动回退到原始查询，使用该查询进行检索和代码生成。

## 相关文件

- 后端分析逻辑：`llm_agent/prompt_agent.py`
- RAG检索：`RAG/retriever_v2.py`
- API端点：`app.py` (/generate 路由)
- 前端集成点：需要修改的 Home.vue 组件
