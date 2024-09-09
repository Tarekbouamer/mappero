#!/bin/bash

. "$(dirname "$0")/common_utils.sh"

CMAKE_VERSION="3.30.1"
INSTALL_DIR="$HOME/softwares"
CMAKE_URL="https://github.com/Kitware/CMake/releases/download/v$CMAKE_VERSION/cmake-$CMAKE_VERSION.tar.gz"

download_and_extract() {
    if [ -d "$INSTALL_DIR/cmake-$CMAKE_VERSION" ]; then
        log_warning "$INSTALL_DIR/cmake-$CMAKE_VERSION already exists, skipping download and extraction."
        return
    fi
    log_info "Downloading and extracting CMake..."
    wget -P "$INSTALL_DIR" "$CMAKE_URL" || { log_error "Failed to download CMake"; exit 1; }
    tar -xzf "$INSTALL_DIR/cmake-$CMAKE_VERSION.tar.gz" -C "$INSTALL_DIR" || { log_error "Failed to extract CMake"; exit 1; }
    rm "$INSTALL_DIR/cmake-$CMAKE_VERSION.tar.gz"
}

build_and_install() {
    cd "$INSTALL_DIR/cmake-$CMAKE_VERSION" || { log_error "Failed to enter directory $INSTALL_DIR/cmake-$CMAKE_VERSION"; exit 1; }
    if [ ! -d "build" ]; then
        mkdir build
    fi
    cd build || { log_error "Failed to enter build directory"; exit 1; }
    ../bootstrap --prefix="$INSTALL_DIR/cmake-$CMAKE_VERSION" || { log_error "Bootstrap failed"; exit 1; }
    make -j "$(nproc)" || { log_error "Make failed"; exit 1; }
    sudo make install || { log_error "Make install failed"; exit 1; }
}

update_bashrc() {
    CMAKE_BIN_DIR="$INSTALL_DIR/cmake-$CMAKE_VERSION/bin"
    if ! grep -q "export PATH=$CMAKE_BIN_DIR:\$PATH" "$HOME/.bashrc"; then
        log_info "Adding CMake to PATH in .bashrc..."
        echo "export PATH=$CMAKE_BIN_DIR:\$PATH" >> "$HOME/.bashrc"
        log_info "CMake path added. Sourcing .bashrc to update environment..."
        source "$HOME/.bashrc" || { log_error "Failed to source .bashrc"; exit 1; }
    else
        log_warning "CMake path already exists in .bashrc, skipping."
    fi
}

main() {
    mkdir -p "$INSTALL_DIR"

    download_and_extract
    build_and_install

    update_bashrc
    
    # cmake --version
}

main
