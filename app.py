import asyncio
import datetime
import json
import time

from flask import Flask, render_template, stream_with_context, jsonify
from flask import request, Response

from config.app_config import app_config
from llm_agent.ollma_chat import get_llm_response
from llm_agent.rag_agent import RAGAgent
from flask_cors import CORS, cross_origin
from llm_agent import evaluator_agent
from utils.dataset import add_data, get_all_data, modify_object,get_object_by_id,modify_object_with_export
from llm_agent.prompt_agent import analyze_query
from config.ollama_config import ollama_config
import os
import base64
from datetime import datetime

# 定义数据集根目录
DATA_DIR = os.path.join('data', 'vtkjs-examples')

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
        "generator_prompt":obj.get("generatorPrompt", ""),
        "final_prompt":None,
        "evaluator_prompt": obj.get("evaluatorPrompt", ""),
        "generator": obj["generator"],
        "evaluator": obj["evaluator"],
        "score": None,
        "workflow": obj["workflow"],
        "eval_id": eval_id,
        "eval_user": obj.get("evalUser", ""),
        "export_time":None,
        "console_output":None,
        "eval_time": current_time,
        # "eval_status": app_config.eval_status[0],
        # "manual_evaluation": None,
        "evaluator_evaluation": None,
        "options":None
    }
    # if obj['workflow']['iterativeLoop']:
    #     data_dict['options']={
    #         "error_type_list":[],
    #         "generated_code":'',
    #         'loop_time':0,
    #         'error_log':''
    #     }
    final_prompt=obj['prompt']
    analysis=''
    analysis_data = []  # 存储结构化的分析数据
    retrieval_results = []
    
    if obj['workflow']['inquiryExpansion']:
        analysis=analyze_query(obj['prompt'],model_name=ollama_config.inquiry_expansion_model,system=None)
        print('prompt analysis (result):\n', analysis, '\n')
        
        # 保存结构化的分析数据供前端使用
        # analysis 现在返回 list[dict]，每个 dict 包含: phase, step_name, vtk_modules, description
        if isinstance(analysis, list):
            analysis_data = analysis  # 直接保存结构化数据
        else:
            analysis_data = []  # 如果不是列表，返回空数组
        print('analysis_data for frontend:\n', analysis_data, '\n')

    if obj['workflow']['rag']:
        # 如果没有启用提示词拓展，但启用了RAG，使用原始prompt
        search_analysis = analysis if analysis else obj['prompt']
        
        rag_agent = RAGAgent(use_v3=True)  # 使用 retriever_v3
        # 传递分析结果列表给 RAG agent
        # RAG agent 会提取 description 和其他元信息用于检索
        final_prompt = rag_agent.search(search_analysis, obj['prompt'])
        print('rag prompt\n',final_prompt)
        
        # Extract retrieval results for frontend display
        retrieval_results = rag_agent.get_retrieval_metadata()
    
    response = get_llm_response(final_prompt, obj['generator'],system=obj.get('generatorPrompt', ''))

    data_dict['generated_code']=response
    data_dict['final_prompt']=final_prompt
    data_dict['analysis']=analysis_data  # 返回结构化数据而不是文本
    data_dict['retrieval_results']=retrieval_results
    add_data(data_dict)

    return Response(json.dumps(data_dict), content_type='application/json')

@app.route('/retrieval', methods=["POST"])
def handle_retrieval():
    """
    单独的检索端点，接收用户编辑后的拓展数据，执行RAG检索
    """
    try:
        obj = request.json
        analysis = obj.get('analysis', [])
        prompt = obj.get('prompt', '')
        
        print('[Retrieval API] Received analysis:', analysis)
        print('[Retrieval API] Received prompt:', prompt)
        
        # 初始化 RAG Agent
        rag_agent = RAGAgent(use_v3=True)
        
        # 执行检索
        final_prompt = rag_agent.search(analysis, prompt)
        print('[Retrieval API] Generated prompt:', final_prompt[:200], '...')
        
        # 获取检索结果元数据
        retrieval_results = rag_agent.get_retrieval_metadata()
        print(f'[Retrieval API] Found {len(retrieval_results)} retrieval results')
        
        return jsonify({
            'success': True,
            'final_prompt': final_prompt,
            'retrieval_results': retrieval_results,
            'analysis': analysis
        })
        
    except Exception as e:
        print(f'[Retrieval API] Error: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/expand', methods=["POST"])
