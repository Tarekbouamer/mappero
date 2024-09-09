#!/bin/bash

INFO='\033[0;32m'
WARNING='\033[0;33m'
ERROR='\033[0;31m'
RESET='\033[0m'

log_info() {
    echo -e "${INFO}$1${RESET}"
}

log_warning() {
    echo -e "${WARNING}$1${RESET}"
}

log_error() {
    echo -e "${ERROR}$1${RESET}"
}

check_install_dir() {
    if [ ! -d "$1" ]; then
        log_info "creating directory $1..."
        mkdir -p "$1"
    else
        log_warning "$1 already exists, skipping installation."
        exit 0
    fi
}
