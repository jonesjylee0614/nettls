"""
日志配置模块
"""
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logger(log_dir: str = "logs", log_level: int = logging.INFO):
    """
    配置日志系统
    
    Args:
        log_dir: 日志目录
        log_level: 日志级别
    """
    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)
    
    # 日志文件路径
    log_file = os.path.join(log_dir, "rtmgr.log")
    
    # 配置根日志记录器
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # 清除现有处理器
    logger.handlers.clear()
    
    # 文件处理器(带轮转)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logging.info("=" * 60)
    logging.info(f"路由管理工具启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("=" * 60)

