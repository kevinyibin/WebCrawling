#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据存储模块
负责以结构化的形式保存处理后的数据
"""

import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DataStorage:
    """
    数据存储类，负责保存处理后的数据
    """
    
    def __init__(self, base_dir='data'):
        """
        初始化数据存储器
        
        Args:
            base_dir: 数据存储的基础目录
        """
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
    
    def save(self, company_name, product_pages):
        """
        保存公司产品页面数据
        
        Args:
            company_name: 公司名称
            product_pages: 筛选后的产品页面数据列表
        """
        # 创建公司目录
        company_dir = os.path.join(self.base_dir, company_name)
        os.makedirs(company_dir, exist_ok=True)
        
        # 生成时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存完整原始网页数据
        full_data_path = os.path.join(company_dir, f"products_{timestamp}.json")
        with open(full_data_path, 'w', encoding='utf-8') as f:
            json.dump(product_pages, f, ensure_ascii=False, indent=2)
        
        # 保存简化版数据（CSV格式，便于查看）
        summary_path = os.path.join(company_dir, f"summary_{timestamp}.csv")
        with open(summary_path, 'w', encoding='utf-8') as f:
            # 写入CSV头
            f.write("URL,标题,公司\n")
            
            # 写入每个产品页面的基本信息
            for page in product_pages:
                url = page.get('url', '')
                title = page.get('title', '').replace(',', ' ') if 'title' in page else ''
                company = page.get('company', '')
                
                # 如果没有标题字段，尝试从HTML中提取
                if not title and 'html' in page:
                    from bs4 import BeautifulSoup
                    try:
                        soup = BeautifulSoup(page['html'], 'html.parser')
                        title = soup.title.text.strip().replace(',', ' ') if soup.title else ''
                    except Exception as e:
                        logger.warning(f"从HTML提取标题失败: {e}")
                
                f.write(f"{url},{title},{company}\n")
        
        logger.info(f"已保存 {len(product_pages)} 个产品页面数据到 {full_data_path} 和 {summary_path}")
        
        return full_data_path, summary_path