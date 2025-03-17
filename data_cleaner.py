#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据清洗模块
负责提取产品技术规格相关的内容
"""

import logging
import re
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class DataCleaner:
    """
    数据清洗类，负责从爬取的网页中提取产品信息
    """
    
    def __init__(self):
        """
        初始化数据清洗器
        """
        # 产品相关的关键词
        self.product_keywords = [
            '无人机', '飞行器', '无人飞行器', 'UAV', 'drone', 
            '产品', '技术参数', '规格', 'specification', 
            '飞行时间', '续航', '载荷', 'payload', '摄像头', 'camera',
            '重量', 'weight', '尺寸', 'dimension', '速度', 'speed'
        ]
        
        # 产品页面可能的URL特征
        self.product_url_patterns = [
            r'/product', r'/products', r'/drone', r'/uav',
            r'/specification', r'/tech', r'/technical', r'/detail'
        ]
    
    def clean(self, raw_data):
        """
        清洗爬取的原始数据，提取产品信息
        
        Args:
            raw_data: 爬取的原始数据列表
            
        Returns:
            list: 提取的产品信息列表
        """
        products = []
        
        # 首先筛选可能包含产品信息的页面
        product_pages = self._filter_product_pages(raw_data)
        logger.info(f"筛选出 {len(product_pages)} 个可能包含产品信息的页面")
        
        # 从筛选出的页面中提取产品信息
        for page in product_pages:
            extracted_products = self._extract_product_info(page)
            if extracted_products:
                products.extend(extracted_products)
        
        logger.info(f"共提取出 {len(products)} 个产品信息")
        return products
    
    def _filter_product_pages(self, raw_data):
        """
        筛选可能包含产品信息的页面
        
        Args:
            raw_data: 爬取的原始数据列表
            
        Returns:
            list: 可能包含产品信息的页面列表
        """
        product_pages = []
        
        for page in raw_data:
            url = page['url']
            content = page['content']
            
            # 检查URL是否符合产品页面特征
            if any(re.search(pattern, url, re.IGNORECASE) for pattern in self.product_url_patterns):
                product_pages.append(page)
                continue
            
            # 检查页面内容是否包含产品关键词
            if any(keyword in content.lower() for keyword in self.product_keywords):
                product_pages.append(page)
                continue
        
        return product_pages
    
    def _extract_product_info(self, page):
        """
        从页面中提取产品信息
        
        Args:
            page: 页面数据
            
        Returns:
            list: 提取的产品信息列表
        """
        products = []
        url = page['url']
        company = page['company']
        soup = BeautifulSoup(page['html'], 'html.parser')
        
        # 尝试提取产品名称
        product_name = self._extract_product_name(soup, url)
        
        # 尝试提取产品描述
        product_description = self._extract_product_description(soup)
        
        # 尝试提取产品技术规格
        tech_specs = self._extract_tech_specs(soup)
        
        # 如果提取到了产品信息，则添加到结果中
        if product_name and (product_description or tech_specs):
            product = {
                'name': product_name,
                'company': company,
                'url': url,
                'description': product_description,
                'tech_specs': tech_specs
            }
            products.append(product)
        
        return products
    
    def _extract_product_name(self, soup, url):
        """
        提取产品名称
        
        Args:
            soup: BeautifulSoup对象
            url: 页面URL
            
        Returns:
            str: 产品名称
        """
        # 尝试从标题中提取
        title = soup.title.text if soup.title else ''
        
        # 尝试从h1标签中提取
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags:
            text = h1.text.strip()
            if any(keyword in text.lower() for keyword in ['无人机', 'drone', 'uav']):
                return text
        
        # 尝试从URL中提取
        url_parts = url.split('/')
        for part in url_parts:
            if any(keyword in part.lower() for keyword in ['product', 'drone', 'uav']):
                # 清理URL部分，将连字符和下划线替换为空格
                cleaned_part = re.sub(r'[-_]', ' ', part)
                if cleaned_part and len(cleaned_part) > 3:  # 避免过短的名称
                    return cleaned_part.title()
        
        # 如果无法提取，则返回标题
        return title
    
    def _extract_product_description(self, soup):
        """
        提取产品描述
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            str: 产品描述
        """
        # 尝试查找产品描述段落
        description = ''
        
        # 查找可能包含描述的元素
        description_elements = soup.find_all(['p', 'div'], class_=lambda c: c and any(word in c.lower() for word in ['desc', 'intro', 'about', 'overview']))
        
        for element in description_elements:
            text = element.text.strip()
            if len(text) > 50:  # 避免过短的描述
                description += text + '\n'
        
        # 如果没有找到，尝试查找页面中的长段落
        if not description:
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.text.strip()
                if len(text) > 100:  # 只考虑较长的段落
                    description += text + '\n'
                    if len(description) > 500:  # 限制描述长度
                        break
        
        return description.strip()
    
    def _extract_tech_specs(self, soup):
        """
        提取产品技术规格
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            dict: 产品技术规格字典
        """
        tech_specs = {}
        
        # 尝试查找技术规格表格
        tables = soup.find_all('table')
        for table in tables:
            # 检查表格是否包含技术规格关键词
            table_text = table.text.lower()
            if any(keyword in table_text for keyword in ['技术参数', '规格', 'specification', 'parameter']):
                # 提取表格中的行
                rows = table.find_all('tr')
                for row in rows:
                    # 提取行中的单元格
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = cells[0].text.strip()
                        value = cells[1].text.strip()
                        if key and value:
                            tech_specs[key] = value
        
        # 尝试查找技术规格列表
        if not tech_specs:
            # 查找可能包含技术规格的列表
            spec_lists = soup.find_all(['ul', 'ol'], class_=lambda c: c and any(word in c.lower() for word in ['spec', 'parameter', 'tech']))
            
            for spec_list in spec_lists:
                list_items = spec_list.find_all('li')
                for item in list_items:
                    text = item.text.strip()
                    # 尝试从列表项中提取键值对
                    match = re.search(r'([^:：]+)[：:](.*)', text)
                    if match:
                        key = match.group(1).strip()
                        value = match.group(2).strip()
                        if key and value:
                            tech_specs[key] = value
        
        # 尝试从段落中提取技术规格
        if not tech_specs:
            # 查找可能包含技术规格的段落
            spec_paragraphs = soup.find_all(['p', 'div'], class_=lambda c: c and any(word in c.lower() for word in ['spec', 'parameter', 'tech']))
            
            for paragraph in spec_paragraphs:
                text = paragraph.text.strip()
                # 尝试从段落中提取键值对
                for line in text.split('\n'):
                    match = re.search(r'([^:：]+)[：:](.*)', line)
                    if match:
                        key = match.group(1).strip()
                        value = match.group(2).strip()
                        if key and value:
                            tech_specs[key] = value
        
        return tech_specs