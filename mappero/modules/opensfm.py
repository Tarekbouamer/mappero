from collections import defaultdict
from pathlib import Path
from typing import Dict, Union

import click
import numpy as np
import torch
from imm.tools import Extraction
from imm.tools.match import Matching
from imm.utils.dataset import FeaturesPairsDataset, ImagesFromList
from loguru import logger
from omegaconf import OmegaConf
from tqdm import tqdm

from mappero.utils.colmap.database import COLMAPDatabase
from mappero.utils.colmap.read_write_model import read_model
from mappero.utils.config import save_config
from mappero.utils.general import (
    OutputCapture,
    compute_epipolar_errors,
    find_unique_new_pairs,
    get_keypoints,
    get_matches,
    get_pairs_from_txt,
    names_to_ids,
    parse_retrieval,
)
from mappero.utils.logger import setup_logger
from mappero.utils.warnings import suppress_warnings

try:
    import pycolmap
except ImportError:
    logger.error("PyCOLMAP is not installed")


def covisible_pairs(config, sfm_model_path: Path, num_covis: int = None, sfm_pairs_path: Path = None) -> Path:
    """Find covisible pairs of images in the reconstruction and save them to a file."""

    # Set default output
    if sfm_pairs_path is None:
        sfm_pairs_path = sfm_model_path / "covisible_pairs.txt"

    # Set the number of covisible pairs
    if num_covis is None:
        num_covis = config.covisibility

    logger.info(f"Searching for {num_covis} covisibility pairs")
    # Load the model
    _, images, points3D = read_model(sfm_model_path)

    sfm_pairs = []
    for image_id, image in tqdm(images.items(), desc="Processing images"):
        # Filter points associated with 3D points
        matched = image.point3D_ids != -1
        points3D_covis = image.point3D_ids[matched]

        # Gather covisible images by counting shared 3D points
        covis = defaultdict(int)
        for point_id in points3D_covis:
            for image_covis_id in points3D[point_id].image_ids:
                if image_covis_id != image_id:
                    covis[image_covis_id] += 1

        if len(covis) == 0:
            logger.warning(f"Image {image_id} has no covisible images.")
            continue

        covis_ids = np.array(list(covis.keys()))
        covis_num = np.array([covis[i] for i in covis_ids])

        # Select top covisible images
        if len(covis_ids) <= num_covis:
            top_covis_ids = covis_ids[np.argsort(-covis_num)]
        else:
            # Efficient top-k selection and sorting
            ind_top = np.argpartition(covis_num, -num_covis)[-num_covis:]
            ind_top = ind_top[np.argsort(-covis_num[ind_top])]
            top_covis_ids = [covis_ids[i] for i in ind_top]

            assert covis_num[ind_top[0]] == np.max(covis_num)

        # Collect image pairs
        for i in top_covis_ids:
            pair = (image.name, images[i].name)
            sfm_pairs.append(pair)

    # Save the pairs to the specified path
    with open(sfm_pairs_path, "w") as f:
        f.write("\n".join(" ".join(pair) for pair in sfm_pairs))

    logger.info(f"Found {len(sfm_pairs)} covisible pairs and saved to {sfm_pairs_path}")

    return sfm_pairs_path


def create_database(sfm_model_path: Path, database_path: Path) -> None:
    """Create a reconstruction database from an SfM model."""

    # Check if the database already exists
    if database_path.exists():
        logger.info("The database already exists. Deleting it.")
        database_path.unlink()

    # Load the SfM model
    model = pycolmap.Reconstruction(sfm_model_path)
    logger.info(f"Loaded SfM model from {sfm_model_path}")

    # Connect to the database and create tables
    db = COLMAPDatabase.connect(database_path)
    db.create_tables()
    logger.info("Initialized database and created tables.")

    # Add cameras
    for i, camera in model.cameras.items():
        db.add_camera(
            camera.model.value, camera.width, camera.height, camera.params, camera_id=i, prior_focal_length=True
        )
    logger.info(f"Added {len(model.cameras)} cameras to the database.")

    # Add images
    for i, image in model.images.items():
        db.add_image(image.name, image.camera_id, image_id=i)
    logger.info(f"Added {len(model.images)} images to the database.")

    # Close
    db.commit()
    db.close()
    logger.success(f"Database created successfully at {database_path}")


def import_features(sfm_model_path: Path, features_path: Path, database_path: Path) -> None:
    """Import features from a feature file into the COLMAP database."""

    logger.info("Importing features into the database")

    # Connect to the database
    db = COLMAPDatabase.connect(database_path)

    # Get image IDs
    image_ids = names_to_ids(sfm_model_path)

    # Import features
    for image_name, image_id in tqdm(image_ids.items(), desc="Importing features", colour="magenta"):
        keypoints = get_keypoints(features_path, image_name)
        keypoints += 0.5  # Adjust for COLMAP origin
        db.add_keypoints(image_id, keypoints)

    # Close
    db.commit()
    db.close()
    logger.info(f"Features successfully imported into {database_path}")


