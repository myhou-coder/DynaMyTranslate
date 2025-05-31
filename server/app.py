from flask import Flask, request, jsonify, g, send_file, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import time
import uuid
import os
import shutil
from functools import wraps
from flask_cors import CORS
from werkzeug.utils import secure_filename
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
import en_pdf_to_zh_markdown as translator
from dotenv import load_dotenv
import json

# Load environment variables from .env file
# 获取项目根目录的路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 加载根目录下的 .env 文件
load_dotenv(os.path.join(ROOT_DIR, '.env'))

# 线程池配置
executor = ThreadPoolExecutor(max_workers=4)

# 加载配置文件
def load_config():
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        # 默认配置
        return {
            "backend_host": "0.0.0.0",
            "backend_port": 5000,
            "frontend_port": 3000,
            "tailscale_ip": "100.88.126.48"
        }

config = load_config()
tailscale_ip = config.get('tailscale_ip', '100.88.126.48')
frontend_port = config.get('frontend_port', 3000)

# 创建Flask应用实例
app = Flask(__name__)

# 配置CORS支持多地址访问
allowed_origins = [
    "http://localhost:3000",
    f"http://127.0.0.1:{frontend_port}",
    f"http://{tailscale_ip}:{frontend_port}"
]

CORS(app,
     origins=allowed_origins,  # 支持本机和Tailscale IP访问
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     expose_headers=["Content-Disposition"]
     )

# 配置数据库连接URI为SQLite数据库文件
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
# 禁用SQLAlchemy的修改跟踪功能
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# 设置文件上传的文件夹路径
app.config['UPLOAD_FOLDER'] = 'uploads'
# 增加处理后文件存储路径的配置
app.config['PROCESSED_FOLDER'] = 'processed_files'
# 生成一个随机的密钥用于会话管理
app.secret_key = os.urandom(24)

# 初始化SQLAlchemy数据库实例
db = SQLAlchemy(app)

# 定义用户数据库模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # 用户ID，主键
    email = db.Column(db.String(120), unique=True, nullable=False)  # 用户邮箱，唯一且不能为空
    password_hash = db.Column(db.String(128))  # 用户密码的哈希值
    token = db.Column(db.String(36))  # 用户认证token

# 定义用户API配置数据库模型
class UserApiConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # 配置ID，主键
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)  # 用户ID，外键，唯一
    deepseek_api_key = db.Column(db.String(255))  # DeepSeek API密钥
    # 添加默认语言设置
    default_source_language = db.Column(db.String(10), default='en')  # 默认原文语言
    default_target_language = db.Column(db.String(10), default='zh-CN')  # 默认目标语言
    created_at = db.Column(db.DateTime, server_default=db.func.now())  # 创建时间
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())  # 更新时间

# 定义翻译任务数据库模型
class TranslationTask(db.Model):
    id = db.Column(db.String(36), primary_key=True)  # 任务ID，主键
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 用户ID，外键
    filename = db.Column(db.String(255))  # 文件名
    status = db.Column(db.String(20), default='pending')  # 任务状态，默认为'pending'
    progress = db.Column(db.Integer, default=0)  # 任务进度，默认为0
    download_url = db.Column(db.String(255))  # 下载链接
    # 添加语言设置
    source_language = db.Column(db.String(10), default='en')  # 原文语言
    target_language = db.Column(db.String(10), default='zh-CN')  # 目标语言
    created_at = db.Column(db.DateTime, server_default=db.func.now())  # 任务创建时间，默认为当前时间

# 在应用上下文中创建数据库表
with app.app_context():
    db.create_all()

# 辅助函数，检查文件扩展名是否为PDF
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

# Token验证装饰器，用于保护需要认证的路由
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        if not token:
            return jsonify({'success': False, 'error': '未提供token', 'code': 401}), 401
      
        # 查找拥有该token的用户（支持多token）
        users = User.query.all()
        current_user = None
        for user in users:
            if user.token:
                # 支持多个token，用逗号分隔
                user_tokens = [t.strip() for t in user.token.split(',') if t.strip()]
                if token in user_tokens:
                    current_user = user
                    break
        
        if not current_user:
            return jsonify({'success': False, 'error': '无效token', 'code': 401}), 401
      
        g.current_user = current_user
        g.current_token = token
        return f(*args, **kwargs)
    return decorated

