# ... existing code ...
from config.ollama_config import models
from llm_agent.ollma_chat import get_llm_response
import re
import xml.etree.ElementTree as ET


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


def parse_evaluation_xml(xml_text):
    """
    解析评估XML格式，提取结构化数据
    :param xml_text: LLM返回的XML格式字符串
    :return: 结构化字典对象或None
    """
    try:
        # 尝试解析XML
        root = ET.fromstring(xml_text)
        
        # 提取维度分数
        dimensions = {}
        for dimension in root.findall('Dimension'):
            name = dimension.get('name')
            score_elem = dimension.find('Score')
            reason_elem = dimension.find('Reason')
            
            if name and score_elem is not None:
                try:
                    score = float(score_elem.text.strip())
                    reason = reason_elem.text.strip() if reason_elem is not None else ''
                    dimensions[name] = {
                        'score': score,
                        'reason': reason
                    }
                except (ValueError, AttributeError) as e:
                    print(f"Error parsing dimension {name}: {e}")
                    continue
        
        # 提取总分和总结
        summary = root.find('Summary')
        overall_score = None
        critique = ''
        
        if summary is not None:
            overall_elem = summary.find('OverallScore')
            critique_elem = summary.find('Critique')
            
            if overall_elem is not None:
                try:
                    overall_score = float(overall_elem.text.strip())
                except (ValueError, AttributeError):
                    pass
            
            if critique_elem is not None:
                critique = critique_elem.text.strip() if critique_elem.text else ''
        
        # 如果没有overall_score，计算平均值
        if overall_score is None and dimensions:
            scores = [d['score'] for d in dimensions.values() if 'score' in d]
            if scores:
                overall_score = sum(scores) / len(scores)
        
        return {
            'dimensions': dimensions,
            'overall': overall_score,
            'critique': critique,
            'raw_xml': xml_text
        }
    
    except ET.ParseError as e:
        print(f"XML parsing failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error in XML parsing: {e}")
        return None


def evaluate(generated_code, ground_truth, evaluator_prompt, evaluator):
    """
    评估函数，调用LLM并解析结果
    :param generated_code: 生成的代码
    :param ground_truth: 标准代码
    :param evaluator_prompt: 评估提示词
    :param evaluator: 评估模型名称
    :return: 评估结果字典
    """
    print('evaluator_prompt', evaluator_prompt[:100] + '...')  # 只打印前100个字符
    prompt = f"""
    Ground truth: {ground_truth}

    Generated code: {generated_code}

    """
    
    # 获取LLM响应
    response = get_llm_response(prompt, model_name=evaluator, system=evaluator_prompt)
    
    # 尝试解析XML格式
    parsed_evaluation = parse_evaluation_xml(response)
    
    # 提取分数（兼容旧版本）
    if parsed_evaluation and parsed_evaluation.get('overall') is not None:
        score = str(parsed_evaluation['overall'])
    else:
        # 回退到旧的提取方式
        score = extract_score(response)
    
    return {
        'score': score,
        'evaluator_evaluation': response,
        'parsed_evaluation': parsed_evaluation  # 新增字段
    }


def display_result(self, result):
    """
    展示评估结果的方法
    :param result: 评估结果
    """
    print(f"评估结果为: {result}")
