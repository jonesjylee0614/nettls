"""
管理员权限检查工具
"""
import ctypes
import sys
import os


def is_admin():
    """
    检查当前进程是否具有管理员权限
    
    Returns:
        bool: True 表示具有管理员权限，False 表示没有
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def request_admin():
    """
    请求管理员权限并重启程序
    """
    if sys.platform == 'win32':
        try:
            # 使用 ShellExecute 请求管理员权限重新启动
            ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas", 
                sys.executable, 
                " ".join(sys.argv), 
                None, 
                1
            )
            sys.exit(0)
        except Exception as e:
            print(f"请求管理员权限失败: {e}")
            return False
    return False

