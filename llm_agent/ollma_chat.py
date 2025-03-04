import json
import requests
import config.ollama_config as url
from langchain_ollama import OllamaLLM
from config import app_config, ollama_config
from config.ollama_config import models
from openai import OpenAI

'''
直接和LLM交互的函数
'''
#
app = OpenAI(api_key=app_config.apikey, base_url=app_config.deepseek_url)


#

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        return json.JSONEncoder.default(self, obj)


async def get_llm_response(prompt: str) -> str:
    """调用Ollama获取回答"""
    model = OllamaLLM(
        base_url=app_config.ollama_url,
        model=models["llama3.2_1B"]
    )
    return model.invoke(prompt)


def get_deepseek_response(prompt: str, model_name, system):
    """调用deepseek获取回答"""
    response = app.chat.completions.create(
        model=model_name,
        stream=False,
        messages=[
            {'role': 'system', 'content': system},
            {"role": "user", "content": prompt}
        ],
    )
    # data=json.loads(response)
    print(response)
    content = response.choices[0].message.content
    return content


def get_deepseek_response_stream(prompt: str, model_name, system=app_config.system[0]['prompt']):
    """调用deepseek获取流式回答"""
    response = app.chat.completions.create(
        model=model_name,
        stream=True,
        messages=[
            {'role': 'system', 'content': system},
            {"role": "user", "content": prompt}
        ],
    )
    return response
    # for chunk in response:
    #     if not chunk.choices:
    #         continue
    #     print(chunk.choices[0].delta.content, end="")


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


# def get_prompt_llm_response(prompt):
#     return get_deepseek_response(prompt, model_name=models['deepseek-v3'])


if __name__ == "__main__":
    get_deepseek_response_stream('生成椎体代码', model_name='deepseek-r1-distill-qwen-32b-250120')
    # get_deepseek_response('hello','deepseek-v3')
