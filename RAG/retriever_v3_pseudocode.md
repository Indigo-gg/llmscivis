# VTKSearcherV2 检索算法伪代码

## 整体架构

```
系统组成：
├── MongoDBManager: 数据库管理器
├── analyze_query: 查询分析器
├── WeightedRanker: 加权排序器
└── VTKSearcherV2: 检索控制器
```

---

## 模块1: 查询分析 (analyze_query)

**功能说明**: 从用户查询文本中提取VTK.js模块关键词

**算法流程**:
```
输入: query (用户查询字符串)
输出: analyzed_data (包含提取的模块列表)

函数 analyze_query(query):
    初始化 analyzed_data = {modules: []}
    转换 lower_query = query.toLowerCase()
    
    // 步骤1: 正则提取VTK.js模块名
    定义 module_patterns = [
        "vtk\.?[\w\.]*?vtk([A-Z]\w+)",      // 匹配 vtk.Namespace.vtkClassName
        "vtk\.[a-z]+\.[a-z]+\.[a-zA-Z]+",   // 匹配完整路径
        "(vtk[A-Z]\w+)"                      // 匹配独立 vtkClassName
    ]
    
    对于 每个 pattern in module_patterns:
        matches = 正则匹配(pattern, query)
        对于 每个 match in matches:
            如果 match 以 'vtk.' 开头:
                提取最后一部分并添加到 modules
            否则如果 match 以 'vtk' 开头:
                直接添加到 modules
    
    // 步骤2: 常用模块简写匹配
    获取 common_modules = app_config.VTKJS_COMMON_APIS
    对于 每个 mod in common_modules:
        如果 mod.toLowerCase() 在 lower_query 中 并且 是完整单词:
            添加 mod 到 modules
    
    // 步骤3: 去重
    modules = 去重(modules)
    
    返回 analyzed_data
```

**公式**: 无复杂公式，纯文本匹配

---

## 模块2: 数据库查询 (MongoDBManager)

**功能说明**: 根据模块列表从MongoDB检索相关代码文档

**算法流程**:
```
输入: modules (模块名列表)
输出: docs (匹配的文档列表)

函数 find_docs_by_modules(modules):
    如果 modules 为空 或 数据库未连接:
        返回 []
    
    // 构造正则查询
    初始化 regex_list = []
    对于 每个 module in modules:
        创建正则表达式: /module$/i  // 匹配字符串结尾，忽略大小写
        添加到 regex_list
    
    // MongoDB查询
    query = {
        "meta_info.vtkjs_modules": {
            $in: regex_list
        }
    }
    
    执行查询 cursor = collection.find(query)
    返回 list(cursor)
```

**关键点**: 使用正则后缀匹配，解决 `vtkActor` 无法匹配 `vtk.Rendering.Core.vtkActor` 的问题

---

## 模块3: 加权排序器 (WeightedRanker)

### 3.1 核心打分算法 (calculate_scores)

**功能说明**: 根据带权重的子查询对候选文档进行打分

**算法流程**:
```
输入: query_list_with_weights (带权重的子查询列表)
      格式: [{description: "查询1", weight: 8}, {description: "查询2", weight: 3}]
输出: 更新 doc_scores 和 doc_details

函数 calculate_scores(query_list_with_weights):
    // 阶段1: 权重归一化
    初始化 total_weight = 0
    初始化 valid_queries = []
    
    对于 每个 query_item in query_list_with_weights:
        提取 weight = query_item.get('weight', 5)
        转换 weight 为浮点数
        标记 query_item['parsed_weight'] = weight
        累加 total_weight += weight
        添加到 valid_queries
    
    如果 total_weight == 0:
        total_weight = 1  // 防止除零
    
    // 阶段2: 遍历子查询进行打分
    对于 每个 query_item in valid_queries:
        提取 q_text = query_item['description']
        提取 q_weight = query_item['parsed_weight']
        
        // 计算归一化权重（0.0 ~ 1.0）
        normalized_weight = q_weight / total_weight
        
        // 提取查询关键词
        analyzed = analyze_query(q_text)
        q_modules = analyzed['modules']
        
        如果 q_modules 为空:
            跳过此查询
        
        // 阶段3: 遍历候选文档计算得分
        对于 每个 doc in raw_docs:
            获取 doc_id = doc.faiss_id 或 doc.file_path
            
            // 计算命中数
            (hits, matched_keywords) = _count_hits(doc, q_modules)
            
            如果 hits > 0:
                // 核心打分公式
                score_increment = hits × normalized_weight
                
                // 累加得分
                doc_scores[doc_id] += score_increment
                
                // 记录匹配详情
                记录匹配信息到 doc_details[doc_id]
```

