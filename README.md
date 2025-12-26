# LLM4VIS: Structure-Aware Scientific Visualization Pipeline Construction

**Toward Reliable Scientific Visualization Pipeline Construction with Structure-Aware Retrieval-Augmented LLMs**

An LLM-based scientific visualization pipeline generation system that automatically generates **executable** VTK.js visualization pipelines from natural language descriptions via a **Structure-Aware Retrieval-Augmented Generation** (Structure-Aware RAG) workflow.

## Project Introduction

### Research Background

Scientific visualization pipelines involve strict execution dependencies, including stages such as data loading, transformation, and rendering. Unlike chart visualization, a scientific visualization pipeline **must** have all key stages present and correctly ordered to execute. Therefore, generating executable scientific visualization pipelines from natural language descriptions is a **reliability issue** rather than merely a visual quality issue.

### Core Innovations

LLM4VIS is a research system designed to provide reliable generation of procedural visualization pipelines amidst the challenges of functionality and reliability. Key innovations include:

1. **Structure-Aware RAG Workflow**
   * Explicitly models pipeline structure, module compatibility, and execution order.
   * Organizes VTK.js code examples aligned by pipeline stages.
   * Supports correct module selection, parameter configuration, and execution sequencing.
2. **Reliability Evaluation Framework**
   * Introduces the **Correction Cost** metric.
   * Measures the amount of manual intervention required to obtain a valid pipeline.
   * Uses pipeline executability and correction cost as reliability indicators.
3. **Human-in-the-Loop Interactive Analysis**
   * Provides a lightweight frontend interface to support human-computer interaction.
   * Users can inspect retrieval scores, generated pipeline steps, and execute pipelines within the browser.
   * Allows users to provide granular feedback for improvements.
4. **Multi-LLM System Evaluation**
   * Evaluated across multiple LLMs and multi-stage visualization tasks.
   * Analyzes the impact of structured context on pipeline executability.
   * Identifies semantic and structural challenges that are difficult for RAG to solve.

### System Features

* **Inquiry Expansion** : Expands natural language queries into structured VTK module requirements.
* **Structure-Aware RAG Retrieval** : Retrieves pipeline-aligned example code and API usage from the VTK codebase.
* **Multi-Model Support** : Supports various LLMs including Ollama local models, DeepSeek, Alibaba Qwen (Tongyi Qianwen), etc.
* **Interactive Editing and Verification** : Frontend provides code editing, visualization previews, and pipeline execution feedback.
* **Structured Evaluation** : Quantitatively evaluates pipeline executability, correction cost, and failure modes.

## Quick Start

### System Requirements

* Windows 10/11
* Python 3.12
* Node.js 14+ (for frontend development)
* MongoDB (for data storage)
* Ollama (for local LLM inference, optional)

### One-Click Start

The simplest way is to run the startup script:

**代码段**

```
run.bat
```

This script will automatically:

1. Create necessary directory structures.
2. Start the MongoDB service (if not running).
3. Start the dataset server.
4. Install and start the Python Flask backend (Port 5001).
5. Install and start the frontend development server (Port 5173).

Once started, access the application interface at `http://localhost:5173`.

### Manual Start

#### 1. Backend Startup

**PowerShell**

```
# Activate Python environment
conda activate llm3.12

# Install dependencies
pip install -r requirements.txt

# Start Flask application
python app.py
```

The backend service runs at `http://localhost:5001`.

#### 2. Frontend Startup

**PowerShell**

```
cd front

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

The frontend service runs at `http://localhost:5173`.

## Project Structure

### Core Directories

#### 📁 `front/` - Frontend Application

* **Purpose** : Web User Interface.
* **Tech** : Vue 3 + Vite.
* **Main Modules** :
* `components/`: UI Component library.
* `view/`: Page views.
* `api/`: API call interfaces.
* `utils/`: Utility functions.
* `routers/`: Route configuration.

#### 📁 `llm_agent/` - LLM Agent Module

* **Purpose** : Core LLM calling and processing logic.
* **Main Files** :
* `ollma_chat.py`: Ollama local LLM calls.
* `rag_agent.py`: RAG retrieval agent.
* `prompt_agent.py`: Prompt expansion and query analysis.
* `evaluator_agent.py`: Code evaluation module.
* `code_agent.py`: Code generation agent.
* `data_agent.py`: Data processing agent.

#### 📁 `RAG/` - Retrieval-Augmented Generation Module

* **Purpose** : Constructing and maintaining the VTK code vector database.
* **Main Files** :
* `embedding_v4.py`: Latest text embedding and vectorization module.
* `retriever_v3.py`: Retrieval engine (current version).
* `init_database.py`: Database initialization.
* `mongodb.py`: MongoDB connection management.
* `vtk_code_meta_extract.py`: VTK code metadata extraction.

#### 📁 `config/` - Configuration Module

