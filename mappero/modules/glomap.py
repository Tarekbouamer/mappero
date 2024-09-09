from pathlib import Path

import click
from loguru import logger
from omegaconf import OmegaConf

from mappero.utils.config import save_config
from mappero.utils.process import run_command
from mappero.utils.io import find_images


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
@click.option("--config_path", default="mappero/config/glomap.yaml", help="path to the config file.")
@click.option("--image_path", type=click.Path(), help="path to the image directory.")
@click.option(
    "--task",
    type=click.Choice(["sfm"]),
    default="sfm",
    help="task to run in the pipeline.",
)
@click.option("--vis", is_flag=True, help="enable visualization of results.")
@click.help_option("--help", "-h")
def run_glomap(workspace_path, config_path, image_path, task, vis):
    """
    run the glomap pipeline.
    
    example:
    glomap mapper \
        --database_path ./data/gerrard-hall/database.db \
        --image_path    ./data/gerrard-hall/images \
        --output_path   ./output/gerrard-hall/sparse \
    """
    # set up paths
    workspace_path = Path(workspace_path)
    database_path = workspace_path / "database.db"

    # model path
    glomap_path = workspace_path / "glomap"
    glomap_path.mkdir(exist_ok=True, parents=True)

    # load configuration
    config_path = Path(config_path)
    config = OmegaConf.load(config_path)

    # set images path
    image_path = Path(image_path) if image_path else workspace_path / "images"
    images_paths = find_images(image_path, glomap_path / "images_paths.txt")

    if len(images_paths) == 0:
        logger.error("no images found in the specified path.")
        return

    logger.info(f"found {len(images_paths)} images in {image_path}")

    # update configuration
    save_config(config, workspace_path)

    # exe
    if task == "sfm":
        run_sfm(config, image_path, database_path, glomap_path)
    else:
        raise

    logger.success("glomap pipeline complete")


if __name__ == "__main__":
    run_glomap()
