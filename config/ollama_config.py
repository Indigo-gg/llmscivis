from config import app_config
modals=['llama3.2:1b']
embedding_modals=['BAAI/bge-small-en-v1.5']
base = app_config.ollama_url+'/api'
faissDB_path='data/faiss_cache'
generate = base+'/generate'

