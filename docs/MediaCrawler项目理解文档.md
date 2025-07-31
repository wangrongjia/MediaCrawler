# MediaCrawler 项目理解文档

## 📖 项目概述

MediaCrawler 是一个功能强大的**多平台自媒体数据采集工具**，支持小红书、抖音、快手、B站、微博、贴吧、知乎等主流平台的公开信息抓取。

### 🎯 项目特点
- **技术门槛低**：基于 Playwright 浏览器自动化，无需复杂的JS逆向
- **多平台支持**：支持7个主流社交媒体平台
- **功能全面**：支持关键词搜索、指定帖子爬取、创作者主页数据、评论爬取等
- **数据存储灵活**：支持SQLite、MySQL、CSV、JSON多种存储方式
- **反检测能力强**：支持IP代理池、CDP模式等反检测技术

## 🏗️ 项目架构

### 核心设计模式
项目采用**抽象类设计模式**，通过定义抽象基类来规范各平台爬虫的实现：

```
AbstractCrawler (抽象爬虫类)
├── XiaoHongShuCrawler (小红书爬虫)
├── DouYinCrawler (抖音爬虫)  
├── KuaishouCrawler (快手爬虫)
├── BilibiliCrawler (B站爬虫)
├── WeiboCrawler (微博爬虫)
├── TieBaCrawler (贴吧爬虫)
└── ZhihuCrawler (知乎爬虫)
```

### 📁 目录结构详解

```
MediaCrawler/
├── main.py                    # 🚀 程序入口文件
├── requirements.txt           # 📦 Python依赖包列表
├── pyproject.toml            # 🔧 项目配置文件(uv包管理器)
├── 
├── base/                     # 🏛️ 抽象基类定义
│   └── base_crawler.py       # 定义爬虫、登录、存储等抽象接口
├── 
├── config/                   # ⚙️ 配置文件目录
│   ├── base_config.py        # 基础配置(平台、关键词、爬取类型等)
│   ├── db_config.py          # 数据库连接配置
│   ├── xhs_config.py         # 小红书专用配置
│   ├── dy_config.py          # 抖音专用配置
│   └── ...                   # 其他平台配置文件
├── 
├── media_platform/           # 🎭 各平台爬虫实现
│   ├── xhs/                  # 小红书爬虫模块
│   │   ├── core.py           # 核心爬虫逻辑
│   │   ├── client.py         # API客户端
│   │   ├── login.py          # 登录处理
│   │   ├── field.py          # 数据字段定义
│   │   └── help.py           # 辅助函数
│   ├── douyin/               # 抖音爬虫模块
│   ├── bilibili/             # B站爬虫模块
│   └── ...                   # 其他平台模块
├── 
├── store/                    # 💾 数据存储模块
│   ├── xhs/                  # 小红书数据存储
│   │   ├── xhs_store_impl.py # 存储实现
│   │   ├── xhs_store_sql.py  # SQL语句定义
│   │   └── xhs_store_media.py# 媒体文件存储
│   └── ...                   # 其他平台存储模块
├── 
├── model/                    # 📊 数据模型定义
│   ├── m_xiaohongshu.py      # 小红书数据模型
│   ├── m_douyin.py           # 抖音数据模型
│   └── ...                   # 其他平台数据模型
├── 
├── tools/                    # 🔧 工具函数库
│   ├── utils.py              # 通用工具函数
│   ├── crawler_util.py       # 爬虫相关工具
│   ├── browser_launcher.py   # 浏览器启动工具
│   ├── cdp_browser.py        # CDP模式浏览器管理
│   ├── slider_util.py        # 滑块验证工具
│   ├── time_util.py          # 时间处理工具
│   ├── words.py              # 词云图生成工具
│   └── easing.py             # 滑动轨迹模拟
├── 
├── cache/                    # 🗄️ 缓存模块
│   ├── local_cache.py        # 本地缓存实现
│   ├── redis_cache.py        # Redis缓存实现
│   └── cache_factory.py      # 缓存工厂
├── 
├── proxy/                    # 🌐 代理IP模块
│   ├── proxy_ip_pool.py      # IP代理池管理
│   ├── base_proxy.py         # 代理基类
│   └── providers/            # 代理服务商实现
├── 
├── cmd_arg/                  # 📝 命令行参数处理
│   └── arg.py                # 参数解析逻辑
├── 
├── libs/                     # 📚 JavaScript库文件
│   ├── douyin.js             # 抖音签名算法
│   ├── zhihu.js              # 知乎签名算法
│   └── stealth.min.js        # 反检测脚本
├── 
├── schema/                   # 🗃️ 数据库表结构
│   ├── tables.sql            # MySQL表结构
│   └── sqlite_tables.sql     # SQLite表结构
├── 
└── docs/                     # 📖 项目文档
    ├── 常见问题.md
    ├── 代理使用.md
    └── ...
```

