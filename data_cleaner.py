#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据清洗模块
负责使用DeepSeek模型筛选和提取产品技术规格相关的内容
"""

import logging
import re
from bs4 import BeautifulSoup
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

logger = logging.getLogger(__name__)

class DataCleaner:
    """
    数据清洗类，负责从爬取的网页中提取产品信息
    """
    
    def __init__(self):
        """
        初始化数据清洗器，加载DeepSeek模型
        """
        # 加载DeepSeek模型和分词器
        self.tokenizer = AutoTokenizer.from_pretrained("deepseek-ai/deepseek-coder-1.3b-base")
        self.model = AutoModelForSequenceClassification.from_pretrained("deepseek-ai/deepseek-coder-1.3b-base", num_labels=2)
        self.model.eval()
        
        # 产品页面可能的URL特征
        self.product_url_patterns = [
            r'/product', r'/products', r'/drone', r'/uav',
            r'/specification', r'/tech', r'/technical', r'/detail'
        ]
    
    def clean(self, raw_data):
        """
        清洗爬取的原始数据，筛选包含产品技术规格的页面并移除无关内容
        
        Args:
            raw_data: 爬取的原始数据列表
            
        Returns:
            list: 清洗后的产品页面数据列表
        """
        # 筛选可能包含产品信息的页面
        product_pages = self._filter_product_pages(raw_data)
        logger.info(f"筛选出 {len(product_pages)} 个可能包含产品信息的页面")
        
        # 清洗每个产品页面的内容
        cleaned_pages = []
        for page in product_pages:
            cleaned_page = self._clean_page_content(page)
            if cleaned_page:
                cleaned_pages.append(cleaned_page)
        
        logger.info(f"完成内容清洗，保留 {len(cleaned_pages)} 个有效页面")
        return cleaned_pages
    
    def _filter_product_pages(self, raw_data):
        """
        使用DeepSeek模型筛选包含产品技术规格的页面
        
        Args:
            raw_data: 爬取的原始数据列表
            
        Returns:
            list: 包含产品技术规格的页面列表
        """
        product_pages = []
        
        for page in raw_data:
            url = page['url']
            content = page['content']
            
            # 首先检查URL是否符合产品页面特征
            if any(re.search(pattern, url, re.IGNORECASE) for pattern in self.product_url_patterns):
                # 使用DeepSeek模型进行内容分析
                if self._is_product_spec_page(content):
                    product_pages.append(page)
        
        return product_pages
        
    def _is_product_spec_page(self, content):
        """
        使用DeepSeek模型判断页面是否包含产品技术规格
        
        Args:
            content: 页面内容
            
        Returns:
            bool: 是否包含产品技术规格
        """
        # 检查内容中是否包含技术规格相关的关键词
        tech_keywords = [
            '技术参数', '技术规格', '产品规格', '规格参数', '性能参数', 
            '产品参数', '参数配置', '技术指标', '产品特性', '功能特点',
            'specifications', 'technical data', 'parameters', 'performance',
            'features', 'dimensions', 'weight', 'battery', 'camera', 'sensor',
            '飞行时间', '续航时间', '最大速度', '最大高度', '控制距离', '载重',
            '分辨率', '像素', '重量', '电池', '相机', '传感器', '遥控器'
        ]
        
        # 如果内容中包含技术规格关键词，增加识别的可能性
        keyword_match = any(keyword in content.lower() for keyword in tech_keywords)
        
        # 准备模型输入，增强提示词
        prompt = "判断以下文本是否包含无人机或相关产品的技术规格、参数、性能指标等信息：\n" + content[:1000]
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        
        # 使用模型进行预测
        with torch.no_grad():
            outputs = self.model(**inputs)
            prediction = torch.softmax(outputs.logits, dim=1)
            model_confidence = prediction[0][1].item()
            
            # 降低阈值，提高识别率，如果有关键词匹配，进一步降低阈值
            threshold = 0.2 if keyword_match else 0.3
            is_spec_page = model_confidence > threshold
            
            logger.debug(f"页面识别置信度: {model_confidence:.4f}, 阈值: {threshold}, 关键词匹配: {keyword_match}")
        
        return is_spec_page
    
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
        
    def _clean_page_content(self, page):
        """
        清洗页面内容，只保留产品相关的文字内容
        
        Args:
            page: 页面数据
            
        Returns:
            dict: 清洗后的页面数据
        """
        if not page or 'html' not in page:
            return None
            
        url = page['url']
        company = page['company']
        html_content = page['html']
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除常见的无关元素
        self._remove_irrelevant_elements(soup)
        
        # 提取产品名称
        product_name = self._extract_product_name(soup, url)
        
        # 提取产品描述
        product_description = self._extract_product_description(soup)
        
        # 提取产品技术规格
        tech_specs = self._extract_tech_specs(soup)
        
        # 提取主要内容区域的文本
        main_content = self._extract_main_content(soup)
        
        # 如果没有提取到有效内容，返回None
        if not product_name and not product_description and not tech_specs and not main_content:
            return None
        
        # 构建清洗后的页面数据
        cleaned_page = {
            'url': url,
            'company': company,
            'product_name': product_name,
            'description': product_description,
            'tech_specs': tech_specs,
            'content': main_content
        }
        
        return cleaned_page
    
    def _remove_irrelevant_elements(self, soup):
        """
        移除页面中的无关元素
        
        Args:
            soup: BeautifulSoup对象
        """
        # 移除脚本和样式
        for element in soup(['script', 'style', 'iframe', 'noscript']):
            element.decompose()
        
        # 移除导航栏
        nav_elements = soup.find_all(['nav', 'header'])
        for nav in nav_elements:
            nav.decompose()
        
        # 移除页脚
        footer_elements = soup.find_all(['footer'])
        for footer in footer_elements:
            footer.decompose()
        
        # 移除可能的广告区域
        ad_elements = soup.find_all(class_=lambda c: c and any(word in str(c).lower() for word in ['ad', 'ads', 'advertisement', 'banner']))
        for ad in ad_elements:
            ad.decompose()
        
        # 移除社交媒体链接区域
        social_elements = soup.find_all(class_=lambda c: c and any(word in str(c).lower() for word in ['social', 'share', 'follow']))
        for social in social_elements:
            social.decompose()
        
        # 移除评论区域
        comment_elements = soup.find_all(class_=lambda c: c and any(word in str(c).lower() for word in ['comment', 'comments', 'discuss']))
        for comment in comment_elements:
            comment.decompose()
    
    def _extract_main_content(self, soup):
        """
        提取页面主要内容区域的文本
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            str: 主要内容文本
        """
        # 尝试查找主要内容区域
        main_content = ''
        
        # 尝试查找主要内容容器
        main_elements = soup.find_all(['main', 'article', 'section', 'div'], 
                                     id=lambda i: i and any(word in str(i).lower() for word in ['content', 'main', 'article', 'product']),
                                     class_=lambda c: c and any(word in str(c).lower() for word in ['content', 'main', 'article', 'product']))
        
        # 如果找到了主要内容容器
        if main_elements:
            for element in main_elements:
                # 提取段落文本
                paragraphs = element.find_all('p')
                for p in paragraphs:
                    text = p.text.strip()
                    if text and len(text) > 20:  # 忽略过短的段落
                        main_content += text + '\n\n'
                
                # 提取列表文本
                lists = element.find_all(['ul', 'ol'])
                for list_element in lists:
                    items = list_element.find_all('li')
                    for item in items:
                        text = item.text.strip()
                        if text:
                            main_content += '• ' + text + '\n'
                    main_content += '\n'
                
                # 提取标题文本
                headings = element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                for heading in headings:
                    text = heading.text.strip()
                    if text:
                        main_content += text + '\n\n'
        
        # 如果没有找到主要内容容器，尝试直接提取所有段落和列表
        if not main_content:
            # 提取所有段落
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.text.strip()
                if text and len(text) > 20:  # 忽略过短的段落
                    main_content += text + '\n\n'
            
            # 提取所有列表
            lists = soup.find_all(['ul', 'ol'])
            for list_element in lists:
                items = list_element.find_all('li')
                for item in items:
                    text = item.text.strip()
                    if text:
                        main_content += '• ' + text + '\n'
                main_content += '\n'
        
        # 清理文本，移除多余的空白字符和换行符
        main_content = re.sub(r'\s+', ' ', main_content).strip()
        main_content = re.sub(r'\n\s*\n', '\n\n', main_content)
        
        return main_content