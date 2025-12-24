FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# 安装编译器和解释器
RUN sed -i 's/archive.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \
    apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    openjdk-17-jdk \
    python3 \
    python3-pip \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 设置系统语言环境为 UTF-8
ENV LANG=C.UTF-8

# 复制并安装 Python 依赖
# 注意：在构建时，需要将 context 设置在 backend/sandbox 目录，或者将 requirements.txt 复制到 runners 目录下
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r /tmp/requirements.txt

# 创建非 root 用户以提高安全性
RUN useradd -m judge
WORKDIR /home/judge

# 预先创建 app 目录并授权
RUN mkdir /app && chown judge:judge /app
USER judge
WORKDIR /app
CMD ["/bin/bash"]
