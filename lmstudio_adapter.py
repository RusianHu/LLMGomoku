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

            # Token usage tracking
            self._total_input_tokens = 0
            self._total_output_tokens = 0

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

        def _estimate_token_usage(self, input_text: str, output_text: str) -> None:
            """估算Token使用量（LMStudio可能不返回准确数据）"""
            # 简单估算：中文字符按1个token，英文单词按0.75个token计算
            def count_tokens(text: str) -> int:
                chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
                other_chars = len(text) - chinese_chars
                return chinese_chars + int(other_chars * 0.75)

            input_tokens = count_tokens(input_text)
            output_tokens = count_tokens(output_text)

            self._total_input_tokens += input_tokens
            self._total_output_tokens += output_tokens

        def get_token_usage(self) -> dict:
            """获取总Token使用量"""
            return {
                "total_input_tokens": self._total_input_tokens,
                "total_output_tokens": self._total_output_tokens,
                "total_tokens": self._total_input_tokens + self._total_output_tokens
            }

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

                # 估算Token使用量
                self._estimate_token_usage(text, response_text)

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

                # 记录原始响应数据用于调试
                logger.info(f"LMStudio JSON response type: {type(response_data)}")
                logger.info(f"LMStudio JSON response keys: {response_data.keys() if isinstance(response_data, dict) else 'Not a dict'}")

                # 验证和清理JSON响应
                cleaned_response = self._validate_and_clean_json_response(response_data)
                if not cleaned_response:
                    logger.error("Failed to validate JSON response, using fallback")
                    raise ValueError("Invalid JSON response from LMStudio")

                # 将清理后的JSON响应转换为文本
                response_text = json.dumps(cleaned_response, ensure_ascii=False)

                # 记录响应长度
                logger.info(f"LMStudio cleaned JSON response length: {len(response_text)} characters")
                if len(response_text) > 1000:
                    logger.info(f"LMStudio cleaned JSON response preview: {response_text[:500]}...{response_text[-500:]}")
                else:
                    logger.info(f"LMStudio cleaned JSON response: {response_text}")

                # 估算Token使用量
                self._estimate_token_usage(text, response_text)

                # 添加AI响应到历史
                self._history.append({
                    "role": "assistant",
                    "content": response_text
                })

                # 转换为Gemini格式的响应
                return self._convert_to_gemini_response(response_text)

            except Exception as e:
                logger.error(f"Error in LMStudio JSON chat: {e}")
                logger.error(f"Exception type: {type(e)}")
                logger.error(f"Exception details: {str(e)}")
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

        def _validate_and_clean_json_response(self, response_data: Any) -> Optional[Dict[str, Any]]:
            """验证和清理JSON响应，确保符合五子棋游戏的要求"""
            try:
                # 如果响应不是字典，尝试解析
                if not isinstance(response_data, dict):
                    logger.warning(f"Response is not a dict, type: {type(response_data)}")
                    return None

                # 检查必需的字段
                required_fields = ["analysis", "move", "reasoning"]
                for field in required_fields:
                    if field not in response_data:
                        logger.error(f"Missing required field: {field}")
                        return None

                # 验证move字段
                move = response_data.get("move")
                if not isinstance(move, dict):
                    logger.error(f"Move field is not a dict: {move}")
                    return None

                if "row" not in move or "col" not in move:
                    logger.error(f"Move missing row or col: {move}")
                    return None

                try:
                    row = int(move["row"])
                    col = int(move["col"])
                except (ValueError, TypeError):
                    logger.error(f"Invalid row/col values: {move}")
                    return None

                # 验证坐标范围
                if not (0 <= row <= 14 and 0 <= col <= 14):
                    logger.error(f"Row/col out of range: row={row}, col={col}")
                    return None

                # 构建清理后的响应
                cleaned_response = {
                    "analysis": str(response_data.get("analysis", "")),
                    "move": {
                        "row": row,
                        "col": col
                    },
                    "reasoning": str(response_data.get("reasoning", ""))
                }

                logger.info(f"JSON response validated successfully: move=({row}, {col})")
                return cleaned_response

            except Exception as e:
                logger.error(f"Error validating JSON response: {e}")
                return None

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
