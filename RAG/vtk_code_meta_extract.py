# -*- coding: utf-8 -*-
"""
该脚本用于从VTK.js HTML代码文件中提取元信息，便于RAG检索。
提供了extract_vtkjs_meta和get_project_root函数供其他模块调用。
"""
import os
import re
import json
from bs4 import BeautifulSoup

__all__ = ['extract_vtkjs_meta', 'get_project_root']


def extract_vtkjs_meta(html_path):
    # 尝试从同文件夹下的description.txt文件中读取描述信息
    description = ''  
    example_dir = os.path.dirname(html_path)
    # 检查可能的描述文件名变体
    desc_file_variants = [
        os.path.join(example_dir, "description.txt"),
        os.path.join(example_dir, "descriptions.txt"),
        os.path.join(example_dir, "dexcription.txt"),
        os.path.join(example_dir, "descripttion.txt")
    ]
    
    for desc_file in desc_file_variants:
        if os.path.exists(desc_file):
            try:
                with open(desc_file, encoding="utf-8") as f:
                    desc_content = f.read().strip()
                    if desc_content:  # 确保内容不为空
                        description = desc_content
                    break
            except Exception as e:
                print(f"读取描述文件 {desc_file} 时出错: {e}")
    
    # 获取项目根目录
    project_root = get_project_root()
    # 计算相对路径
    rel_path = os.path.relpath(html_path, project_root)
    
    meta = {
        "file_name": os.path.basename(html_path),
        "file_path": rel_path,  # 使用相对路径而非绝对路径
        "description": description,
        "vtkjs_modules": [],
        "render_objects": [],
        "data_flow": [],
        "formula": None
    }
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script")
    code = "\n".join([s.get_text() for s in scripts])
    # 提取VTK.js模块
    modules = re.findall(r"vtk\.[\w\.]+", code)
    meta["vtkjs_modules"] = sorted(set(modules))
    # 提取渲染对象
    render_objs = re.findall(r"vtk\.(Rendering|Filters|Common)\.[\w\.]+", code)
    meta["render_objects"] = sorted(set(render_objs))
    # 解析VTK.js管线式编程的各个阶段
    pipeline_stages = {
        "data_sources": [],      # 数据源对象（Source类型）
        "filters": [],          # 过滤器对象（Filter类型）
        "mappers": [],         # 映射器对象（Mapper类型）
        "actors": [],          # 演员对象（Actor类型）
        "renderers": [],       # 渲染器对象（Renderer类型）
        "controls": [],        # 控制器对象（如InteractorStyle、RenderWindowInteractor等）
        "other_objects": []    # 其他VTK对象
    }
    
    # 1. 直接从代码中识别VTK对象创建
    # 查找形如 const xxx = vtk.Module.Class.newInstance() 的模式
    object_types = {}
    
    # 查找所有变量赋值语句
    assignments = re.findall(r'(?:const|let|var)?\s*(\w+)\s*=\s*vtk\.(\w+)\.(\w+)(?:\.(\w+))?(?:\.(\w+))?(?:\.(\w+))?\.newInstance\(([^)]*)\)', code)
    
    for match in assignments:
        parts = [p for p in match if p]
        var_name = parts[0]
        module_parts = parts[1:-1]  # 除去变量名和参数
        params = parts[-1]
        
        # 构建完整的类路径
        module_path = '.'.join(module_parts[:-1]) if len(module_parts) > 1 else module_parts[0]
        class_name = module_parts[-1] if module_parts else "Unknown"
        
        # 创建对象信息
        object_info = {
            "name": var_name,
            "class": class_name,
            "module": module_path,
            "params": params.strip() if params.strip() else None
        }
        
        # 根据类名特征分类到不同的管线阶段
        if "Source" in class_name or "Reader" in class_name:
            pipeline_stages["data_sources"].append(object_info)
        elif "Filter" in class_name or "Calculator" in class_name:
            pipeline_stages["filters"].append(object_info)
        elif "Mapper" in class_name:
            pipeline_stages["mappers"].append(object_info)
        elif "Actor" in class_name:
            pipeline_stages["actors"].append(object_info)
        elif "Renderer" in class_name or "RenderWindow" in class_name:
            pipeline_stages["renderers"].append(object_info)
        elif "Interactor" in class_name or "Camera" in class_name or "Picker" in class_name:
            pipeline_stages["controls"].append(object_info)
        else:
            pipeline_stages["other_objects"].append(object_info)
        
        # 记录对象类型，用于后续分析
        object_types[var_name] = class_name
        
    # 2. 尝试从其他模式识别VTK对象
    # 例如：直接从方法调用中推断对象类型
    method_calls = [
        (r'(\w+)\.setInputConnection', 'Filter'),
        (r'(\w+)\.getOutputPort', 'Source'),
        (r'(\w+)\.setMapper', 'Actor'),
        (r'(\w+)\.addActor', 'Renderer'),
        (r'(\w+)\.setCamera', 'Renderer'),
        (r'(\w+)\.setInteractor', 'RenderWindow')
    ]
    
    for pattern, obj_type in method_calls:
        for match in re.findall(pattern, code):
            var_name = match
            if var_name not in object_types:
                object_types[var_name] = obj_type
                
                # 根据推断的类型添加到相应的管线阶段
                object_info = {
                    "name": var_name,
                    "class": obj_type,
                    "module": "Unknown",
                    "params": None,
                    "inferred": True  # 标记为推断的对象
                }
                
                if obj_type == "Source" or "Reader" in obj_type:
                    pipeline_stages["data_sources"].append(object_info)
                elif obj_type == "Filter" or "Calculator" in obj_type:
                    pipeline_stages["filters"].append(object_info)
                elif obj_type == "Mapper":
                    pipeline_stages["mappers"].append(object_info)
                elif obj_type == "Actor":
                    pipeline_stages["actors"].append(object_info)
                elif obj_type == "Renderer" or "RenderWindow" in obj_type:
                    pipeline_stages["renderers"].append(object_info)
                elif "Interactor" in obj_type or "Camera" in obj_type:
                    pipeline_stages["controls"].append(object_info)
                else:
                    pipeline_stages["other_objects"].append(object_info)
    
    # 3. 识别管线连接关系
    pipeline_connections = []
    connection_patterns = [
        # 输入连接模式
        (r"(\w+)\.setInputConnection\(\s*(\w+)\.getOutputPort\(\)\s*\)", "data_flow"),
        # 映射器设置模式
        (r"(\w+)\.setMapper\(\s*(\w+)\s*\)", "visual_mapping"),
        # 数据源设置模式
        (r"(\w+)\.setSource\(\s*(\w+)\s*\)", "data_source"),
        # 输入数据设置模式
        (r"(\w+)\.setInputData\(\s*(\w+)\s*\)", "data_input"),
        # 添加演员到渲染器
        (r"(\w+)\.addActor\(\s*(\w+)\s*\)", "rendering"),
        # 设置属性模式
        (r"(\w+)\.set(\w+)\(([^)]*)\)", "property_setting")
    ]
    
    for pattern, conn_type in connection_patterns:
        for match in re.findall(pattern, code):
            if conn_type == "property_setting" and len(match) == 3:
                obj, prop, value = match
                # 只记录重要属性设置
                if prop in ["Color", "Position", "Opacity", "Visibility", "Resolution", "Radius"]:
                    pipeline_connections.append({
                        "type": conn_type,
                        "object": obj,
                        "property": prop,
                        "value": value.strip()
                    })
            elif len(match) == 2:
                target, source = match
                # 根据连接类型推断对象类型
                if conn_type == "visual_mapping" and source not in object_types:
                    object_types[source] = "Mapper"
                    pipeline_stages["mappers"].append({
                        "name": source,
                        "class": "Mapper",
                        "module": "Unknown",
                        "params": None,
                        "inferred": True
                    })
                elif conn_type == "data_flow" and source not in object_types:
                    object_types[source] = "Source"
                    pipeline_stages["data_sources"].append({
                        "name": source,
                        "class": "Source",
                        "module": "Unknown",
                        "params": None,
                        "inferred": True
                    })
                
                pipeline_connections.append({
                    "type": conn_type,
                    "source": source,
                    "target": target,
                    "source_type": object_types.get(source, "Unknown"),
                    "target_type": object_types.get(target, "Unknown")
                })
    
    # 4. 查找特定的VTK.js对象创建模式
    # 例如：planeSource = vtk.Filters.Sources.vtkPlaneSource.newInstance()
    specific_patterns = [
        (r"(\w+)\s*=\s*vtk\.Filters\.Sources\.vtkPlaneSource\.newInstance", "PlaneSource", "data_sources"),
        (r"(\w+)\s*=\s*vtk\.Filters\.General\.vtkCalculator\.newInstance", "Calculator", "filters"),
        (r"(\w+)\s*=\s*vtk\.Rendering\.Core\.vtkMapper\.newInstance", "Mapper", "mappers"),
        (r"(\w+)\s*=\s*vtk\.Rendering\.Core\.vtkActor\.newInstance", "Actor", "actors"),
        (r"(\w+)\s*=\s*vtk\.Rendering\.Misc\.vtkFullScreenRenderWindow\.newInstance", "RenderWindow", "renderers")
    ]
    
    for pattern, obj_type, stage in specific_patterns:
        for match in re.findall(pattern, code):
            var_name = match
            if var_name not in object_types:
                object_types[var_name] = obj_type
                pipeline_stages[stage].append({
                    "name": var_name,
                    "class": obj_type,
                    "module": "vtk",
                    "params": None,
                    "inferred": True
                })
    
    meta["pipeline"] = {
        "stages": pipeline_stages,
        "connections": pipeline_connections
    }
    # 移除旧的数据流字段
    meta.pop("data_flow", None)
    # 公式（如setFormulaSimple/Calculator等）
    formula_match = re.search(r"setFormulaSimple\([^,]+,[^,]+,[^,]+,\s*\((.*?)\)\s*=>\s*([^\)]*)\)", code, re.DOTALL)
    if formula_match:
        meta["formula"] = formula_match.group(2).strip()
    return meta


def get_project_root():
    """获取项目根目录的绝对路径"""
    # 当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 项目根目录（当前文件所在目录的上一级）
    project_root = os.path.dirname(current_dir)
    return project_root

def main():
    # 使用相对路径，基于项目根目录
    project_root = get_project_root()
    relative_path = os.path.join("data", "vtk-example", "Filter-Calculator", "code.html")
    html_path = os.path.join(project_root, relative_path)
    meta = extract_vtkjs_meta(html_path)
    out_path = html_path + ".meta.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"元信息已保存到: {out_path}")
    print(f"使用的相对路径: {relative_path}")

if __name__ == "__main__":
    main()