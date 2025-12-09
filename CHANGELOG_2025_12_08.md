# 变更日志 - 2025年12月8日

## 🎯 核心改进

### 1. 代码生成加载状态显示
- ✅ 在右侧栏评估卡片中添加生成过程的加载指示器
- ✅ 显示进度圆形和"Generating Code..."文本
- ✅ 隐藏其他内容，突出加载状态

### 2. 导出功能重构
- ✅ 将保存人工评估和导出完整结果功能集成到右侧栏
- ✅ 新增"保存人工评估"按钮 - 保存用户评估数据
- ✅ 新增"导出完整结果"按钮 - 导出所有阶段结果
- ✅ 导出数据包含人工评估总分
- ✅ 支持导出最终提示词和工作流配置

### 3. 截屏功能修复
- ✅ 修复iframe中VTK.js内容的截图白屏问题
- ✅ 实现三层降级策略（直接截图 → iframe内部截图 → 占位符图像）
- ✅ 改进VTK渲染检测逻辑
- ✅ 确保导出过程不因截屏失败而中断

---

## 📝 修改文件列表

### 前端文件
```
front/src/
├── view/
│   └── home.vue                    (传递isGenerating和export-results事件)
├── components/
│   ├── sidebar/
│   │   └── RightSidebar.vue        (接收isGenerating属性)
│   └── dashboard/
│       └── EvaluationScoreCard.vue (添加加载状态和导出按钮)
└── utils/
    └── export.js                   (改进截屏和数据转换逻辑)
```

---

## 🔧 技术细节

### HTML2Canvas配置变化
```javascript
// 之前
{
    useCORS: true,
    allowTaint: true,
    foreignObjectRendering: true,
    scale: 2
}

// 现在（iframe内容）
{
    useCORS: true,
    allowTaint: true,
    foreignObjectRendering: false,  // 禁用SVG渲染
    backgroundColor: '#ffffff',
    scale: 1                         // 降低scale
}
```

### 导出数据新增字段
```javascript
{
    overall_score: 0-100,  // 总体分数
    manual_evaluation: {
        total_score: 0-100  // 新增：人工评估总分
    },
    final_prompt: string,   // 新增：最终提示词
    workflow: object        // 新增：工作流配置
}
```

---

## ✅ 验证状态

- ✅ 前端构建成功 (1177 modules, 19.66s)
- ✅ 所有修改的Vue组件语法检查通过
- ✅ 导出数据结构完整
- ✅ 错误处理机制完善

---

## 📊 影响范围

### 受影响的用户功能
- ✅ 代码生成流程：改进了用户体验反馈
- ✅ 人工评估：提供了更清晰的保存机制
- ✅ 结果导出：新增了更多导出选项
- ✅ 截屏功能：修复了白屏问题

### API调用
- `POST /export` - 增强的导出数据结构
- `POST /update_manual_evaluation` - 保存人工评估

---

## 🚀 部署建议

1. 更新前端构建文件 (dist/)
2. 测试导出功能是否与后端兼容
3. 验证截屏功能在不同浏览器上的效果
4. 检查导出JSON文件格式

---

