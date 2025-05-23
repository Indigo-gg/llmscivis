import asyncio
import datetime
import json
from datetime import datetime
import time

from flask import Flask, render_template, stream_with_context, jsonify
from flask import request, Response

from config.app_config import app_config
from llm_agent.ollma_chat import get_llm_response
from llm_agent.rag_agent import RAGAgent
from flask_cors import CORS, cross_origin
from llm_agent import evaluator_agent
from utils.dataset import add_data, get_all_data, modify_object
from llm_agent.prompt_agent import analyze_query, merge_analysis
from config.ollama_config import ollama_config
import os
import base64
from datetime import datetime

app = Flask(__name__)
# 配置跨域

CORS(app, resources={
    r'/*': {
        'origins': '*',
        'methods': ['GET', 'POST', 'OPTIONS'],
        'allow_headers': ['Content-Type']
    }
})


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
        "final_prompt":None,
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
        analysis=analyze_query(obj['prompt'],model_name=obj['generator'],system=None)
        final_prompt=merge_analysis(analysis)
        print('after_analysis\n',final_prompt)

    if obj['workflow']['rag']:
        rag_agent = RAGAgent()
        final_prompt = rag_agent.search(analysis,obj['prompt'])
        print('rag prompt\n',final_prompt)
    
    response = get_llm_response(final_prompt, obj['generator'],system=obj['generatorPrompt'])
    data_dict['generated_code']=response
    data_dict['final_prompt']=final_prompt
    return Response(json.dumps(data_dict), content_type='application/json')

@app.route('/error_analysis', methods=["POST"])
def handle_error_analysis():
    from llm_agent.fix_agent import FixAgent
    error_data = request.json
    analyzer = FixAgent()
    
    # 使用FixAgent分析错误并获取修复建议
    fix_result = analyzer.analyze_and_fix({
        'error_type': error_data.get('error_type', ''),
        'error_message': json.dumps(error_data['errors']),
        'code_snippet': error_data.get('current_code', ''),
        'error_history': error_data.get('error_history', [])  # 添加错误历史
    })
    
    # 获取错误分析摘要
    error_summary = analyzer.get_error_summary()
    
    return jsonify({
        'success': True,
        'errors': fix_result['errors'],  # 包含错误的详细信息
        'suggestion': fix_result['suggestion'],  # 综合修复建议
        'new_code': fix_result['new_code'],  # 修复后的代码建议
        'should_retry': fix_result['should_retry'],
        'error_summary': error_summary,  # 添加错误分析摘要
        'iteration': fix_result['iteration']  # 当前迭代次数
    })

@app.route('/code_error', methods=["POST"])
def handle_code_error():
    from llm_agent.fix_agent import FixAgent
    error_data = request.json
    analyzer = FixAgent()
    
    # 使用FixAgent分析错误并获取修复建议
    fix_result = analyzer.analyze_and_fix({
        'error_type': error_data.get('error_type', ''),
        'error_message': json.dumps(error_data['errors']),
        'code_snippet': error_data.get('current_code', '')
    })
    
    if fix_result['should_retry']:
        # 构建新的生成提示
        enhancement_prompt = "\n".join([
            "请根据以下错误修复代码：",
            *fix_result['suggestions'],
            "原始代码：",
            error_data.get('current_code', '')
        ])
        
        # 重新生成代码
        new_code = get_llm_response(enhancement_prompt, ollama_config.models_deepseek['deepseek-v3'])
        
        return jsonify({
            'success': True,
            'should_continue': True,
            'new_code': new_code,
            'iteration': fix_result['iteration'],
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

def read_directory_structure(base_path, current_path):
    structure = []
    full_current_path = os.path.join(base_path, current_path)
    if not os.path.exists(full_current_path):
        return structure

    for item_name in os.listdir(full_current_path):
        item_path = os.path.join(full_current_path, item_name)
        relative_item_path = os.path.join(current_path, item_name)
        if os.path.isdir(item_path):
            structure.append({
                'name': item_name,
                'type': 'directory',
                'path': relative_item_path,
                'children': read_directory_structure(base_path, relative_item_path)
            })
        else:
            try:
                with open(item_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                content = f"Error reading file: {e}"
            structure.append({
                'name': item_name,
                'type': 'file',
                'path': relative_item_path,
                'content': content
            })
    return structure

@app.route('/get_case_list', methods=["GET"])
def get_case_list():
    base_path = os.path.join('data', 'vtk-examples', 'benchmark')
    tree_structure = read_directory_structure(base_path, '')
    return jsonify(tree_structure)

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

# 数据的位置在http://127.0.0.1:5000/dataset/filename
@app.route('/dataset/<path:filename>', methods=['GET'])
def get_dataset_file(filename):
    # 构建文件路径
    file_path = os.path.join('data', 'dataset', filename)

    # 检查文件是否存在
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404

    # 根据文件扩展名确定内容类型和读取模式
    file_ext = os.path.splitext(filename)[1].lower()
    
    # 文本文件类型
    text_types = {
        '.txt': 'text/plain',
        '.json': 'application/json',
        '.html': 'text/html',
        '.csv': 'text/csv',
        '.xml': 'application/xml'
    }
    
    # 二进制文件类型
    binary_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.vtp': 'application/octet-stream'
    }
    
    # 确定内容类型和读取模式
    if file_ext in text_types:
        content_type = text_types[file_ext]
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    elif file_ext in binary_types:
        content_type = binary_types[file_ext]
        with open(file_path, 'rb') as file:
            content = file.read()
    else:
        # 默认处理为二进制文件
        content_type = 'application/octet-stream'
        with open(file_path, 'rb') as file:
            content = file.read()
    
    # 返回文件内容
    return Response(content, content_type=content_type)

if __name__ == '__main__':
    app.run(debug=True)
    # get_message()
