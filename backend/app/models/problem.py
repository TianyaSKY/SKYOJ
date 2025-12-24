from app.models.user import db


class Problem(db.Model):
    __tablename__ = 'problems'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)  # Markdown 格式 of problem description

    # Problem type: acm (standard IO), oop (unit test), kaggle (CSV scoring)
    type = db.Column(db.Enum('acm', 'oop', 'kaggle'), nullable=False)
    language = db.Column(db.Enum('python', 'java', 'c', 'cpp'), nullable=False)

    # Evaluation limits
    time_limit = db.Column(db.Integer, default=1000)  # Unit: ms
    memory_limit = db.Column(db.Integer, default=128)  # Unit: mb

    # Storage paths and templates
    test_case_path = db.Column(db.String(500))  # Path to test cases or correct answer CSV
    template_code = db.Column(db.Text)  # Class/function template for OOP mode

    created_at = db.Column(db.DateTime, default=db.func.now())

    # Cascade delete: when a problem is deleted, its submissions and exam associations are also deleted.
    # We remove passive_deletes=True so SQLAlchemy handles the deletion of child records 
    # even if the database schema doesn't have ON DELETE CASCADE set up.
    submissions = db.relationship('Submission', backref=db.backref('problem', lazy=True), cascade="all, delete-orphan")
    exam_problems = db.relationship('ExamProblem', backref=db.backref('problem', lazy=True),
                                    cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Problem {self.title}>'
