@echo off
setlocal

:: 设置AI相关参数
set "ai=doubao"					:: 请替换为你的实际模型产品
set "model=doubao-1-5-pro-32k-250115"        	:: 请替换为你的实际模型名称
set "api_key=xxxxxxxxxxxxxxxxxxxxxxxxx"  	:: 请替换为你的实际API密钥


:: 获取传入的XML文件路径
set "xml_path=%~1"

:: 检查参数是否传入
if "%xml_path%"=="" (
    echo 错误：未指定gamelist.xml路径
    exit /b 1
)

:: 检查文件是否存在
if not exist "%xml_path%" (
    echo 错误：文件 "%xml_path%" 不存在
    exit /b 1
)

:: 获取当前BAT脚本所在目录
set "bat_dir=%~dp0"

:: 构建Python脚本的完整路径
set "py_script=%bat_dir%GamelistToZh.py"

:: 调用Python脚本（使用完整路径），并传递参数
python "%py_script%" --ai "%ai%" --api_key "%api_key%" --model "%model%" --input "%xml_path%" --local_db 

endlocal