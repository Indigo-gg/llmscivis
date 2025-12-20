#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
替换 experiment_results\generated_code_without_rag 下所有 case_export_data.json 文件的 retrieval_results 字段

用途：用真实的检索结果替换生成代码中的检索结果数据，并加入检索耗时和 title 字段
"""

import json
import os
from pathlib import Path


# 从 retrieval_results_v3_output.xlsx 加载检索结果和耗时数据
def load_retrieval_data_from_excel():
    """
    从 retrieval_results_v3_output.xlsx 加载检索结果和耗时数据
    返回格式: (reranked_results, retrieval_times, task_names)
    reranked_results: {task_name: [doc1, doc2, ...]} - 按 task 名字分类的检索结果
    retrieval_times: {task_name: elapsed_time}
    task_names: 从 Excel 读取的实际 task 名字列表（用于匹配 case）
    """
    import pandas as pd
    
    try:
        excel_path = 'experiment_results/retrieval_results_v3_output.xlsx'
        df = pd.read_excel(excel_path, sheet_name='第二期实验数据')
        
        reranked_results = {}  # 改为字典，按 task 名字索引
        retrieval_times = {}
        task_names = []  # 记录读取到的 task 名字
        
        # 从 Excel 的 reranked_results 列提取每行的数据
        for idx, row in df.iterrows():
            if idx >= 4:  # 只处理前4行（对应4个case）
                break
            
            task_name = str(row.get('task', '')).strip().lower()
            reranked_str = row.get('reranked_results', '')
            retrieval_time = row.get('retrieval_time', 0.0)
            
            if not task_name:
                print(f"警告：第 {idx} 行没有 task 名字")
                continue
            
            try:
                # 解析 JSON 字符串
                if isinstance(reranked_str, str) and reranked_str.strip():
                    reranked_list = json.loads(reranked_str)
                    # 为每条结果添加 title 字段
                    for item in reranked_list:
                        if 'title' not in item:
                            item['title'] = extract_title_from_path(item.get('file_path', ''))
                else:
                    reranked_list = []
                
                reranked_results[task_name] = reranked_list
                task_names.append(task_name)
                
                # 记录检索时间
                retrieval_times[task_name] = float(retrieval_time) if retrieval_time else 0.0
            
            except json.JSONDecodeError as e:
                print(f"警告：第 {idx} 行 (task={task_name}) JSON 解析失败 - {e}")
                reranked_results[task_name] = []
                task_names.append(task_name)
        
        print(f"✓ 从 Excel 加载了 {len(reranked_results)} 个 case 的检索结果")
        print(f"✓ 检测到的 task 名字: {task_names}")
        print(f"✓ 从 Excel 加载了 {len(retrieval_times)} 个 case 的检索耗时")
        
        return reranked_results, retrieval_times, task_names
    
    except Exception as e:
        print(f"错误：无法从 Excel 加载数据 - {e}")
        import traceback
        traceback.print_exc()
        return {}, {}, []


def extract_title_from_path(file_path):
    """
    从文件路径提取模块标题
    例如: "data\\vtkjs-examples\\prompt-sample\\Filter-ImageLabelOutline\\code.html" -> "Filter-ImageLabelOutline"
    """
    try:
        parts = file_path.replace('\\', '/').split('/')
        for part in parts:
            if part.startswith('Filter-') or part.startswith('Rendering-') or part.startswith('IO-'):
                return part
    except:
        pass
    return "Unknown"


# 全局数据：从 Excel 加载检索结果和耗时数据
reranked_results, retrieval_times, detected_task_names = load_retrieval_data_from_excel()

# 如果 reranked_results 为空，使用备用数据（防止加载失败）
if not reranked_results:
    print("\n警告：从 Excel 加载数据失败，使用备用数据")
    reranked_results = {}
    detected_task_names = []



def replace_retrieval_results():
    """
    替换 experiment_results\\generated_code_without_rag 目录下所有 case_export_data.json 文件中的 retrieval_results 字段
    并添加 title 字段和检索耗时信息
    """
    base_path = Path('experiment_results/generated_code_without_rag')
    
    if not base_path.exists():
        print(f"错误：目录不存在 {base_path}")
        return False
    
    # 遍历所有模型目录
    model_dirs = sorted([d for d in base_path.iterdir() if d.is_dir()])
    print(f"找到 {len(model_dirs)} 个模型目录")
    print("=" * 60)
    
    total_files = 0
    updated_files = 0
    
    for model_dir in model_dirs:
        model_name = model_dir.name
        print(f"\n处理模型: {model_name}")
        
        # 遍历每个 case 目录
        case_dirs = sorted([d for d in model_dir.iterdir() if d.is_dir()])
        print(f"  找到 {len(case_dirs)} 个 case")
        
        for case_dir in case_dirs:
            case_name = case_dir.name
            json_file = case_dir / 'case_export_data.json'
            
            if not json_file.exists():
                print(f"    警告：{case_name} 中没有找到 case_export_data.json")
                continue
            
            total_files += 1
            
            try:
                # 读取 JSON 文件
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 检查是否有 retrieval_results 字段
                if 'retrieval_results' not in data:
                    print(f"    警告：{case_name} 中没有 retrieval_results 字段")
                    continue
                
                # 根据 case 名称获取对应的任务类型
                task_key = get_task_key_from_case_name(case_name)
                if task_key is None:
                    print(f"    警告：无法确定 {case_name} 的任务类型")
                    continue
                
                if task_key not in reranked_results:
                    print(f"    警告：reranked_results 中没有 '{task_key}' 的数据")
                    continue
                
                # 替换 retrieval_results 字段
                old_count = len(data.get('retrieval_results', []))
                new_results = reranked_results[task_key]
                
                # 为每条结果添加 title 字段（如果不存在）
                for result in new_results:
                    if 'title' not in result:
                        result['title'] = extract_title_from_path(result.get('file_path', ''))
                
                data['retrieval_results'] = new_results
                new_count = len(new_results)
                
                # 添加检索耗时信息到 metadata（如果存在）
                if 'metadata' not in data:
                    data['metadata'] = {}
                
                if task_key in retrieval_times:
                    data['metadata']['keyword_aware_retrieval_time'] = retrieval_times[task_key]
                    data['metadata']['retrieval_time_seconds'] = round(retrieval_times[task_key], 2)
                
                # 写回 JSON 文件
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                updated_files += 1
                retrieval_time_str = f" (耗时: {data['metadata'].get('retrieval_time_seconds', 0)}s)" if 'metadata' in data and 'retrieval_time_seconds' in data['metadata'] else ""
                print(f"    ✓ {case_name}: 已更新 {old_count} -> {new_count} 条结果{retrieval_time_str}")
            
            except json.JSONDecodeError as e:
                print(f"    错误：{case_name} JSON 解析失败 - {e}")
            except Exception as e:
                print(f"    错误：{case_name} 处理失败 - {e}")
    
    print(f"\n" + "=" * 60)
    print(f"处理完成")
    print(f"总文件数: {total_files}")
    print(f"已更新: {updated_files}")
    if total_files > 0:
        success_rate = 100 * updated_files / total_files
        print(f"成功率: {updated_files}/{total_files} ({success_rate:.1f}%)")
    
    return updated_files > 0


def get_task_key_from_case_name(case_name):
    """
    根据 case 名称获取对应的任务 key（与 Excel 中 task 列的值匹配）
    首先尝试从 detected_task_names 中精确匹配，然后使用 fallback 映射
    """
    case_lower = case_name.lower()
    
    # 首先尝试从检测到的 task 名字中匹配
    for task_name in detected_task_names:
        if task_name in case_lower or case_lower in task_name:
            return task_name
    
    # Fallback: 使用硬编码的映射关系
    if 'isosurface' in case_lower:
        return 'isosurface'
    elif 'slice' in case_lower or 'cutter' in case_lower:
        return 'slice'
    elif 'streamline' in case_lower or 'stream' in case_lower:
        return 'streamline'
    elif 'volume' in case_lower or 'volume_rendering' in case_lower:
        return 'volume_rendering'
    
    return None





def print_retrieval_time_summary():
    """
    打印检索耗时总结
    """
    if not retrieval_times:
        return
    
    print("\n" + "=" * 60)
    print("检索耗时总结（关键词感知检索）")
    print("=" * 60)
    
    total_time = 0
    for case_type, elapsed_time in sorted(retrieval_times.items()):
        print(f"{case_type:20s}: {elapsed_time:8.4f}s")
        total_time += elapsed_time
    
    print("-" * 60)
    print(f"{'总耗时':20s}: {total_time:8.4f}s")
    print(f"{'平均耗时':20s}: {total_time / len(retrieval_times) if retrieval_times else 0:8.4f}s")
    print("=" * 60)


if __name__ == '__main__':
    success = replace_retrieval_results()
    print_retrieval_time_summary()
    exit(0 if success else 1)
