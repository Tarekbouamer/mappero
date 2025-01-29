from pathlib import Path

from mappero.utils.process import run_command


def glomap_mapper(database_path: Path, image_path: Path, output_path: Path) -> None:
    """Run Structure-from-Motion using Glomap."""
    params = {
        "database_path": str(database_path),
        "image_path": str(image_path),
        "output_path": str(output_path),
    }
    run_command(["glomap", "mapper"], params)
