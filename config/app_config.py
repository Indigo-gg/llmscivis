class AppConfig:
    def __init__(self):
        self.ollama_url = "http://127.0.0.1:11435"
        self.deepseek_url = "https://ark.cn-beijing.volces.com/api/v3/"
        self.system = [
            {
                'prompt': 'you are a programmer， you should give a code by user_query'
            }
        ]
        self.keywords = {
            'QUESTION':"__QUESTION__"
        }
        self.apikey = '13e5c21e-66bf-4b13-a4d8-a414956e7a39'
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
