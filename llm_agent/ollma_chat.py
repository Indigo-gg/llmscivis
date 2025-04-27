import json
from pydantic_core.core_schema import model_ser_schema
import requests
import config.ollama_config as url
from langchain_ollama import OllamaLLM
from config import app_config, ollama_config
from openai import OpenAI

'''
直接和LLM交互的函数
'''
#
app = OpenAI(api_key=app_config.apikey, base_url=app_config.deepseek_url)




class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        return json.JSONEncoder.default(self, obj)


# 获取模型回答的入口函数

def get_llm_response(prompt: str, model_name, system) -> str:
    if model_name in ollama_config.models_ollama.keys():
        return get_ollama_response(prompt, ollama_config.models_ollama[model_name], system)
    elif model_name in ollama_config.models_deepseek.keys():
        return get_deepseek_response(prompt, ollama_config.models_deepseek[model_name], system)

#!!! 提前开启ollama服务
def get_ollama_response(prompt: str, model_name, system):
    """调用ollama获取回答"""
    # 使用 OllamaLLM 类初始化，指定基础 URL 和模型名称
    llm = OllamaLLM(
        base_url=app_config.ollama_url,
        model=model_name
    )
    try:
        # 调用 Ollama API 获取回答
        response = llm.invoke(prompt, config={"system": system,"stream":False})
        return response
    except Exception as e:
        print(f"调用 Ollama 出错: {e}")

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



if __name__ == "__main__":
    get_deepseek_response_stream('生成椎体代码', model_name='deepseek-r1-distill-qwen-32b-250120')
    # get_deepseek_response('hello','deepseek-v3')
