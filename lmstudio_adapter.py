"""
LMStudio 适配器
LMStudio adapter for LLMGomoku, providing Gemini-compatible interface
"""

import json
import logging
from typing import Dict, Any, List, Optional
from lmstudio_client import LMStudioClient

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LMStudioAdapter:
    """LMStudio适配器，提供与Gemini API兼容的接口"""

    def __init__(self, base_url: str = "http://localhost:1234/v1"):
        self.client = LMStudioClient(base_url)
        self.chat_session = None

    def start_chat(self, model: str, system_prompt: str = "", generation_config: Optional[Dict] = None):
        """启动聊天会话，返回兼容的ChatSession对象"""
        return self.ChatSession(self.client, model, system_prompt, generation_config)

    class ChatSession:
        """兼容Gemini API的ChatSession类"""

        def __init__(self, client: LMStudioClient, model: str, system_prompt: str = "", generation_config: Optional[Dict] = None):
            self.client = client
            self.model = model
            self.system_prompt = system_prompt
            self.generation_config = generation_config or {}
            self._history: List[Dict[str, Any]] = []
            
            # 如果有系统提示词，添加到历史记录
            if system_prompt:
                self._history.append({
                    "role": "system",
                    "content": system_prompt
                })

        @property
        def history(self) -> List[Dict[str, Any]]:
            """返回对话历史"""
            return self._history

        def send(self, text: str, **kwargs) -> Dict[str, Any]:
            """发送消息，返回Gemini格式的响应"""
            try:
                # 添加用户消息到历史
                self._history.append({
                    "role": "user",
                    "content": text
                })

                # 准备LMStudio格式的消息
                messages = self._convert_history_to_lmstudio_format()

                # 合并生成配置
                gen_config = {**self.generation_config}
                if "generation_config" in kwargs:
                    gen_config.update(kwargs["generation_config"])

                # 转换参数名称
                lmstudio_params = self._convert_generation_config(gen_config)

                # 调用LMStudio API
                response_text = self.client.chat_multi(
                    messages, 
                    model=self.model,
                    **lmstudio_params
                )

                # 添加AI响应到历史
                self._history.append({
                    "role": "assistant",
                    "content": response_text
                })

                # 转换为Gemini格式的响应
                return self._convert_to_gemini_response(response_text)

            except Exception as e:
                logger.error(f"Error in LMStudio chat: {e}")
                # 返回错误响应，保持Gemini格式
                return {
                    "candidates": [{
                        "content": {
                            "parts": [{"text": f"[Error: {str(e)}]"}]
                        },
                        "finishReason": "ERROR"
                    }]
                }

        def send_json(self, text: str, schema: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
            """发送消息并强制JSON响应，返回Gemini格式的响应"""
            try:
                # 添加用户消息到历史
                self._history.append({
                    "role": "user",
                    "content": text
                })

                # 准备LMStudio格式的消息
                messages = self._convert_history_to_lmstudio_format()

                # 合并生成配置
                gen_config = {**self.generation_config}
                if "generation_config" in kwargs:
                    gen_config.update(kwargs["generation_config"])

                # 转换参数名称
                lmstudio_params = self._convert_generation_config(gen_config)

                # 调用LMStudio JSON API
                response_data = self.client.chat_multi_json(
                    messages,
                    model=self.model,
                    **lmstudio_params
                )

                # 将JSON响应转换为文本
                response_text = json.dumps(response_data, ensure_ascii=False)

                # 添加AI响应到历史
                self._history.append({
                    "role": "assistant",
                    "content": response_text
                })

                # 转换为Gemini格式的响应
                return self._convert_to_gemini_response(response_text)

            except Exception as e:
                logger.error(f"Error in LMStudio JSON chat: {e}")
                # 返回错误响应，保持Gemini格式
                return {
                    "candidates": [{
                        "content": {
                            "parts": [{"text": f"[Error: {str(e)}]"}]
                        },
                        "finishReason": "ERROR"
                    }]
                }

        def _convert_history_to_lmstudio_format(self) -> List[Dict[str, Any]]:
            """将历史记录转换为LMStudio格式"""
            messages = []
            for msg in self._history:
                role = msg["role"]
                content = msg["content"]
                
                # LMStudio使用不同的角色名称
                if role == "model":
                    role = "assistant"
                
                messages.append({
                    "role": role,
                    "content": content
                })
            
            return messages

        def _convert_generation_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
            """转换生成配置参数名称"""
            converted = {}
            
            # 参数名称映射
            param_mapping = {
                "maxOutputTokens": "max_tokens",
                "temperature": "temperature",
                "topP": "top_p",
                "topK": "top_k"
            }
            
            for gemini_param, lmstudio_param in param_mapping.items():
                if gemini_param in config:
                    converted[lmstudio_param] = config[gemini_param]
            
            return converted

        def _convert_to_gemini_response(self, response_text: str) -> Dict[str, Any]:
            """将LMStudio响应转换为Gemini格式"""
            return {
                "candidates": [{
                    "content": {
                        "parts": [{"text": response_text}]
                    },
                    "finishReason": "STOP"
                }]
            }
