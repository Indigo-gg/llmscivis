import json
import requests
import config.ollama_config as url
from langchain_ollama import OllamaLLM
from config import app_config
from config.ollama_config import modals

'''
直接和ollama交互的函数
'''


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        return json.JSONEncoder.default(self, obj)


async def get_llm_response(prompt: str) -> str:
    """调用Ollama获取回答"""
    model = OllamaLLM(
        base_url=app_config.ollama_url,
        model=modals[0]
    )
    return model.invoke(prompt)


def get_message(user_input, modal, system):
    data = {"model": modal,
            "prompt": user_input,
            "system": system,
            # "context": context,
            # "options": {"num_ctx": 2048}
            }

    response = requests.post(url=url.generate, json=data)
    if response.status_code == 200:

        return 'ok', response
    else:
        return 'error', response.text


def show_answer(response):
    for line in response.iter_lines():
        body = json.loads(line)
        # print(line)
        response_part = body.get('response', '')
        # the response streams one token at a time, print that as we receive it
        print(response_part, end='', flush=True)
        # print('\n')
