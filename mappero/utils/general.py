import contextlib
import io
import sys
from collections import defaultdict
from pathlib import Path
from typing import List, Tuple, Union

import h5py
import numpy as np
from loguru import logger

try:
    import pycolmap
except ImportError:
    logger.error("PyCOLMAP is not installed")


def parse_name(name):
    return name.replace("/", "-")


def get_keypoints(
    h5_path: str, name: str, return_uncertainty: bool = False
) -> Union[np.ndarray, Tuple[np.ndarray, float]]:
    """Retrieves keypoints for a given name from an HDF5 file."""

    with h5py.File(str(h5_path), "r", libver="latest") as hfile:
        dset = hfile[name]["kpts"]
        p = dset.__array__()
        uncertainty = dset.attrs.get("uncertainty")

    if return_uncertainty:
        return p, uncertainty
    return p


def names_to_pair(name0, name1, separator="/"):
    return separator.join((name0.replace("/", "-"), name1.replace("/", "-")))


def find_pair(hfile: h5py.File, name0: str, name1: str):
    if (pair := names_to_pair(name0, name1)) in hfile:
        return pair, False
    elif (pair := names_to_pair(name1, name0)) in hfile:
        return pair, True
    raise ValueError(f"Pair ({name0}, {name1}) not found in hfile.")


def get_matches(h5_path: str, name0: str, name1: str) -> Tuple[np.ndarray, np.ndarray]:
    """Finds matching indices and scores between two names in an HDF5 file."""
    with h5py.File(str(h5_path), "r", libver="latest") as hfile:
        # Find correct pair
        pair, reverse = find_pair(hfile, name0, name1)

        matches = hfile[pair]["matches"].__array__()
        mscores = hfile[pair]["mscores"].__array__()

    # -1 means no match
    idx = np.where(matches != -1)[0]
    matches = np.stack([idx, matches[idx]], -1)

    # Reverse matches if True
    if reverse:
        matches = np.flip(matches, -1)

    # FIXME: Remove this when imm provides correct scores shapes
    mscores = np.zeros_like(mscores)

    return matches, mscores


def find_unique_new_pairs(pairs_all: List[Tuple[str]], match_path: Path = None):
    """Avoid to recompute duplicates to save time."""
    pairs = set()
    for i, j in pairs_all:
        if (j, i) not in pairs:
            pairs.add((i, j))
    pairs = list(pairs)
    if match_path is not None and match_path.exists():
        with h5py.File(str(match_path), "r", libver="latest") as fd:
            pairs_filtered = []
            for i, j in pairs:
                if names_to_pair(i, j) in fd or names_to_pair(j, i) in fd:
                    continue
                pairs_filtered.append((i, j))
        return pairs_filtered
    return pairs


def parse_retrieval(path):
    retrieval = defaultdict(list)
    with open(path, "r") as f:
        for p in f.read().rstrip("\n").split("\n"):
            if len(p) == 0:
                continue
            q, r = p.split()
            retrieval[q].append(r)
    return dict(retrieval)


class OutputCapture:
    def __init__(self, verbose):
        self.verbose = verbose

    def __enter__(self):
        if not self.verbose:
            self.capture = contextlib.redirect_stdout(io.StringIO())
            self.out = self.capture.__enter__()

    def __exit__(self, exc_type, *args):
        if not self.verbose:
            self.capture.__exit__(exc_type, *args)
            if exc_type is not None:
                print("Failed with output:\n%s", self.out.getvalue())
        sys.stdout.flush()


def get_pairs_from_txt(path):
    pairs = []
    with open(path, "r") as f:
        for line in f.read().rstrip("\n").split("\n"):
            if len(line) == 0:
                continue

            q_name, db_name = line.split()
            pairs.append((q_name, db_name))

    return pairs


def to_homogeneous(p):
    return np.pad(p, ((0, 0),) * (p.ndim - 1) + ((0, 1),), constant_values=1)


def load_model(model_path: str):
    """Reads a COLMAP model from disk."""
    return pycolmap.Reconstruction(model_path)


def names_to_ids(model: Union[str, Path, pycolmap.Reconstruction]) -> List[int]:
    """Model mapping image names to their IDs."""

    if isinstance(model, (str, Path)):
        model = load_model(model)

    return {image.name: i for i, image in model.images.items()}


def compute_epipolar_errors(j_from_i: pycolmap.Rigid3d, p2d_i, p2d_j):
    j_E_i = j_from_i.essential_matrix()
    l2d_j = to_homogeneous(p2d_i) @ j_E_i.T
    l2d_i = to_homogeneous(p2d_j) @ j_E_i
    dist = np.abs(np.sum(to_homogeneous(p2d_i) * l2d_i, axis=1))
    errors_i = dist / np.linalg.norm(l2d_i[:, :2], axis=1)
    errors_j = dist / np.linalg.norm(l2d_j[:, :2], axis=1)
    return errors_i, errors_j
