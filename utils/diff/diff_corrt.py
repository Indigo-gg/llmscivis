import os
import sys
import difflib
from collections import defaultdict

def compare_files_with_stats(file1_path, file2_path, output_file):
    """
    使用 Python 内置的 difflib 库比较两个文件，并打印差异和统计数据到输出文件。
    忽略空白符和缩进差异，只关注实际的内容差异。
    """
    try:
        with open(file1_path, 'r', encoding='utf-8') as f1, \
             open(file2_path, 'r', encoding='utf-8') as f2:
            file1_lines = f1.readlines()
            file2_lines = f2.readlines()
    except FileNotFoundError:
        print(f"错误: 文件 {file1_path} 或 {file2_path} 未找到。")
        return
    except Exception as e:
        print(f"发生错误: {e}")
        return

    # 去除每行的空白符和缩进，忽略格式化差异
    file1_lines_stripped = [line.strip() for line in file1_lines]
    file2_lines_stripped = [line.strip() for line in file2_lines]
    
    # 使用 difflib.SequenceMatcher 来分析差异
    matcher = difflib.SequenceMatcher(None, file1_lines_stripped, file2_lines_stripped)
    
    added_lines = 0
    deleted_lines = 0
    changed_lines = 0
    
    # 遍历操作码来统计差异
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue
        elif tag == 'delete':
            deleted_lines += (i2 - i1)
        elif tag == 'insert':
            added_lines += (j2 - j1)
        elif tag == 'replace':
            deleted_lines += (i2 - i1)
            added_lines += (j2 - j1)
            # 只有实际内容变化的行才算修改行
            changed_lines += sum(1 for line1, line2 in zip(file1_lines[i1:i2], file2_lines[j1:j2]) if line1.strip() != line2.strip())

    # 计算总差异行数（新增行数 + 删除行数），修改行数不计入总差异
    total_differences = added_lines + deleted_lines
    
    # 使用 unified_diff 生成可读的差异输出
    diff_output = difflib.unified_diff(
        file1_lines_stripped, file2_lines_stripped,
        fromfile=file1_path, tofile=file2_path,
        lineterm='',  # 去除行尾换行符
    )

    # 写入差异输出到文件
    with open(output_file, 'a', encoding='utf-8') as out_file:
        out_file.write(f"正在比较文件：{file1_path} 和 {file2_path}\n")
        for line in diff_output:
            # 只写入实际差异的部分
            if line.startswith('+') and not line.startswith('+++'):
                out_file.write(f"{line.strip()}\n")
            elif line.startswith('-') and not line.startswith('---'):
                out_file.write(f"{line.strip()}\n")
            else:
                out_file.write(f"{line.strip()}\n")
        
        out_file.write("\n" + "=" * 50 + "\n")
        out_file.write("差异统计：\n")
        out_file.write(f"  总差异行数: {total_differences}\n")
        out_file.write(f"  新增行数: {added_lines}\n")
        out_file.write(f"  删除行数: {deleted_lines}\n")
        out_file.write(f"  修改行数: {changed_lines}\n")
        out_file.write("=" * 50 + "\n")

def find_file_pairs(folder_path):
    """
    根据命名规则查找文件对。
    """
    files = os.listdir(folder_path)
    file_map = defaultdict(list)
    
    for filename in files:
        if filename.endswith('.html'):
            base_name = filename.replace('_modified.html', '').replace('.html', '')
            file_map[base_name].append(filename)
    
    pairs = []
    for base_name, file_list in file_map.items():
        original_file = f"{base_name}.html"
        correct_file = f"{base_name}_modified.html"
        
        if original_file in file_list and correct_file in file_list:
            pairs.append((os.path.join(folder_path, original_file),
                          os.path.join(folder_path, correct_file)))
            
    return pairs

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python diff_tool.py <文件夹路径> <输出文件路径>")
        sys.exit(1)
    
    folder_to_scan = sys.argv[1]
    output_file = sys.argv[2]
    
    if not os.path.isdir(folder_to_scan):
        print(f"错误: 提供的路径不是一个有效的文件夹。")
        sys.exit(1)

    file_pairs = find_file_pairs(folder_to_scan)
    
    if not file_pairs:
        print("未在指定的文件夹中找到符合命名规则的文件对。")
    else:
        with open(output_file, 'w', encoding='utf-8') as out_file:
            out_file.write("差异比较报告\n")
            out_file.write("=" * 50 + "\n")
        
        for original, corrected in file_pairs:
            print(f"正在比较文件：{os.path.basename(original)} 和 {os.path.basename(corrected)}")
            compare_files_with_stats(original, corrected, output_file)
            
        print(f"所有比较结果已写入 {output_file}")
