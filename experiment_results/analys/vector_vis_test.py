# 测试代码
import json
import numpy as np
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
import os

def load_vectors_from_json(json_file_path):
    """
    从JSON文件中加载向量数据
    """
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    vectors = []
    file_paths = []
    
    for item in data:
        vectors.append(np.array(item['embedding']))
        file_paths.append(item['file_path'])
    
    return vectors, file_paths

def visualize_vectors_tsne(vectors_list, labels_list=None, names=None, perplexity=1, n_iter=1000, random_state=42):
    """
    对多组向量进行t-SNE降维可视化
    
    参数:
    vectors_list: 向量组列表，每个元素为形状为 (n_samples, 384) 的数组
    labels_list: 标签列表，每个元素为对应的标签数组 (可选)
    names: 各组向量的名称列表
    perplexity: t-SNE的困惑度参数 (应小于样本数)
    n_iter: t-SNE迭代次数
    random_state: 随机种子
    """
    
    # 检查输入有效性
    if len(vectors_list) < 2:
        raise ValueError("至少需要两组向量进行可视化")
    
    # 合并所有向量以检查perplexity参数
    all_vectors = np.vstack(vectors_list)
    
    # 检查perplexity是否合适
    if perplexity >= len(all_vectors):
        raise ValueError(f"perplexity ({perplexity}) 必须小于样本数 ({len(all_vectors)})")
    
    # 设置默认名称
    if names is None:
        names = [f'Group {i+1}' for i in range(len(vectors_list))]
    elif len(names) != len(vectors_list):
        raise ValueError("名称数量必须与向量组数量一致")
    
    # 创建标签
    if labels_list is not None and len(labels_list) == len(vectors_list):
        # 检查是否所有标签都是数值型
        all_numeric = all(
            not isinstance(labels[0], str) 
            for labels in labels_list 
            if len(labels) > 0
        )
        
        if all_numeric:
            all_labels = np.hstack(labels_list)
        else:
            # 使用组别作为标签
            all_labels = np.hstack([
                np.full(len(vectors_list[i]), names[i]) 
                for i in range(len(vectors_list))
            ])
    else:
        # 如果没有提供标签，则使用组别作为标签
        all_labels = np.hstack([
            np.full(len(vectors_list[i]), names[i]) 
            for i in range(len(vectors_list))
        ])
    
    # 执行t-SNE降维
    tsne = TSNE(n_components=2, perplexity=perplexity, max_iter=n_iter, random_state=random_state)
    vectors_2d = tsne.fit_transform(all_vectors)
    
    # 绘制可视化结果
    plt.figure(figsize=(12, 10))
    
    # 判断是否使用颜色映射
    use_colormap = (
        labels_list is not None and 
        len(labels_list) == len(vectors_list) and
        all(len(labels) > 0 for labels in labels_list) and
        all(not isinstance(labels[0], str) for labels in labels_list if len(labels) > 0)
    )
    
    if use_colormap:
        scatter = plt.scatter(vectors_2d[:, 0], vectors_2d[:, 1], c=all_labels, cmap='viridis', alpha=0.7)
        plt.colorbar(scatter)
    else:
        # 按组别用不同颜色绘制
        start_idx = 0
        for i, vectors in enumerate(vectors_list):
            end_idx = start_idx + len(vectors)
            plt.scatter(vectors_2d[start_idx:end_idx, 0], 
                       vectors_2d[start_idx:end_idx, 1], 
                       label=names[i], alpha=0.7, s=100)
            start_idx = end_idx
        plt.legend()
    
    plt.title('t-SNE Visualization of High-dimensional Vectors')
    plt.xlabel('t-SNE Component 1')
    plt.ylabel('t-SNE Component 2')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
    
    return vectors_2d

def main():
    # JSON文件路径
    json_file_path = os.path.join(os.path.dirname(__file__), 'test.json')
    
    # 从JSON文件加载向量数据
    vectors, file_paths = load_vectors_from_json(json_file_path)
    
    print(f"成功加载 {len(vectors)} 个向量")
    for i, path in enumerate(file_paths):
        print(f"  {i+1}. {os.path.basename(path)}")
    
    # 将4个向量分成两组，每组两个向量
    group1_vectors = [vectors[0], vectors[1]]
    group2_vectors = [vectors[2], vectors[3]]
    
    group1_names = [os.path.basename(file_paths[0]), os.path.basename(file_paths[1])]
    group2_names = [os.path.basename(file_paths[2]), os.path.basename(file_paths[3])]
    
    # 进行t-SNE可视化 (调整perplexity为1)
    print("\n正在进行t-SNE降维可视化...")
    visualize_vectors_tsne(
        vectors_list=[np.array(group1_vectors), np.array(group2_vectors)],
        names=['Group 1', 'Group 2'],
        perplexity=1  # 调整为1，因为每组只有2个样本
    )
    
    # 也可以单独可视化每个组内的向量差异
    print("\n正在分别可视化各组内向量...")
    
    # 可视化第一组
    plt.figure(figsize=(10, 5))
    plt.subplot(1, 2, 1)
    tsne1 = TSNE(n_components=2, perplexity=1, max_iter=1000, random_state=42)
    group1_2d = tsne1.fit_transform(np.array(group1_vectors))
    plt.scatter(group1_2d[:, 0], group1_2d[:, 1], alpha=0.7, s=100)
    for i, name in enumerate(group1_names):
        plt.annotate(name.split('\\')[-1][:20], (group1_2d[i, 0], group1_2d[i, 1]))
    plt.title('Group 1 Vectors')
    plt.grid(True, alpha=0.3)
    
    # 可视化第二组
    plt.subplot(1, 2, 2)
    tsne2 = TSNE(n_components=2, perplexity=1, max_iter=1000, random_state=42)
    group2_2d = tsne2.fit_transform(np.array(group2_vectors))
    plt.scatter(group2_2d[:, 0], group2_2d[:, 1], alpha=0.7, s=100)
    for i, name in enumerate(group2_names):
        plt.annotate(name.split('\\')[-1][:20], (group2_2d[i, 0], group2_2d[i, 1]))
    plt.title('Group 2 Vectors')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()