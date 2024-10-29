#!/bin/bash

# Load common utility functions
. "$(dirname "$0")/common_utils.sh"

# Variables
PYCOLMAP_REPO="https://github.com/colmap/pycolmap.git"
PYCOLMAP_TAG="v0.6.1"
INSTALL_DIR="$HOME/softwares/pycolmap_test"

# Check if colmap is installed
check_colmap_installed() {
    if ! command -v colmap &>/dev/null; then
        log_error "colmap is not installed. Please install colmap first before proceeding with pycolmap installation."
        exit 1
    fi
}

install_pycolmap() {
    log_info "Cloning pycolmap repository..."
    git clone "$PYCOLMAP_REPO" "$INSTALL_DIR"

    cd "$INSTALL_DIR" || exit 1

    log_info "Checking out pycolmap tag: $PYCOLMAP_TAG"
    git checkout "$PYCOLMAP_TAG"

    log_info "Installing pycolmap using pip..."
    python3 -m pip install . || {
        log_error "Pip installation of pycolmap failed."
        exit 1
    }

    log_info "pycolmap installation completed successfully!"
}

main() {
    log_info "Starting pycolmap installation script..."
    log_info "pycolmap git tag: $PYCOLMAP_TAG"
    log_info "Installation directory: $INSTALL_DIR"

    # check_colmap_installed
    check_install_dir "$INSTALL_DIR"
    install_pycolmap
}

main
