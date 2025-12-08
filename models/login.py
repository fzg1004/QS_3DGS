from functools import wraps
from flask import session, redirect, url_for, jsonify

def login_required(f):
    """登录装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': '需要登录'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

class LoginHandler:
    """登录处理器"""
    
    def __init__(self):
        self.users = {}  # 演示用，实际应该使用数据库
        
    def authenticate(self, username, password):
        """验证用户（演示用）"""
        # 这里简化验证，实际应该使用数据库和安全哈希
        if username and password:
            return True
        return False
    
    def register_user(self, username, password):
        """注册用户（演示用）"""
        if username in self.users:
            return False
        self.users[username] = password
        return True