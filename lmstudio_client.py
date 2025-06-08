import requests
import json
import base64
import os
from typing import List, Dict, Any, Iterator, Optional

class LMStudioClient:
    """
    一个用于与 LM Studio 本地推理服务器进行交互的 Python 客户端工具类。
    该类不依赖官方的 openai 库，而是直接通过 requests 构造 HTTP 请求。
    """

    # --- 可配置参数 ---
    DEFAULT_MODEL = "deepseek-r1-0528-qwen3-8b"
    # 备注一个推荐的多模态模型: qwen2.5-vl-3b-instruct
    VISION_MODEL = "qwen2.5-vl-3b-instruct" 
    
    def __init__(self, base_url: str = "http://localhost:1234/v1"):
        """
        初始化客户端。

        :param base_url: LM Studio API 的基础 URL。
                         通常是 'http://<你的IP地址>:1234/v1'。
        """
        self.base_url = base_url
        self.chat_endpoint = f"{self.base_url}/chat/completions"

    def _encode_image_to_base64(self, image_path: str) -> str:
        """
        将本地图片文件编码为 Base64 字符串。

        :param image_path: 图片文件的路径。
        :return: Base64 编码后的字符串。
        :raises FileNotFoundError: 如果图片路径不存在。
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件未找到: {image_path}")
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def _post_request(self, payload: Dict[str, Any]) -> requests.Response:
        """
        发送 POST 请求到 LM Studio API。

        :param payload: 请求体。
        :return: requests 的响应对象。
        :raises requests.exceptions.RequestException: 如果发生网络错误。
        """
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(self.chat_endpoint, headers=headers, data=json.dumps(payload), stream=payload.get("stream", False))
            response.raise_for_status()  # 如果状态码是 4xx 或 5xx，则抛出异常
            return response
        except requests.exceptions.RequestException as e:
            print(f"请求 API 时发生错误: {e}")
            # 尝试解析错误响应体
            try:
                error_details = e.response.json()
                print(f"API 返回的错误详情: {error_details}")
            except (ValueError, AttributeError):
                pass
            raise

    # --- 核心对话方法 ---

    def chat_single(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """
        进行单轮对话。

        :param prompt: 用户的输入文本。
        :param model: 要使用的模型名称。如果为 None，则使用类默认模型。
        :param kwargs: 其他传递给 API 的参数 (例如 temperature, max_tokens)。
        :return: 模型的回复文本。
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat_multi(messages, model, **kwargs)

    def chat_multi(self, messages: List[Dict[str, Any]], model: Optional[str] = None, **kwargs) -> str:
        """
        进行多轮对话。

        :param messages: 对话历史列表，遵循 OpenAI 格式。
        :param model: 要使用的模型名称。如果为 None，则使用类默认模型。
        :param kwargs: 其他传递给 API 的参数 (例如 temperature, max_tokens)。
        :return: 模型的回复文本。
        """
        payload = {
            "model": model or self.DEFAULT_MODEL,
            "messages": messages,
            **kwargs
        }
        response = self._post_request(payload)
        response_data = response.json()
        return response_data['choices'][0]['message']['content']

    def chat_stream(self, messages: List[Dict[str, Any]], model: Optional[str] = None, **kwargs) -> Iterator[str]:
        """
        以流式方式进行多轮对话。

        :param messages: 对话历史列表。
        :param model: 要使用的模型名称。如果为 None，则使用类默认模型。
        :param kwargs: 其他传递给 API 的参数。
        :return: 一个迭代器，逐块产生模型的回复文本。
        """
        payload = {
            "model": model or self.DEFAULT_MODEL,
            "messages": messages,
            "stream": True,
            **kwargs
        }
        response = self._post_request(payload)
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    json_str = decoded_line[6:]
                    if json_str.strip() == '[DONE]':
                        break
                    try:
                        data = json.loads(json_str)
                        if 'choices' in data and data['choices']:
                            delta = data['choices'][0].get('delta', {})
                            content_chunk = delta.get('content')
                            if content_chunk:
                                yield content_chunk
                    except json.JSONDecodeError:
                        print(f"无法解析的流数据: {json_str}")

    # --- 强制 JSON 输出方法 ---

    def chat_single_json(self, prompt: str, model: Optional[str] = None, **kwargs) -> Dict:
        """
        进行单轮对话，并强制模型输出 JSON 格式。

        :param prompt: 用户的输入文本。
        :param model: 要使用的模型名称。如果为 None，则使用类默认模型。
        :param kwargs: 其他传递给 API 的参数。
        :return: 模型回复的已解析的 JSON 对象 (字典或列表)。
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat_multi_json(messages, model, **kwargs)

    def chat_multi_json(self, messages: List[Dict[str, Any]], model: Optional[str] = None, **kwargs) -> Dict:
        """
        进行多轮对话，并强制模型输出 JSON 格式。

        :param messages: 对话历史列表。
        :param model: 要使用的模型名称。如果为 None，则使用类默认模型。
        :param kwargs: 其他传递给 API 的参数。
        :return: 模型回复的已解析的 JSON 对象 (字典或列表)。
        """
        kwargs['response_format'] = {"type": "json_schema", "json_schema": {"name": "response", "schema": {"type": "object"}}}
        response_text = self.chat_multi(messages, model, **kwargs)

        print(f"[DEBUG] LMStudio raw response length: {len(response_text)}")
        if len(response_text) > 2000:
            print(f"[DEBUG] LMStudio raw response preview: {response_text[:1000]}...{response_text[-1000:]}")
        else:
            print(f"[DEBUG] LMStudio raw response: {response_text}")

        # 清理和提取JSON
        cleaned_json = self._extract_and_clean_json(response_text)
        if cleaned_json:
            return cleaned_json

        # 如果清理失败，尝试直接解析
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            print("模型返回的不是一个有效的 JSON 字符串:")
            print(f"JSON解析错误: {e}")
            print(f"响应文本: {response_text}")
            raise

    def _extract_and_clean_json(self, text: str) -> Optional[Dict]:
        """从响应文本中提取和清理JSON"""
        try:
            # 移除可能的markdown格式
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            # 查找JSON对象的开始和结束
            start_idx = text.find('{')
            if start_idx == -1:
                return None

            # 从后往前找最后一个完整的}
            brace_count = 0
            end_idx = -1
            for i in range(start_idx, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i
                        break

            if end_idx == -1:
                print("[DEBUG] Could not find complete JSON object")
                return None

            json_text = text[start_idx:end_idx + 1]
            print(f"[DEBUG] Extracted JSON: {json_text}")

            return json.loads(json_text)

        except Exception as e:
            print(f"[DEBUG] Error extracting JSON: {e}")
            return None

    # --- 多模态方法 ---

    def chat_vision(self, prompt: str, image_path: str, model: Optional[str] = None, **kwargs) -> str:
        """
        进行包含单个图片的多模态对话。

        :param prompt: 用户的输入文本。
        :param image_path: 本地图片的路径。
        :param model: 要使用的多模态模型名称。如果为 None，则使用类默认的 VISION_MODEL。
        :param kwargs: 其他传递给 API 的参数 (例如 max_tokens)。
        :return: 模型的回复文本。
        """
        base64_image = self._encode_image_to_base64(image_path)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
        
        # 多模态模型通常需要指定，否则可能出错
        vision_model = model or self.VISION_MODEL
        if not vision_model:
            raise ValueError("必须为多模态对话指定一个模型 (model) 或设置一个默认的 VISION_MODEL。")
            
        return self.chat_multi(messages, vision_model, **kwargs)

    def chat_vision_json(self, prompt: str, image_path: str, model: Optional[str] = None, **kwargs) -> Dict:
        """
        进行多模态对话，并强制模型输出 JSON 格式。

        :param prompt: 用户的输入文本。
        :param image_path: 本地图片的路径。
        :param model: 要使用的多模态模型名称。如果为 None，则使用类默认的 VISION_MODEL。
        :param kwargs: 其他传递给 API 的参数。
        :return: 模型回复的已解析的 JSON 对象 (字典或列表)。
        """
        kwargs['response_format'] = {"type": "json_schema", "json_schema": {"name": "response", "schema": {"type": "object"}}}
        # chat_vision 内部会处理消息格式和模型选择
        response_text = self.chat_vision(prompt, image_path, model, **kwargs)
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            print("模型返回的不是一个有效的 JSON 字符串:")
            print(response_text)
            raise

# --- 使用示例 ---
if __name__ == '__main__':
    # 在运行此脚本前，请确保 LM Studio 正在运行并已加载相应的模型。
    
    # 创建一个图片用于测试多模态功能
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (400, 100), color = (73, 109, 137))
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 30)
        except IOError:
            font = ImageFont.load_default()
        d.text((10,10), "Hello, LM Studio!", fill=(255,255,0), font=font)
        test_image_path = "test_image.jpg"
        img.save(test_image_path)
        print(f"已创建测试图片: {test_image_path}")
        image_created = True
    except ImportError:
        print("未安装 Pillow 库 (pip install Pillow)，将跳过多模态测试。")
        test_image_path = ""
        image_created = False
        
    client = LMStudioClient()

    try:
        # --- 1. 单轮对话测试 ---
        print("\n--- 1. 单轮对话 ---")
        prompt = "你好，请用中文介绍一下你自己。"
        response = client.chat_single(prompt, temperature=0.7)
        print(f"模型回复:\n{response}")

        # --- 2. 多轮对话测试 ---
        print("\n--- 2. 多轮对话 ---")
        messages = [
            {"role": "system", "content": "你是一个乐于助人的AI助手。"},
            {"role": "user", "content": "世界上最高的山峰是哪座？"},
            {"role": "assistant", "content": "世界上最高的山峰是珠穆朗玛峰。"},
            {"role": "user", "content": "它有多高？"}
        ]
        response = client.chat_multi(messages)
        print(f"模型回复:\n{response}")
        
        # --- 3. 流式对话测试 ---
        print("\n--- 3. 流式对话 ---")
        stream_messages = [{"role": "user", "content": "请写一首关于宇宙的五行短诗。"}]
        print("模型流式回复:")
        full_stream_response = ""
        for chunk in client.chat_stream(stream_messages):
            print(chunk, end='', flush=True)
            full_stream_response += chunk
        print("\n流式传输结束。")

        # --- 4. 强制 JSON 输出测试 ---
        print("\n--- 4. 强制 JSON 输出 ---")
        json_prompt = "请提供一个关于苹果公司的JSON对象，包含名称(name)，股票代码(ticker)和创始人列表(founders)。"
        json_response = client.chat_single_json(json_prompt)
        print(f"模型返回的 JSON 对象: {json_response}")
        print(f"类型: {type(json_response)}")
        print(f"股票代码: {json_response.get('ticker')}")

        if image_created:
            # --- 5. 多模态对话测试 ---
            print("\n--- 5. 多模态对话 (Vision) ---")
            print(f"使用的多模态模型: {client.VISION_MODEL}")
            print("注意：请确保你已在 LM Studio 中加载了此模型！")
            try:
                vision_prompt = "这张图片里写了什么文字？"
                vision_response = client.chat_vision(vision_prompt, test_image_path)
                print(f"模型对图片的描述:\n{vision_response}")
            except Exception as e:
                print(f"多模态测试失败，可能是因为模型 '{client.VISION_MODEL}' 未加载。错误: {e}")
            
            # --- 6. 多模态强制 JSON 输出测试 ---
            print("\n--- 6. 多模态强制 JSON 输出 ---")
            try:
                vision_json_prompt = "请分析图片中的内容，并以JSON格式返回。JSON应包含一个'text'字段，其值为图片中的文字。"
                vision_json_response = client.chat_vision_json(vision_json_prompt, test_image_path)
                print(f"模型返回的 JSON 对象: {vision_json_response}")
                print(f"识别出的文字: {vision_json_response.get('text')}")
            except Exception as e:
                 print(f"多模态JSON测试失败，可能是因为模型 '{client.VISION_MODEL}' 未加载或不支持JSON模式。错误: {e}")

    except requests.exceptions.RequestException as e:
        print("\n\n测试中断：无法连接到 LM Studio 服务器。")
        print("请确保 LM Studio 正在运行，并且服务器已开启。")
    except Exception as e:
        print(f"\n\n测试过程中发生意外错误: {e}")