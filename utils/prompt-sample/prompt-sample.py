from time import sleep
from httpx import get
from llm_agent import ollma_chat
import os

sample_system="""
你是一个专业vtkjs的代码助手，现在需要你理解vtkjs代码，根据下面的代码生成vtkjs对应的描述。
请保证描述清晰,还原出代码表达的用户需求
下面是一个vtkjs的代码转化为描述的示例：
代码：
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    </style>
</head>

<body>
    <div id="renderer"></div>
    <script src="https://unpkg.com/vtk.js"></script>
    <script>
        const vtkFullScreenRenderWindow = vtk.Rendering.Misc.vtkFullScreenRenderWindow;
        const vtkImageSlice = vtk.Rendering.Core.vtkImageSlice;//用于渲染二维图片切片的actor
        const vtkImageMapper = vtk.Rendering.Core.vtkImageMapper;
        const vtkImageData = vtk.Common.DataModel.vtkImageData;

        // 创建渲染窗口
        const fullScreenRenderer = vtkFullScreenRenderWindow.newInstance({ background: [0, 0, 0] });
        const renderer = fullScreenRenderer.getRenderer();
        const renderWindow = fullScreenRenderer.getRenderWindow();

        // 创建图像数据
        const imageData = vtkImageData.newInstance();
        imageData.setDimensions(100, 100, 1);
        imageData.setSpacing(1.0, 1.0, 1.0);
        imageData.setOrigin(0.0, 0.0, 0.0);

        // 设置图像数据的像素值
        const scalars = new Uint8Array(100 * 100);
        for (let i = 0; i < 100 * 100; i++) {
            scalars[i] = Math.random() * 255;
        }
        imageData.getPointData().setScalars(vtk.Common.Core.vtkDataArray.newInstance({ values: scalars, numberOfComponents: 1 }));

        // 创建映射器和 actor
        const mapper = vtkImageMapper.newInstance();
        mapper.setInputData(imageData);

        const actor = vtkImageSlice.newInstance();
        actor.setMapper(mapper);

        // 将 actor 添加到渲染器
        renderer.addActor(actor);
        renderer.resetCamera();
        renderWindow.render();
    </script>
</body>

</html>

描述示例：
Create 2D image data with dimensions of (100, 100, 1), where the field values are random. This data is then rendered using a vtk renderer, specifically leveraging vtkImageSlice and vtkImageMapper for displaying the image slice. The actor (an instance of vtkImageSlice) is set up with the mapper and then added to the renderer for visualization.
"""

def get_llm_response(prompt,system):
    response = ollma_chat.get_qwen_response(prompt, model_name='qwen-turbo-2025-07-15', system=system)
    print(response)

    return response



if __name__ == '__main__':
       # 循环读取data\vtkjs-examples\prompt-sample 路径下的所有文件夹下的所有code.html文件，赋值给content
    base_dir = r'd:\Pcode\LLM4VIS\llmscivis\data\vtkjs-examples\prompt-sample'
    for root, dirs, files in os.walk(base_dir):
        # print(root)

        for file in files:
            if file == 'code.html':
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = '以下是要描述的vtkjs代码，请直接给出描述：'+f.read() + '\n\n'
                    res=get_llm_response(content,sample_system)
                    print(res)
                    sleep(100)
                    # 把结果写在同文件夹下面的description.txt中
                    desc_path = os.path.join(root, 'description.txt')

                    with open('./des.txt', 'w', encoding='utf-8') as f:
                        f.write(res)
                    with open(desc_path, 'w', encoding='utf-8') as f:
                        f.write(res)
