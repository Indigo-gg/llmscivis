#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试图片 API 端点
"""

import os
import base64

def test_image_read():
    """测试图片读取逻辑"""
    
    # 测试路径
    filename = "vtkjs-examples/benchmark/data/dataset/test.png"
    file_path = os.path.join('data', filename)
    
    print(f"测试文件路径: {file_path}")
    print(f"文件是否存在: {os.path.exists(file_path)}")
    
    if os.path.exists(file_path):
        # 读取图片
        with open(file_path, 'rb') as f:
            image_data = f.read()
        
        # 转换为 base64
        base64_data = base64.b64encode(image_data).decode('utf-8')
        image_url = f'data:image/png;base64,{base64_data[:50]}...'
        
        print(f"图片大小: {len(image_data)} bytes")
        print(f"Base64 长度: {len(base64_data)} chars")
        print(f"图片 URL 示例: {image_url}")
        print("✅ 图片读取成功！")
    else:
        print("❌ 文件不存在！")

if __name__ == '__main__':
    test_image_read()
