from pathlib import Path
from typing import List, Optional

import click
from loguru import logger
from omegaconf import OmegaConf

from mappero.modules.colmap import (
    feature_extraction,
    image_undistorter,
    mapper,
    matcher,
    patch_match_stereo,
    poisson_mesher,
    stereo_fusion,
)
from mappero.utils.config import save_config
from mappero.utils.io import find_images


@click.group()
def colmap_cli() -> None:
    """imm-colmap: A CLI tool for running COLMAP pipeline tasks."""
    pass


@colmap_cli.command()
@click.argument("workspace_path", type=click.Path(exists=True))
@click.option("--image_path", type=click.Path(), help="Path to the image directory.")
@click.option(
    "--config_path",
    default="mappero/config/colmap.yaml",
    help="Path to the configuration file.",
)
def sfm(workspace_path: str, image_path: Optional[str], config_path: str) -> None:
    """Run the Structure-from-Motion (SfM) pipeline."""
    # Workspace
    workspace_path = Path(workspace_path)

    # Colmap path
    colmap_path = workspace_path / "colmap"
    colmap_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Colmap path: {colmap_path}")

    # Image path
    image_path = Path(image_path) if image_path else workspace_path / "images"

    database_path = colmap_path / "database.db"
    sparse_path = colmap_path / "sparse"

    # Config
    config = OmegaConf.load(config_path)
    save_config(config, colmap_path)

    # Find images
    images_paths: List[Path] = find_images(image_path, colmap_path / "images_paths.txt")

    if len(images_paths) == 0:
        logger.error("No images found in the specified path.")
        return

    logger.info(f"Found {len(images_paths)} images in {image_path}")

    # Execute
    sparse_path.mkdir(exist_ok=True, parents=True)
    feature_extraction(config, image_path, database_path)
    matcher(config, database_path)
    mapper(database_path, image_path, sparse_path)

    logger.success("COLMAP SfM pipeline completed successfully")


@colmap_cli.command()
@click.argument("workspace_path", type=click.Path(exists=True))
@click.option(
    "--config_path",
    default="mappero/config/colmap.yaml",
    help="Path to the configuration file.",
)
def mvs(workspace_path: str, config_path: str) -> None:
    """Run the Multi-View Stereo (MVS) pipeline."""
    # Workspace
    workspace_path = Path(workspace_path)

    # Colmap path
    colmap_path = workspace_path / "colmap"
    colmap_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Colmap path: {colmap_path}")

    # Config
    images_path = workspace_path / "images"
    sparse_path = colmap_path / "sparse"
    dense_path = colmap_path / "dense"
    fusion_path = colmap_path / "fused.ply"

    # Execute
    image_undistorter(images_path, sparse_path, dense_path)
    patch_match_stereo(dense_path)
    stereo_fusion(dense_path, fusion_path)

    logger.success("COLMAP MVS pipeline completed successfully")


@colmap_cli.command()
@click.argument("workspace_path", type=click.Path(exists=True))
@click.option(
    "--config_path",
    default="mappero/config/colmap.yaml",
    help="Path to the configuration file.",
)
def fusion(workspace_path: str, config_path: str) -> None:
    """Run the Fusion pipeline."""
    # Workspace
    workspace_path = Path(workspace_path)

    # Colmap path
    colmap_path = workspace_path / "colmap"
    colmap_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Workspace path: {colmap_path}")

    dense_path = colmap_path / "dense"
    fusion_path = colmap_path / "fused.ply"

    # Config
    config = OmegaConf.load(config_path)
    save_config(config, colmap_path)

    # Execute
    stereo_fusion(dense_path, fusion_path)

    logger.success("COLMAP fusion pipeline completed successfully")


@colmap_cli.command()
@click.argument("workspace_path", type=click.Path(exists=True))
@click.option(
    "--config_path",
    default="mappero/config/colmap.yaml",
    help="Path to the configuration file.",
)
def mesh(workspace_path: str, config_path: str) -> None:
    """Run the Meshing pipeline."""
    # Workspace
    workspace_path = Path(workspace_path)

    # Colmap path
    colmap_path = workspace_path / "colmap"
    colmap_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Workspace path: {colmap_path}")

    fusion_path = colmap_path / "fused.ply"
    mesh_path = colmap_path / "mesh.ply"

    # Config
    config = OmegaConf.load(config_path)
    save_config(config, colmap_path)

    # Execute
    poisson_mesher(fusion_path, mesh_path)

    logger.success("COLMAP meshing pipeline completed successfully")


if __name__ == "__main__":
    colmap_cli()
