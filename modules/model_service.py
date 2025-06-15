import json
import requests
import os
from typing import Dict, Any, List, Optional, Union
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ModelService:
    """模型服务基类，定义通用接口"""

    def extract_info(self, content: str, extraction_type: str = "product") -> Dict[Any, Any]:
        """
        从内容中提取信息
        :param content: 要分析的文本内容
        :param extraction_type: 提取类型，如"product"表示产品信息
        :return: 提取的结构化信息
        """
        raise NotImplementedError("Subclasses must implement this method")

    def chat(self, messages: List[Dict[str, Any]], temperature: float = 0.7, stream: bool = False) -> Dict[str, Any]:
        """
        聊天接口
        :param messages: 消息列表
        :param temperature: 温度参数
        :param stream: 是否流式输出
        :return: 模型响应
        """
        raise NotImplementedError("Subclasses must implement this method")


class QianfanModelService(ModelService):
    """百度千帆大模型服务"""

    def __init__(self, api_key: str = None, authorization: str = None, model: str = "ernie-4.5-turbo-vl-32k"):
        """
        初始化千帆大模型服务
        :param api_key: API密钥（可选）
        :param authorization: 授权令牌（必须提供）
        :param model: 使用的模型名称
        """
        self.authorization = authorization or os.environ.get("QIANFAN_AUTHORIZATION")
        self.model = model

        if not self.authorization:
            raise ValueError("千帆授权令牌未设置，请设置QIANFAN_AUTHORIZATION环境变量或在初始化时提供")

        # 配置请求会话，处理代理问题
        self.session = requests.Session()

        # 尝试禁用代理
        self.session.proxies = {
            'http': None,
            'https': None
        }

        # 设置超时和重试
        self.session.timeout = 30

        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

    def chat(self, messages: List[Dict[str, Any]], temperature: float = 0.7, stream: bool = False) -> Dict[str, Any]:
        """
        调用千帆大模型聊天接口
        :param messages: 消息列表
        :param temperature: 温度参数，控制响应的随机性
        :param stream: 是否使用流式响应
        :return: 模型响应
        """
        url = "https://qianfan.baidubce.com/v2/chat/completions"

        # 处理消息格式 - 兼容不同的输入格式
        formatted_messages = []
        for msg in messages:
            if msg["role"] == "system":
                # 系统消息转换为用户消息的前缀
                continue
            elif isinstance(msg["content"], str):
                # 如果内容是字符串，转换为千帆API所需的格式
                formatted_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            else:
                # 如果已经是正确格式，直接使用
                formatted_messages.append(msg)

        # 如果有系统消息，将其合并到第一个用户消息中
        system_content = ""
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"] + "\n\n"
                break

        if system_content and formatted_messages:
            first_user_msg = formatted_messages[0]
            if first_user_msg["role"] == "user":
                first_user_msg["content"] = system_content + first_user_msg["content"]

        # 构建请求体
        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "stream": stream
        }

        # 添加可选参数
        if temperature is not None:
            payload["temperature"] = temperature

        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": self.authorization
        }

        try:
            # 发送请求
            response = self.session.post(
                url,
                headers=headers,
                json=payload,
                timeout=30,
                verify=False  # 忽略SSL验证
            )

            # 解析响应
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                raise Exception(f"API请求失败: {response.status_code} {response.text}")

        except requests.exceptions.ProxyError as e:
            # 如果是代理错误，尝试使用备用方法
            print(f"代理错误，尝试直接连接: {e}")

            # 创建新的会话，完全禁用代理
            backup_session = requests.Session()
            backup_session.trust_env = False  # 忽略环境变量中的代理设置

            response = backup_session.post(
                url,
                headers=headers,
                json=payload,
                timeout=30,
                verify=False
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"API请求失败: {response.status_code} {response.text}")

        except Exception as e:
            raise Exception(f"网络请求失败: {str(e)}")

    def extract_info(self, content: str, extraction_type: str = "product") -> Dict[Any, Any]:
        """
        使用千帆大模型从内容中提取信息
        :param content: 要分析的文本内容
        :param extraction_type: 提取类型，如"product"表示产品信息
        :return: 提取的结构化信息
        """
        # 根据提取类型构建不同的提示词
        if extraction_type == "product":
            prompt = self._build_product_extraction_prompt(content)
        else:
            raise ValueError(f"不支持的提取类型: {extraction_type}")

        # 调用模型
        messages = [{
            "role": "user",
            "content": prompt
        }]

        response = self.chat(messages)

        # 解析响应
        try:
            if "choices" in response and len(response["choices"]) > 0:
                text_response = response["choices"][0]["message"]["content"]

                # 尝试从文本中提取JSON
                start_pos = text_response.find('{')
                end_pos = text_response.rfind('}') + 1

                if start_pos >= 0 and end_pos > start_pos:
                    json_str = text_response[start_pos:end_pos]
                    result = json.loads(json_str)
                    return result
                else:
                    raise ValueError("无法从响应中提取有效的JSON")
            else:
                raise ValueError(f"模型响应错误: {response}")
        except Exception as e:
            print(f"解析模型响应失败: {e}")
            print(f"原始响应: {response}")
            # 返回一个空结构，避免程序崩溃
            return {
                "product_name": "",
                "parameters": [],
                "selling_points": [],
                "technical_specs": []
            }

    def _build_product_extraction_prompt(self, content: str) -> str:
        """
        构建产品信息提取的提示词
        :param content: 文档内容
        :return: 提示词
        """
        return f"""
        请从以下文档中提取产品相关信息，并以JSON格式返回。需要提取的信息包括：
        1. 产品名称
        2. 产品参数（如尺寸、重量、材质等）
        3. 产品卖点描述
        4. 技术指标（如性能参数、规格标准等）

        请以以下JSON格式返回：
        {{
            "product_name": "产品名称",
            "parameters": [
                {{"name": "参数名称1", "value": "参数值1"}},
                {{"name": "参数名称2", "value": "参数值2"}},
                ...
            ],
            "selling_points": [
                "卖点1",
                "卖点2",
                ...
            ],
            "technical_specs": [
                {{"name": "指标名称1", "value": "指标值1"}},
                {{"name": "指标名称2", "value": "指标值2"}},
                ...
            ]
        }}

        文档内容：
        {content}
        """


