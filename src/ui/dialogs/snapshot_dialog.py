"""
快照管理对话框 - 显示和管理路由快照
"""
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QHeaderView, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt

from core.snapshot_manager import SnapshotManager
from core.route_manager import RouteManager

logger = logging.getLogger(__name__)


class SnapshotDialog(QDialog):
    """快照管理对话框"""
    
    def __init__(self, parent=None, snapshot_manager: SnapshotManager = None, route_manager: RouteManager = None):
        """
        初始化对话框
        
        Args:
            parent: 父窗口
            snapshot_manager: 快照管理器
            route_manager: 路由管理器
        """
        super().__init__(parent)
        
        self.snapshot_manager = snapshot_manager
        self.route_manager = route_manager
        self.snapshots = []
        
        # 设置窗口
        self.setWindowTitle("快照与回滚")
        self.setModal(True)
        self.setMinimumSize(900, 500)
        
        # 初始化UI
        self._init_ui()
        
        # 加载快照列表
        self._load_snapshots()
    
    def _init_ui(self):
        """初始化UI组件"""
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("快照管理 - 自动记录每次Apply前的系统路由状态")
        title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
        layout.addWidget(title)
        
        # 快照表格
        self.snapshot_table = QTableWidget()
        self.snapshot_table.setColumnCount(5)
        self.snapshot_table.setHorizontalHeaderLabels([
            "时间", "类型", "路由数量", "大小(KB)", "文件名"
        ])
        
        # 设置列宽
        header = self.snapshot_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        # 设置表格属性
        self.snapshot_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.snapshot_table.setAlternatingRowColors(True)
        self.snapshot_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        layout.addWidget(self.snapshot_table)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("创建快照")
        self.create_btn.clicked.connect(self._on_create_snapshot)
        button_layout.addWidget(self.create_btn)
        
        self.restore_btn = QPushButton("回滚到此快照")
        self.restore_btn.clicked.connect(self._on_restore_snapshot)
        self.restore_btn.setEnabled(False)
        button_layout.addWidget(self.restore_btn)
        
        self.export_btn = QPushButton("导出快照")
        self.export_btn.clicked.connect(self._on_export_snapshot)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)
        
        self.delete_btn = QPushButton("删除快照")
        self.delete_btn.clicked.connect(self._on_delete_snapshot)
        self.delete_btn.setEnabled(False)
        button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self._load_snapshots)
        button_layout.addWidget(self.refresh_btn)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        # 说明
        note_label = QLabel(
            "提示: 回滚操作会将系统路由恢复到快照时的状态。"
            "请谨慎操作,建议在回滚前创建新快照。"
        )
        note_label.setStyleSheet("color: #f97316; padding: 10px;")
        note_label.setWordWrap(True)
        layout.addWidget(note_label)
        
        self.setLayout(layout)
        
        # 连接选择事件
        self.snapshot_table.itemSelectionChanged.connect(self._on_selection_changed)
    
    def _load_snapshots(self):
        """加载快照列表"""
        self.snapshot_table.setRowCount(0)
        self.snapshots = self.snapshot_manager.list_snapshots()
        
        for snapshot in self.snapshots:
            row = self.snapshot_table.rowCount()
            self.snapshot_table.insertRow(row)
            
            # 时间
            timestamp = snapshot.get('timestamp', '')
            if 'T' in timestamp:
                timestamp = timestamp.replace('T', ' ').split('.')[0]
            self.snapshot_table.setItem(row, 0, QTableWidgetItem(timestamp))
            
            # 类型
            snap_type = snapshot.get('type', 'unknown')
            type_text = "系统路由" if snap_type == "system" else "配置文件"
            self.snapshot_table.setItem(row, 1, QTableWidgetItem(type_text))
            
            # 路由数量
            total_routes = snapshot.get('total_routes', 0)
            self.snapshot_table.setItem(row, 2, QTableWidgetItem(str(total_routes)))
            
            # 大小
            size_kb = snapshot.get('size', 0) / 1024
            self.snapshot_table.setItem(row, 3, QTableWidgetItem(f"{size_kb:.1f}"))
            
            # 文件名
            filename = snapshot.get('filename', '')
            self.snapshot_table.setItem(row, 4, QTableWidgetItem(filename))
        
        # 更新标题
        title_text = f"快照管理 - 共 {len(self.snapshots)} 个快照"
        self.findChild(QLabel).setText(title_text)
    
    def _on_selection_changed(self):
        """选择变化事件"""
        has_selection = len(self.snapshot_table.selectedItems()) > 0
        self.restore_btn.setEnabled(has_selection)
        self.export_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
    
    def _get_selected_snapshot(self):
        """获取选中的快照"""
        selected_rows = self.snapshot_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        
        row = selected_rows[0].row()
        if row < len(self.snapshots):
            return self.snapshots[row]
        
        return None
    
    def _on_create_snapshot(self):
        """创建快照"""
        reply = QMessageBox.question(
            self, "创建快照",
            "是否创建系统路由快照?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            filepath = self.snapshot_manager.create_system_snapshot(self.route_manager)
            
            if filepath:
                QMessageBox.information(self, "成功", f"快照已创建:\n{filepath}")
                self._load_snapshots()
            else:
                QMessageBox.critical(self, "错误", "创建快照失败")
    
    def _on_restore_snapshot(self):
        """回滚到快照"""
        snapshot = self._get_selected_snapshot()
        if not snapshot:
            return
        
        # 确认操作
        reply = QMessageBox.warning(
            self, "警告 - 回滚操作",
            f"即将回滚到快照:\n\n"
            f"时间: {snapshot.get('timestamp', '')}\n"
            f"路由数量: {snapshot.get('total_routes', 0)}\n\n"
            f"此操作将修改系统路由,建议先创建新快照。\n\n"
            f"是否继续?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 先创建新快照
            create_backup = QMessageBox.question(
                self, "创建备份",
                "是否在回滚前创建当前系统快照?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if create_backup == QMessageBox.StandardButton.Yes:
                self.snapshot_manager.create_system_snapshot(self.route_manager)
            
            # 执行回滚
            filepath = snapshot.get('filepath', '')
            success = self.snapshot_manager.restore_system_snapshot(filepath, self.route_manager)
            
            if success:
                QMessageBox.information(self, "成功", "快照已恢复")
            else:
                QMessageBox.critical(self, "错误", "恢复快照失败,请查看日志")
    
    def _on_export_snapshot(self):
        """导出快照"""
        snapshot = self._get_selected_snapshot()
        if not snapshot:
            return
        
        # 选择保存位置
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出快照",
            snapshot.get('filename', ''),
            "JSON Files (*.json)"
        )
        
        if filepath:
            import shutil
            try:
                shutil.copy(snapshot.get('filepath', ''), filepath)
                QMessageBox.information(self, "成功", f"快照已导出到:\n{filepath}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败:\n{e}")
    
    def _on_delete_snapshot(self):
        """删除快照"""
        snapshot = self._get_selected_snapshot()
        if not snapshot:
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"是否删除快照:\n\n{snapshot.get('filename', '')}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            filepath = snapshot.get('filepath', '')
            success = self.snapshot_manager.delete_snapshot(filepath)
            
            if success:
                QMessageBox.information(self, "成功", "快照已删除")
                self._load_snapshots()
            else:
                QMessageBox.critical(self, "错误", "删除快照失败")

