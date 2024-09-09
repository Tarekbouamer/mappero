#!/bin/bash

. "$(dirname "$0")/common_utils.sh"

OPENMVG_TAG="v2.1"
INSTALL_DIR="$HOME/softwares/openmvg"
OPENMVG_REPO_URL="https://github.com/openMVG/openMVG.git"

install_dependencies() {
    log_info "installing dependencies..."
    sudo apt-get update
    sudo apt-get install -y \
        git \
        cmake \
        build-essential \
        libpng-dev \
        libjpeg-dev \
        libtiff-dev \
        libxxf86vm1 \
        libxxf86vm-dev \
        libxi-dev \
        libxrandr-dev \
        libglew-dev \
        liblapack-dev \
        libcgal-dev \
        libeigen3-dev \
        libboost-iostreams-dev \
        libboost-program-options-dev \
        libboost-system-dev \
        libboost-serialization-dev \
        qtbase5-dev \
        graphviz
}

clone_and_checkout() {
    log_info "cloning openMVG repository..."
    git clone "$OPENMVG_REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR" || exit

    log_info "checking out openMVG tag: $OPENMVG_TAG"
    git checkout "$OPENMVG_TAG"

    log_info "initializing and updating submodules..."
    git submodule init
    git submodule update
}

build_and_install() {
    log_info "configuring and building openMVG..."
    mkdir -p "$INSTALL_DIR/build" && cd "$INSTALL_DIR/build" || exit
    cmake -DCMAKE_BUILD_TYPE=RELEASE ../src/ || { log_error "cmake configuration failed"; exit 1; }
    
    log_info "compiling openMVG..."
    make -j$(nproc) || { log_error "make failed"; exit 1; }

    log_info "installing openMVG..."
    sudo make install || { log_error "installation failed"; exit 1; }
}

main() {
    install_dependencies
    clone_and_checkout
    build_and_install
}

main
