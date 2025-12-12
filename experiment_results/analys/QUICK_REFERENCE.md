# 快速参考卡

## 什么是 draw_correct_cost.py？

一个**自动化分析工具**，可以：
1. 📂 扫描所有LLM生成的代码文件
2. 📊 计算每个模型每个任务的修正成本（行数差异）
3. 📄 生成详细的汇总报告
4. 💾 导出JSON数据供其他脚本使用
5. 📈 自动生成对比图表

## 快速命令

| 场景 | 命令 |
|-----|------|
| **完整分析**（推荐） | `python draw_correct_cost.py` |
| 只生成报告 | `python draw_correct_cost.py --no-plot` |
| 只显示图表 | `python draw_correct_cost.py --plot-only` |
| 自定义路径 | `python draw_correct_cost.py --root-folder <path> --output-dir <path>` |
| 查看帮助 | `python draw_correct_cost.py -h` |

## 输出文件说明

### diff_analysis_report.txt
📋 **人类可读的汇总报告**
- 按模型列出每个任务的差异行数
- 按任务汇总所有模型的成本
- 按模型汇总每个模型的总成本

### diff_analysis_data.json
💾 **结构化数据备份**
```json
{
  "模型名": {
    "任务名": {
      "added": 新增行数,
      "deleted": 删除行数,
      "total": 总差异行数,
      "changed": 修改行数
    }
  }
}
```

## 支持的文件命名规则

| 模型示例 | 命名规则 |
|---------|---------|
| `qwen_plus` | `xxx.html` + `xxx_corrt.html` |
| `chatgpt-4o-without-rag` | `xxx.html` + `xxx_modified.html` |

## 关键概念

- **总差异行数** = 新增行数 + 删除行数
- **新增行数** = 修正文件中新添加的代码行
- **删除行数** = 原始文件中被删除的代码行
- **修改行数** = 同一行内容被修改的次数

## 典型输出示例

```
模型: chatgpt-4o
──────────────────────────────
  任务: isosurface
    总差异行数: 56     ← 修正成本最大的任务
    新增行数: 28
    删除行数: 28
  
  模型总计: 62 行      ← ChatGPT-4o的平均修正成本最低
```

## 使用技巧

✅ **第一次运行**
```bash
python draw_correct_cost.py  # 生成报告、数据和图表
```

✅ **快速重新绘图**（无需重新扫描）
```bash
python draw_correct_cost.py --plot-only  # 快10倍！
```

✅ **在批处理脚本中使用**
```bash
python draw_correct_cost.py --no-plot  # 不显示图表窗口
```

✅ **程序中导入使用**
```python
from experiment_results.analys.draw_correct_cost import scan_all_models
results = scan_all_models('path/to/generated_code')
```

## 故障排查

| 问题 | 解决方案 |
|-----|---------|
| 找不到模型 | 检查文件夹中是否有 `.html` 和 `_modified.html`/`_corrt.html` 文件对 |
| 图表不显示 | 运行 `python draw_correct_cost.py --no-plot` 或检查 matplotlib 是否安装 |
| 权限错误 | 确保对输出目录有写权限 |
| JSON 加载失败 | 删除旧的 `diff_analysis_data.json`，重新运行完整分析 |

## 文件位置

```
experiment_results/
├── generated_code/          ← 扫描源文件夹（包含各模型子目录）
│   ├── chatgpt-4o/
│   ├── qwen_plus/
│   ├── chatgpt-4o-without-rag/
│   └── ...
└── analys/
    ├── draw_correct_cost.py  ← 本脚本
    ├── diff_analysis_report.txt      ← 生成的报告
    ├── diff_analysis_data.json       ← 生成的数据
    └── USAGE_GUIDE.md                ← 完整使用指南
```

---

**提示**：本工具集成了 `diff_corrt.py` 的核心逻辑，自动支持扫描多模型目录结构。
