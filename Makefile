PYTHON := python3
PIP := $(PYTHON) -m pip
PROJECT_NAME := mappero

SRC_DIR := ./$(PROJECT_NAME)

.PHONY: install dev clean lint format check

install:
	$(PIP) install .

dev:
	$(PIP) install -ve .[extra]

torch:
	$(PIP) install torch==2.4.0 torchvision==0.19.0 --index-url https://download.pytorch.org/whl/cu118

clean:
	rm -rf build dist *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	$(PIP) uninstall -y $(PROJECT_NAME)

lint:
	ruff check $(SRC_DIR) --fix
	ruff format $(SRC_DIR)

format:
	ruff format $(SRC_DIR)
sort:
	ruff check $(SRC_DIR) --select I --fix