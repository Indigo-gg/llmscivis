import pandas as pd
import os
import re
import pymongo
import numpy as np
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt

# 假设 LLM_NAME 在 vector_vis.py 中也需要定义
LLM_NAME = "llm_qwen2.5_14b"

def loadExcelData(file_path):
    """
    读取Excel文件中的LLM和embedding列数据并分割
    
    Parameters:
    file_path (str): Excel文件路径
    
    Returns:
    tuple: (llm_data_list, embedding_data_list) 分别包含每行的模块列表
    """
    # 读取Excel文件中的"检索效果对比"表格
    df = pd.read_excel(file_path, sheet_name='检索效果对比')
    
    # 解析模块列表的辅助函数
    def parse_modules(text):
        if pd.notna(text):
            # 使用正则表达式按换行符分割，并过滤掉空字符串
            return [item.strip() for item in re.split(r'\n+', str(text).strip()) if item.strip()]
        return []
    
    # 提取并解析LLM列和embedding列的数据
    llm_data_list = []
    embedding_data_list = []
    
    # 遍历每一行数据
    for index, row in df.iterrows():
        # 解析LLM列数据
        llm_modules = parse_modules(row[LLM_NAME])
        llm_data_list.append(llm_modules)
        
        # 解析embedding列数据
        embedding_modules = parse_modules(row['embedding'])
        embedding_data_list.append(embedding_modules)
    
    return llm_data_list, embedding_data_list

def debug_matching_process(modules_list, file_path_to_doc, method_name):
    """
    调试匹配过程，显示详细信息
    """
    print(f"\n=== 调试 {method_name} 匹配过程 ===")
    for i, modules in enumerate(modules_list):
        print(f"第 {i+1} 行模块:")
        for module in modules:
            print(f"  模块: '{module}'")
            matched = False
            for file_name, doc in file_path_to_doc.items():
                # 多种匹配策略
                conditions = [
                    module.lower() == file_name.lower().replace('.html', ''),  # 精确匹配
                    module.lower() in file_name.lower(),  # 包含匹配
                    file_name.lower().replace('.html', '') in module.lower()   # 反向包含匹配
                ]
                
                if any(conditions):
                    print(f"    -> 匹配到文件: '{file_name}'")
                    matched = True
                    break
            
            if not matched:
                print(f"    -> 未匹配到任何文件")

