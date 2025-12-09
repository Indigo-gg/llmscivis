#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 retriever_v3 与提示词拓展的集成
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_agent.prompt_agent import analyze_query
from llm_agent.rag_agent import RAGAgent
from config.ollama_config import ollama_config

def test_full_workflow():
    """测试完整的工作流程"""
    print("=" * 80)
    print("测试 retriever_v3 与提示词拓展的集成")
    print("=" * 80)
    
    # 1. 模拟用户查询
    user_query = """Generate HTML with vtk.js to visualize volume rendering.
Load from http://127.0.0.1:5000/dataset/airfoil_oneslice.vtp
Scalar Mapping: Activates the p scalar array for color encoding
Visualization: Renders the colors and representation, positions the camera to focus on the dataset bounds"""
    
    print(f"\n📝 用户查询:\n{user_query}\n")
    
    # 2. 提示词拓展
    print("🔄 步骤 1: 提示词拓展...")
    analysis = analyze_query(user_query, model_name=ollama_config.inquiry_expansion_model)
    
    if analysis:
        print(f"✅ 提示词拓展成功，生成了 {len(analysis)} 个步骤:")
        for i, step in enumerate(analysis):
            print(f"\n  步骤 {i+1}:")
            print(f"    阶段: {step.get('phase', 'N/A')}")
            print(f"    名称: {step.get('step_name', 'N/A')}")
            print(f"    模块: {step.get('vtk_modules', [])}")
            print(f"    描述: {step.get('description', 'N/A')[:100]}...")
    else:
        print("❌ 提示词拓展失败")
        return
    
    # 3. RAG 检索 (使用 retriever_v3)
    print("\n🔄 步骤 2: RAG 检索 (使用 retriever_v3)...")
    rag_agent = RAGAgent(use_v3=True)  # 使用 v3
    
    try:
        final_prompt = rag_agent.search(analysis, user_query)
        print(f"✅ RAG 检索成功")
        print(f"\n📄 最终 Prompt 长度: {len(final_prompt)} 字符")
        print(f"\n最终 Prompt 预览 (前500字符):\n{final_prompt[:500]}...\n")
        
        # 4. 获取检索元数据
        retrieval_results = rag_agent.get_retrieval_metadata()
        print(f"\n📊 检索到 {len(retrieval_results)} 条结果:")
        for i, result in enumerate(retrieval_results[:3]):  # 只显示前3条
            print(f"\n  结果 {i+1}:")
            print(f"    标题: {result.get('title', 'N/A')}")
            print(f"    相关性分数: {result.get('relevance', 0):.4f}")
            print(f"    匹配关键词: {result.get('matched_keywords', [])}")
            print(f"    描述: {result.get('description', 'N/A')[:100]}...")
        
        print("\n✅ 完整流程测试成功!")
        return True
        
    except Exception as e:
        print(f"❌ RAG 检索失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_without_expansion():
    """测试不使用提示词拓展的情况"""
    print("\n" + "=" * 80)
    print("测试不使用提示词拓展的情况")
    print("=" * 80)
    
    user_query = "Generate a cone visualization with vtk.js"
    print(f"\n📝 用户查询:\n{user_query}\n")
    
    print("🔄 RAG 检索 (不使用提示词拓展)...")
    rag_agent = RAGAgent(use_v3=True)
    
    try:
        # analysis 为空，将使用原始 query
        final_prompt = rag_agent.search(None, user_query)
        print(f"✅ RAG 检索成功")
        print(f"\n📄 最终 Prompt 长度: {len(final_prompt)} 字符")
        
        retrieval_results = rag_agent.get_retrieval_metadata()
        print(f"\n📊 检索到 {len(retrieval_results)} 条结果")
        
        print("\n✅ 无提示词拓展流程测试成功!")
        return True
        
    except Exception as e:
        print(f"❌ RAG 检索失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def compare_v2_and_v3():
    """对比 retriever_v2 和 retriever_v3 的检索结果"""
    print("\n" + "=" * 80)
    print("对比 retriever_v2 和 retriever_v3")
    print("=" * 80)
    
    user_query = "Create a sphere with vtkSphereSource"
    
    # 简单的分析结果（模拟）
    analysis = [
        {
            "phase": "Data Processing",
            "step_name": "Create Sphere",
            "vtk_modules": ["vtkSphereSource"],
            "description": "Create a sphere using vtkSphereSource"
        }
    ]
    
    print(f"\n📝 用户查询: {user_query}\n")
    
    # 测试 v2
    print("🔄 使用 retriever_v2...")
    try:
        rag_v2 = RAGAgent(use_v3=False)
        prompt_v2 = rag_v2.search(analysis, user_query)
        results_v2 = rag_v2.get_retrieval_metadata()
        print(f"✅ V2 检索到 {len(results_v2)} 条结果")
    except Exception as e:
        print(f"❌ V2 失败: {e}")
        results_v2 = []
    
    # 测试 v3
    print("\n🔄 使用 retriever_v3...")
    try:
        rag_v3 = RAGAgent(use_v3=True)
        prompt_v3 = rag_v3.search(analysis, user_query)
        results_v3 = rag_v3.get_retrieval_metadata()
        print(f"✅ V3 检索到 {len(results_v3)} 条结果")
    except Exception as e:
        print(f"❌ V3 失败: {e}")
        results_v3 = []
    
    # 对比结果
    print("\n📊 结果对比:")
    print(f"  V2 结果数: {len(results_v2)}")
    print(f"  V3 结果数: {len(results_v3)}")
    
    if results_v3:
        print(f"\n  V3 前3条结果:")
        for i, r in enumerate(results_v3[:3]):
            print(f"    {i+1}. {r.get('title', 'N/A')} (分数: {r.get('relevance', 0):.4f})")

if __name__ == "__main__":
    # 运行测试
    print("开始测试...\n")
    
    # 测试1: 完整流程
    success1 = test_full_workflow()
    
    # 测试2: 不使用提示词拓展
    success2 = test_without_expansion()
    
    # 测试3: 对比 v2 和 v3
    compare_v2_and_v3()
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"完整流程测试: {'✅ 通过' if success1 else '❌ 失败'}")
    print(f"无提示词拓展测试: {'✅ 通过' if success2 else '❌ 失败'}")
    print("\n所有测试完成!")
