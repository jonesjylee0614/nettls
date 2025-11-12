"""
Profile 管理对话框
"""
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QGroupBox, QMessageBox, QInputDialog, QFileDialog
)
from PyQt6.QtCore import Qt

from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class ProfileDialog(QDialog):
    """Profile管理对话框"""
    
    def __init__(self, parent=None, config_manager: ConfigManager = None):
        """
        初始化对话框
        
        Args:
            parent: 父窗口
            config_manager: 配置管理器
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.selected_profile = None
        self.action = None  # 'load' 或 'load_and_apply'
        
        # 设置窗口
        self.setWindowTitle("Profile 管理")
        self.setModal(True)
        self.setMinimumSize(600, 400)
        
        # 初始化UI
        self._init_ui()
        
        # 加载Profile列表
        self._load_profiles()
    
    def _init_ui(self):
        """初始化UI组件"""
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("Profile 配置管理")
        title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
        layout.addWidget(title)
        
        # Profile列表
        list_group = QGroupBox("现有 Profile")
        list_layout = QVBoxLayout()
        
        self.profile_list = QListWidget()
        self.profile_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.profile_list.itemDoubleClicked.connect(self._on_load_profile)
        list_layout.addWidget(self.profile_list)
        
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # 按钮组1: Profile操作
        button_layout1 = QHBoxLayout()
        
        self.new_btn = QPushButton("新建")
        self.new_btn.clicked.connect(self._on_new_profile)
        button_layout1.addWidget(self.new_btn)
        
        self.rename_btn = QPushButton("重命名")
        self.rename_btn.clicked.connect(self._on_rename_profile)
        self.rename_btn.setEnabled(False)
        button_layout1.addWidget(self.rename_btn)
        
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self._on_delete_profile)
        self.delete_btn.setEnabled(False)
        button_layout1.addWidget(self.delete_btn)
        
        button_layout1.addStretch()
        layout.addLayout(button_layout1)
        
        # 按钮组2: 导入导出
        button_layout2 = QHBoxLayout()
        
        self.import_btn = QPushButton("导入 Profile")
        self.import_btn.clicked.connect(self._on_import_profile)
        button_layout2.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("导出 Profile")
        self.export_btn.clicked.connect(self._on_export_profile)
        self.export_btn.setEnabled(False)
        button_layout2.addWidget(self.export_btn)
        
        button_layout2.addStretch()
        layout.addLayout(button_layout2)
        
        # 按钮组3: 加载操作
        button_layout3 = QHBoxLayout()
        button_layout3.addStretch()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout3.addWidget(self.cancel_btn)
        
        self.load_btn = QPushButton("加载到编辑态")
        self.load_btn.clicked.connect(self._on_load_profile)
        self.load_btn.setEnabled(False)
        button_layout3.addWidget(self.load_btn)
        
        self.load_apply_btn = QPushButton("加载并立即应用")
        self.load_apply_btn.clicked.connect(self._on_load_and_apply_profile)
        self.load_apply_btn.setEnabled(False)
        button_layout3.addWidget(self.load_apply_btn)
        
        layout.addLayout(button_layout3)
        
        self.setLayout(layout)
    
    def _load_profiles(self):
        """加载Profile列表"""
        self.profile_list.clear()
        
        profiles = self.config_manager.list_profiles()
        current_profile = self.config_manager.current_profile
        
        for profile in profiles:
            item = QListWidgetItem(profile)
            
            # 标记当前Profile
            if profile == current_profile:
                item.setText(f"{profile} (当前)")
                item.setForeground(Qt.GlobalColor.blue)
            
            self.profile_list.addItem(item)
    
    def _on_selection_changed(self):
        """选择变化事件"""
        has_selection = len(self.profile_list.selectedItems()) > 0
        self.rename_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.export_btn.setEnabled(has_selection)
        self.load_btn.setEnabled(has_selection)
        self.load_apply_btn.setEnabled(has_selection)
    
    def _get_selected_profile(self) -> str:
        """获取选中的Profile名称"""
        selected_items = self.profile_list.selectedItems()
        if not selected_items:
            return ""
        
        # 去除 "(当前)" 标记
        profile_text = selected_items[0].text()
        return profile_text.replace(" (当前)", "")
    
    def _on_new_profile(self):
        """新建Profile"""
        name, ok = QInputDialog.getText(self, "新建 Profile", "Profile 名称:")
        
        if ok and name:
            # 检查是否已存在
            if name in self.config_manager.list_profiles():
                QMessageBox.warning(self, "错误", f"Profile '{name}' 已存在")
                return
            
            # 创建默认配置
            if self.config_manager.create_default_profile(name):
                QMessageBox.information(self, "成功", f"Profile '{name}' 已创建")
                self._load_profiles()
            else:
                QMessageBox.critical(self, "错误", "创建 Profile 失败")
    
    def _on_rename_profile(self):
        """重命名Profile"""
        old_name = self._get_selected_profile()
        if not old_name:
            return
        
        new_name, ok = QInputDialog.getText(
            self, "重命名 Profile", 
            f"新名称 (原: {old_name}):",
            text=old_name
        )
        
        if ok and new_name and new_name != old_name:
            # 检查新名称是否已存在
            if new_name in self.config_manager.list_profiles():
                QMessageBox.warning(self, "错误", f"Profile '{new_name}' 已存在")
                return
            
            # 导出旧Profile
            import os
            old_path = self.config_manager.get_profile_path(old_name)
            new_path = self.config_manager.get_profile_path(new_name)
            
            try:
                # 读取并修改配置
                import json
                with open(old_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                config['profileName'] = new_name
                
                with open(new_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                
                # 删除旧文件
                os.remove(old_path)
                
                QMessageBox.information(self, "成功", f"Profile 已重命名为 '{new_name}'")
                self._load_profiles()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"重命名失败:\n{e}")
    
    def _on_delete_profile(self):
        """删除Profile"""
        profile_name = self._get_selected_profile()
        if not profile_name:
            return
        
        # 不允许删除当前Profile
        if profile_name == self.config_manager.current_profile:
            QMessageBox.warning(self, "错误", "不能删除当前正在使用的 Profile")
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"是否删除 Profile '{profile_name}'?\n\n此操作不可恢复!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.config_manager.delete_profile(profile_name):
                QMessageBox.information(self, "成功", f"Profile '{profile_name}' 已删除")
                self._load_profiles()
            else:
                QMessageBox.critical(self, "错误", "删除 Profile 失败")
    
    def _on_import_profile(self):
        """导入Profile"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "导入 Profile",
            "", "JSON Files (*.json)"
        )
        
        if not filepath:
            return
        
        # 询问Profile名称
        name, ok = QInputDialog.getText(self, "导入 Profile", "Profile 名称:")
        
        if ok and name:
            if self.config_manager.import_profile(filepath, name):
                QMessageBox.information(self, "成功", f"Profile '{name}' 已导入")
                self._load_profiles()
            else:
                QMessageBox.critical(self, "错误", "导入 Profile 失败")
    
    def _on_export_profile(self):
        """导出Profile"""
        profile_name = self._get_selected_profile()
        if not profile_name:
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出 Profile",
            f"{profile_name}.json",
            "JSON Files (*.json)"
        )
        
        if filepath:
            if self.config_manager.export_profile(profile_name, filepath):
                QMessageBox.information(self, "成功", f"Profile 已导出到:\n{filepath}")
            else:
                QMessageBox.critical(self, "错误", "导出 Profile 失败")
    
    def _on_load_profile(self):
        """加载Profile到编辑态"""
        profile_name = self._get_selected_profile()
        if not profile_name:
            return
        
        self.selected_profile = profile_name
        self.action = "load"
        self.accept()
    
    def _on_load_and_apply_profile(self):
        """加载Profile并立即应用"""
        profile_name = self._get_selected_profile()
        if not profile_name:
            return
        
        reply = QMessageBox.question(
            self, "确认",
            f"加载 Profile '{profile_name}' 并立即应用到系统?\n\n"
            "这将修改系统路由。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.selected_profile = profile_name
            self.action = "load_and_apply"
            self.accept()
    
    def get_result(self) -> tuple:
        """
        获取结果
        
        Returns:
            tuple: (Profile名称, 操作类型)
        """
        return self.selected_profile, self.action

