"""
Diff 预览对话框 - 显示路由变更计划并执行应用
"""
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QCheckBox, QTextEdit, QGroupBox,
    QHeaderView, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from core.apply_manager import ApplyManager, DiffItem

logger = logging.getLogger(__name__)


class ApplyThread(QThread):
    """Apply 执行线程"""
    
    # 信号
    progress = pyqtSignal(str)  # 进度信息
    finished = pyqtSignal(bool, list)  # 完成信号(是否成功, 结果列表)
    
    def __init__(self, apply_manager: ApplyManager, diff_items: list):
        super().__init__()
        self.apply_manager = apply_manager
        self.diff_items = diff_items
    
    def run(self):
        """执行应用"""
        self.progress.emit("开始执行应用...")
        
        # 执行 Diff
        success, results = self.apply_manager.execute_diff(self.diff_items)
        
        # 发送完成信号
        self.finished.emit(success, results)


class DiffDialog(QDialog):
    """Diff 预览对话框"""
    
    def __init__(self, parent=None, apply_manager: ApplyManager = None, diff_items: list = None):
        """
        初始化对话框
        
        Args:
            parent: 父窗口
            apply_manager: Apply 管理器
            diff_items: Diff 列表
        """
        super().__init__(parent)
        
        self.apply_manager = apply_manager
        self.diff_items = diff_items or []
        self.apply_thread = None
        
        # 统计信息
        self.stats = self._calculate_stats()
        
        # 设置窗口
        self.setWindowTitle("Apply 预览与执行")
        self.setModal(True)
        self.setMinimumSize(900, 600)
        
        # 初始化UI
        self._init_ui()
    
    def _calculate_stats(self) -> dict:
        """计算统计信息"""
        stats = {
            "add": 0,
            "change": 0,
            "delete": 0,
            "skip": 0,
            "total": len(self.diff_items)
        }
        
        for item in self.diff_items:
            if item.action in stats:
                stats[item.action] += 1
        
        return stats
    
    def _init_ui(self):
        """初始化UI组件"""
        layout = QVBoxLayout()
        
        # 统计信息
        stats_label = QLabel(
            f"变更统计: 新增 {self.stats['add']} | "
            f"修改 {self.stats['change']} | "
            f"删除 {self.stats['delete']} | "
            f"跳过 {self.stats['skip']}"
        )
        stats_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
        layout.addWidget(stats_label)
        
        # Diff 表格
        self.diff_table = QTableWidget()
        self.diff_table.setColumnCount(5)
        self.diff_table.setHorizontalHeaderLabels(["操作", "目标", "网关", "接口", "说明"])
        
        # 设置列宽
        header = self.diff_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        # 填充表格
        self._populate_table()
        
        layout.addWidget(self.diff_table)
        
        # 选项
        options_layout = QHBoxLayout()
        
        self.auto_verify_checkbox = QCheckBox("执行后自动验证")
        self.auto_verify_checkbox.setChecked(True)
        options_layout.addWidget(self.auto_verify_checkbox)
        
        self.auto_rollback_checkbox = QCheckBox("失败自动回滚")
        self.auto_rollback_checkbox.setChecked(True)
        options_layout.addWidget(self.auto_rollback_checkbox)
        
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        # 日志输出区域
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.execute_btn = QPushButton("执行")
        self.execute_btn.setDefault(True)
        self.execute_btn.clicked.connect(self._on_execute)
        button_layout.addWidget(self.execute_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _populate_table(self):
        """填充表格"""
        self.diff_table.setRowCount(len(self.diff_items))
        
        for row, item in enumerate(self.diff_items):
            # 操作类型
            action_item = QTableWidgetItem(item.action.upper())
            
            # 根据操作类型设置颜色
            if item.action == "add":
                action_item.setForeground(QColor(34, 197, 94))  # 绿色
            elif item.action == "change":
                action_item.setForeground(QColor(249, 115, 22))  # 橙色
            elif item.action == "delete":
                action_item.setForeground(QColor(239, 68, 68))  # 红色
            elif item.action == "skip":
                action_item.setForeground(QColor(156, 163, 175))  # 灰色
            
            self.diff_table.setItem(row, 0, action_item)
            
            # 目标
            self.diff_table.setItem(row, 1, QTableWidgetItem(item.route.get_destination_prefix()))
            
            # 网关
            gateway_text = item.route.gateway
            if item.action == "change" and item.old_route:
                old_gateway = item.old_route.get('NextHop', '')
                if old_gateway != item.route.gateway:
                    gateway_text = f"{old_gateway} → {item.route.gateway}"
            
            self.diff_table.setItem(row, 2, QTableWidgetItem(gateway_text))
            
            # 接口
            self.diff_table.setItem(row, 3, QTableWidgetItem(item.route.interface_name))
            
            # 说明
            self.diff_table.setItem(row, 4, QTableWidgetItem(item.reason))
    
    def _on_execute(self):
        """执行按钮点击事件"""
        # 确认执行
        reply = QMessageBox.question(
            self, "确认执行",
            f"即将执行 {self.stats['add'] + self.stats['change'] + self.stats['delete']} 项变更。\n\n是否继续?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 禁用按钮
        self.execute_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        
        # 过滤出需要执行的项(排除 skip)
        exec_items = [item for item in self.diff_items if item.action != "skip"]
        
        # 创建并启动执行线程
        self.apply_thread = ApplyThread(self.apply_manager, exec_items)
        self.apply_thread.progress.connect(self._on_progress)
        self.apply_thread.finished.connect(self._on_finished)
        self.apply_thread.start()
    
    def _on_progress(self, message: str):
        """进度更新"""
        self.log_text.append(message)
    
    def _on_finished(self, success: bool, results: list):
        """执行完成"""
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        
        # 启用按钮
        self.execute_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        
        # 显示结果
        if success:
            self.log_text.append("\n=== 执行成功 ===")
            for result in results:
                action = result['action']
                target = result['target']
                self.log_text.append(f"[{action.upper()}] {target} - 成功")
            
            QMessageBox.information(self, "执行成功", f"成功执行 {len(results)} 项变更")
            self.accept()
        else:
            self.log_text.append("\n=== 执行失败 ===")
            for result in results:
                action = result['action']
                target = result['target']
                if result['success']:
                    self.log_text.append(f"[{action.upper()}] {target} - 成功")
                else:
                    error = result.get('error', '未知错误')
                    self.log_text.append(f"[{action.upper()}] {target} - 失败: {error}")
            
            # 如果启用了自动回滚
            if self.auto_rollback_checkbox.isChecked():
                self.log_text.append("\n自动回滚已执行")
            
            QMessageBox.critical(self, "执行失败", "部分变更执行失败,请查看日志")

