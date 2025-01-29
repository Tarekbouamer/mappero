from pathlib import Path

from loguru import logger

from mappero.utils.process import run_command


def run_colmap_process(process_name: str, params: dict):
    """run a colmap process."""
    logger.info(f"starting {process_name}")
    run_command(["colmap", process_name], params)
    logger.success(f"{process_name.replace('_', ' ').title()} completed")


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


def image_undistorter(image_path: Path, sparse_path: Path, dense_path: Path, max_image_size=2000):
    """undistort images."""
    params = {
        "image_path": str(image_path),
        "input_path": str(sparse_path / "0"),
        "output_path": str(dense_path),
        "output_type": "COLMAP",
        "max_image_size": max_image_size,
    }
    run_colmap_process("image_undistorter", params)


def patch_match_stereo(dense_path: Path):
    """run patchmatch stereo for dense reconstruction."""
    params = {
        "workspace_path": str(dense_path),
        "workspace_format": "COLMAP",
        "PatchMatchStereo.geom_consistency": "true",
    }
    run_colmap_process("patch_match_stereo", params)


def stereo_fusion(dense_path: Path, output_path: Path):
    """fuse stereo results."""
    params = {
        "workspace_path": str(dense_path),
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
