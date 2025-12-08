import os
from pathlib import Path

class Config:
    # 基础配置
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"
    LOG_DIR = BASE_DIR / "logs"
    STATIC_DIR = BASE_DIR / "static"
    TEMPLATE_DIR = BASE_DIR / "templates"
    
    # 服务器配置
    HOST = "0.0.0.0"
    PORT = 8090
    VIEWER_PORT = 8091
    DEBUG = True
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}
    UPLOAD_CHUNK_SIZE = 8192
    
    # 路径配置
    GS_REPO_PATH = BASE_DIR / "gaussian-splatting"
    GS_TRAIN_SCRIPT = GS_REPO_PATH / "train.py" if GS_REPO_PATH.exists() else None
    WEB_3DGS_REPO_PATH = BASE_DIR / "web-3dgs"
    WEB_3DGS_SCRIPT = WEB_3DGS_REPO_PATH / "main.py" if WEB_3DGS_REPO_PATH.exists() else None
    
    # 训练配置
    TRAINING_ITERATIONS = 30000  # 演示时可以用较少的迭代次数
    
    # 用户会话配置
    SECRET_KEY = "your-secret-key-change-this"
    
    @classmethod
    def init_dirs(cls):
        """初始化必要的目录"""
        dirs = [cls.DATA_DIR, cls.LOG_DIR, cls.STATIC_DIR, cls.TEMPLATE_DIR]
        for dir_path in dirs:
            dir_path.mkdir(exist_ok=True)
    
    @classmethod
    def get_user_dir(cls, username):
        """获取用户目录"""
        user_dir = cls.DATA_DIR / username
        user_dir.mkdir(exist_ok=True)
        return user_dir
    
    @classmethod
    def get_video_dir(cls, username, filename):
        """获取视频文件目录"""
        video_dir = cls.get_user_dir(username) / filename
        video_dir.mkdir(exist_ok=True)
        return video_dir

config = Config()