def import_matches(
    sfm_model_path: Path,
    matches_path: Path,
    pairs_path: Path,
    database_path: Path,
    config: Dict = None,
    skip_geometric_verification: bool = False,
) -> None:
    """Import matches from a file into the COLMAP database."""

    logger.info("Importing matches into the database")

    # Load image pairs
    with open(pairs_path, "r") as f:
        pairs = [line.split() for line in f.readlines()]

    # Connect to the database
    db = COLMAPDatabase.connect(database_path)
    logger.info("Connected to the database.")

    # Retrieve image IDs
    image_ids = names_to_ids(sfm_model_path)
    matched = set()

    # Process each pair of images
    for name0, name1 in tqdm(pairs, desc="Importing matches", colour="magenta"):
        id0, id1 = image_ids[name0], image_ids[name1]

        # Skip if this pair has already been matched in either order
        if len({(id0, id1), (id1, id0)} & matched) > 0:
            continue

        # Get matches for the pair
        matches, scores = get_matches(matches_path, name0, name1)

        # Apply minimum match score filter
        min_match_score = config.get("min_match_score", 0.0)
        if min_match_score:
            matches = matches[scores > min_match_score]

        # Add matches
        db.add_matches(id0, id1, matches)
        matched |= {(id0, id1), (id1, id0)}

        # Add two-view geometry
        if skip_geometric_verification:
            db.add_two_view_geometry(id0, id1, matches)

    # Commit and close the database
    db.commit()
    db.close()
    logger.success(f"Matches successfully imported into {database_path}")


def geometric_verification(
    sfm_model_path: Path,
    database_path: Path,
    pairs_path: Path,
    features_path: Path,
    matches_path: Path,
    max_epip_error: float = 4.0,
) -> None:
    """Perform geometric verification on pair matches to filter based on epipolar constraints."""

    logger.info("Performing geometric verification of the matches")

    # Load image IDs and the reference reconstruction
    image_ids = names_to_ids(sfm_model_path)
    reference = pycolmap.Reconstruction(sfm_model_path)

    # Parse image pairs and connect to the database
    pairs = parse_retrieval(pairs_path)
    db = COLMAPDatabase.connect(database_path)

    #
    inlier_ratios = []
    matched = set()
    for name0 in tqdm(pairs):
        id0 = image_ids[name0]
        image0 = reference.images[id0]
        cam0 = reference.cameras[image0.camera_id]
        kps0, noise0 = get_keypoints(features_path, name0, return_uncertainty=True)
        noise0 = 1.0 if noise0 is None else noise0
        if len(kps0) > 0:
            kps0 = np.stack(cam0.cam_from_img(kps0))
        else:
            kps0 = np.zeros((0, 2))

        for name1 in pairs[name0]:
            id1 = image_ids[name1]
            image1 = reference.images[id1]
            cam1 = reference.cameras[image1.camera_id]
            kps1, noise1 = get_keypoints(features_path, name1, return_uncertainty=True)
            noise1 = 1.0 if noise1 is None else noise1
            if len(kps1) > 0:
                kps1 = np.stack(cam1.cam_from_img(kps1))
            else:
                kps1 = np.zeros((0, 2))

            matches = get_matches(matches_path, name0, name1)[0]

            if len({(id0, id1), (id1, id0)} & matched) > 0:
                continue
            matched |= {(id0, id1), (id1, id0)}

            if matches.shape[0] == 0:
                db.add_two_view_geometry(id0, id1, matches)
                continue

            cam1_from_cam0 = image1.cam_from_world * image0.cam_from_world.inverse()
            errors0, errors1 = compute_epipolar_errors(cam1_from_cam0, kps0[matches[:, 0]], kps1[matches[:, 1]])
            valid_matches = np.logical_and(
                errors0 <= cam0.cam_from_img_threshold(noise0 * max_epip_error),
                errors1 <= cam1.cam_from_img_threshold(noise1 * max_epip_error),
            )
            # TODO: We could also add E to the database, but we need
            # to reverse the transformations if id0 > id1 in utils/database.py.
            db.add_two_view_geometry(id0, id1, matches[valid_matches, :])
            inlier_ratios.append(np.mean(valid_matches))

    # Log statistics
    logger.info(
        f"Mean/Median/Min/Max valid matches: "
        f"{np.mean(inlier_ratios) * 100:.2f}% / "
        f"{np.median(inlier_ratios) * 100:.2f}% / "
        f"{np.min(inlier_ratios) * 100:.2f}% / "
        f"{np.max(inlier_ratios) * 100:.2f}%"
    )

    db.commit()
    db.close()
    logger.success("Geometric verification completed and database updated.")


def extract_features(
    image_path: Path, features_path: Path, config: dict = None, device: Union[str, torch.device] = "cpu"
) -> None:
    """Extract features from a list of images and save them to features.h5."""
    logger.info("Starting feature extraction")

    # Load images
    dataset = ImagesFromList(image_path)

    # Extractor configuration
    ext_name = config["feature_extraction"].get("extractor")
    max_keypoints = config["feature_extraction"].get("max_keypoints")

    ext_config = {
        "max_keypoints": max_keypoints,
    }

    extractor = Extraction(ext_name, ext_config, device=device)
    extractor.extract_dataset(dataset, features_path)

    logger.success(f"Features saved to {features_path}")


