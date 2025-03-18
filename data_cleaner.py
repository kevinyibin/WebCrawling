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
tech_specs = {}
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
        logger.debug(f"开始提取产品名称，URL: {url}")
        product_name = None
        
        # 1. 尝试从元标签中提取
        meta_tags = [
            soup.find('meta', property='og:title'),
            soup.find('meta', attrs={'name': 'title'}),
            soup.find('meta', attrs={'name': 'product:title'}),
            soup.find('meta', attrs={'name': 'twitter:title'})
        ]
        
        for meta in meta_tags:
            if meta and meta.get('content'):
                content = meta.get('content').strip()
                if content and len(content) > 3:
                    logger.debug(f"从元标签提取到产品名称: {content}")
                    product_name = content
                    break
        
        # 2. 尝试从产品名称特定的HTML结构中提取
        if not product_name:
            product_selectors = [
                soup.find('h1', class_=lambda c: c and any(word in str(c).lower() for word in ['product-name', 'product-title', 'product_name', 'product_title', 'productname', 'producttitle'])),
                soup.find('div', class_=lambda c: c and any(word in str(c).lower() for word in ['product-name', 'product-title', 'product_name', 'product_title', 'productname', 'producttitle'])),
                soup.find('span', class_=lambda c: c and any(word in str(c).lower() for word in ['product-name', 'product-title', 'product_name', 'product_title', 'productname', 'producttitle']))
            ]
            
            for selector in product_selectors:
                if selector:
                    text = selector.text.strip()
                    if text and len(text) > 3:
                        logger.debug(f"从产品名称选择器提取到: {text}")
                        product_name = text
                        break
        
        # 3. 尝试从标题中提取
        if not product_name and soup.title:
            title = soup.title.text.strip()
            # 移除常见的网站名称后缀
            title = re.sub(r'\s*[\|\-–—_]\s*.*$', '', title)
            if title and len(title) > 3:
                logger.debug(f"从页面标题提取到: {title}")
                product_name = title
        
        # 4. 尝试从h1标签中提取
        if not product_name:
            h1_tags = soup.find_all('h1')
            for h1 in h1_tags:
                text = h1.text.strip()
                # 检查是否包含无人机相关关键词
                if any(keyword in text.lower() for keyword in ['无人机', 'drone', 'uav', 'quadcopter', 'copter', 'aircraft']):
                    logger.debug(f"从h1标签提取到产品名称: {text}")
                    product_name = text
                    break
                # 如果只有一个h1标签，且长度适中，也可能是产品名称
                elif len(h1_tags) == 1 and 3 < len(text) < 50:
                    logger.debug(f"从唯一h1标签提取到可能的产品名称: {text}")
                    product_name = text
                    break
        
        # 5. 尝试从URL中提取
        if not product_name:
            url_parts = url.split('/')
            for part in url_parts:
                if any(keyword in part.lower() for keyword in ['product', 'drone', 'uav', 'model']):
                    # 清理URL部分，将连字符和下划线替换为空格
                    cleaned_part = re.sub(r'[-_]', ' ', part)
                    if cleaned_part and len(cleaned_part) > 3:  # 避免过短的名称
                        logger.debug(f"从URL提取到产品名称: {cleaned_part.title()}")
                        product_name = cleaned_part.title()
                        break
        
        # 如果仍然无法提取，使用页面标题
        if not product_name and soup.title:
            product_name = soup.title.text.strip()
            logger.debug(f"使用页面标题作为产品名称: {product_name}")
        
        # 清理产品名称
        if product_name:
            # 移除多余空白字符
            product_name = re.sub(r'\s+', ' ', product_name).strip()
            # 移除常见的无关后缀
            product_name = re.sub(r'\s*[\|\-–—_]\s*(官方网站|官网|详情|规格|参数|价格|购买|订购|商城|商店|专卖店).*$', '', product_name)
        
        logger.debug(f"最终提取的产品名称: {product_name}")
        return product_name if product_name else ''
    
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
            str: 产品技术规格文本
        """
        tech_specs_text = ""
        logger.debug("开始提取产品技术规格")
        
        # 技术规格相关关键词
        spec_keywords = [
            '技术参数', '技术规格', '产品规格', '规格参数', '性能参数', '产品参数', '参数配置', 
            '技术指标', '产品特性', '功能特点', '详细参数', '详细规格', '产品参数', '基本参数',
            'specifications', 'technical data', 'parameters', 'performance', 'tech specs',
            'technical specifications', 'product specifications', 'spec sheet'
        ]
        
        # 1. 查找专门的技术规格区域
        spec_containers = []
        
        # 查找可能包含技术规格的容器元素
        for keyword in spec_keywords:
            # 通过ID查找
            elements = soup.find_all(id=lambda i: i and keyword.lower() in i.lower())
            spec_containers.extend(elements)
            
            # 通过class查找
            elements = soup.find_all(class_=lambda c: c and keyword.lower() in c.lower())
            spec_containers.extend(elements)
            
            # 通过标题查找
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            for heading in headings:
                if keyword.lower() in heading.text.lower():
                    # 获取标题后面的元素作为可能的规格容器
                    next_element = heading.find_next_sibling()
                    if next_element:
                        spec_containers.append(next_element)
        
        # 2. 从表格中提取技术规格
        tables = []
        
        # 首先查找专门的规格表格
        for container in spec_containers:
            container_tables = container.find_all('table')
            tables.extend(container_tables)
        
        # 如果没有找到，查找所有表格
        if not tables:
            tables = soup.find_all('table')
        
        for table in tables:
            # 检查表格是否包含技术规格关键词
            table_text = table.text.lower()
            is_spec_table = any(keyword.lower() in table_text for keyword in spec_keywords)
            
            # 如果表格在规格容器中或包含规格关键词
            if is_spec_table or any(container in spec_containers for container in table.parents):
                logger.debug(f"找到可能的技术规格表格")
                
                # 提取表格中的行
                rows = table.find_all('tr')
                for row in rows:
                    # 提取行中的单元格
                    cells = row.find_all(['td', 'th'])
                    
                    # 处理2列表格 (键-值对)
                    if len(cells) >= 2:
                        key = cells[0].text.strip()
                        value = cells[1].text.strip()
                        
                        # 清理和验证键值对
                        key = re.sub(r'\s+', ' ', key)
                        value = re.sub(r'\s+', ' ', value)
                        
                        if key and value and len(key) < 100 and not key.isdigit():
                            # 移除键中的常见后缀
                            key = re.sub(r'[：:*]\s*$', '', key)
                            logger.debug(f"从表格提取: {key} -> {value}")
                            tech_specs[key] = value
                    
                    # 处理多列表格 (尝试识别表头和数据)
                    elif len(cells) > 2:
                        # 尝试识别第一行是否为表头
                        if row.find_parent('thead') or all(cell.name == 'th' for cell in cells):
                            continue  # 跳过表头行
                        
                        # 尝试从同一表格中找到表头行
                        header_row = None
                        for potential_header in table.find_all('tr'):
                            if potential_header.find('th') and potential_header != row:
                                header_row = potential_header
                                break
                        
                        if header_row:
                            header_cells = header_row.find_all(['th', 'td'])
                            # 确保表头单元格数量与数据单元格数量匹配
                            if len(header_cells) == len(cells):
                                for i in range(len(cells)):
                                    key = header_cells[i].text.strip()
                                    value = cells[i].text.strip()
                                    if key and value and key != value and len(key) < 100 and not key.isdigit():
                                        key = re.sub(r'[：:*]\s*$', '', key)
                                        logger.debug(f"从多列表格提取: {key} -> {value}")
                                        tech_specs[key] = value
        
        # 3. 从定义列表(dl/dt/dd)中提取技术规格
        dl_elements = []
        
        # 首先查找规格容器中的定义列表
        for container in spec_containers:
            container_dls = container.find_all('dl')
            dl_elements.extend(container_dls)
        
        # 如果没有找到，查找所有定义列表
        if not dl_elements:
            dl_elements = soup.find_all('dl')
        
        for dl in dl_elements:
            dt_elements = dl.find_all('dt')
            dd_elements = dl.find_all('dd')
            
            # 确保dt和dd元素数量匹配
            if len(dt_elements) == len(dd_elements):
                for i in range(len(dt_elements)):
                    key = dt_elements[i].text.strip()
                    value = dd_elements[i].text.strip()
                    if key and value and len(key) < 100 and not key.isdigit():
                        key = re.sub(r'[：:*]\s*$', '', key)
                        logger.debug(f"从定义列表提取: {key} -> {value}")
                        tech_specs[key] = value
        
        # 4. 从列表中提取技术规格
        spec_lists = []
        
        # 首先查找规格容器中的列表
        for container in spec_containers:
            container_lists = container.find_all(['ul', 'ol'])
            spec_lists.extend(container_lists)
        
        # 如果没有找到，查找可能包含技术规格的列表
        if not spec_lists:
            spec_lists = soup.find_all(['ul', 'ol'], class_=lambda c: c and any(word in str(c).lower() for word in ['spec', 'parameter', 'tech', 'feature']))
        
        # 如果仍然没有找到，查找所有列表
        if not spec_lists:
            # 查找所有列表，但要求在规格相关区域附近
            for keyword in spec_keywords:
                for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    if keyword.lower() in heading.text.lower():
                        next_list = heading.find_next(['ul', 'ol'])
                        if next_list:
                            spec_lists.append(next_list)
        
        for spec_list in spec_lists:
            list_items = spec_list.find_all('li')
            for item in list_items:
                text = item.text.strip()
                # 尝试从列表项中提取键值对
                match = re.search(r'([^:：]+)[：:](.*)', text)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2).strip()
                    if key and value and len(key) < 100 and not key.isdigit():
                        key = re.sub(r'[：:*]\s*$', '', key)
                        logger.debug(f"从列表项提取: {key} -> {value}")
                        tech_specs[key] = value
        
        # 5. 从段落和div中提取技术规格
        spec_paragraphs = []
        
        # 首先查找规格容器中的段落
        for container in spec_containers:
            container_paragraphs = container.find_all(['p', 'div'])
            spec_paragraphs.extend(container_paragraphs)
        
        # 如果没有找到，查找可能包含技术规格的段落
        if not spec_paragraphs:
            spec_paragraphs = soup.find_all(['p', 'div'], class_=lambda c: c and any(word in str(c).lower() for word in ['spec', 'parameter', 'tech', 'feature']))
        
        for paragraph in spec_paragraphs:
            text = paragraph.text.strip()
            # 尝试从段落中提取键值对
            for line in text.split('\n'):
                # 使用更复杂的正则表达式匹配各种格式的键值对
                match = re.search(r'([^:：]+)[：:\s]*([^\n]+)', line)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2).strip()
                    if key and value and len(key) < 100 and not key.isdigit():
                        key = re.sub(r'[：:*]\s*$', '', key)
                        logger.debug(f"从段落提取: {key} -> {value}")
                        tech_specs[key] = value
        
        # 6. 查找具有特定格式的div元素（常见于产品规格展示）
        spec_divs = soup.find_all('div', class_=lambda c: c and any(word in str(c).lower() for word in ['spec-item', 'param-item', 'feature-item']))
        for div in spec_divs:
            # 查找可能的键值对元素
            key_element = div.find(class_=lambda c: c and any(word in str(c).lower() for word in ['name', 'key', 'label', 'title']))
            value_element = div.find(class_=lambda c: c and any(word in str(c).lower() for word in ['value', 'data', 'content']))
            
            if key_element and value_element:
                key = key_element.text.strip()
                value = value_element.text.strip()
                if key and value and len(key) < 100 and not key.isdigit():
                    key = re.sub(r'[：:*]\s*$', '', key)
                    logger.debug(f"从特殊div提取: {key} -> {value}")
                    tech_specs[key] = value
        
        # 将提取的技术规格区域内容合并为纯文本
        tech_specs_text = ""
        
        # 1. 从规格容器中提取文本
        for container in spec_containers:
            container_text = container.get_text(separator='\n', strip=True)
            if container_text:
                tech_specs_text += container_text + "\n\n"
        
        # 2. 从表格中提取文本
        for table in tables:
            table_text = table.get_text(separator='\n', strip=True)
            if table_text:
                tech_specs_text += table_text + "\n\n"
        
        # 3. 从定义列表中提取文本
        for dl in dl_elements:
            dl_text = dl.get_text(separator='\n', strip=True)
            if dl_text:
                tech_specs_text += dl_text + "\n\n"
        
        # 4. 从列表中提取文本
        for spec_list in spec_lists:
            list_text = spec_list.get_text(separator='\n', strip=True)
            if list_text:
                tech_specs_text += list_text + "\n\n"
        
        # 5. 从段落和div中提取文本
        for paragraph in spec_paragraphs:
            para_text = paragraph.get_text(strip=True)
            if para_text:
                tech_specs_text += para_text + "\n"
        
        # 6. 从特定格式的div元素中提取文本
        for div in spec_divs:
            div_text = div.get_text(separator='\n', strip=True)
            if div_text:
                tech_specs_text += div_text + "\n"
        
        # 清理文本，移除多余的空行和空格
        tech_specs_text = re.sub(r'\n{3,}', '\n\n', tech_specs_text)
        tech_specs_text = re.sub(r'\s+', ' ', tech_specs_text)
        tech_specs_text = tech_specs_text.strip()
        
        logger.debug(f"提取到技术规格文本，长度: {len(tech_specs_text)}")
        return tech_specs_text
        
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
            
        # 确保tech_specs是字符串类型
        if isinstance(tech_specs, dict):
            # 兼容旧版本的键值对格式，转换为纯文本
            tech_specs_text = "\n".join([f"{k}: {v}" for k, v in tech_specs.items()])
        else:
            tech_specs_text = tech_specs
        
        # 构建清洗后的页面数据
        cleaned_page = {
            'url': url,
            'company': company,
            'product_name': product_name,
            'description': product_description,
            'tech_specs': tech_specs_text,
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