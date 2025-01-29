from pathlib import Path
from typing import List, Optional

from loguru import logger


def find_images(image_path: Path, output_file: Optional[Path] = None) -> List[Path]:
    """Find images in the specified path"""

    # Search for image files with specified extensions, accounting for case sensitivity
    image_files = [
        file
        for ext in {"jpg", "jpeg", "png"}
        for file in list(image_path.rglob(f"*.{ext}")) + list(image_path.rglob(f"*.{ext.upper()}"))
    ]

    # Return early if no images are found
    if not image_files:
        logger.warning(f"No images found in {image_path}")
        return []

    # Optionally write to an output file
    if output_file:
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with output_file.open("w") as f:
                for image_file in image_files:
                    relative_path = image_file.relative_to(image_path)
                    f.write(f"{relative_path}\n")
            logger.info(f"Image list written to {output_file}")
        except Exception as e:
            logger.error(f"Error writing to {output_file}: {e}")

    return image_files
