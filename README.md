# MySourceTree - Linux Git客户端

一个基于 GTK 4 + Python 开发的原生 Git 客户端，提供类似 SourceTree 的可视化 Git 管理体验。

## 功能特性

### 📁 仓库管理
- 支持打开本地 Git 仓库
- 创建新仓库（支持裸仓库）
- 多仓库标签页管理

### 📋 文件状态管理
- 实时显示工作区文件状态
- 暂存/取消暂存文件
- 提交变更到本地仓库

### 🔄 提交历史可视化
- 提交历史列表展示
- 分支图谱可视化
- 提交详情查看（作者、日期、父提交等）

### 🌿 分支管理
- 分支列表显示（本地/远程）
- 创建新分支
- 切换分支
- 合并分支

### 📤 远程操作
- Pull（拉取）
- Push（推送）
- Fetch（获取）

### 📊 差异对比
- 文件修改差异显示
- 行级别差异高亮（新增/删除）
- 语法高亮代码查看

### 🎯 其他功能
- Stash（贮藏）
- Tag（标签）管理
- 提交搜索过滤

## 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| GUI框架 | GTK | 4.0+ |
| 语言 | Python | 3.8+ |
| Git库 | pygit2 | 1.10+ |
| 绑定 | PyGObject | 3.40+ |

## 安装指南

### 前置依赖

**Ubuntu/Debian:**
```bash
sudo apt-get install libgtk-4-dev libgit2-dev python3-gi python3-gi-cairo
```

**Fedora:**
```bash
sudo dnf install gtk4-devel libgit2-devel python3-gobject
```

### 安装依赖包

```bash
pip install -r requirements.txt
```

## 运行方式

```bash
cd src
python main.py
```

## 项目结构

```
mysorcetree/
├── src/
│   ├── main.py                    # 应用入口
│   ├── app/
│   │   ├── application.py         # 主应用类
│   │   └── window.py              # 主窗口
│   ├── git/
│   │   └── repository.py          # Git仓库操作封装
│   ├── ui/
│   │   ├── widgets/
│   │   │   └── repo_tab.py        # 仓库标签页组件
│   │   └── dialogs/
│   │       ├── new_repo_dialog.py # 新建仓库对话框
│   │       └── open_repo_dialog.py# 打开仓库对话框
│   └── utils/
├── requirements.txt
└── README.md
```

## 使用说明

### 打开仓库
1. 点击顶部"打开"按钮
2. 选择本地 Git 仓库目录
3. 仓库会在新标签页中打开

### 查看提交历史
- 打开仓库后，主区域会显示提交历史列表
- 点击提交可查看详情和代码差异

### 执行 Git 操作
- **提交**: 点击工具栏"提交"按钮，输入提交消息
- **拉取/推送**: 点击对应按钮执行远程操作
- **分支操作**: 使用工具栏按钮创建/合并分支

### 搜索过滤
- 使用右侧搜索框按作者名过滤提交
- 点击侧边栏分支可过滤特定分支的提交

## 快捷键

| 操作 | 快捷键 |
|------|--------|
| 新建仓库 | Ctrl+N |
| 打开仓库 | Ctrl+O |
| 提交 | Ctrl+S |
| 退出 | Ctrl+Q |

## 开发指南

### 代码风格
- 遵循 PEP 8 编码规范
- 使用 Google 风格的 docstrings
- 类型提示（Type Hints）

### 调试运行
```bash
cd src
python -m pdb main.py
```

### 测试
```bash
# 运行单元测试（待实现）
python -m pytest tests/
```

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -m 'Add xxx'`)
4. 推送到分支 (`git push origin feature/xxx`)
5. 创建 Pull Request

## 许可证

MIT License

## 致谢

- [SourceTree](https://www.sourcetreeapp.com/) - UI设计参考
- [pygit2](https://www.pygit2.org/) - Git操作支持
- [GTK](https://www.gtk.org/) - UI框架