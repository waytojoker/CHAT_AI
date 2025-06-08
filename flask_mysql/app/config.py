import os

class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql://root:mysql12345#@localhost:3306/chat_ai'
    SQLALCHEMY_TRACK_MODIFICATIONS = False