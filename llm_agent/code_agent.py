import re

class ErrorAnalyzer:
    ERROR_PATTERNS = {
        'VueSyntaxError': r'Component is missing template or render function',
        'FlaskRouteError': r'404 Not Found',
        'APIDataError': r'Unexpected response structure'
    }

    def analyze_log(self, log):
        for error_type, pattern in self.ERROR_PATTERNS.items():
            if re.search(pattern, log):
                return self.generate_prompt(error_type)
        return "General error occurred"

    def generate_prompt(self, error_type):
        prompts = {
            'VueSyntaxError': "修复Vue3组件缺少template/render的问题...",
            'FlaskRouteError': "检查Flask路由配置，确保...",
            'APIDataError': "验证API响应数据结构，需要包含..."
        }
        return prompts.get(error_type, "请检查代码实现")
