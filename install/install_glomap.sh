#!/bin/bash

. "$(dirname "$0")/common_utils.sh"

GLOMAP_TAG="1.0.0"
INSTALL_DIR="$HOME/softwares/glomap"
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

install_glomap() {
    log_info "cloning glomap repository..."
    git clone https://github.com/colmap/glomap.git "$INSTALL_DIR"

    cd "$INSTALL_DIR" || exit

    log_info "checking out glomap tag: $GLOMAP_TAG"
    git checkout "$GLOMAP_TAG"

    log_info "building glomap..."
    if [ ! -d "build" ]; then
        mkdir build
    fi
    cd build || exit
    cmake .. -GNinja
    ninja -j "$NP" || {
        log_error "ninja build failed"
        exit 1
    }

    log_info "installing glomap..."
    sudo ninja install

    log_info "glomap installation completed at $INSTALL_DIR!"
}

main() {
    log_info "starting glomap installation script..."
    log_info "glomap git tag: $GLOMAP_TAG"
    log_info "installation directory: $INSTALL_DIR"

    install_dependencies
    check_install_dir "$INSTALL_DIR"
    install_glomap
}

main
