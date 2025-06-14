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
    conversation_id = data.get('conversation_id')  # 新增参数，用于指定对话ID
    messages = data.get('messages')  # 新增参数，用于接收多条消息

    # 如果没有指定 conversation_id，则创建新的对话会话
    if not conversation_id:
        conversation = Conversation(user_id=user_id)
        db.session.add(conversation)
        db.session.commit()
        conversation_id = conversation.conversation_id
    else:
        # 检查对话是否存在
        conversation = Conversation.query.filter_by(conversation_id=conversation_id, user_id=user_id).first()
        if not conversation:
            conversation = Conversation(user_id=user_id)
            db.session.add(conversation)
            db.session.commit()
            conversation_id = conversation.conversation_id

    # 为每条消息创建消息记录
    for message in messages:
        role = message.get('role')
        content = message.get('content')
        if role and content:
            msg = Message(conversation_id=conversation_id, role=role, content=content)
            db.session.add(msg)

    db.session.commit()
    return jsonify({'status': 'success', 'conversation_id': conversation_id})

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

# 删除用户的全部历史记录
@app.route('/delete_user_history', methods=['POST'])
def delete_user_history():
    data = request.get_json()
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'status': 'failure', 'message': '用户ID不能为空'}), 400

    # 删除用户的所有对话
    conversations = Conversation.query.filter_by(user_id=user_id).all()
    for conversation in conversations:
        # 删除对话中的所有消息
        Message.query.filter_by(conversation_id=conversation.conversation_id).delete()
        # 删除对话本身
        db.session.delete(conversation)

    db.session.commit()
    return jsonify({'status': 'success', 'message': '用户历史记录已全部删除'})

# 删除某个特定对话的历史记录
@app.route('/delete_conversation_history', methods=['POST'])
def delete_conversation_history():
    data = request.get_json()
    user_id = data.get('user_id')
    conversation_id = data.get('conversation_id')
    if not user_id or not conversation_id:
        return jsonify({'status': 'failure', 'message': '用户ID和对话ID不能为空'}), 400

    # 检查对话是否存在
    conversation = Conversation.query.filter_by(conversation_id=conversation_id, user_id=user_id).first()
    if not conversation:
        return jsonify({'status': 'failure', 'message': '对话不存在'}), 404

    # 删除对话中的所有消息
    Message.query.filter_by(conversation_id=conversation_id).delete()
    # 删除对话本身
    db.session.delete(conversation)

    db.session.commit()
    return jsonify({'status': 'success', 'message': '对话历史记录已删除'})

# 新建空对话
@app.route('/new_conversation', methods=['POST'])
def new_conversation():
    data = request.get_json()
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'status': 'failure', 'message': '用户ID不能为空'}), 400
    conversation = Conversation(user_id=user_id)
    db.session.add(conversation)
    db.session.commit()
    return jsonify({'status': 'success', 'conversation_id': conversation.conversation_id})
