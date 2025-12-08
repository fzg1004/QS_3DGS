import os
import shutil
import sys
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
import logging


# 添加父目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

logger = logging.getLogger(__name__)

class UploadHandler:
    """上传处理器"""
    
    def __init__(self):
        self.allowed_extensions = Config.ALLOWED_EXTENSIONS
        
    def allowed_file(self, filename):
        """检查文件扩展名"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def save_video(self, username, file):
        """保存视频文件"""
        try:
            if not self.allowed_file(file.filename):
                raise ValueError(f"不支持的文件类型，允许的类型: {self.allowed_extensions}")
            
            # 安全文件名
            original_filename = secure_filename(file.filename)
            filename_without_ext = Path(original_filename).stem
            extension = Path(original_filename).suffix
            
            # 创建用户目录
            user_dir = Config.get_user_dir(username)
            video_dir = user_dir / filename_without_ext
            video_dir.mkdir(exist_ok=True, parents=True)
            
            video_path = video_dir / f"input{extension}"
           
           # 4. 核心修复：Flask文件读取（关键！重置指针 + 正确保存）
            # 重置文件指针（避免中间件/前置操作读取过文件，导致指针到末尾）
            file.seek(0)
            # 方式1：直接用Flask的save方法（推荐，底层处理了流的问题）
            file.save(str(video_path))
            
            logger.info(f"视频文件保存到: {video_path}")
            
            return {
                'success': True,
                'video_path': str(video_path),
                'video_dir': str(video_dir),
                'filename': filename_without_ext,
                'original_filename': original_filename
            }
            
        except Exception as e:
            logger.error(f"保存视频失败: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def cleanup_user_data(self, username, days_old=7):
        """清理旧数据"""
        try:
            user_dir = Config.get_user_dir(username)
            if not user_dir.exists():
                return
            
            import time
            current_time = time.time()
            cutoff_time = current_time - (days_old * 24 * 60 * 60)
            
            for item in user_dir.iterdir():
                if item.is_dir():
                    # 检查目录最后修改时间
                    stat_info = item.stat()
                    if stat_info.st_mtime < cutoff_time:
                        shutil.rmtree(item)
                        logger.info(f"清理旧目录: {item}")
                        
        except Exception as e:
            logger.error(f"清理数据失败: {str(e)}")