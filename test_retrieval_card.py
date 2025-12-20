#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 RetrievalResultsCard 前端组件的后端数据生成
"""

import json
import os
import base64

def generate_mock_retrieval_results():
    """生成模拟的检索结果，用于前端测试"""
    
    # 读取测试图片
    test_image_path = 'data/vtkjs-examples/benchmark/data/dataset/test.png'
    
    # 初始化结果列表
    results = []
    
    # 创建 3 个模拟的检索结果
    mock_data = [
        {
            "title": "Cutter",
            "description": "VTK Cutter 用于将数据集切割成任意平面，适用于体积数据和表面数据的切割操作",
            "vtkjs_modules": ["Filters/General/Cutter", "IO/Image"],
            "relevance": 0.92
        },
        {
            "title": "Volume Rendering",
            "description": "体积渲染技术用于三维科学数据的可视化，支持高质量的光线投射和色彩映射",
            "vtkjs_modules": ["Rendering/Volume", "Rendering/Core"],
            "relevance": 0.78
        },
        {
            "title": "IsosurfaceExtraction",
            "description": "提取标量数据的等值面，常用于医学影像和科学计算中的表面提取",
            "vtkjs_modules": ["Filters/Core/ContourFilter", "Rendering/OpenGL"],
            "relevance": 0.65
        }
    ]
    
    # 生成检索结果
    for idx, item in enumerate(mock_data):
        result = {
            "id": f"result_{idx}",
            "title": item["title"],
            "description": item["description"],
            "relevance": item["relevance"],
            "vtkjs_modules": item["vtkjs_modules"],
            "matched_keywords": ["VTK", "数据可视化", "3D渲染"],
            "file_path": f"data/vtkjs-examples/{idx}.html",
            "raw_score": item["relevance"] * 100,
            "thumbnail_url": "/get_image/vtkjs-examples/benchmark/data/dataset/test.png"
        }
        results.append(result)
    
    return results

def print_results(results):
    """打印结果信息"""
    print("\n" + "="*80)
    print("模拟的检索结果")
    print("="*80)
    
    for idx, result in enumerate(results, 1):
        print(f"\n【结果 {idx}】")
        print(f"  标题: {result['title']}")
        print(f"  描述: {result['description']}")
        print(f"  相关度: {result['relevance']:.0%}")
        print(f"  VTK模块: {', '.join(result['vtkjs_modules'])}")
        print(f"  匹配关键词: {', '.join(result['matched_keywords'])}")
        print(f"  缩略图URL: {result['thumbnail_url']}")
    
    print("\n" + "="*80)
    print(f"总共生成 {len(results)} 个检索结果")
    print("="*80)

def save_results_json(results, filename='mock_retrieval_results.json'):
    """保存结果到 JSON 文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 结果已保存到 {filename}")

if __name__ == '__main__':
    # 生成模拟数据
    results = generate_mock_retrieval_results()
    
    # 打印结果
    print_results(results)
    
    # 保存为 JSON
    save_results_json(results)
    
    # 验证图片访问
    test_image_path = 'data/vtkjs-examples/benchmark/data/dataset/test.png'
    if os.path.exists(test_image_path):
        with open(test_image_path, 'rb') as f:
            image_data = f.read()
        print(f"\n✅ 测试图片存在 ({len(image_data)} bytes)")
        print(f"   路径: {test_image_path}")
    else:
        print(f"\n❌ 测试图片不存在: {test_image_path}")
    
    print("\n✨ 前端可以通过以下方式访问图片:")
    print("   GET /get_image/vtkjs-examples/benchmark/data/dataset/test.png")
    print("\n📋 前端组件可以绑定以下数据:")
    print("   - result.title: 语料标题")
    print("   - result.description: 语料描述（已加粗，字体更大）")
    print("   - result.thumbnail_url: 缩略图URL")
    print("   - result.vtkjs_modules: VTK模块标签（已淡化）")
    print("   - result.relevance: 相关度分数")
