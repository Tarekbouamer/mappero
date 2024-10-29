# Use NVIDIA CUDA 11.8.0 base image with Ubuntu 22.04
FROM nvidia/cuda:11.8.0-devel-ubuntu22.04 as base

# Set environment variables and versions
ENV DEBIAN_FRONTEND=noninteractive
ENV COLMAP_TAG="3.9.1"
ENV GLOMAP_TAG="1.0.0"
ENV PYCOLMAP_TAG="v0.6.0"
ENV CUDA_VERSION="11.8.0"
ENV CUDA_ARCHITECTURES="86"
ENV NP=12

# Install basic dependencies
RUN apt-get update && apt-get install -y software-properties-common wget curl git build-essential libssl-dev

# Install Python 3.10 and pip
RUN apt-get install -y python3.10 python3.10-venv python3.10-dev python3-pip

# Install Boost libraries
RUN apt-get install -y \
    libboost-program-options-dev \
    libboost-filesystem-dev \
    libboost-graph-dev \
    libboost-system-dev \
    libboost-test-dev

# Install other development libraries
RUN apt-get install -y \
    libeigen3-dev \
    libsuitesparse-dev \
    libfreeimage-dev \
    libgoogle-glog-dev \
    libgflags-dev \
    libglew-dev \
    qtbase5-dev \
    libqt5opengl5-dev \
    libcgal-dev

# Install additional libraries required for COLMAP and GLOMAP
RUN apt-get install -y \
    libatlas-base-dev \
    libsuitesparse-dev \
    libceres-dev \
    libflann-dev \
    libvtk7-dev \
    libmetis-dev \
    libopencv-dev

# Clean up apt cache
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Install CMake 3.30.1
RUN wget https://github.com/Kitware/CMake/releases/download/v3.30.1/cmake-3.30.1.tar.gz && \
    tar xfvz cmake-3.30.1.tar.gz && cd cmake-3.30.1 && \
    ./bootstrap && make -j${NP} && make install && \
    cd .. && rm -rf cmake-3.30.1 cmake-3.30.1.tar.gz

# Clone and install COLMAP
RUN git clone --branch ${COLMAP_TAG} https://github.com/colmap/colmap.git --single-branch
RUN cd colmap && mkdir build && cd build && \
    cmake .. -DCUDA_ENABLED=ON -DCMAKE_CUDA_ARCHITECTURES=${CUDA_ARCHITECTURES} && \
    make -j${NP} && make install && \
    cd ../.. && rm -rf colmap

# Clone and install GLOMAP
RUN git clone --branch ${GLOMAP_TAG} --depth 1 https://github.com/colmap/glomap.git /glomap
RUN cd /glomap && mkdir build && cd build && \
    cmake .. -DCUDA_ARCHITECTURES="${CUDA_ARCHITECTURES}" && \
    make -j${NP} && make install && cd / && rm -rf /glomap

# Clone PyCOLMAP repository
RUN git clone --depth 1 --branch ${PYCOLMAP_TAG} https://github.com/colmap/pycolmap.git
RUN cd pycolmap && \
    sed -i 's/set(CMAKE_CUDA_ARCHITECTURES .*)/set(CMAKE_CUDA_ARCHITECTURES "86")/' CMakeLists.txt && \
    cat CMakeLists.txt && \
    python3.10 -m pip install --no-cache-dir . && \

# Upgrade pip and install necessary Python dependencies
RUN python3.10 -m pip install --no-cache-dir --upgrade pip setuptools==69.5.1 pathtools

# Install PyTorch and torchvision with CUDA support
RUN CUDA_VER=$(echo "${CUDA_VERSION}" | sed 's/.$//' | tr -d '.') && \
    python3.10 -m pip install --no-cache-dir torch==2.1.2+cu${CUDA_VER} torchvision==0.16.2+cu${CUDA_VER} \
    --extra-index-url https://download.pytorch.org/whl/cu${CUDA_VER}

# Clean up apt cache again
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /mappero
COPY pyproject.toml /mappero/
COPY . /mappero/

# Install Mappero using pyproject.toml
RUN pip install --ignore-installed --no-cache-dir .