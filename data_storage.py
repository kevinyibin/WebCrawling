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
    
    def save(self, company_name, products_data):
        """
        保存公司产品数据
        
        Args:
            company_name: 公司名称
            products_data: 产品数据列表
        """
        # 创建公司目录
        company_dir = os.path.join(self.base_dir, company_name)
        os.makedirs(company_dir, exist_ok=True)
        
        # 生成时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存完整数据
        full_data_path = os.path.join(company_dir, f"products_{timestamp}.json")
        with open(full_data_path, 'w', encoding='utf-8') as f:
            json.dump(products_data, f, ensure_ascii=False, indent=2)
        
        # 保存简化版数据（CSV格式，便于查看）
        summary_path = os.path.join(company_dir, f"summary_{timestamp}.csv")
        with open(summary_path, 'w', encoding='utf-8') as f:
            # 写入CSV头
            f.write("产品名称,特点,应用场景,URL\n")
            
            # 写入每个产品的数据
            for product in products_data:
                name = product.get('name', '').replace(',', ' ')
                features = product.get('features', '').replace(',', ' ')
                applications = product.get('applications', '').replace(',', ' ')
                url = product.get('url', '')
                
                f.write(f"{name},{features},{applications},{url}\n")
        
        logger.info(f"已保存 {len(products_data)} 个产品数据到 {full_data_path} 和 {summary_path}")
        
        return full_data_path, summary_path