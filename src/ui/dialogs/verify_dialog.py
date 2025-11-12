"""
验证结果对话框 - 显示路由验证结果
"""
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QCheckBox, QHeaderView, QMessageBox,
    QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from core.verify_manager import VerifyManager, VerifyResult

logger = logging.getLogger(__name__)


class VerifyThread(QThread):
    """验证执行线程"""
    
    # 信号
    progress = pyqtSignal(str, int, int)  # (消息, 当前进度, 总数)
    result_ready = pyqtSignal(object)  # 单个验证结果
    finished_all = pyqtSignal(list)  # 所有验证结果
    
    def __init__(self, verify_manager: VerifyManager, targets: list, do_trace: bool = False):
        super().__init__()
        self.verify_manager = verify_manager
        self.targets = targets
        self.do_trace = do_trace
    
    def run(self):
        """执行验证"""
        results = []
        total = len(self.targets)
        
        for i, target in enumerate(self.targets):
            self.progress.emit(f"验证 {target}...", i + 1, total)
            
            result = self.verify_manager.verify_route(target, self.do_trace)
            results.append(result)
            
            self.result_ready.emit(result)
        
        self.finished_all.emit(results)


class VerifyDialog(QDialog):
    """验证结果对话框"""
    
    def __init__(self, parent=None, verify_manager: VerifyManager = None, targets: list = None, routes: dict = None):
        """
        初始化对话框
        
        Args:
            parent: 父窗口
            verify_manager: 验证管理器
            targets: 要验证的目标列表
            routes: 目标到路由描述的映射 {target: desc}
        """
        super().__init__(parent)
        
        self.verify_manager = verify_manager
        self.targets = targets or []
        self.routes = routes or {}
        self.verify_thread = None
        self.results = []
        
        # 设置窗口
        self.setWindowTitle("路由验证结果")
        self.setModal(True)
        self.setMinimumSize(800, 500)
        
        # 初始化UI
        self._init_ui()
        
        # 自动开始验证
        if self.targets:
            self._start_verify()
    
    def _init_ui(self):
        """初始化UI组件"""
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel(f"正在验证 {len(self.targets)} 条路由...")
        title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
        layout.addWidget(title)
        
        # 选项
        options_layout = QHBoxLayout()
        
        self.trace_checkbox = QCheckBox("执行 TraceRoute(会比较慢)")
        self.trace_checkbox.setChecked(False)
        self.trace_checkbox.stateChanged.connect(self._on_trace_option_changed)
        options_layout.addWidget(self.trace_checkbox)
        
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        # 结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(7)
        self.result_table.setHorizontalHeaderLabels([
            "目标", "描述", "状态", "出接口", "下一跳", "延迟(ms)", "错误信息"
        ])
        
        # 设置列宽
        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # 描述
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # 状态
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # 出接口
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # 下一跳
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # 延迟
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)  # 错误信息
        
        # 设置表格属性
        self.result_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.itemDoubleClicked.connect(self._on_row_double_clicked)
        
        layout.addWidget(self.result_table)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(self.targets))
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.retry_btn = QPushButton("重新验证失败项")
        self.retry_btn.clicked.connect(self._on_retry_failed)
        self.retry_btn.setEnabled(False)
        button_layout.addWidget(self.retry_btn)
        
        self.export_btn = QPushButton("导出结果")
        self.export_btn.clicked.connect(self._on_export)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _start_verify(self):
        """开始验证"""
        # 清空结果
        self.result_table.setRowCount(0)
        self.results.clear()
        
        # 禁用选项和按钮
        self.trace_checkbox.setEnabled(False)
        self.retry_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        
        # 创建并启动验证线程
        do_trace = self.trace_checkbox.isChecked()
        
        self.verify_thread = VerifyThread(
            self.verify_manager, 
            self.targets, 
            do_trace
        )
        self.verify_thread.progress.connect(self._on_progress)
        self.verify_thread.result_ready.connect(self._on_result_ready)
        self.verify_thread.finished_all.connect(self._on_finished)
        self.verify_thread.start()
    
    def _on_progress(self, message: str, current: int, total: int):
        """进度更新"""
        self.progress_bar.setValue(current)
        self.setWindowTitle(f"路由验证结果 - {current}/{total}")
    
    def _on_result_ready(self, result: VerifyResult):
        """单个结果就绪"""
        self.results.append(result)
        
        # 添加到表格
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        
        # 目标
        self.result_table.setItem(row, 0, QTableWidgetItem(result.target))
        
        # 描述
        desc = self.routes.get(result.target, "-")
        desc_item = QTableWidgetItem(desc)
        desc_item.setForeground(QColor(255, 255, 255))  # 白色
        self.result_table.setItem(row, 1, desc_item)
        
        # 状态
        status_item = QTableWidgetItem("命中" if result.hit else "未命中")
        if result.hit:
            status_item.setForeground(QColor(34, 197, 94))  # 绿色
        else:
            status_item.setForeground(QColor(239, 68, 68))  # 红色
        self.result_table.setItem(row, 2, status_item)
        
        # 出接口
        self.result_table.setItem(row, 3, QTableWidgetItem(result.interface))
        
        # 下一跳
        hop = result.first_hop if result.trace_success else result.gateway
        self.result_table.setItem(row, 4, QTableWidgetItem(hop))
        
        # 延迟
        latency_text = f"{result.latency_ms}" if result.latency_ms > 0 else "-"
        self.result_table.setItem(row, 5, QTableWidgetItem(latency_text))
        
        # 错误信息
        self.result_table.setItem(row, 6, QTableWidgetItem(result.error))
    
    def _on_finished(self, results: list):
        """验证完成"""
        # 启用选项和按钮
        self.trace_checkbox.setEnabled(True)
        self.retry_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        
        # 统计结果
        hit_count = sum(1 for r in results if r.hit)
        failed_count = len(results) - hit_count
        
        self.setWindowTitle(f"路由验证结果 - 命中: {hit_count}, 未命中: {failed_count}")
        
        if failed_count == 0:
            QMessageBox.information(self, "验证完成", f"所有 {len(results)} 条路由均已命中")
    
    def _on_trace_option_changed(self, state: int):
        """TraceRoute 选项变化"""
        # 如果已经有结果,提示是否重新验证
        if self.results:
            reply = QMessageBox.question(
                self, "重新验证",
                "修改选项后需要重新验证,是否继续?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._start_verify()
    
    def _on_retry_failed(self):
        """重新验证失败项"""
        failed_targets = [r.target for r in self.results if not r.hit]
        
        if not failed_targets:
            QMessageBox.information(self, "提示", "没有失败的验证项")
            return
        
        # 更新目标列表并重新验证
        self.targets = failed_targets
        self.progress_bar.setRange(0, len(self.targets))
        self._start_verify()
    
    def _on_export(self):
        """导出结果"""
        QMessageBox.information(self, "提示", "导出功能开发中...")
    
    def _on_row_double_clicked(self, item: QTableWidgetItem):
        """双击行查看详细日志"""
        row = item.row()
        if row < len(self.results):
            result = self.results[row]
            
            # 显示详细日志
            log_text = f"目标: {result.target}\n"
            log_text += f"命中: {'是' if result.hit else '否'}\n"
            log_text += f"出接口: {result.interface}\n"
            log_text += f"下一跳: {result.gateway}\n"
            
            if result.trace_success:
                log_text += f"首跳: {result.first_hop}\n"
                log_text += f"延迟: {result.latency_ms} ms\n"
            
            if result.error:
                log_text += f"错误: {result.error}\n"
            
            log_text += f"\n详细日志:\n{result.log}"
            
            msg = QMessageBox(self)
            msg.setWindowTitle(f"验证详情 - {result.target}")
            msg.setText(log_text)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()

