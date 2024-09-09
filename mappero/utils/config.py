import json
from pathlib import Path

from loguru import logger
from omegaconf import OmegaConf


def save_config(config, workspace_path: Path):
    """save configuration to a json file."""
    config_json_path = workspace_path / "config.json"
    with open(config_json_path, "w") as config_file:
        json.dump(OmegaConf.to_container(config, resolve=True), config_file, indent=4)
    logger.info(f"configuration saved to {config_json_path}")
