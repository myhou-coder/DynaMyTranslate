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

# Load environment variables from .env file
# 获取项目根目录的路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 加载根目录下的 .env 文件
load_dotenv(os.path.join(ROOT_DIR, '.env'))

# 线程池配置
executor = ThreadPoolExecutor(max_workers=4)

# 创建Flask应用实例
app = Flask(__name__)

# CORS(app)  # 启用CORS（默认允许所有来源）
# 应改为更明确的配置（不要用通配符）
CORS(app,
     origins="http://localhost:3000",  # 明确指定前端地址
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],  # 显式声明允许的头部
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # 包含OPTIONS
     expose_headers=["Content-Disposition"]  # 按需暴露特殊头部
     )


# 配置数据库连接URI为SQLite数据库文件
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
# 禁用SQLAlchemy的修改跟踪功能
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# 设置文件上传的文件夹路径
app.config['UPLOAD_FOLDER'] = 'uploads'
# 增加处理后文件存储路径的配置
app.config['PROCESSED_FOLDER'] = 'processed_files'
app.config['CONFIG_SHORT'] = {
        "provider": "deepseek",
        "api_key": os.getenv('DEEPSEEK_API_KEY'),
        "modelname":"deepseek-chat",
        "maxtoken": 8192
    }
app.config['CONFIG_LONG'] = {
        "provider": "deepseek",
        "api_key": os.getenv('DEEPSEEK_API_KEY'),
        "modelname":"deepseek-chat",
        "maxtoken": 8192
    }
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

# 定义翻译任务数据库模型
class TranslationTask(db.Model):
    id = db.Column(db.String(36), primary_key=True)  # 任务ID，主键
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 用户ID，外键
    filename = db.Column(db.String(255))  # 文件名
    status = db.Column(db.String(20), default='pending')  # 任务状态，默认为'pending'
    progress = db.Column(db.Integer, default=0)  # 任务进度，默认为0
    download_url = db.Column(db.String(255))  # 下载链接
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
      
        user = User.query.filter_by(token=token).first()
        if not user:
            return jsonify({'success': False, 'error': '无效token', 'code': 401}), 401
      
        g.current_user = user
        return f(*args, **kwargs)
    return decorated

def process_task(task_id):
    """ 实际处理翻译任务的函数 """
    with app.app_context():
        task = TranslationTask.query.get(task_id)
        try:
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
            config_short = app.config.get('CONFIG_SHORT')  # 假设配置从 app.config 中获取
            config_long = app.config.get('CONFIG_LONG')    # 假设配置从 app.config 中获取
            # 调用 translate_one_pdf 函数进行翻译并生成 ZIP 文件
            translator.translate_one_pdf(original_file_path, output_dir, config_short, config_long)
            # 阶段3: 完成处理
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

    # 生成新token
    user.token = str(uuid.uuid4())
    db.session.commit()

    return jsonify({
        'success': True,
        'data': {'token': user.token}
    }), 200

# 文件上传接口
@app.route('/api/upload', methods=['POST'])
@token_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未上传文件', 'code': 400}), 400
  
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'success': False, 'error': '无效的PDF文件', 'code': 400}), 400
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
        status='pending'
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
    # 运行Flask应用，开启调试模式
    # app.run(host='0.0.0.0', port=5000, debug=True)
    # 运行Flask应用
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)