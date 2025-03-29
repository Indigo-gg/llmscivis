#!/bin/bash

# 检测操作系统类型
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows环境
    echo "检测到Windows系统..."
    
    # 等待前端启动
    timeout 5
    
    # 安装依赖并启动后端
    echo "正在启动后端项目..."
    pip install -r requirements.txt
    python app.py
    
    # 启动前端项目
    cd front
    echo "正在启动前端项目..."
    npm install
    npm run dev
    
    echo "前后端项目已启动完成!"
    
    # Windows下等待用户输入
    pause
    
    # Windows下结束进程
    taskkill /F /IM "node.exe" /T
    taskkill /F /IM "python.exe" /T
else
    # Linux/Unix环境
    echo "检测到Unix/Linux系统..."
    
    # 等待前端启动
    sleep 5
    
    # 安装依赖并启动后端
    echo "正在启动后端项目..."
    pip install -r requirements.txt
    python app.py &
    
    # 启动前端项目
    cd front
    echo "正在启动前端项目..."
    npm install
    npm run dev &
    
    echo "前后端项目已启动完成!"
    
    # Linux下等待用户输入
    read -p "按任意键停止服务..." 
    
    # Linux下结束进程
    pkill -f "npm run dev"
    pkill -f "python app.py"
fi

echo "服务已停止"
