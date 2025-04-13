# ... existing code ...
from config.ollama_config import models
from llm_agent.ollma_chat import get_llm_response
import re


class EvaluateAgent:
    def __init__(self):
        pass


def extract_score(text):
    # 定义正则表达式模式，匹配 <Score> 和 </Score> 之间的所有字符
    pattern = r'<Score>(.*?)</Score>'

    # 使用 re.search 查找匹配项
    match = re.search(pattern, text)
    if match:
        # 提取分数
        score = match.group(1)
        return score
    else:
        return None


def evaluate(generated_code, ground_truth, evaluator_prompt, evaluator):
    ""
    """
    评估函数，这里简单返回数据的长度作为评估结果
    :param self:
    :param data: 待评估的数据
    :return: 评估结果
    """
    # evaluator_prompt=evaluator_prompt.replace("[GENERATED_CODE]",generated_code).replace("[GROUND_TRUTH]",ground_truth)
    print('evaluator_prompt', evaluator_prompt)
    prompt = f"""
    Ground truth: {ground_truth}\n
    Generated code: {generated_code}\n
    """
    response = get_llm_response(prompt, model_name=evaluator, system=evaluator_prompt)
    score = extract_score(response)
    return {
        'score': score,
        'evaluator_evaluation': response
    }


def display_result(self, result):
    """
    展示评估结果的方法
    :param result: 评估结果
    """
    print(f"评估结果为: {result}")
