#NL2Vis 
基于LLM生成vtkjs框架的可视化


# benchmark

设计一个用于评估NL2Vis 的基准


# RAG

通过RAG增强LLM生成可视化的能力

## 构建向量数据库

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


## 以下文件包含测试函数

- rag_agent.py
- retriever.py
