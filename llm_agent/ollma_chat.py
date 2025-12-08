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
    def default(self, o):
        if isinstance(o, bytes):
            return str(o, encoding='utf-8')
        return json.JSONEncoder.default(self, o)


# 获取模型回答的入口函数

def get_llm_response(prompt: str, model_name, system) -> str:
    try:
        if model_name in ollama_config.models_ollama.keys():
            print("使用ollama模型")
            result = get_ollama_response(
                prompt, ollama_config.models_ollama[model_name], system)
            return result if result is not None else f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>error page</title>
</head>
<body>
    <h1>error</h1>
    <div class="error-box">
        <h2>Ollama调用失败</h2>
    </div>
</body>
</html>"""
        elif model_name in ollama_config.models_qwen.keys():
            print("使用qwen模型")
            return get_qwen_response(prompt, ollama_config.models_qwen[model_name], system)
        elif model_name in ollama_config.models_aihub.keys():
            print("使用aihub模型")
            return get_aihub_response(prompt, ollama_config.models_aihub[model_name], system)
        elif model_name in ollama_config.models_cst.keys():
            print("使用cst模型")
            return get_cst_response(prompt, ollama_config.models_cst[model_name], system)
        else:
            return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>error page</title>
</head>
<body>
    <h1>error</h1>
    <div class="error-box">
        <h2>未找到对应的模型: {model_name}</h2>
    </div>
</body>
</html>"""
    except Exception as e:
        print(f"调用 LLM 出错: {e}")
        return f"""
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


def get_ollama_response(prompt: str, model_name, system) -> str | None:
    """调用ollama获取回答"""
    # 使用 OllamaLLM 类初始化，指定基础 URL 和模型名称
    llm = OllamaLLM(
        base_url=app_config.ollama_url,
        model=model_name
    )
    try:
        # 调用 Ollama API 获取回答
        response = llm.invoke(prompt)
        return response
    except Exception as e:
        print(f"调用 Ollama 出错: {e}")
        return None


def get_deepseek_response(prompt: str, model_name, system) -> str:
    """调用deepseek获取回答"""
    # Initialize OpenAI client here to avoid module-level initialization issues
    app = OpenAI(api_key=app_config.deepseek_apikey,
                 base_url=app_config.deepseek_url)
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
    return content or ""


def get_cst_response(prompt: str, model_name, system) -> str:
    """调用deepseek获取回答"""
    app = OpenAI(api_key=app_config.cst_apikey, base_url=app_config.cst_url)
    response = app.chat.completions.create(
        model=model_name,
        stream=False,
        messages=[
            {'role': 'system', 'content': system},
            {"role": "user", "content": prompt}
        ],
    )
    content = response.choices[0].message.content
    return content or ""


def get_deepseek_response_stream(prompt: str, model_name, system):
    app = OpenAI(api_key=app_config.deepseek_apikey,
                 base_url=app_config.deepseek_url)
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


def get_qwen_response(prompt: str, model_name, system) -> str:
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
    return content or ""
    # print(completion.model_dump_json())


def get_aihub_response(prompt: str, model_name, system):

    app = OpenAI(api_key=app_config.aihub_apikey,
                 base_url=app_config.aihub_url)
    """调用aihub获取非流式回答"""
    response = app.chat.completions.create(
        model=model_name,
        stream=False,
        messages=[
            {'role': 'system', 'content': system},
            {"role": "user", "content": prompt}
        ],
    )
    # 直接返回完整响应内容
    try:
        content = response.choices[0].message.content
        return content or ""
    except Exception as e:
        print(f"处理响应出错: {e}")
        return ""


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

    final_prompt = """\
        \n    Generate only the HTML code without any additional text or markdown formatting.\n    User Requirements:\n    Generate an HTML page using vtk.js to visualize the Redsea dataset with volume rendering.\n\nLoad the dataset from: http://127.0.0.1:5000/dataset/redsea.vti\n\nCompute velocity magnitude from the \"velocity\" array and set it as the active scalar\n\nApply volume rendering using a blue → white → red color map spanning the scalar range (min to max)\n\nApply a piecewise opacity function to control transparency across scalar values\n\nSet shading, ambient, diffuse, and specular properties for realistic volume appearance\n\nAdjust the camera to look along +Z and center on the dataset\n\n    Relevant VTK.js Examples:\n    示例 1:\n描述: Displays a synthetic 2D image generated by `vtkRTAnalyticSource` using `vtkImageMapper` and `vtkImageSlice`.\nVTK.js 模块: ['vtk.Common.DataModel.vtkImageData', 'vtk.Filters.Sources.vtkRTAnalyticSource', 'vtk.Rendering.Core.vtkImageMapper', 'vtk.Rendering.Core.vtkImageSlice', 'vtk.Rendering.Misc.vtkFullScreenRenderWindow']\n代码:\n<!DOCTYPE html>\n<html lang=\"en\">\n\n<head>\n    <meta charset=\"UTF-8\">\n    </style>\n</head>\n\n<body>\n    <div id=\"renderer\"></div>\n    <script src=\"https://unpkg.com/vtk.js\"></script>\n    <script>\n        const vtkFullScreenRenderWindow = vtk.Rendering.Misc.vtkFullScreenRenderWindow;\n        const vtkImageSlice = vtk.Rendering.Core.vtkImageSlice;\n        const vtkImageMapper = vtk.Rendering.Core.vtkImageMapper;\n        const vtkImageData = vtk.Common.DataModel.vtkImageData;\n\n        // create render window\n        const fullScreenRenderer = vtkFullScreenRenderWindow.newInstance({ background: [0, 0, 0] });\n        const renderer = fullScreenRenderer.getRenderer();\n        const renderWindow = fullScreenRenderer.getRenderWindow();\n\n        const vtkImgSource = vtk.Filters.Sources.vtkRTAnalyticSource;\n        const imgSource = vtkImgSource.newInstance();\n        imgSource.update();\n        const img = imgSource.getOutputData();\n\n        // set mapper and actor\n        const mapper = vtkImageMapper.newInstance();\n        mapper.setInputData(img);\n\n        const actor = vtkImageSlice.newInstance();\n        actor.setMapper(mapper);\n\n        // adding actor to render\n        renderer.addActor(actor);\n        renderer.resetCamera();\n        renderWindow.render();\n    </script>\n</body>\n\n</html>\n\n--------------------------------------------------------------------------------------------------------------\n示例 2:\n描述: Loads and visualizes a 3D model (VTP format) from a remote URL using `vtkHttpDataSetReader` with gzip support.\n\nVTK.js 模块: ['vtk.IO.Core.DataAccessHelper.HttpDataAccessHelper', 'vtk.IO.Core.vtkHttpDataSetReader', 'vtk.Rendering.Core.vtkActor', 'vtk.Rendering.Core.vtkMapper', 'vtk.Rendering.Misc.vtkFullScreenRenderWindow', 'vtk.Rendering.OpenGL.Profiles.Geometry']\n代码:\n<!DOCTYPE html>\n<html lang=\"en\">\n\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>vtk.js IO-HttpDataSetReader</title>\n</head>\n\n<body>\n    <script src=\"https://unpkg.com/vtk.js\"></script>\n    <script>\n        const data_path = 'http://kitware.github.io/vtk-js/data/cow.vtp'\n        const vtkHttpDataSetReader = vtk.IO.Core.vtkHttpDataSetReader;\n        // const vtkGeometry = vtk.Rendering.OpenGL.Profiles.Geometry\n\n        const vtkFullScreenRenderWindow = vtk.Rendering.Misc.vtkFullScreenRenderWindow;\n        const vtkActor = vtk.Rendering.Core.vtkActor\n        const vtkMapper = vtk.Rendering.Core.vtkMapper\n\n        // Force the loading of HttpDataAccessHelper to support gzip decompression\n        const vtkHttpDataAccessHelper = vtk.IO.Core.DataAccessHelper.HttpDataAccessHelper\n\n        // ----------------------------------------------------------------------------\n        // Standard rendering code setup\n        // ----------------------------------------------------------------------------\n\n        const fullScreenRenderer = vtkFullScreenRenderWindow.newInstance();\n        const renderer = fullScreenRenderer.getRenderer();\n        const renderWindow = fullScreenRenderer.getRenderWindow();\n\n        // ----------------------------------------------------------------------------\n        // Example code\n        // ----------------------------------------------------------------------------\n        // Server is not sending the .gz and with the compress header\n        // Need to fetch the true file name and uncompress it locally\n        // ----------------------------------------------------------------------------\n\n        const reader = vtkHttpDataSetReader.newInstance({ fetchGzip: true });\n        reader.setUrl(data_path).then(() => {\n            reader.loadData().then(() => {\n                renderer.resetCamera();\n                renderWindow.render();\n            });\n        });\n\n        const mapper = vtkMapper.newInstance();\n        mapper.setInputConnection(reader.getOutputPort());\n\n        const actor = vtkActor.newInstance();\n        actor.setMapper(mapper);\n\n        renderer.addActor(actor);\n\n        // -----------------------------------------------------------\n        // Make some variables global so that you can inspect and\n        // modify objects in your browser's developer console:\n        // -----------------------------------------------------------\n\n        // global.source = reader;\n        // global.mapper = mapper;\n        // global.actor = actor;\n        // global.renderer = renderer;\n        // global.renderWindow = renderWindow;\n\n    </script>\n</body>\n\n</html>\n\n--------------------------------------------------------------------------------------------------------------\n示例 3:\n描述: Loads and visualizes a 3D polygonal data file (`test_cone.vtp`) using `vtkXMLPolyDataReader` and `vtkMapper`.\n\nVTK.js 模块: ['vtk.IO.XML.vtkXMLPolyDataReader', 'vtk.Rendering.Core.vtkActor', 'vtk.Rendering.Core.vtkMapper', 'vtk.Rendering.Misc.vtkFullScreenRenderWindow']\n代码:\n<!DOCTYPE html>\n<html lang=\"en\">\n\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>vtk.js loading poly data, need to start by live server</title>\n</head>\n\n<body>\n    <div id=\"renderer\"></div>\n    <script src=\"https://unpkg.com/vtk.js\"></script>\n    <script>\n        const vtkFullScreenRenderWindow = vtk.Rendering.Misc.vtkFullScreenRenderWindow;\n        const vtkXMLPolyDataReader = vtk.IO.XML.vtkXMLPolyDataReader;\n        const vtkActor = vtk.Rendering.Core.vtkActor;\n        const vtkMapper = vtk.Rendering.Core.vtkMapper;\n\n        // crete the render window\n        const fullScreenRenderer = vtkFullScreenRenderWindow.newInstance({ background: [0, 0, 0] });\n        const renderer = fullScreenRenderer.getRenderer();\n        const renderWindow = fullScreenRenderer.getRenderWindow();\n\n        // load the vtp data locally\n        const reader = vtkXMLPolyDataReader.newInstance();\n        // set url and load the data\n        reader.setUrl('../datasets/test_cone.vtp').then(() => {\n            reader.loadData().then(() => {\n                // assign data to actor\n                const mapper = vtkMapper.newInstance();\n                console.log(reader.getOutputData(0))\n                mapper.setInputData(reader.getOutputData(0));\n                const actor = vtkActor.newInstance();\n                actor.setMapper(mapper);\n\n                //  adding actor to render and render the data\n                renderer.addActor(actor);\n                renderer.resetCamera();\n                renderWindow.render();\n            });\n        });\n    </script>\n</body>\n\n</html>\n\n\n--------------------------------------------------------------------------------------------------------------\n示例 4:\n描述: Generates and displays a 2D random image (100x100) using `vtkImageSlice` and `vtkImageMapper`.\n\nVTK.js 模块: ['vtk.Common.Core.vtkDataArray.newInstance', 'vtk.Common.DataModel.vtkImageData', 'vtk.Rendering.Core.vtkImageMapper', 'vtk.Rendering.Core.vtkImageSlice', 'vtk.Rendering.Misc.vtkFullScreenRenderWindow']\n代码:\n<!DOCTYPE html>\n<html lang=\"en\">\n\n<head>\n    <meta charset=\"UTF-8\">\n    </style>\n</head>\n\n<body>\n    <div id=\"renderer\"></div>\n    <script src=\"https://unpkg.com/vtk.js\"></script>\n    <script>\n        const vtkFullScreenRenderWindow = vtk.Rendering.Misc.vtkFullScreenRenderWindow;\n        const vtkImageSlice = vtk.Rendering.Core.vtkImageSlice;//用于渲染二维图片切片的actor\n        const vtkImageMapper = vtk.Rendering.Core.vtkImageMapper;\n        const vtkImageData = vtk.Common.DataModel.vtkImageData;\n\n        // 创建渲染窗口\n        const fullScreenRenderer = vtkFullScreenRenderWindow.newInstance({ background: [0, 0, 0] });\n        const renderer = fullScreenRenderer.getRenderer();\n        const renderWindow = fullScreenRenderer.getRenderWindow();\n\n        // 创建图像数据\n        const imageData = vtkImageData.newInstance();\n        imageData.setDimensions(100, 100, 1);\n        imageData.setSpacing(1.0, 1.0, 1.0);\n        imageData.setOrigin(0.0, 0.0, 0.0);\n\n        // 设置图像数据的像素值\n        const scalars = new Uint8Array(100 * 100);\n        for (let i = 0; i < 100 * 100; i++) {\n            scalars[i] = Math.random() * 255;\n        }\n        imageData.getPointData().setScalars(vtk.Common.Core.vtkDataArray.newInstance({ values: scalars, numberOfComponents: 1 }));\n\n        // 创建映射器和 actor\n        const mapper = vtkImageMapper.newInstance();\n        mapper.setInputData(imageData);\n\n        const actor = vtkImageSlice.newInstance();\n        actor.setMapper(mapper);\n\n        // 将 actor 添加到渲染器\n        renderer.addActor(actor);\n        renderer.resetCamera();\n        renderWindow.render();\n    </script>\n</body>\n\n</html>\n\n\n       

        """
    # answer=get_qwen_response('生成椎体代码', model_name='claude-sonnet-4',system='you are a programmer， you should give a code by user_query')
    # get_deepseek_response('hello','deepseek-v3')
    
    # 调用get_aihub_response获取回答
    answer = get_aihub_response(
        prompt=final_prompt,
        model_name='gpt-4o-mini',
        system='You are a programmer. You should generate VTK.js visualization code based on user query.'
    )
    
    # 将结果写入文件
    output_file = 'llm_response.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Prompt: {final_prompt}\n")
        f.write(f"Model: aihub\n")
        f.write(f"Response:\n")
        f.write(answer)
    
    print(f"Response has been written to {output_file}")
    print(answer)
