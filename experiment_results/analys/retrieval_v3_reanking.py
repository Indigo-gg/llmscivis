"""
Retrieval V3 重排序结果展开脚本
读取 retrieval_results_v3_output.xlsx 中的 reranked_results 列，
将数组格式的数据展开为新的 Excel 表格
"""

import pandas as pd
import json
import ast
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment


def parse_reranked_results(reranked_str):
    """
    解析 reranked_results 列的字符串，支持 JSON 和 Python literal 格式
    
    Args:
        reranked_str: reranked_results 列的字符串值
        
    Returns:
        list: 解析后的数组，失败返回 None
    """
    if pd.isna(reranked_str) or not reranked_str:
        return None
    
    try:
        # 尝试作为 JSON 解析
        if isinstance(reranked_str, str):
            return json.loads(reranked_str)
    except (json.JSONDecodeError, ValueError):
        pass
    
    try:
        # 尝试作为 Python literal 解析
        if isinstance(reranked_str, str):
            return ast.literal_eval(reranked_str)
    except (ValueError, SyntaxError):
        pass
    
    # 如果已经是 list，直接返回
    if isinstance(reranked_str, list):
        return reranked_str
    
    return None


def expand_reranked_results(input_file: str, output_file: str, sheet_name: str = "第二期实验数据"):
    """
    展开 reranked_results 列的数组数据到新的 Excel 文件，为每个 task 创建单独的工作表
    
    Args:
        input_file: 输入 Excel 文件路径
        output_file: 输出 Excel 文件路径
        sheet_name: 要读取的表格名称
    """
    print(f"📖 正在读取: {input_file}")
    print(f"   Sheet: {sheet_name}")
    
    # 读取 Excel 数据
    try:
        df = pd.read_excel(input_file, sheet_name=sheet_name)
        print(f"✓ 成功读取 {len(df)} 行数据")
    except Exception as e:
        print(f"✗ 读取失败: {e}")
        return
    
    # 检查是否存在必要的列
    if 'reranked_results' not in df.columns:
        print(f"✗ 未找到 'reranked_results' 列")
        print(f"   可用列: {df.columns.tolist()}")
        return
    
    if 'task' not in df.columns:
        print(f"✗ 未找到 'task' 列")
        print(f"   可用列: {df.columns.tolist()}")
        return
    
    print(f"\n🔄 开始按 task 展开 reranked_results 数据...")
    
    # 按 task 分组存储展开后的数据
    task_expanded_data = {}
    
    # 遍历每一行
    for idx, row in df.iterrows():
        task_name = row.get('task', 'Unknown')
        reranked_str = row.get('reranked_results')
        reranked_list = parse_reranked_results(reranked_str)
        
        if reranked_list is None or not isinstance(reranked_list, list):
            print(f"  ⚠ Task '{task_name}' (行 {idx+1}): 无法解析 reranked_results")
            continue
        
        # 初始化该 task 的数据列表
        if task_name not in task_expanded_data:
            task_expanded_data[task_name] = []
        
        # 遍历数组中的每个项目
        for item_idx, item in enumerate(reranked_list):
            if not isinstance(item, dict):
                continue
            
            # 创建展开后的行数据
            expanded_row = {
                'task': task_name,  # 保留 task 信息
                'item_index': item_idx + 1,  # 在数组中的索引
                'file_path': item.get('file_path', 'N/A'),
                'faiss_id': item.get('faiss_id', 'N/A'),
                'description': item.get('description', 'N/A'),
                'vtkjs_modules': item.get('vtkjs_modules', 'N/A'),
                'rerank_score': item.get('rerank_score', 0),
                'matched_keywords': item.get('matched_keywords', 'N/A'),
                'match_explanation': item.get('match_explanation', 'N/A'),
            }
            
            # 保留原始行的其他关键字段
            for col in ['Benchmark prompt', 'ground_truth', 'used_in_code']:
                if col in df.columns:
                    expanded_row[col] = row[col]
            
            task_expanded_data[task_name].append(expanded_row)
    
    # 统计信息
    total_records = sum(len(records) for records in task_expanded_data.values())
    print(f"✓ 展开完成，共 {len(task_expanded_data)} 个 task，{total_records} 条记录")
    
    for task_name, records in task_expanded_data.items():
        print(f"  • {task_name}: {len(records)} 条记录")
    
    if not task_expanded_data:
        print(f"✗ 没有数据可导出")
        return
    
    # 导出到 Excel，每个 task 一个工作表
    print(f"\n💾 正在导出到: {output_file}")
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # 为每个 task 创建一个工作表
            for task_name, records in task_expanded_data.items():
                # 创建 DataFrame
                df_task = pd.DataFrame(records)
                
                # 清理 task 名称作为工作表名称（Excel 工作表名称限制）
                sheet_name_clean = task_name.replace('\\', '_').replace('/', '_')
                # Excel 工作表名称最长 31 个字符
                if len(sheet_name_clean) > 31:
                    sheet_name_clean = sheet_name_clean[:28] + '...'
                
                # 写入工作表
                df_task.to_excel(writer, sheet_name=sheet_name_clean, index=False)
                
                # 获取工作表对象
                worksheet = writer.sheets[sheet_name_clean]
                
                # 设置表头样式
                header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
                header_font = Font(bold=True, color="FFFFFF")
                
                for cell in worksheet[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                
                # 调整列宽
                column_widths = {
                    'A': 35,  # task
                    'B': 12,  # item_index
                    'C': 45,  # file_path
                    'D': 12,  # faiss_id
                    'E': 50,  # description
                    'F': 40,  # vtkjs_modules
                    'G': 15,  # rerank_score
                    'H': 30,  # matched_keywords
                    'I': 60,  # match_explanation
                    'J': 30,  # Benchmark prompt
                    'K': 30,  # ground_truth
                    'L': 30,  # used_in_code
                }
                
                for col_letter, width in column_widths.items():
                    if col_letter <= chr(64 + len(df_task.columns)):
                        worksheet.column_dimensions[col_letter].width = width
        
        print(f"✓ 导出成功!")
        print(f"   工作表数量: {len(task_expanded_data)}")
        print(f"   总记录数: {total_records}")
        
    except Exception as e:
        print(f"✗ 导出失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    # 设置工作目录
    work_dir = Path(__file__).parent
    
    # 输入输出文件路径
    input_file = work_dir / "retrieval_results_v3_output.xlsx"
    output_file = work_dir / "retrieval_v3_reranked_expanded.xlsx"
    
    print("="*80)
    print("  Retrieval V3 重排序结果展开工具")
    print("="*80)
    
    # 检查输入文件是否存在
    if not input_file.exists():
        print(f"✗ 输入文件不存在: {input_file}")
        return
    
    # 执行展开操作
    expand_reranked_results(
        input_file=str(input_file),
        output_file=str(output_file),
        sheet_name="第二期实验数据"
    )
    
    print("\n" + "="*80)
    print("  处理完成!")
    print("="*80)


if __name__ == "__main__":
    main()