## 🔧 核心技术原理

### 1. 浏览器自动化技术
- **核心框架**：Playwright - 微软开发的现代浏览器自动化工具
- **优势**：相比Selenium更快、更稳定、反检测能力更强
- **工作原理**：启动真实浏览器，模拟用户操作获取数据

### 2. 登录态保持
- **Cookie管理**：自动保存和恢复登录状态
- **多种登录方式**：
  - 二维码登录（推荐）
  - 手机号登录
  - Cookie直接登录

### 3. 反检测技术
- **CDP模式**：连接用户本地浏览器，使用真实环境
- **IP代理池**：支持多个代理IP轮换使用
- **请求频率控制**：避免被平台检测为机器人
- **User-Agent伪装**：模拟真实用户浏览器

### 4. 数据获取方式
- **API调用**：通过分析网页请求，直接调用平台API
- **签名算法**：使用JavaScript执行平台的签名算法
- **无需逆向**：利用浏览器环境直接获取签名参数

## 🚀 使用方法

### 1. 环境准备
```bash
# 安装uv包管理器（推荐）
# 访问：https://docs.astral.sh/uv/getting-started/installation

# 安装Node.js（版本 >= 16.0.0）
# 访问：https://nodejs.org/

# 进入项目目录
cd MediaCrawler

# 安装Python依赖
uv sync

# 安装浏览器驱动
uv run playwright install
```

### 2. 基本使用
```bash
# 小红书关键词搜索
uv run main.py --platform xhs --lt qrcode --type search

# 抖音指定帖子爬取
uv run main.py --platform dy --lt qrcode --type detail

# B站创作者主页数据
uv run main.py --platform bili --lt qrcode --type creator

# 查看所有参数选项
uv run main.py --help
```

### 3. 配置说明

#### 主要配置文件：`config/base_config.py`
```python
# 基础配置
PLATFORM = "xhs"                    # 平台选择
KEYWORDS = "编程副业,编程兼职"        # 搜索关键词
LOGIN_TYPE = "qrcode"               # 登录方式
CRAWLER_TYPE = "search"             # 爬取类型

# 功能开关
ENABLE_GET_COMMENTS = True          # 是否爬取评论
ENABLE_GET_SUB_COMMENTS = False     # 是否爬取二级评论
ENABLE_GET_MEIDAS = False           # 是否下载媒体文件
ENABLE_GET_WORDCLOUD = False        # 是否生成词云图

# 数据存储
SAVE_DATA_OPTION = "json"           # 存储方式
CRAWLER_MAX_NOTES_COUNT = 200       # 最大爬取数量

# 反检测设置
HEADLESS = False                    # 是否无头模式
ENABLE_IP_PROXY = False             # 是否使用代理
ENABLE_CDP_MODE = False             # 是否使用CDP模式
```

## 📊 支持的功能矩阵

| 平台   | 关键词搜索 | 指定帖子 | 二级评论 | 创作者主页 | 登录态缓存 | IP代理 | 词云图 |
|--------|------------|----------|----------|------------|------------|--------|--------|
| 小红书 | ✅         | ✅       | ✅       | ✅         | ✅         | ✅     | ✅     |
| 抖音   | ✅         | ✅       | ✅       | ✅         | ✅         | ✅     | ✅     |
| 快手   | ✅         | ✅       | ✅       | ✅         | ✅         | ✅     | ✅     |
| B站    | ✅         | ✅       | ✅       | ✅         | ✅         | ✅     | ✅     |
| 微博   | ✅         | ✅       | ✅       | ✅         | ✅         | ✅     | ✅     |
| 贴吧   | ✅         | ✅       | ✅       | ✅         | ✅         | ✅     | ✅     |
| 知乎   | ✅         | ✅       | ✅       | ✅         | ✅         | ✅     | ✅     |

## 💾 数据存储方式

### 1. SQLite（推荐个人使用）
```bash
uv run main.py --platform xhs --save_data_option sqlite
```
- **优点**：无需配置数据库服务器，开箱即用
- **适用**：个人学习、小规模数据采集

### 2. MySQL（推荐生产环境）
```bash
# 首次使用需初始化数据库
python db.py

# 运行爬虫
uv run main.py --platform xhs --save_data_option db
```
- **优点**：性能好，支持大规模数据
- **适用**：生产环境、大规模数据采集

