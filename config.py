#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置文件
存储爬虫的配置信息
"""

def load_config(config_file):
    """
    加载配置文件
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        dict: 配置信息
    """
    # 默认配置
    config = {
        # 爬虫配置
        'timeout': 30,  # 请求超时时间（秒）
        'max_pages': 50,  # 每个公司最多爬取的页面数
        'delay': 1,  # 请求间隔（秒）
        
        # DeepSeek API配置
        'deepseek_api_key': 'sk-986095f8d2224142ab8be578a8fead64',  # 替换为实际的API密钥
        
        # 目标公司列表
        'companies': [
            {
                'name': 'DJI大疆创新',
                'url': 'https://www.dji.com/cn/support?site=brandsite&from=nav'
            },
            # 可以添加更多公司
        ]
    }
    
    return config