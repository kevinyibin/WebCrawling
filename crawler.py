#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
爬虫模块
负责抓取无人机公司网站的内容
"""

import logging
import time
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class Crawler:
    """
    爬虫类，负责抓取无人机公司网站的内容
    """
    
    def __init__(self, config):
        """
        初始化爬虫
        
        Args:
            config: 配置信息
        """
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        self.timeout = config.get('timeout', 30)
        self.max_pages = config.get('max_pages', 300)
        self.delay = config.get('delay', 0.5)  # 爬取间隔，避免被封
    
    def crawl(self, company):
        """
        爬取公司网站
        
        Args:
            company: 公司信息，包含名称和网址
            
        Returns:
            list: 爬取的页面数据列表
        """
        company_name = company['name']
        start_url = company['url']
        logger.info(f"开始爬取公司: {company_name}, URL: {start_url}")
        
        # 初始化已访问的URL集合和待访问的URL队列
        visited_urls = set()
        to_visit = [start_url]
        results = []
        
        # 提取网站域名，用于限制爬取范围
        domain = urlparse(start_url).netloc
        
        # 开始爬取
        page_count = 0
        while to_visit and page_count < self.max_pages:
            # 取出一个URL进行访问
            current_url = to_visit.pop(0)
            
            # 如果已经访问过，则跳过
            if current_url in visited_urls:
                continue
            
            # 标记为已访问
            visited_urls.add(current_url)
            
            try:
                # 发送请求获取页面内容
                response = requests.get(current_url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()  # 检查请求是否成功
                
                # 解析页面内容
                html_content = response.text
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 提取页面文本内容
                text_content = soup.get_text(separator=' ', strip=True)
                
                # 保存页面数据
                page_data = {
                    'url': current_url,
                    'company': company_name,
                    'html': html_content,
                    'content': text_content
                }
                results.append(page_data)
                
                # 增加页面计数
                page_count += 1
                logger.info(f"已爬取 {page_count} 个页面，当前: {current_url}")
                
                # 提取页面中的链接
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    
                    # 将相对URL转换为绝对URL
                    absolute_url = urljoin(current_url, href)
                    
                    # 检查URL是否属于同一域名，避免爬取外部链接
                    if urlparse(absolute_url).netloc == domain:
                        # 只考虑HTTP和HTTPS链接
                        if absolute_url.startswith('http') and absolute_url not in visited_urls:
                            to_visit.append(absolute_url)
                
                # 延时，避免请求过于频繁
                time.sleep(self.delay)
                
            except Exception as e:
                logger.error(f"爬取 {current_url} 时出错: {str(e)}")
        
        logger.info(f"爬取完成，共爬取 {len(results)} 个页面")
        return results