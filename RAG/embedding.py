import faiss
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
# from langchain.vectorstores import FAISS
from langchain.schema import Document
import os
import sys

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.app_config import app_config
from config.ollama_config import ollama_config
from RAG.vtk_code_meta_extract import extract_vtkjs_meta

import json

def get_embedding():
    model_name = ollama_config.embedding_models['bge']
    model_kwargs = {'device': 'cpu'}
    encode_kwargs = {'normalize_embeddings': False}
    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )

def read_file(file_path):
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # 如果UTF-8解码失败，尝试其他编码
        with open(file_path, 'r', encoding='gbk') as f:
            return f.read()

def extract_code_meta(file_path):
    """提取代码元信息并保存到同目录下"""
    meta = extract_vtkjs_meta(file_path)
    # 生成元信息文件路径
    meta_file = os.path.splitext(file_path)[0] + '_meta.json'
    # 保存元信息到JSON文件
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta
def split_text_with_meta(text, meta, chunk_size=app_config.TRUNK_SIZE, chunk_overlap=app_config.TRUNK_OVERLAP):
    """按指定大小分块，并将元信息加入每块metadata"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    chunks = splitter.split_text(text)
    docs = []
    for i, chunk in enumerate(chunks):
        doc_meta = meta.copy()
        doc_meta["chunk_id"] = i
        docs.append(Document(page_content=chunk, metadata=doc_meta))
    return docs

def process_vtk_examples(vtk_dir):
    """处理VTK示例文件夹，提取元信息并分块"""
    
    documents = []
    
    for example_dir in os.listdir(vtk_dir):
        example_path = os.path.join(vtk_dir, example_dir)
        if not os.path.isdir(example_path):
            continue
        code_file = os.path.join(example_path, "code.html")
        if os.path.exists(code_file):
            # 提取并保存元信息
            meta = extract_code_meta(code_file)
            code_content = read_file(code_file)
            docs = split_text_with_meta(code_content, meta, chunk_size=3000, chunk_overlap=200)
            documents.extend(docs)
    return documents

def main():
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 确保data目录存在
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    # 确保vtk-example目录存在
    vtk_dir = os.path.join(data_dir, "vtkjs-examples","prompt-sample")
    os.makedirs(vtk_dir, exist_ok=True)
    
    # 确保faiss_cache目录存在
    cache_dir = os.path.join(project_root, "data", "faiss_cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    print(f"数据目录: {vtk_dir}")
    print("开始处理VTK示例...")
    documents = process_vtk_examples(vtk_dir)
    print(f"共处理 {len(documents)} 个文档块")
    print("初始化embedding模型...")
    embeddings = get_embedding()
    print("创建向量数据库...")
    db = FAISS.from_documents(documents, embeddings)
    print("保存向量数据库...")
    db.save_local(cache_dir)
    print("处理完成！")

if __name__ == "__main__":
    main()