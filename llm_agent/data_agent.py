import re
import json
import requests
import pyvista as pv
import numpy as np
from typing import Dict, List, Any, Tuple
import tempfile
import os


class VTKDataAnalyzer:
    """VTK数据分析工具
    
    功能:
    1. 从提示词字符串中提取URL地址
    2. 下载并分析VTK数据文件
    3. 返回结构化的分析结果，包含推荐的前端模块
    """
    
    # VTK数据类型对应的前端VTK.js读取器模块推荐
    VTKJS_MODULE_RECOMMENDATIONS = {
        'PolyData': {
            'modules': ['vtkPolyDataMapper', 'vtkActor', 'vtkRenderer'],
            'description': '多边形数据，适合网格、点云、表面数据',
            'common_use_cases': ['网格渲染', '点云显示', '表面可视化'],
            'rendering_techniques': ['Surface Rendering', 'Wireframe']
        },
        'UnstructuredGrid': {
            'modules': ['vtkUnstructuredGridMapper', 'vtkActor', 'vtkRenderer', 'vtkVolume', 'vtkVolumeMapper'],
            'description': '非结构化网格，适合体数据和复杂几何',
            'common_use_cases': ['体数据渲染', '等值面提取', '流线追踪'],
            'rendering_techniques': ['Volume Rendering', 'Isosurface', 'Streamlines']
        },
        'StructuredGrid': {
            'modules': ['vtkStructuredGridMapper', 'vtkActor', 'vtkRenderer'],
            'description': '结构化网格，适合规则网格数据',
            'common_use_cases': ['规则网格渲染', '切片显示'],
            'rendering_techniques': ['Surface Rendering', 'Slicing']
        },
        'RectilinearGrid': {
            'modules': ['vtkRectilinearGridMapper', 'vtkActor', 'vtkRenderer'],
            'description': '直线性网格，轴对齐的规则网格',
            'common_use_cases': ['直线网格渲染', '等值面提取'],
            'rendering_techniques': ['Isosurface', 'Surface Rendering']
        },
        'ImageData': {
            'modules': ['vtkImageDataMapper', 'vtkVolume', 'vtkVolumeMapper', 'vtkVolumeProperty'],
            'description': '图像数据/体素数据，适合体数据',
            'common_use_cases': ['体渲染', '医学影像', '科学计算'],
            'rendering_techniques': ['Volume Rendering', 'Texture Slicing']
        },
        'MultiBlock': {
            'modules': ['vtkCompositePolyDataMapper', 'vtkActor', 'vtkRenderer'],
            'description': '多块数据集，适合复杂场景',
            'common_use_cases': ['多部件渲染', '装配体显示'],
            'rendering_techniques': ['Multi-block Rendering']
        }
    }
    
    @staticmethod
    def extract_urls_from_prompt(prompt_text: str) -> List[str]:
        """从提示词字符串中提取所有URL地址
        
        Args:
            prompt_text: 提示词字符串
            
        Returns:
            URL列表
        """
        # 匹配http/https URL
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]*'
        urls = re.findall(url_pattern, prompt_text)
        return urls
    
    @staticmethod
    def download_file(url: str, timeout: int = 30) -> Tuple[bytes, str]:
        """下载文件
        
        Args:
            url: 文件URL
            timeout: 超时时间（秒）
            
        Returns:
            (文件内容, 文件扩展名)
        """
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            
            # 从URL或Content-Disposition获取文件扩展名
            filename = url.split('/')[-1].split('?')[0]
            if '.' not in filename:
                content_type = response.headers.get('content-type', '')
                ext_map = {
                    'xml': '.xml',
                    'vtp': '.vtp',
                    'vtu': '.vtu',
                    'vtk': '.vtk',
                    'vts': '.vts',
                    'vtr': '.vtr'
                }
                ext = next((ext for key, ext in ext_map.items() if key in content_type), '.vtu')
                filename = f'data{ext}'
            
            return response.content, filename
        except Exception as e:
            raise Exception(f"下载文件失败: {str(e)}")
    
    @staticmethod
    def analyze_vtk_file(file_path: str) -> Dict[str, Any]:
        """分析VTK文件并提取关键信息
        
        Args:
            file_path: VTK文件路径
            
        Returns:
            分析结果字典
        """
        try:
            mesh = pv.read(file_path)
        except Exception as e:
            raise Exception(f"读取VTK文件失败: {str(e)}")
        
        # 获取数据类型
        data_type = type(mesh).__name__
        
        # 基础几何信息
        bounds = mesh.bounds
        geometry_info = {
            'data_type': data_type,
            'points_count': mesh.n_points,
            'cells_count': mesh.n_cells,
            'bounds': {
                'x': [float(bounds[0]), float(bounds[1])],
                'y': [float(bounds[2]), float(bounds[3])],
                'z': [float(bounds[4]), float(bounds[5])]
            }
        }
        
        # 全局字段数据
        field_data_info = {}
        if mesh.field_data:
            for name, data in mesh.field_data.items():
                if isinstance(data, np.ndarray):
                    val = data[0] if len(data) > 0 else None
                else:
                    val = data
                field_data_info[name] = {
                    'value': float(val) if isinstance(val, (int, float, np.number)) else str(val),
                    'type': str(type(val).__name__)
                }
        
        # 点数据
        point_data_info = {}
        if mesh.point_data:
            for name, array in mesh.point_data.items():
                dim = array.shape[1] if len(array.shape) > 1 else 1
                min_val = float(np.min(array))
                max_val = float(np.max(array))
                
                info = {
                    'dimensions': int(dim),
                    'data_type': str(array.dtype),
                    'range': {
                        'min': min_val,
                        'max': max_val
                    }
                }
                
                # 如果是向量，计算模长
                if dim == 3:
                    magnitude = np.linalg.norm(array, axis=1)
                    info['magnitude_range'] = {
                        'min': float(np.min(magnitude)),
                        'max': float(np.max(magnitude))
                    }
                
                point_data_info[name] = info
        
        # 单元数据
        cell_data_info = {}
        if mesh.cell_data:
            for name, array in mesh.cell_data.items():
                cell_data_info[name] = {
                    'data_type': str(array.dtype),
                    'range': {
                        'min': float(np.min(array)),
                        'max': float(np.max(array))
                    }
                }
        
        return {
            'geometry': geometry_info,
            'field_data': field_data_info,
            'point_data': point_data_info,
            'cell_data': cell_data_info
        }
    
    @classmethod
    def get_module_recommendations(cls, data_type: str) -> Dict[str, Any]:
        """根据数据类型获取前端VTK.js模块推荐
        
        Args:
            data_type: VTK数据类型
            
        Returns:
            推荐的模块和配置
        """
        # 如果没有精确匹配，尝试模糊匹配
        if data_type in cls.VTKJS_MODULE_RECOMMENDATIONS:
            recommendation = cls.VTKJS_MODULE_RECOMMENDATIONS[data_type].copy()
        else:
            # 默认推荐
            recommendation = cls.VTKJS_MODULE_RECOMMENDATIONS['PolyData'].copy()
        
        recommendation['data_type'] = data_type
        return recommendation
    
    @classmethod
    def analyze_from_prompt(cls, prompt_text: str, download: bool = True) -> Dict[str, Any]:
        """从提示词字符串中提取URL并分析VTK数据
        
        Args:
            prompt_text: 提示词字符串
            download: 是否下载文件进行分析
            
        Returns:
            完整的分析结果
        """
        result = {
            'urls_extracted': [],
            'analyses': []
        }
        
        # 提取URLs
        urls = cls.extract_urls_from_prompt(prompt_text)
        result['urls_extracted'] = urls
        
        if not urls:
            return result
        
        # 分析每个URL对应的VTK文件
        for url in urls:
            analysis_item = {
                'url': url,
                'status': 'success',
                'error': None,
                'analysis': None,
                'module_recommendation': None
            }
            
            try:
                if download:
                    # 下载文件
                    file_content, filename = cls.download_file(url)
                    
                    # 保存到临时文件
                    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as tmp:
                        tmp.write(file_content)
                        tmp_path = tmp.name
                    
                    try:
                        # 分析VTK文件
                        analysis = cls.analyze_vtk_file(tmp_path)
                        analysis_item['analysis'] = analysis
                        
                        # 获取模块推荐
                        data_type = analysis['geometry']['data_type']
                        recommendation = cls.get_module_recommendations(data_type)
                        analysis_item['module_recommendation'] = recommendation
                    finally:
                        # 清理临时文件
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
            except Exception as e:
                analysis_item['status'] = 'failed'
                analysis_item['error'] = str(e)
            
            result['analyses'].append(analysis_item)
        
        return result


