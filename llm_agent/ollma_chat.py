import json
import sys
from pydantic_core.core_schema import model_ser_schema
import requests
from langchain_ollama import OllamaLLM
from urllib3 import response
from config.app_config import app_config
from config.ollama_config import ollama_config
from openai import OpenAI

'''
直接和LLM交互的函数
'''

#
# app = OpenAI(api_key=app_config.apikey, base_url=app_config.deepseek_url) # Moved initialization



class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        return json.JSONEncoder.default(self, obj)


# 获取模型回答的入口函数

def get_llm_response(prompt: str, model_name, system) -> str:
    try:
        if model_name in ollama_config.models_ollama.keys():
            return get_ollama_response(prompt, ollama_config.models_ollama[model_name], system)
        elif model_name in ollama_config.models_deepseek.keys():
            return get_deepseek_response(prompt, ollama_config.models_deepseek[model_name], system)
        elif model_name in ollama_config.models_qwen.keys():
            return get_qwen_response(prompt, ollama_config.models_qwen[model_name], system)
        elif model_name in ollama_config.models_coreai.keys():
            return get_coreai_response(prompt, ollama_config.models_coreai[model_name], system)
    except Exception as e:
        print(f"调用 LLM 出错: {e}")
        return  f"""
        <!DOCTYPE html>
<html lang="zh-CN">

<head>
    <meta charset="UTF-8">
    <title>error page</title>
</head>

<body>
    <h1>error</h1>

    <div class="error-box">
        <h2>error_message</h2>
        <pre><code>{e}</code></pre>
    </div>
</body>

</html>
        """

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
    # Initialize OpenAI client here to avoid module-level initialization issues
    app = OpenAI(api_key=app_config.deepseek_apikey, base_url=app_config.deepseek_url)
    response = app.chat.completions.create(
        model=model_name,
        stream=False,
        messages=[
            {'role': 'system', 'content': system},
            {"role": "user", "content": prompt}
        ],
    )
    # data=json.loads(response)
    # print(response)
    content = response.choices[0].message.content
    return content

def get_deepseek_response_stream(prompt: str, model_name, system):
    app = OpenAI(api_key=app_config.apikey, base_url=app_config.deepseek_url)
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

def get_qwen_response(prompt: str, model_name, system):
    """调用qwen获取回答"""

    client = OpenAI(
        # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
        api_key=app_config.qwen_apikey,
        base_url=app_config.qwen_url,
    )

    response = client.chat.completions.create(
        # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        model=model_name,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        extra_body={"enable_thinking": False},
        # 不开启思考模式：
    )
    content = response.choices[0].message.content
    return content
    # print(completion.model_dump_json()) 
def get_coreai_response(prompt: str, model_name, system):
    """调用coreai获取回答"""
    client = OpenAI(
    base_url=app_config.coreai_url,
    api_key=app_config.coreai_apikey
)
    
    completion = client.chat.completions.create(
    model=model_name,
    stream=False,

    messages=[
        {
        "role":"system",
        "content":system
        },
        {
        "role": "user",
        "content": prompt
        }
        
    ]
    )
    return completion.choices[0].message.content

def get_message(user_input, modal, system):
    data = {"model": modal,
            "prompt": user_input,
            "system": system,
            }

    response = requests.post(url=ollama_config.generate, json=data)
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
    answer=get_qwen_response('生成椎体代码', model_name='qwen-plus-latest',system='you are a programmer， you should give a code by user_query')
    # get_deepseek_response('hello','deepseek-v3')
    print(answer)
