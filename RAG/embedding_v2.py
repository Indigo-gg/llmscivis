import vtk_code_meta_extract
import faiss
import numpy as np
from langchain_community.embeddings import HuggingFaceEmbeddings
import pymongo
import os
from RAG.mongodb import insert_code_snippet, find_code_snippet, update_code_snippet, delete_code_snippet

# 加载嵌入模型
model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 初始化 FAISS 向量数据库
index = faiss.IndexFlatL2(model.get_sentence_embedding_dimension())

# 连接到 MongoDB
client = pymongo.MongoClient('mongodb://localhost:27017/')
db = client['code_database']
collection = db['code_snippets']

# 定义数据目录
DATA_DIR = 'D:\\work\\llmscivis\\data\\vtkjs-examples\\prompt-sample'

# 提取 VTK.js 元数据并生成嵌入向量
def extract_vtkjs_metadata(file_path):
    """从 VTK.js HTML 文件中提取元数据."""
    meta_info = vtk_code_meta_extract.extract_vtkjs_meta(file_path)
    return meta_info

# 将描述文本转换为向量
def embed_text(text):
    """将文本转换为向量."""
    return model.encode([text])

# 存储阶段：将代码块及其元数据添加到向量数据库和代码数据库
def add_code_snippet(file_path):
    """存储阶段：将代码块及其元数据添加到向量数据库和代码数据库."""
    # 提取元数据
    meta_info = extract_vtkjs_metadata(file_path)

    # 生成唯一 ID
    snippet_id = len(collection.find_one({}, {'_id': 1})) + 1 if collection.count_documents({}) > 0 else 1

    # 向量化描述文本
    description = meta_info.get('description', '')
    vector = embed_text(description)

    # 将向量添加到 FAISS 向量数据库
    index.add_with_ids(vector, np.array([snippet_id]))

    # 将代码和元数据存入代码数据库
    insert_code_snippet(file_path, meta_info)

# 检索阶段：根据用户查询获取匹配的代码块
def search_code(query, k=3):
    """检索阶段：根据用户查询获取匹配的代码块."""
    # 向量化用户查询
    query_vector = embed_text(query)

    # 在 FAISS 中搜索相似向量
    distances, ids = index.search(query_vector, k)

    # 用匹配的 ID 去代码数据库查询完整代码块
    results = []
    for id in ids[0]:
        if id in collection.find_one({}, {'_id': 1}):
            results.append(find_code_snippet({'_id': id}))

    return results

# 从指定目录读取所有文件并添加到数据库
def load_data_from_directory(directory):
    """从指定目录读取所有文件并添加到数据库."""
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            add_code_snippet(file_path)

# 示例使用
if __name__ == '__main__':
    # 加载数据目录中的所有文件
    load_data_from_directory(DATA_DIR)

    # 进行查询
    query = 'How to visualize a 3D object?'
    results = search_code(query)

    # 输出结果
    for result in results:
        print(f'File Path: {result["file_path"]}')
        print(f'Meta Info: {result["meta_info"]}')