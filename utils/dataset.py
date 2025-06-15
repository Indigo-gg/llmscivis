# 处理dataset相关逻辑
import json
from datetime import time
from config.app_config import app_config


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

def get_object_by_id(obj):
    """
    根据 eval_id 获取 JSON 文件中的数据。

    :param eval_id: 要获取的数据的 eval_id
    :param file_path: JSON 文件的路径
    :return: 如果找到匹配的 eval_id，则返回 EvalData 对象，否则返回 None
    """
    try:
        with open(app_config.DATASET_PATH, 'r', encoding='utf-8') as file:
            existing_data = json.load(file)
            for data_item in existing_data:
                if data_item.get("eval_id") == obj.get("evalId"):
                #    print('find',data_item)
                   return data_item
        # The following lines seem incorrect in a get function, they should be removed or moved elsewhere if needed.
        # with open(app_config.DATASET_PATH, 'w', encoding='utf-8') as file:
        #     json.dump(existing_data, file, ensure_ascii=False, indent=4)
    except (FileNotFoundError, json.JSONDecodeError):
        print('ADD_ERROR', FileNotFoundError, json.JSONDecodeError)
        return None


def modify_object(obj):
    """
    根据 eval_id 修改 JSON 文件中的数据。

    :param obj: 包含新数据的 EvalData 对象
    """
    try:
        with open(app_config.DATASET_PATH, 'r', encoding='utf-8') as file:
            existing_data = json.load(file)
            for index, data_item in enumerate(existing_data):
                if data_item.get("eval_id") == obj.get('eval_id') and data_item.get("evaluator_evaluation") is None:
                    existing_data[index]["evaluator_evaluation"] = obj.get("evaluator_evaluation")
                    existing_data[index]["score"] = obj.get("score")
                    print('\n update score and evaluatorEvaluation \n')
                    break
        with open(app_config.DATASET_PATH, 'w', encoding='utf-8') as file:
            json.dump(existing_data, file, ensure_ascii=False, indent=4)
    except (FileNotFoundError, json.JSONDecodeError):
        print('ADD_ERROR', FileNotFoundError, json.JSONDecodeError)


def modify_object_with_export(obj):
    """
    根据 eval_id 修改 JSON 文件中的数据。

    :param obj: 包含新数据的 ExportData 对象
    """
    try:
        with open(app_config.DATASET_PATH, 'r', encoding='utf-8') as file:
            existing_data = json.load(file)
            for index, data_item in enumerate(existing_data):
                if data_item.get("eval_id") == obj.get('evalId') and data_item.get("evaluatorEvaluation") is None:
                    existing_data[index]["export_time"] = obj.get("exportTime")
                    existing_data[index]["console_output"] = obj.get("consoleOutput")
                    print('\n update export_time and console_output \n')
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
