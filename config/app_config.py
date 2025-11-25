from .secrets import secrets
class AppConfig:
    def __init__(self):
        self.ollama_url = "http://127.0.0.1:11435"
        self.deepseek_url = "https://ark.cn-beijing.volces.com/api/v3/"
        self.qwen_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.cst_url="https://uni-api.cstcloud.cn/v1"
        self.coreai_url="https://api.xty.app/v1"
        self.aihub_url="https://aihubmix.com/v1"
        self.system = {
            'deepseek': "",
            'qwen': "", 
        }
        self.keywords = {
            'QUESTION':"__QUESTION__"
        }
       # 从本地密钥文件加载API密钥
        try:
            self.deepseek_apikey = secrets.deepseek_apikey
            self.qwen_apikey = secrets.qwen_apikey
            self.coreai_apikey = secrets.coreai_apikey
            self.aihub_apikey = secrets.aihub_apikey
            self.cst_apikey = secrets.cst_apikey
            
        except ImportError:
            # 如果没有secrets.py文件，使用默认值或抛出警告
            print("警告: 未找到secrets.py文件，请创建config/secrets.py并配置API密钥")
            self.deepseek_apikey = ''
            self.qwen_apikey = ''
            self.coreai_apikey = ''
            self.aihub_apikey = ''
            self.cst_apikey = ''
            


        self.eval_status = ['failed','completed']
        self.DATASET_PATH = './utils/dataset/dataset.json'
        self.VTKJS_COMMON_APIS = ["vtkCalculator", "vtkMapper", "vtkContourTriangulator", "vtkSampleFunction", "vtkImageMarchingCubes", "vtkImageMarchingSquares", "vtkImageSlice", "vtkImageMapper", "vtkImageStreamline", "vtkOutlineFilter", "vtkHttpDataSetReader", "vtkCylinderSource", "vtkTriangleFilter", "vtkVolumeMapper", "vtkVolumeActor", "vtkElevationReader", "vtkGCodeReader", "vtkOBJReader", "vtkMTLReader", "vtkPDBReader", "vtkMoleculeToRepresentation", "vtkXMLPolyDataReader", "vtkStickMapper", "vtkXMLImageDataWriter", "vtkXMLImageDataReader", "vtkXMLPolyDataWriter", "vtkGlyph3DMapper", "vtkRTAnalyticSource", "vtkSphereSource", "vtkSphereMapper", "vtkPlaneSource"] # Added more based on query examples

        self.faissDB_path = 'data/faiss_cache'
        self.TRUNK_SIZE = 3000
        self.TRUNK_OVERLAP = 200

app_config = AppConfig()