def load_vector_data(llm_data_list, embedding_data_list):
    """
    从MongoDB数据库中加载向量数据，根据文件路径匹配
    
    Parameters:
    llm_data_list (list): LLM数据列表，每个元素是模块名称列表
    embedding_data_list (list): Embedding数据列表，每个元素是模块名称列表
    
    Returns:
    tuple: (llm_vectors_list, embedding_vectors_list) 分别包含每行对应的向量数据
    """
    # 连接MongoDB数据库
    client = pymongo.MongoClient('localhost', 27017)
    db = client['code_database']
    collection = db['code_snippets']
    
    # 获取所有文档以便后续查找
    all_documents = list(collection.find({}))
    print(f"MongoDB中总共有 {len(all_documents)} 个文档")
    
    # 显示所有文档的文件名
    print("\n=== MongoDB中的所有文档 ===")
    file_path_to_doc = {}
    for doc in all_documents:
        file_path = doc.get('file_path')
        if file_path:
            file_name = os.path.basename(file_path)
            file_path_to_doc[file_name] = doc
            print(f"文件: {file_name}")
            print(f"  完整路径: {file_path}")
    
    # 调试匹配过程
    debug_matching_process(llm_data_list, file_path_to_doc, "LLM")
    debug_matching_process(embedding_data_list, file_path_to_doc, "Embedding")
    
    # 根据llm_data_list中的信息获取对应的向量
    llm_vectors_list = []
    for llm_modules in llm_data_list:
        # 为每个模块列表创建一个对应的向量列表
        row_vectors = []
        for module in llm_modules:
            # 尝试通过模块名匹配文件
            matched = False
            for file_name, doc in file_path_to_doc.items():
                # 多种匹配策略
                if (module.lower() == file_name.lower().replace('.html', '') or  # 精确匹配
                    module.lower() in file_name.lower() or  # 包含匹配
                    file_name.lower().replace('.html', '') in module.lower()):  # 反向包含匹配
                    
                    embedding = doc.get('embedding')
                    if embedding:
                        row_vectors.append(np.array(embedding))
                        matched = True
                        print(f"LLM模块 '{module}' 匹配到文件 '{file_name}'")
                        break
            
            # 如果没有匹配，尝试更宽松的匹配
            if not matched:
                for file_name, doc in file_path_to_doc.items():
                    # 去除前缀后匹配
                    file_name_clean = file_name.lower().replace('.html', '').replace('vtk', '')
                    module_clean = module.lower().replace('vtk', '')
                    if file_name_clean == module_clean or file_name_clean in module_clean or module_clean in file_name_clean:
                        embedding = doc.get('embedding')
                        if embedding:
                            row_vectors.append(np.array(embedding))
                            matched = True
                            print(f"LLM模块 '{module}' 通过宽松匹配到文件 '{file_name}'")
                            break
        
        llm_vectors_list.append(row_vectors)
    
    # 根据embedding_data_list中的信息获取对应的向量
    embedding_vectors_list = []
    for emb_modules in embedding_data_list:
        # 为每个模块列表创建一个对应的向量列表
        row_vectors = []
        for module in emb_modules:
            # 尝试通过模块名匹配文件
            matched = False
            for file_name, doc in file_path_to_doc.items():
                # 多种匹配策略
                if (module.lower() == file_name.lower().replace('.html', '') or  # 精确匹配
                    module.lower() in file_name.lower() or  # 包含匹配
                    file_name.lower().replace('.html', '') in module.lower()):  # 反向包含匹配
                    
                    embedding = doc.get('embedding')
                    if embedding:
                        row_vectors.append(np.array(embedding))
                        matched = True
                        print(f"Embedding模块 '{module}' 匹配到文件 '{file_name}'")
                        break
            
            # 如果没有匹配，尝试更宽松的匹配
            if not matched:
                for file_name, doc in file_path_to_doc.items():
                    # 去除前缀后匹配
                    file_name_clean = file_name.lower().replace('.html', '').replace('vtk', '')
                    module_clean = module.lower().replace('vtk', '')
                    if file_name_clean == module_clean or file_name_clean in module_clean or module_clean in file_name_clean:
                        embedding = doc.get('embedding')
                        if embedding:
                            row_vectors.append(np.array(embedding))
                            matched = True
                            print(f"Embedding模块 '{module}' 通过宽松匹配到文件 '{file_name}'")
                            break
        
        embedding_vectors_list.append(row_vectors)
    
    return llm_vectors_list, embedding_vectors_list

def visualize_per_task(llm_vectors_list, embedding_vectors_list, task_names=None):
    """
    对每行数据（每个任务）中的模块向量进行可视化
    
    Parameters:
    llm_vectors_list: LLM向量列表，每个元素是一行中所有模块的向量
    embedding_vectors_list: Embedding向量列表，每个元素是一行中所有模块的向量
    task_names: 任务名称列表
    """
    num_rows = min(len(llm_vectors_list), len(embedding_vectors_list))
    
    for i in range(num_rows):
        task_name = f"Row {i+1}" if task_names is None else task_names[i]
        llm_vectors = llm_vectors_list[i]
        emb_vectors = embedding_vectors_list[i]
        
        print(f"处理 {task_name}:")
        print(f"  LLM模块向量数: {len(llm_vectors)}")
        print(f"  Embedding模块向量数: {len(emb_vectors)}")
        
        # 检查是否有足够的数据进行可视化
        if len(llm_vectors) == 0 and len(emb_vectors) == 0:
            print(f"  跳过 {task_name} - 没有向量数据")
            continue
            
        # 合并向量和标签
        all_vectors = []
        all_labels = []
        
        if len(llm_vectors) > 0:
            all_vectors.extend(llm_vectors)
            all_labels.extend(['LLM'] * len(llm_vectors))
            
        if len(emb_vectors) > 0:
            all_vectors.extend(emb_vectors)
            all_labels.extend(['Embedding'] * len(emb_vectors))
        
        all_vectors = np.array(all_vectors)
        
        # 调整perplexity参数
        perplexity = min(30, max(1, len(all_vectors) - 1))
        
        # 执行t-SNE降维
        tsne = TSNE(n_components=2, perplexity=perplexity, max_iter=1000, random_state=42)
        vectors_2d = tsne.fit_transform(all_vectors)
        
        # 绘制可视化结果
        plt.figure(figsize=(10, 8))
        
        # 为不同方法设置不同颜色
        colors = {'LLM': '#4575b4', 'Embedding': '#74add1'}
        unique_labels = list(set(all_labels))
        
        for label in unique_labels:
            indices = [j for j, l in enumerate(all_labels) if l == label]
            plt.scatter(vectors_2d[indices, 0], vectors_2d[indices, 1], 
                       label=label, alpha=0.7, s=100, color=colors[label])
        
        plt.title(f't-SNE Visualization for {task_name}')
        plt.xlabel('t-SNE Component 1')
        plt.ylabel('t-SNE Component 2')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()

