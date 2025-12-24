from datetime import datetime

from app.models.user import db


class Submission(db.Model):
    __tablename__ = 'submissions'

    id = db.Column(db.Integer, primary_key=True)

    # 外键关联：关联到用户和题目
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    problem_id = db.Column(db.Integer, db.ForeignKey('problems.id', ondelete='CASCADE'), nullable=False)
    
    # 考试关联
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=True)

    # 提交的具体内容
    code_path = db.Column(db.String(500))  # 存放代码文件或 CSV 文件的路径
    code_content = db.Column(db.Text)  # 用户提交的代码文本
    language = db.Column(db.String(50))  # 如: python, cpp, csv

    # 判题结果
    # 'Pending', 'Accepted', 'Wrong Answer', 'Time Limit Exceeded', 'Runtime Error', 'Compile Error', 'System Error'
    status = db.Column(db.Enum('Pending', 'Accepted', 'Wrong Answer', 'Time Limit Exceeded', 'Runtime Error', 'Compile Error', 'System Error'),
                       default='Pending')

    score = db.Column(db.Float, default=0.0)  # 针对 Kaggle 模式的分数
    output_log = db.Column(db.Text)  # 存放判题过程中的错误日志或详细信息

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 建立模型间的关系，方便查询
    user = db.relationship('User', backref=db.backref('submissions', lazy=True))
    # problem 关系已在 Problem 模型中通过 backref 定义，此处可省略或保持一致
    # problem = db.relationship('Problem', backref=db.backref('submissions', lazy=True))
    exam = db.relationship('Exam', backref=db.backref('submissions', lazy=True))

    def __repr__(self):
        return f'<Submission {self.id} by User {self.user_id}>'
