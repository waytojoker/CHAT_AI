from datetime import datetime
from . import db

class User(db.Model):
    """
    用户模型，用于存储用户信息。
    属性：
        user_id (int): 用户的唯一标识符。
        username (str): 用户的用户名。
        password (str): 用户的密码。
        email (str): 用户的电子邮件地址。
        created_at (datetime): 用户创建的时间戳。
    """
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, username, password, email=None):
        self.username = username
        self.password = password
        self.email = email

class Conversation(db.Model):
    """
    对话模型，用于存储用户对话。
    属性：
        conversation_id (int): 对话的唯一标识符。
        user_id (int): 用户的唯一标识符。
        content (str): 对话的内容。
        timestamp (datetime): 对话创建的时间戳。
    """
    __tablename__ = 'conversations'
    conversation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id, content):
        self.user_id = user_id
        self.content = content