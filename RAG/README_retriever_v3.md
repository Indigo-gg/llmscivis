# retriever_v3.py 使用说明

## 功能概述

`retriever_v3.py` 是 NL2Vis 项目中基于关键词检索的代码检索模块，它实现了以下功能：

1. **关键词提取**：从用户查询中提取 VTK.js 模块名称
2. **数据库检索**：基于关键词直接查询 MongoDB 数据库
3. **加权重排序**：根据子查询权重对检索结果进行重排序
4. **结果导出**：将检索结果保存到 Excel 文件中

## 主要特性

- 纯关键词检索，无需向量计算
- 支持子查询权重配置
- 检索结果自动保存到 Excel
- 兼容原有接口格式

## 使用方法

### 1. 准备输入数据

输入数据应为 Excel 文件，包含以下格式的 `splited_prompt` 列：

```json
[
  {
    "description": "渲染一个球体",
    "weight": 8
  },
  {
    "description": "设置背景为蓝色",
    "weight": 3
  }
]
```

### 2. 运行检索器

```bash
python retriever_v3.py
```

### 3. 查看输出结果

程序会生成以下输出：
- 控制台日志
- 文本日志文件 `output_weighted.txt`
- Excel 结果文件 `retrieval_results_v3_output.xlsx`

## 输出格式

Excel 输出文件包含以下列：
- `raw_results`: 初筛结果（JSON 格式）
- `reranked_results`: 重排序结果（JSON 格式），包含：
  - 文件路径
  - FAISS ID
  - 描述信息
  - VTK.js 模块列表
  - 重排序得分
  - 匹配关键词
  - 匹配说明

## 配置说明

主要配置项：
- `DB_HOST`: MongoDB 主机地址
- `DB_PORT`: MongoDB 端口
- `DB_NAME`: 数据库名称
- `COLLECTION_NAME`: 集合名称

## 注意事项

1. 确保 MongoDB 服务正在运行
2. 确保数据库中有正确的代码片段数据
3. 输入 Excel 文件必须包含 `第二期实验数据` 工作表
4. 输出文件将覆盖同名文件