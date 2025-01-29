from pathlib import Path

import click
import torch
from loguru import logger

from mappero.modules.opensfm import (
    covisible_pairs,
    create_database,
    extract_features,
    feature_matching,
    geometric_verification,
    import_features,
    import_matches,
    triangulate_points,
)
from mappero.utils.warnings import suppress_warnings


@click.group()
def opensfm_cli():
    """OpenSfM pipeline CLI group."""
    pass


@opensfm_cli.command()
@click.option("--model_path", type=click.Path(exists=True), required=True, help="Path to the COLMAP model.")
@click.option("--workspace", type=click.Path(), required=True, help="Path to the workspace directory.")
@click.option("--images_path", type=click.Path(), help="Path to the image directory.")
@click.option("--extractor", default="superpoint", help="Feature extractor.")
@click.option("--matcher", default="superglue_outdoor", help="Feature matcher.")
@click.option("--max_keypoints", default=-1, help="Maximum number of keypoints to extract per image, -1 for no limit.")
@click.option("--max_img_size", default=None, help="Maximum image size for feature extraction, None for no resizing.")
@click.option("--covisibility", default=10, help="Number of covisible images.")
@click.option("--save_path", help="Path to save the OpenSfM model.")
@click.help_option("--help", "-h")
@suppress_warnings()
def sfm(
    model_path: str,
    workspace: str,
    images_path: str,
    extractor: str,
    matcher: str,
    max_keypoints: int,
    max_img_size: int,
    covisibility: int,
    save_path: str,
):
    """
    OpenSfM pipeline to process images, extract features, match pairs, perform geometric verification, and triangulate points.
    """
    logger.info("Initializing OpenSfM pipeline")

    # Device setup
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.debug(f"Using device: {device}")

    # Workspace and image path setup
    workspace = Path(workspace)
    images_path = Path(images_path) if images_path else workspace / "images"

    # OpenSfM Paths
    if save_path:
        opensfm_path = Path(save_path)
    else:
        new_model_name = f"opensfm_{extractor}_{max_keypoints}_{matcher}_{covisibility}"
        opensfm_path = workspace / new_model_name
    opensfm_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"New model path: {opensfm_path}")

    # Output paths
    database_path = opensfm_path / "database.db"
    features_path = opensfm_path / "features.h5"
    matches_path = opensfm_path / "matches.h5"
    pairs_path = opensfm_path / "covisible_pairs.txt"
    sparse_path = opensfm_path / "sparse"

    # Generate covisible pairs
    covisible_pairs(model_path, num_covis=covisibility, pairs_path=pairs_path)

    # Extract features
    extract_features(
        images_path=images_path,
        extractor=extractor,
        max_keypoints=max_keypoints,
        max_img_size=max_img_size,
        features_path=features_path,
        device=device,
    )

    # Feature matching
    feature_matching(pairs_path, features_path, matcher=matcher, matches_path=matches_path, device=device)

    # Create and populate the database
    create_database(model_path, database_path)
    import_features(model_path, features_path, database_path)
    import_matches(model_path, matches_path, pairs_path, database_path)

    # Perform geometric verification
    geometric_verification(model_path, database_path, pairs_path, features_path, matches_path)

    # Triangulate 3D points
    triangulate_points(model_path, sparse_path, database_path, images_path)

    logger.success("OpenSfM pipeline completed successfully")

    return opensfm_path


if __name__ == "__main__":
    opensfm_cli()
