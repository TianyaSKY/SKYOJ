from app.models.user import db


class Exam(db.Model):
    __tablename__ = 'exams'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    password = db.Column(db.String(2000))  # 考试进入密码（可选）
    is_visible = db.Column(db.Boolean, default=False)  # 考试是否对学生可见

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    creator = db.relationship('User', backref=db.backref('created_exams', lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "is_visible": self.is_visible,
            "created_by": self.created_by
        }


class ExamProblem(db.Model):
    __tablename__ = 'exam_problems'

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    problem_id = db.Column(db.Integer, db.ForeignKey('problems.id', ondelete='CASCADE'), nullable=False)
    display_id = db.Column(db.String(10))  # 考试中的题号，如 A, B, C
    score = db.Column(db.Integer, default=100)  # 该题在本次考试中的分数

    exam = db.relationship('Exam', backref=db.backref('problems', lazy='dynamic', cascade="all, delete-orphan"))
    # problem 关系已在 Problem 模型中通过 backref 定义，此处可省略或保持一致
    # problem = db.relationship('Problem')
