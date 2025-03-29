import re
from typing import Dict, List, Optional

class ErrorAnalyzer:
    ERROR_PATTERNS = {
        'VueSyntaxError': r'Component is missing template or render function',
        'FlaskRouteError': r'404 Not Found',
        'APIDataError': r'Unexpected response structure',
        'ImportError': r'Cannot find module|Module not found',
        'SyntaxError': r'Unexpected token|Unexpected identifier|Invalid or unexpected token',
        'RuntimeError': r'Cannot read property .* of undefined|TypeError: .* is not a function',
        'StyleError': r'Failed to compile|Invalid CSS syntax',
        'BuildError': r'Build failed|Failed to compile',
        'NetworkError': r'Network Error|Failed to fetch',
        'StateError': r'Cannot read property .* of null|undefined'
    }

    MAX_ITERATIONS = 5

    def __init__(self):
        self.iteration_count = 0
        self.error_history: List[Dict] = []

    def analyze_log(self, log: str) -> Dict:
        self.iteration_count += 1
        errors = []

        for error_type, pattern in self.ERROR_PATTERNS.items():
            if re.search(pattern, log, re.IGNORECASE):
                errors.append({
                    'type': error_type,
                    'prompt': self.generate_prompt(error_type),
                    'log': log
                })

        result = {
            'iteration': self.iteration_count,
            'errors': errors
        }

        self.error_history.append(result)
        return result

    def generate_prompt(self, error_type: str) -> str:
        prompts = {
            'VueSyntaxError': "请修复Vue3组件缺少template/render的问题，确保组件定义了正确的模板结构",
            'FlaskRouteError': "请检查Flask路由配置，确保路由路径正确且与前端请求匹配",
            'APIDataError': "请验证API响应数据结构，确保返回格式符合前端要求",
            'ImportError': "请检查模块依赖是否正确安装，并确保import语句路径正确",
            'SyntaxError': "请修复代码语法错误，检查是否有未闭合的括号或引号",
            'RuntimeError': "请检查运行时错误，确保对象和方法的调用顺序正确",
            'StyleError': "请修复CSS语法错误，确保样式规则格式正确",
            'BuildError': "请解决项目构建错误，检查配置文件和依赖版本",
            'NetworkError': "请处理网络请求错误，确保API端点可用且请求格式正确",
            'StateError': "请修复状态管理相关错误，确保在访问属性前初始化对象"
        }
        return prompts.get(error_type, "请根据错误日志检查并修复代码实现")

    def get_error_summary(self) -> Dict:
        return {
            'total_iterations': self.iteration_count,
            'error_history': self.error_history,
            'resolved': not bool(self.error_history[-1]['errors']) if self.error_history else False
        }

    def reset(self) -> None:
        self.iteration_count = 0
        self.error_history = []
