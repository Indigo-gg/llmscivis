from typing import Dict, List
import re
from .code_agent import ErrorAnalyzer

class FixAgent(ErrorAnalyzer):
    """
    代码修复智能体，继承自ErrorAnalyzer基类
    提供更智能的错误分析和修复建议功能
    """
    
    def __init__(self):
        super().__init__()
        
    def analyze_and_fix(self, error_data: Dict) -> Dict:
        """
        分析前端发送的错误数据并生成修复建议
        
        参数:
            error_data: {
                'error_type': str,  # 错误类型
                'error_message': str,  # 错误信息
                'code_snippet': str,  # 相关代码片段
                'context': Dict  # 其他上下文信息
            }
            
        返回:
            {
                'errors': List[Dict],  # 错误详细信息列表
                'suggestion': str,  # 综合修复建议
                'should_retry': bool,  # 是否需要重试
                'new_code': str,  # 修复后的代码建议
                'iteration': int  # 当前迭代次数
            }
        """
        # 组合错误信息
        error_info = f"{error_data.get('error_type', '')}: {error_data.get('error_message', '')}"
        
        # 调用父类方法分析错误
        analysis = super().analyze_log(error_info)
        
        # 分析代码中的错误
        code_snippet = error_data.get('code_snippet', '')
        error_details = []
        suggestions = []
        
        for error in analysis['errors']:
            error_detail = {
                'type': error['type'],
                'location': self._locate_error(code_snippet, error['type']),
                'description': error['prompt'],
                'severity': self._assess_severity(error['type'])
            }
            error_details.append(error_detail)
            suggestions.append(f"- {error['type']}: {error['prompt']}")
        
        # 生成综合修复建议
        suggestion = "\n".join([
            "发现以下问题：",
            *suggestions,
            "\n建议修复步骤：",
            *[f"{i+1}. {self._generate_fix_step(error)}" 
              for i, error in enumerate(error_details)]
        ])
        
        # 尝试生成修复后的代码
        new_code = self._attempt_code_fix(code_snippet, error_details) if code_snippet else ''
        
        return {
            'errors': error_details,
            'suggestion': suggestion,
            'should_retry': len(error_details) > 0,
            'new_code': new_code,
            'iteration': analysis['iteration']
        }
        
    def _locate_error(self, code: str, error_type: str) -> Dict:
        """定位错误在代码中的位置"""
        # 根据错误类型分析可能的错误位置
        # 这里可以实现更复杂的错误定位逻辑
        return {
            'line': -1,  # 暂时返回-1表示未知行号
            'column': -1,
            'context': ''
        }
    
    def _assess_severity(self, error_type: str) -> str:
        """评估错误的严重程度"""
        severity_map = {
            'ReferenceError': 'high',
            'SyntaxError': 'high',
            'TypeError': 'medium',
            'RuntimeError': 'medium',
            'Warning': 'low'
        }
        return severity_map.get(error_type, 'medium')
    
    def _generate_fix_step(self, error: Dict) -> str:
        """根据错误详情生成修复步骤"""
        return f"修复 {error['type']} - {error['description']}"
    
    def _attempt_code_fix(self, code: str, errors: List[Dict]) -> str:
        """尝试自动修复代码"""
        # 这里可以实现自动代码修复逻辑
        # 当前版本返回空字符串，表示暂不支持自动修复
        return ''