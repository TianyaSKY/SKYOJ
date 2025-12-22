FROM python:3.10-slim

# 设置中文字符集支持（可选，防止日志乱码）
ENV LANG C.UTF-8

# 安装系统依赖：C/C++ 编译器、Java 运行环境以及基础工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    default-jdk \
    timeout \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 默认保持运行（会被 judge_service 的指令覆盖）
CMD ["sleep", "3600"]