import subprocess
import sys
import json
from pathlib import Path
import logging
import time

from config import Config

logger = logging.getLogger(__name__)

class ModelTrainer:
    """高斯溅射模型训练器"""
    
    def __init__(self):
        self.gs_repo_path = Config.GS_REPO_PATH
        self.train_script = Config.GS_TRAIN_SCRIPT
    
    def train(self, colmap_path, output_dir=None):
        """训练高斯溅射模型"""
        try:
            colmap_path = Path(colmap_path)
            if not colmap_path.exists():
                raise ValueError(f"COLMAP路径不存在: {colmap_path}")
            
            # 确定输出目录
            if output_dir is None:
                output_dir = colmap_path.parent / "output"
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True)
            
            # 检查训练脚本是否存在
            if not self.train_script or not self.train_script.exists():
                return {
                    'success': False,
                    'message': '没有找到训练脚本'
                }
            
            # 构建训练命令
            train_cmd = [
                sys.executable, str(self.train_script),
                '-s', str(colmap_path),
                '-m', str(output_dir),
                '--iterations', str(Config.TRAINING_ITERATIONS),
                '--eval'
            ]
            
            logger.info(f"开始训练模型: {' '.join(train_cmd)}")
            
            # 运行训练
            process = subprocess.Popen(
                train_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 监控训练进度
            training_log = []
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    logger.info(f"训练输出: {output.strip()}")
                    training_log.append(output.strip())
            
            process.wait()
            
            if process.returncode != 0:
                error_output = process.stderr.read()
                logger.error(f"训练失败: {error_output}")
                raise Exception(f"训练失败: {error_output}")
            
            # 查找生成的ply文件
            ply_files = list(output_dir.glob("**/*.ply"))
            if not ply_files:
                # 尝试默认位置
                ply_path = output_dir / "point_cloud" / "iteration_7000" / "point_cloud.ply"
                if not ply_path.exists():
                    ply_path = output_dir / "point_cloud.ply"
                    
                if not ply_path.exists():
                    raise Exception("找不到生成的PLY文件")
            else:
                # 使用最新的ply文件
                ply_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                ply_path = ply_files[0]
            
            logger.info(f"训练完成，PLY文件: {ply_path}")
            
            return {
                'success': True,
                'ply_path': str(ply_path),
                'output_dir': str(output_dir),
                'log': training_log[-10:],  # 返回最后10行日志
                'message': '模型训练完成'
            }
            
        except Exception as e:
            logger.error(f"训练失败: {str(e)}")
            return {
                'success': False,
                'message': f"训练失败: {str(e)}"
            }