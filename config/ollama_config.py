from config import app_config

models = {
    # "deepseek": 'deepseek-chat',
    'deepseek-v3':'deepseek-v3-241226',
    "llama3.2_1B": 'llama3.2:1b',
    'deepseek-qwen-32B':'deepseek-r1-distill-qwen-32b-250120',
    'deepseek-r1':'deepseek-r1-250120'
}
embedding_models = {
    "bge": 'BAAI/bge-small-en-v1.5',

}
base = app_config.ollama_url + '/api'
faissDB_path = 'data/faiss_cache'
generate = base + '/generate'
