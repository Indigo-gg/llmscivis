import json

from flask import Flask, render_template, stream_with_context, jsonify
from flask import request, Response
# from llm_agent.ollma_chat import get_message, show_answer, MyEncoder
from llm_agent.rag import get_response
from config.app_config import system
from flask_cors import CORS, cross_origin
import sys
# from llm_agent import callollama_generate
from llm_agent import callollama_chat

app = Flask(__name__)
# 配置跨域

CORS(app, resources=r'/*')


@app.route('/get_code', methods=['GET', 'POST'])
@cross_origin(origins="*", methods=['GET', 'POST'])  # 视图级别的跨域配置
def get_code():
    data = request.json
    user_input = data.get('input')
    print(user_input)
    msg, response = get_response(user_input)
    print(msg, response)


    # if msg == 'ok':
    #     def generate():
    #         n = ''
    #         for line in response.iter_lines():
    #             body = json.loads(line)
    #             response_part = n + body.get('response', '')
    #             print(response_part, end='', flush=True)
    #             yield f"{response_part}"
    #
    #     return Response(stream_with_context(generate()), content_type='text/event-stream')
    # else:
    #     return msg, 400


# Flask will look for templates in the templates folder
# the html loaded dynamically by iframe should be put under static dir
@app.route('/test')
def home():
    return render_template('test_views.html')


# Recieve the send request from the server
@app.route('/send', methods=["POST"])
def send():
    # get user input from frontend
    data = request.json
    user_intput = data.get('input')

    status, msg = callollama_chat.send_to_ollama(user_intput)

    print("status", status, "msg", msg)

    # todo add return messages as needed
    return Response("{}", status=200, mimetype='application/json')


# save update the contents in file
@app.route('/save', methods=["POST"])
def save():
    data = request.json
    user_intput = data.get('input')
    # print("get user_intput for save:",user_intput)
    # put user_intput into file
    file_name = './static/vtk-js-demo.html'
    f = open(file_name, 'w')
    # do sth to create the str for writting
    f.write(user_intput)
    f.close()
    return Response("{}", status=200, mimetype='application/json')


if __name__ == '__main__':
    app.run(debug=True)
    # get_message()
