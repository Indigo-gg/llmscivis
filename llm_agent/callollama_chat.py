import requests
import json

# refer to 
# https://github.com/ollama/ollama/blob/main/examples/python-simplechat/client.py

messages = []
file_name="./static/vtk-js-demo.html"

def filter_code(raw_code):
    splitter="```"
    # the return code may include info such as ```html
    output_msg=raw_code.replace("```html","```")
    if splitter in output_msg:
        new_code_sections = output_msg.split(splitter)
        output_msg=new_code_sections[1]
    
    return output_msg

def send_to_ollama(user_input):

    # load content from code, and use it as input messages

    file = open(file_name, "r")
    current_file_content = file.read()
    file.close()

    messages.append({"role": "assistant", "content": current_file_content})

    status=""
    msg=""

    #prompt= '"Write a vtk javascript code in html file, only show code, no explanation'
    #prompt= '"only show code, no explanation'
    #input_all=prompt+","+user_input+'"'

    input_all='"'+user_input+'"'

    # API endpoint and headers
    url = "http://localhost:11434/api/chat"

    messages.append({"role": "user", "content": user_input})

    print("messages",messages)

    model="llama3"
    json_data={"model": model, "messages": messages, "stream": False}

    print("send ollama data:",json_data)

    # Sending the POST request
    response = requests.post(url, json=json_data, stream=False)

    output = ""

    # Checking the response
    if response.status_code == 200:
        result = response.json()
        # print("Generated Text:", result['response'])
        # output resutls into a js file
        # resp_code_str = result['response']
        # get the context info

        print(result)

        # clean the content and append the messages
        resp_content = result['message']['content']

        print("resp_content is: ",resp_content)

        filter_content = filter_code(resp_content)

        print("filter_content:",filter_content)

        f = open(file_name,'w')
        # # do sth to create the str for writting
        f.write(filter_content+"\n")
        f.close() 
        # add contents as a new message
        # messages.append({"role": "assistant", "content": filter_content})

    else:
        print("Error:", response.status_code, response.text)

    return "ok", msg


