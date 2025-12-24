from datetime import datetime

from app.models.user import db


class Dataset(db.Model):
    __tablename__ = 'datasets'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(256), nullable=False)
    file_size = db.Column(db.String(64))
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    uploader = db.relationship('User', backref=db.backref('datasets', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'uploader': self.uploader.username if self.uploader else 'Unknown',
            'file_size': self.file_size,
            'created_at': self.created_at.isoformat(),
            'download_url': f'/api/datasets/{self.id}/download'
        }
