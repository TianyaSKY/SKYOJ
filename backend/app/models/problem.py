from app.models.user import db


class Problem(db.Model):
    __tablename__ = 'problems'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)  # Markdown 格式的题目描述

    # 题目类型：acm (标准IO), oop (单元测试), kaggle (CSV评分)
    type = db.Column(db.Enum('acm', 'oop', 'kaggle'), nullable=False)
    language = db.Column(db.Enum('python', 'java', 'c', 'cpp'), nullable=False)

    # 评测限制
    time_limit = db.Column(db.Integer, default=1000)  # 单位：ms
    memory_limit = db.Column(db.Integer, default=128)  # 单位：mb

    # 存储路径与模板
    test_case_path = db.Column(db.String(500))  # 存放测试用例或正确答案 CSV 的路径
    template_code = db.Column(db.Text)  # OOP 模式下的类/函数模板

    created_at = db.Column(db.DateTime, default=db.func.now())

    def __repr__(self):
        return f'<Problem {self.title}>'
