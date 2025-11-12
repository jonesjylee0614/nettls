"""
主窗口 - 路由管理工具的主界面
"""
import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QToolBar, QStatusBar, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QLabel, QSplitter, QTreeWidget,
    QTreeWidgetItem, QLineEdit, QHeaderView, QMessageBox,
    QCheckBox, QDialog, QTabWidget, QFileDialog, QProgressDialog,
    QGroupBox, QGridLayout, QInputDialog, QFormLayout
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QIcon

from core.interface_manager import InterfaceManager
from core.route_manager import RouteManager, Route
from core.config_manager import ConfigManager
from core.apply_manager import ApplyManager
from core.verify_manager import VerifyManager
from core.snapshot_manager import SnapshotManager
from ui.dialogs.route_dialog import RouteDialog
from ui.dialogs.diff_dialog import DiffDialog
from ui.dialogs.verify_dialog import VerifyDialog
from ui.dialogs.snapshot_dialog import SnapshotDialog
from ui.dialogs.profile_dialog import ProfileDialog

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化管理器
        self.interface_manager = InterfaceManager()
        self.route_manager = RouteManager()
        self.config_manager = ConfigManager()
        self.apply_manager = ApplyManager(self.route_manager, self.interface_manager)
        self.verify_manager = VerifyManager()
        self.snapshot_manager = SnapshotManager()
        
        # 当前路由列表
        self.routes: list[Route] = []
        
        # 设置窗口
        self.setWindowTitle("路由管理工具 - NetTLS Route Manager")
        self.setGeometry(100, 100, 1400, 800)
        
        # 初始化 UI
        self._init_ui()
        
        # 加载默认配置
        self._load_default_profile()
        
        # 延迟刷新数据(避免启动卡顿)
        QTimer.singleShot(100, self._delayed_refresh)
    
    def _init_ui(self):
        """初始化UI组件"""
        # 创建菜单栏
        self._create_menubar()
        
        # 创建工具栏
        self._create_toolbar()
        
        # 创建中心窗口部件
        self._create_central_widget()
        
        # 创建状态栏
        self._create_statusbar()
    
    def _create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        
        # 新增路由
        add_action = QAction("新增路由", self)
        add_action.setShortcut("Ctrl+N")
        add_action.triggered.connect(self._on_add_route)
        file_menu.addAction(add_action)
        
        file_menu.addSeparator()
        
        # 导入
        import_action = QAction("导入...", self)
        import_action.triggered.connect(self._on_import)
        file_menu.addAction(import_action)
        
        # 导出
        export_action = QAction("导出...", self)
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")
        
        # 刷新
        refresh_action = QAction("刷新", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._refresh_all)
        edit_menu.addAction(refresh_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        # 关于
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Profile 选择
        toolbar.addWidget(QLabel("  Profile: "))
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(150)
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        toolbar.addWidget(self.profile_combo)
        
        # Profile 管理按钮
        profile_mgr_btn = QPushButton("管理...")
        profile_mgr_btn.clicked.connect(self._on_profile_manage)
        toolbar.addWidget(profile_mgr_btn)
        
        toolbar.addSeparator()
        
        # 新增路由按钮
        add_btn = QPushButton("新增路由")
        add_btn.clicked.connect(self._on_add_route)
        toolbar.addWidget(add_btn)
        
        toolbar.addSeparator()
        
        # 读取接口按钮
        refresh_if_btn = QPushButton("读取接口")
        refresh_if_btn.clicked.connect(self._on_refresh_interfaces)
        toolbar.addWidget(refresh_if_btn)
        
        # 应用按钮
        apply_btn = QPushButton("应用")
        apply_btn.clicked.connect(self._on_apply)
        toolbar.addWidget(apply_btn)
        
        # 验证按钮
        verify_btn = QPushButton("验证")
        verify_btn.clicked.connect(self._on_verify)
        toolbar.addWidget(verify_btn)
        
        # 回滚按钮
        rollback_btn = QPushButton("回滚")
        rollback_btn.clicked.connect(self._on_rollback)
        toolbar.addWidget(rollback_btn)
        
        toolbar.addSeparator()
        
        # 设置按钮
        settings_btn = QPushButton("设置")
        settings_btn.clicked.connect(self._on_settings)
        toolbar.addWidget(settings_btn)
        
        # 帮助按钮
        help_btn = QPushButton("帮助")
        help_btn.clicked.connect(self._on_help)
        toolbar.addWidget(help_btn)
    
    def _create_central_widget(self):
        """创建中心窗口部件"""
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 标签页1: 配置路由
        config_tab = self._create_config_routes_tab()
        self.tab_widget.addTab(config_tab, "配置路由")
        
        # 标签页2: 系统路由
        system_tab = self._create_system_routes_tab()
        self.tab_widget.addTab(system_tab, "系统路由")
        
        # 监听标签页切换事件
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        
        # 默认显示系统路由标签页
        self.tab_widget.setCurrentIndex(1)
        
        self.setCentralWidget(self.tab_widget)
    
    def _create_config_routes_tab(self) -> QWidget:
        """创建配置路由标签页"""
        # 创建分割器(左侧分组树,右侧路由表格)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧:分组树
        left_widget = self._create_group_tree()
        splitter.addWidget(left_widget)
        
        # 右侧:路由表格区域
        right_widget = self._create_routes_area()
        splitter.addWidget(right_widget)
        
        # 设置分割比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        
        return splitter
    
    def _create_system_routes_tab(self) -> QWidget:
        """创建系统路由标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        # 新增路由按钮
        add_route_btn = QPushButton("新增路由")
        add_route_btn.setStyleSheet("background-color: #10B981; color: white; padding: 5px 15px;")
        add_route_btn.clicked.connect(self._on_add_system_route)
        toolbar.addWidget(add_route_btn)
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._on_refresh_system_routes)
        toolbar.addWidget(refresh_btn)
        
        # 网关筛选
        toolbar.addWidget(QLabel("  网关筛选: "))
        self.gateway_filter_combo = QComboBox()
        self.gateway_filter_combo.setMinimumWidth(150)
        self.gateway_filter_combo.currentIndexChanged.connect(self._on_gateway_filter_changed)
        toolbar.addWidget(self.gateway_filter_combo)
        
        toolbar.addStretch()
        
        # 统计标签
        self.system_routes_count_label = QLabel("系统路由: 0 条")
        toolbar.addWidget(self.system_routes_count_label)
        
        layout.addLayout(toolbar)
        
        # 表格
        self.system_routes_table = QTableWidget()
        self.system_routes_table.setColumnCount(6)
        self.system_routes_table.setHorizontalHeaderLabels([
            "目标", "网关", "接口索引", "Metric", "协议", "操作"
        ])
        
        # 设置列宽
        header = self.system_routes_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # 目标
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # 网关
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # 接口索引
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Metric
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # 协议
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # 操作
        
        # 设置表格属性
        self.system_routes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.system_routes_table.setAlternatingRowColors(True)
        self.system_routes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.system_routes_table)
        
        widget.setLayout(layout)
        return widget
    
    def _create_group_tree(self) -> QWidget:
        """创建分组树"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 路由统计信息面板
        stats_group = QGroupBox("路由统计")
        stats_layout = QGridLayout()
        
        # 统计标签
        self.stats_total_label = QLabel("总路由: 0")
        self.stats_enabled_label = QLabel("已启用: 0")
        self.stats_applied_label = QLabel("已应用: 0")
        self.stats_system_label = QLabel("系统路由: 0")
        
        stats_layout.addWidget(QLabel("📊"), 0, 0)
        stats_layout.addWidget(self.stats_total_label, 0, 1)
        stats_layout.addWidget(QLabel("✓"), 1, 0)
        stats_layout.addWidget(self.stats_enabled_label, 1, 1)
        stats_layout.addWidget(QLabel("🌐"), 2, 0)
        stats_layout.addWidget(self.stats_applied_label, 2, 1)
        stats_layout.addWidget(QLabel("💾"), 3, 0)
        stats_layout.addWidget(self.stats_system_label, 3, 1)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # 分组标题
        title = QLabel("分组")
        title.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
        layout.addWidget(title)
        
        # 树控件
        self.group_tree = QTreeWidget()
        self.group_tree.setHeaderHidden(True)
        self.group_tree.itemClicked.connect(self._on_group_selected)
        layout.addWidget(self.group_tree)
        
        # WireGuard 警告标签
        self.wg_warning = QLabel()
        self.wg_warning.setStyleSheet("background-color: #FEF3C7; color: #92400E; padding: 8px; border-radius: 4px;")
        self.wg_warning.setWordWrap(True)
        self.wg_warning.setVisible(False)
        layout.addWidget(self.wg_warning)
        
        widget.setLayout(layout)
        return widget
    
    def _create_routes_area(self) -> QWidget:
        """创建路由表格区域"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 搜索栏
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("按目标、描述或分组过滤...")
        self.search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # 表格
        self.routes_table = QTableWidget()
        self.routes_table.setColumnCount(12)
        self.routes_table.setHorizontalHeaderLabels([
            "启用", "目标", "掩码", "网关", "接口名", 
            "Metric", "持久", "系统状态", "描述", "分组", "结果", "操作"
        ])
        
        # 设置列宽
        header = self.routes_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # 启用
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # 目标
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # 掩码
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # 网关
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # 接口名
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Metric
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # 持久
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # 系统状态
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)  # 描述
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)  # 分组
        header.setSectionResizeMode(10, QHeaderView.ResizeMode.Stretch)  # 结果
        header.setSectionResizeMode(11, QHeaderView.ResizeMode.ResizeToContents)  # 操作
        
        # 设置表格属性
        self.routes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.routes_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.routes_table)
        
        widget.setLayout(layout)
        return widget
    
    def _create_statusbar(self):
        """创建状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # 默认接口标签
        self.status_interface = QLabel("默认物理接口: 未设置")
        self.statusbar.addWidget(self.status_interface)
        
        self.statusbar.addWidget(QLabel(" | "))
        
        # WireGuard 状态标签
        self.status_wireguard = QLabel("WireGuard: 未检测")
        self.statusbar.addWidget(self.status_wireguard)
        
        self.statusbar.addWidget(QLabel(" | "))
        
        # 上次应用标签
        self.status_last_apply = QLabel("上次应用: 从未")
        self.statusbar.addWidget(self.status_last_apply)
        
        self.statusbar.addPermanentWidget(QLabel(" | "))
        
        # 当前 Profile 标签
        self.status_profile = QLabel("Profile: home")
        self.statusbar.addPermanentWidget(self.status_profile)
    
    def _load_default_profile(self):
        """加载默认 Profile"""
        # 加载 home.json
        if not self.config_manager.load_profile("home"):
            # 如果加载失败,创建默认配置
            self.config_manager.create_default_profile("home")
            self.config_manager.load_profile("home")
        
        # 加载路由列表
        self.routes = self.config_manager.get_routes()
        
        # 更新 Profile 下拉列表
        self._update_profile_combo()
    
    def _update_profile_combo(self):
        """更新 Profile 下拉列表"""
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        
        profiles = self.config_manager.list_profiles()
        self.profile_combo.addItems(profiles)
        
        # 选中当前 Profile
        index = self.profile_combo.findText(self.config_manager.current_profile)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)
        
        self.profile_combo.blockSignals(False)
    
    def _delayed_refresh(self):
        """延迟刷新(启动后异步执行)"""
        from PyQt6.QtWidgets import QApplication
        
        # 创建加载进度对话框
        progress = QProgressDialog("正在加载网络配置...", None, 0, 3, self)
        progress.setWindowTitle("NetTLS Route Manager")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)  # 不显示取消按钮
        progress.setAutoClose(True)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()  # 确保对话框显示
        
        # 第1步: 刷新接口
        progress.setLabelText("正在读取网络接口...")
        progress.setValue(1)
        QApplication.processEvents()  # 更新界面
        self.interface_manager.refresh_interfaces()
        QApplication.processEvents()  # 处理事件
        
        # 第2步: 刷新系统路由
        progress.setLabelText("正在读取系统路由...")
        progress.setValue(2)
        QApplication.processEvents()  # 更新界面
        self.route_manager.refresh_system_routes()
        QApplication.processEvents()  # 处理事件
        
        # 第3步: 更新界面
        progress.setLabelText("正在更新界面...")
        progress.setValue(3)
        QApplication.processEvents()  # 更新界面
        self._update_group_tree()
        self._update_routes_table()
        self._update_statusbar()
        self._update_route_stats()
        QApplication.processEvents()  # 处理事件
        
        # 完成
        progress.close()
        
        # 在对话框关闭后再更新系统路由表格(确保能正确渲染)
        QTimer.singleShot(50, self._update_system_routes_table)
        
        self.statusbar.showMessage("加载完成", 3000)
    
    def _refresh_all(self):
        """刷新所有数据"""
        # 刷新接口列表
        self.interface_manager.refresh_interfaces()
        
        # 刷新系统路由
        self.route_manager.refresh_system_routes()
        
        # 更新 UI
        self._update_group_tree()
        self._update_routes_table()
        self._update_statusbar()
        self._update_system_routes_table()
        self._update_route_stats()
        
        self.statusbar.showMessage("刷新完成", 3000)
    
    def _update_group_tree(self):
        """更新分组树"""
        self.group_tree.clear()
        
        # 添加 "All" 节点
        all_item = QTreeWidgetItem(["All ({})".format(len(self.routes))])
        all_item.setData(0, Qt.ItemDataRole.UserRole, "All")
        self.group_tree.addTopLevelItem(all_item)
        
        # 统计各分组的路由数量
        groups = {}
        ungrouped_count = 0
        
        for route in self.routes:
            if route.group:
                groups[route.group] = groups.get(route.group, 0) + 1
            else:
                ungrouped_count += 1
        
        # 添加 "未分组" 节点
        if ungrouped_count > 0:
            ungrouped_item = QTreeWidgetItem([f"未分组 ({ungrouped_count})"])
            ungrouped_item.setData(0, Qt.ItemDataRole.UserRole, "")
            self.group_tree.addTopLevelItem(ungrouped_item)
        
        # 添加各分组节点
        for group_name, count in sorted(groups.items()):
            group_item = QTreeWidgetItem([f"{group_name} ({count})"])
            group_item.setData(0, Qt.ItemDataRole.UserRole, group_name)
            self.group_tree.addTopLevelItem(group_item)
        
        # 默认选中 "All"
        all_item.setSelected(True)
    
    def _update_routes_table(self, filter_group: str = "All", search_text: str = ""):
        """
        更新路由表格
        
        Args:
            filter_group: 过滤分组("All" 表示全部)
            search_text: 搜索文本
        """
        self.routes_table.setRowCount(0)
        
        # 过滤路由
        filtered_routes = []
        for route in self.routes:
            # 分组过滤
            if filter_group != "All":
                if filter_group == "" and route.group:
                    continue
                elif route.group != filter_group:
                    continue
            
            # 搜索过滤
            if search_text:
                search_lower = search_text.lower()
                if (search_lower not in route.target.lower() and
                    search_lower not in route.desc.lower() and
                    search_lower not in route.group.lower()):
                    continue
            
            filtered_routes.append(route)
        
        # 填充表格
        for row, route in enumerate(filtered_routes):
            self.routes_table.insertRow(row)
            
            # 启用复选框
            enabled_checkbox = QCheckBox()
            enabled_checkbox.setChecked(route.enabled)
            enabled_widget = QWidget()
            enabled_layout = QHBoxLayout(enabled_widget)
            enabled_layout.addWidget(enabled_checkbox)
            enabled_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            enabled_layout.setContentsMargins(0, 0, 0, 0)
            self.routes_table.setCellWidget(row, 0, enabled_widget)
            
            # 目标
            self.routes_table.setItem(row, 1, QTableWidgetItem(route.get_destination_prefix()))
            
            # 掩码
            self.routes_table.setItem(row, 2, QTableWidgetItem(route.get_subnet_mask()))
            
            # 网关
            self.routes_table.setItem(row, 3, QTableWidgetItem(route.gateway))
            
            # 接口名
            self.routes_table.setItem(row, 4, QTableWidgetItem(route.interface_name))
            
            # Metric
            self.routes_table.setItem(row, 5, QTableWidgetItem(str(route.metric)))
            
            # 持久
            self.routes_table.setItem(row, 6, QTableWidgetItem("是" if route.persistent else "否"))
            
            # 系统状态 - 检查路由是否在系统中
            system_status = self._check_route_in_system(route)
            status_item = QTableWidgetItem(system_status['text'])
            if system_status['exists']:
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                status_item.setForeground(Qt.GlobalColor.gray)
            self.routes_table.setItem(row, 7, status_item)
            
            # 描述
            self.routes_table.setItem(row, 8, QTableWidgetItem(route.desc))
            
            # 分组
            self.routes_table.setItem(row, 9, QTableWidgetItem(route.group))
            
            # 结果
            result_text = route.last_apply_result or "待应用"
            self.routes_table.setItem(row, 10, QTableWidgetItem(result_text))
            
            # 操作按钮
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            
            edit_btn = QPushButton("编辑")
            edit_btn.clicked.connect(lambda checked, r=route: self._on_edit_route(r))
            actions_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(lambda checked, r=route: self._on_delete_route(r))
            actions_layout.addWidget(delete_btn)
            
            self.routes_table.setCellWidget(row, 11, actions_widget)
    
    def _update_statusbar(self):
        """更新状态栏"""
        # 更新默认接口
        default_if = self.config_manager.get_default_interface()
        if default_if:
            interface = self.interface_manager.get_interface_by_name(default_if)
            if interface:
                self.status_interface.setText(
                    f"默认物理接口: {interface.name} / ifIndex {interface.if_index} / 网关 {interface.gateway}"
                )
            else:
                self.status_interface.setText(f"默认物理接口: {default_if} (未找到)")
        else:
            self.status_interface.setText("默认物理接口: 未设置")
        
        # 更新 WireGuard 状态
        is_full_tunnel, warning_msg = self.interface_manager.detect_wireguard()
        if is_full_tunnel:
            self.status_wireguard.setText("WireGuard: 全隧道")
            self.status_wireguard.setStyleSheet("color: orange;")
            self.wg_warning.setText(warning_msg)
            self.wg_warning.setVisible(True)
        else:
            self.status_wireguard.setText("WireGuard: 未检测")
            self.status_wireguard.setStyleSheet("")
            self.wg_warning.setVisible(False)
        
        # 更新 Profile 名称
        self.status_profile.setText(f"Profile: {self.config_manager.current_profile}")
    
    def _update_system_routes_table(self, gateway_filter: str = None):
        """
        更新系统路由表格
        
        Args:
            gateway_filter: 网关筛选条件 (None 或 "All (全部)" 表示全部)
        """
        system_routes = self.route_manager.get_system_routes()
        
        # 总是更新网关筛选下拉列表(确保数据最新)
        self._update_gateway_filter_combo(system_routes)
        
        # 如果没有指定筛选条件,从下拉列表获取当前选择的数据
        if gateway_filter is None:
            # 从 itemData 获取实际的网关地址
            current_index = self.gateway_filter_combo.currentIndex()
            if current_index == 0:
                gateway_filter = "All (全部)"
            elif current_index > 0:
                gateway_filter = self.gateway_filter_combo.itemData(current_index)
            else:
                gateway_filter = "All (全部)"
        
        # 过滤路由
        if gateway_filter and gateway_filter != "All (全部)":
            filtered_routes = [r for r in system_routes if r.get('NextHop', '') == gateway_filter]
        else:
            filtered_routes = system_routes
        
        # 更新表格
        self.system_routes_table.setRowCount(0)
        self.system_routes_count_label.setText(f"系统路由: {len(system_routes)} 条 (显示: {len(filtered_routes)})")
        
        for row, route_data in enumerate(filtered_routes):
            self.system_routes_table.insertRow(row)
            
            # 目标
            dest = route_data.get('DestinationPrefix', '')
            self.system_routes_table.setItem(row, 0, QTableWidgetItem(dest))
            
            # 网关
            gateway = route_data.get('NextHop', '')
            self.system_routes_table.setItem(row, 1, QTableWidgetItem(gateway))
            
            # 接口索引
            if_index = str(route_data.get('ifIndex', ''))
            self.system_routes_table.setItem(row, 2, QTableWidgetItem(if_index))
            
            # Metric
            metric = str(route_data.get('RouteMetric', ''))
            self.system_routes_table.setItem(row, 3, QTableWidgetItem(metric))
            
            # 协议
            protocol = route_data.get('Protocol', '')
            self.system_routes_table.setItem(row, 4, QTableWidgetItem(protocol))
            
            # 操作按钮
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            
            # 只有 NetMgmt 协议的路由才能删除 (静态路由)
            if protocol == 'NetMgmt':
                delete_btn = QPushButton("删除")
                delete_btn.setStyleSheet("background-color: #FEE2E2; color: #991B1B;")
                delete_btn.clicked.connect(lambda checked, d=dest: self._on_delete_system_route(d))
                actions_layout.addWidget(delete_btn)
            else:
                # 系统路由不可删除
                readonly_label = QLabel("系统路由")
                readonly_label.setStyleSheet("color: gray;")
                actions_layout.addWidget(readonly_label)
            
            self.system_routes_table.setCellWidget(row, 5, actions_widget)
    
    def _check_route_in_system(self, route: Route) -> dict:
        """
        检查配置路由是否在系统中存在
        
        Args:
            route: 配置路由对象
            
        Returns:
            dict: {'exists': bool, 'text': str}
        """
        system_routes = self.route_manager.get_system_routes()
        
        # 获取目标前缀
        target_prefix = route.get_destination_prefix()
        target_ip = route.target.split('/')[0] if '/' in route.target else route.target
        
        # 在系统路由中查找匹配项
        for sys_route in system_routes:
            dest = sys_route.get('DestinationPrefix', '')
            gateway = sys_route.get('NextHop', '')
            
            # 检查目标是否匹配
            if dest == target_prefix or dest.startswith(target_ip):
                # 检查网关是否匹配
                if gateway == route.gateway or gateway == '0.0.0.0':
                    return {'exists': True, 'text': '✓ 已存在'}
        
        return {'exists': False, 'text': '未应用'}
    
    def _update_route_stats(self):
        """更新路由统计信息"""
        # 统计配置路由
        total_routes = len(self.routes)
        enabled_routes = len([r for r in self.routes if r.enabled])
        
        # 统计已应用的路由
        applied_routes = 0
        for route in self.routes:
            if self._check_route_in_system(route)['exists']:
                applied_routes += 1
        
        # 统计系统路由
        system_routes = self.route_manager.get_system_routes()
        system_route_count = len(system_routes)
        
        # 更新标签
        self.stats_total_label.setText(f"总路由: {total_routes}")
        self.stats_enabled_label.setText(f"已启用: {enabled_routes}")
        self.stats_applied_label.setText(f"已应用: {applied_routes}")
        self.stats_system_label.setText(f"系统路由: {system_route_count}")
    
    def _update_gateway_filter_combo(self, system_routes: list):
        """
        更新网关筛选下拉列表
        
        Args:
            system_routes: 系统路由列表
        """
        # 保存当前选择
        current_selection = self.gateway_filter_combo.currentText()
        
        # 阻塞信号
        self.gateway_filter_combo.blockSignals(True)
        self.gateway_filter_combo.clear()
        
        # 统计各网关的路由数量
        gateway_counts = {}
        for route in system_routes:
            gateway = route.get('NextHop', '')
            gateway_counts[gateway] = gateway_counts.get(gateway, 0) + 1
        
        # 添加 "All"选项
        total_count = len(system_routes)
        self.gateway_filter_combo.addItem(f"All (全部) - {total_count} 条")
        
        # 按网关排序(192开头的优先)
        sorted_gateways = sorted(gateway_counts.keys(), key=lambda g: (not g.startswith('192'), g))
        
        # 添加各网关选项
        for gateway in sorted_gateways:
            count = gateway_counts[gateway]
            self.gateway_filter_combo.addItem(f"{gateway} - {count} 条", gateway)
        
        # 恢复选择或默认选择192开头的网关
        if current_selection:
            index = self.gateway_filter_combo.findText(current_selection)
            if index >= 0:
                self.gateway_filter_combo.setCurrentIndex(index)
            else:
                # 找到第一个192开头的网关
                self._select_default_gateway(sorted_gateways)
        else:
            # 首次加载,选择192开头的网关
            self._select_default_gateway(sorted_gateways)
        
        # 取消阻塞信号
        self.gateway_filter_combo.blockSignals(False)
    
    def _select_default_gateway(self, gateways: list):
        """选择默认网关(192开头的第一个)"""
        for i, gateway in enumerate(gateways):
            if gateway.startswith('192'):
                self.gateway_filter_combo.setCurrentIndex(i + 1)  # +1 因为第0项是All
                return
        # 如果没有192开头的,选择All
        self.gateway_filter_combo.setCurrentIndex(0)
    
    # === 事件处理 ===
    
    def _on_tab_changed(self, index: int):
        """标签页切换事件"""
        if index == 1:  # 切换到系统路由标签页
            # 只在表格为空时才刷新(避免重复刷新)
            if self.system_routes_table.rowCount() == 0:
                self._update_system_routes_table()
    
    def _on_refresh_system_routes(self):
        """刷新系统路由"""
        self.statusbar.showMessage("正在刷新系统路由...", 0)
        if self.route_manager.refresh_system_routes():
            self._update_system_routes_table()
            self._update_route_stats()  # 同时更新统计信息
            self.statusbar.showMessage("系统路由刷新完成", 3000)
        else:
            self.statusbar.showMessage("系统路由刷新失败", 3000)
            QMessageBox.warning(self, "警告", "刷新系统路由失败")
    
    def _on_gateway_filter_changed(self, index: int):
        """网关筛选变化事件"""
        # 更新表格(会自动从下拉列表读取当前选择)
        self._update_system_routes_table()
    
    def _on_add_system_route(self):
        """新增系统路由"""
        # 创建简化的对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("新增系统路由")
        dialog.setMinimumWidth(400)
        
        layout = QFormLayout()
        
        # 目标IP输入
        target_input = QLineEdit()
        target_input.setPlaceholderText("例如: 8.8.8.8")
        layout.addRow("目标 IP:", target_input)
        
        # 网关输入(默认192.168.1.1)
        gateway_input = QLineEdit()
        gateway_input.setText("192.168.1.1")
        layout.addRow("网关:", gateway_input)
        
        # Metric输入(默认1)
        metric_input = QLineEdit()
        metric_input.setText("1")
        layout.addRow("Metric:", metric_input)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("添加并应用")
        ok_btn.setStyleSheet("background-color: #10B981; color: white;")
        cancel_btn = QPushButton("取消")
        
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow("", button_layout)
        
        dialog.setLayout(layout)
        
        # 连接信号
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        # 显示对话框
        if dialog.exec() == QDialog.DialogCode.Accepted:
            target = target_input.text().strip()
            gateway = gateway_input.text().strip()
            
            try:
                metric = int(metric_input.text().strip())
            except:
                metric = 1
            
            # 验证输入
            if not target or not gateway:
                QMessageBox.warning(self, "输入错误", "请输入目标 IP 和网关")
                return
            
            # 创建路由对象
            route = Route(
                enabled=True,
                target=target,
                prefix_length=32,  # 默认 /32 主机路由
                gateway=gateway,
                interface_name="",
                metric=metric,
                persistent=True,  # 永久路由
                group="",
                desc=f"手动添加 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            
            # 获取接口索引(从当前接口列表中查找)
            interface = None
            for iface in self.interface_manager.get_all_interfaces():
                if gateway.startswith(iface.gateway.split('.')[0:3]):  # 简单匹配网关所在网段
                    interface = iface
                    break
            
            if not interface:
                # 如果找不到匹配的接口,尝试使用默认接口
                interfaces = self.interface_manager.get_all_interfaces()
                if interfaces:
                    interface = interfaces[0]
                else:
                    QMessageBox.critical(self, "错误", "无法找到可用的网络接口")
                    return
            
            # 应用路由到系统
            self.statusbar.showMessage(f"正在添加路由 {target}...", 0)
            success, error = self.route_manager.add_route(route, interface.if_index)
            
            if success:
                logger.info(f"成功添加系统路由: {target} -> {gateway}")
                QMessageBox.information(self, "成功", f"已添加路由:\n{target} -> {gateway}")
                
                # 刷新显示
                self.route_manager.refresh_system_routes()
                self._update_system_routes_table()
                self._update_route_stats()
                
                self.statusbar.showMessage("路由添加成功", 3000)
            else:
                logger.error(f"添加系统路由失败: {target}, 错误: {error}")
                QMessageBox.critical(self, "错误", f"添加路由失败:\n{error}")
                self.statusbar.showMessage("路由添加失败", 3000)
    
    def _on_delete_system_route(self, destination_prefix: str):
        """删除系统路由"""
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除系统路由?\n\n"
            f"目标: {destination_prefix}\n\n"
            f"注意: 删除后可能影响网络连接!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 执行删除
        self.statusbar.showMessage(f"正在删除路由 {destination_prefix}...", 0)
        success, error = self.route_manager.delete_route(destination_prefix)
        
        if success:
            logger.info(f"成功删除系统路由: {destination_prefix}")
            QMessageBox.information(self, "成功", f"已删除路由: {destination_prefix}")
            
            # 刷新显示
            self.route_manager.refresh_system_routes()
            self._update_system_routes_table()
            self._update_routes_table()  # 同时更新配置路由的状态
            self._update_route_stats()
            
            self.statusbar.showMessage("路由删除成功", 3000)
        else:
            logger.error(f"删除系统路由失败: {destination_prefix}, 错误: {error}")
            QMessageBox.critical(self, "错误", f"删除路由失败:\n{error}")
            self.statusbar.showMessage("路由删除失败", 3000)
    
    def _on_profile_changed(self, profile_name: str):
        """Profile 切换事件"""
        if not profile_name:
            return
        
        # 提示保存当前配置
        reply = QMessageBox.question(
            self, "切换 Profile",
            "是否保存当前 Profile 的更改?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Cancel:
            # 取消切换,恢复原选项
            index = self.profile_combo.findText(self.config_manager.current_profile)
            if index >= 0:
                self.profile_combo.blockSignals(True)
                self.profile_combo.setCurrentIndex(index)
                self.profile_combo.blockSignals(False)
            return
        elif reply == QMessageBox.StandardButton.Yes:
            # 保存当前配置
            self.config_manager.set_routes(self.routes)
            self.config_manager.save_profile()
        
        # 加载新 Profile
        if self.config_manager.load_profile(profile_name):
            self.routes = self.config_manager.get_routes()
            self._update_group_tree()
            self._update_routes_table()
            self._update_statusbar()
            self.statusbar.showMessage(f"已切换到 Profile: {profile_name}", 3000)
        else:
            QMessageBox.critical(self, "错误", f"加载 Profile 失败: {profile_name}")
    
    def _on_group_selected(self, item: QTreeWidgetItem, column: int):
        """分组选择事件"""
        group_name = item.data(0, Qt.ItemDataRole.UserRole)
        search_text = self.search_input.text()
        self._update_routes_table(group_name, search_text)
    
    def _on_search_changed(self, text: str):
        """搜索文本变化事件"""
        # 获取当前选中的分组
        selected_items = self.group_tree.selectedItems()
        if selected_items:
            group_name = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        else:
            group_name = "All"
        
        self._update_routes_table(group_name, text)
    
    def _on_add_route(self):
        """新增路由"""
        # 打开路由对话框
        interfaces = self.interface_manager.get_all_interfaces()
        
        if not interfaces:
            QMessageBox.warning(self, "提示", "请先读取接口信息")
            return
        
        dialog = RouteDialog(self, interfaces=interfaces)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            route = dialog.get_route()
            if route:
                # 添加到路由列表
                self.routes.append(route)
                
                # 保存配置
                self.config_manager.set_routes(self.routes)
                self.config_manager.save_profile()
                
                # 刷新显示
                self._update_group_tree()
                self._update_routes_table()
                
                self.statusbar.showMessage(f"已添加路由: {route.target}", 3000)
    
    def _on_edit_route(self, route: Route):
        """编辑路由"""
        # 打开路由对话框
        interfaces = self.interface_manager.get_all_interfaces()
        
        if not interfaces:
            QMessageBox.warning(self, "提示", "请先读取接口信息")
            return
        
        dialog = RouteDialog(self, route=route, interfaces=interfaces)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            edited_route = dialog.get_route()
            if edited_route:
                # 更新路由信息
                index = self.routes.index(route)
                self.routes[index] = edited_route
                
                # 保存配置
                self.config_manager.set_routes(self.routes)
                self.config_manager.save_profile()
                
                # 刷新显示
                self._update_group_tree()
                self._update_routes_table()
                
                self.statusbar.showMessage(f"已更新路由: {edited_route.target}", 3000)
    
    def _on_delete_route(self, route: Route):
        """删除路由"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"是否删除路由: {route.target}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.routes.remove(route)
            self.config_manager.set_routes(self.routes)
            self.config_manager.save_profile()
            self._update_group_tree()
            self._update_routes_table()
            self.statusbar.showMessage(f"已删除路由: {route.target}", 3000)
    
    def _on_refresh_interfaces(self):
        """刷新接口"""
        if self.interface_manager.refresh_interfaces():
            self._update_statusbar()
            
            # 显示接口信息
            interfaces = self.interface_manager.get_all_interfaces()
            info_text = "网络接口列表:\n\n"
            for interface in interfaces:
                info_text += f"名称: {interface.name}\n"
                info_text += f"  ifIndex: {interface.if_index}\n"
                info_text += f"  MAC: {interface.mac_address}\n"
                info_text += f"  IP: {interface.ip_address}/{interface.prefix_length}\n"
                info_text += f"  网关: {interface.gateway}\n\n"
            
            QMessageBox.information(self, "接口列表", info_text)
        else:
            QMessageBox.critical(self, "错误", "刷新接口失败")
    
    def _on_apply(self):
        """应用路由"""
        # 刷新接口信息
        if not self.interface_manager.refresh_interfaces():
            QMessageBox.critical(self, "错误", "刷新接口信息失败")
            return
        
        # 创建快照
        self.statusbar.showMessage("正在创建快照...", 0)
        snapshot_path = self.snapshot_manager.create_system_snapshot(self.route_manager)
        if snapshot_path:
            logger.info(f"Apply前快照已创建: {snapshot_path}")
        
        # 生成 Diff
        self.statusbar.showMessage("正在生成 Diff...", 0)
        diff_items, error = self.apply_manager.generate_diff(self.routes)
        
        if error:
            self.statusbar.clearMessage()
            QMessageBox.critical(self, "错误", f"生成 Diff 失败: {error}")
            return
        
        self.statusbar.clearMessage()
        
        if not diff_items:
            QMessageBox.information(self, "提示", "没有需要应用的变更")
            return
        
        # 打开 Diff 预览对话框
        dialog = DiffDialog(self, self.apply_manager, diff_items)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 应用成功,更新路由状态
            for route in self.routes:
                route.last_apply_result = "成功"
                route.last_apply_time = datetime.now().strftime("%H:%M")
            
            # 保存配置
            self.config_manager.set_routes(self.routes)
            self.config_manager.save_profile()
            
            # 创建配置快照
            config_path = self.config_manager.get_profile_path(self.config_manager.current_profile)
            self.snapshot_manager.create_config_snapshot(config_path)
            
            # 刷新显示
            self._update_routes_table()
            self._update_statusbar()
            
            self.statusbar.showMessage("应用成功", 5000)
    
    def _on_verify(self):
        """验证路由"""
        # 获取所有启用的路由
        enabled_routes = [r for r in self.routes if r.enabled]
        
        if not enabled_routes:
            QMessageBox.information(self, "提示", "没有启用的路由需要验证")
            return
        
        # 获取目标列表
        targets = [r.get_destination_prefix() for r in enabled_routes]
        
        # 打开验证对话框
        dialog = VerifyDialog(self, self.verify_manager, targets)
        dialog.exec()
    
    def _on_rollback(self):
        """回滚"""
        # 打开快照管理对话框
        dialog = SnapshotDialog(self, self.snapshot_manager, self.route_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 刷新路由信息
            self._refresh_all()
    
    def _on_import(self):
        """导入"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "导入路由",
            "", "JSON Files (*.json);;CSV Files (*.csv)"
        )
        
        if not filepath:
            return
        
        try:
            if filepath.endswith('.json'):
                # JSON导入
                import json
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 可能是完整Profile或仅路由列表
                if isinstance(data, dict) and 'routes' in data:
                    routes_data = data['routes']
                elif isinstance(data, list):
                    routes_data = data
                else:
                    raise ValueError("JSON格式不正确")
                
                # 转换为Route对象
                imported_routes = [Route.from_dict(r) for r in routes_data]
                
            elif filepath.endswith('.csv'):
                # CSV导入
                import csv
                imported_routes = []
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        route = Route(
                            enabled=row.get('enabled', 'true').lower() == 'true',
                            target=row.get('target', ''),
                            prefix_length=int(row.get('prefix_length', '32')),
                            gateway=row.get('gateway', ''),
                            interface_name=row.get('interface_name', ''),
                            metric=int(row.get('metric', '5')),
                            persistent=row.get('persistent', 'true').lower() == 'true',
                            group=row.get('group', ''),
                            desc=row.get('desc', '')
                        )
                        imported_routes.append(route)
            else:
                QMessageBox.warning(self, "错误", "不支持的文件格式")
                return
            
            if imported_routes:
                # 询问导入策略
                reply = QMessageBox.question(
                    self, "导入策略",
                    f"找到 {len(imported_routes)} 条路由。\n\n"
                    "是: 追加到现有路由\n"
                    "否: 替换所有路由",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                )
                
                if reply == QMessageBox.StandardButton.Cancel:
                    return
                elif reply == QMessageBox.StandardButton.Yes:
                    # 追加
                    self.routes.extend(imported_routes)
                else:
                    # 替换
                    self.routes = imported_routes
                
                # 保存配置
                self.config_manager.set_routes(self.routes)
                self.config_manager.save_profile()
                
                # 刷新显示
                self._update_group_tree()
                self._update_routes_table()
                
                QMessageBox.information(self, "成功", f"已导入 {len(imported_routes)} 条路由")
            else:
                QMessageBox.warning(self, "警告", "未找到有效的路由数据")
        
        except Exception as e:
            logger.error(f"导入路由失败: {e}")
            QMessageBox.critical(self, "错误", f"导入失败:\n{e}")
    
    def _on_export(self):
        """导出"""
        if not self.routes:
            QMessageBox.information(self, "提示", "没有路由可导出")
            return
        
        # 选择格式
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self, "导出路由",
            f"{self.config_manager.current_profile}_routes.json",
            "JSON Files (*.json);;CSV Files (*.csv)"
        )
        
        if not filepath:
            return
        
        try:
            if 'JSON' in selected_filter or filepath.endswith('.json'):
                # JSON导出
                import json
                routes_data = [route.to_dict() for route in self.routes]
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(routes_data, f, ensure_ascii=False, indent=2)
            
            elif 'CSV' in selected_filter or filepath.endswith('.csv'):
                # CSV导出
                import csv
                
                with open(filepath, 'w', encoding='utf-8', newline='') as f:
                    fieldnames = [
                        'enabled', 'target', 'prefix_length', 'gateway', 
                        'interface_name', 'metric', 'persistent', 'group', 'desc'
                    ]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for route in self.routes:
                        writer.writerow({
                            'enabled': str(route.enabled).lower(),
                            'target': route.target,
                            'prefix_length': route.prefix_length,
                            'gateway': route.gateway,
                            'interface_name': route.interface_name,
                            'metric': route.metric,
                            'persistent': str(route.persistent).lower(),
                            'group': route.group,
                            'desc': route.desc
                        })
            else:
                QMessageBox.warning(self, "错误", "不支持的文件格式")
                return
            
            QMessageBox.information(self, "成功", f"已导出 {len(self.routes)} 条路由到:\n{filepath}")
        
        except Exception as e:
            logger.error(f"导出路由失败: {e}")
            QMessageBox.critical(self, "错误", f"导出失败:\n{e}")
    
    def _on_profile_manage(self):
        """Profile 管理"""
        dialog = ProfileDialog(self, self.config_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            profile_name, action = dialog.get_result()
            
            if profile_name:
                # 加载Profile
                if self.config_manager.load_profile(profile_name):
                    self.routes = self.config_manager.get_routes()
                    self._update_profile_combo()
                    self._update_group_tree()
                    self._update_routes_table()
                    self._update_statusbar()
                    
                    if action == "load_and_apply":
                        # 立即应用
                        self._on_apply()
                    else:
                        self.statusbar.showMessage(f"已加载 Profile: {profile_name}", 3000)
                else:
                    QMessageBox.critical(self, "错误", f"加载 Profile 失败: {profile_name}")
            
            # 刷新Profile列表
            self._update_profile_combo()
    
    def _on_settings(self):
        """设置"""
        QMessageBox.information(self, "提示", "设置功能开发中...")
    
    def _on_help(self):
        """帮助"""
        help_text = """
路由管理工具 - 帮助

快速操作:
- Ctrl+N: 新增路由
- F5: 刷新
- Ctrl+Q: 退出

使用流程:
1. 读取接口 - 获取当前网络接口信息
2. 新增/编辑路由 - 配置路由条目
3. 应用 - 将配置应用到系统
4. 验证 - 检查路由是否生效

注意事项:
- 需要管理员权限
- 操作前会自动创建快照
- 支持回滚到之前的状态
        """
        QMessageBox.information(self, "帮助", help_text.strip())
    
    def _on_about(self):
        """关于"""
        about_text = """
路由管理工具 v1.0

Windows 路由管理 GUI 工具

技术栈:
- Python + PyQt6
- PowerShell / route.exe

© 2025 NetTLS
        """
        QMessageBox.about(self, "关于", about_text.strip())

