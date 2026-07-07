# 📰 NYT-Archive-Flow

一个自动化、轻量级的《纽约时报》中文网内容归档系统。通过 Python 定时抓取头条新闻，自动生成精美的移动端适配网页，并利用 GitHub Pages 进行托管和展示。

---

## ✨ 功能特性

* **自动化抓取**：自动监测并获取《纽约时报》中文网最新头条，支持断点续传（去重处理）。
* **优雅阅读体验**：生成的文章页采用经典的 Georgia 衬线字体，支持移动端适配，带来类似阅读纸媒的沉浸式体验。
* **可视化日历视图**：自动生成聚合索引页，通过日历形式直观查看历史归档。
* **云端管理**：支持在移动端通过简单的手势（双击日历）开启管理模式，直接删除过期或无需保留的归档。
* **零成本部署**：依托 GitHub Actions + GitHub Pages，无需后端服务器，完全免费。

---

## 🛠 技术栈

* **后端**：Python (Requests, BeautifulSoup4)
* **前端**：原生 HTML/CSS/JavaScript (无框架，极致轻量)
* **存储**：GitHub Repository (HTML 文件 + JSON 索引)
* **部署**：GitHub Actions

---

## 🚀 快速开始

### 1. 准备工作
1. **Fork 本项目**到你的 GitHub 账户。
2. 在仓库 `Settings` -> `Secrets and variables` -> `Actions` 中添加以下 `Repository secrets`：
    * `GH_TOKEN_NYT`: 你的 GitHub Personal Access Token (需具备 `repo` 权限)。
    * `GH_OWNER_NYT`: 你的 GitHub 用户名。
    * `GH_REPO_NYT`: 当前仓库名称。

### 2. 配置定时任务
项目已包含 GitHub Actions 工作流（位于 `.github/workflows/`），默认配置为每天定时运行。你可以根据需求修改 `cron` 表达式：

```yaml
on:
  schedule:
    - cron: '0 9 * * *' # 每天早上 9 点运行
  workflow_dispatch:     # 支持手动触发
```

### 3. 使用说明
* **查看内容**：访问你的 `https://[username].github.io/[repo-name]/` 即可查看归档库。
* **删除条目**：在移动端或网页上，**快速双击日历空白区域**，即可在列表项后显示“🗑️”删除按钮，点击后将同步清除云端文件与本地索引。

---

## 📁 目录结构

```text
├── docs/                # 归档存储目录（含生成的 HTML 页面）
│   ├── YYYY/MM/         # 按年/月归档的文章
│   └── index.html       # 聚合日历与索引页
├── script.py            # 核心抓取与渲染逻辑
└── .github/workflows/   # 自动化流水线配置
```

---

## 📝 许可证

本项目仅供学习与个人阅读使用，新闻内容的版权归《纽约时报》所有。
