"""
快速验证脚本 - 测试 mock_generation 模块的导入和基本功能

运行此脚本验证所有依赖和导入是否正确
"""

import sys
import os
from pathlib import Path

print("="*80)
print("Mock Generation Pipeline - 导入验证")
print("="*80)

# 检查项目根目录
project_root = Path(__file__).parent
print(f"\n[1] 项目根目录: {project_root}")

# 添加到 Python 路径
sys.path.insert(0, str(project_root))

# 测试导入
test_results = {
    'passed': [],
    'failed': []
}

def test_import(module_name, description):
    """测试导入模块"""
    try:
        __import__(module_name)
        test_results['passed'].append(f"✓ {description}: {module_name}")
        print(f"  ✓ {description}")
        return True
    except Exception as e:
        test_results['failed'].append(f"✗ {description}: {module_name} - {str(e)}")
        print(f"  ✗ {description}: {str(e)[:100]}")
        return False

print("\n[2] 测试基础依赖...")
test_import('pandas', "pandas (数据处理)")
test_import('openpyxl', "openpyxl (Excel 引擎)")
test_import('json', "json (数据序列化)")
test_import('time', "time (时间处理)")

print("\n[3] 测试项目模块...")
test_import('config.ollama_config', "ollama_config (模型配置)")
test_import('llm_agent.prompt_agent', "prompt_agent (提示词拓展)")
test_import('llm_agent.rag_agent', "rag_agent (RAG 检索)")
test_import('llm_agent.ollma_chat', "ollma_chat (LLM 调用)")
test_import('llm_agent.evaluator_agent', "evaluator_agent (代码评估)")
test_import('RAG.retriever_v3', "retriever_v3 (V3 检索器)")

print("\n[4] 测试 mock_generation 模块...")
test_import('test.mock_generation.mock_generation', "MockGenerationPipeline (主模块)")

# 检查关键函数是否存在
print("\n[5] 检查关键函数...")

try:
    from RAG.retriever_v3 import process_benchmark_prompts_for_generation
    print("  ✓ process_benchmark_prompts_for_generation() 函数存在")
    test_results['passed'].append("✓ process_benchmark_prompts_for_generation()")
except Exception as e:
    print(f"  ✗ process_benchmark_prompts_for_generation() 函数缺失: {e}")
    test_results['failed'].append(f"✗ process_benchmark_prompts_for_generation() - {e}")

try:
    from test.mock_generation.mock_generation import MockGenerationPipeline
    print("  ✓ MockGenerationPipeline 类存在")
    test_results['passed'].append("✓ MockGenerationPipeline 类")
except Exception as e:
    print(f"  ✗ MockGenerationPipeline 类缺失: {e}")
    test_results['failed'].append(f"✗ MockGenerationPipeline 类 - {e}")

# 检查文件结构
print("\n[6] 检查文件结构...")

required_files = [
    'test/__init__.py',
    'test/mock_generation/__init__.py',
    'test/mock_generation/mock_generation.py',
    'test/mock_generation/README.md',
    'test/mock_generation/test_example.py',
    'MOCK_GENERATION_INTEGRATION.md',
]

for file_path in required_files:
    full_path = project_root / file_path
    if full_path.exists():
        print(f"  ✓ {file_path}")
        test_results['passed'].append(f"✓ {file_path}")
    else:
        print(f"  ✗ {file_path} (不存在)")
        test_results['failed'].append(f"✗ {file_path} (不存在)")

# 测试基本功能
print("\n[7] 测试基本功能...")

try:
    from test.mock_generation.mock_generation import MockGenerationPipeline
    
    # 创建实例（不需要真实文件，只测试初始化）
    pipeline = MockGenerationPipeline('test.xlsx')
    print("  ✓ MockGenerationPipeline 实例化成功")
    test_results['passed'].append("✓ MockGenerationPipeline 实例化")
    
    # 检查方法是否存在
    if hasattr(pipeline, 'run_complete_pipeline'):
        print("  ✓ run_complete_pipeline() 方法存在")
        test_results['passed'].append("✓ run_complete_pipeline() 方法")
    
    if hasattr(pipeline, 'print_results_summary'):
        print("  ✓ print_results_summary() 方法存在")
        test_results['passed'].append("✓ print_results_summary() 方法")
    
except Exception as e:
    print(f"  ✗ 基本功能测试失败: {e}")
    test_results['failed'].append(f"✗ 基本功能测试 - {e}")

# 打印测试总结
print("\n" + "="*80)
print("验证总结")
print("="*80)

passed_count = len(test_results['passed'])
failed_count = len(test_results['failed'])
total_count = passed_count + failed_count

print(f"\n总计: {total_count} 项测试")
print(f"通过: {passed_count} ✓")
print(f"失败: {failed_count} ✗")

if test_results['failed']:
    print("\n失败项目:")
    for item in test_results['failed']:
        print(f"  {item}")
    print("\n[建议] 检查上述失败项，确保所有依赖已安装")
else:
    print("\n[成功] 所有验证通过！✓")
    print("\n可以现在运行以下命令:")
    print("  python test/mock_generation/mock_generation.py --excel <your_excel_file>")
    print("\n或使用 Python 代码:")
    print("  from test.mock_generation.mock_generation import MockGenerationPipeline")
    print("  pipeline = MockGenerationPipeline('your_excel.xlsx')")
    print("  result = pipeline.run_complete_pipeline()")

print("\n" + "="*80)

# 返回测试状态
sys.exit(0 if failed_count == 0 else 1)
