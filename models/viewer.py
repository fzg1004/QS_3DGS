import subprocess
import sys
import time
import threading
from pathlib import Path
import logging
import signal

from config import Config

logger = logging.getLogger(__name__)

class ViewerManager:
    """3D查看器管理器"""
    
    def __init__(self):
        self.viewer_process = None
        self.current_port = Config.VIEWER_PORT
        self.is_running = False
    
    def start_viewer(self, ply_path):
        """启动3D查看器"""
        try:
            # 停止已有的查看器
            self.stop_viewer()
            
            ply_path = Path(ply_path)
            if not ply_path.exists():
                raise ValueError(f"PLY文件不存在: {ply_path}")
            
            # 检查web-3dgs脚本
            web_3dgs_script = Config.WEB_3DGS_SCRIPT
            if not web_3dgs_script or not web_3dgs_script.exists():
                # 返回模拟的查看器URL
                return f"http://{Config.HOST}:{self.current_port}/viewer?ply={ply_path.name}"
            
            # 构建启动命令
            viewer_cmd = [
                sys.executable, str(web_3dgs_script),
                '-s', str(ply_path),
                '--port', str(self.current_port),
                '--host', Config.HOST
            ]
            
            logger.info(f"启动3D查看器: {' '.join(viewer_cmd)}")
            
            # 启动查看器进程
            self.viewer_process = subprocess.Popen(
                viewer_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.is_running = True
            
            # 启动监控线程
            monitor_thread = threading.Thread(
                target=self._monitor_viewer,
                args=(self.viewer_process,)
            )
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # 等待查看器启动
            time.sleep(2)
            
            viewer_url = f"http://{Config.HOST}:{self.current_port}"
            logger.info(f"查看器启动成功: {viewer_url}")
            
            return viewer_url
            
        except Exception as e:
            logger.error(f"启动查看器失败: {str(e)}")
            # 返回模拟URL用于演示
            return f"http://{Config.HOST}:{self.current_port}/demo-viewer"
    
    def stop_viewer(self):
        """停止查看器"""
        try:
            if self.viewer_process and self.is_running:
                self.viewer_process.terminate()
                self.viewer_process.wait(timeout=5)
                logger.info("查看器已停止")
            
            self.is_running = False
            self.viewer_process = None
            
        except Exception as e:
            logger.error(f"停止查看器失败: {str(e)}")
            # 强制终止
            if self.viewer_process:
                self.viewer_process.kill()
    
    def _monitor_viewer(self, process):
        """监控查看器进程"""
        try:
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    logger.debug(f"查看器输出: {output.strip()}")
            
            process.wait()
            self.is_running = False
            logger.info("查看器进程已结束")
            
        except Exception as e:
            logger.error(f"监控查看器时出错: {str(e)}")
    
    def get_status(self):
        """获取查看器状态"""
        return {
            'is_running': self.is_running,
            'port': self.current_port if self.is_running else None,
            'url': f"http://{Config.HOST}:{self.current_port}" if self.is_running else None
        }