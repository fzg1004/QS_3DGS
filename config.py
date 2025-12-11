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
    
    
    # ==================== Conda 环境基础配置 ====================
    # Conda根路径（可通过 `conda info --base` 命令获取）
    CONDA_BASE = Path("/usr/local/anaconda3")  # 替换为你的conda根目录
    # 方式2：自动获取（更通用，推荐）
    # CONDA_BASE = Path(os.popen("conda info --base").read().strip())
   
    # ==================== 高斯泼溅项目配置 ====================
    # 高斯泼溅项目仓库路径
    GAUSSIAN_REPO_PATH = Path("/home/fzg25/projects/gaussian-splatting")
    #虚拟环境名
    GAUSSIAN_ENV = "gaussian-splatting"
    #环境变量
    GAUSSIAN_EXPORTS = {
        "CUDA_HOME" : "$CONDA_PREFIX",
        "PATH" : "$CUDA_HOME/bin:$PATH",
        "TORCH_CUDA_ARCH_LIST" :"7.0",
        "CC": "$CONDA_PREFIX/bin/gcc",
        "CXX" : "$CONDA_PREFIX/bin/g++",
        "LD_LIBRARY_PATH" : (
            "$CONDA_PREFIX/lib/python3.8/site-packages/torch/lib:"
            "/usr/lib/x86_64-linux-gnu:"	
            "$CUDA_HOME/lib:"
            "$CUDA_HOME/lib64"       
        )
    }
    
    GAUSSIAN_TRAIN_SCRIPT = GAUSSIAN_REPO_PATH / "train.py" if GAUSSIAN_REPO_PATH.exists() else None
     # 训练参数配置
    GAUSSIAN_TRAINING_ARGS = {
        "iterations": 30000,  # 训练迭代数
    }

    
    # ==================== web-dgs项目配置 ====================
    # web-3dgs项目仓库路径
    WEB_3DGS_REPO_PATH = Path("/home/fzg25/projects/web-3dgs")
    #虚拟环境名
    WEB_3DGS_ENV = "web_gs"
    #环境变量
    WEB_3DGS_EXPORTS = {
        "CUDA_HOME" : "/usr/local/cuda-11.8",
        "PATH" : "$CONDA_PREFIX/bin:$PATH",
        "TORCH_CUDA_ARCH_LIST" :"7.0",
        "CC": "/usr/bin/gcc",
        "CXX" : "/usr/bin/g++",
        "LD_LIBRARY_PATH" : (
            "$CUDA_HOME/lib64:"
            "$CONDA_PREFIX/lib/python3.10/site-packages/torch/lib:"
            "/usr/lib/x86_64-gnu:"
            "$CONDA_PREFIX/lib:"
            "$CONDA_PREFIX/lib64"
            
        ),
        "TORCH_CXX11_ABI" : "0",
        "CFLAGS" : "-D_GLIBCXX_USE_CXX11_ABI=0 $CFLAGS",	
        "CXXFLAGS" : "-D_GLIBCXX_USE_CXX11_ABI=0 $CXXFLAGS"
    }
    WEB_3DGS_TRAIN_SCRIPT = WEB_3DGS_REPO_PATH / "main.py" if WEB_3DGS_REPO_PATH.exists() else None

   
    
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