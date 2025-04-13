#NL2Vis 
基于LLM生成vtkjs框架的可视化


# benchmark

设计一个用于评估NL2Vis 的基准


# RAG

通过RAG增强LLM生成可视化的能力



## 构建向量数据库

### 需要把待处理的文件放入data目录
> data
>   - fassi_cache(里面内容在执行embedding.py后自动生成)
>   - vtk-example(样本代码)
>      - vtk_api
>          - code.html
>          - description.txt
### 执行构建代码
```shell
python RAG\embedding.py 
#因缺乏依赖执行失败时，尝试执行以下命令
# pip install -r 'requirements.txt'

```


# Project backend
## 安装依赖
```shell
    pip install -r 'requirements.txt'
```

## 运行
```shell
python app.py
```

# Project frontend
## 进入front目录
```shell
    cd front
```

## 安装依赖
```shell
    npm install
```

## 运行
```shell
    npm run dev
```

# 一键运行(linux/windows)
```shell
    bash run.sh
```
## 以下文件包含测试函数

- llm_agent/rag_agent.py
- llm_agent/ollma_chat.py
- llm_agent/prompt_agent.py
- retriever.py
