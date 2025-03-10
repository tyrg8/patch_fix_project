# docker build -t my_base_image .

FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    cmake \
    gmp-ecm \
    autoconf \
    automake \
    libtool-bin \
    pkg-config \
    make \
    gcc \
    g++ \
    build-essential \
    ninja-build \
    software-properties-common \
    wget \
    meson \
    && apt-get clean
    RUN add-apt-repository ppa:deadsnakes/ppa

# 更新源并安装 Python 3.8
RUN apt-get update && apt-get install -y \
    python3.8 \
    python3.8-dev \
    python3.8-venv \
    python3-pip \
    && apt-get clean

# 设置默认 Python 版本为 3.8
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1

# 验证 Python 版本
RUN python3 --version


WORKDIR /project