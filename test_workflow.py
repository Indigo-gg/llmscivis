#!/usr/bin/env python3
"""
快速测试提示词拓展可视化工作流程
"""

import json
import requests

# API 基础 URL
BASE_URL = "http://localhost:5000"

def test_query_expansion():
    """测试提示词拓展"""
    print("=" * 60)
    print("测试 1: 提示词拓展")
    print("=" * 60)
    
    payload = {
        "prompt": "Generate HTML with vtk.js to visualize volume rendering of a VTI file",
        "groundTruth": "<html></html>",
        "generator": "qwen2.5-coder:7b",
        "evaluator": "qwen2.5-coder:7b",
        "workflow": {
            "inquiryExpansion": True,
            "rag": False
        },
        "evaluatorPrompt": "Evaluate the code",
        "generatorPrompt": "Generate VTK.js code",
        "evalUser": "test_user"
    }
    
    print(f"\n发送请求到: {BASE_URL}/generate")
    print(f"Workflow: inquiryExpansion=True, rag=False")
    
    try:
        response = requests.post(f"{BASE_URL}/generate", json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        print("\n✓ 请求成功!")
        
        # 检查 analysis 字段
        if 'analysis' in data:
            analysis = data['analysis']
            print(f"\n提示词拓展结果 (共 {len(analysis)} 个步骤):")
            print("-" * 60)
            
            for i, step in enumerate(analysis, 1):
                print(f"\n步骤 {i}:")
                print(f"  Phase: {step.get('phase', 'N/A')}")
                print(f"  Step Name: {step.get('step_name', 'N/A')}")
                print(f"  VTK Modules: {', '.join(step.get('vtk_modules', []))}")
                print(f"  Description: {step.get('description', 'N/A')[:100]}...")
            
            return analysis
        else:
            print("\n✗ 响应中没有 'analysis' 字段")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\n✗ 请求失败: {e}")
        return None


def test_retrieval(analysis_data):
    """测试检索功能"""
    print("\n" + "=" * 60)
    print("测试 2: RAG 检索")
    print("=" * 60)
    
    if not analysis_data:
        print("\n跳过测试（没有拓展数据）")
        return None
    
    # 模拟用户编辑：修改第一个步骤
    edited_analysis = json.loads(json.dumps(analysis_data))  # Deep copy
    if len(edited_analysis) > 0:
        edited_analysis[0]['step_name'] = "【已编辑】" + edited_analysis[0]['step_name']
        edited_analysis[0]['description'] = "【用户修改】" + edited_analysis[0]['description']
    
    payload = {
        "analysis": edited_analysis,
        "prompt": "Generate volume rendering"
    }
    
    print(f"\n发送请求到: {BASE_URL}/retrieval")
    print(f"使用编辑后的拓展数据（共 {len(edited_analysis)} 个步骤）")
    
    try:
        response = requests.post(f"{BASE_URL}/retrieval", json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('success'):
            print("\n✓ 检索成功!")
            
            retrieval_results = data.get('retrieval_results', [])
            print(f"\n检索结果 (共 {len(retrieval_results)} 个示例):")
            print("-" * 60)
            
            for i, result in enumerate(retrieval_results[:5], 1):  # 只显示前5个
                print(f"\n示例 {i}:")
                print(f"  Title: {result.get('title', 'N/A')}")
                print(f"  Relevance: {result.get('relevance', 0):.4f}")
                print(f"  Matched Keywords: {', '.join(result.get('matched_keywords', []))}")
                print(f"  Description: {result.get('description', 'N/A')[:80]}...")
            
            if len(retrieval_results) > 5:
                print(f"\n  ... 还有 {len(retrieval_results) - 5} 个结果")
            
            return retrieval_results
        else:
            print(f"\n✗ 检索失败: {data.get('error', 'Unknown error')}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\n✗ 请求失败: {e}")
        return None


def test_full_workflow():
    """测试完整工作流程"""
    print("\n" + "=" * 60)
    print("测试 3: 完整工作流程（拓展 + 检索 + 生成）")
    print("=" * 60)
    
    payload = {
        "prompt": "Generate HTML with vtk.js to create a cone visualization with interactive controls",
        "groundTruth": "<html></html>",
        "generator": "qwen2.5-coder:7b",
        "evaluator": "qwen2.5-coder:7b",
        "workflow": {
            "inquiryExpansion": True,
            "rag": True  # 启用 RAG
        },
        "evaluatorPrompt": "Evaluate the code",
        "generatorPrompt": "Generate VTK.js code",
        "evalUser": "test_user"
    }
    
    print(f"\n发送请求到: {BASE_URL}/generate")
    print(f"Workflow: inquiryExpansion=True, rag=True")
    
    try:
        response = requests.post(f"{BASE_URL}/generate", json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        print("\n✓ 完整流程执行成功!")
        
        # 分析结果
        if 'analysis' in data:
            print(f"\n提示词拓展: {len(data['analysis'])} 个步骤")
        
        if 'retrieval_results' in data:
            print(f"检索结果: {len(data['retrieval_results'])} 个示例")
        
        if 'generated_code' in data:
            code_length = len(data['generated_code'])
            print(f"生成代码: {code_length} 字符")
            
            # 显示代码预览
            print("\n生成代码预览:")
            print("-" * 60)
            print(data['generated_code'][:500])
            if code_length > 500:
                print(f"\n... (还有 {code_length - 500} 个字符)")
        
        return True
            
    except requests.exceptions.RequestException as e:
        print(f"\n✗ 请求失败: {e}")
        return False


def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║     提示词拓展可视化工作流程 - 测试脚本                    ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    print(f"\n目标服务器: {BASE_URL}")
    print("请确保后端服务已启动 (python app.py)\n")
    
    input("按 Enter 开始测试...")
    
    # 测试 1: 提示词拓展
    analysis_data = test_query_expansion()
    
    # 测试 2: 检索
    if analysis_data:
        input("\n按 Enter 继续测试检索功能...")
        test_retrieval(analysis_data)
    
    # 测试 3: 完整流程
    input("\n按 Enter 测试完整工作流程...")
    test_full_workflow()
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
    
    print("""
    
下一步操作:
1. 启动前端: cd front && npm run dev
2. 访问: http://localhost:5173
3. 在界面中测试:
   - 勾选 "Inquiry Expansion"
   - 输入查询
   - 点击 Generate
   - 在 Retrieval 面板查看时间轴
   - 编辑步骤
   - 点击 "Proceed to Retrieval"
   - 查看检索结果
   - 点击 "Proceed to Generation"
    """)


if __name__ == "__main__":
    main()
