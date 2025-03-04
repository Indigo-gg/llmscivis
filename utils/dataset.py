# 处理dataset相关逻辑
import json
from datetime import time
from config import app_config


class EvalData:
    def __init__(self, prompt=None, ground_truth=None, generated_code=None, evaluator_prompt=None, generator=None,
                 evaluator=None, score=None, workflow=None, eval_id=None, eval_user=None, eval_time=None,
                 eval_status=None, manual_evaluation=None):
        self.prompt = prompt
        self.ground_truth = ground_truth
        self.generated_code = generated_code
        self.evaluator_prompt = evaluator_prompt
        self.generator = generator
        self.evaluator = evaluator
        self.score = score
        self.workflow = workflow
        self.eval_id = eval_id
        self.eval_user = eval_user
        self.eval_time = eval_time
        self.eval_status = eval_status
        self.manual_evaluation = manual_evaluation

    def show_data_info(self):
        print(f"Prompt: {self.prompt}, Ground Truth: {self.groundtruth}, Generated Code: {self.generatedcode}")


class Evaluation:
    def __init__(self, score=None, workflow=None, generator=None, evaluator=None, prompt=None, console_output=None,
                 evaluation_output=None):
        self.score = score  # Data Fidelity,
        self.workflow = workflow  # Readability
        self.generator = generator  # Interactivity
        self.evaluator = evaluator
        self.prompt = prompt
        self.console_output = console_output
        self.evaluation_output = evaluation_output

    def show_evaluation_info(self):
        print(f"Score: {self.score}, Workflow: {self.workflow}, Generator: {self.generator}")


def add_data(obj):
    # print("add_data", obj)
    try:
        # 尝试读取现有的 JSON 文件
        with open(app_config.DATASET_PATH, 'r', encoding='utf-8') as file:
            existing_data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        # 如果文件不存在或解析失败，创建一个新的列表
        print('error')
        existing_data = []

    # 将新数据添加到现有数据列表中
    existing_data.append(obj)

    # 将更新后的数据写回 JSON 文件
    with open(app_config.DATASET_PATH, 'w', encoding='utf-8') as file:
        json.dump(existing_data, file, ensure_ascii=False, indent=4)
        # print(existing_data)
        # print(t)


def delete_object(eval_id):
    """
    根据 eval_id 删除 JSON 文件中的数据。

    :param eval_id: 要删除的数据的 eval_id
    :param file_path: JSON 文件的路径
    """
    try:
        with open(app_config.DATASET_PATH, 'r', encoding='utf-8') as file:
            existing_data = json.load(file)
        # 过滤掉要删除的数据
        existing_data = [data for data in existing_data if data["eval_id"] != eval_id]
        with open(app_config.DATASET_PATH, 'w', encoding='utf-8') as file:
            json.dump(existing_data, file, ensure_ascii=False, indent=4)
    except (FileNotFoundError, json.JSONDecodeError):
        pass


def modify_object(obj):
    """
    根据 eval_id 修改 JSON 文件中的数据。

    :param obj: 包含新数据的 EvalData 对象
    :param file_path: JSON 文件的路径
    """
    try:
        with open(app_config.DATASET_PATH, 'r', encoding='utf-8') as file:
            existing_data = json.load(file)
            for i, data in enumerate(existing_data):
                if data["eval_id"] == obj['eval_id']:
                    existing_data[i] = obj
                    break
        with open(app_config.DATASET_PATH, 'w', encoding='utf-8') as file:
            json.dump(existing_data, file, ensure_ascii=False, indent=4)
    except (FileNotFoundError, json.JSONDecodeError):
        print('ADD_ERROR', FileNotFoundError, json.JSONDecodeError)


def get_all_data():
    try:
        with open(app_config.DATASET_PATH, 'r', encoding='utf-8') as file:
            existing_data = json.load(file)
        return existing_data
    except (FileNotFoundError, json.JSONDecodeError):
        return []
