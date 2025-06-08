from flask import request, jsonify
from . import app, db
from .models import User, Conversation
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt(app)

#  注册、登录、保存会话
# 用户注册接口


@app.route('/register', methods=['POST'])
def register():
    """
    用户注册接口。
    接收 JSON 数据，包含用户名、密码和可选的邮箱地址。
    如果用户名已存在，返回失败信息；否则创建新用户并返回用户ID。
    """
    # 从请求中获取 JSON 数据
    data = request.get_json()
    username = data.get('username')  # 获取用户名
    password = data.get('password')  # 获取密码
    email = data.get('email')        # 获取邮箱地址（可选）
    # 检查用户名是否已存在
    if User.query.filter_by(username=username).first():
        return jsonify({'status': 'failure', 'message': '用户名已存在'}), 400
    # 创建新用户
    user = User(username=username, password=password, email=email)
    db.session.add(user)  # 将用户对象添加到会话
    db.session.commit()   # 提交会话，保存到数据库

    # 返回注册成功的信息
    return jsonify({'status': 'success', 'user_id': user.user_id})

# 用户登录接口
@app.route('/login', methods=['POST'])
def login():
    """
    用户登录接口。
    接收 JSON 数据，包含用户名和密码。
    如果用户名和密码匹配，返回用户ID；否则返回失败信息。
    """
    # 从请求中获取 JSON 数据
    data = request.get_json()
    username = data.get('username')  # 获取用户名
    password = data.get('password')  # 获取密码
    # 查询用户
    user = User.query.filter_by(username=username, password=password).first()
    if user:
        # 如果用户存在且密码匹配，返回用户ID
        return jsonify({'status': 'success', 'user_id': user.user_id})
    else:
        # 如果用户名或密码错误，返回失败信息
        return jsonify({'status': 'failure', 'message': '用户名或密码错误'}), 401

#  保存会话
@app.route('/save_conversation', methods=['POST'])
def save_conversation():
    data = request.get_json()
    user_id = data.get('user_id')
    content = data.get('content')
    if not user_id or not content:
        return jsonify({'status': 'failure', 'message': '缺少必要参数'}), 400
    conversation = Conversation(user_id=user_id, content=content)
    db.session.add(conversation)
    db.session.commit()
    return jsonify({'status': 'success', 'conversation_id': conversation.conversation_id})

@app.route('/get_conversations', methods=['GET'])
def get_conversations(user_id):
    conversations = Conversation.query.filter_by(user_id=user_id).order_by(Conversation.timestamp.desc()).all()
    result = [{'conversation_id': c.conversation_id, 'content': c.content, 'timestamp': c.timestamp} for c in conversations]
    return jsonify({'status': 'success', 'conversations': result})

