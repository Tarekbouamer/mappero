import subprocess

from loguru import logger


def run_command(cmd: list, params: dict):
    """run a colmap command with parameters."""
    for key, value in params.items():
        cmd.append(f"--{key}")
        if value is not None:
            cmd.append(str(value))
    try:
        logger.info(f"running command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"command failed: {' '.join(cmd)}\nerror: {e}")
        raise
