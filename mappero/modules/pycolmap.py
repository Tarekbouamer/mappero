from pathlib import Path

import click
from loguru import logger
from omegaconf import OmegaConf

from mappero.utils.config import save_config
from mappero.utils.io import find_images
from mappero.utils.logger import setup_logger

try:
    import pycolmap
except ImportError:
    logger.error("PyCOLMAP is not installed")


def extract_features(config, image_path, database_path):
    """Extract features from images using PyCOLMAP.

    Args:
        config (OmegaConf): Configuration parameters for feature extraction.
        image_path (Path): Path to the directory containing images.
        database_path (Path): Path where the database file will be stored.

    Returns:
        None
    """
    logger.info("Starting feature extraction")
    # Set up SIFT extraction options
    sift_options = pycolmap.SiftExtractionOptions()
    sift_options.max_image_size = config.feature_extraction.max_image_size
    sift_options.max_num_features = config.feature_extraction.max_num_features
    logger.debug(f"SIFT options: {sift_options}")

    # Extract features and store them in the database
    pycolmap.extract_features(
        database_path=database_path,
        image_path=image_path,
        sift_options=sift_options,
    )
    logger.info("Feature extraction completed.")


def match_features(config, database_path, feature_matching="exhaustive"):
    """Match features using the specified matcher.

    Args:
        config (OmegaConf): Configuration parameters for feature matching.
        database_path (Path): Path to the database file containing features.
        feature_matching (str): Type of feature matcher to use ('exhaustive', 'spatial').

    Returns:
        None
    """
    logger.info(f"Starting feature matching using '{feature_matching}' matcher")
    # Set up SIFT matching options
    sift_options = pycolmap.SiftMatchingOptions()
    logger.debug(f"SIFT matching options: {sift_options}")

    # Choose matcher and matching options based on the specified type
    if feature_matching == "exhaustive":
        matcher = pycolmap.match_exhaustive
        matching_options = pycolmap.ExhaustiveMatchingOptions()
    elif feature_matching == "spatial":
        matcher = pycolmap.match_spatial
        matching_options = pycolmap.SpatialMatchingOptions()
    else:
        raise ValueError(f"Unknown feature matcher type: {feature_matching}")
    logger.debug(f"Matching options: {matching_options}")

    # Perform feature matching
    matcher(
        database_path=database_path,
        device=pycolmap.Device.auto,
        sift_options=sift_options,
        matching_options=matching_options,
    )
    logger.info("Feature matching completed.")


def incremental_mapper(config, database_path, image_path, output_path):
    """Run the incremental mapping algorithm to create a sparse model.

    Args:
        config (OmegaConf): Configuration parameters for mapping.
        database_path (Path): Path to the database file.
        image_path (Path): Path to the directory containing images.
        output_path (Path): Path where the sparse model will be saved.

    Returns:
        None
    """
    logger.info("Starting incremental mapping")

    # Run the incremental mapping process
    maps = pycolmap.incremental_mapping(
        database_path=database_path,
        image_path=image_path,
        output_path=output_path,
    )

    # Save the largest reconstructed model
    if maps:
        largest_model = maps[0]
        largest_model.write(output_path)
        logger.info(f"Mapping completed. Model saved to {output_path}")
    else:
        logger.warning("No models were reconstructed during mapping.")


def undistort_images(config, image_path, sparse_path, dense_path):
    """Undistort images based on the sparse reconstruction.

    Args:
        config (OmegaConf): Configuration parameters.
        image_path (Path): Path to the directory containing images.
        sparse_path (Path): Path to the sparse model directory.
        dense_path (Path): Path where undistorted images will be saved.

    Returns:
        None
    """
    logger.info("Starting image undistortion")
    # Perform image undistortion
    pycolmap.undistort_images(
        output_path=dense_path,
        input_path=sparse_path,
        image_path=image_path,
    )
    logger.info(f"Image undistortion completed. Undistorted images saved to {dense_path}")