def feature_matching(
    pairs_path: Path,
    features_path: Path,
    matches_path: Path,
    matcher: str = "superglue_outdoor",
    device: Union[str, torch.device] = "cpu",
) -> None:
    """Matches features based on image pairs and saves the results."""

    logger.info(f"Starting feature matching with matcher {matcher}")

    # Load and filter unique, new pairs
    pairs = get_pairs_from_txt(pairs_path)
    pairs = find_unique_new_pairs(pairs)
    logger.info(f"Loaded {len(pairs)} unique pairs for matching.")

    if not pairs:
        logger.warning("No new pairs to match.")
        return

    # Load the features dataset
    pairs_dataset = FeaturesPairsDataset(pairs, features_path)

    # Match Features
    matcher = Matching(matcher, device=device)
    matcher.match_sequence_features(pairs_dataset, matches_path)

    logger.success("Feature matching saved to %s", matches_path)


def triangulate_points(
    sfm_model_path: Path,
    opensfm_path: Path,
    database_path: Path,
    images_path: Path,
    options: dict = {},
    verbose: bool = False,
) -> "pycolmap.Reconstruction":
    """Triangulate 3D points from 2D-3D correspondences."""

    logger.info("Running 3D triangulation")

    # Load the reference model
    reference_model = pycolmap.Reconstruction(sfm_model_path)
    logger.info(f"Loaded reference model from {sfm_model_path}")

    # Run the triangulation with output capture for optional verbosity
    with OutputCapture(verbose):
        with pycolmap.ostream():
            reconstruction = pycolmap.triangulate_points(reference_model, database_path, images_path, opensfm_path)

    # Log summary statistics
    logger.info(f"Reconstruction statistics:\n{reconstruction.summary()}")

    logger.success(f"3D triangulation completed and saved to {opensfm_path}")

    return reconstruction


@click.command()
@click.argument("workspace_path", type=click.Path(exists=True))
@click.option("--image_path", type=click.Path(), help="Path to the image directory.")
@click.option("--config_path", default="mappero/config/opensfm.yaml", help="Path to the config file.")
@click.option("--extractor", default="superpoint", help="Feature extractor.")
@click.option("--max_keypoints", default=4096, help="Maximum number of keypoints to extract per image.")
@click.option("--matcher", default="superglue_outdoor", help="Feature matcher.")
@click.option("--covisibility", default=10, help="Number of covisible images.")
@click.help_option("--help", "-h")
@suppress_warnings()
def run_opensfm(workspace_path, image_path, config_path, extractor, max_keypoints, matcher, covisibility):
    """
    OpenSfM pipeline to process images, extract features, match pairs, perform geometric verification, and triangulate points.
    """
    # Setup logger
    setup_logger("OpenSfM")
    logger.info("Initializing OpenSfM pipeline")

    # Device setup
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.debug(f"Using device: {device}")

    # Workspace
    workspace_path = Path(workspace_path)

    # Image path
    image_path = Path(image_path) if image_path else workspace_path / "images"

    # SfM model path TODO: better handling of multiple source of models, default to colmap/sparse/0
    sfm_model_path = workspace_path / "colmap/sparse/0"

    # OpenSfM Paths
    new_model_name = f"opensfm_{extractor}_{max_keypoints}_{matcher}_{covisibility}"
    opensfm_path = workspace_path / new_model_name
    opensfm_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"New model path: {opensfm_path}")

    # Output paths
    database_path = opensfm_path / "database.db"
    features_path = opensfm_path / "features.h5"
    matches_path = opensfm_path / "matches.h5"
    sfm_pairs_path = opensfm_path / "covisible_pairs.txt"
    sparse_path = opensfm_path / "sparse"

    # Config
    config = OmegaConf.load(config_path)
    config.covisibility = covisibility
    config.feature_extraction.extractor = extractor
    config.feature_extraction.max_keypoints = max_keypoints
    config.feature_matching.matcher = matcher
    save_config(config, opensfm_path)
    logger.debug(f"Configuration loaded: {config}")

    # Generate covisible pairs
    covisible_pairs(config, sfm_model_path, num_covis=config.covisibility, sfm_pairs_path=sfm_pairs_path)

    # Extract features
    extract_features(image_path, features_path, config=config, device=device)

    # Feature matching
    feature_matching(
        sfm_pairs_path, features_path, matches_path, matcher=config.feature_matching.matcher, device=device
    )

    # Create and populate the database
    create_database(sfm_model_path, database_path)

    import_features(sfm_model_path, features_path, database_path)

    import_matches(sfm_model_path, matches_path, sfm_pairs_path, database_path, config=config)

    # Perform geometric verification
    geometric_verification(sfm_model_path, database_path, sfm_pairs_path, features_path, matches_path)

    # Triangulate 3D points
    triangulate_points(sfm_model_path, sparse_path, database_path, image_path)

    logger.success("OpenSfM pipeline completed successfully")


if __name__ == "__main__":
    run_opensfm()