def handle_expand():
    """
    单独的提示词拓展端点，只执行 analyze_query
    """
    try:
        obj = request.json
        prompt = obj.get('prompt', '')
        
        print('[Expand API] Received prompt:', prompt)
        
        # 执行提示词拓展
        analysis = analyze_query(prompt, model_name=ollama_config.inquiry_expansion_model, system=None)
        print('[Expand API] Analysis result:', analysis)
        
        # 确保返回结构化数据
        if isinstance(analysis, list):
            analysis_data = analysis
        else:
            analysis_data = []
        
        return jsonify({
            'success': True,
            'analysis': analysis_data
        })
        
    except Exception as e:
        print(f'[Expand API] Error: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
        new_code = get_llm_response(enhancement_prompt, ollama_config.models_cst['deepseek-v3'])
        
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
    
    # 构建响应数据
    data_dict = {
        "score":obj['score'],
        "eval_id":obj['evalId'],
        "evaluator_evaluation":obj['evaluatorEvaluation'],
        "parsed_evaluation": eval_result.get('parsed_evaluation')  # 新增字段
    }
    modify_object(data_dict)
    # 返回 evaluate 结果给前端
    return Response(json.dumps(data_dict), content_type='application/json')


@app.route('/get_models', methods=["GET"])
def get_models():
    """Get all available models from ollama_config"""
    models = []
    
    # Collect keys from all model dictionaries
    model_sources = [
        ollama_config.models_cst,
        ollama_config.models_ollama,
        ollama_config.models_qwen,
        ollama_config.models_aihub
    ]
    
    for source in model_sources:
        models.extend(list(source.keys()))
    
    # Remove duplicates while preserving order
    seen = set()
    unique_models = []
    for model in models:
        if model not in seen:
            seen.add(model)
            unique_models.append(model)
    
    return jsonify(unique_models)

@app.route('/get_all_data', methods=["GET"])
def get_all():
    data_list = get_all_data()
    return Response(json.dumps(data_list), content_type='application/json')

def read_directory_structure(base_path, current_path, include_content=False):
    """Read directory structure. Set include_content=True to load file contents."""
    structure = []
    full_current_path = os.path.join(base_path, current_path)
    if not os.path.exists(full_current_path):
        return structure

    for item_name in os.listdir(full_current_path):
        # Skip 'data' folder and README files
        if item_name == 'data' or item_name.lower() == 'readme.md':
            continue
            
        item_path = os.path.join(full_current_path, item_name)
        relative_item_path = os.path.join(current_path, item_name)
        if os.path.isdir(item_path):
            structure.append({
                'name': item_name,
                'type': 'directory',
                'path': relative_item_path,
                'children': read_directory_structure(base_path, relative_item_path, include_content)
            })
        else:
            file_item = {
                'name': item_name,
                'type': 'file',
                'path': relative_item_path,
            }
            
            # Only load content if explicitly requested
            if include_content:
                content = None
                # Try multiple encodings to handle different file types
                encodings = ['utf-8', 'gbk', 'latin-1', 'cp1252']
                for encoding in encodings:
                    try:
                        with open(item_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        break  # Successfully read the file
                    except (UnicodeDecodeError, LookupError):
                        continue  # Try next encoding
                    except Exception as e:
                        content = f"Error reading file: {e}"
                        break  # Stop trying on non-encoding errors
                
                # If all encodings failed, set a default error message
                if content is None:
                    content = f"Unable to read file with available encodings"
                
                file_item['content'] = content
            
            structure.append(file_item)
    return structure

@app.route('/get_case_list', methods=["GET"])
def get_case_list():
    try:
        base_path = os.path.join('data', 'vtkjs-examples', 'benchmark')
        # 检查目录是否存在
        if not os.path.exists(base_path):
            # 目录不存在，返回空数组
            return jsonify([])
        
        # Only load content when explicitly requested via query parameter
        include_content = request.args.get('include_content', 'false').lower() == 'true'
        tree_structure = read_directory_structure(base_path, '', include_content=include_content)
        return jsonify(tree_structure)
    except Exception as e:
        # 发生错误时返回空数组
        print(f"Error in get_case_list: {e}")
        return jsonify([]), 500

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
        
        # Support both evalId and evaluation_id field names
        eval_id = d.get("evalId") or d.get("evaluation_id")
        if not eval_id:
            raise ValueError("Missing evalId or evaluation_id in request")
            
        print(f"Processing export for evalId: {eval_id}")
        
        # Create a dict with the expected field name for backend functions
        export_dict = {"evalId": eval_id}
        
        modify_object_with_export(export_dict)
        data=get_object_by_id(export_dict)
        # print(f"Type of data: {type(data)}, Data: {data}")
        if 'generated_code' in data and 'path' in data and 'generator' in data and 'evaluator' in data and 'workflow' in data:
            generated_code = data['generated_code']
            ground_truth = data['ground_truth']
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
            new_folder_name = f"{formatted_original_dir}_{generator}_{evaluator}_{workflow_name}_{data.get('eval_id')}"
            
            export_case_dir = os.path.join(export_dir, new_folder_name)
            
            # 确保目录存在
            os.makedirs(export_case_dir, exist_ok=True)
            print(f"Exporting to {export_case_dir}")
            
            # 生成文件路径
            generated_code_file_path = os.path.join(export_case_dir, 'generated_code.html')
            modified_code_file_path = os.path.join(export_case_dir, 'modified_code.html')
            ground_truth_file_path = os.path.join(export_case_dir, 'ground_truth.html')
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
                with  open(ground_truth_file_path, 'w', encoding='utf-8') as f:
                    f.write(ground_truth)

                print(f"Successfully created {final_prompt_file_path}")
                    
            except Exception as e:
                print(f"Error writing generated code files: {e}")

      
        for image_type in ['generatedImage', 'truthImage']:
            # Check in both d (request data) and data (database data)
            image_data = d.get(image_type) or data.get(image_type)
            if image_data:
                # 解码base64图片数据
                img_data = base64.b64decode(image_data.split(',')[1])
                # Save to export_case_dir if available, otherwise to export_dir
                image_dir = export_case_dir if export_case_dir else export_dir
                with open(f"{image_dir}/{image_type}.png", 'wb') as f:
                    f.write(img_data)
        
        # 确保 export_case_dir 已经被正确赋值后再使用
        if export_case_dir:
            with open(f"{export_case_dir}/case_export_data.json", 'w', encoding='utf-8') as f:
                # need_var={
                #     'generator': data['generator'],
                #     'evaluator': data['evaluator'],
                #     'workflow': data['workflow'],
                #     'final_prompt': data['final_prompt'],
                #     'path': data['path'],
                #     'eval_id': data['eval_id'],
                #     'eval_user': data['eval_user'],
                #     'eval_time': data['eval_time'],
                #     'prompt':  data['prompt'],
                #     'ground_truth'
                # }
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


@app.route('/get_exported_cases', methods=["GET"])
def get_exported_cases():
    # 定义 exports 目录的绝对路径
    exports_path = os.path.join(os.getcwd(), 'exports')
    
    # 只有当明确指定时才加载文件内容
    include_content = request.args.get('include_content', 'false').lower() == 'true'
    tree_structure = read_directory_structure(exports_path, '', include_content=include_content)
    
    return Response(json.dumps(tree_structure), content_type='application/json')


@app.route('/get_image/<path:filename>', methods=['GET'])
def get_image(filename):
    """
    获取图片文件并返回 base64 编码
    """
    try:
        file_path = os.path.join('data', filename)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # 只允许 PNG 和 JPG 文件
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in ['.png', '.jpg', '.jpeg']:
            return jsonify({'error': 'Unsupported file type'}), 400
        
        # 读取文件并转换为 base64
        with open(file_path, 'rb') as f:
            image_data = f.read()
        
        # 确定 MIME 类型
        mime_type = 'image/png' if file_ext == '.png' else 'image/jpeg'
        
        # 生成 base64 数据 URL
        base64_data = base64.b64encode(image_data).decode('utf-8')
        image_url = f'data:{mime_type};base64,{base64_data}'
        
        return jsonify({
            'success': True,
            'image_url': image_url,
            'filename': filename
        })
        
    except Exception as e:
        print(f"Error reading image: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/dataset/<path:filename>', methods=['GET'])
def get_dataset_file(filename):
    # 检查请求路径是否以 "/index.json" 结尾
    if filename.endswith('/index.json'):
        # 提取真实的文件名（去掉最后的 "/index.json"）
        real_filename = filename[:-len('/index.json')]
        file_path = os.path.join(DATA_DIR, real_filename)

        # 检查真实文件是否存在
        if os.path.exists(file_path) and os.path.isfile(file_path):
            # 如果文件存在，生成一个包含元数据的 JSON 响应
            # 这会告诉 vtk.js 如何加载这个文件
            response_data = {
                "version": "1.0",
                "name": os.path.basename(real_filename),
                "type": "vtkMultiBlockDataSet",
                "datasets": [
                    {
                        "relativePath": os.path.basename(real_filename),
                        "name": os.path.basename(real_filename),
                        "type": "vtkStructuredPoints",
                        "dataType": "LittleEndian",
                        "compression": "gzipped"
                    }
                ]
            }
            return jsonify(response_data)
        else:
            # 如果真实文件不存在，返回404错误
            return jsonify({'error': 'File not found'}), 404
    else:
        # 如果请求路径不是以 "/index.json" 结尾，执行原有的文件服务逻辑
        file_path = os.path.join(DATA_DIR, filename)

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
            '.vtp': 'application/octet-stream',
            '.vti': 'application/octet-stream',
            '.vtk': 'application/octet-stream',
            '.vtu': 'application/octet-stream',
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
    app.run(debug=True, use_reloader=False, port=5001)
    # get_message()
