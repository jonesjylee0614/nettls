"""
路由新增/编辑对话框
"""
import logging
from typing import Tuple
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox, QCheckBox,
    QTextEdit, QPushButton, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt

from core.route_manager import Route, RouteManager
from core.interface_manager import NetworkInterface
from core.validator import Validator

logger = logging.getLogger(__name__)


class RouteDialog(QDialog):
    """路由新增/编辑对话框"""
    
    def __init__(self, parent=None, route: Route = None, interfaces: list = None, default_gateway: str = None):
        """
        初始化对话框
        
        Args:
            parent: 父窗口
            route: 要编辑的路由(None 表示新增)
            interfaces: 可用接口列表
            default_gateway: 默认网关
        """
        super().__init__(parent)
        
        self.route = route
        self.interfaces = interfaces or []
        self.is_edit = route is not None
        self.default_gateway = default_gateway
        
        # 结果
        self.result_route: Route = None
        self.should_apply: bool = False  # 是否立即应用到系统
        
        # 设置窗口
        self.setWindowTitle("编辑路由" if self.is_edit else "新增路由")
        self.setModal(True)
        self.setMinimumWidth(600)
        
        # 初始化UI
        self._init_ui()
        
        # 如果是编辑模式,加载路由数据
        if self.is_edit:
            self._load_route_data()
    
    def _init_ui(self):
        """初始化UI组件"""
        layout = QVBoxLayout()
        
        # 基本信息组
        basic_group = self._create_basic_group()
        layout.addWidget(basic_group)
        
        # 高级选项组
        advanced_group = self._create_advanced_group()
        layout.addWidget(advanced_group)
        
        # 描述和分组
        desc_group = self._create_desc_group()
        layout.addWidget(desc_group)
        
        # 命令预览组
        preview_group = self._create_preview_group()
        layout.addWidget(preview_group)
        
        # 验证信息标签
        self.validation_label = QLabel()
        self.validation_label.setStyleSheet("color: red; padding: 5px;")
        self.validation_label.setWordWrap(True)
        self.validation_label.setVisible(False)
        layout.addWidget(self.validation_label)
        
        # 按钮
        button_layout = self._create_buttons()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 所有UI创建完成后,连接信号
        self._connect_signals()
    
    def _create_basic_group(self) -> QGroupBox:
        """创建基本信息组"""
        group = QGroupBox("基本信息")
        form_layout = QFormLayout()
        
        # 目标地址
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("支持 IP、CIDR 或域名，如 192.168.1.0/24")
        # 暂不连接信号,等所有UI创建完成后再连接
        form_layout.addRow("目标地址*:", self.target_input)
        
        # 前缀长度（仅对 IP 和域名显示）
        self.prefix_input = QSpinBox()
        self.prefix_input.setRange(1, 32)
        self.prefix_input.setValue(32)
        # 暂不连接信号,等所有UI创建完成后再连接
        form_layout.addRow("前缀长度:", self.prefix_input)
        
        # 掩码（只读显示）
        self.mask_display = QLineEdit()
        self.mask_display.setReadOnly(True)
        self.mask_display.setStyleSheet("background-color: #f0f0f0;")
        form_layout.addRow("子网掩码:", self.mask_display)
        
        # 网关
        self.gateway_input = QLineEdit()
        self.gateway_input.setPlaceholderText("网关 IP 地址")
        
        # 如果有默认网关，设置默认值
        if not self.is_edit and self.default_gateway:
            self.gateway_input.setText(self.default_gateway)
        
        form_layout.addRow("网关*:", self.gateway_input)
        
        # 接口选择
        self.interface_combo = QComboBox()
        # 暂不连接信号,等所有UI创建完成后再连接
        
        # 填充接口列表
        for interface in self.interfaces:
            display_text = f"{interface.name} (ifIndex: {interface.if_index})"
            self.interface_combo.addItem(display_text, interface)
        
        form_layout.addRow("接口*:", self.interface_combo)
        
        # Metric
        self.metric_input = QSpinBox()
        self.metric_input.setRange(1, 999)
        self.metric_input.setValue(5)
        form_layout.addRow("Metric:", self.metric_input)
        
        group.setLayout(form_layout)
        return group
    
    def _create_advanced_group(self) -> QGroupBox:
        """创建高级选项组"""
        group = QGroupBox("高级选项")
        layout = QVBoxLayout()
        
        # 持久化
        self.persistent_checkbox = QCheckBox("持久化路由 (-p)")
        self.persistent_checkbox.setChecked(True)
        self.persistent_checkbox.setToolTip("勾选后路由将在重启后保留")
        layout.addWidget(self.persistent_checkbox)
        
        # 验证连通性
        self.verify_checkbox = QCheckBox("应用后验证连通性")
        self.verify_checkbox.setChecked(True)
        layout.addWidget(self.verify_checkbox)
        
        # 固定解析（仅对域名有效）
        self.pin_checkbox = QCheckBox("固定域名解析 (Pin)")
        self.pin_checkbox.setEnabled(False)
        self.pin_checkbox.setToolTip("域名解析后固定 IP，离线时仍可使用")
        layout.addWidget(self.pin_checkbox)
        
        group.setLayout(layout)
        return group
    
    def _create_desc_group(self) -> QGroupBox:
        """创建描述和分组"""
        group = QGroupBox("描述与分组")
        form_layout = QFormLayout()
        
        # 描述
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("路由的用途和说明...")
        self.desc_input.setMaximumHeight(80)
        form_layout.addRow("描述*:", self.desc_input)
        
        # 分组
        self.group_input = QComboBox()
        self.group_input.setEditable(True)
        self.group_input.addItems(["", "aliyun", "office", "devops", "lab", "debug"])
        form_layout.addRow("分组:", self.group_input)
        
        group.setLayout(form_layout)
        return group
    
    def _create_preview_group(self) -> QGroupBox:
        """创建命令预览组"""
        group = QGroupBox("命令预览")
        layout = QVBoxLayout()
        
        # 命令预览文本框
        self.command_preview = QTextEdit()
        self.command_preview.setReadOnly(True)
        self.command_preview.setMaximumHeight(100)
        self.command_preview.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10pt;
                border: 1px solid #ccc;
                padding: 5px;
            }
        """)
        self.command_preview.setPlaceholderText("命令预览将在这里显示...")
        layout.addWidget(self.command_preview)
        
        # 立即更新按钮
        update_btn = QPushButton("刷新预览")
        update_btn.clicked.connect(self._update_command_preview)
        layout.addWidget(update_btn)
        
        group.setLayout(layout)
        return group
    
    def _create_buttons(self) -> QHBoxLayout:
        """创建按钮组"""
        layout = QHBoxLayout()
        
        # 立即应用选项
        self.apply_immediately_checkbox = QCheckBox("立即应用到系统")
        self.apply_immediately_checkbox.setChecked(True)
        self.apply_immediately_checkbox.setToolTip("保存后立即将路由添加到系统路由表")
        layout.addWidget(self.apply_immediately_checkbox)
        
        layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        
        # 保存按钮
        save_btn = QPushButton("保存")
        save_btn.setDefault(True)
        save_btn.setStyleSheet("background-color: #10B981; color: white; padding: 8px 20px;")
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)
        
        # 保存并继续按钮(仅新增模式)
        if not self.is_edit:
            save_continue_btn = QPushButton("保存并继续新增")
            save_continue_btn.clicked.connect(self._on_save_and_continue)
            layout.addWidget(save_continue_btn)
        
        return layout
    
    def _connect_signals(self):
        """连接信号(在所有UI创建完成后调用)"""
        # 连接目标地址变化信号
        self.target_input.textChanged.connect(self._on_target_changed)
        
        # 连接前缀长度变化信号
        self.prefix_input.valueChanged.connect(self._update_mask_display)
        
        # 连接接口选择变化信号
        self.interface_combo.currentIndexChanged.connect(self._on_interface_changed)
        
        # 初始化掩码显示
        self._update_mask_display()
    
    def _load_route_data(self):
        """加载路由数据到表单"""
        if not self.route:
            return
        
        # 目标
        self.target_input.setText(self.route.target)
        
        # 前缀长度
        self.prefix_input.setValue(self.route.prefix_length)
        
        # 网关
        self.gateway_input.setText(self.route.gateway)
        
        # 接口
        for i in range(self.interface_combo.count()):
            interface = self.interface_combo.itemData(i)
            if interface and interface.name == self.route.interface_name:
                self.interface_combo.setCurrentIndex(i)
                break
        
        # Metric
        self.metric_input.setValue(self.route.metric)
        
        # 高级选项
        self.persistent_checkbox.setChecked(self.route.persistent)
        self.pin_checkbox.setChecked(self.route.pin)
        
        # 描述和分组
        self.desc_input.setPlainText(self.route.desc)
        self.group_input.setCurrentText(self.route.group)
    
    def _on_target_changed(self, text: str):
        """目标地址变化事件"""
        # 验证目标地址
        valid, error, target_type = Validator.validate_target(text)
        
        if valid:
            # 根据类型更新UI
            if target_type == "cidr":
                # CIDR 格式,自动提取前缀长度
                parts = text.split('/')
                if len(parts) == 2:
                    try:
                        prefix = int(parts[1])
                        self.prefix_input.setValue(prefix)
                        self.prefix_input.setEnabled(False)
                    except ValueError:
                        pass
            elif target_type == "ip":
                # IP 格式,启用前缀长度输入
                self.prefix_input.setEnabled(True)
            elif target_type == "domain":
                # 域名格式,启用前缀长度和 Pin 选项
                self.prefix_input.setEnabled(True)
                self.pin_checkbox.setEnabled(True)
            
            self._update_mask_display()
            self.validation_label.setVisible(False)
            self._update_command_preview()
        else:
            if text:  # 只有在有输入时才显示错误
                self.validation_label.setText(error)
                self.validation_label.setVisible(True)
    
    def _update_mask_display(self):
        """更新掩码显示"""
        prefix_length = self.prefix_input.value()
        mask = RouteManager.prefix_to_mask(prefix_length)
        self.mask_display.setText(mask)
        self._update_command_preview()
    
    def _update_command_preview(self):
        """更新命令预览"""
        # 检查 command_preview 是否已创建
        if not hasattr(self, 'command_preview'):
            return
        
        try:
            # 获取表单数据
            target = self.target_input.text().strip()
            if not target:
                self.command_preview.setPlainText("请输入目标地址...")
                return
            
            gateway = self.gateway_input.text().strip()
            if not gateway:
                gateway = "<网关>"
            
            # 获取目标IP和前缀长度
            if '/' in target:
                target_ip = target.split('/')[0]
                prefix_length = int(target.split('/')[1])
            else:
                target_ip = target
                prefix_length = self.prefix_input.value()
            
            mask = RouteManager.prefix_to_mask(prefix_length)
            metric = self.metric_input.value()
            
            # 获取接口
            interface = self.interface_combo.currentData()
            if_index = interface.if_index if interface else "<ifIndex>"
            
            # 构建命令
            persistent_flag = "-p" if self.persistent_checkbox.isChecked() else ""
            
            # 添加命令
            add_cmd = f"route {persistent_flag} add {target_ip} mask {mask} {gateway} IF {if_index} metric {metric}"
            
            # 删除命令
            del_cmd = f"route delete {target_ip}"
            
            # 显示命令
            preview_text = f"# 添加路由命令:\n{add_cmd}\n\n"
            preview_text += f"# 删除路由命令:\n{del_cmd}"
            
            self.command_preview.setPlainText(preview_text)
            
        except Exception as e:
            self.command_preview.setPlainText(f"命令预览错误: {e}")
    
    def _on_interface_changed(self, index: int):
        """接口选择变化事件"""
        if index < 0:
            return
        
        interface = self.interface_combo.itemData(index)
        if interface and interface.gateway:
            # 自动填充网关
            if not self.gateway_input.text():
                self.gateway_input.setText(interface.gateway)
        
        self._update_command_preview()
    
    def _validate_form(self) -> Tuple[bool, str]:
        """
        验证表单数据
        
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        # 验证目标地址
        target = self.target_input.text().strip()
        valid, error, target_type = Validator.validate_target(target)
        if not valid:
            return False, f"目标地址错误: {error}"
        
        # 验证网关
        gateway = self.gateway_input.text().strip()
        if not gateway:
            return False, "网关不能为空"
        
        valid, error = Validator.validate_ip(gateway)
        if not valid:
            return False, f"网关地址错误: {error}"
        
        # 验证接口
        if self.interface_combo.currentIndex() < 0:
            return False, "请选择接口"
        
        interface = self.interface_combo.currentData()
        if not interface:
            return False, "接口无效"
        
        # 验证网关与接口是否在同一网段
        if interface.ip_address and interface.subnet_mask:
            valid, error = Validator.validate_gateway(
                gateway, 
                interface.ip_address, 
                interface.subnet_mask
            )
            if not valid:
                return False, error
        
        # 验证描述
        desc = self.desc_input.toPlainText().strip()
        valid, error = Validator.validate_description(desc, required=True)
        if not valid:
            return False, f"描述错误: {error}"
        
        # 检查危险路由
        is_dangerous, warning = Validator.is_dangerous_route(target)
        if is_dangerous:
            reply = QMessageBox.warning(
                self, "警告", 
                f"{warning}\n\n是否继续?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return False, "用户取消操作"
        
        return True, ""
    
    def _create_route_from_form(self) -> Route:
        """从表单创建路由对象"""
        # 获取目标地址和前缀长度
        target = self.target_input.text().strip()
        
        # 如果是 CIDR 格式,提取 IP 部分
        if '/' in target:
            parts = target.split('/')
            target_ip = parts[0]
            prefix_length = int(parts[1])
        else:
            target_ip = target
            prefix_length = self.prefix_input.value()
        
        # 获取接口
        interface = self.interface_combo.currentData()
        
        # 创建路由对象
        route = Route(
            enabled=True,
            target=target_ip,
            prefix_length=prefix_length,
            gateway=self.gateway_input.text().strip(),
            interface_name=interface.name if interface else "",
            metric=self.metric_input.value(),
            persistent=self.persistent_checkbox.isChecked(),
            pin=self.pin_checkbox.isChecked(),
            group=self.group_input.currentText().strip(),
            desc=self.desc_input.toPlainText().strip()
        )
        
        return route
    
    def _on_save(self):
        """保存按钮点击事件"""
        # 验证表单
        valid, error = self._validate_form()
        if not valid:
            QMessageBox.warning(self, "验证失败", error)
            return
        
        # 创建路由对象
        self.result_route = self._create_route_from_form()
        
        # 保存是否立即应用标志
        self.should_apply = self.apply_immediately_checkbox.isChecked()
        
        # 关闭对话框
        self.accept()
    
    def _on_save_and_continue(self):
        """保存并继续新增"""
        # 验证表单
        valid, error = self._validate_form()
        if not valid:
            QMessageBox.warning(self, "验证失败", error)
            return
        
        # 创建路由对象
        self.result_route = self._create_route_from_form()
        
        # 通知父窗口保存
        self.accept()
        
        # 清空表单,准备下一次输入
        self.target_input.clear()
        self.desc_input.clear()
        self.result_route = None
        
        # 重新显示对话框
        self.show()
    
    def get_route(self) -> Route:
        """获取结果路由对象"""
        return self.result_route
    
    def should_apply_immediately(self) -> bool:
        """是否立即应用到系统"""
        return self.should_apply

