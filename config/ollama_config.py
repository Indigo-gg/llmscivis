from openai import models
from config import app_config

models_deepseek = {
    # "deepseek": 'deepseek-chat',
    'deepseek-v3':'deepseek-v3-241226',
    'deepseek-r1':'deepseek-r1-250120',
    'deepseek-r1-distill-qwen-32b':'deepseek-r1-distill-qwen-32b-250120'
}
models_ollama = {
    "llama3.2-1b": 'llama3.2:1b',
}
embedding_models = {
    "bge": 'BAAI/bge-small-en-v1.5',

}
base = app_config.ollama_url + '/api'
faissDB_path = 'data/faiss_cache'
generate = base + '/generate'
