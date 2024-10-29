from pathlib import Path
import shutil

import click
from loguru import logger
from omegaconf import OmegaConf

from mappero.utils.config import save_config
from mappero.utils.logger import setup_logger
from mappero.utils.process import run_command


def run_sfm(config, image_path, database_path, output_path):
    """run structure from motion."""
    params = {
        "database_path": str(database_path),
        "image_path": str(image_path),
        "output_path": str(output_path),
    }
    run_command(["glomap", "mapper"], params)


@click.command()
@click.argument("workspace_path", type=click.Path(exists=True))
@click.option("--config_path", default="mappero/config/glomap.yaml", help="Path to the config file.")
@click.option("--image_path", type=click.Path(), help="Path to the image directory.")
@click.option(
    "--task",
    type=click.Choice(["sfm"]),
    default="sfm",
    help="Task to run in the pipeline.",
)
@click.help_option("--help", "-h")
def run_glomap(workspace_path, config_path, image_path, task):
    """Glomap pipeline wrapper."""

    # Setup logger
    setup_logger("Glomap")
    logger.info("Initializing Glomap pipeline")

    # Workspace
    workspace_path = Path(workspace_path)

    # Image path
    image_path = Path(image_path) if image_path else workspace_path / "images"

    # Colmap paths
    colmap_path = workspace_path / "colmap"

    # Glomap paths
    glomap_path = workspace_path / "glomap"
    glomap_path.mkdir(exist_ok=True, parents=True)
    database_path = glomap_path / "database.db"

    # Copy database
    colmap_database_path = colmap_path / "database.db"
    shutil.copy2(colmap_database_path, database_path)

    # Config
    config_path = config_path
    config = OmegaConf.load(config_path)
    save_config(config, glomap_path)

    # exe
    if task == "sfm":
        run_sfm(config, image_path, database_path, glomap_path)
    else:
        raise

    logger.success("Glomap pipeline completed successfully.")


if __name__ == "__main__":
    run_glomap()
