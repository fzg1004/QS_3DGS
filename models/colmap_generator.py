import os
import cv2
import logging
from pathlib import Path
import pycolmap
from typing import Optional

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ColmapGenerator:
    def __init__(self):
        # 可配置参数
        self.frame_interval = 10  # 每10帧提取一帧（可根据视频帧率调整）
        self.image_ext = "jpg"     # 提取帧的格式
        self.min_num_matches = 15  # pycolmap特征匹配最小数量
        self.camera_model = "PINHOLE"  # 相机模型（可选：SIMPLE_PINHOLE, RADIAL等）
        self.max_image_size = 640     # 特征提取最大图像尺寸
        self.sift_num_octaves = 8     # SIFT八度数量

    def extract_video_frames(self, video_path: Path, output_dir: Path) -> None:
        """
        从视频提取帧到指定目录
        :param video_path: 视频文件路径
        :param output_dir: 帧输出目录
        """
        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        # 初始化视频捕获
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频文件: {video_path}")
        
        # 清空输出目录（可选，避免旧帧干扰）
        for img_file in output_dir.glob(f"*.{self.image_ext}"):
            img_file.unlink()
        
        frame_count = 0
        saved_count = 0
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        logger.info(f"开始提取视频帧：总帧数={total_frames}, 帧率={fps}, 提取间隔={self.frame_interval}")

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 按间隔提取帧
            if frame_count % self.frame_interval == 0:
                frame_filename = f"frame_{saved_count:06d}.{self.image_ext}"
                frame_path = output_dir / frame_filename
                # 保存帧（高质量）
                cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                saved_count += 1
            
            frame_count += 1

        cap.release()
        logger.info(f"帧提取完成：共保存 {saved_count} 帧到 {output_dir}")

    def run_sparse_reconstruction(self, colmap_dir:Path, frames_dir: Path, sparse_dir: Path) -> None:
        # 步骤2：pycolmap稀疏重建（生成二进制.bin文件）
        logger.info("开始COLMAP稀疏重建...")
        
        # 2.1 特征提取（适配3.13.0版本）
        database_path = colmap_dir / "database.db"
        
        pycolmap.extract_features(str(database_path),str(frames_dir))
        logger.info("特征提取完成")
       
         # ========== 2.2 特征匹配（3.13.0 直接传参） ==========
        pycolmap.match_exhaustive(str(database_path))
        logger.info("特征匹配完成")

        # ========== 2.3 稀疏重建（3.13.0 直接传参） ==========
        # 执行增量重建（无需IncrementalMapperOptions，直接传参）
        reconstructions = pycolmap.incremental_mapping(str(database_path),str(frames_dir),str(sparse_dir))
         # 验证并保存结果
        if not reconstructions:
            raise RuntimeError("稀疏重建失败，无有效数据")
        
        # 取第一个重建结果（主流场景只有一个模型）
        reconstruction = reconstructions[0]
        
        sparse_dir.mkdir(exist_ok=True, parents=True)
        reconstruction.write_binary(str(sparse_dir))
        
        logger.info(f"稀疏重建完成：相机数={len(reconstruction.cameras)}, 图像数={len(reconstruction.images)}, 点云数={len(reconstruction.points3D)}")



    def generate_from_video(self, video_path: str) -> dict:
        """
        从视频生成COLMAP格式稀疏重建数据（二进制.bin格式）
        :param video_path: 视频文件路径
        :return: 重建结果字典
        """
        try:
            # 路径初始化
            video_path = Path(video_path)
            if not video_path.exists():
                raise FileNotFoundError(f"视频文件不存在: {video_path}")
            
            video_dir = video_path.parent
            colmap_dir = video_dir / "colmap"
            frames_dir = colmap_dir / "images"  # 提取的视频帧目录
            sparse_dir = colmap_dir / "sparse"  # 稀疏重建输出目录
            dense_dir = colmap_dir / "dense"    # 可选：密集重建目录（暂不使用）
            
            # 创建目录
            for dir_path in [colmap_dir, frames_dir, sparse_dir, dense_dir]:
                dir_path.mkdir(exist_ok=True, parents=True)

            # 步骤1：提取视频帧
            self.extract_video_frames(video_path, frames_dir)
            if not list(frames_dir.glob(f"*.{self.image_ext}")):
                raise RuntimeError("未提取到任何视频帧，无法进行COLMAP重建")

            #稀疏重建
            self.run_sparse_reconstruction(colmap_dir, frames_dir, sparse_dir)

            # 返回结果信息
            return {
                "success": True,
                "video_path": str(video_path),
                "colmap_dir": str(colmap_dir),
                "frames_dir": str(frames_dir),
                "sparse_dir": str(sparse_dir),
            }

        except Exception as e:
            logger.error(f"从视频生成COLMAP数据失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": str(e),
                "video_path": str(video_path) if 'video_path' in locals() else ""
            }