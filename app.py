import asyncio
import datetime
import json
from datetime import datetime
import time

from flask import Flask, render_template, stream_with_context, jsonify
from flask import request, Response

from config import app_config
from llm_agent.ollma_chat import get_deepseek_response
from llm_agent.rag_agent import RAGAgent
from flask_cors import CORS, cross_origin
from llm_agent import evaluator_agent
from utils.dataset import add_data, get_all_data, modify_object
from llm_agent.prompt_agent import analyze_query, merge_analysis
from config import ollama_config
import os
import base64
from datetime import datetime

app = Flask(__name__)
# 配置跨域

CORS(app, resources=r'/*')


@app.route('/upload', methods=["POST"])
def upload():
    # 检查请求中是否包含文件
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    # 如果用户没有选择文件，浏览器也会提交一个没有文件名的空文件
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        # 保存文件到服务器
        filename = file.filename
        file.save(f"data/user_space/{filename}")
        return jsonify({'message': 'File uploaded successfully'}), 200

    return jsonify({'error': 'An error occurred while uploading the file'}), 500


@app.route('/generate', methods=["POST"])
def generation():
    obj = request.json
    print('case',obj)
    eval_id = str(int(time.time()))
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_dict = {
        "prompt": obj["prompt"],
        "ground_truth": obj["groundTruth"],
        "generated_code": None,
        "generator_prompt":obj["generatorPrompt"],
        "evaluator_prompt": obj["evaluatorPrompt"],
        "generator": obj["generator"],
        "evaluator": obj["evaluator"],
        "score": None,
        "workflow": obj["workflow"],
        "eval_id": eval_id,
        "eval_user": obj["evalUser"],
        "eval_time": current_time,
        "eval_status": app_config.eval_status[0],
        "manual_evaluation": None,
        "evaluator_evaluation": None,
        "options":None
    }
    if obj['workflow']['iterativeLoop']:
        data_dict['options']={
            "error_type_list":[],
            "generated_code":'',
            'loop_time':0,
            'error_log':''
        }
    add_data(data_dict)
    final_prompt=obj['prompt']
    analysis=''
    if obj['workflow']['inquiryExpansion']:
        analysis=analyze_query(obj['prompt'],model_name=obj['generator'],system=obj['generatorPrompt'])
        final_prompt=merge_analysis(analysis)
        print('analysis\n',final_prompt)

    if obj['workflow']['rag']:
        rag_agent = RAGAgent()
        final_prompt = rag_agent.search(analysis,obj['prompt'])
        print('rag prompt',final_prompt)

    response = get_deepseek_response(final_prompt, ollama_config.models[obj['generator']],system=obj['generatorPrompt'])
    data_dict['generated_code']=response
    return Response(json.dumps(data_dict), content_type='application/json')

@app.route('/code_error', methods=["POST"])
def handle_code_error():
    from llm_agent.code_agent import ErrorAnalyzer
    error_data = request.json
    analyzer = ErrorAnalyzer()
    
    # 分析错误并生成修复建议
    analysis_result = analyzer.analyze_log(json.dumps(error_data['errors']))
    
    if analysis_result['should_continue']:
        # 获取最新的错误提示
        error_prompts = [error['prompt'] for error in analysis_result['errors']]
        
        # 构建新的生成提示
        enhancement_prompt = "\n".join([
            "请根据以下错误修复代码：",
            *error_prompts,
            "原始代码：",
            error_data.get('current_code', '')
        ])
        
        # 重新生成代码
        new_code = get_deepseek_response(enhancement_prompt, ollama_config.models['deepseek'])
        
        return jsonify({
            'success': True,
            'should_continue': True,
            'new_code': new_code,
            'iteration': analysis_result['iteration'],
            'error_summary': analyzer.get_error_summary()
        })
    
    return jsonify({
        'success': True,
        'should_continue': False,
        'error_summary': analyzer.get_error_summary()
    })


