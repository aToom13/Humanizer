import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    DEBUG = os.environ.get('DEBUG') == 'True'
    
    # Default Provider Settings
    DEFAULT_PROVIDER = 'gemini'
    DEFAULT_MODEL = 'gemini-3-flash-preview'
