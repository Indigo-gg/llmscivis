from openai import models
from config.app_config import app_config

class OllamaConfig:
    def __init__(self):
        self.models_deepseek = {
            # "deepseek": 'deepseek-chat',
            'deepseek-v3':'deepseek-v3-241226',
            'deepseek-r1':'deepseek-r1-250120',
            'deepseek-r1-distill-qwen-32b':'deepseek-r1-distill-qwen-32b-250120'
        }
        self.models_ollama = {
            "llama3.2-1b": 'llama3.2:1b',
        }
        self.embedding_models = {
            "bge": 'BAAI/bge-small-en-v1.5',
        }
        self.base = app_config.ollama_url + '/api'
        self.generate = self.base + '/generate'

ollama_config = OllamaConfig()
