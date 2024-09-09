import click
import numpy as np
import open3d as o3d
from loguru import logger

from mappero.utils.colmap.read_write_model import qvec2rotmat, read_model


class Vis3D:
    def __init__(self):
        self.cameras = {}
        self.images = {}
        self.points3D = {}

        # open3d vis
        self.__vis = None

    def read_model(self, mode_path: str, ext: str = "") -> None:
        """read colmap model from path."""
        self.cameras, self.images, self.points3D = read_model(mode_path, ext)

        logger.info(f"num_cameras: {len(self.cameras)}")
        logger.info(f"num_images: {len(self.images)}")
        logger.info(f"num_points3D: {len(self.points3D)}")

    def create_window(self) -> None:
        """creates an open3d visualization window."""
        self.__vis = o3d.visualization.VisualizerWithKeyCallback()
        self.__vis.create_window()
        # add coordinate axes
        self.__vis.add_geometry(o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.5))

    def show(self) -> None:
        """shows the 3d model."""
        self.__vis.poll_events()
        self.__vis.update_renderer()
        self.__vis.run()

        # close window
        self.__vis.destroy_window()

    def add_points(self, min_track_len: int = 3, remove_statistical_outlier: bool = True) -> None:
        """adds and filters 3d points"""
        pcd = o3d.geometry.PointCloud()
        xyz, rgb = [], []

        # filter points
        for point3D in self.points3D.values():
            track_len = len(point3D.point2D_idxs)
            if track_len >= min_track_len:
                xyz.append(point3D.xyz)
                rgb.append(point3D.rgb / 255)

        #
        pcd.points = o3d.utility.Vector3dVector(np.stack(xyz))
        pcd.colors = o3d.utility.Vector3dVector(np.stack(rgb))

        # remove statistical outlier
        if remove_statistical_outlier:
            pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)

        # add point cloud to geometry
        self.__vis.add_geometry(pcd)
        self.__vis.poll_events()
        self.__vis.update_renderer()

    def add_cameras(self, scale: float = 0.25) -> None:
        """adds cameras to the open3d visualization."""
        for img in self.images.values():
            # create camera vis
            cam_vis = self.create_camera(img, scale)

            # add camera to geometry
            self.__vis.add_geometry(cam_vis)

    def create_camera(self, img, scale: float):
        """creates a camera visualization for the given image data."""

        # extrinsics
        T = self.get_extrinsics(img.qvec, img.tvec)

        # camera intrinsics
        cam = self.cameras[img.camera_id]
        K, width, height = self.get_intrinsics(cam, scale)

        # create camera visualization
        cam_vis = o3d.geometry.LineSet.create_camera_visualization(width, height, K, np.eye(4), scale=scale)
        cam_vis.transform(T)
        cam_vis.paint_uniform_color([1.0, 0.0, 0.0])  # red
        return cam_vis

    def get_extrinsics(self, qvec, tvec):
        """converts quaternion (qvec) and translation (tvec) to a transformation matrix."""
        R = qvec2rotmat(qvec)
        t = tvec

        # invert
        t = -R.T @ t
        R = R.T

        T = np.column_stack((R, t))
        T = np.vstack((T, (0, 0, 0, 1)))
        return T

    def get_intrinsics(self, cam, scale: float = 1.0):
        """returns scaled camera intrinsics for the given camera data."""
        width = int(cam.width * scale)
        height = int(cam.height * scale)
        K = np.identity(3)

        if cam.model in ("SIMPLE_PINHOLE", "SIMPLE_RADIAL", "RADIAL"):
            fx = fy = cam.params[0] * scale
            cx = cam.params[1] * scale
            cy = cam.params[2] * scale
        elif cam.model in ("PINHOLE", "OPENCV", "OPENCV_FISHEYE", "FULL_OPENCV"):
            fx = cam.params[0] * scale
            fy = cam.params[1] * scale
            cx = cam.params[2] * scale
            cy = cam.params[3] * scale
        else:
            raise ValueError(f"unsupported camera model: {cam.model}")

        # set intrinsics
        K[0, 0] = fx
        K[1, 1] = fy
        K[0, 2] = cx
        K[1, 2] = cy
        return K, width, height


@click.command()
@click.option("--model", required=True, type=click.Path(exists=True), help="path to input model folder.")
@click.option("--format", type=click.Choice([".bin", ".txt"]), default=".bin", help="input model format.")
@click.option("--scale", type=float, default=0.25, help="scale for visualizing cameras.")
@click.option("--min_track_len", type=int, default=3, help="minimum track length for 3d points.")
@click.option("--remove_statistical_outlier", is_flag=True, default=True, help="whether to remove statistical outliers.")
def run_vis(model: str, format: str, scale: float, min_track_len: int, remove_statistical_outlier: bool) -> None:
    """main function to run the colmap visualization."""
    vis3d = Vis3D()
    vis3d.read_model(model, ext=format)

    vis3d.create_window()
    vis3d.add_points(min_track_len=min_track_len, remove_statistical_outlier=remove_statistical_outlier)
    vis3d.add_cameras(scale=scale)
    vis3d.show()


if __name__ == "__main__":
    run_vis()
