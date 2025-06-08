from flask import request, jsonify
from . import app, db
from .models import User, Conversation, Message
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt(app)

# 用户注册接口
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    if User.query.filter_by(username=username).first():
        return jsonify({'status': 'failure', 'message': '用户名已存在'}), 400
    user = User(username=username, password=password, email=email)
    db.session.add(user)
    db.session.commit()
    return jsonify({'status': 'success', 'user_id': user.user_id})

# 用户登录接口
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username, password=password).first()
    if user:
        return jsonify({'status': 'success', 'user_id': user.user_id})
    else:
        return jsonify({'status': 'failure', 'message': '用户名或密码错误'}), 401

# 保存对话
@app.route('/save_conversation', methods=['POST'])
def save_conversation():
    data = request.get_json()
    user_id = data.get('user_id')
    conversations = data.get('conversations')
    if not user_id or not conversations:
        return jsonify({'status': 'failure', 'message': '缺少必要参数'}), 400

    # 创建新的对话会话
    conversation = Conversation(user_id=user_id)
    db.session.add(conversation)
    db.session.commit()

    # 为每轮对话创建消息记录
    for message in conversations:
        role = message.get('role')
        content = message.get('content')
        if role and content:
            msg = Message(conversation_id=conversation.conversation_id, role=role, content=content)
            db.session.add(msg)

    db.session.commit()
    return jsonify({'status': 'success', 'conversation_id': conversation.conversation_id})

# 获取对话
@app.route('/get_conversations', methods=['GET'])
def get_conversations():
    data = request.get_json()
    user_id = data.get('user_id')
    conversations = Conversation.query.filter_by(user_id=user_id).order_by(Conversation.timestamp.desc()).all()
    result = []
    for c in conversations:
        messages = Message.query.filter_by(conversation_id=c.conversation_id).order_by(Message.timestamp.asc()).all()
        conversation_content = [{'role': msg.role, 'content': msg.content, 'timestamp': msg.timestamp} for msg in messages]
        result.append({
            'conversation_id': c.conversation_id,
            'content': conversation_content,
            'timestamp': c.timestamp
        })
    return jsonify({'status': 'success', 'conversations': result})