def process_task(task_id):
    """ 实际处理翻译任务的函数 """
    with app.app_context():
        task = TranslationTask.query.get(task_id)
        try:
            # 获取用户的API配置
            user_config = UserApiConfig.query.filter_by(user_id=task.user_id).first()
            
            if not user_config or not user_config.deepseek_api_key:
                # 如果用户没有配置API Key，任务失败
                task.status = 'failed'
                db.session.commit()
                print(f"Task {task_id} failed: 用户未配置API Key")
                return
                
            # 阶段1: 文件转换
            task.status = 'converting'
            task.progress = 30
            db.session.commit()
            print(f"Converting file {task.filename}")
            time.sleep(2)  # 模拟耗时操作
            # 阶段2: 翻译处理
            task.status = 'translating'
            task.progress = 60
            db.session.commit()
            print(f"Translating file {task.filename}")
            # 调用 translate_pdf_to_zh 函数进行翻译
            original_file_path = os.path.join(app.config['UPLOAD_FOLDER'], task.filename)
            output_dir = app.config['PROCESSED_FOLDER']
            
            # 使用用户自定义的API Key创建配置
            config_short = {
                "provider": "deepseek",
                "api_key": user_config.deepseek_api_key,
                "modelname": "deepseek-chat",
                "maxtoken": 8192
            }
            config_long = {
                "provider": "deepseek",
                "api_key": user_config.deepseek_api_key,
                "modelname": "deepseek-chat",
                "maxtoken": 8192
            }
            
            # 调用 translate_one_pdf 函数进行翻译并生成 ZIP 文件，传递语言设置
            translator.translate_one_pdf(
                original_file_path, 
                output_dir, 
                config_short, 
                config_long,
                source_language=task.source_language,
                target_language=task.target_language
            )
            
            # 阶段3: 标题修复
            task.status = 'fixing_headers'
            task.progress = 80
            db.session.commit()
            print(f"Fixing markdown headers for {task.filename}")
            
            # 阶段4: 完成处理
            task.status = 'success'
            task.progress = 100
            # 获取生成的 ZIP 文件路径
            filename_without_ext = os.path.splitext(task.filename)[0]
            original_zip_path = os.path.join(output_dir, f"{filename_without_ext}.zip")
            # 将 ZIP 文件重命名为 task_id 命名
            new_zip_name = f"{task_id}.zip"
            new_zip_path = os.path.join(output_dir, new_zip_name)
            shutil.move(original_zip_path, new_zip_path)
            # 设置下载 URL
            task.download_url = f'/api/download/{task.id}'
            db.session.commit()
            print(f"Task {task_id} completed")
        except Exception as e:
            print(f"Task {task_id} failed: {str(e)}")
            task.status = 'failed'
            db.session.commit()
def background_checker():
    """ 后台任务检查线程 """
    while True:
        with app.app_context():
            try:
                with db.session.begin():
                    # 原子化获取并锁定任务
                    task = TranslationTask.query.filter_by(status='pending').with_for_update(skip_locked=True).first()
                    if task:
                        task.status = 'processing'
                        print(f"Processing task {task.id}")
                        # 提交任务到线程池
                        executor.submit(process_task, task.id)
            except Exception as e:
                print(f"Background checker error: {str(e)}")
            time.sleep(10)


# 用户注册接口
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'success': False, 'error': '邮箱和密码不能为空', 'code': 400}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': '该邮箱已注册', 'code': 409}), 409

    hashed_pw = generate_password_hash(password)
    new_user = User(email=email, password_hash=hashed_pw)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'success': True}), 200

# 用户登录接口
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()

    if not user or not check_password_hash(user.password_hash, data.get('password')):
        return jsonify({'success': False, 'error': '认证失败', 'code': 401}), 401

    # 生成新token并添加到现有token列表中
    new_token = str(uuid.uuid4())
    
    if user.token:
        # 获取现有token列表，限制最多保留5个活跃token
        existing_tokens = [t.strip() for t in user.token.split(',') if t.strip()]
        existing_tokens.append(new_token)
        # 只保留最新的5个token
        if len(existing_tokens) > 5:
            existing_tokens = existing_tokens[-5:]
        user.token = ','.join(existing_tokens)
    else:
        user.token = new_token
    
    db.session.commit()

    return jsonify({
        'success': True,
        'data': {'token': new_token}
    }), 200

