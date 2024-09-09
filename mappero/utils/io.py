from pathlib import Path


def find_images(image_path: Path, output_file: Path):
    """find images in the specified path."""
    image_files = []
    for ext in ["jpg", "jpeg", "png"]:
        image_files.extend(image_path.rglob(f"*.{ext}"))
        image_files.extend(image_path.rglob(f"*.{ext.upper()}"))
    if output_file.exists():
        output_file.unlink()
    with output_file.open("w") as f:
        for image_file in image_files:
            relative_path = image_file.relative_to(image_path)
            f.write(f"{relative_path}\n")
    return image_files
