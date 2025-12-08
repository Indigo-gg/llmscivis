@echo off
REM 跨平台 LLM4VIS 项目启动脚本 (Windows 版本)

REM 设置标题
title LLM4VIS 项目启动脚本

echo ========================================
echo LLM4VIS 项目启动脚本 (Windows)
echo ========================================
echo.

REM 创建必要的目录
echo 正在创建必要的目录...
mkdir data\db 2>nul
echo.

REM 检查MongoDB是否已经在运行
echo 检查MongoDB是否已经在运行...
netstat -an | findstr ":27017" >nul
if %errorlevel% == 0 (
    echo MongoDB 已在运行，跳过启动
) else (
    REM 启动 MongoDB 服务 (在新终端窗口中)
    echo 正在启动 MongoDB 服务...
    start "MongoDB Service" cmd /k "mongod --dbpath=data/db --port 27017 || echo MongoDB 启动失败 && pause"
    
    REM 等待 MongoDB 启动
    echo 等待 MongoDB 启动...
    timeout /t 10 /nobreak >nul
)

REM 启动 dataset server（如果存在）(在新终端窗口中)
if exist "data\vtkjs-examples\benchmark\data\dataset_server.py" (
    echo 正在启动 Dataset Server...
    start "Dataset Server" cmd /k "python data/vtkjs-examples/benchmark/data/dataset_server.py || echo Dataset Server 启动失败 && pause"
    timeout /t 5 /nobreak >nul
) else (
    echo 注意: 未找到 dataset_server.py 文件，跳过启动
)

REM 安装 Python 依赖
echo.
echo 正在安装 Python 依赖...
pip install -r requirements.txt

REM 启动 Python Flask 应用 (在新终端窗口中)
echo.
echo 正在启动 Python Flask 应用...
start "Flask App" cmd /k "python app.py || echo Flask 应用启动失败 && pause"

REM 等待 Flask 应用启动
echo 等待 Flask 应用启动...
timeout /t 10 /nobreak >nul

REM 安装前端依赖并启动开发服务器 (在新终端窗口中)
echo.
echo 正在安装前端依赖并启动开发服务器...
cd front
if not exist node_modules (
    echo 正在安装前端依赖...
    call npm install
)
start "Frontend Dev Server" cmd /k "npm run dev || echo 前端服务启动失败 && pause"
cd ..

echo.
echo 所有服务已在独立终端窗口中启动！
echo 请查看各个终端窗口的状态
echo.
echo 主要访问地址:
echo - 应用界面: http://localhost:5173
echo - 后端API: http://localhost:5001
echo.
echo 按任意键关闭此窗口（注意：这不会停止其他服务）...
pause >nul