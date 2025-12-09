# 🚀 快速切换到 Retriever V3

## 一行代码修改

### 修改文件: `app.py`

**找到第 111 行**:
```python
rag_agent = RAGAgent()
```

**替换为**:
```python
rag_agent = RAGAgent(use_v3=True)
```

**完整代码片段** (第 110-118 行):
```python
if obj['workflow']['rag']:
    rag_agent = RAGAgent(use_v3=True)  # 👈 添加 use_v3=True
    # 现在传递分析结果列表给 RAG agent
    # RAG agent 会提取 description 和其他元信息用于检索
    final_prompt = rag_agent.search(analysis, obj['prompt'])
    print('rag prompt\n',final_prompt)
    
    # Extract retrieval results for frontend display
    retrieval_results = rag_agent.get_retrieval_metadata()
```

## ✅ 完成！

就这么简单！现在你的系统将使用 **纯关键词检索**（retriever_v3）而不是 FAISS 向量检索。

## 🔍 验证修改

运行测试脚本验证：

```bash
python test_v3_integration.py
```

或者直接启动应用：

```bash
python app.py
```

查看日志中是否显示：
```
[RAGAgent] 使用 VTKSearcherV3 (关键词检索)
```

## ⚙️ 切换回 V2

如果需要切回 FAISS 向量检索，改为：
```python
rag_agent = RAGAgent(use_v3=False)
```

## 🎯 优势

使用 retriever_v3 的优势：
1. ✅ **不依赖 FAISS** - 只需要 MongoDB
2. ✅ **精确匹配** - 基于 VTK 模块名称的关键词匹配
3. ✅ **权重排序** - 支持基于查询权重的智能排序
4. ✅ **更快** - 直接数据库查询，无需向量计算
5. ✅ **更透明** - 可以看到匹配的具体关键词

---

**注意**: 确保 MongoDB 已启动并包含数据！
