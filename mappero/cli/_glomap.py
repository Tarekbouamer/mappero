import shutil
from pathlib import Path
from typing import Optional

import click
from loguru import logger
from omegaconf import DictConfig, OmegaConf

from mappero.modules.colmap import feature_extraction, mapper, matcher
from mappero.modules.glomap import glomap_mapper
from mappero.utils.config import save_config


@click.command()
@click.argument("workspace_path", type=click.Path(exists=True))
@click.option(
    "--config_path",
    default="mappero/config/glomap.yaml",
    help="Path to the configuration file.",
)
@click.option("--image_path", type=click.Path(), help="Path to the image directory.")
@click.option(
    "--colmap_path",
    type=click.Path(),
    default=None,
    help="Path to the COLMAP directory.",
)
@click.help_option("--help", "-h")
def glomap_cli(
    workspace_path: str,
    config_path: str,
    image_path: Optional[str],
    colmap_path: Optional[str],
) -> None:
    """Glomap pipeline wrapper."""
    logger.info("Initializing Glomap pipeline")

    # Workspace
    workspace_path = Path(workspace_path)

    # Image path
    image_path = Path(image_path) if image_path else workspace_path / "images"
    if not image_path.exists():
        logger.error(f"Image path does not exist: {image_path}")
        return

    # Glomap paths
    glomap_path = workspace_path / "glomap"
    glomap_path.mkdir(exist_ok=True, parents=True)

    # Load and save config
    config: DictConfig = OmegaConf.load(config_path)
    save_config(config, glomap_path)

    # COLMAP paths
    colmap_path = Path(colmap_path) if colmap_path else workspace_path / "colmap"
    colmap_database_path = colmap_path / "database.db"

    # Initialize sparse reconstruction
    if colmap_path.exists():
        logger.info(f"Skipping mapping as COLMAP path already exists: {colmap_path}")
    else:
        colmap_path.mkdir(parents=True, exist_ok=True)

        # Sparse path
        sparse_path = colmap_path / "sparse"
        sparse_path.mkdir(exist_ok=True, parents=True)

        # Run COLMAP pipeline
        logger.info("Running COLMAP pipeline for initial reconstruction")
        feature_extraction(config, image_path, colmap_database_path)
        matcher(config, colmap_database_path)
        mapper(colmap_database_path, image_path, sparse_path)

    # Copy database to Glomap directory
    glomap_database_path = glomap_path / "database.db"
    shutil.copy2(colmap_database_path, glomap_database_path)

    # Run Glomap pipeline
    logger.info("Running Glomap pipeline")
    sparse_path = glomap_path / "sparse"
    sparse_path.mkdir(exist_ok=True, parents=True)

    glomap_mapper(glomap_database_path, image_path, sparse_path)

    logger.success("Glomap pipeline completed successfully.")
