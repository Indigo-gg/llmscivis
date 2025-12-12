# 代码修正成本分析工具 - 使用指南

## 概述

`draw_correct_cost.py` 是一个自动化工具，用于：
1. **扫描所有模型**：自动遍历 `experiment_results/generated_code` 下的所有模型子文件夹
2. **计算差异统计**：比对原始HTML文件和修正后的文件，计算行数差异
3. **生成汇总报告**：输出详细的成本分析报告（TXT格式）
4. **导出数据**：保存为JSON格式便于其他脚本使用
5. **生成可视化图表**：自动生成柱状图对比不同模型的修正成本

## 支持的命名规则

脚本支持两种文件命名规则：
- 规则1：`xxx.html` + `xxx_modified.html` （例如：chatgpt-4o-without-rag）
- 规则2：`xxx.html` + `xxx_corrt.html` （例如：qwen_plus）

## 基本使用

### 1. 默认运行（推荐）
```bash
cd d:\Pcode\LLM4VIS\llmscivis
python experiment_results/analys/draw_correct_cost.py
```

**效果**：
- 自动扫描 `experiment_results/generated_code` 下所有模型
- 生成 `diff_analysis_report.txt` （汇总报告）
- 生成 `diff_analysis_data.json` （数据备份）
- 显示第一张图表：模型成本对比

### 2. 只生成报告，不显示图表
```bash
python experiment_results/analys/draw_correct_cost.py --no-plot
```

**适用场景**：在无图形界面的服务器上运行

### 3. 指定custom输入和输出路径
```bash
python experiment_results/analys/draw_correct_cost.py --root-folder "D:\path\to\generated_code" --output-dir "D:\path\to\output"
```

**参数说明**：
- `--root-folder`：generated_code 文件夹的完整路径
- `--output-dir`：输出报告的目录

### 4. 只重新生成图表（从缓存数据）
```bash
python experiment_results/analys/draw_correct_cost.py --plot-only
```

**适用场景**：
- 已经生成过 `diff_analysis_data.json` 
- 只想重新调整图表样式或参数
- 节省扫描和计算时间

## 输出文件

### 1. diff_analysis_report.txt（文本报告）
包含以下信息：
- **按模型分类**：每个模型的每个任务的差异统计
  - 总差异行数：新增行 + 删除行
  - 新增行数：添加的代码行数
  - 删除行数：移除的代码行数
- **汇总统计**：按任务分类和按模型分类的总计
- **易读格式**：用分隔线和缩进组织

示例输出：
```
模型: chatgpt-4o
──────────────────────────────

  任务: cutter
    总差异行数: 3
    新增行数: 2
    删除行数: 1

  任务: isosurface
    总差异行数: 56
    新增行数: 28
    删除行数: 28

  模型总计: 62 行
```

### 2. diff_analysis_data.json（数据备份）
结构化的JSON数据，便于其他脚本处理：
```json
{
  "model_name": {
    "task_name": {
      "added": 28,        // 新增行数
      "deleted": 28,      // 删除行数
      "total": 56,        // 总差异行数
      "changed": 17       // 修改行数
    }
  }
}
```

### 3. 柱状图（matplotlib弹窗）
显示所有模型在各任务上的修正成本对比

## 核心函数说明

### calculate_diff_stats(file1_path, file2_path)
计算两个文件的差异统计
- **输入**：原始文件路径、修正文件路径
- **输出**：包含 added, deleted, total, changed 的字典
- **特点**：忽略空白符和缩进，只关注实际内容差异

### find_file_pairs(folder_path)
在文件夹中查找文件对
- **输入**：扫描的文件夹路径
- **输出**：(原始文件, 修正文件) 的元组列表
- **特点**：支持两种命名规则

### scan_all_models(root_folder)
扫描所有模型子文件夹
- **输入**：generated_code 文件夹的路径
- **输出**：{model_name: {task_name: stats_dict}}

### generate_summary_report(results, output_file)
生成汇总报告文件
- **输入**：扫描结果字典、输出文件路径
- **输出**：写入格式化的TXT报告

### prepare_plotting_data(results)
提取绘图数据
- **输入**：扫描结果字典
- **输出**：({model_name: [task1, task2, ...]}, [任务列表])

## 扩展使用场景

### 场景1：新增模型后重新分析
```bash
# 在 experiment_results/generated_code 中新增了模型文件夹后
python experiment_results/analys/draw_correct_cost.py
```

### 场景2：与旧数据比对
```python
# 在Python脚本中加载旧JSON数据
import json
with open('old_diff_analysis_data.json', 'r') as f:
    old_results = json.load(f)
# 可进行对比分析
```

### 场景3：自定义图表样式
编辑脚本中的以下函数来自定义：
- `plot_model_cost_comparison()`：修改颜色、字体、标题等
- `plot_rag_impact_comparison()`：修改RAG对比图的数据和样式

## 常见问题

### Q1：为什么找不到某些模型？
**A**：检查以下条件：
- 模型文件夹中是否同时存在 `*.html` 和修正文件（`*_modified.html` 或 `*_corrt.html`）
- 文件夹名称是否正确（区分大小写）

### Q2：能否只分析某个模型？
**A**：可以通过修改 `scan_all_models()` 函数中的目录过滤逻辑，或者：
```python
# 在脚本底部添加
if __name__ == "__main__":
    # 只扫描 qwen_plus 模型
    results = {'qwen_plus': scan_all_models(...)}
```

### Q3：图表显示不出来怎么办？
**A**：
1. 运行 `python experiment_results/analys/draw_correct_cost.py --no-plot`
2. 使用 `--plot-only` 尝试只显示图表
3. 检查是否安装了 matplotlib：`pip install matplotlib`

### Q4：如何在脚本中使用这些函数？
**A**：
```python
from experiment_results.analys.draw_correct_cost import (
    scan_all_models,
    calculate_diff_stats,
    prepare_plotting_data
)

results = scan_all_models('path/to/generated_code')
plot_data, task_list = prepare_plotting_data(results)
```

## 性能注意事项

- 脚本会遍历所有模型和文件，对于大量文件可能需要几秒钟
- JSON数据保存后可使用 `--plot-only` 快速重新生成图表
- 建议定期备份 `diff_analysis_data.json` 以保留历史数据

## 版本历史

### v2.0（当前版本）
- ✅ 支持自动扫描所有模型
- ✅ 支持两种命名规则
- ✅ 集成 diff_corrt.py 的差异计算逻辑
- ✅ 命令行参数支持
- ✅ 输出JSON数据备份
- ✅ matplotlib 兼容性改进

### v1.0（原始版本）
- 硬编码数据
- 仅显示示例图表

## 联系和反馈

如有问题或建议，请检查：
1. 文件夹结构是否正确
2. 文件命名是否符合规则
3. Python版本是否 >= 3.6
4. 必要的库是否已安装：matplotlib, numpy