class OllamaModelService(ModelService):
    """Ollama模型服务"""

    def __init__(self, host: str = "http://127.0.0.1:11434", model: str = "llama3"):
        """
        初始化Ollama模型服务
        :param host: Ollama服务器地址
        :param model: 使用的模型名称
        """
        try:
            import ollama
            self.client = ollama.Client(host=host)
            self.model = model
        except ImportError:
            raise ImportError("请安装ollama包: pip install ollama")

    def chat(self, messages: List[Dict[str, Any]], temperature: float = 0.7, stream: bool = False) -> Dict[str, Any]:
        """
        Ollama聊天接口
        :param messages: 消息列表
        :param temperature: 温度参数
        :param stream: 是否流式输出
        :return: 模型响应
        """
        response = self.client.chat(
            model=self.model,
            messages=messages,
            stream=stream,
            options={"temperature": temperature}
        )

        if stream:
            return response
        else:
            # 转换为统一格式
            return {
                "choices": [{
                    "message": {
                        "content": response['message']['content']
                    }
                }]
            }

    def extract_info(self, content: str, extraction_type: str = "product") -> Dict[Any, Any]:
        """
        使用Ollama模型从内容中提取信息
        :param content: 要分析的文本内容
        :param extraction_type: 提取类型，如"product"表示产品信息
        :return: 提取的结构化信息
        """
        # 根据提取类型构建不同的提示词
        if extraction_type == "product":
            prompt = self._build_product_extraction_prompt(content)
        else:
            raise ValueError(f"不支持的提取类型: {extraction_type}")

        # 调用模型
        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )

        # 解析响应
        try:
            # 尝试直接解析JSON
            text_response = response['message']['content']

            # 尝试从文本中提取JSON
            start_pos = text_response.find('{')
            end_pos = text_response.rfind('}') + 1

            if start_pos >= 0 and end_pos > start_pos:
                json_str = text_response[start_pos:end_pos]
                result = json.loads(json_str)
                return result
            else:
                raise ValueError("无法从响应中提取有效的JSON")
        except Exception as e:
            print(f"解析模型响应失败: {e}")
            # 返回一个空结构，避免程序崩溃
            return {
                "product_name": "",
                "parameters": [],
                "selling_points": [],
                "technical_specs": []
            }

    def _build_product_extraction_prompt(self, content: str) -> str:
        """
        构建产品信息提取的提示词
        :param content: 文档内容
        :return: 提示词
        """
        return f"""
        请从以下文档中提取产品相关信息，并以JSON格式返回。需要提取的信息包括：
        1. 产品名称
        2. 产品参数（如尺寸、重量、材质等）
        3. 产品卖点描述
        4. 技术指标（如性能参数、规格标准等）

        请以以下JSON格式返回：
        {{
            "product_name": "产品名称",
            "parameters": [
                {{"name": "参数名称1", "value": "参数值1"}},
                {{"name": "参数名称2", "value": "参数值2"}},
                ...
            ],
            "selling_points": [
                "卖点1",
                "卖点2",
                ...
            ],
            "technical_specs": [
                {{"name": "指标名称1", "value": "指标值1"}},
                {{"name": "指标名称2", "value": "指标值2"}},
                ...
            ]
        }}

        文档内容：
        {content}
        """


# 工厂函数，用于创建模型服务实例
def create_model_service(service_type: str = "qianfan", **kwargs) -> ModelService:
    """
    创建模型服务实例
    :param service_type: 服务类型，支持"qianfan"和"ollama"
    :param kwargs: 其他参数，将传递给相应的模型服务构造函数
    :return: 模型服务实例
    """
    if service_type.lower() == "qianfan":
        return QianfanModelService(**kwargs)
    elif service_type.lower() == "ollama":
        return OllamaModelService(**kwargs)
    else:
        raise ValueError(f"不支持的服务类型: {service_type}")
