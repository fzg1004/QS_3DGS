from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_from_directory
from flask_cors import CORS
import logging
from pathlib import Path
import threading
import time
import json
import os

import pycolmap

from config import Config
from models.login import login_required, LoginHandler
from models.upload_handler import UploadHandler
from models.viewer import ViewerManager

# 初始化配置
Config.init_dirs()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_DIR / 'app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__, 
           static_folder=Config.STATIC_DIR,
           template_folder=Config.TEMPLATE_DIR)
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
CORS(app)

# 初始化管理器
login_handler = LoginHandler()
upload_handler = UploadHandler()
viewer_manager = ViewerManager()

# 存储任务状态
tasks = {}

class TaskStatus:
    """任务状态跟踪"""
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"

def update_task_status(task_id, status, message="", progress=0, result=None):
    """更新任务状态"""
    if task_id not in tasks:
        tasks[task_id] = {
            "status": status,
            "message": message,
            "progress": progress,
            "result": result,
            "created_at": time.time(),
            "updated_at": time.time()
        }
    else:
        tasks[task_id].update({
            "status": status,
            "message": message,
            "progress": progress,
            "result": result,
            "updated_at": time.time()
        })

@app.route('/')
def index():
    """首页"""
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'GET':
        return render_template('login.html')
    
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    # 简化登录验证（演示用）
    if username and password:
        session['username'] = username
        session['logged_in'] = True
        return jsonify({
            'success': True,
            'username': username,
            'message': '登录成功'
        })
    else:
        return jsonify({
            'success': False,
            'message': '用户名和密码不能为空'
        }), 401

@app.route('/logout')
def logout():
    """退出登录"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/upload', methods=['GET'])
@login_required
def upload_page():
    """上传页面"""
    username = session.get('username')
    return render_template('upload.html', username=username)

@app.route('/upload/video', methods=['POST'])
@login_required
def upload_video():
    """上传视频文件"""
    try:
        username = session.get('username')
        task_id = f"{username}_{int(time.time())}"
        
        # 检查文件
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'}), 400
        
        # 更新任务状态
        update_task_status(task_id, TaskStatus.UPLOADING, "开始上传文件...", 0)
        
        
        # 步骤1: 上传视频（在主线程中进行，避免file stream被关闭）
        update_task_status(task_id, TaskStatus.UPLOADING, "上传视频文件中...", 10)
        video_info = upload_handler.save_video(username, file)
        if not video_info['success']:
            logger.error(f"处理任务 {task_id} 出错: {video_info['message']}")
            update_task_status(task_id, TaskStatus.FAILED, f"保存失败: {video_info['message']}", 0)
            return jsonify({
                'success': False,
                'task_id': task_id,
                'message': video_info['message']
            }), 500
        
        
        
        # 异步处理生成COLMAP格式和训练
        thread = threading.Thread(
            target=process_colmap_and_train,
            args=(username, video_info, task_id)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '开始上传和处理'
        })
        
    except Exception as e:
        logger.error(f"上传错误: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

def process_colmap_and_train(username, video_info, task_id):
    """处理COLMAP格式生成和训练过程"""
    try:
        update_task_status(task_id, TaskStatus.UPLOADING, "视频文件上传完成...", 20)
            
        # 步骤1: 生成COLMAP数据
        update_task_status(task_id, TaskStatus.PROCESSING, "正在生成COLMAP格式数据...", 30)
        from models.colmap_generator import ColmapGenerator
        colmap_gen = ColmapGenerator()
        colmap_result = colmap_gen.generate_from_video(video_info['video_path'])
        
        if not colmap_result['success']:
            update_task_status(task_id, TaskStatus.FAILED, f"生成COLMAP数据失败: {colmap_result['message']}", 30)
            return
        
        update_task_status(task_id, TaskStatus.TRAINING, f"生成COLMAP数据成功，开始训练高斯溅射模型...", 50)
        
        
        # 步骤2: 训练模型
        from models.trainer import ModelTrainer
        trainer = ModelTrainer()
        training_result = trainer.train(colmap_result['colmap_path'])
        
        if not training_result['success']:
            update_task_status(task_id, TaskStatus.FAILED, f"模型训练失败: {training_result['message']}", 50)
            return
        
        # 步骤3: 完成
        update_task_status(task_id, TaskStatus.COMPLETED, 
                          "模型训练完成", 100,
                          {
                              'ply_path': training_result['ply_path'],
                              'username': username,
                              'filename': video_info['filename']
                          })
        
        logger.info(f"任务 {task_id} 完成: {training_result['ply_path']}")
        
    except Exception as e:
        logger.error(f"处理任务 {task_id} 出错: {str(e)}")
        update_task_status(task_id, TaskStatus.FAILED, f"处理失败: {str(e)}", 0)

@app.route('/task/status/<task_id>')
@login_required
def get_task_status(task_id):
    """获取任务状态"""
    task = tasks.get(task_id)
    if not task:
        return jsonify({
            'success': False,
            'message': '任务不存在'
        }), 404
    
    return jsonify({
        'success': True,
        'task': task
    })

@app.route('/viewer/<username>/<filename>')
@login_required
def viewer_page(username, filename):
    """查看器页面"""
    # 检查当前用户是否有权限访问
    current_user = session.get('username')
    if current_user != username:
        return jsonify({'success': False, 'message': '没有权限访问'}), 403
    
    ply_path = Config.DATA_DIR / username / filename / "output" / "point_cloud.ply"
    
    if not ply_path.exists():
        # 尝试其他可能的路径
        ply_path = Config.DATA_DIR / username / filename / "point_cloud.ply"
    
    if not ply_path.exists():
        return render_template('viewer.html', 
                             username=username,
                             filename=filename,
                             ply_exists=False,
                             message="PLY文件不存在")
    
    # 启动查看器
    viewer_url = viewer_manager.start_viewer(str(ply_path))
    
    return render_template('viewer.html',
                         username=username,
                         filename=filename,
                         ply_exists=True,
                         viewer_url=viewer_url)

@app.route('/api/viewer/start', methods=['POST'])
@login_required
def start_viewer():
    """启动查看器API"""
    data = request.get_json()
    ply_path = data.get('ply_path')
    
    if not ply_path or not Path(ply_path).exists():
        return jsonify({'success': False, 'message': 'PLY文件不存在'}), 404
    
    try:
        viewer_url = viewer_manager.start_viewer(ply_path)
        return jsonify({
            'success': True,
            'viewer_url': viewer_url,
            'message': '查看器启动成功'
        })
    except Exception as e:
        logger.error(f"启动查看器失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/viewer/stop')
@login_required
def stop_viewer():
    """停止查看器"""
    try:
        viewer_manager.stop_viewer()
        return jsonify({'success': True, 'message': '查看器已停止'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/tasks')
@login_required
def list_tasks():
    """列出用户的任务"""
    username = session.get('username')
    user_tasks = {tid: task for tid, task in tasks.items() 
                  if tid.startswith(f"{username}_")}
    
    return jsonify({
        'success': True,
        'tasks': user_tasks,
        'count': len(user_tasks)
    })

@app.route('/static/<path:filename>')
def static_files(filename):
    """静态文件服务"""
    return send_from_directory(Config.STATIC_DIR, filename)

@app.errorhandler(413)
def too_large(e):
    """文件太大错误处理"""
    return jsonify({'success': False, 'message': '文件太大'}), 413

if __name__ == '__main__':
    logger.info(f"启动服务器: {Config.HOST}:{Config.PORT}")
    
    print(pycolmap.__version__)
    
    
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
        threaded=True
    )
    