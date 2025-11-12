"""
分组管理对话框 - 用于管理路由分组
"""
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QInputDialog, QMessageBox,
    QLabel, QGroupBox
)
from PyQt6.QtCore import Qt
from typing import List

logger = logging.getLogger(__name__)


class GroupDialog(QDialog):
    """分组管理对话框"""
    
    def __init__(self, parent=None, groups: List[str] = None):
        super().__init__(parent)
        
        self.groups = groups or []
        self.modified = False
        
        self.setWindowTitle("分组管理")
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)
        
        self._init_ui()
        self._load_groups()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 说明
        info_label = QLabel(
            "管理路由分组，可以添加、编辑和删除分组。\n"
            "在新增路由时，分组选择器会显示这里管理的所有分组。\n"
            "注意：删除分组不会删除路由，只会清空路由的分组字段。"
        )
        info_label.setStyleSheet(
            "background-color: #EFF6FF; color: #1E40AF; "
            "padding: 10px; border-radius: 4px; border: 1px solid #BFDBFE;"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 分组列表区域
        group_box = QGroupBox("现有分组")
        group_layout = QVBoxLayout()
        
        self.group_list = QListWidget()
        self.group_list.itemDoubleClicked.connect(self._on_edit_group)
        group_layout.addWidget(self.group_list)
        
        group_box.setLayout(group_layout)
        layout.addWidget(group_box)
        
        # 统计信息
        self.stats_label = QLabel("分组数量: 0")
        self.stats_label.setStyleSheet("color: #6B7280; padding: 5px;")
        layout.addWidget(self.stats_label)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("➕ 新增分组")
        add_btn.setStyleSheet(
            "QPushButton { background-color: #10B981; color: white; "
            "padding: 8px 15px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        add_btn.clicked.connect(self._on_add_group)
        button_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("✏️ 编辑分组")
        edit_btn.setStyleSheet(
            "QPushButton { background-color: #3B82F6; color: white; "
            "padding: 8px 15px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #2563EB; }"
        )
        edit_btn.clicked.connect(self._on_edit_group_btn)
        button_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ 删除分组")
        delete_btn.setStyleSheet(
            "QPushButton { background-color: #EF4444; color: white; "
            "padding: 8px 15px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #DC2626; }"
        )
        delete_btn.clicked.connect(self._on_delete_group)
        button_layout.addWidget(delete_btn)
        
        layout.addLayout(button_layout)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("padding: 8px 20px;")
        close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(close_btn)
        
        layout.addLayout(bottom_layout)
        
        self.setLayout(layout)
    
    def _load_groups(self):
        """加载分组列表"""
        self.group_list.clear()
        
        for group in sorted(self.groups):
            item = QListWidgetItem(group)
            self.group_list.addItem(item)
        
        self._update_stats()
    
    def _update_stats(self):
        """更新统计信息"""
        count = len(self.groups)
        self.stats_label.setText(f"分组数量: {count}")
    
    def _on_add_group(self):
        """新增分组"""
        text, ok = QInputDialog.getText(
            self, "新增分组",
            "请输入分组名称:",
            text=""
        )
        
        if ok and text:
            text = text.strip()
            
            if not text:
                QMessageBox.warning(self, "错误", "分组名称不能为空")
                return
            
            if text in self.groups:
                QMessageBox.warning(self, "错误", f"分组 '{text}' 已存在")
                return
            
            self.groups.append(text)
            self.modified = True
            self._load_groups()
            logger.info(f"添加分组: {text}")
    
    def _on_edit_group_btn(self):
        """编辑分组（按钮触发）"""
        current_item = self.group_list.currentItem()
        if current_item:
            self._on_edit_group(current_item)
        else:
            QMessageBox.information(self, "提示", "请先选择一个分组")
    
    def _on_edit_group(self, item: QListWidgetItem = None):
        """编辑分组"""
        if item is None:
            item = self.group_list.currentItem()
        
        if item is None:
            return
        
        old_name = item.text()
        
        text, ok = QInputDialog.getText(
            self, "编辑分组",
            f"修改分组名称:",
            text=old_name
        )
        
        if ok and text:
            text = text.strip()
            
            if not text:
                QMessageBox.warning(self, "错误", "分组名称不能为空")
                return
            
            if text != old_name and text in self.groups:
                QMessageBox.warning(self, "错误", f"分组 '{text}' 已存在")
                return
            
            # 更新分组名称
            index = self.groups.index(old_name)
            self.groups[index] = text
            self.modified = True
            self._load_groups()
            logger.info(f"编辑分组: {old_name} -> {text}")
    
    def _on_delete_group(self):
        """删除分组"""
        current_item = self.group_list.currentItem()
        
        if current_item is None:
            QMessageBox.information(self, "提示", "请先选择一个分组")
            return
        
        group_name = current_item.text()
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除分组 '{group_name}'?\n\n"
            "注意：删除分组不会删除路由，只会清空路由的分组字段。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.groups.remove(group_name)
            self.modified = True
            self._load_groups()
            logger.info(f"删除分组: {group_name}")
    
    def get_groups(self) -> List[str]:
        """获取分组列表"""
        return self.groups.copy()
    
    def is_modified(self) -> bool:
        """是否已修改"""
        return self.modified

