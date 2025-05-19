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
        self.coreai_apikey="sk-uGHmKbQF4MixICHP6f21D975Fa7c4d6e9c1f4eAb182987C8"

        self.eval_status = ['failed','completed']
        self.DATASET_PATH = './utils/dataset/dataset.json'
        self.VTKJS_COMMON_APIS = [
            "vtkConeSource", "vtkSphereSource", "vtkCylinderSource", "vtkPlaneSource", 
            "vtkLineSource", "vtkCubeSource", "vtkPolyData", "vtkMapper", "vtkActor",
            "vtkRenderer", "vtkRenderWindow", "vtkRenderWindowInteractor", "vtkCamera",
            "vtkVolume", "vtkVolumeMapper", "vtkColorTransferFunction", "vtkPiecewiseFunction",
            "vtkImageData", "vtkPointData", "vtkCellData", "vtkDataArray", "vtkPoints",
            "vtkCellArray", "vtkPolyDataMapper", "vtkProperty", "vtkLight", "vtkLookupTable"
        ]
        self.faissDB_path = 'data/faiss_cache'
        self.TRUNK_SIZE = 3000
        self.TRUNK_OVERLAP = 200

app_config = AppConfig()
