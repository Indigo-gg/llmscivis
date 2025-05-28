import pandas as pd
import matplotlib.pyplot as plt

def modify_time_by_models():
# 读取 Excel 文件

    file_path = 'E://Pcode//MLLM2V//LLMSciVis-main//exports//recoreds//实验结果记录.xlsx'
    df = pd.read_excel(file_path)

    # 过滤出 workflow 为 'query-expansion' 和 'rag' 的数据
    filtered_df = df[df['workflows'] == '1,2']

    # 提取 RAG_model 和 change_lines 列
    x = filtered_df['RAG_model']
    y = filtered_df['change_lines']

    # 绘制图表
    plt.figure(figsize=(10, 6))
    plt.bar(x, y, color='skyblue')
    plt.xlabel('RAG_model')
    plt.ylabel('change_lines')
    plt.title('RAG_model vs change_lines')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # 显示图表
    plt.savefig("res.png")
def modify_time_by_workflows():
    no_workflow = 12
    query_expansion_RAG = 5
    generator = 'deepseek-v3'

    # Prepare data
    labels = ['No Workflow', 'Query Expansion + RAG']
    values = [no_workflow, query_expansion_RAG]

    # Plotting
    plt.figure(figsize=(6, 4))
    plt.bar(labels, values, color=['#4E79A7', '#F28E2B'])
    plt.ylabel('Modification Count')
    plt.title(f'Modification Count by Workflow ({generator})')
    plt.tight_layout()

    # Save the figure
    plt.savefig("res_workflow.png")

if __name__ == '__main__':

    modify_time_by_workflows()