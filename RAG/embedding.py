import faiss
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
# from langchain.vectorstores import FAISS
from langchain.schema import Document
import os
import sys

# Add project root directory to system path
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
    """Read file content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # If UTF-8 decoding fails, try other encodings
        with open(file_path, 'r', encoding='gbk') as f:
            return f.read()

def extract_code_meta(file_path):
    """Extract code metadata and save to the same directory"""
    meta = extract_vtkjs_meta(file_path)
    # Generate metadata file path
    meta_file = os.path.splitext(file_path)[0] + '_meta.json'
    # Save metadata to JSON file
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta
def split_text_with_meta(text, meta, chunk_size=app_config.TRUNK_SIZE, chunk_overlap=app_config.TRUNK_OVERLAP):
    """Split by specified size and add metadata to each chunk"""
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
    """Process VTK example folder, extract metadata and split into chunks"""
    
    documents = []
    
    for example_dir in os.listdir(vtk_dir):
        example_path = os.path.join(vtk_dir, example_dir)
        if not os.path.isdir(example_path):
            continue
        code_file = os.path.join(example_path, "code.html")
        if os.path.exists(code_file):
            # Extract and save metadata
            meta = extract_code_meta(code_file)
            code_content = read_file(code_file)
            docs = split_text_with_meta(code_content, meta, chunk_size=3000, chunk_overlap=200)
            documents.extend(docs)
    return documents

def main():
    # Get project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Ensure data directory exists
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Ensure vtk-example directory exists
    vtk_dir = os.path.join(data_dir, "vtkjs-examples","prompt-sample")
    os.makedirs(vtk_dir, exist_ok=True)
    
    # Ensure faiss_cache directory exists
    cache_dir = os.path.join(project_root, "data", "faiss_cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    print(f"Data directory: {vtk_dir}")
    print("Starting to process VTK examples...")
    documents = process_vtk_examples(vtk_dir)
    print(f"Processed {len(documents)} document chunks")
    print("Initializing embedding model...")
    embeddings = get_embedding()
    print("Creating vector database...")
    db = FAISS.from_documents(documents, embeddings)
    print("Saving vector database...")
    db.save_local(cache_dir)
    print("Processing completed!")

if __name__ == "__main__":
    main()