* **Purpose** : Application configuration and API key management.
* **Main Files** :
* `app_config.py`: App config (ports, paths, API addresses, etc.).
* `ollama_config.py`: Ollama model config.
* `secrets.py`: API keys (must be created manually, not submitted to git).

#### 📁 `utils/` - Utility Module

* **Purpose** : General utility functions.
* **Main Files** :
* `dataset.py`: Dataset management.
* `diff/`: Code difference analysis.
* `prompt-sample/`: Prompt samples.

#### 📁 `experiment_results/` - Experiment Results

* **Purpose** : Saving evaluation and testing results.
* **Subdirectories** :
* `generated_code/`: Generated code results.
* `backup/`: Backup data.
* `analys/`: Analysis reports.

### Other Important Files

* `app.py`: Main Flask application file defining all API endpoints.
* `requirements.txt`: Python dependencies.
* `run.bat`: Windows one-click startup script.

## API Endpoints

The backend provides the following main API endpoints to support the structure-aware pipeline generation workflow:

| **Endpoint** | **Method** | **Function**                                   |
| ------------------ | ---------------- | ---------------------------------------------------- |
| `/generate`      | POST             | Generate a pipeline from a natural language question |
| `/expand`        | POST             | Prompt Expansion (Structuring the question)          |
| `/retrieval`     | POST             | Execute Structure-Aware RAG Retrieval                |
| `/upload`        | POST             | Upload data files                                    |

## Workflow

```
User Input → Prompt Expansion (Optional) → Structure-Aware RAG Retrieval (Optional) → LLM Generation → Pipeline Execution & Verification → Return Results
```

 **Core Workflow Characteristics** :

* **Structure-Aligned Retrieval** : Code examples retrieved by the RAG system are explicitly aligned with pipeline stages.
* **Human-Computer Interaction** : Users can execute generated pipelines in real-time in the browser and receive feedback.
* **Iterative Improvement** : Targeted corrections based on execution feedback.
* **Reliability Evaluation** : Real-time evaluation of pipeline executability and correction costs.

## Configuration Instructions

### Python Environment

The project uses a Python 3.12 environment named `llm3.12`. Before running any Python script, you need to activate this environment:

**PowerShell**

```
conda activate llm3.12
```

### API Key Configuration

Configure API keys for each LLM in `config/secrets.py` (this file is not submitted to the repository):

**Python**

```
class Secrets:
    deepseek_apikey = "your_deepseek_key"
    qwen_apikey = "your_qwen_key"
    aihub_apikey = "your_aihub_key"
    cst_apikey = "your_cst_key"
```

## Testing

The following files contain test functions:

* `llm_agent/rag_agent.py`
* `llm_agent/ollma_chat.py`
* `llm_agent/prompt_agent.py`
* `RAG/retriever_v3.py`

## Data Construction

### Building the RAG Vector Database (Deprecated)

> **Note**: This section describes a deprecated approach for building the RAG vector database. It is an old version scheme and is no longer recommended.

**PowerShell**

```
conda activate llm3.12
python RAG/embedding_v4.py
```

Data sources need to be placed in the `data/` directory with the following structure:

```
data/
├── vtkjs-examples/
│   ├── benchmark/
│   └── prompt-sample/
│       └── vtk_api/
│           ├── code.html
│           └── description.txt
└── faiss_cache/  (automatically generated after embedding)
```

## Main Dependencies

* **Backend Framework** : Flask
* **Vector Database** : FAISS (Deprecated: old version approach)
* **Vector Model** : sentence-transformers
* **LLM Invocation** : LangChain + Ollama/OpenAI API
* **Database** : MongoDB
* **Frontend Framework** : Vue 3
* **Frontend Build** : Vite

## Technical Highlights

### Structure-Aware RAG

The retrieval system of LLM4VIS not only retrieves software code but also explicitly models pipeline structure, module compatibility, and execution order. Compared to naive text retrieval, this structure-aware method improves pipeline executability.

### Correction Cost Metric

LLM4VIS introduces the **Correction Cost** metric to measure the amount of manual intervention required to obtain a valid pipeline. Compared to simple executability metrics, correction cost better reflects the actual usability of the generated pipeline.

### Human-in-the-Loop Interactive Insights

LLM4VIS is not a fully automated system but a platform for human-computer interactive insights. Users can inspect retrieval scores, check generated pipeline steps, execute pipelines in the browser, and continuously provide feedback to improve the pipeline.

## FAQ

### MongoDB Connection Failed

Ensure the MongoDB service is running. Use `mongod` to start the MongoDB service:

**PowerShell**

```
mongod --dbpath=data/db --port 27017
```

### Ollama Model Load Failed

Ensure the Ollama service is running at the specified URL (default `http://127.0.0.1:11435`). You can modify the configuration in `config/ollama_config.py`.

### Frontend Cannot Connect to Backend

Ensure the backend service is running at `http://localhost:5001` and the CORS configuration is correct.
