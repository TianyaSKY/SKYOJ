from app.models.user import db

class SysDict(db.Model):
    __table__name = "sys_dict"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100))
    val = db.Column(db.String(100))