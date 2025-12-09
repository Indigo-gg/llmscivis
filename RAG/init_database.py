# -*- coding: utf-8 -*-
"""
数据库初始化和导入脚本
从 vtkjs-examples 目录中提取代码和元信息，导入到 MongoDB
"""

import pymongo
import os
import json
import hashlib
from typing import List, Dict, Any
from pathlib import Path

# 导入元信息提取函数
from vtk_code_meta_extract import extract_vtkjs_meta, get_project_root

# --- 配置区域 ---
DB_HOST = 'localhost'
DB_PORT = 27017
DB_NAME = 'code_database'
COLLECTION_NAME = 'code_snippets'

# 数据目录
DATA_DIR = os.path.join(get_project_root(), 'data', 'vtkjs-examples', 'prompt-sample')


class MongoDBManager:
    """MongoDB 连接管理类"""
    
    def __init__(self, host=DB_HOST, port=DB_PORT, db_name=DB_NAME, collection_name=COLLECTION_NAME):
        try:
            self.client = pymongo.MongoClient(host, port, serverSelectionTimeoutMS=2000)
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]
            # 测试连接
            self.client.server_info()
            print(f"✓ MongoDB 连接成功: {host}:{port}")
            print(f"  数据库: {db_name}, 集合: {collection_name}")
        except Exception as e:
            print(f"✗ 无法连接到 MongoDB: {e}")
            self.collection = None
    
    def clear_collection(self):
        """清空集合中的所有文档"""
        if self.collection is None:
            print("✗ 无法清空集合：未连接到 MongoDB")
            return
        try:
            result = self.collection.delete_many({})
            print(f"✓ 已清空集合，删除了 {result.deleted_count} 个文档")
        except Exception as e:
            print(f"✗ 清空集合失败: {e}")
    
    def insert_many(self, documents: List[Dict[str, Any]]):
        """批量插入文档"""
        if self.collection is None:
            print("✗ 无法插入文档：未连接到 MongoDB")
            return False
        
        if not documents:
            print("⚠ 没有文档可以插入")
            return False
        
        try:
            result = self.collection.insert_many(documents)
            print(f"✓ 成功插入 {len(result.inserted_ids)} 个文档到 MongoDB")
            return True
        except pymongo.errors.BulkWriteError as e:
            print(f"✗ 批量写入错误: {e.details}")
            return False
        except Exception as e:
            print(f"✗ 插入文档失败: {e}")
            return False
    
    def count_documents(self) -> int:
        """获取集合中的文档数量"""
        if self.collection is None:
            return 0
        try:
            return self.collection.count_documents({})
        except Exception as e:
            print(f"✗ 计数失败: {e}")
            return 0


def load_code_file(file_path: str) -> str:
    """加载代码文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"  ⚠ 无法读取文件 {file_path}: {e}")
        return None


def load_data_from_directory(mongo_manager: MongoDBManager, directory: str) -> bool:
    """
    从指定目录读取所有 VTK.js 示例代码和元信息，导入到 MongoDB
    
    Args:
        mongo_manager: MongoDB 管理器实例
        directory: 数据目录路径
    
    Returns:
        bool: 导入是否成功
    """
    
    if not os.path.isdir(directory):
        print(f"✗ 错误: 目录不存在或不是有效目录: {directory}")
        return False
    
    print(f"\n开始从目录加载数据...")
    print(f"数据目录: {directory}\n")
    
    documents_to_insert = []
    processed_count = 0
    skipped_count = 0
    
    # 遍历所有子目录，查找 code.html 文件
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename == 'code.html':
                file_path = os.path.join(root, filename)
                example_name = os.path.basename(os.path.dirname(file_path))
                
                try:
                    # 1. 提取元信息
                    meta_info = extract_vtkjs_meta(file_path)
                    
                    # 2. 加载代码内容
                    code_content = load_code_file(file_path)
                    if code_content is None:
                        print(f"  ⚠ 跳过: {example_name} (无法读取代码)")
                        skipped_count += 1
                        continue
                    
                    # 3. 生成 FAISS ID (基于文件路径的哈希)
                    faiss_id = int(hashlib.sha1(file_path.encode("utf-8")).hexdigest(), 16) % (2**31 - 1)
                    if faiss_id < 0:
                        faiss_id *= -1
                    
                    # 4. 构建 MongoDB 文档
                    mongo_document = {
                        "faiss_id": faiss_id,
                        "file_path": file_path,
                        "code": code_content,
                        "meta_info": meta_info
                    }
                    
                    documents_to_insert.append(mongo_document)
                    processed_count += 1
                    
                    # 打印进度
                    if processed_count % 5 == 0:
                        print(f"  ✓ 已处理 {processed_count} 个文件...")
                    
                except Exception as e:
                    print(f"  ✗ 处理 {example_name} 时出错: {e}")
                    skipped_count += 1
    
    print(f"\n处理完成:")
    print(f"  - 成功处理: {processed_count} 个文件")
    print(f"  - 跳过: {skipped_count} 个文件")
    
    # 5. 清空集合并插入新数据
    if documents_to_insert:
        print(f"\n开始导入数据到 MongoDB...")
        mongo_manager.clear_collection()
        success = mongo_manager.insert_many(documents_to_insert)
        
        if success:
            doc_count = mongo_manager.count_documents()
            print(f"\n✓ 数据导入完成，当前集合中有 {doc_count} 个文档")
            return True
        else:
            print("\n✗ 数据导入失败")
            return False
    else:
        print("\n✗ 没有找到有效的文档可以导入")
        return False


def main():
    """主程序入口"""
    print("=" * 60)
    print("VTK.js 代码数据库初始化工具")
    print("=" * 60)
    
    # 1. 初始化 MongoDB 连接
    print("\n[步骤 1] 连接到 MongoDB...")
    mongo_manager = MongoDBManager()
    
    if mongo_manager.collection is None:
        print("\n✗ 初始化失败：无法连接到 MongoDB")
        return False
    
    # 2. 检查现有数据
    print("\n[步骤 2] 检查现有数据...")
    existing_count = mongo_manager.count_documents()
    
    if existing_count > 0:
        print(f"  当前集合中已有 {existing_count} 个文档")
        response = input("\n是否要清空现有数据并重新导入? (y/n): ").strip().lower()
        if response != 'y':
            print("取消操作")
            return False
    
    # 3. 验证数据目录
    print("\n[步骤 3] 验证数据目录...")
    if not os.path.isdir(DATA_DIR):
        print(f"✗ 数据目录不存在: {DATA_DIR}")
        print(f"  请确保存在: data/vtkjs-examples/prompt-sample 目录")
        return False
    
    print(f"✓ 数据目录有效: {DATA_DIR}")
    
    # 4. 加载数据
    print("\n[步骤 4] 加载和导入数据...")
    success = load_data_from_directory(mongo_manager, DATA_DIR)
    
    # 5. 总结
    print("\n" + "=" * 60)
    if success:
        final_count = mongo_manager.count_documents()
        print(f"✓ 初始化成功！")
        print(f"  MongoDB 集合中现在有 {final_count} 个文档")
        print("=" * 60)
        return True
    else:
        print(f"✗ 初始化失败！")
        print("=" * 60)
        return False


if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