# 用户登出接口
@app.route('/api/logout', methods=['POST'])
@token_required
def logout():
    """用户登出接口，移除当前token"""
    try:
        # 从token列表中移除当前token
        if g.current_user.token:
            existing_tokens = [t.strip() for t in g.current_user.token.split(',') if t.strip()]
            if g.current_token in existing_tokens:
                existing_tokens.remove(g.current_token)
            
            # 更新token列表
            if existing_tokens:
                g.current_user.token = ','.join(existing_tokens)
            else:
                g.current_user.token = None
                
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '登出成功'
        }), 200
    except Exception as e:
        print(f"Logout error: {str(e)}")
        return jsonify({
            'success': False,
            'error': '登出失败'
        }), 500

# 获取用户API配置接口
@app.route('/api/config', methods=['GET'])
@token_required
def get_api_config():
    """获取当前用户的API配置"""
    config = UserApiConfig.query.filter_by(user_id=g.current_user.id).first()
    
    if config:
        return jsonify({
            'success': True,
            'data': {
                'deepseek_api_key': config.deepseek_api_key or "",
                'default_source_language': config.default_source_language or "",
                'default_target_language': config.default_target_language or ""
            }
        }), 200
    else:
        # 如果用户还没有配置，返回空配置
        return jsonify({
            'success': True,
            'data': {
                'deepseek_api_key': "",
                'default_source_language': "",
                'default_target_language': ""
            }
        }), 200

# 更新用户API配置接口
@app.route('/api/config', methods=['POST'])
@token_required
def update_api_config():
    """更新当前用户的API配置"""
    data = request.get_json()
    deepseek_api_key = data.get('deepseek_api_key', '').strip()
    default_source_language = data.get('default_source_language', '').strip()
    default_target_language = data.get('default_target_language', '').strip()
    
    if not deepseek_api_key:
        return jsonify({'success': False, 'error': 'DeepSeek API Key不能为空', 'code': 400}), 400
    
    # 查找现有配置
    config = UserApiConfig.query.filter_by(user_id=g.current_user.id).first()
    
    if config:
        # 更新现有配置
        config.deepseek_api_key = deepseek_api_key
        config.default_source_language = default_source_language
        config.default_target_language = default_target_language
        config.updated_at = db.func.now()
    else:
        # 创建新配置
        config = UserApiConfig(
            user_id=g.current_user.id,
            deepseek_api_key=deepseek_api_key,
            default_source_language=default_source_language,
            default_target_language=default_target_language
        )
        db.session.add(config)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'API配置已更新'
    }), 200

# 文件上传接口
@app.route('/api/upload', methods=['POST'])
@token_required
def upload_file():
    # 检查用户是否已配置API Key
    user_config = UserApiConfig.query.filter_by(user_id=g.current_user.id).first()
    if not user_config or not user_config.deepseek_api_key:
        return jsonify({'success': False, 'error': '请先配置DeepSeek API Key', 'code': 400}), 400
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未上传文件', 'code': 400}), 400
  
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'success': False, 'error': '无效的PDF文件', 'code': 400}), 400
    
    # 获取语言设置参数
    source_language = request.form.get('sourceLanguage', user_config.default_source_language or 'en')
    target_language = request.form.get('targetLanguage', user_config.default_target_language or 'zh-CN')
    
    # 确保文件名安全
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # 保存文件到本地
    file.save(file_path)
    # 创建翻译任务
    task_id = str(uuid.uuid4())
    new_task = TranslationTask(
        id=task_id,
        user_id=g.current_user.id,
        filename=filename,
        status='pending',
        source_language=source_language,
        target_language=target_language
    )
    db.session.add(new_task)
    db.session.commit()
    return jsonify({
        'success': True,
        'data': {'taskId': task_id}
    }), 202


@app.route('/api/download/<string:task_id>', methods=['GET'])
@token_required
def download_file(task_id):
    """
    文件下载接口
    参数：
        path: 文件路径参数（需包含在安全路径中）
    响应: 文件下载流或错误信息
    """
    task = TranslationTask.query.get_or_404(task_id)
    print(f"Download request for task: {task}")  # 添加日志
    # 确保当前用户有权限访问该文件
    if task.user_id != g.current_user.id:
        return jsonify({'success': False, 'error': '无权访问该文件', 'code': 403}), 403
    
    # 构建文件路径
    filename = f"{task_id}.zip"
    file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    
    # 验证文件存在性
    if not os.path.exists(file_path):
        return jsonify({'success': False, 'error': '文件不存在', 'code': 404}), 404
    
    # 设置下载文件名（可选）
    name = os.path.basename(task.filename)
    name_without_ext = os.path.splitext(name)[0]
    download_name = f"{name_without_ext}.zip"
    
    # return send_from_directory(
    #     directory=app.config['PROCESSED_FOLDER'],
    #     path=filename,
    #     as_attachment=True,
    #     download_name=download_name
    # )
    return send_file(file_path, as_attachment=True, download_name=download_name)