def patch_match_stereo(config, dense_path):
    """Run PatchMatch stereo algorithm for dense reconstruction.

    Args:
        config (OmegaConf): Configuration parameters for PatchMatch.
        dense_path (Path): Path to the directory containing undistorted images.

    Returns:
        None
    """
    logger.info("Starting PatchMatch stereo")
    # Set up PatchMatch options
    mvs_options = pycolmap.PatchMatchOptions()
    mvs_options.window_radius = config.patch_match_stereo.window_radius
    mvs_options.num_iterations = config.patch_match_stereo.num_iterations
    mvs_options.max_image_size = config.patch_match_stereo.max_image_size
    logger.debug(f"PatchMatch options: {mvs_options}")

    # Run PatchMatch stereo
    pycolmap.patch_match_stereo(
        workspace_path=dense_path,
        options=mvs_options,
    )
    logger.info("PatchMatch stereo completed.")


def stereo_fusion(config, dense_path, fusion_path):
    """Fuse depth maps into a single point cloud.

    Args:
        config (OmegaConf): Configuration parameters for stereo fusion.
        dense_path (Path): Path to the directory containing depth maps.
        fusion_path (Path): Path where the fused point cloud will be saved.

    Returns:
        None
    """
    logger.info("Starting stereo fusion")
    # Set up stereo fusion options
    fusion_options = pycolmap.StereoFusionOptions()
    logger.debug(f"Stereo fusion options: {fusion_options}")

    # Run stereo fusion
    pycolmap.stereo_fusion(
        output_path=fusion_path,
        workspace_path=dense_path,
        workspace_format="COLMAP",
        options=fusion_options,
    )
    logger.info(f"Stereo fusion completed. Fused point cloud saved to {fusion_path}")


@click.command()
@click.argument("workspace_path", type=click.Path(exists=True))
@click.option("--config_path", default="mappero/config/pycolmap.yaml", help="Path to the config file.")
@click.option("--image_path", type=click.Path(), help="Path to the image directory.")
@click.option(
    "--task",
    type=click.Choice(["sfm", "mvs", "fusion", "mesh", "bundle_adjustment", "triangulation"]),
    default="sfm",
    help="Task to run in the pipeline.",
)
@click.option("--max_image_size", default=None, help="Maximum image size for feature extraction.")
@click.option(
    "--matcher",
    default="exhaustive",
    type=click.Choice(["exhaustive", "sequential", "vocab_tree"]),
    help="Matcher type to use.",
)
@click.help_option("--help", "-h")
def run_pycolmap(workspace_path, config_path, image_path, task, max_image_size, matcher):
    """PyCOLMAP pipeline."""
    # Setup logger
    setup_logger("PyCOLMAP")
    logger.info("Initializing PyCOLMAP pipeline")

    # Workspace
    workspace_path = Path(workspace_path)

    # Image path
    image_path = Path(image_path) if image_path else workspace_path / "images"

    # PyCOLMAP paths
    pycolmap_path = workspace_path / "pycolmap"
    pycolmap_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"PyCOLMAP path: {pycolmap_path}")

    database_path = pycolmap_path / "database.db"
    sparse_path = pycolmap_path / "sparse"
    dense_path = pycolmap_path / "dense"
    fusion_path = pycolmap_path / "fused.ply"

    # Config
    config = OmegaConf.load(config_path)
    save_config(config, pycolmap_path)
    logger.debug(f"Configuration loaded: {config}")

    # Find images
    images_paths = find_images(image_path, pycolmap_path / "images_paths.txt")

    if len(images_paths) == 0:
        logger.error("No images found in the specified path.")
        return

    logger.info(f"Found {len(images_paths)} images in {image_path}")

    # Execute tasks
    if task == "sfm":
        extract_features(config, image_path, database_path)
        match_features(config, database_path, matcher)
        incremental_mapper(config, database_path, image_path, sparse_path)
    elif task == "mvs":
        undistort_images(config, image_path, sparse_path, dense_path)
        patch_match_stereo(config, dense_path)
    elif task == "fusion":
        stereo_fusion(config, dense_path, fusion_path)
    else:
        logger.error(f"Task '{task}' is not implemented.")
        return

    logger.success("PyCOLMAP pipeline completed successfully.")


if __name__ == "__main__":
    run_pycolmap()
