from typing import Dict, List, Optional
from openai import OpenAI
import time
import json

class APIClient:
    """
    统一接口的翻译客户端基类。
    """

    def translate(self, text: str, context: Optional[str] = None) -> str:
        """
        翻译文本。
        :param text: 待翻译的文本
        :param context: 上下文提示
        :return: 翻译后的文本
        """
        raise NotImplementedError



class SiliconFlowClient(APIClient):
    """
    SiliconFlow API客户端实现。
    """

    def __init__(self, config:Dict):
        self.api_key = config['api_key']
        self.base_url = "https://api.siliconflow.cn/v1/chat/completions"
        self.modelname = config['modelname']
        self.maxtoken=config['maxtoken']


    def translate(self, text: str, context: Optional[str] = None) -> str:
        """
        使用SiliconFlow API翻译文本 [^1][^2]。
        """
        import requests

        # 添加提示词
        prompt = (
            "请接收含有复杂数学公式、学术表格的英文markdown论文，检查公式以及表格的格式是否正确，并只输出译文，不要有其他说明。"
            f"\n\n原文：{text}"
        )

        payload = {
            "model": self.modelname,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": self.maxtoken,
            "temperature": 0.3,
            "top_p": 0.3,
            "top_k": 50,
            "frequency_penalty": 0.5,
            "response_format": {"type": "text"}
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        response = requests.post(self.base_url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"API请求失败: {response.status_code}")


class DeepSeekClient(APIClient):
    """深度求索(DeepSeek) API客户端实现"""

    def __init__(self, config: Dict):
        self.client = OpenAI(
            api_key=config['api_key'],
            base_url="https://api.deepseek.com"
        )
        self.modelname = config['modelname']
        self.maxtoken = config['maxtoken']
        self.max_retries = config.get('max_retries', 15)  # 默认最大重试次数为3

    def detect_domain(self, text: str) -> str:
        """领域检测方法（返回JSON格式的关键词）"""
        prompt = """请根据以下学术文献的前几段内容判断所属专业领域，返回JSON格式包含单个关键词：
        {
            "domain": "领域关键词"
        }
        
        领域候选示例：大气科学，模拟IC，生物医学工程...
        
        请确保：
        1. 必须识别具体学科方向
        2. 不要概括性表述
        3. 输出严格为JSON格式"""
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system",
                        "content": f"{prompt}"},
                    {"role": "user",
                        "content": f"{text}"}
                ],
                max_tokens=self.maxtoken,
                temperature=0.3,
                frequency_penalty=0,
                stream=False,
                response_format={
                    'type': 'json_object'
                }
            )
            data = json.loads(response.choices[0].message.content)
            print(data['domain'])
            return data['domain']
        except Exception as e:
                return {"domain": "general"}  # 失败时返回通用领域

    def translate(self, text: str, context: Optional[str] = None) -> str:
        """使用DeepSeek API翻译文本（保留原始提示词和参数风格）"""
        retry_count_1 = 0
        retry_count_2 = 0
        errors_1 = []
        errors_2 = []
        prompt="""
        ## 角色定位
        高度精准的英中学术文本翻译引擎，专注将{context}英文文献翻译为中文、学术文档格式校对与完整性修复
        
        ## 翻译规范
        - 保证原文意思没有改变，不要删减原文内容
        - 确保学术用语准确
        - 参考文献部分不翻译
        
        ## 输出规范（特别重要，必须遵守）
        1. 保证输出内容仅有纯净的翻译内容，加括号的解释内容也不行
        1. 禁用任何形式的解释性内容输出
        2. 禁止添加任何注释说明
        3. 屏蔽任何示例展示
        
        ## 领域能力
        1. 数学公式结构验证
        2. 表格格式规范化检测
        3. 语义完整性缝合
        
        ## 格式处理规则
        ### 公式验证标准
        - 检查所有`$$...$$`区块完整性
        - 确认公式特殊符号转译有效性
        
        ### 表格处理协议
        1. 强制采用管道符表格格式
        2. 表尾保留两个连续`\n`换行符
        3. 验证列宽一致性
        
        ## 语段整合机制
        - 监测未闭合段落（缺失终止标点）
        - 基于语法树完成段落重组
        - 消除断行字符干扰
        """
        for i in range(1):
            while retry_count_1 < self.max_retries:
                try:
                    response = self.client.chat.completions.create(
                        model=self.modelname,
                        messages=[
                            {"role": "system", "content": f"{prompt}"},
                            {"role": "user", "content": f"{text}"}
                        ],
                        max_tokens=self.maxtoken,
                        temperature=0.3,
                        frequency_penalty=0,###就是你！！！！！！！，终于找到问题了！！！！
                        stream=False
                    )
                    break
                except Exception as e:
                    errors_1.append(str(e))
                    retry_count_1 += 1
                    print("1_")
                    print(retry_count_1)
                    if retry_count_1 < self.max_retries:
                        time.sleep(2)  # 重试前等待1秒
            if retry_count_1==self.max_retries:
                raise Exception(f"DeepSeek API请求失败，重试 {self.max_retries} 次后仍然失败。错误信息: {', '.join(errors_1)}")
            while retry_count_2 < self.max_retries:
                try:
                    # 调用R1模型检查翻译是否完整
                    check = self.client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system",
                             "content": """判断译文是否完整无删减地翻译了原文的内容或者是否存在多余内容（不能有多余的注释等），如果翻译完整且无多余内容，输出True，否则False，仅返回JSON：{"is_valid": bool}"""},
                            {"role": "user",
                             "content": f"原文：\n{text}\n\n译文：\n{response.choices[0].message.content}"}
                        ],
                        max_tokens=self.maxtoken,
                        temperature=0.3,
                        frequency_penalty=0,
                        stream=False,
                        response_format={
                            'type': 'json_object'
                        }
                    )
                    break
                except Exception as e:
                    errors_2.append(str(e))
                    retry_count_2 += 1
                    print("2_")
                    print(retry_count_2)
                    if retry_count_2 < self.max_retries:
                        time.sleep(2)  # 重试前等待1秒
            if retry_count_2==self.max_retries:
                raise Exception(f"DeepSeek API请求失败，重试 {self.max_retries} 次后仍然失败。错误信息: {', '.join(errors_2)}")
            data = json.loads(check.choices[0].message.content)
            print(data)
            if data['is_valid'] == True:
                break
            elif data['is_valid'] == False and i == 4:
                print("段落翻译不完整")
        return response.choices[0].message.content
    

def api_client_factory(config:Dict) -> APIClient:
    """
    根据提供者创建翻译客户端 [^1][^2]。
    :param provider: API提供者名称
    :param api_key: API密钥
    :return: 统一接口的翻译客户端
    """
    if config['provider'] == "siliconflow":
        return SiliconFlowClient(config)
    elif config['provider'] == "deepseek":
        return DeepSeekClient(config)
    else:
        raise ValueError(f"不支持的提供者: {config['provider']}")