@app.route('/generateStream', methods=["POST"])
def generation_stream():

    obj = request.json
    print('case',obj)
    eval_id = str(int(time.time()))
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_dict = {
        "prompt": obj["prompt"],
        "ground_truth": obj["groundTruth"],
        "generated_code": None,
        "evaluator_prompt": obj["evaluatorPrompt"],
        "generator": obj["generator"],
        "evaluator": obj["evaluator"],
        "score": None,
        "workflow": obj["workflow"],
        "eval_id": eval_id,
        "eval_user": obj["evalUser"],
        "eval_time": current_time,
        "eval_status": app_config.eval_status[0],
        "manual_evaluation": None,
        "evaluator_evaluation": None,
        "options":None
    }
    add_data(data_dict)
    rag_agent = RAGAgent()
    response_generator = rag_agent.get_response_stream(obj['prompt'], obj['workflow'])  # 假设 get_response_stream 返回一个生成器

    for chunk in response_generator:
        if not chunk.choices:
            continue
        print(chunk, end="")

    def generate():
        try:
            for chunkk in response_generator:
                print(chunkk,'\n')
                yield chunkk.choices[0].delta.content
        except Exception as e:
            yield json.dumps({"error": str(e)}).encode()
    return Response(stream_with_context(generate()), content_type='text/event-stream')




@app.route('/evaluate', methods=["POST"])
def evaluation():
    obj = request.json
    print('evaluation case',obj)
    # 执行 evaluate
    eval_result = evaluator_agent.evaluate(obj['generatedCode'], obj["groundTruth"], obj['evaluatorPrompt'],obj['evaluator'])
    obj['score']=eval_result['score']
    obj['evaluatorEvaluation']=eval_result['evaluator_evaluation']
    data_dict = {
        "prompt":obj['prompt'],
        "ground_truth":obj['groundTruth'],
        "generated_code":obj['generatedCode'],
        "evaluator_prompt":obj['evaluatorPrompt'],
        "generator":obj['generator'],
        "evaluator":obj['evaluator'],
        "score":obj['score'],
        "workflow":obj['workflow'],
        "eval_id":obj['evalId'],
        "eval_user":obj['evalUser'],
        "manual_evaluation":obj['manualEvaluation'],
        "evaluator_evaluation":obj['evaluatorEvaluation'],
        "options":obj['options']
    }
    modify_object(data_dict)
    # 返回 evaluate 结果给前端
    return Response(json.dumps(data_dict), content_type='application/json')


@app.route('/get_all_data', methods=["GET"])
def get_all():
    data_list = get_all_data()
    return Response(json.dumps(data_list), content_type='application/json')


# save update the contents in file
@app.route('/save', methods=["POST"])
# 保存结果文件
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

@app.route('/export', methods=['POST'])
def export_results():
    try:
        data = request.json
        
        # 创建导出目录
        export_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = f"exports/case_{data['evalId']}_{export_time}"
        os.makedirs(export_dir, exist_ok=True)
        
        # 保存图片
        for image_type in ['generatedImage', 'truthImage']:
            if data.get(image_type):
                # 解码base64图片数据
                img_data = base64.b64decode(data[image_type].split(',')[1])
                with open(f"{export_dir}/{image_type}.png", 'wb') as f:
                    f.write(img_data)
        
        # 保存用例数据
        case_data = {
            'evalId': data['evalId'],
            'prompt': data['prompt'],
            'groundTruth': data['groundTruth'],
            'generatedCode': data['generatedCode'],
            'evaluatorEvaluation': data['evaluatorEvaluation'],
            'score': data['score'],
            'consoleOutput': data['consoleOutput'],
            'exportTime': data['exportTime']
        }
        
        with open(f"{export_dir}/case_data.json", 'w', encoding='utf-8') as f:
            json.dump(case_data, f, ensure_ascii=False, indent=2)
            
        return jsonify({
            'success': True,
            'message': '导出成功',
            'exportPath': export_dir
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'导出失败: {str(e)}'
        }), 500


if __name__ == '__main__':
    app.run(debug=True)
    # get_message()
