"""
统一日志配置模块
提供应用日志、脚本日志的统一管理，支持日志轮转和清理
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional
import json
import os


class LogConfig:
    """日志配置"""
    # 日志根目录
    BASE_DIR = Path(__file__).parent.parent / "logs"
    
    # 各类日志目录
    APP_LOG_DIR = BASE_DIR / "app"
    SCRIPT_LOG_DIR = BASE_DIR / "scripts"
    ARCHIVE_DIR = BASE_DIR / "archive"
    
    # 应用日志配置
    APP_LOG_FILE = APP_LOG_DIR / "app.log"
    APP_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    APP_BACKUP_COUNT = 5
    
    # 脚本日志配置
    SCRIPT_MAX_FILES_PER_SCRIPT = 100  # 每个脚本最多保留日志文件数
    SCRIPT_RETENTION_DAYS = 30  # 脚本日志保留天数
    
    # 归档配置
    ARCHIVE_AFTER_DAYS = 7  # 超过此天数的日志压缩归档
    ARCHIVE_RETENTION_DAYS = 90  # 归档文件保留天数
    
    # 数据库清理配置
    HISTORY_RETENTION_COUNT = 500  # 每个脚本保留的历史记录数
    SYSTEM_LOG_RETENTION_DAYS = 30  # 系统日志保留天数
    
    # 日志格式
    STANDARD_FORMAT = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    DETAILED_FORMAT = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    @classmethod
    def ensure_dirs(cls):
        """确保所有日志目录存在"""
        cls.APP_LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.SCRIPT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


class AppLogger:
    """应用日志管理器"""
    
    _instance: Optional['AppLogger'] = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        LogConfig.ensure_dirs()
        self._setup_root_logger()
        self._setup_app_logger()
        AppLogger._initialized = True
    
    def _setup_root_logger(self):
        """配置根日志记录器"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # 避免重复添加 handler
        if root_logger.handlers:
            return
        
        # 控制台输出
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(LogConfig.STANDARD_FORMAT)
        root_logger.addHandler(console_handler)
    
    def _setup_app_logger(self):
        """配置应用日志记录器"""
        app_logger = logging.getLogger('app')
        app_logger.setLevel(logging.DEBUG)
        
        # 文件处理器 - 按大小轮转
        file_handler = logging.handlers.RotatingFileHandler(
            LogConfig.APP_LOG_FILE,
            maxBytes=LogConfig.APP_MAX_BYTES,
            backupCount=LogConfig.APP_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(LogConfig.DETAILED_FORMAT)
        app_logger.addHandler(file_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取指定模块的日志记录器"""
        return logging.getLogger(f'app.{name}')


class ScriptLogger:
    """脚本日志管理器"""
    
    def __init__(self):
        LogConfig.ensure_dirs()
    
    def get_log_file_path(self, script_name: str) -> Path:
        """获取脚本日志文件路径（按日期分文件）"""
        script_dir = LogConfig.SCRIPT_LOG_DIR / script_name
        script_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        return script_dir / f"{date_str}.log"
    
    def get_logger(self, script_name: str) -> logging.Logger:
        """获取脚本日志记录器（按天轮转）"""
        logger = logging.getLogger(f'script.{script_name}')
        logger.setLevel(logging.DEBUG)
        
        # 避免重复添加 handler
        if logger.handlers:
            return logger
        
        script_dir = LogConfig.SCRIPT_LOG_DIR / script_name
        script_dir.mkdir(parents=True, exist_ok=True)
        
        # 按天轮转
        file_handler = logging.handlers.TimedRotatingFileHandler(
            script_dir / "output.log",
            when='midnight',
            interval=1,
            backupCount=LogConfig.SCRIPT_RETENTION_DAYS,
            encoding='utf-8'
        )
        file_handler.suffix = "%Y-%m-%d"
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(LogConfig.STANDARD_FORMAT)
        logger.addHandler(file_handler)
        
        return logger


# 全局实例
_app_logger: Optional[AppLogger] = None
_script_logger: Optional[ScriptLogger] = None


def get_logger(name: str = 'app') -> logging.Logger:
    """
    获取日志记录器
    
    用法:
        logger = get_logger('process_manager')
        logger.info("脚本已启动")
    """
    global _app_logger
    
    if _app_logger is None:
        _app_logger = AppLogger()
    
    return _app_logger.get_logger(name)


def get_script_logger(script_name: str) -> logging.Logger:
    """获取脚本日志记录器"""
    global _script_logger
    
    if _script_logger is None:
        _script_logger = ScriptLogger()
    
    return _script_logger.get_logger(script_name)


def get_script_log_path(script_name: str) -> Path:
    """获取脚本日志文件路径"""
    global _script_logger
    
    if _script_logger is None:
        _script_logger = ScriptLogger()
    
    return _script_logger.get_log_file_path(script_name)


def init_logging():
    """初始化日志系统"""
    global _app_logger
    _app_logger = AppLogger()
    logger = get_logger('logger')
    logger.info("日志系统初始化完成")
    logger.info(f"应用日志目录: {LogConfig.APP_LOG_DIR}")
    logger.info(f"脚本日志目录: {LogConfig.SCRIPT_LOG_DIR}")