"""
路由管理工具 - 主程序入口
"""
import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

# 导入主窗口
from ui.main_window import MainWindow
from utils.admin_check import is_admin, request_admin
from utils.logger import setup_logger


def main():
    """程序入口"""
    # 创建必要的目录
    os.makedirs("profiles", exist_ok=True)
    os.makedirs("snapshots", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # 配置日志
    setup_logger()
    
    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("路由管理工具")
    app.setOrganizationName("NetTLS")
    
    # 检查管理员权限
    if not is_admin():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("需要管理员权限")
        msg.setText("此程序需要管理员权限才能管理永久路由。")
        msg.setInformativeText("请以管理员身份运行此程序。")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        return 1
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

