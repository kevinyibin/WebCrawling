#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主程序入口
负责协调爬虫、数据清洗、分析和存储模块的工作流程
"""

import os
import logging
import argparse
from datetime import datetime

from crawler import Crawler
from data_cleaner import DataCleaner
from data_storage import DataStorage
from config import load_config

# 确保日志目录存在
os.makedirs('logs', exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/crawler_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='公司网络爬虫系统')
    parser.add_argument('--config', type=str, default='config.py', help='配置文件路径')
    parser.add_argument('--company', type=str, help='指定爬取的公司名称')
    args = parser.parse_args()
    
    # 确保数据目录存在
    os.makedirs('data', exist_ok=True)
    
    # 加载配置
    config = load_config(args.config)
    
    # 如果指定了公司，则只爬取该公司
    if args.company:
        companies = [c for c in config['companies'] if c['name'] == args.company]
        if not companies:
            logger.error(f"未找到指定的公司: {args.company}")
            return
    else:
        companies = config['companies']
    
    # 初始化各模块
    crawler = Crawler(config)
    cleaner = DataCleaner()
    storage = DataStorage()
    
    # 处理每个公司
    for company in companies:
        logger.info(f"开始处理公司: {company['name']}")
        
        # 爬取公司网站
        raw_data = crawler.crawl(company)
        logger.info(f"爬取完成，获取到 {len(raw_data)} 个页面")
        
        # 数据清洗，筛选包含产品技术规格的页面
        product_pages = cleaner.clean(raw_data)
        logger.info(f"数据清洗完成，筛选出 {len(product_pages)} 个产品页面")
        
        # 存储结果
        storage.save(company['name'], product_pages)
        logger.info(f"公司 {company['name']} 的原始网页数据已保存")
    
    logger.info("所有任务完成")


if __name__ == "__main__":
    main()