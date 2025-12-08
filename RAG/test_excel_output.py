import pandas as pd
import json
import os

# 创建测试数据
test_data = {
    'splited_prompt': [
        json.dumps([
            {"description": "渲染一个球体", "weight": 8},
            {"description": "设置背景为蓝色", "weight": 3}
        ], ensure_ascii=False),
        json.dumps([
            {"description": "绘制圆锥", "weight": 7},
            {"description": "添加坐标轴", "weight": 5}
        ], ensure_ascii=False)
    ]
}

# 创建DataFrame
df = pd.DataFrame(test_data)

# 保存为Excel文件
test_excel_path = "D://Pcode//LLM4VIS//llmscivis//data//recoreds//res2_embedding4_test.xlsx"
os.makedirs(os.path.dirname(test_excel_path), exist_ok=True)

# 确保有"第二期实验数据"工作表
with pd.ExcelWriter(test_excel_path, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='第二期实验数据', index=False)

print(f"Test Excel file created at: {test_excel_path}")