def visualize_all_modules_combined(llm_vectors_list, embedding_vectors_list):
    """
    将所有行的所有模块向量组合在一起进行可视化
    
    Parameters:
    llm_vectors_list: LLM向量列表
    embedding_vectors_list: Embedding向量列表
    """
    # 合并所有向量
    all_llm_vectors = []
    all_emb_vectors = []
    
    for llm_vectors in llm_vectors_list:
        all_llm_vectors.extend(llm_vectors)
        
    for emb_vectors in embedding_vectors_list:
        all_emb_vectors.extend(emb_vectors)
    
    print(f"合并所有模块向量:")
    print(f"  总LLM向量数: {len(all_llm_vectors)}")
    print(f"  总Embedding向量数: {len(all_emb_vectors)}")
    
    # 检查是否有足够的数据进行可视化
    if len(all_llm_vectors) == 0 and len(all_emb_vectors) == 0:
        print("没有向量数据进行可视化")
        return
    
    # 合并向量和标签
    all_vectors = []
    all_labels = []
    
    if len(all_llm_vectors) > 0:
        all_vectors.extend(all_llm_vectors)
        all_labels.extend(['LLM'] * len(all_llm_vectors))
        
    if len(all_emb_vectors) > 0:
        all_vectors.extend(all_emb_vectors)
        all_labels.extend(['Embedding'] * len(all_emb_vectors))
    
    all_vectors = np.array(all_vectors)
    
    # 调整perplexity参数
    perplexity = min(30, max(1, len(all_vectors) - 1))
    
    # 执行t-SNE降维
    tsne = TSNE(n_components=2, perplexity=perplexity, max_iter=1000, random_state=42)
    vectors_2d = tsne.fit_transform(all_vectors)
    
    # 绘制可视化结果
    plt.figure(figsize=(12, 10))
    
    # 为不同方法设置不同颜色
    colors = {'LLM': '#4575b4', 'Embedding': '#74add1'}
    unique_labels = list(set(all_labels))
    
    for label in unique_labels:
        indices = [j for j, l in enumerate(all_labels) if l == label]
        plt.scatter(vectors_2d[indices, 0], vectors_2d[indices, 1], 
                   label=label, alpha=0.7, s=100, color=colors[label])
    
    plt.title('t-SNE Visualization of All Modules Combined')
    plt.xlabel('t-SNE Component 1')
    plt.ylabel('t-SNE Component 2')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    # Excel文件路径
    excel_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'res2.xlsx')
    
    # 加载Excel数据
    llm_data_list, embedding_data_list = loadExcelData(excel_path)
    
    # 从MongoDB加载向量数据
    llm_vectors_list, embedding_vectors_list = load_vector_data(llm_data_list, embedding_data_list)
    
    # 显示数据统计信息
    print(f"加载了 {len(llm_data_list)} 行LLM数据")
    print(f"加载了 {len(embedding_data_list)} 行Embedding数据")
    
    # 显示每行向量的数量
    for i, (llm_modules, emb_modules) in enumerate(zip(llm_data_list, embedding_data_list)):
        llm_vecs = llm_vectors_list[i]
        emb_vecs = embedding_vectors_list[i]
        print(f"第 {i+1} 行: LLM模块数={len(llm_modules)}, Embedding模块数={len(emb_modules)}, "
              f"LLM向量数={len(llm_vecs)}, Embedding向量数={len(emb_vecs)}")
    
    # 如果有匹配到向量，则进行可视化
    total_llm_vecs = sum(len(vecs) for vecs in llm_vectors_list)
    total_emb_vecs = sum(len(vecs) for vecs in embedding_vectors_list)
    
    if total_llm_vecs > 0 or total_emb_vecs > 0:
        # 构造任务名称（每4行为一个任务循环）
        tasks = ['task1', 'task2', 'task3', 'task4']
        task_names = [tasks[i % len(tasks)] for i in range(len(llm_data_list))]
        
        # 1. 分别可视化每行数据
        print("\n=== 分别可视化每行数据 ===")
        visualize_per_task(llm_vectors_list, embedding_vectors_list, task_names)
        
        # 2. 将所有模块向量组合在一起进行可视化
        print("\n=== 所有模块向量组合可视化 ===")
        visualize_all_modules_combined(llm_vectors_list, embedding_vectors_list)
    else:
        print("\n没有匹配到任何向量数据，无法进行可视化")