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
from utils.dataset import add_data, get_all_data, modify_object,get_object_by_id
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
        "path":obj['path'],
        "name":obj['name'],
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
        # "eval_status": app_config.eval_status[0],
        # "manual_evaluation": None,
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
    add_data(data_dict)

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



@app.route('/evaluate', methods=["POST"])
def evaluation():
    obj = request.json
    print('evaluation start')
    # 执行 evaluate
    eval_result = evaluator_agent.evaluate(obj['generatedCode'], obj["groundTruth"], obj['evaluatorPrompt'],obj['evaluator'])
    obj['score']=eval_result['score']
    obj['evaluatorEvaluation']=eval_result['evaluator_evaluation']
    data_dict = {
        "score":obj['score'],
        "eval_id":obj['evalId'],
        "evaluator_evaluation":obj['evaluatorEvaluation'],
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
        d = request.json
        export_dir = "exports"
        export_case_dir = ''
        print(d["evalId"])
        data=get_object_by_id(d)
        # print(f"Type of data: {type(data)}, Data: {data}")
        if 'generated_code' in data and 'path' in data and 'generator' in data and 'evaluator' in data and 'workflow' in data:
            generated_code = data['generated_code']
            path = data['path']
            generator = data['generator']
            evaluator = data['evaluator']
            workflow = data['workflow']

            
            # 查找 workflow 中为 true 的变量名
            workflow_name = ''
            for key, value in workflow.items():
                if value is True:
                    workflow_name = key
                    break
                workflow_name = 'no_workflow'
            
            formatted_original_dir = os.path.dirname(path).replace('\\', '_').replace('/', '_')
            new_folder_name = f"{formatted_original_dir}_{generator}_{evaluator}_{workflow_name}"
            
            export_case_dir = os.path.join(export_dir, new_folder_name)
            
            # 确保目录存在
            os.makedirs(export_case_dir, exist_ok=True)
            print(f"Exporting to {export_case_dir}")
            
            # 生成文件路径
            generated_code_file_path = os.path.join(export_case_dir, 'generated_code.html')
            modified_code_file_path = os.path.join(export_case_dir, 'modified_code.html')
            final_prompt_file_path = os.path.join(export_case_dir, 'final_prompt.txt')            
            # 写入文件内容
            try:
                # 去除 markdown 代码块语法（如果存在）
                generated_code = generated_code.replace('```html\n', '').replace('```', '')
                with open(generated_code_file_path, 'w', encoding='utf-8') as f:
                    f.write(generated_code)
                print(f"Successfully created {generated_code_file_path}")

                with open(modified_code_file_path, 'w', encoding='utf-8') as f:
                    f.write(generated_code)
                print(f"Successfully created {modified_code_file_path}")

                with open(final_prompt_file_path, 'w', encoding='utf-8') as f:
                    f.write(data['final_prompt'])

                print(f"Successfully created {final_prompt_file_path}")
                    
            except Exception as e:
                print(f"Error writing generated code files: {e}")

      
        for image_type in ['generatedImage', 'truthImage']:
            if data.get(image_type):
                # 解码base64图片数据
                img_data = base64.b64decode(data[image_type].split(',')[1])
                with open(f"{export_dir}/{image_type}.png", 'wb') as f:
                    f.write(img_data)
        
        # 确保 export_case_dir 已经被正确赋值后再使用
        if export_case_dir:
            with open(f"{export_case_dir}/case_export_data.json", 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            

        return jsonify({
            'success': True,
            'message': '导出成功',
            'exportPath': export_dir
        })
        
    except Exception as e:
        print(f"Error exporting results: {e}")
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
