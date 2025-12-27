import os
import time
import threading

from flask import Flask
from sqlalchemy.exc import OperationalError

from app.api.auth import auth_bp
from app.api.dataset import dataset_bp
from app.api.exam import exam_bp
from app.api.llm import llm_bp
from app.api.problem import problem_bp
from app.api.submission import submission_bp
from app.api.sys_dict import sys_dict_bp
from app.api.user import user_bp
from app.api.search import search_bp
from app.api.plagiarism import plagiarism_bp
from app.models.sysdict import SysDict
from app.models.user import db
from app.utils.sys_dict import sys_dict_kv

# 导入服务以进行初始化
from app.services.search_service import search_service
from app.services.plagiarism_service import plagiarism_service

if os.path.exists('/.dockerenv'):
    db_host = 'mysql'
else:
    db_host = '127.0.0.1'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://root:root@{db_host}:3306/oj_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'TianyaSKY'

db.init_app(app)


def init_db():
    """尝试连接数据库并创建表，带有重试机制"""
    with app.app_context():
        retries = 5
        while retries > 0:
            try:
                db.create_all()
                print("Successfully connected to MySQL and created tables!")

                # 初始化系统字典
                if SysDict.query.count() == 0:
                    for key, val in sys_dict_kv.items():
                        new_dict = SysDict(key=key, val=str(val))
                        db.session.add(new_dict)
                    db.session.commit()
                    print("Initialized SysDict from sys_dict_kv.")
                return
            except OperationalError:
                retries -= 1
                print(f"Waiting for MySQL... ({5 - retries}/5)")
                time.sleep(3)  # 等待3秒再试
        print("Could not connect to MySQL after several retries.")


def init_services():
    """初始化搜索索引和查重模型"""
    print("Initializing services (Search Index & Plagiarism Model)...")
    try:
        # 加载查重模型
        plagiarism_service._ensure_model_loaded()
        
        # 建立搜索索引
        with app.app_context():
            search_service.rebuild_index()
            
        print("Services initialized successfully.")
    except Exception as e:
        print(f"Error initializing services: {e}")


# 初始化数据库
init_db()

# 异步初始化服务，避免阻塞启动
threading.Thread(target=init_services).start()


@app.route('/')
def hello():
    return {"status": "SKYOJ Backend is ready!"}


app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(problem_bp, url_prefix='/api/problems')
app.register_blueprint(submission_bp, url_prefix='/api/submissions')
app.register_blueprint(user_bp, url_prefix='/api/user')
app.register_blueprint(dataset_bp, url_prefix='/api/datasets')
app.register_blueprint(sys_dict_bp, url_prefix='/api/sys')
app.register_blueprint(exam_bp, url_prefix='/api/exams')
app.register_blueprint(llm_bp, url_prefix='/api/llm')
app.register_blueprint(search_bp, url_prefix='/api/search')
app.register_blueprint(plagiarism_bp, url_prefix='/api/plagiarism')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
