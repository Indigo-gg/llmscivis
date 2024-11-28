from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
import os

def get_embedding():
    model_name = "BAAI/bge-small-en-v1.5"
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

def process_vtk_examples(vtk_dir):
    """处理VTK示例文件夹"""
    documents = []
    
    # 文本分割器
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    
    # 遍历vtk-example目录下的所有子文件夹
    for example_dir in os.listdir(vtk_dir):
        example_path = os.path.join(vtk_dir, example_dir)
        
        # 确保是目录
        if not os.path.isdir(example_path):
            continue
            
        # 获取示例名称（文件夹名）
        example_name = os.path.basename(example_path)
        
        # 处理code.html
        code_file = os.path.join(example_path, "code.html")
        if os.path.exists(code_file):
            code_content = read_file(code_file)
            code_chunks = text_splitter.split_text(code_content)
            
            for i, chunk in enumerate(code_chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "example_name": example_name,
                        "source": f"vtk-example/{example_name}/code.html",
                        "file_type": "code",
                        "chunk_id": i,
                    }
                )
                documents.append(doc)
        
        # 处理description.txt
        desc_file = os.path.join(example_path, "description.txt")
        if os.path.exists(desc_file):
            desc_content = read_file(desc_file)
            desc_chunks = text_splitter.split_text(desc_content)
            
            for i, chunk in enumerate(desc_chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "example_name": example_name,
                        "source": f"vtk-example/{example_name}/description.txt",
                        "file_type": "description",
                        "chunk_id": i,
                    }
                )
                documents.append(doc)
        
        print(f"处理完成: {example_name}")
    
    return documents

def main():
    # 获取当前脚本的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建数据目录的路径
    vtk_dir = os.path.join(current_dir, "..", "data", "vtk-example")
    cache_dir = os.path.join(current_dir, "..", "data", "faiss_cache")
    
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