FROM python:3.10-slim

WORKDIR /app

# 复制项目文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 设置环境变量
ENV RUN_ENV=docker
ENV CI=true
ENV PYTHONUNBUFFERED=1

# 默认命令
CMD ["python", "run_tests.py"]