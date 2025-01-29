from pathlib import Path

import pycolmap
import torch
from loguru import logger
from omegaconf import OmegaConf


def extract_features(config: OmegaConf, image_path: Path, database_path: Path) -> None:
    """Extract features from images using PyCOLMAP."""
    logger.info("Starting feature extraction")
    sift_options = pycolmap.SiftExtractionOptions()
    sift_options.max_image_size = config.feature_extraction.max_image_size
    sift_options.max_num_features = config.feature_extraction.max_num_features
    logger.debug(f"SIFT options: {sift_options}")

    pycolmap.extract_features(
        database_path=database_path,
        image_path=image_path,
        sift_options=sift_options,
    )
    logger.info("Feature extraction completed.")


def match_features(config: OmegaConf, database_path: Path, feature_matching: str = "exhaustive") -> None:
    """Match features using the specified matcher."""
    logger.info(f"Starting feature matching using '{feature_matching}' matcher")
    sift_options = pycolmap.SiftMatchingOptions()
    logger.debug(f"SIFT matching options: {sift_options}")

    if feature_matching == "exhaustive":
        matcher = pycolmap.match_exhaustive
        matching_options = pycolmap.ExhaustiveMatchingOptions()
    elif feature_matching == "spatial":
        matcher = pycolmap.match_spatial
        matching_options = pycolmap.SpatialMatchingOptions()
    else:
        raise ValueError(f"Unknown feature matcher type: {feature_matching}")
    logger.debug(f"Matching options: {matching_options}")

    matcher(
        database_path=database_path,
        device=pycolmap.Device.auto,
        sift_options=sift_options,
        matching_options=matching_options,
    )
    logger.info("Feature matching completed.")


def incremental_mapper(config: OmegaConf, database_path: Path, image_path: Path, output_path: Path) -> None:
    """Run the incremental mapping algorithm to create a sparse model."""
    logger.info("Starting incremental mapping")

    maps = pycolmap.incremental_mapping(
        database_path=database_path,
        image_path=image_path,
        output_path=output_path,
    )

    if maps:
        largest_model = maps[0]
        largest_model.write(output_path)
        logger.info(f"Mapping completed. Model saved to {output_path}")
    else:
        logger.warning("No models were reconstructed during mapping.")


def undistort_images(config: OmegaConf, image_path: Path, sparse_path: Path, dense_path: Path) -> None:
    """Undistort images based on the sparse reconstruction."""
    logger.info("Starting image undistortion")
    pycolmap.undistort_images(
        output_path=dense_path,
        input_path=sparse_path,
        image_path=image_path,
    )
    logger.info(f"Image undistortion completed. Undistorted images saved to {dense_path}")


def patch_match_stereo(config: OmegaConf, dense_path: Path) -> None:
    """Run PatchMatch stereo algorithm for dense reconstruction."""
    logger.info("Starting PatchMatch stereo")
    mvs_options = pycolmap.PatchMatchOptions()
    mvs_options.window_radius = config.patch_match_stereo.window_radius
    mvs_options.num_iterations = config.patch_match_stereo.num_iterations
    mvs_options.max_image_size = config.patch_match_stereo.max_image_size
    logger.debug(f"PatchMatch options: {mvs_options}")

    pycolmap.patch_match_stereo(
        workspace_path=dense_path,
        options=mvs_options,
    )
    logger.info("PatchMatch stereo completed.")


def stereo_fusion(config: OmegaConf, dense_path: Path, fusion_path: Path) -> None:
    """Fuse depth maps into a single point cloud."""
    logger.info("Starting stereo fusion")
    fusion_options = pycolmap.StereoFusionOptions()
    logger.debug(f"Stereo fusion options: {fusion_options}")

    pycolmap.stereo_fusion(
        output_path=fusion_path,
        workspace_path=dense_path,
        workspace_format="COLMAP",
        options=fusion_options,
    )
    logger.info(f"Stereo fusion completed. Fused point cloud saved to {fusion_path}")
