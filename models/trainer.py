import subprocess
import sys
import json
from pathlib import Path
import logging
import time
import os

# 导入你的Config配置（确保Config里包含修正后的conda和环境配置）
from config import Config

logger = logging.getLogger(__name__)

class ModelTrainer:
    """高斯溅射模型训练器（适配conda虚拟环境+环境变量）"""
    
    def __init__(self):
        # 从Config加载核心配置
        self.gs_repo_path = Config.GAUSSIAN_REPO_PATH  # 修正配置名（对应之前的GAUSSIAN_REPO_PATH）
        self.train_script = Config.GAUSSIAN_TRAIN_SCRIPT  # 修正配置名
        self.conda_base = Config.CONDA_BASE  # conda根目录 /usr/local/anaconda3
        self.gs_env = Config.GAUSSIAN_ENV  # 虚拟环境名 gaussian-splatting
        self.gs_exports = Config.GAUSSIAN_EXPORTS  # 环境变量配置
        self.train_iterations = Config.GAUSSIAN_TRAINING_ARGS["iterations"]  # 30000迭代数

    def _build_conda_command(self, cmd_list):
        """构建带conda激活+环境变量的完整命令"""
        # 1. 拼接环境变量export命令
        env_commands = [f"export {k}='{v}'" for k, v in self.gs_exports.items()]
        # 2. Conda激活命令（系统级conda）
        activate_cmd = f"source {self.conda_base}/etc/profile.d/conda.sh && conda activate {self.gs_env}"
        # 3. 切换到项目目录
        cd_cmd = f"cd {self.gs_repo_path}"
        # 4. 拼接最终命令（用&&保证前一步成功才执行后一步）
        full_cmd = " && ".join(env_commands + [activate_cmd, cd_cmd] + [" ".join(cmd_list)])
        return full_cmd

    def train(self, colmap_path, output_dir=None):
        """训练高斯溅射模型（适配conda环境+环境变量）"""
        try:
            # 校验输入路径
            colmap_path = Path(colmap_path).absolute()
            if not colmap_path.exists():
                raise ValueError(f"COLMAP路径不存在: {colmap_path}")
            
            # 确定输出目录
            if output_dir is None:
                output_dir = colmap_path.parent / "output"
            output_dir = Path(output_dir).absolute()
            output_dir.mkdir(exist_ok=True)
            
            # 检查训练脚本是否存在
            if not self.train_script or not self.train_script.exists():
                return {
                    'success': False,
                    'message': f'训练脚本不存在: {self.train_script}'
                }
            
            # 构建基础训练命令（仅python+参数，无环境激活）
            base_train_cmd = [
                "python", str(self.train_script),  # 用虚拟环境内的python，而非sys.executable
                '-s', str(colmap_path),
                '-m', str(output_dir),
                '--iterations', str(self.train_iterations),
                '--eval'
            ]
            
            # 构建带conda激活和环境变量的完整命令
            full_train_cmd = self._build_conda_command(base_train_cmd)
            logger.info(f"开始训练模型（conda环境）: {full_train_cmd}")
            
            # 运行训练（必须用shell=True执行bash命令）
            process = subprocess.Popen(
                full_train_cmd,
                shell=True,  # 关键：执行bash命令（conda激活需要）
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 将stderr重定向到stdout，统一捕获
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=self.gs_repo_path,  # 工作目录设为高斯溅射项目根目录
                env=os.environ.copy()  # 继承当前环境变量
            )
            
            # 实时监控训练输出
            training_log = []
            start_time = time.time()
            logger.info(f"训练启动，输出目录: {output_dir}")
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    output_strip = output.strip()
                    training_log.append(output_strip)
                    logger.info(f"训练日志 [{time.strftime('%H:%M:%S')}]: {output_strip}")
            
            # 等待进程结束并获取返回码
            return_code = process.wait()
            elapsed_time = time.time() - start_time
            logger.info(f"训练进程结束，返回码: {return_code}，耗时: {elapsed_time:.2f}秒")
            
            # 检查训练是否成功
            if return_code != 0:
                error_msg = f"训练进程返回非0码: {return_code}，最后10行日志: {training_log[-10:]}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # 查找生成的PLY文件（适配30000迭代数的默认路径）
            ply_path = None
            # 优先找指定迭代数的路径
            target_iter_dir = output_dir / "point_cloud" / f"iteration_{self.train_iterations}"
            target_ply = target_iter_dir / "point_cloud.ply"
            if target_ply.exists():
                ply_path = target_ply
            else:
                # 降级查找7000迭代数（兼容默认配置）
                fallback_ply = output_dir / "point_cloud" / "iteration_7000" / "point_cloud.ply"
                if fallback_ply.exists():
                    ply_path = fallback_ply
                    logger.warning(f"未找到{self.train_iterations}迭代的PLY，使用7000迭代版本: {ply_path}")
                else:
                    # 全局查找所有PLY文件
                    ply_files = list(output_dir.glob("**/*.ply"))
                    if ply_files:
                        # 按修改时间排序，取最新的
                        ply_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                        ply_path = ply_files[0]
                        logger.info(f"找到PLY文件（全局查找）: {ply_path}")
                    else:
                        raise Exception(f"在输出目录未找到PLY文件: {output_dir}")
            
            # 最终校验PLY文件
            if not ply_path or not ply_path.exists():
                raise Exception(f"PLY文件不存在: {ply_path}")
            
            logger.info(f"训练完成！PLY文件路径: {ply_path}，总耗时: {elapsed_time:.2f}秒")
            
            return {
                'success': True,
                'ply_path': str(ply_path.absolute()),
                'output_dir': str(output_dir.absolute()),
                'log': training_log[-10:],  # 返回最后10行日志
                'elapsed_time': round(elapsed_time, 2),
                'message': f'模型训练完成（{self.train_iterations}迭代），耗时{elapsed_time:.2f}秒'
            }
            
        except Exception as e:
            error_msg = f"训练失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'message': error_msg,
                'log': training_log[-10:] if 'training_log' in locals() else []
            }