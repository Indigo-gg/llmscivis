ollama_url = "http://127.0.0.1:11435"
# deepseek_url = "https://api.deepseek.com"

deepseek_url = "https://ark.cn-beijing.volces.com/api/v3/"
system = [
    {
        'prompt': 'you are a programmer， you should give a code by user_query'
    }
]
keywords = {
    'QUESTION':"__QUESTION__"
}

apikey = '13e5c21e-66bf-4b13-a4d8-a414956e7a39'

eval_status = ['failed','completed']

DATASET_PATH='./utils/dataset/dataset.json'
