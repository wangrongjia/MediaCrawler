# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import asyncio
import os
import random
from asyncio import Task
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    async_playwright,
)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import douyin as douyin_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var
from tools.utils import clean_filename

from .client import DouYinClient
from .exception import DataFetchError
from .field import PublishTimeType
from .login import DouYinLogin


class DouYinCrawler(AbstractCrawler):
    """
    抖音爬虫核心类
    负责管理浏览器实例、处理登录、执行数据爬取等核心功能
    """
    context_page: Page  # 浏览器页面实例
    dy_client: DouYinClient  # 抖音客户端实例
    browser_context: BrowserContext  # 浏览器上下文
    cdp_manager: Optional[CDPBrowserManager]  # CDP浏览器管理器

    def __init__(self) -> None:
        """初始化抖音爬虫"""
        self.index_url = "https://www.douyin.com"  # 抖音首页URL
        self.cdp_manager = None  # CDP管理器初始化为空

    async def start(self) -> None:
        """
        启动抖音爬虫的主入口方法
        负责初始化浏览器、登录、选择爬取模式等
        """
        # 初始化代理设置
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            # 创建代理IP池
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = utils.format_proxy_info(ip_proxy_info)

        async with async_playwright() as playwright:
            # 根据配置选择启动模式
            if config.ENABLE_CDP_MODE:
                # 使用CDP模式启动浏览器（更稳定，反检测能力更强）
                utils.logger.info("[DouYinCrawler] 使用CDP模式启动浏览器")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright,
                    playwright_proxy_format,
                    None,
                    headless=config.CDP_HEADLESS,
                )
            else:
                # 使用标准模式启动浏览器
                utils.logger.info("[DouYinCrawler] 使用标准模式启动浏览器")
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium,
                    playwright_proxy_format,
                    user_agent=None,
                    headless=config.HEADLESS,
                )
            
            # 添加反检测脚本，防止被网站识别为爬虫
            await self.browser_context.add_init_script(path="libs/stealth.min.js")
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            # 创建抖音客户端
            self.dy_client = await self.create_douyin_client(httpx_proxy_format)
            
            # 检查登录状态，如果未登录则进行登录
            if not await self.dy_client.pong(browser_context=self.browser_context):
                login_obj = DouYinLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",  # 手机号登录时的手机号
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES,
                )
                await login_obj.begin()
                await self.dy_client.update_cookies(browser_context=self.browser_context)
            
            # 设置爬虫类型变量
            crawler_type_var.set(config.CRAWLER_TYPE)
            
            # 根据爬虫类型执行不同的爬取逻辑
            if config.CRAWLER_TYPE == "search":
                # 搜索模式：搜索关键词并获取相关视频的评论信息
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # 详情模式：获取指定视频的详细信息和评论
                await self.get_specified_awemes()
            elif config.CRAWLER_TYPE == "creator":
                # 创作者模式：获取指定创作者的信息和视频
                await self.get_creators_and_videos()

            utils.logger.info("[DouYinCrawler.start] Douyin Crawler finished ...")

    async def search(self) -> None:
        """
        搜索模式：根据关键词搜索抖音视频
        支持分页爬取，自动获取视频详情和评论
        """
        utils.logger.info("[DouYinCrawler.search] Begin search douyin keywords")
        dy_limit_count = 10  # 抖音每页固定返回10条数据
        if config.CRAWLER_MAX_NOTES_COUNT < dy_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = dy_limit_count
        
        start_page = config.START_PAGE  # 起始页码
        
        # 遍历每个关键词进行搜索
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[DouYinCrawler.search] Current keyword: {keyword}")
            aweme_list: List[str] = []  # 存储视频ID列表
            page = 0
            dy_search_id = ""  # 搜索会话ID
            
            # 分页爬取，直到达到最大数量限制
            while (page - start_page + 1) * dy_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[DouYinCrawler.search] Skip {page}")
                    page += 1
                    continue
                
                try:
                    utils.logger.info(f"[DouYinCrawler.search] search douyin keyword: {keyword}, page: {page}")
                    # 调用API搜索视频
                    posts_res = await self.dy_client.search_info_by_keyword(
                        keyword=keyword,
                        offset=page * dy_limit_count - dy_limit_count,
                        publish_time=PublishTimeType(config.PUBLISH_TIME_TYPE),
                        search_id=dy_search_id,
                    )
                    
                    # 检查返回数据是否为空
                    if posts_res.get("data") is None or posts_res.get("data") == []:
                        utils.logger.info(f"[DouYinCrawler.search] search douyin keyword: {keyword}, page: {page} is empty,{posts_res.get('data')}`")
                        break
                except DataFetchError:
                    utils.logger.error(f"[DouYinCrawler.search] search douyin keyword: {keyword} failed")
                    break

                page += 1
                if "data" not in posts_res:
                    utils.logger.error(f"[DouYinCrawler.search] search douyin keyword: {keyword} failed，账号也许被风控了。")
                    break
                
                # 获取搜索会话ID，用于下次请求
                dy_search_id = posts_res.get("extra", {}).get("logid", "")
                
                # 处理搜索结果中的每个视频
                for post_item in posts_res.get("data"):
                    try:
                        # 提取视频信息
                        aweme_info: Dict = (post_item.get("aweme_info") or post_item.get("aweme_mix_info", {}).get("mix_items")[0])
                    except TypeError:
                        continue
                    
                    aweme_list.append(aweme_info.get("aweme_id", ""))
                    # 保存视频信息到数据库
                    await douyin_store.update_douyin_aweme(aweme_item=aweme_info)
                    # 下载视频媒体文件
                    await self.get_aweme_media(aweme_item=aweme_info)
            
            utils.logger.info(f"[DouYinCrawler.search] keyword:{keyword}, aweme_list:{aweme_list}")
            # 批量获取视频评论
            await self.batch_get_note_comments(aweme_list)

    async def get_specified_awemes(self):
        """
        详情模式：获取指定视频的详细信息和评论
        支持批量处理多个视频ID
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)  # 并发控制
        # 创建异步任务列表
        task_list = [self.get_aweme_detail(aweme_id=aweme_id, semaphore=semaphore) for aweme_id in config.DY_SPECIFIED_ID_LIST]
        aweme_details = await asyncio.gather(*task_list)
        
        # 处理每个视频的详细信息
        for aweme_detail in aweme_details:
            if aweme_detail is not None:
                await douyin_store.update_douyin_aweme(aweme_item=aweme_detail)
                await self.get_aweme_media(aweme_item=aweme_detail)
        
        # 批量获取评论
        await self.batch_get_note_comments(config.DY_SPECIFIED_ID_LIST)

    async def get_aweme_detail(self, aweme_id: str, semaphore: asyncio.Semaphore) -> Any:
        """
        获取单个视频的详细信息
        
        Args:
            aweme_id: 视频ID
            semaphore: 并发控制信号量
            
        Returns:
            视频详细信息字典，失败时返回None
        """
        async with semaphore:
            try:
                return await self.dy_client.get_video_by_id(aweme_id)
            except DataFetchError as ex:
                utils.logger.error(f"[DouYinCrawler.get_aweme_detail] Get aweme detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(f"[DouYinCrawler.get_aweme_detail] have not fund note detail aweme_id:{aweme_id}, err: {ex}")
                return None

    async def batch_get_note_comments(self, aweme_list: List[str]) -> None:
        """
        批量获取视频评论
        
        Args:
            aweme_list: 视频ID列表
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[DouYinCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        task_list: List[Task] = []
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        
        # 为每个视频创建获取评论的异步任务
        for aweme_id in aweme_list:
            task = asyncio.create_task(self.get_comments(aweme_id, semaphore), name=aweme_id)
            task_list.append(task)
        
        if len(task_list) > 0:
            await asyncio.wait(task_list)

    async def get_comments(self, aweme_id: str, semaphore: asyncio.Semaphore) -> None:
        """
        获取单个视频的评论
        
        Args:
            aweme_id: 视频ID
            semaphore: 并发控制信号量
        """
        async with semaphore:
            try:
                # 调用客户端方法获取所有评论
                await self.dy_client.get_aweme_all_comments(
                    aweme_id=aweme_id,
                    crawl_interval=random.random(),  # 随机间隔，避免被检测
                    is_fetch_sub_comments=config.ENABLE_GET_SUB_COMMENTS,  # 是否获取二级评论
                    callback=douyin_store.batch_update_dy_aweme_comments,  # 评论保存回调
                    max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,  # 最大评论数量
                )
                utils.logger.info(f"[DouYinCrawler.get_comments] aweme_id: {aweme_id} comments have all been obtained and filtered ...")
            except DataFetchError as e:
                utils.logger.error(f"[DouYinCrawler.get_comments] aweme_id: {aweme_id} get comments failed, error: {e}")

    async def get_creators_and_videos(self) -> None:
        """
        创作者模式：获取指定创作者的信息和所有视频
        """
        utils.logger.info("[DouYinCrawler.get_creators_and_videos] Begin get douyin creators")
        
        for user_id in config.DY_CREATOR_ID_LIST:
            # 获取创作者基本信息
            creator_info: Dict = await self.dy_client.get_user_info(user_id)
            if creator_info:
                await douyin_store.save_creator(user_id, creator=creator_info)

            # 获取创作者的所有视频信息
            all_video_list = await self.dy_client.get_all_user_aweme_posts(sec_user_id=user_id, callback=self.fetch_creator_video_detail)

            # 提取视频ID列表，用于批量获取评论
            video_ids = [video_item.get("aweme_id") for video_item in all_video_list]
            await self.batch_get_note_comments(video_ids)

    async def fetch_creator_video_detail(self, video_list: List[Dict]):
        """
        并发获取指定视频列表的详细信息并保存数据
        
        Args:
            video_list: 视频信息列表
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        # 创建获取视频详情的异步任务列表
        task_list = [self.get_aweme_detail(post_item.get("aweme_id"), semaphore) for post_item in video_list]

        note_details = await asyncio.gather(*task_list)
        # 处理每个视频的详细信息
        for aweme_item in note_details:
            if aweme_item is not None:
                await douyin_store.update_douyin_aweme(aweme_item=aweme_item)
                await self.get_aweme_media(aweme_item=aweme_item)

    async def create_douyin_client(self, httpx_proxy: Optional[str]) -> DouYinClient:
        """
        创建抖音客户端实例
        
        Args:
            httpx_proxy: HTTP代理设置
            
        Returns:
            DouYinClient实例
        """
        # 获取浏览器cookies并转换为字符串和字典格式
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())  # type: ignore
        
        # 创建抖音客户端
        douyin_client = DouYinClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": await self.context_page.evaluate("() => navigator.userAgent"),
                "Cookie": cookie_str,
                "Host": "www.douyin.com",
                "Origin": "https://www.douyin.com/",
                "Referer": "https://www.douyin.com/",
                "Content-Type": "application/json;charset=UTF-8",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return douyin_client

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """
        启动浏览器并创建浏览器上下文
        
        Args:
            chromium: Chromium浏览器类型
            playwright_proxy: Playwright代理设置
            user_agent: 用户代理字符串
            headless: 是否无头模式
            
        Returns:
            浏览器上下文实例
        """
        if config.SAVE_LOGIN_STATE:
            # 保存登录状态模式：使用持久化用户数据目录
            user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)  # type: ignore
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={
                    "width": 1920,
                    "height": 1080
                },
                user_agent=user_agent,
            )  # type: ignore
            return browser_context
        else:
            # 普通模式：启动浏览器并创建新上下文
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
            browser_context = await browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=user_agent)
            return browser_context

    async def launch_browser_with_cdp(
        self,
        playwright: Playwright,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """
        使用CDP模式启动浏览器
        CDP模式提供更强的反检测能力和更稳定的连接
        
        Args:
            playwright: Playwright实例
            playwright_proxy: Playwright代理设置
            user_agent: 用户代理字符串
            headless: 是否无头模式
            
        Returns:
            浏览器上下文实例
        """
        try:
            self.cdp_manager = CDPBrowserManager()
            browser_context = await self.cdp_manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless,
            )

            # 添加反检测脚本
            await self.cdp_manager.add_stealth_script()

            # 显示浏览器信息
            browser_info = await self.cdp_manager.get_browser_info()
            utils.logger.info(f"[DouYinCrawler] CDP浏览器信息: {browser_info}")

            return browser_context

        except Exception as e:
            utils.logger.error(f"[DouYinCrawler] CDP模式启动失败，回退到标准模式: {e}")
            # 回退到标准模式
            chromium = playwright.chromium
            return await self.launch_browser(chromium, playwright_proxy, user_agent, headless)

    async def close(self) -> None:
        """
        关闭浏览器上下文
        根据启动模式选择不同的关闭方式
        """
        # 如果使用CDP模式，需要特殊处理
        if self.cdp_manager:
            await self.cdp_manager.cleanup()
            self.cdp_manager = None
        else:
            await self.browser_context.close()
        utils.logger.info("[DouYinCrawler.close] Browser context closed ...")

    async def get_aweme_media(self, aweme_item: Dict):
        """
        获取抖音媒体文件，自动判断媒体类型是短视频还是帖子图片并下载
        
        Args:
            aweme_item: 抖音作品详情字典
        """
        if not config.ENABLE_GET_MEIDAS:
            utils.logger.info(f"[DouYinCrawler.get_aweme_media] Crawling image mode is not enabled")
            return
        
        # 笔记图片URL列表，若为短视频类型则返回为空列表
        note_download_url: List[str] = douyin_store._extract_note_image_list(aweme_item)
        # 视频URL，永远存在，但为短视频类型时的文件其实是音频文件
        video_download_url: str = douyin_store._extract_video_download_url(aweme_item)
        
        # TODO: 抖音并没采用音视频分离的策略，故音频可从原视频中分离，暂不提取
        if note_download_url:
            # 如果有图片URL，说明是图文帖子，下载图片
            await self.get_aweme_images(aweme_item)
        else:
            # 如果没有图片URL，说明是短视频，下载视频
            await self.get_aweme_video(aweme_item)

    async def get_aweme_images(self, aweme_item: Dict):
        """
        获取抖音作品的图片文件
        
        Args:
            aweme_item: 抖音作品详情字典
        """
        if not config.ENABLE_GET_MEIDAS:
            return
        
        aweme_id = aweme_item.get("aweme_id")
        # 提取图片URL列表
        note_download_url: List[str] = douyin_store._extract_note_image_list(aweme_item)

        if not note_download_url:
            return
        
        picNum = 0
        # 遍历下载每张图片
        for url in note_download_url:
            if not url:
                continue
            content = await self.dy_client.get_aweme_media(url)
            if content is None:
                continue
            extension_file_name = f"{picNum}.jpeg"
            picNum += 1
            # 保存图片到存储
            await douyin_store.update_dy_aweme_image(aweme_id, content, extension_file_name)

    async def get_aweme_video(self, aweme_item: Dict):
        """
        获取抖音作品的视频文件
        
        Args:
            aweme_item: 抖音作品详情字典
        """
        if not config.ENABLE_GET_MEIDAS:
            return
        
        aweme_id = aweme_item.get("aweme_id")
        # 提取视频下载URL
        video_download_url: str = douyin_store._extract_video_download_url(aweme_item)
        utils.logger.info(f"[DouYinCrawler.get_aweme_video] video_download_url:{video_download_url}")
        if not video_download_url:
            return
        
        content = await self.dy_client.get_aweme_media(video_download_url)
        if content is None:
            return
        
        # 取标题并清理非法字符
        title = aweme_item.get("title") or aweme_item.get("desc") or ""
        safe_title = clean_filename(title.strip())[:50]  # 限制长度，防止过长
        extension_file_name = f"{aweme_id}_{safe_title}.mp4"
        
        # 保存视频到存储
        await douyin_store.update_dy_aweme_video(aweme_id, content, extension_file_name)
