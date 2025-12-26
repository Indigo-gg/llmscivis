# LLM4VIS: Structure-Aware Scientific Visualization Pipeline Construction

**Toward Reliable Scientific Visualization Pipeline Construction with Structure-Aware Retrieval-Augmented LLMs** 

一个基于大语言模型（LLM）的科学可视化管道生成系统，通过**结构感知的检索增强生成**（Structure-Aware RAG）工作流，自动从自然语言描述生成**可执行的**VTK.js可视化管道。

## 项目简介

### 研究背景

科学可视化管道包含严格的执行依赖关系，包括数据加载、变换和渲染等多个阶段。与图表可视化不同，科学可视化管道**必须**所有关键阶段都存在且正确排序才能执行。因此，从自然语言描述生成可执行的科学可视化管道是一个**可靠性问题**而非单纯的视觉质量问题。

### 核心创新点

LLM4VIS是一个研究系统，旨在从功能和可靠性的江湖中提供程序型可视化管道的可靠生成。主要创新包括：

1. **结构感知的RAG工作流**

   - 显式编程管道结构、模块兼容性和执行顺序
   - 将VTK.js代码示例按管道阶段对齐组织
   - 支持正确的模块选择、参数配置和执行顺序
2. **可靠性评估框架**

   - 引入**修正成本（Correction Cost）**度量标准
   - 衡量获得有效管道所需的手动干预量
   - 以管道可执行性和修正成本作为可靠性指标
3. **人在回路的交互式分析**

   - 前端提供轻量级界面支持人机交互
   - 用户可检查检索评分、生成的管道步骤、宜执行容器中的管道
   - 针对改进提供程度反馈
4. **多LLM系统评估**

   - 跨多个LLM和多阶段可视化任务的评估
   - 分析结构化上下文对管道可执行性的影响
   - 识别RAG难以解决的语义和结构挑战

### 系统特性

- **提示词拓展（Inquiry Expansion）**：将自然语言查询拓展为结构化的VTK模块需求
- **结构感知RAG检索**：从VTK代码库中检索管道对齐的示例代码和API使用方法
- **多模型支持**：支持Ollama本地模型、DeepSeek、阿里通义千问等多种LLM
- **交互式编辑和验证**：前端提供代码编辑、可视化预览和管道执行反馈
- **结构化评估**：定量评估管道可执行性、修正成本和失败模式

## 快速开始

### 系统要求

- Windows 10/11
- Python 3.12
- Node.js 14+ (用于前端开发)
- MongoDB (用于数据存储)
- Ollama (用于本地LLM推理，可选)

### 一键启动

最简单的方式是运行启动脚本：

```batch
run.bat
```

这个脚本会自动：

1. 创建必要的目录结构
2. 启动MongoDB服务（如果未运行）
3. 启动数据集服务器
4. 安装并启动Python Flask后端（端口5001）
5. 安装并启动前端开发服务器（端口5173）

启动完成后，访问 `http://localhost:5173` 进入应用界面。

### 手动启动

#### 1. 后端启动

```powershell
# 激活Python环境
conda activate llm3.12

# 安装依赖
pip install -r requirements.txt

# 启动Flask应用
python app.py
```

后端服务运行在 `http://localhost:5001`

#### 2. 前端启动

```powershell
cd front

# 安装依赖（首次）
npm install

# 启动开发服务器
npm run dev
```

前端服务运行在 `http://localhost:5173`

## 项目结构

### 核心目录

#### 📁 `front/` - 前端应用

- **用途**：Web用户界面
- **技术**：Vue 3 + Vite
- **主要模块**：
  - `components/` - UI组件库
  - `view/` - 页面视图
  - `api/` - API调用接口
  - `utils/` - 工具函数
  - `routers/` - 路由配置

#### 📁 `llm_agent/` - LLM代理模块

- **用途**：核心LLM调用和处理逻辑
- **主要文件**：
  - `ollma_chat.py` - Ollama本地LLM调用
  - `rag_agent.py` - RAG检索代理
  - `prompt_agent.py` - 提示词拓展和查询分析
  - `evaluator_agent.py` - 代码评估模块
  - `code_agent.py` - 代码生成代理
  - `data_agent.py` - 数据处理代理

#### 📁 `RAG/` - 检索增强生成模块

- **用途**：构建和维护VTK代码向量数据库
- **主要文件**：
  - `embedding_v4.py` - 最新的文本嵌入和向量化模块
  - `retriever_v3.py` - 检索引擎（当前使用版本）
  - `init_database.py` - 数据库初始化
  - `mongodb.py` - MongoDB连接管理
  - `vtk_code_meta_extract.py` - VTK代码元数据提取

#### 📁 `config/` - 配置模块

- **用途**：应用配置和API密钥管理
- **主要文件**：
  - `app_config.py` - 应用配置（端口、路径、API地址等）
  - `ollama_config.py` - Ollama模型配置
  - `secrets.py` - API密钥（需创建，不提交到git）

