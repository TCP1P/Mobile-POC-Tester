import os

class Config:
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
    ENABLE_POW = os.environ.get("ENABLE_POW", "false").lower() == "true"
    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(24))
    
    MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", "100")) * 1024 * 1024
    ALLOWED_EXTENSIONS = {'apk'}
    
    UPLOAD_FOLDER = 'uploads'
    SCREENSHOT_FOLDER = 'screenshots'
    CHALLENGES_FOLDER = 'challenges'
    
    MAX_QUEUE_SIZE = int(os.environ.get("MAX_QUEUE_SIZE", "50"))
    
    ADB_TIMEOUT = int(os.environ.get("ADB_TIMEOUT", "30"))
    PROCESS_TIMEOUT = int(os.environ.get("PROCESS_TIMEOUT", "30"))
    APK_INSTALL_TIMEOUT = int(os.environ.get("APK_INSTALL_TIMEOUT", "60"))
    
    ADB_HOST = os.environ.get("ADB_HOST", "device")
    ADB_PORT = int(os.environ.get("ADB_PORT", "5037"))
    
    POW_DIFFICULTY = int(os.environ.get("POW_DIFFICULTY", "10000"))