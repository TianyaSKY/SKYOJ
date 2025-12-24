FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# 安装 Python (生成脚本通常使用 Python)
RUN sed -i 's/archive.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \
    apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 设置系统语言环境为 UTF-8
ENV LANG=C.UTF-8

# 创建非 root 用户
RUN useradd -m generator
WORKDIR /home/generator

# 预先创建 app 目录并授权，生成沙箱需要写权限
RUN mkdir /app && chown generator:generator /app
USER generator
WORKDIR /app
CMD ["/bin/bash"]
