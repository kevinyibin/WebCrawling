#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试分析模块
"""

import logging
import sys

from analyzer import Analyzer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_analyzer():
    """测试分析器功能"""
    
    # 替换为您的实际API密钥
    api_key = "sk-986095f8d2224142ab8be578a8fead64"  # 注意：实际应用中应从环境变量或配置文件中读取
    
    # 创建分析器实例
    analyzer = Analyzer(api_key)
    
    # 测试产品数据
    test_product = {
        "name": "测试无人机",
        "description": "这是一款高性能的专业级无人机，配备4K高清摄像头，30分钟续航时间，最大飞行高度500米。",
        "tech_specs": {
            "摄像头": "4K高清",
            "续航时间": "30分钟",
            "最大飞行高度": "500米",
            "重量": "1.2kg"
        }
    }
    
    try:
        # 分析产品
        logger.info("开始分析产品...")
        result = analyzer.analyze(test_product)
        
        # 输出结果
        logger.info(f"分析结果:")
        logger.info(f"特点: {result['features']}")
        logger.info(f"应用场景: {result['applications']}")
        
        return True
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_analyzer()
    if success:
        logger.info("测试成功完成!")
    else:
        logger.error("测试失败!")
        sys.exit(1) 