# 进度查询接口
@app.route('/api/progress', methods=['GET'])
@token_required
def get_progress():
    task_id = request.args.get('taskId')
    task = TranslationTask.query.get(task_id)

    if not task or task.user_id != g.current_user.id:
        return jsonify({'success': False, 'error': '任务不存在', 'code': 404}), 404
    print(task.status)
    return jsonify({
        'success': True,
        'data': {
            'status': task.status,
            'progress': task.progress,
            'downloadUrl': task.download_url
        }
    })

# 历史记录接口
@app.route('/api/history', methods=['GET'])
@token_required
def get_history():
    tasks = TranslationTask.query.filter_by(user_id=g.current_user.id).all()
  
    history = [{
        'id': task.id,
        'filename': task.filename,
        'status': task.status,
        'progress': task.progress,
        'sourceLanguage': task.source_language,
        'targetLanguage': task.target_language,
        'translatedLang': task.target_language,  # 保持兼容性
        'createdAt': task.created_at.isoformat(),
        'downloadUrl': task.download_url
    } for task in tasks]

    return jsonify({'success': True, 'data': history})

# 删除历史记录接口
@app.route('/api/history/<task_id>', methods=['DELETE'])
@token_required
def delete_history(task_id):
    task = TranslationTask.query.get(task_id)
  
    if not task or task.user_id != g.current_user.id:
        return jsonify({'success': False, 'error': '未找到记录', 'code': 404}), 404
  
    # 删除上传的文件
    upload_file_path = os.path.join(app.config['UPLOAD_FOLDER'], task.filename)
    if os.path.exists(upload_file_path):
        os.remove(upload_file_path)
  
    # 删除处理后的文件
    processed_file_path = os.path.join(app.config['PROCESSED_FOLDER'], f"{task.id}.zip")
    if os.path.exists(processed_file_path):
        os.remove(processed_file_path)
  
    # 删除数据库记录
    db.session.delete(task)
    db.session.commit()
  
    return jsonify({'success': True})

# 获取用户活跃会话接口
@app.route('/api/sessions', methods=['GET'])
@token_required
def get_user_sessions():
    """获取当前用户的活跃会话列表"""
    if not g.current_user.token:
        return jsonify({'success': True, 'data': []}), 200
    
    tokens = [t.strip() for t in g.current_user.token.split(',') if t.strip()]
    sessions = []
    
    for i, token in enumerate(tokens):
        sessions.append({
            'id': i + 1,
            'token': token[:8] + "...",  # 只显示前8位
            'is_current': token == g.current_token,
            'created_at': 'Unknown'  # 简化版本不存储创建时间
        })
    
    return jsonify({
        'success': True,
        'data': sessions
    }), 200

# 撤销所有其他会话接口
@app.route('/api/sessions/revoke-others', methods=['POST'])
@token_required
def revoke_other_sessions():
    """撤销除当前会话外的所有其他会话"""
    if not g.current_user.token:
        return jsonify({'success': True, 'message': '没有其他会话需要撤销'}), 200
    
    # 只保留当前token
    g.current_user.token = g.current_token
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '已撤销所有其他会话'
    }), 200

# 主程序入口
if __name__ == '__main__':
    # 如果上传文件夹不存在，则创建它
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    # 在处理完成阶段添加文件生成逻辑
    if not os.path.exists(app.config['PROCESSED_FOLDER']):
        os.makedirs(app.config['PROCESSED_FOLDER'])
    # 启动后台线程
    checker_thread = Thread(target=background_checker, daemon=True)
    checker_thread.start()
    
    # 从配置文件读取启动参数
    host = config.get('backend_host', '0.0.0.0')
    port = config.get('backend_port', 5000)
    
    print(f"🚀 后端服务启动中...")
    print(f"📍 地址: {host}:{port}")
    print(f"🌐 支持的访问地址:")
    print(f"   - http://localhost:{port}")
    print(f"   - http://127.0.0.1:{port}")
    print(f"   - http://{tailscale_ip}:{port}")
    print(f"🔗 前端CORS允许地址: {allowed_origins}")
    
    # 运行Flask应用
    from waitress import serve
    serve(app, host=host, port=port)