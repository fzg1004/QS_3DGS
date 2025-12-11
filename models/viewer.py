import subprocess
import sys
import time
import threading
from pathlib import Path
import logging
import signal
import os

from config import Config

logger = logging.getLogger(__name__)

class ViewerManager:
    """3D查看器管理器（适配web-3dgs conda环境+环境变量）"""
    
    def __init__(self):
        # 从Config加载核心配置
        self.web_3dgs_repo_path = Config.WEB_3DGS_REPO_PATH
        self.web_3dgs_script = Config.WEB_3DGS_MAIN_SCRIPT  # 修正为main.py
        self.conda_base = Config.CONDA_BASE  # /usr/local/anaconda3
        self.web_3dgs_env = Config.WEB_3DGS_ENV  # web_gs
        self.web_3dgs_exports = Config.WEB_3DGS_EXPORTS  # 环境变量配置
        
        self.viewer_process = None
        self.current_port = Config.VIEWER_PORT if hasattr(Config, 'VIEWER_PORT') else 8080
        self.host = Config.HOST if hasattr(Config, 'HOST') else "0.0.0.0"
        self.is_running = False
        self.viewer_log = []  # 存储查看器日志
    
    def _build_conda_command(self, cmd_list):
        """构建带conda激活+环境变量的完整bash命令（后台运行）"""
        # 1. 拼接环境变量export命令（值用单引号包裹避免解析错误）
        env_commands = [f"export {k}='{v}'" for k, v in self.web_3dgs_exports.items()]
        # 2. Conda激活命令（系统级conda）
        activate_cmd = f"source {self.conda_base}/etc/profile.d/conda.sh && conda activate {self.web_3dgs_env}"
        # 3. 切换到web-3dgs项目目录
        cd_cmd = f"cd {self.web_3dgs_repo_path}"
        # 4. 拼接基础命令 + 后台运行（nohup+&，避免进程阻塞）
        # 日志输出到项目目录的viser.log，方便排查
        base_cmd = " ".join(cmd_list)
        nohup_cmd = f"nohup {base_cmd} > viser.log 2>&1 &"
        
        # 组合完整命令（&& 保证前一步成功才执行后一步）
        full_cmd = " && ".join(env_commands + [activate_cmd, cd_cmd, nohup_cmd])
        return full_cmd
    
    def _get_pid_by_port(self, port):
        """根据端口查找进程PID（用于冲突检测）"""
        try:
            # Linux下查找占用端口的进程
            result = subprocess.run(
                f"lsof -i:{port} -t",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            pids = result.stdout.strip().split('\n')
            return [pid for pid in pids if pid.strip()]
        except Exception as e:
            logger.warning(f"检测端口占用失败: {e}")
            return []
    
    def start_viewer(self, ply_path):
        """启动3D查看器（适配conda环境+后台运行）"""
        try:
            # 1. 基础校验
            ply_path = Path(ply_path).absolute()
            if not ply_path.exists():
                raise ValueError(f"PLY文件不存在: {ply_path}")
            
            # 检查web-3dgs主脚本
            if not self.web_3dgs_script or not self.web_3dgs_script.exists():
                logger.error(f"web-3dgs主脚本不存在: {self.web_3dgs_script}")
                # 返回模拟URL
                return f"http://{self.host}:{self.current_port}/viewer?ply={ply_path.name}"
            
            # 2. 端口冲突检测 & 停止已有进程
            self.stop_viewer()
            port_pids = self._get_pid_by_port(self.current_port)
            if port_pids:
                logger.warning(f"端口{self.current_port}被占用(PID: {port_pids})，尝试终止...")
                for pid in port_pids:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        time.sleep(1)
                    except Exception as e:
                        logger.error(f"终止端口占用进程{pid}失败: {e}")
            
            # 3. 构建基础启动命令（web-3dgs的main.py）
            base_viewer_cmd = [
                "python", str(self.web_3dgs_script),  # 使用虚拟环境内的python
                '-s', str(ply_path),
                '--port', str(self.current_port),
                '--host', self.host
            ]
            
            # 4. 构建带conda激活和环境变量的完整命令
            full_viewer_cmd = self._build_conda_command(base_viewer_cmd)
            logger.info(f"启动3D查看器（conda环境）: {full_viewer_cmd}")
            
            # 5. 执行启动命令（shell=True执行bash命令）
            # 后台运行，不阻塞主线程
            subprocess.run(
                full_viewer_cmd,
                shell=True,
                cwd=self.web_3dgs_repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 6. 等待查看器启动（延长等待时间，确保服务加载完成）
            start_timeout = 10
            start_time = time.time()
            self.is_running = True
            
            # 轮询检查端口是否监听
            while time.time() - start_time < start_timeout:
                port_pids = self._get_pid_by_port(self.current_port)
                if port_pids:
                    self.viewer_process = port_pids[0]  # 记录主进程PID
                    logger.info(f"端口{self.current_port}已监听，查看器启动成功（PID: {self.viewer_process}）")
                    break
                time.sleep(1)
            else:
                raise TimeoutError(f"查看器启动超时（{start_timeout}秒），端口{self.current_port}未监听")
            
            # 7. 启动日志监控线程
            monitor_thread = threading.Thread(
                target=self._monitor_viewer_log,
                args=(self.web_3dgs_repo_path / "viser.log",)
            )
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # 8. 构造访问URL
            viewer_url = f"http://{self.host}:{self.current_port}"
            logger.info(f"查看器启动成功，访问地址: {viewer_url}")
            
            return viewer_url
            
        except Exception as e:
            error_msg = f"启动查看器失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.is_running = False
            # 返回模拟URL用于演示
            return f"http://{self.host}:{self.current_port}/demo-viewer?error={error_msg}"
    
    def stop_viewer(self):
        """停止查看器（兼容后台进程终止）"""
        try:
            # 1. 终止进程对象（如果存在）
            if self.viewer_process and isinstance(self.viewer_process, subprocess.Popen):
                self.viewer_process.terminate()
                self.viewer_process.wait(timeout=5)
            
            # 2. 根据端口终止残留进程
            port_pids = self._get_pid_by_port(self.current_port)
            if port_pids:
                logger.info(f"终止端口{self.current_port}的残留进程: {port_pids}")
                for pid in port_pids:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        time.sleep(1)
                        # 强制终止未退出的进程
                        os.kill(int(pid), signal.SIGKILL)
                    except ProcessLookupError:
                        continue
                    except Exception as e:
                        logger.error(f"终止进程{pid}失败: {e}")
            
            # 3. 清理状态
            self.is_running = False
            self.viewer_process = None
            self.viewer_log.clear()
            logger.info("查看器已停止（含残留进程清理）")
            
        except Exception as e:
            logger.error(f"停止查看器失败: {str(e)}")
    
    def _monitor_viewer_log(self, log_file):
        """监控查看器的nohup日志文件"""
        try:
            if not log_file.exists():
                # 创建空日志文件
                log_file.touch()
            
            # 实时读取日志（类似tail -f）
            with open(log_file, 'r', encoding='utf-8') as f:
                f.seek(0, 2)  # 移动到文件末尾
                while self.is_running:
                    line = f.readline()
                    if line:
                        line_strip = line.strip()
                        self.viewer_log.append(line_strip)
                        logger.debug(f"查看器日志: {line_strip}")
                    else:
                        time.sleep(0.5)
        except Exception as e:
            if self.is_running:  # 运行中报错才记录
                logger.error(f"监控查看器日志失败: {str(e)}")
    
    def get_status(self):
        """获取查看器状态（增强版）"""
        # 检查端口是否真的在运行
        is_port_running = bool(self._get_pid_by_port(self.current_port))
        self.is_running = is_port_running
        
        return {
            'is_running': self.is_running,
            'port': self.current_port if self.is_running else None,
            'url': f"http://{self.host}:{self.current_port}" if self.is_running else None,
            'pid': self.viewer_process if self.is_running else None,
            'last_logs': self.viewer_log[-10:] if self.viewer_log else []  # 返回最后10行日志
        }
    
    def __del__(self):
        """析构函数：确保进程终止"""
        self.stop_viewer()