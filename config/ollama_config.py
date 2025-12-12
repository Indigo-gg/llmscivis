from openai import models
from config.app_config import app_config

class OllamaConfig:
    def __init__(self):
        self.models_cst={
            'deepseek-v3':'deepseek-v3:671b',
            'qwen2.5-vl':'qwen2.5-vl:72b',
            'qwen3':'qwen3:235b',
            'deepseek-r1':'deepseek-r1:671b'
        }
        self.models_ollama = {
            "llama3.2-1b": 'llama3.2:1b',
        }
        self.models_qwen={
            "qwen3-turbo":"qwen-turbo-2025-07-15",
            "qwen3-plus":"qwen-plus-2025-09-11",
            "qwen-max":"qwen3-max-2025-09-23",
            "qwen3-max":"qwen3-max-preview",
            "qwen3-32b":"qwen3-32b",
            "qwen3-325b":"qwen3-235b-a22b",
            "qwen2.5-14b":"qwen2.5-14b-instruct-1m"
        }
        self.embedding_models = {
            "bge": 'BAAI/bge-small-en-v1.5',
        }

        self.models_aihub={
            "claude-sonnet-4":"claude-sonnet-4-20250514",
            "gemini-2.5-pro":"gemini-2.5-pro",
            "gemini-pro":"gemini-pro-preview-05-06",
            "gpt-5":"gpt-5",
            "claude-opus-4-1":"claude-opus-4-1-20250805"
        }
        self.inquiry_expansion_model="qwen3-max"
        # self.inquiry_expansion_model="qwen-turbo-2025-07-15"
        self.base = app_config.ollama_url + '/api'
        self.generate = self.base + '/generate'
        self.code_sytstem="""
 You are a VTK.js visualization expert. Based on the user's requirements and the provided VTK.js examples, generate complete and functional HTML code that meets all specified requirements.
    Please follow these guidelines:
    1. Generate complete HTML code that can run independently
    2. Use the VTK.js library from CDN (https://unpkg.com/vtk.js@34.10.0/vtk.js)
    3. Implement ALL requirements specified in the user question
    4. Add detailed comments explaining how each requirement is implemented
    5. Ensure the visualization is displayed properly without UI controls unless specifically requested
    6. Use appropriate VTK.js modules and methods as shown in the examples
    7. Pay special attention to data loading paths and visualization parameters

    Important: Highlight in comments how each specific user requirement is addressed in the code.

"""

ollama_config = OllamaConfig()
