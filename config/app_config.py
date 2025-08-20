class AppConfig:
    def __init__(self):
        self.ollama_url = "http://127.0.0.1:11435"
        self.deepseek_url = "https://ark.cn-beijing.volces.com/api/v3/"
        self.qwen_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.coreai_url="https://api.xty.app/v1"
        self.system = {
            'deepseek': "",
            'qwen': "", 
        }
        self.keywords = {
            'QUESTION':"__QUESTION__"
        }
        self.deepseek_apikey = '13e5c21e-66bf-4b13-a4d8-a414956e7a39'
        self.qwen_apikey = 'sk-bb51f49d7aac4a04adde0794f3f1dfe9'
        # self.coreai_apikey="sk-uGHmKbQF4MixICHP6f21D975Fa7c4d6e9c1f4eAb182987C8"
        self.coreai_apikey="sk-uGHmKbQF4MixIJh89f21D97jklowc4d6e9c1f4eAb182987C8"

        self.eval_status = ['failed','completed']
        self.DATASET_PATH = './utils/dataset/dataset.json'
        self.VTKJS_COMMON_APIS = ["vtkCalculator", "vtkMapper", "vtkContourTriangulator", "vtkSampleFunction", "vtkImageMarchingCubes", "vtkImageMarchingSquares", "vtkImageSlice", "vtkImageMapper", "vtkImageStreamline", "vtkOutlineFilter", "vtkHttpDataSetReader", "vtkCylinderSource", "vtkTriangleFilter", "vtkVolumeMapper", "vtkVolumeActor", "vtkElevationReader", "vtkGCodeReader", "vtkOBJReader", "vtkMTLReader", "vtkPDBReader", "vtkMoleculeToRepresentation", "vtkXMLPolyDataReader", "vtkStickMapper", "vtkXMLImageDataWriter", "vtkXMLImageDataReader", "vtkXMLPolyDataWriter", "vtkGlyph3DMapper", "vtkRTAnalyticSource", "vtkSphereSource", "vtkSphereMapper", "vtkPlaneSource"] # Added more based on query examples

        self.faissDB_path = 'data/faiss_cache'
        self.TRUNK_SIZE = 3000
        self.TRUNK_OVERLAP = 200

app_config = AppConfig()
