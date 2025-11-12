# 路由管理工具 (NetTLS Route Manager)

> Windows 路由管理 GUI 工具 - 轻松管理永久 IPv4 路由

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)

## 📖 简介

一款专为 Windows 设计的图形化路由管理工具，解决手工 `route add` 命令的繁琐和易错问题。

### 核心优势

- 🎯 **可视化管理**: 直观的图形界面，告别命令行
- 🔒 **安全可靠**: 自动快照、失败回滚、操作审计
- 🚀 **功能完整**: 支持 IP/CIDR/域名、批量操作、多配置
- 💡 **智能辅助**: 自动校验、ifIndex 动态解析、WireGuard 检测

### 主要功能

- ✅ 路由管理: 查看/新增/编辑/删除永久路由
- ✅ 多种格式: 支持 IPv4、CIDR、域名(自动解析)
- ✅ 一键应用: Diff 预览、幂等执行、失败回滚
- ✅ 路由验证: route print 命中检查 + TraceRoute
- ✅ 快照回滚: 每次应用前自动快照，可随时回滚
- ✅ Profile: 多配置管理，快速切换场景
- ✅ 导入导出: CSV/JSON 批量导入导出
- ✅ 智能检测: WireGuard 全隧道提醒
- ✅ 分组管理: 按用途分组，便于维护
- ✅ 审计日志: 完整记录所有操作

## 📸 界面预览

<details>
<summary>点击查看界面截图</summary>

> 注: 实际界面基于 PyQt6，美观实用

主窗口: 分组树 + 路由表格 + 工具栏  
新增路由: 完整的表单校验  
Diff 预览: 清晰显示变更计划  
验证结果: route print + TraceRoute  
快照管理: 一键回滚到任意时间点

</details>

## 🚀 快速开始

### 使用打包版本(推荐)

1. 下载 `RouteManager.exe`
2. **右键 → 以管理员身份运行**
3. 开始使用

### 从源码运行

```bash
# 克隆仓库
git clone https://github.com/yourusername/nettls.git
cd nettls

# 安装依赖
pip install -r requirements.txt

# 以管理员身份运行
python src/main.py
```

## 💻 技术栈

- **语言**: Python 3.10+
- **GUI框架**: PyQt6
- **系统调用**: PowerShell / route.exe / netsh
- **打包工具**: PyInstaller

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行

**注意**: 需要以管理员身份运行

```bash
python src/main.py
```

## 打包

Windows 下执行:

```bash
build.bat
```

或手动执行:

```bash
pyinstaller RouteManager.spec
```

打包后的可执行文件位于 `dist/RouteManager.exe`

## 项目结构

```
nettls/
├── src/                    # 源代码
│   ├── main.py            # 程序入口
│   ├── core/              # 核心功能模块
│   │   ├── route_manager.py     # 路由管理
│   │   ├── interface_manager.py # 接口管理
│   │   ├── config_manager.py    # 配置管理
│   │   ├── snapshot_manager.py  # 快照管理
│   │   └── validator.py         # 校验工具
│   ├── ui/                # UI 组件
│   │   ├── main_window.py       # 主窗口
│   │   ├── dialogs/             # 对话框
│   │   └── widgets/             # 自定义控件
│   └── utils/             # 工具函数
├── profiles/              # 配置文件
├── snapshots/             # 快照
├── logs/                  # 日志
├── docs/                  # 文档
└── requirements.txt       # 依赖
```

## 📚 文档

- [用户指南](docs/USER_GUIDE.md) - 详细使用说明
- [设计文档](docs/设计文档.md) - 技术设计文档
- [原型说明](docs/prototype/原型说明.md) - UI 原型说明

## 🔧 开发

### 项目结构说明

- `src/core/`: 核心业务逻辑(路由、接口、配置、验证等)
- `src/ui/`: 界面组件(主窗口、对话框)
- `src/utils/`: 工具函数(PowerShell 封装、日志、权限检查)
- `profiles/`: Profile 配置文件目录
- `snapshots/`: 快照文件目录
- `logs/`: 日志文件目录

### 代码规范

- 使用 Python 类型提示
- 遵循 PEP 8 代码风格
- 所有函数/类都有文档字符串
- 核心逻辑有日志记录

## 🤝 贡献

欢迎提交 Issue 和 Pull Request!

## ⚠️ 注意事项

1. **必须以管理员身份运行** - 路由操作需要管理员权限
2. **谨慎操作默认路由** - 修改 0.0.0.0/0 可能导致网络中断
3. **备份配置** - 定期导出 Profile 和创建快照
4. **测试环境先行** - 重要变更先在测试环境验证

## 📝 常见问题

**Q: 为什么需要管理员权限?**  
A: 修改系统路由表需要管理员权限，这是 Windows 系统要求。

**Q: ifIndex 变化怎么办?**  
A: 工具不会硬编码 ifIndex，而是保存接口名称，应用时动态解析。

**Q: 支持 IPv6 吗?**  
A: 当前版本仅支持 IPv4，IPv6 支持将在后续版本加入。

**Q: 可以在 Windows 10 上使用吗?**  
A: 可以，支持 Windows 10/11 x64。

更多问题请查看 [用户指南](docs/USER_GUIDE.md)

## 📄 License

本项目采用 [MIT License](LICENSE) 开源协议。

## 🙏 致谢

- 设计文档和原型参考了现代路由管理工具的最佳实践
- 感谢 PyQt6 提供的强大 GUI 框架
- 感谢所有贡献者和使用者的反馈

---

**版本**: v1.0  
**作者**: NetTLS  
**最后更新**: 2025-11-11

