from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    # role: enum('student', 'teacher')
    role = db.Column(db.Enum('student', 'teacher'), default='student')

    def __repr__(self):
        return f'<User {self.username}>'