### 3. CSV文件
```bash
uv run main.py --platform xhs --save_data_option csv
```
- **优点**：简单直观，便于Excel打开
- **适用**：数据分析、报表制作

### 4. JSON文件
```bash
uv run main.py --platform xhs --save_data_option json
```
- **优点**：结构化存储，便于程序处理
- **适用**：数据交换、API开发

## 🔍 核心代码流程

### 1. 程序启动流程
```python
# main.py
async def main():
    # 1. 解析命令行参数
    await cmd_arg.parse_cmd()
    
    # 2. 初始化数据库
    if config.SAVE_DATA_OPTION in ["db", "sqlite"]:
        await db.init_db()
    
    # 3. 创建对应平台的爬虫实例
    crawler = CrawlerFactory.create_crawler(platform=config.PLATFORM)
    
    # 4. 启动爬虫
    await crawler.start()
```

### 2. 爬虫工厂模式
```python
class CrawlerFactory:
    CRAWLERS = {
        "xhs": XiaoHongShuCrawler,
        "dy": DouYinCrawler,
        "ks": KuaishouCrawler,
        "bili": BilibiliCrawler,
        "wb": WeiboCrawler,
        "tieba": TieBaCrawler,
        "zhihu": ZhihuCrawler,
    }
    
    @staticmethod
    def create_crawler(platform: str) -> AbstractCrawler:
        crawler_class = CrawlerFactory.CRAWLERS.get(platform)
        return crawler_class()
```

### 3. 抽象基类设计
```python
class AbstractCrawler(ABC):
    @abstractmethod
    async def start(self):
        """启动爬虫"""
        pass
    
    @abstractmethod
    async def search(self):
        """搜索功能"""
        pass
    
    @abstractmethod
    async def launch_browser(self, ...):
        """启动浏览器"""
        pass
```

## 🛠️ 扩展开发指南

### 添加新平台支持
1. **创建平台目录**：`media_platform/新平台名/`
2. **实现核心文件**：
   - `core.py` - 继承AbstractCrawler
   - `client.py` - API客户端
   - `login.py` - 登录逻辑
   - `field.py` - 数据字段
3. **添加配置文件**：`config/新平台_config.py`
4. **创建数据模型**：`model/m_新平台.py`
5. **实现存储逻辑**：`store/新平台/`
6. **注册到工厂**：在`CrawlerFactory.CRAWLERS`中添加

### 自定义数据处理
1. **修改存储逻辑**：继承`AbstractStore`类
2. **添加数据清洗**：在`tools/utils.py`中添加函数
3. **扩展数据模型**：修改对应的model文件

## ⚠️ 注意事项

### 法律合规
- **仅供学习使用**：请勿用于商业用途
- **遵守平台规则**：遵守各平台的robots.txt和使用条款
- **合理使用频率**：避免对平台造成负担
- **数据使用规范**：不得侵犯他人隐私和知识产权

### 技术注意点
- **登录状态维护**：定期检查登录状态，及时更新Cookie
- **反检测策略**：合理设置请求间隔，使用代理IP
- **异常处理**：网络异常、验证码等情况的处理
- **数据去重**：避免重复采集相同数据

### 常见问题
1. **登录失败**：尝试手动过验证码，或使用CDP模式
2. **数据获取失败**：检查网络连接和平台接口变化
3. **性能问题**：调整并发数量和请求间隔
4. **存储问题**：检查数据库连接和磁盘空间

## 🎯 学习建议

### 对于Python初学者
1. **先理解项目结构**：从main.py开始，理解程序流程
2. **学习配置使用**：修改config文件，尝试不同参数
3. **观察数据流向**：从爬取到存储的完整流程
4. **阅读单个平台**：选择一个平台深入理解实现

### 对于有经验的开发者
1. **研究架构设计**：抽象类的使用、工厂模式的应用
2. **学习反检测技术**：CDP模式、代理池的实现
3. **扩展功能开发**：添加新平台、优化存储方案
4. **性能优化**：异步编程、并发控制的实现

## 📚 相关资源

- **Playwright官方文档**：https://playwright.dev/
- **项目在线文档**：https://nanmicoder.github.io/MediaCrawler/
- **爬虫学习教程**：https://github.com/NanmiCoder/CrawlerTutorial

---

这个项目是一个很好的学习现代Python爬虫技术的案例，通过阅读和实践可以学到：
- 现代浏览器自动化技术
- 异步编程模式
- 面向对象设计模式
- 反爬虫技术
- 数据存储和处理

希望这个文档能帮助你快速理解和使用这个项目！