from openai import OpenAI
# from config.app_config import app_config



def get_aiCore_response(prompt: str, model_name, system):
    client = OpenAI(
    base_url="https://api.xty.app/v1",
    api_key="sk-uGHmKbQF4MixICHP6f21D975Fa7c4d6e9c1f4eAb182987C8"
#   base_url="https://openrouter.ai/api/v1",
#   api_key="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"
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
    print(completion)
    print(completion.choices[0].message.content)


def get_qwen_response(prompt: str, model_name, system):
    """调用qwen获取回答"""
    client = OpenAI(
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key="sk-bb51f49d7aac4a04adde0794f3f1dfe9"
#   base_url="https://openrouter.ai/api/v1",
#   api_key="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"
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

if __name__ == '__main__':
    # print(get_qwen_response("你好", "qwen3-32b", "你好"))
    get_aiCore_response("", "claude-3-7-sonnet-20250219", "重复三遍用户说的话")