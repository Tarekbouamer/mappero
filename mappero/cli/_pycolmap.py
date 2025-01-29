from pathlib import Path
from typing import Optional

import click
from loguru import logger
from omegaconf import OmegaConf

from mappero.modules.pycolmap import (
    extract_features,
    incremental_mapper,
    match_features,
    patch_match_stereo,
    stereo_fusion,
    undistort_images,
)


@click.group()
def pycolmap_cli():
    """Mappero Pycolmap CLI tool for 3D reconstruction tasks."""
    pass


@pycolmap_cli.command(name="sfm")
@click.argument("workspace_path", type=click.Path(exists=True))
@click.option("--config_path", default="mappero/config/pycolmap.yaml", help="Path to the config file.")
@click.option("--image_path", type=click.Path(), help="Path to the image directory.")
@click.option(
    "--matcher", default="exhaustive", type=click.Choice(["exhaustive", "spatial"]), help="Feature matching type."
)
def sfm(workspace_path: Path, config_path: str, image_path: Optional[Path], matcher: str) -> None:
    """Run Structure-from-Motion (SfM) pipeline."""
    # Setup logger
    logger.info("Initializing SfM task")

    # Workspace and paths
    workspace_path = Path(workspace_path)
    image_path = Path(image_path) if image_path else workspace_path / "images"
    pycolmap_path = workspace_path / "pycolmap"
    pycolmap_path.mkdir(parents=True, exist_ok=True)

    database_path = pycolmap_path / "database.db"
    sparse_path = pycolmap_path / "sparse"

    # Load config
    config = OmegaConf.load(config_path)

    # Run SFM tasks
    extract_features(config, image_path, database_path)
    match_features(config, database_path, matcher)
    incremental_mapper(config, database_path, image_path, sparse_path)

    logger.success("SfM task completed successfully.")


@pycolmap_cli.command(name="mvs")
@click.argument("workspace_path", type=click.Path(exists=True))
@click.option("--config_path", default="mappero/config/pycolmap.yaml", help="Path to the config file.")
@click.option("--image_path", type=click.Path(), help="Path to the image directory.")
def mvs(workspace_path: Path, config_path: str, image_path: Optional[Path]) -> None:
    """Run Multi-View Stereo (MVS) pipeline."""
    # Setup logger
    logger.info("Initializing MVS task")

    # Workspace and paths
    workspace_path = Path(workspace_path)
    image_path = Path(image_path) if image_path else workspace_path / "images"
    pycolmap_path = workspace_path / "pycolmap"
    pycolmap_path.mkdir(parents=True, exist_ok=True)

    sparse_path = pycolmap_path / "sparse"
    dense_path = pycolmap_path / "dense"

    # Load config
    config = OmegaConf.load(config_path)

    # Run MVS tasks
    undistort_images(config, image_path, sparse_path, dense_path)
    patch_match_stereo(config, dense_path)

    logger.success("MVS task completed successfully.")


@pycolmap_cli.command(name="fusion")
@click.argument("workspace_path", type=click.Path(exists=True))
@click.option("--config_path", default="mappero/config/pycolmap.yaml", help="Path to the config file.")
def fusion(workspace_path: Path, config_path: str) -> None:
    """Run Fusion pipeline for creating the 3D model."""
    # Setup logger
    logger.info("Initializing Fusion task")

    # Workspace and paths
    workspace_path = Path(workspace_path)
    pycolmap_path = workspace_path / "pycolmap"
    pycolmap_path.mkdir(parents=True, exist_ok=True)

    dense_path = pycolmap_path / "dense"
    fusion_path = pycolmap_path / "fused.ply"

    # Load config
    config = OmegaConf.load(config_path)

    # Run Fusion task
    stereo_fusion(config, dense_path, fusion_path)

    logger.success("Fusion task completed successfully.")


if __name__ == "__main__":
    pycolmap_cli()
