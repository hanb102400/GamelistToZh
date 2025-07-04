@echo off
setlocal

:: ����AI��ز���
set "ai=doubao"					:: ���滻Ϊ���ʵ��ģ�Ͳ�Ʒ
set "model=doubao-1-5-pro-32k-250115"        	:: ���滻Ϊ���ʵ��ģ������
set "api_key=xxxxxxxxxxxxxxxxxxxxxxxxx"  	:: ���滻Ϊ���ʵ��API��Կ


:: ��ȡ�����XML�ļ�·��
set "xml_path=%~1"

:: �������Ƿ���
if "%xml_path%"=="" (
    echo ����δָ��gamelist.xml·��
    exit /b 1
)

:: ����ļ��Ƿ����
if not exist "%xml_path%" (
    echo �����ļ� "%xml_path%" ������
    exit /b 1
)

:: ��ȡ��ǰBAT�ű�����Ŀ¼
set "bat_dir=%~dp0"

:: ����Python�ű�������·��
set "py_script=%bat_dir%GamelistToZh.py"

:: ����Python�ű���ʹ������·�����������ݲ���
python "%py_script%" --ai "%ai%" --api_key "%api_key%" --model "%model%" --input "%xml_path%" --local_db 

endlocal