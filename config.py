import os

class Config:
    SECRET_KEY = 'campuscartsecretkey'
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:ssk03@localhost:5432/campuscart'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join('static', 'uploads')

