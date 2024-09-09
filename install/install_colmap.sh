#!/bin/bash

. "$(dirname "$0")/common_utils.sh"

INSTALL_DIR="$HOME/softwares/colmap"
COLMAP_TAG="3.9.1"
CUDA_COMPUTE_CAPABILITY="86"
NP=$(nproc)

install_dependencies() {
    log_info "installing dependencies..."
    sudo apt-get update
    sudo apt-get install -y \
        git \
        cmake \
        ninja-build \
        build-essential \
        libboost-program-options-dev \
        libboost-filesystem-dev \
        libboost-graph-dev \
        libboost-system-dev \
        libeigen3-dev \
        libflann-dev \
        libfreeimage-dev \
        libmetis-dev \
        libgoogle-glog-dev \
        libgtest-dev \
        libsqlite3-dev \
        libglew-dev \
        qtbase5-dev \
        libqt5opengl5-dev \
        libcgal-dev \
        libceres-dev
}

install_colmap() {
    log_info "cloning colmap repository..."
    git clone https://github.com/colmap/colmap.git "$INSTALL_DIR"

    cd "$INSTALL_DIR" || exit

    log_info "checking out colmap tag: $COLMAP_TAG"
    git checkout "$COLMAP_TAG"

    log_info "building colmap..."
    if [ ! -d "build" ]; then
        mkdir build
    fi
    cd build || exit
    cmake .. -GNinja -DCMAKE_CUDA_ARCHITECTURES="$CUDA_COMPUTE_CAPABILITY"
    ninja -j "$NP" || { log_error "ninja build failed"; exit 1; }

    log_info "installing colmap..."
    sudo ninja install

    log_info "colmap installation completed at $INSTALL_DIR!"
}

main() {
    log_info "starting colmap installation script..."
    log_info "colmap git tag: $COLMAP_TAG"
    log_info "installation directory: $INSTALL_DIR"
    log_info "cuda compute capability: $CUDA_COMPUTE_CAPABILITY"

    install_dependencies
    check_install_dir "$INSTALL_DIR"
    install_colmap
}

main