def format_analysis_output(analysis_result: Dict[str, Any]) -> str:
    """格式化分析结果为可读的文本
    
    Args:
        analysis_result: 分析结果字典
        
    Returns:
        格式化的文本
    """
    output = []
    output.append("="*60)
    output.append("VTK数据分析结果")
    output.append("="*60)
    
    # 输出提取的URLs
    output.append(f"\n[1] 提取的URL列表 ({len(analysis_result['urls_extracted'])} 个):")
    for i, url in enumerate(analysis_result['urls_extracted'], 1):
        output.append(f"    {i}. {url}")
    
    # 输出分析结果
    for idx, item in enumerate(analysis_result['analyses'], 1):
        output.append(f"\n[2.{idx}] URL分析结果: {item['url']}")
        output.append(f"    状态: {item['status']}")
        
        if item['status'] == 'failed':
            output.append(f"    错误: {item['error']}")
            continue
        
        analysis = item['analysis']
        if analysis:
            # 几何信息
            geom = analysis['geometry']
            output.append(f"\n    [几何信息]")
            output.append(f"    - 数据类型: {geom['data_type']}")
            output.append(f"    - 点数: {geom['points_count']}")
            output.append(f"    - 单元数: {geom['cells_count']}")
            output.append(f"    - 空间范围 (Bounding Box):")
            output.append(f"      X: [{geom['bounds']['x'][0]:.4f}, {geom['bounds']['x'][1]:.4f}]")
            output.append(f"      Y: [{geom['bounds']['y'][0]:.4f}, {geom['bounds']['y'][1]:.4f}]")
            output.append(f"      Z: [{geom['bounds']['z'][0]:.4f}, {geom['bounds']['z'][1]:.4f}]")
            
            # 点数据
            if analysis['point_data']:
                output.append(f"\n    [点数据 (Point Data)]")
                for name, info in analysis['point_data'].items():
                    output.append(f"    - {name}:")
                    output.append(f"      维度: {info['dimensions']}")
                    output.append(f"      范围: [{info['range']['min']:.6f}, {info['range']['max']:.6f}]")
                    if 'magnitude_range' in info:
                        output.append(f"      向量模长范围: [{info['magnitude_range']['min']:.6f}, {info['magnitude_range']['max']:.6f}]")
            
            # 单元数据
            if analysis['cell_data']:
                output.append(f"\n    [单元数据 (Cell Data)]")
                for name, info in analysis['cell_data'].items():
                    output.append(f"    - {name}: [{info['range']['min']:.6f}, {info['range']['max']:.6f}]")
            
            # 模块推荐
            if item['module_recommendation']:
                rec = item['module_recommendation']
                output.append(f"\n    [前端VTK.js模块推荐]")
                output.append(f"    - 数据类型: {rec['data_type']}")
                output.append(f"    - 描述: {rec['description']}")
                output.append(f"    - 推荐模块: {', '.join(rec['modules'])}")
                output.append(f"    - 常见应用: {', '.join(rec['common_use_cases'])}")
                output.append(f"    - 渲染技术: {', '.join(rec['rendering_techniques'])}")
    
    output.append("\n" + "="*60)
    return "\n".join(output)


if __name__ == "__main__":
    # 示例使用
    example_prompt = """
    请分析这个VTK数据文件: http://127.0.0.1:5000/dataset/rotor.vti
    然后生成相应的可视化代码。
    """
    
    analyzer = VTKDataAnalyzer()
    result = analyzer.analyze_from_prompt(example_prompt, download=False)
    print(json.dumps(result, indent=2, ensure_ascii=False))
