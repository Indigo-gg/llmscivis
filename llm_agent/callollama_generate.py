import requests
import json

last_context = []
def get_contex_str_from_list(context_list):
    context_str = '['
    for i in range(len(context_list)):
        if i == 0:
            context_str = context_str + str(context_list[i])
        else:
            context_str = context_str + "," + str(context_list[i])

    context_str = context_str + ']'

    return context_str


def filter_code(raw_code):
    splitter = "```"
    new_code = raw_code.replace(splitter, '')
    return new_code


def send_to_ollama(user_input):
    status = ""
    msg = ""

    # prompt= '"Write a vtk javascript code in html file, only show code, no explanation'
    # prompt= '"only show code, no explanation'
    # input_all=prompt+","+user_input+'"'

    input_all = '"' + user_input + '"'

    # API endpoint and headers
    url = "http://localhost:11434/api/generate"
    # headers = {
    #     "Authorization": "Bearer your_api_key",
    #     "Content-Type": "application/json"
    # }

    # Request payload (multiple lines)
    # data = '{"model": "llama3", "prompt":"Write a vtkjs code that can compute the streamline for specific input file,adding *** before the start of the code and after the end of the code, only show code,do not show explanation", "stream": false}'
    # data = '{"model": "llama3", "prompt":"Write a vtkjs code that can compute the streamline (using vtkjs api) for specific input file, only show code, do not show explanation, put all code in a function called render with proper import operations, the code will be used in html direactly",  "stream": false}'
    # data = '{"model": "llama3", "prompt":'+input_all+ ',"stream": false}'

    # data with context    
    global last_context
    # data = '{"model": "llama3", "prompt":'+input_all+ ',"stream": false, "context":'+get_contex_str_from_list(last_context)+'}'

    data = '{"model": "llama3", "prompt":' + input_all + ',"stream": false, "context":' + get_contex_str_from_list(
        last_context) + ''
    data = data + ',"options": { "num_ctx": 2048} '
    data = data + '}'

    print("send ollama data:", data)

    json_data = json.loads(data)
    # Sending the POST request
    response = requests.post(url, json=json_data)

    # Checking the response
    if response.status_code == 200:
        result = response.json()
        # print("Generated Text:", result['response'])
        # output resutls into a js file
        resp_code_str = result['response']
        # get the context info
        last_context = result['context']
        print("last_context size is", len(last_context))

        file_name = "./static/vtk-js-demo.html"
        filtered_code = filter_code(resp_code_str)

        f = open(file_name, 'w')
        # do sth to create the str for writting
        f.write(filtered_code + "\n")
        f.close()
    else:
        print("Error:", response.status_code, response.text)

    return "ok", msg