**核心公式说明**:

```
归一化权重计算:
normalized_weight_i = weight_i / Σ(weight_j)
其中: weight_i 为第 i 个子查询的权重
     Σ(weight_j) 为所有子查询权重之和

文档得分计算:
Score(doc) = Σ(hits_i × normalized_weight_i)
其中: hits_i 为文档匹配第 i 个查询的关键词数量
     normalized_weight_i 为第 i 个查询的归一化权重
```

**示例**:
```
假设有两个子查询:
- 查询1: "render a cone", weight=10
- 查询2: "set background to blue", weight=3

总权重 = 10 + 3 = 13

归一化权重:
- 查询1: 10/13 ≈ 0.77
- 查询2: 3/13 ≈ 0.23

假设某文档A:
- 匹配查询1的2个关键词 (hits=2)
- 匹配查询2的1个关键词 (hits=1)

文档A得分 = 2 × 0.77 + 1 × 0.23 = 1.54 + 0.23 = 1.77
```

---

### 3.2 命中计数算法 (_count_hits)

**功能说明**: 计算文档命中了多少个查询关键词

**算法流程**:
```
输入: doc (文档对象), query_modules (查询模块列表)
输出: (count, matched) 命中数和匹配的关键词列表

函数 _count_hits(doc, query_modules):
    // 提取文档信息
    doc_modules = doc.meta_info.vtkjs_modules
    doc_desc = doc.meta_info.description.toLowerCase()
    
    // 转换为小写集合
    doc_modules_lower = set(doc_modules.toLowerCase())
    
    初始化 count = 0
    初始化 matched = []
    
    // 遍历查询关键词
    对于 每个 qm in query_modules:
        qm_lower = qm.toLowerCase()
        qm_clean = qm_lower.replace('vtk', '')  // vtkActor -> Actor
        
        初始化 hit = false
        
        // A. 检查模块列表匹配
        对于 每个 dm in doc_modules_lower:
            如果 qm_lower == dm 或 dm.endsWith(qm_clean):
                hit = true
                跳出循环
        
        // B. 检查描述匹配
        如果 not hit 并且 qm_lower 在 doc_desc 中:
            hit = true
        
        // 统计命中
        如果 hit:
            count += 1
            添加 qm 到 matched
    
    返回 (count, matched)
```

---

### 3.3 排序输出 (get_ranked_results)

**功能说明**: 返回按得分排序的Top-K文档

**算法流程**:
```
输入: top_k (返回文档数量，默认6)
输出: ranked_list (排序后的文档列表)

函数 get_ranked_results(top_k=6):
    初始化 ranked_list = []
    
    对于 每个 (doc_id, score) in doc_scores:
        获取 details = doc_details[doc_id]
        获取 doc = details["doc_obj"]
        
        // 将计算数据写入文档对象
        doc['rerank_score'] = score
        doc['match_explanation'] = details["matches"]
        doc['matched_keywords'] = list(details["all_matched_keywords"])
        
        添加 doc 到 ranked_list
    
    // 按得分降序排序
    ranked_list.sort(key=lambda x: x['rerank_score'], reverse=True)
    
    返回 ranked_list[0:top_k]
```

---

## 模块4: 检索控制器 (VTKSearcherV2)

**功能说明**: 协调整个检索流程，从查询到返回Prompt

