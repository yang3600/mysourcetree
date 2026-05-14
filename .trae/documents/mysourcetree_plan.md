# MySourceTree - Linux Git客户端开发计划

## 1. 项目概述

开发一个基于GTK + Python的Linux原生Git客户端，提供类似SourceTree的可视化Git管理功能。

## 2. 技术栈选择

- **GUI框架**: GTK 4（使用PyGObject）
- **编程语言**: Python 3
- **Git操作**: pygit2（libgit2的Python绑定）
- **项目结构**: 模块化设计

## 3. 核心功能模块

### 3.1 项目初始化
- 项目目录结构创建
- 依赖管理（requirements.txt）
- 基础应用框架搭建

### 3.2 仓库管理
- 打开/克隆Git仓库
- 仓库信息展示
- 多仓库支持

### 3.3 文件状态管理
- 工作区文件状态显示
- 暂存/取消暂存文件
- 提交功能
- 差异查看

### 3.4 Git历史可视化
- 提交历史列表
- 分支图可视化
- 提交详情查看

### 3.5 分支管理
- 分支列表显示
- 创建/切换/删除分支
- 合并分支
- 远程分支管理

### 3.6 差异对比
- 文件修改差异显示
- 行级别差异高亮

## 4. 项目结构

```
mysorcetree/
├── src/
│   ├── __init__.py
│   ├── main.py                    # 应用入口
│   ├── app/
│   │   ├── __init__.py
│   │   ├── application.py         # 主应用类
│   │   └── window.py              # 主窗口
│   ├── git/
│   │   ├── __init__.py
│   │   ├── repository.py          # Git仓库操作
│   │   ├── commit.py              # 提交相关
│   │   ├── branch.py              # 分支相关
│   │   └── diff.py                # 差异对比
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── widgets/
│   │   │   ├── __init__.py
│   │   │   ├── file_list.py       # 文件列表组件
│   │   │   ├── commit_history.py  # 提交历史组件
│   │   │   ├── branch_list.py     # 分支列表组件
│   │   │   └── diff_viewer.py     # 差异查看组件
│   │   └── dialogs/
│   │       ├── __init__.py
│   │       ├── open_repo.py       # 打开仓库对话框
│   │       ├── commit_dialog.py   # 提交对话框
│   │       └── branch_dialog.py   # 分支操作对话框
│   └── utils/
│       ├── __init__.py
│       └── helpers.py             # 辅助函数
├── requirements.txt
└── README.md
```

## 5. 开发步骤

1. **第一阶段：基础框架搭建**
   - 初始化项目结构
   - 创建GTK 4应用框架
   - 主窗口布局

2. **第二阶段：Git仓库集成**
   - 实现Git仓库操作类
   - 打开/克隆仓库功能
   - 仓库信息展示

3. **第三阶段：文件状态管理**
   - 实现文件状态显示
   - 暂存/取消暂存功能
   - 提交功能

4. **第四阶段：历史可视化**
   - 实现提交历史列表
   - 分支图可视化
   - 提交详情查看

5. **第五阶段：分支管理**
   - 分支列表显示
   - 创建/切换/删除分支
   - 合并分支

6. **第六阶段：差异对比**
   - 文件差异显示
   - 差异高亮

## 6. 依赖项

- pygobject>=3.40.0
- pygit2>=1.10.0

## 7. 风险与注意事项

- 确保系统已安装GTK 4开发库
- pygit2需要libgit2的支持
- 处理大仓库时的性能优化
