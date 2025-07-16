import os
import json

def update_meta_description(root_dir):
    """
    遍历指定根目录下的所有子目录，查找并更新 code_meta.json 文件中的 description 字段。
    如果子目录中存在 description.txt 和 code_meta.json，则将 description.txt 的内容写入
    对应的 code_meta.json 文件的 description 字段。

    Args:
        root_dir (str): 包含各个代码示例子目录的根目录。
    """
    for subdir, dirs, files in os.walk(root_dir):
        description_path = os.path.join(subdir, 'description.txt')
        meta_path = os.path.join(subdir, 'code_meta.json')

        if os.path.exists(description_path) and os.path.exists(meta_path):
            try:
                with open(description_path, 'r', encoding='utf-8') as f:
                    description_content = f.read()

                with open(meta_path, 'r+', encoding='utf-8') as f:
                    meta_data = json.load(f)
                    meta_data['description'] = description_content
                    f.seek(0)  # Rewind to the beginning of the file
                    json.dump(meta_data, f, indent=2, ensure_ascii=False)
                    f.truncate() # Truncate any remaining part of the file
                print(f"Updated description in {meta_path}")
            except Exception as e:
                print(f"Error processing {subdir}: {e}")

def update_meta_info(root_dir):
    '''
    读取code_meta.json文件中的所有字段，只保留以下字段的内容，删除其余字段
    以下是需要保留的："file_name", "file_path", "description", "vtkjs_modules"
    '''
    fields_to_keep = ["file_name", "file_path", "description", "vtkjs_modules"]
    for subdir, dirs, files in os.walk(root_dir):
        meta_path = os.path.join(subdir, 'code_meta.json')

        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r+', encoding='utf-8') as f:
                    meta_data = json.load(f)
                    updated_meta_data = {k: v for k, v in meta_data.items() if k in fields_to_keep}
                    f.seek(0)  # Rewind to the beginning of the file
                    json.dump(updated_meta_data, f, indent=2, ensure_ascii=False)
                    f.truncate()  # Truncate any remaining part of the file
                print(f"Updated meta info in {meta_path}")
            except Exception as e:
                print(f"Error processing {subdir}: {e}")

def get_all_description(root_dir):
    """
    遍历指定根目录下的所有子目录，查找并返回所有 code_meta.json 文件中的 description 字段。

    Args:
        root_dir (str): 包含各个代码示例子目录的根目录。

    Returns:
        list: 包含所有 code_meta.json 文件中的 description 字段的列表 txt格式，换行分割(包含一级文件夹名称和描述内容)。
    """
    all_descriptions = []
    for subdir, dirs, files in os.walk(root_dir):
        meta_path = os.path.join(subdir, 'code_meta.json')
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta_data = json.load(f)
                    description = meta_data.get('description')
                    if description:
                        # 提取一级文件夹名称
                        relative_path = os.path.relpath(subdir, root_dir)
                        first_level_folder = relative_path.split(os.sep)[0]
                        all_descriptions.append(f"{first_level_folder}\n{description}")
            except Exception as e:
                print(f"Error reading {meta_path}: {e}")
    return all_descriptions


if __name__ == '__main__':
    # 示例用法：假设你的所有代码示例都在这个目录下
    # 请根据你的实际项目结构调整此路径
    # 例如：d:\Pcode\LLM4VIS\llmscivis\data\vtkjs-examples\prompt-sample
    base_sample_dir = r'd:\Pcode\LLM4VIS\llmscivis\data\vtkjs-examples\prompt-sample'
    # update_meta_description(base_sample_dir) # 确保这个函数被调用以更新description

    # 调用 update_meta_info 函数
    # update_meta_info(base_sample_dir)

    # # 调用 get_all_description 并打印结果
    # descriptions = get_all_description(base_sample_dir)
    # for desc in descriptions:
    #     print(desc)
    #     print("\n" + "-"*50 + "\n") # 分隔符