# 基於 Python 官方映像
FROM python:3.9

# 設置工作目錄
WORKDIR /app

# 將依賴檔案拷貝到容器中
COPY requirements.txt ./

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 將 linebot_service 目錄下的所有文件拷貝到容器中的工作目錄
COPY linebot_service/ .

# 啟動 Gunicorn 並綁定容器內部端口，不對外暴露
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "test_docker_app:app"]