**主流程算法**:
```
输入: query (完整用户请求), query_list (分割的子查询列表)
输出: prompt (最终生成的提示词)

函数 search(query, query_list):
    // ===== 阶段1: 广度召回 (Recall) =====
    初始化 all_candidate_docs = {}  // 用于去重
    初始化 temp_raw_history = []
    
    对于 每个 q_item in query_list:
        // 兼容处理
        如果 q_item 是字符串:
            转换为 {description: q_item, weight: 5}
        
        提取 q_text = q_item['description']
        
        // 分析查询提取关键词
        analyzed = analyze_query(q_text)
        
        // 数据库查询
        docs = mongo_manager.find_docs_by_modules(analyzed['modules'])
        
        // 记录原始结果
        docs_copy = []
        对于 每个 doc in docs:
            创建 doc 副本并标记来源查询
            添加到 docs_copy
            
            // 去重存入候选池
            获取 doc_id = doc.faiss_id 或 doc.file_path
            如果 doc_id 不在 all_candidate_docs:
                all_candidate_docs[doc_id] = doc
        
        添加 docs_copy 到 temp_raw_history
    
    candidate_list = all_candidate_docs.values()
    
    // ===== 阶段2: 深度精排 (Rerank) =====
    // 初始化加权排序器
    ranker = WeightedRanker(candidate_list)
    
    // 计算得分
    ranker.calculate_scores(query_list)
    
    // 获取Top-K结果
    final_results = ranker.get_ranked_results(top_k=6)
    
    // 保存历史记录
    保存 temp_raw_history 到 raw_results_history
    保存 final_results 到 reranked_results_history
    
    // ===== 阶段3: 构建Prompt (Context) =====
    prompt = _build_prompt(query, final_results)
    
    返回 prompt
```

---

## 完整工作流程示意图

```
┌─────────────────────────────────────────────────────────┐
│              用户输入处理                                │
│  输入: "render a cone with blue background"             │
│  子查询: [{desc: "render cone", w: 10},                │
│          {desc: "blue background", w: 3}]              │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         阶段1: 广度召回 (Recall)                         │
├─────────────────────────────────────────────────────────┤
│  对于每个子查询:                                         │
│    1. analyze_query() → 提取关键词                      │
│       查询1: [vtkConeSource, vtkRenderer]               │
│       查询2: [vtkRenderer]                              │
│                                                          │
│    2. MongoDB检索 → 召回相关文档                        │
│       查询1 召回: [doc1, doc2, doc3, doc4]              │
│       查询2 召回: [doc3, doc5]                          │
│                                                          │
│    3. 去重合并 → 候选文档池                             │
│       候选池: [doc1, doc2, doc3, doc4, doc5]           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         阶段2: 深度精排 (Rerank)                         │
├─────────────────────────────────────────────────────────┤
│  1. 权重归一化:                                          │
│     total_weight = 10 + 3 = 13                          │
│     查询1权重: 10/13 ≈ 0.77                             │
│     查询2权重: 3/13 ≈ 0.23                              │
│                                                          │
│  2. 文档打分 (对每个候选文档):                          │
│     doc1: hits_q1=2, hits_q2=0                          │
│           score = 2×0.77 + 0×0.23 = 1.54               │
│                                                          │
│     doc3: hits_q1=1, hits_q2=1                          │
│           score = 1×0.77 + 1×0.23 = 1.00               │
│                                                          │
│     doc5: hits_q1=0, hits_q2=1                          │
│           score = 0×0.77 + 1×0.23 = 0.23               │
│                                                          │
│  3. 排序: [doc1(1.54), doc2(...), doc3(1.00), ...]     │
│                                                          │
│  4. 截取Top-6                                            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         阶段3: 构建Prompt                                │
├─────────────────────────────────────────────────────────┤
│  拼接最终Prompt:                                         │
│    - 用户需求                                            │
│    - Top-6 代码示例 (包含得分、匹配关键词等)            │
│                                                          │
│  输出给LLM生成代码                                       │
└─────────────────────────────────────────────────────────┘
```

---

## 关键算法特点总结

### 1. **两阶段检索架构**
- **召回阶段**: 广度优先，保证覆盖率
- **排序阶段**: 精准打分，保证相关性

### 2. **加权评分机制**
- 归一化权重确保公平性
- 累加得分反映综合相关度
- 命中数量体现匹配程度

### 3. **模块匹配策略**
- 正则表达式提取关键词
- 后缀匹配解决命名空间问题
- 描述文本作为补充匹配

### 4. **时间复杂度分析**
```
假设:
- n: 子查询数量
- m: 候选文档数量
- k: 每个文档的模块数

召回阶段: O(n × DB_query)
排序阶段: O(n × m × k)
总体复杂度: O(n × m × k)
```
