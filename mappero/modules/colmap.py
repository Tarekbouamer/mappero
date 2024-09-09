from pathlib import Path

import click
from loguru import logger
from omegaconf import OmegaConf

from mappero.utils.config import save_config
from mappero.utils.process import run_command
from mappero.utils.io import find_images


def run_colmap_process(process_name: str, params: dict):
    """run a colmap process."""
    logger.info(f"starting {process_name}")
    run_command(["colmap", process_name], params)
    logger.success(f"{process_name.replace('_', ' ').title()} complete")


def feature_extraction(config, image_path: Path, database_path: Path):
    """extract features from images."""
    params = {
        "database_path": str(database_path),
        "image_path": str(image_path),
        "ImageReader.single_camera": config.feature_extraction.single_camera,
        "SiftExtraction.max_image_size": config.feature_extraction.max_image_size,
        "SiftExtraction.max_num_features": config.feature_extraction.max_num_features,
    }
    run_colmap_process("feature_extractor", params)


def matcher(config, database_path: Path, method="exhaustive", block_size=50):
    """perform image matching."""
    params = {"database_path": str(database_path)}
    if method == "exhaustive":
        params["ExhaustiveMatching.block_size"] = block_size
    elif method == "sequential":
        params["SequentialMatching.overlap"] = config.matcher.sequential.overlap
    elif method == "vocab_tree":
        params["VocabTreeMatching.vocab_tree_path"] = config.matcher.vocab_tree_path
    run_colmap_process(f"{method}_matcher", params)


def mapper(database_path: Path, image_path: Path, output_path: Path):
    """run sparse mapping."""
    params = {
        "database_path": str(database_path),
        "image_path": str(image_path),
        "output_path": str(output_path),
    }
    run_colmap_process("mapper", params)


def bundle_adjustment(input_path: Path, output_path: Path):
    """perform bundle adjustment."""
    params = {
        "input_path": str(input_path),
        "output_path": str(output_path),
    }
    run_colmap_process("bundle_adjuster", params)


def point_triangulator(database_path: Path, image_path: Path, input_path: Path, output_path: Path):
    """triangulate points."""
    params = {
        "database_path": str(database_path),
        "image_path": str(image_path),
        "input_path": str(input_path),
        "output_path": str(output_path),
    }
    run_colmap_process("point_triangulator", params)


def patch_match_stereo(workspace_path: Path):
    """run patchmatch stereo for dense reconstruction."""
    params = {
        "workspace_path": str(workspace_path),
        "workspace_format": "COLMAP",
        "PatchMatchStereo.geom_consistency": "true",
    }
    run_colmap_process("patch_match_stereo", params)


def stereo_fusion(workspace_path: Path, output_path: Path):
    """fuse stereo results."""
    params = {
        "workspace_path": str(workspace_path),
        "workspace_format": "COLMAP",
        "input_type": "geometric",
        "output_path": str(output_path),
    }
    run_colmap_process("stereo_fusion", params)


def poisson_mesher(input_path: Path, output_path: Path):
    """perform poisson meshing."""
    params = {
        "input_path": str(input_path),
        "output_path": str(output_path),
    }
    run_colmap_process("poisson_mesher", params)


def delaunay_mesher(input_path: Path, output_path: Path):
    """perform delaunay meshing."""
    params = {
        "input_path": str(input_path),
        "output_path": str(output_path),
    }
    run_colmap_process("delaunay_mesher", params)


def run_sfm(config, image_path: Path, database_path: Path, output_path: Path):
    """run the structure-from-motion pipeline."""
    feature_extraction(config, image_path, database_path)
    matcher(config, database_path)
    mapper(database_path, image_path, output_path)


def run_mvs(workspace_path: Path, output_path: Path):
    """run the multi-view stereo pipeline."""
    patch_match_stereo(workspace_path)
    stereo_fusion(workspace_path, output_path)


@click.command("run_colmap")
@click.argument("workspace_path", type=click.Path(exists=True))
@click.option("--config_path", default="mappero/config/colmap.yaml", help="path to the config file.")
@click.option("--image_path", type=click.Path(), help="path to the image directory.")
@click.option(
    "--task",
    type=click.Choice(["sfm", "mvs", "fusion", "mesh", "bundle_adjustment", "triangulation"]),
    default="sfm",
    help="task to run in the pipeline.",
)
@click.option("--max_image_size", default=None, help="maximum image size for feature extraction.")
@click.option("--vis", is_flag=True, help="enable visualization of results.")
@click.option(
    "--matcher",
    default="exhaustive",
    type=click.Choice(["exhaustive", "sequential", "vocab_tree"]),
    help="matcher type to use.",
)
@click.help_option("--help", "-h")
def run_colmap(workspace_path, config_path, image_path, task, max_image_size, vis, matcher):
    """
    run the colmap pipeline using the specified workspace and configuration.
    """
    # set up paths
    workspace_path = Path(workspace_path)
    config_path = Path(config_path)
    database_path = workspace_path / "database.db"

    # set images path
    image_path = Path(image_path) if image_path else workspace_path / "images"

    # create directories
    sparse_path = workspace_path / "sparse"
    dense_path = workspace_path / "dense"
    fusion_path = dense_path / "fused.ply"

    # load configuration
    config = OmegaConf.load(config_path)

    # find images and save configuration
    images_paths = find_images(image_path, workspace_path / "images_paths.txt")

    if len(images_paths) == 0:
        logger.error("no images found in the specified path.")
        return

    logger.info(f"found {len(images_paths)} images in {image_path}")

    # update configuration
    save_config(config, workspace_path)

    # exe
    if task == "sfm":
        sparse_path.mkdir(exist_ok=True, parents=True)
        run_sfm(config, image_path, database_path, sparse_path)
    elif task == "mvs":
        dense_path.mkdir(exist_ok=True, parents=True)
        run_mvs(dense_path, fusion_path)
    elif task == "fusion":
        stereo_fusion(dense_path, fusion_path)
    elif task == "mesh":
        poisson_mesher(fusion_path, dense_path / "meshed-poisson.ply")
    elif task == "bundle_adjustment":
        raise NotImplementedError("bundle adjustment is not yet implemented")
    elif task == "triangulation":
        raise NotImplementedError("triangulation is not yet implemented")

    logger.success("colmap pipeline complete")


if __name__ == "__main__":
    run_colmap()
