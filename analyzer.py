#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
分析模块
使用DeepSeek模型分析数据并生成产品特点和应用场景的摘要
"""

import logging
import requests
import json
import time

logger = logging.getLogger(__name__)

class Analyzer:
    """
    分析类，使用DeepSeek模型分析产品数据
    """
    
    def __init__(self, api_key):
        """
        初始化分析器
        
        Args:
            api_key: DeepSeek API密钥
        """
        # 使用传入的API密钥，而不是硬编码覆盖
        self.api_key = api_key
        # 修正API端点URL
        self.api_url = "https://api.deepseek.com/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        # 设置重试次数和超时时间
        self.max_retries = 3
        self.timeout = 60  # 增加超时时间到60秒
    
    def analyze(self, product):
        """
        分析产品数据，生成特点和应用场景摘要
        
        Args:
            product: 产品数据字典
            
        Returns:
            dict: 包含特点和应用场景的字典
        """
        try:
            # 构建提示词
            prompt = self._build_prompt(product)
            
            # 调用DeepSeek API
            response = self._call_deepseek_api(prompt)
            
            # 解析响应
            features, applications = self._parse_response(response)
            
            return {
                'features': features,
                'applications': applications
            }
            
        except Exception as e:
            logger.error(f"分析产品 {product.get('name', '未知')} 时出错: {str(e)}")
            return {
                'features': '',
                'applications': ''
            }
    
    def _build_prompt(self, product):
        """
        构建提示词
        
        Args:
            product: 产品数据字典
            
        Returns:
            str: 提示词
        """
        name = product.get('name', '')
        description = product.get('description', '')
        tech_specs = product.get('tech_specs', {})
        
        # 将技术规格转换为文本
        tech_specs_text = '\n'.join([f"{k}: {v}" for k, v in tech_specs.items()])
        
        prompt = f"""请分析以下无人机产品信息，并完成两个任务：
                    1. 用一句话总结该产品的特点
                    2. 用一句话描述该产品的主要应用场景

                    产品名称：{name}

                    产品描述：
                    {description}

                    技术规格：
                    {tech_specs_text}

                    请按照以下格式回答：
                    特点：[一句话总结产品特点]
                    应用场景：[一句话描述主要应用场景]"""
        
        return prompt
    
    def _call_deepseek_api(self, prompt):
        """
        调用DeepSeek API，带有重试机制
        
        Args:
            prompt: 提示词
            
        Returns:
            str: API响应文本
        """
        # 调整请求格式，符合DeepSeek API的要求
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一个帮助分析产品信息的智能助手。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        # 实现重试机制
        for attempt in range(self.max_retries):
            try:
                logger.info(f"API请求尝试 {attempt + 1}/{self.max_retries}")
                
                # 使用更长的超时时间
                response = requests.post(
                    self.api_url, 
                    headers=self.headers, 
                    json=payload, 
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                result = response.json()
                return result['choices'][0]['message']['content']
                
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    logger.error("所有重试都失败，放弃请求")
                    raise
                # 指数退避策略
                time.sleep(2 ** attempt)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"API请求失败: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise
                # 指数退避策略
                time.sleep(2 ** attempt)
    
    def _parse_response(self, response):
        """
        解析API响应
        
        Args:
            response: API响应文本
            
        Returns:
            tuple: (特点, 应用场景)
        """
        features = ""
        applications = ""
        
        # 解析响应文本
        lines = response.strip().split('\n')
        for line in lines:
            if line.startswith('特点：'):
                features = line[3:].strip()
            elif line.startswith('应用场景：'):
                applications = line[5:].strip()
        
        return features, applications