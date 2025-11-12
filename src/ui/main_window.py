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
    QGroupBox, QGridLayout, QInputDialog, QFormLayout, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
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


class LoadWorker(QThread):
    """异步加载Worker"""
    progress = pyqtSignal(int, str)  # 进度和消息
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, interface_manager, route_manager):
        super().__init__()
        self.interface_manager = interface_manager
        self.route_manager = route_manager
    
    def run(self):
        """执行加载任务"""
        try:
            # 第1步: 刷新接口
            self.progress.emit(1, "正在读取网络接口...")
            self.interface_manager.refresh_interfaces()
            
            # 第2步: 刷新系统路由
            self.progress.emit(2, "正在读取系统路由...")
            self.route_manager.refresh_system_routes()
            
            # 第3步: 完成
            self.progress.emit(3, "正在更新界面...")
            
            self.finished.emit()
        except Exception as e:
            logger.error(f"异步加载失败: {e}")
            self.error.emit(str(e))


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
        
        # 缓存网关筛选数据
        self._gateway_filter_cache = None
        self._last_system_routes_count = 0
        
        # 设置窗口
        self.setWindowTitle("路由管理工具 - NetTLS Route Manager")
        self.setGeometry(100, 100, 1400, 800)
        
        # 设置窗口图标
        try:
            # 尝试使用系统网络图标
            style = self.style()
            if style:
                icon = style.standardIcon(style.StandardPixmap.SP_DriveNetIcon)
                if not icon.isNull():
                    self.setWindowIcon(icon)
        except Exception as e:
            logger.warning(f"设置窗口图标失败: {e}")
        
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
        
        toolbar.addSeparator()
        
        # 退出按钮
        exit_btn = QPushButton("退出")
        exit_btn.setStyleSheet("background-color: #EF4444; color: white; padding: 5px 10px;")
        exit_btn.clicked.connect(self._on_exit)
        toolbar.addWidget(exit_btn)
    
    def _create_central_widget(self):
        """创建中心窗口部件"""
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 统一路由视图
        unified_tab = self._create_unified_routes_tab()
        self.tab_widget.addTab(unified_tab, "路由管理")
        
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
    
    def _create_unified_routes_tab(self) -> QWidget:
        """创建统一路由标签页"""
        # 创建分割器(左侧统计和过滤,右侧路由表格)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧面板
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)
        
        # 右侧面板
        right_panel = self._create_routes_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        
        return splitter
    
    def _create_left_panel(self) -> QWidget:
        """创建左侧面板(统计和筛选)"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 路由统计信息面板
        stats_group = QGroupBox("路由统计")
        stats_layout = QGridLayout()
        
        # 统计标签
        self.stats_total_label = QLabel("配置路由: 0")
        self.stats_enabled_label = QLabel("已启用: 0")
        self.stats_system_label = QLabel("系统路由: 0")
        self.stats_managed_label = QLabel("工具管理: 0")
        
        stats_layout.addWidget(QLabel("📋"), 0, 0)
        stats_layout.addWidget(self.stats_total_label, 0, 1)
        stats_layout.addWidget(QLabel("✓"), 1, 0)
        stats_layout.addWidget(self.stats_enabled_label, 1, 1)
        stats_layout.addWidget(QLabel("💾"), 2, 0)
        stats_layout.addWidget(self.stats_system_label, 2, 1)
        stats_layout.addWidget(QLabel("🔧"), 3, 0)
        stats_layout.addWidget(self.stats_managed_label, 3, 1)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # 分组筛选
        group_group = QGroupBox("分组筛选")
        group_layout = QVBoxLayout()
        
        self.group_tree = QTreeWidget()
        self.group_tree.setHeaderHidden(True)
        self.group_tree.itemClicked.connect(self._on_group_filter_changed)
        group_layout.addWidget(self.group_tree)
        
        group_group.setLayout(group_layout)
        layout.addWidget(group_group)
        
        # 网关筛选
        gateway_group = QGroupBox("网关筛选")
        gateway_layout = QVBoxLayout()
        
        self.gateway_filter_combo = QComboBox()
        self.gateway_filter_combo.currentIndexChanged.connect(self._on_gateway_filter_changed)
        gateway_layout.addWidget(self.gateway_filter_combo)
        
        gateway_group.setLayout(gateway_layout)
        layout.addWidget(gateway_group)
        
        # WireGuard 警告标签
        self.wg_warning = QLabel()
        self.wg_warning.setStyleSheet("background-color: #FEF3C7; color: #92400E; padding: 8px; border-radius: 4px;")
        self.wg_warning.setWordWrap(True)
        self.wg_warning.setVisible(False)
        layout.addWidget(self.wg_warning)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def _create_routes_panel(self) -> QWidget:
        """创建路由面板"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        # 新增路由按钮
        add_route_btn = QPushButton("新增路由")
        add_route_btn.setStyleSheet("background-color: #10B981; color: white; padding: 5px 15px;")
        add_route_btn.clicked.connect(self._on_add_route)
        toolbar.addWidget(add_route_btn)
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._on_refresh_all_routes)
        toolbar.addWidget(refresh_btn)
        
        toolbar.addWidget(QLabel("  搜索: "))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("按目标、描述或分组过滤...")
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.setMaximumWidth(300)
        toolbar.addWidget(self.search_input)
        
        toolbar.addStretch()
        
        # 统计标签
        self.unified_routes_count_label = QLabel("显示: 0 条")
        toolbar.addWidget(self.unified_routes_count_label)
        
        layout.addLayout(toolbar)
        
        # 表格
        self.unified_routes_table = QTableWidget()
        self.unified_routes_table.setColumnCount(9)
        self.unified_routes_table.setHorizontalHeaderLabels([
            "目标", "网关", "接口索引", "Metric", "协议", "描述", "分组", "状态", "操作"
        ])
        
        # 设置列宽
        header = self.unified_routes_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # 目标
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # 网关
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # 接口索引
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Metric
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # 协议
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # 描述
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # 分组
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # 状态
        
        # 操作列使用固定宽度以确保按钮有足够空间
        self.unified_routes_table.setColumnWidth(8, 200)  # 操作
        
        # 设置表格属性
        self.unified_routes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.unified_routes_table.setAlternatingRowColors(True)
        self.unified_routes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.unified_routes_table)
        
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
        # 先显示状态栏消息,不使用模态对话框阻塞界面
        self.statusbar.showMessage("正在加载网络配置...", 0)
        
        # 创建进度对话框(非模态)
        self.load_progress = QProgressDialog("正在加载网络配置...", "取消", 0, 3, self)
        self.load_progress.setWindowTitle("加载中")
        self.load_progress.setWindowModality(Qt.WindowModality.NonModal)  # 改为非模态
        self.load_progress.setMinimumDuration(500)  # 延迟显示,如果加载很快就不显示进度条
        self.load_progress.setAutoClose(True)
        self.load_progress.setValue(0)
        
        # 创建并启动Worker
        self.load_worker = LoadWorker(self.interface_manager, self.route_manager)
        self.load_worker.progress.connect(self._on_load_progress)
        self.load_worker.finished.connect(self._on_load_finished)
        self.load_worker.error.connect(self._on_load_error)
        self.load_worker.start()
    
    def _on_load_progress(self, value: int, message: str):
        """加载进度更新"""
        if hasattr(self, 'load_progress') and self.load_progress:
            self.load_progress.setValue(value)
            self.load_progress.setLabelText(message)
        self.statusbar.showMessage(message, 0)
    
    def _on_load_finished(self):
        """加载完成"""
        try:
            # 更新UI
            self._update_group_tree()
            self._update_statusbar()
            self._update_route_stats()
            
            # 关闭进度对话框
            if hasattr(self, 'load_progress') and self.load_progress:
                self.load_progress.close()
                self.load_progress = None
            
            # 更新统一路由表格
            QTimer.singleShot(50, self._update_unified_routes_table)
            
            self.statusbar.showMessage("加载完成", 3000)
        except Exception as e:
            logger.error(f"加载完成后更新UI失败: {e}")
            self.statusbar.showMessage(f"加载完成,但更新界面时出错: {e}", 5000)
    
    def _on_load_error(self, error: str):
        """加载错误"""
        if hasattr(self, 'load_progress') and self.load_progress:
            self.load_progress.close()
            self.load_progress = None
        
        logger.error(f"加载网络配置失败: {error}")
        QMessageBox.critical(self, "加载失败", f"加载网络配置时发生错误:\n{error}\n\n工具将以有限功能继续运行。")
        self.statusbar.showMessage("加载失败 - 部分功能可能不可用", 5000)
    
    def _refresh_all(self):
        """刷新所有数据"""
        # 刷新接口列表
        self.interface_manager.refresh_interfaces()
        
        # 刷新系统路由
        self.route_manager.refresh_system_routes()
        
        # 更新 UI
        self._update_group_tree()
        self._update_statusbar()
        self._update_unified_routes_table()
        self._update_route_stats()
        
        self.statusbar.showMessage("刷新完成", 3000)
    
    def _on_refresh_all_routes(self):
        """刷新所有路由"""
        self._refresh_all()
    
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
    
    # 已废弃: _update_system_routes_table 方法被 _update_unified_routes_table 替代
    
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
        
        # 统计系统路由
        system_routes = self.route_manager.get_system_routes()
        system_route_count = len(system_routes)
        
        # 统计工具管理的路由(在系统中存在且有配置信息的)
        managed_routes = 0
        for sys_route in system_routes:
            dest = sys_route.get('DestinationPrefix', '')
            if self._find_config_route_by_destination(dest):
                managed_routes += 1
        
        # 更新标签
        self.stats_total_label.setText(f"配置路由: {total_routes}")
        self.stats_enabled_label.setText(f"已启用: {enabled_routes}")
        self.stats_system_label.setText(f"系统路由: {system_route_count}")
        self.stats_managed_label.setText(f"工具管理: {managed_routes}")
    
    def _find_config_route_by_destination(self, destination_prefix: str) -> Route:
        """
        根据目标前缀查找配置路由
        
        Args:
            destination_prefix: 目标前缀,如 "192.168.1.0/24"
            
        Returns:
            Route: 找到的配置路由,未找到返回 None
        """
        if not destination_prefix:
            return None
        
        target_ip = destination_prefix.split('/')[0] if '/' in destination_prefix else destination_prefix
        
        for route in self.routes:
            route_ip = route.target.split('/')[0] if '/' in route.target else route.target
            if route_ip == target_ip:
                return route
        
        return None
    
    def _update_gateway_filter_combo(self, system_routes: list):
        """
        更新网关筛选下拉列表(使用缓存优化性能)
        
        Args:
            system_routes: 系统路由列表
        """
        # 检查是否需要更新缓存
        current_count = len(system_routes)
        if self._gateway_filter_cache is not None and current_count == self._last_system_routes_count:
            # 数据未变化,不需要重建下拉列表
            return
        
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
        
        # 更新缓存
        self._gateway_filter_cache = gateway_counts.copy()
        self._last_system_routes_count = current_count
        
        # 取消阻塞信号
        self.gateway_filter_combo.blockSignals(False)
    
    def _update_unified_routes_table(self, group_filter: str = "All", gateway_filter: str = None, search_text: str = ""):
        """
        更新统一路由表格
        
        Args:
            group_filter: 分组筛选("All" 表示全部)
            gateway_filter: 网关筛选(None 或 "All (全部)" 表示全部)
            search_text: 搜索文本
        """
        system_routes = self.route_manager.get_system_routes()
        
        # 更新网关筛选下拉列表(会检查缓存,避免不必要的重建)
        self._update_gateway_filter_combo(system_routes)
        
        # 如果没有指定筛选条件,从下拉列表获取当前选择
        if gateway_filter is None:
            current_index = self.gateway_filter_combo.currentIndex()
            if current_index == 0:
                gateway_filter = "All (全部)"
            elif current_index > 0:
                gateway_filter = self.gateway_filter_combo.itemData(current_index)
            else:
                gateway_filter = "All (全部)"
        
        # 过滤路由
        filtered_routes = []
        for sys_route in system_routes:
            # 网关筛选
            if gateway_filter and gateway_filter != "All (全部)":
                if sys_route.get('NextHop', '') != gateway_filter:
                    continue
            
            # 查找对应的配置路由
            config_route = self._find_config_route_by_destination(sys_route.get('DestinationPrefix', ''))
            
            # 分组筛选
            if group_filter != "All":
                if group_filter == "":
                    # 筛选未分组的
                    if config_route and config_route.group:
                        continue
                else:
                    # 筛选特定分组
                    if not config_route or config_route.group != group_filter:
                        continue
            
            # 搜索筛选
            if search_text:
                search_lower = search_text.lower()
                dest = sys_route.get('DestinationPrefix', '').lower()
                desc = config_route.desc.lower() if config_route else ""
                group = config_route.group.lower() if config_route else ""
                
                if (search_lower not in dest and
                    search_lower not in desc and
                    search_lower not in group):
                    continue
            
            filtered_routes.append((sys_route, config_route))
        
        # 更新表格
        self.unified_routes_table.setRowCount(0)
        self.unified_routes_count_label.setText(f"显示: {len(filtered_routes)} 条 (总计: {len(system_routes)})")
        
        for row, (sys_route, config_route) in enumerate(filtered_routes):
            self.unified_routes_table.insertRow(row)
            
            # 目标
            dest = sys_route.get('DestinationPrefix', '')
            self.unified_routes_table.setItem(row, 0, QTableWidgetItem(dest))
            
            # 网关
            gateway = sys_route.get('NextHop', '')
            self.unified_routes_table.setItem(row, 1, QTableWidgetItem(gateway))
            
            # 接口索引
            if_index = str(sys_route.get('ifIndex', ''))
            self.unified_routes_table.setItem(row, 2, QTableWidgetItem(if_index))
            
            # Metric
            metric = str(sys_route.get('RouteMetric', ''))
            self.unified_routes_table.setItem(row, 3, QTableWidgetItem(metric))
            
            # 协议
            protocol = sys_route.get('Protocol', '')
            self.unified_routes_table.setItem(row, 4, QTableWidgetItem(protocol))
            
            # 描述(来自配置)
            desc = config_route.desc if config_route else "-"
            desc_item = QTableWidgetItem(desc)
            if config_route:
                desc_item.setForeground(Qt.GlobalColor.darkBlue)
            self.unified_routes_table.setItem(row, 5, desc_item)
            
            # 分组(来自配置)
            group = config_route.group if config_route else "-"
            group_item = QTableWidgetItem(group)
            if config_route:
                group_item.setForeground(Qt.GlobalColor.darkGreen)
            self.unified_routes_table.setItem(row, 6, group_item)
            
            # 状态
            if config_route:
                status = "🔧 工具管理"
                status_item = QTableWidgetItem(status)
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                if protocol == 'NetMgmt':
                    status = "📝 手动添加"
                    status_item = QTableWidgetItem(status)
                    status_item.setForeground(Qt.GlobalColor.darkOrange)
                else:
                    status = "🖥️ 系统路由"
                    status_item = QTableWidgetItem(status)
                    status_item.setForeground(Qt.GlobalColor.gray)
            self.unified_routes_table.setItem(row, 7, status_item)
            
            # 操作按钮
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(4)
            
            # 根据不同情况显示不同按钮
            # 判断是否可删除路由(排除系统核心路由)
            is_deletable = protocol not in ['Local', 'Redirect'] and gateway != '0.0.0.0'
            
            if config_route:
                # 工具管理的路由: 显示编辑路由和系统路由按钮
                edit_config_btn = QPushButton("✏️")
                edit_config_btn.setToolTip("编辑路由配置")
                edit_config_btn.setStyleSheet(
                    "QPushButton { background-color: #3B82F6; color: white; border: none; "
                    "border-radius: 4px; padding: 5px; font-size: 14px; min-width: 32px; }"
                    "QPushButton:hover { background-color: #2563EB; }"
                )
                edit_config_btn.clicked.connect(lambda checked, r=config_route: self._on_edit_route_config(r))
                actions_layout.addWidget(edit_config_btn)
                
                system_route_btn = QPushButton("⚙️")
                system_route_btn.setToolTip("管理系统路由")
                system_route_btn.setStyleSheet(
                    "QPushButton { background-color: #F59E0B; color: white; border: none; "
                    "border-radius: 4px; padding: 5px; font-size: 14px; min-width: 32px; }"
                    "QPushButton:hover { background-color: #D97706; }"
                )
                system_route_btn.clicked.connect(lambda checked, r=config_route, d=dest: self._on_manage_system_route(r, d))
                actions_layout.addWidget(system_route_btn)
                
            elif is_deletable:
                # 可操作的系统路由: 显示编辑和删除按钮
                edit_btn = QPushButton("✏️")
                edit_btn.setToolTip("编辑并添加到配置")
                edit_btn.setStyleSheet(
                    "QPushButton { background-color: #3B82F6; color: white; border: none; "
                    "border-radius: 4px; padding: 5px; font-size: 14px; min-width: 32px; }"
                    "QPushButton:hover { background-color: #2563EB; }"
                )
                edit_btn.clicked.connect(lambda checked, d=dest, sr=sys_route: self._on_edit_netmgmt_route(d, sr))
                actions_layout.addWidget(edit_btn)
                
                delete_btn = QPushButton("🗑️")
                delete_btn.setToolTip("删除路由")
                delete_btn.setStyleSheet(
                    "QPushButton { background-color: #EF4444; color: white; border: none; "
                    "border-radius: 4px; padding: 5px; font-size: 14px; min-width: 32px; }"
                    "QPushButton:hover { background-color: #DC2626; }"
                )
                delete_btn.clicked.connect(lambda checked, d=dest: self._on_delete_system_route(d))
                actions_layout.addWidget(delete_btn)
                
            else:
                # 系统核心路由: 不可操作
                readonly_label = QLabel("🔒")
                readonly_label.setStyleSheet("color: #9CA3AF; font-size: 16px;")
                readonly_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                readonly_label.setToolTip("系统核心路由，不可操作")
                actions_layout.addWidget(readonly_label)
            
            self.unified_routes_table.setCellWidget(row, 8, actions_widget)
    
    def _select_default_gateway(self, gateways: list):
        """选择默认网关(192开头的第一个)"""
        for i, gateway in enumerate(gateways):
            if gateway.startswith('192'):
                self.gateway_filter_combo.setCurrentIndex(i + 1)  # +1 因为第0项是All
                return
        # 如果没有192开头的,选择All
        self.gateway_filter_combo.setCurrentIndex(0)
    
    # === 事件处理 ===
    
    def _on_group_filter_changed(self, item: QTreeWidgetItem, column: int):
        """分组筛选变化事件"""
        group_name = item.data(0, Qt.ItemDataRole.UserRole)
        search_text = self.search_input.text()
        self._update_unified_routes_table(group_name, None, search_text)
    
    def _on_refresh_system_routes(self):
        """刷新系统路由"""
        self.statusbar.showMessage("正在刷新系统路由...", 0)
        if self.route_manager.refresh_system_routes():
            # 清空缓存,强制重新加载
            self._gateway_filter_cache = None
            self._last_system_routes_count = 0
            
            self._update_unified_routes_table()
            self._update_route_stats()  # 同时更新统计信息
            self.statusbar.showMessage("系统路由刷新完成", 3000)
        else:
            self.statusbar.showMessage("系统路由刷新失败", 3000)
            QMessageBox.warning(self, "警告", "刷新系统路由失败")
    
    def _on_gateway_filter_changed(self, index: int):
        """网关筛选变化事件"""
        # 获取当前选中的分组
        selected_items = self.group_tree.selectedItems()
        if selected_items:
            group_name = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        else:
            group_name = "All"
        
        search_text = self.search_input.text()
        self._update_unified_routes_table(group_name, None, search_text)
    
    def _on_search_changed(self, text: str):
        """搜索文本变化事件"""
        # 获取当前选中的分组
        selected_items = self.group_tree.selectedItems()
        if selected_items:
            group_name = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        else:
            group_name = "All"
        
        self._update_unified_routes_table(group_name, None, text)
    
    def _on_edit_netmgmt_route(self, destination: str, sys_route: dict):
        """编辑NetMgmt类型的系统路由(转为配置路由)"""
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑路由 - 添加到配置")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # 说明
        info_label = QLabel(
            "此路由是手动添加的系统路由，尚未加入本工具管理。\n"
            "编辑后将添加到配置文件中，由本工具管理。"
        )
        info_label.setStyleSheet("background-color: #FEF3C7; color: #92400E; padding: 10px; border-radius: 4px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        form_layout = QFormLayout()
        
        # 显示路由信息(只读)
        route_info = QLabel(
            f"目标: {destination}\n"
            f"网关: {sys_route.get('NextHop', '')}\n"
            f"接口索引: {sys_route.get('ifIndex', '')}\n"
            f"Metric: {sys_route.get('RouteMetric', '')}"
        )
        route_info.setStyleSheet("background-color: #F3F4F6; color: #1F2937; padding: 10px; border-radius: 4px;")
        form_layout.addRow("路由信息:", route_info)
        
        # 描述输入
        desc_input = QTextEdit()
        desc_input.setPlaceholderText("请输入路由描述...")
        desc_input.setMaximumHeight(80)
        form_layout.addRow("描述*:", desc_input)
        
        # 分组输入
        group_input = QComboBox()
        group_input.setEditable(True)
        group_input.addItems(["", "aliyun", "office", "devops", "lab", "debug"])
        form_layout.addRow("分组:", group_input)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("添加到配置")
        ok_btn.setStyleSheet("background-color: #10B981; color: white; padding: 5px 15px;")
        cancel_btn = QPushButton("取消")
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        # 连接信号
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        # 显示对话框
        if dialog.exec() == QDialog.DialogCode.Accepted:
            desc = desc_input.toPlainText().strip()
            if not desc:
                QMessageBox.warning(dialog, "错误", "描述不能为空")
                return
            
            # 解析目标和前缀
            if '/' in destination:
                target, prefix_str = destination.split('/')
                prefix_length = int(prefix_str)
            else:
                target = destination
                prefix_length = 32
            
            # 获取接口名称
            if_index = sys_route.get('ifIndex', 0)
            interface = None
            for iface in self.interface_manager.get_all_interfaces():
                if iface.if_index == if_index:
                    interface = iface
                    break
            
            # 创建配置路由
            new_route = Route(
                enabled=True,
                target=target,
                prefix_length=prefix_length,
                gateway=sys_route.get('NextHop', ''),
                interface_name=interface.name if interface else "",
                metric=sys_route.get('RouteMetric', 256),
                persistent=True,
                group=group_input.currentText().strip(),
                desc=desc
            )
            
            # 添加到配置
            self.routes.append(new_route)
            self.config_manager.set_routes(self.routes)
            self.config_manager.save_profile()
            
            logger.info(f"已将系统路由添加到配置: {destination}")
            QMessageBox.information(dialog, "成功", f"路由已添加到配置:\n{destination}")
            
            # 刷新显示
            self._update_group_tree()
            self._update_unified_routes_table()
            self._update_route_stats()
            
            self.statusbar.showMessage("路由已添加到配置", 3000)
    
    def _on_edit_route_config(self, config_route: Route):
        """编辑路由配置(仅修改描述和分组,不修改系统路由)"""
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑路由配置")
        dialog.setMinimumWidth(500)
        
        layout = QFormLayout()
        
        # 显示路由基本信息(只读)
        info_label = QLabel(
            f"目标: {config_route.get_destination_prefix()}\n"
            f"网关: {config_route.gateway}\n"
            f"接口: {config_route.interface_name}"
        )
        info_label.setStyleSheet("background-color: #F3F4F6; color: #1F2937; padding: 10px; border-radius: 4px;")
        layout.addRow("路由信息:", info_label)
        
        # 描述输入
        desc_input = QTextEdit()
        desc_input.setPlainText(config_route.desc)
        desc_input.setMaximumHeight(80)
        layout.addRow("描述*:", desc_input)
        
        # 分组输入
        group_input = QComboBox()
        group_input.setEditable(True)
        group_input.addItems(["", "aliyun", "office", "devops", "lab", "debug"])
        group_input.setCurrentText(config_route.group)
        layout.addRow("分组:", group_input)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("保存")
        ok_btn.setStyleSheet("background-color: #10B981; color: white; padding: 5px 15px;")
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
            # 更新配置
            new_desc = desc_input.toPlainText().strip()
            new_group = group_input.currentText().strip()
            
            if not new_desc:
                QMessageBox.warning(self, "错误", "描述不能为空")
                return
            
            # 更新路由配置
            config_route.desc = new_desc
            config_route.group = new_group
            
            # 保存配置
            self.config_manager.set_routes(self.routes)
            self.config_manager.save_profile()
            
            logger.info(f"成功更新路由配置: {config_route.target}")
            QMessageBox.information(self, "成功", "路由配置已更新")
            
            # 刷新显示
            self._update_group_tree()
            self._update_unified_routes_table()
            self._update_route_stats()
            
            self.statusbar.showMessage("路由配置更新成功", 3000)
    
    def _on_manage_system_route(self, config_route: Route, destination: str):
        """管理系统路由(删除或重新应用)"""
        # 创建对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("管理系统路由")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # 显示路由信息
        info_label = QLabel(
            f"目标: {destination}\n"
            f"网关: {config_route.gateway}\n"
            f"接口: {config_route.interface_name}\n"
            f"Metric: {config_route.metric}\n"
            f"描述: {config_route.desc}\n"
            f"分组: {config_route.group}"
        )
        info_label.setStyleSheet("background-color: #F3F4F6; color: #1F2937; padding: 10px; border-radius: 4px;")
        layout.addWidget(info_label)
        
        # 说明
        note_label = QLabel(
            "系统路由操作:\n"
            "• 删除: 删除本地配置和系统路由\n"
            "• 重新应用: 删除旧路由并重新添加"
        )
        note_label.setStyleSheet("padding: 10px;")
        layout.addWidget(note_label)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        delete_btn = QPushButton("删除路由")
        delete_btn.setStyleSheet("background-color: #EF4444; color: white; padding: 8px 15px;")
        button_layout.addWidget(delete_btn)
        
        reapply_btn = QPushButton("重新应用")
        reapply_btn.setStyleSheet("background-color: #F59E0B; color: white; padding: 8px 15px;")
        button_layout.addWidget(reapply_btn)
        
        cancel_btn = QPushButton("取消")
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        # 连接信号
        delete_btn.clicked.connect(lambda: self._confirm_delete_route(dialog, config_route, destination))
        reapply_btn.clicked.connect(lambda: self._confirm_reapply_route(dialog, config_route, destination))
        cancel_btn.clicked.connect(dialog.reject)
        
        dialog.exec()
    
    def _confirm_delete_route(self, parent_dialog: QDialog, config_route: Route, destination: str):
        """确认删除路由(配置+系统)"""
        reply = QMessageBox.question(
            parent_dialog, "确认删除",
            f"确定要删除路由?\n\n"
            f"目标: {destination}\n"
            f"描述: {config_route.desc}\n"
            f"分组: {config_route.group}\n\n"
            f"将同时删除配置和系统路由!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 删除系统路由
        self.statusbar.showMessage(f"正在删除系统路由 {destination}...", 0)
        success, error = self.route_manager.delete_route(destination)
        
        if not success:
            QMessageBox.warning(parent_dialog, "警告", f"删除系统路由失败:\n{error}\n\n将继续删除配置路由。")
        
        # 删除配置路由
        try:
            self.routes.remove(config_route)
            self.config_manager.set_routes(self.routes)
            self.config_manager.save_profile()
            
            logger.info(f"成功删除路由: {destination}")
            QMessageBox.information(parent_dialog, "成功", f"已删除路由: {destination}")
            
            # 刷新显示
            self.route_manager.refresh_system_routes()
            self._update_group_tree()
            self._update_unified_routes_table()
            self._update_route_stats()
            
            self.statusbar.showMessage("路由删除成功", 3000)
            parent_dialog.accept()
        except Exception as e:
            logger.error(f"删除配置路由失败: {e}")
            QMessageBox.critical(parent_dialog, "错误", f"删除配置路由失败:\n{e}")
            self.statusbar.showMessage("路由删除失败", 3000)
    
    def _confirm_reapply_route(self, parent_dialog: QDialog, config_route: Route, destination: str):
        """确认重新应用路由"""
        reply = QMessageBox.question(
            parent_dialog, "确认重新应用",
            f"确定要重新应用路由?\n\n"
            f"目标: {destination}\n"
            f"描述: {config_route.desc}\n\n"
            f"将删除旧路由并重新添加!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 获取接口
        interface = self.interface_manager.get_interface_by_name(config_route.interface_name)
        if not interface:
            QMessageBox.critical(parent_dialog, "错误", f"找不到接口: {config_route.interface_name}")
            return
        
        # 删除旧路由
        self.statusbar.showMessage(f"正在删除旧路由 {destination}...", 0)
        self.route_manager.delete_route(destination)
        
        # 添加新路由
        self.statusbar.showMessage(f"正在重新应用路由 {destination}...", 0)
        success, error = self.route_manager.add_route(config_route, interface.if_index)
        
        if success:
            logger.info(f"成功重新应用路由: {destination}")
            QMessageBox.information(parent_dialog, "成功", f"已重新应用路由: {destination}")
            
            # 刷新显示
            self.route_manager.refresh_system_routes()
            self._update_unified_routes_table()
            
            self.statusbar.showMessage("路由重新应用成功", 3000)
            parent_dialog.accept()
        else:
            logger.error(f"重新应用路由失败: {destination}, {error}")
            QMessageBox.critical(parent_dialog, "错误", f"重新应用路由失败:\n{error}")
            self.statusbar.showMessage("路由重新应用失败", 3000)
    
    def _on_delete_managed_route(self, destination: str, config_route: Route):
        """删除工具管理的路由(同时删除配置和系统路由) - 已废弃,由 _on_manage_system_route 替代"""
        # 保留此方法以防有其他地方调用
        self._on_manage_system_route(config_route, destination)
    
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
                self._update_unified_routes_table()
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
            self._update_unified_routes_table()
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
            self._update_unified_routes_table()
            self._update_statusbar()
            self.statusbar.showMessage(f"已切换到 Profile: {profile_name}", 3000)
        else:
            QMessageBox.critical(self, "错误", f"加载 Profile 失败: {profile_name}")
    
    
    def _on_add_route(self):
        """新增路由"""
        # 打开路由对话框
        interfaces = self.interface_manager.get_all_interfaces()
        
        if not interfaces:
            QMessageBox.warning(self, "提示", "请先读取接口信息")
            return
        
        # 获取当前选中的网关
        default_gateway = None
        current_index = self.gateway_filter_combo.currentIndex()
        if current_index > 0:  # 0是"All (全部)"
            default_gateway = self.gateway_filter_combo.itemData(current_index)
        
        dialog = RouteDialog(self, interfaces=interfaces, default_gateway=default_gateway)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            route = dialog.get_route()
            if route:
                # 添加到路由列表
                self.routes.append(route)
                
                # 保存配置
                self.config_manager.set_routes(self.routes)
                self.config_manager.save_profile()
                
                # 检查是否需要立即应用
                if dialog.should_apply_immediately():
                    # 解析接口索引
                    interface = self.interface_manager.get_interface_by_name(route.interface_name)
                    if interface:
                        self.statusbar.showMessage(f"正在应用路由 {route.target}...", 0)
                        success, error = self.route_manager.add_route(route, interface.if_index)
                        
                        if success:
                            logger.info(f"成功应用路由: {route.target}")
                            self.statusbar.showMessage(f"路由已添加并应用: {route.target}", 3000)
                            
                            # 刷新系统路由
                            self.route_manager.refresh_system_routes()
                            self._update_unified_routes_table()
                        else:
                            logger.error(f"应用路由失败: {route.target}, {error}")
                            QMessageBox.warning(self, "应用失败", f"路由已保存到配置，但应用到系统失败:\n{error}")
                            self.statusbar.showMessage(f"路由已保存但应用失败: {route.target}", 3000)
                    else:
                        QMessageBox.warning(self, "错误", f"找不到接口: {route.interface_name}")
                        self.statusbar.showMessage(f"已添加路由(未应用): {route.target}", 3000)
                else:
                    self.statusbar.showMessage(f"已添加路由: {route.target}", 3000)
                
                # 刷新显示
                self._update_group_tree()
                self._update_unified_routes_table()
                self._update_route_stats()
    
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
                
                # 检查是否需要立即应用
                if dialog.should_apply_immediately():
                    interface = self.interface_manager.get_interface_by_name(edited_route.interface_name)
                    if interface:
                        self.statusbar.showMessage(f"正在应用路由 {edited_route.target}...", 0)
                        
                        # 先删除旧路由(如果存在)
                        self.route_manager.delete_route(route.target)
                        
                        # 添加新路由
                        success, error = self.route_manager.add_route(edited_route, interface.if_index)
                        
                        if success:
                            logger.info(f"成功应用更新的路由: {edited_route.target}")
                            self.statusbar.showMessage(f"路由已更新并应用: {edited_route.target}", 3000)
                            
                            # 刷新系统路由
                            self.route_manager.refresh_system_routes()
                            self._update_unified_routes_table()
                        else:
                            logger.error(f"应用路由失败: {edited_route.target}, {error}")
                            QMessageBox.warning(self, "应用失败", f"路由已保存到配置，但应用到系统失败:\n{error}")
                            self.statusbar.showMessage(f"路由已更新但应用失败: {edited_route.target}", 3000)
                    else:
                        QMessageBox.warning(self, "错误", f"找不到接口: {edited_route.interface_name}")
                        self.statusbar.showMessage(f"已更新路由(未应用): {edited_route.target}", 3000)
                else:
                    self.statusbar.showMessage(f"已更新路由: {edited_route.target}", 3000)
                
                # 刷新显示
                self._update_group_tree()
                self._update_unified_routes_table()
                self._update_route_stats()
    
    def _on_delete_route(self, route: Route):
        """删除配置路由（仅删除配置，不删除系统路由）"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"是否删除路由配置?\n\n"
            f"目标: {route.target}\n"
            f"描述: {route.desc}\n\n"
            f"注意：仅删除配置，不会删除系统中的路由。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.routes.remove(route)
                self.config_manager.set_routes(self.routes)
                self.config_manager.save_profile()
                
                logger.info(f"已删除路由配置: {route.target}")
                
                # 刷新显示
                self._update_group_tree()
                self._update_unified_routes_table()
                self._update_route_stats()
                
                self.statusbar.showMessage(f"已删除路由配置: {route.target}", 3000)
            except Exception as e:
                logger.error(f"删除路由配置失败: {e}")
                QMessageBox.critical(self, "错误", f"删除路由配置失败:\n{e}")
    
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
            self._update_unified_routes_table()
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
                self._update_unified_routes_table()
                
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
                    self._update_unified_routes_table()
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
    
    def _on_exit(self):
        """退出应用程序"""
        # 询问是否保存当前配置
        reply = QMessageBox.question(
            self, "退出确认",
            "是否保存当前配置后退出?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Cancel:
            return
        elif reply == QMessageBox.StandardButton.Yes:
            # 保存当前配置
            try:
                self.config_manager.set_routes(self.routes)
                self.config_manager.save_profile()
                logger.info(f"退出前已保存配置: {self.config_manager.current_profile}")
            except Exception as e:
                logger.error(f"保存配置失败: {e}")
                QMessageBox.warning(self, "警告", f"保存配置失败:\n{e}\n\n将直接退出。")
        
        # 关闭应用程序
        logger.info("应用程序正常退出")
        self.close()