#### 📁 `utils/` - 工具模块

- **用途**：通用工具函数
- **主要文件**：
  - `dataset.py` - 数据集管理
  - `diff/` - 代码差异分析
  - `prompt-sample/` - 提示词样本

#### 📁 `experiment_results/` - 实验结果

- **用途**：保存评估和测试结果
- **子目录**：
  - `generated_code/` - 生成的代码结果
  - `backup/` - 备份数据
  - `analys/` - 分析报告

### 其他重要文件

- `app.py` - Flask应用主文件，定义所有API端点
- `requirements.txt` - Python依赖
- `run.bat` - Windows一键启动脚本

## API端点

后端提供以下主要API端点，支持结构感知的管道生成工作流：

| 端点           | 方法 | 功能                       |
| -------------- | ---- | -------------------------- |
| `/generate`  | POST | 从自然语言问题生成管道     |
| `/expand`    | POST | 提示词拓展（将问题结构化） |
| `/retrieval` | POST | 执行结构感知RAG检索        |
| `/upload`    | POST | 上传数据文件               |

## 工作流程

```
用户输入 → 提示词拓展(可选) → 结构感知RAG检索(可选) → LLM生成 → 管道执行和验证 → 返回结果
```

**核心工作流程特点**：

- **结构对齐检索**：RAG系统检索的代码示例与管道阶段显式对齐
- **人机交互**：用户可在浏览器中实时执行生成的管道，获取反馈
- **迭代改进**：基于执行反馈进行目标修正
- **可靠性评估**：实时评估管道的可执行性和修正成本

## 配置说明

### Python环境

项目使用Python 3.12环境 `llm3.12`。在运行任何Python脚本前，需要激活此环境：

```powershell
conda activate llm3.12
```

### API密钥配置

在 `config/secrets.py` 中配置各LLM的API密钥（该文件不提交到仓库）：

```python
class Secrets:
    deepseek_apikey = "your_deepseek_key"
    qwen_apikey = "your_qwen_key"
    aihub_apikey = "your_aihub_key"
    cst_apikey = "your_cst_key"
```

## 测试

以下文件包含测试函数：

- `llm_agent/rag_agent.py`
- `llm_agent/ollma_chat.py`
- `llm_agent/prompt_agent.py`
- `RAG/retriever_v3.py`

## 数据构建

### 构建RAG向量数据库

```powershell
conda activate llm3.12
python RAG/embedding_v4.py
```

数据源需放在 `data/` 目录下，结构如下：

```
data/
├── vtkjs-examples/
│   ├── benchmark/
│   └── prompt-sample/
│       └── vtk_api/
│           ├── code.html
│           └── description.txt
└── faiss_cache/  (embedding后自动生成)
```

## 主要依赖

- **后端框架**：Flask
- **向量数据库**：FAISS
- **向量模型**：sentence-transformers
- **LLM调用**：LangChain + Ollama/OpenAI API
- **数据库**：MongoDB
- **前端框架**：Vue 3
- **前端构建**：Vite

## 技术事特誉

### 结构感知的RAG

LLM4VIS的检索系统不仅检索代码软件，还显式编程管道结构、模块兼容性和执行顺序。相比于樇晷的文本检索，这种结构感知的方法提高了管道可执行性。

### 修正成本指标

LLM4VIS引入了修正成本（Correction Cost）指标，衡量获得有效管道所需的手动干预量。相比于简单的可执行性指标，修正成本更好地反映了生成管道的实际可用性。

### 人在回路的交互式洞察

LLM4VIS不是一个完全自动化的系统，而是一个人机交互的洞察平台。用户可以检查检索评分、生成的管道步骤、在浏览器中执行管道，並不断扩充反馈以改进管道。

## 技术创新点

### 结构感知的RAG

LLM4VIS的检索系统不仅检索代码，还显式编程管道结构、模块兼容性和执行顺序。相比于晦暗的文本检索，这种结构感知的方法提高了管道可执行性。

### 修正成本指标

LLM4VIS引入了修正成本（Correction Cost）指标，衡量获得有效管道所需的手动干预量。相比于简单的可执行性指标，修正成本更好地反映了生成管道的实际可用性。

### 人在回路的交互式洞察

LLM4VIS不是一个完全自动化的系统，而是一个人机交互的洞察平台。用户可以检查检索评分、生成的管道步骤、在浏览器中执行管道，并提供改进的反馈。

## 常见问题

### MongoDB 连接失败

确保了MongoDB服务正在运行。使用 `mongod` 启动MongoDB服务：

```powershell
mongod --dbpath=data/db --port 27017
```

### Ollama模型加载失败

确保Ollama服务在指定的URL运行（默认 `http://127.0.0.1:11435`）。可在 `config/ollama_config.py` 中修改配置。

### 前端连接后端失败

确保后端服务运行在 `http://localhost:5001`，且CORS配置正确。
