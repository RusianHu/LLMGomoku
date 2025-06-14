"""
LLM 玩家逻辑
LLM player logic supporting multiple providers (Gemini and LMStudio)
"""

import json
import logging
import time
from typing import Dict, Any, Tuple, Optional
from gemini_api import GeminiAPI
from lmstudio_adapter import LMStudioAdapter
from game_logic import GomokuGame
from config import (
    LLM_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL,
    LMSTUDIO_BASE_URL, LMSTUDIO_MODEL, SYSTEM_PROMPT,
    LLM_RESPONSE_SCHEMA, MAX_CONVERSATION_HISTORY, MAX_OUTPUT_TOKENS,
    AI_SYMBOL, PLAYER_SYMBOL, BOARD_SIZE, DEBUG_MODE
)

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMPlayer:
    """LLM 驱动的五子棋玩家，支持多种LLM提供商"""

    def __init__(self):
        self.provider = LLM_PROVIDER.lower()
        self.llm_client = None
        self.chat_session = None
        self.conversation_count = 0
        self.last_ai_move = None  # 记录AI最新落子位置

        # 累计Token使用量统计（本局游戏总消耗）
        self.total_game_tokens = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }
        # 记录上次累计的会话Token数量，避免重复计算
        self._last_session_tokens = {
            "input_tokens": 0,
            "output_tokens": 0
        }

        # 调试信息记录
        self.debug_info = {
            "last_request": None,
            "last_response": None,
            "last_request_time": 0,
            "request_history": []  # 保存最近的几次请求响应记录
        }

        self._init_llm_client()
        self._init_chat_session()

    def _init_llm_client(self):
        """初始化LLM客户端"""
        if self.provider == "gemini":
            self.llm_client = GeminiAPI(GEMINI_API_KEY)
            self.model = GEMINI_MODEL
            logger.info("Initialized Gemini API client")
        elif self.provider == "lmstudio":
            self.llm_client = LMStudioAdapter(LMSTUDIO_BASE_URL)
            self.model = LMSTUDIO_MODEL
            logger.info(f"Initialized LMStudio client with base URL: {LMSTUDIO_BASE_URL}")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

        logger.info(f"Using LLM provider: {self.provider}, model: {self.model}")
    
    def _init_chat_session(self):
        """初始化聊天会话"""
        generation_config = {
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
            "temperature": 0.7,
            "topP": 0.8,
            "topK": 40
        }

        self.chat_session = self.llm_client.start_chat(
            model=self.model,
            system_prompt=SYSTEM_PROMPT,
            generation_config=generation_config
        )
        self.conversation_count = 0
        self.last_ai_move = None  # 重置最新落子记录
        # 重置会话Token记录
        self._last_session_tokens = {
            "input_tokens": 0,
            "output_tokens": 0
        }
        logger.info(f"LLM chat session initialized with {self.provider}")
    
    def _manage_conversation_history(self):
        """管理对话历史，保持在限制范围内"""
        if self.conversation_count >= MAX_CONVERSATION_HISTORY * 2:  # *2 因为每轮包含用户和AI消息
            # 在重新初始化前累计Token使用量
            self._accumulate_token_usage()
            # 重新初始化会话，但保留系统提示
            logger.info("Conversation history limit reached, reinitializing session")
            self._init_chat_session()

    def _accumulate_token_usage(self):
        """累计当前会话的Token使用量到游戏总计中"""
        if self.chat_session and hasattr(self.chat_session, 'get_token_usage'):
            session_usage = self.chat_session.get_token_usage()

            # 获取当前会话的总Token使用量
            session_input_tokens = session_usage.get("total_input_tokens", 0)
            session_output_tokens = session_usage.get("total_output_tokens", 0)

            # 计算新增的Token使用量（当前会话总量 - 上次记录的量）
            new_input_tokens = session_input_tokens - self._last_session_tokens["input_tokens"]
            new_output_tokens = session_output_tokens - self._last_session_tokens["output_tokens"]

            # 累计到游戏总计中
            self.total_game_tokens["input_tokens"] += new_input_tokens
            self.total_game_tokens["output_tokens"] += new_output_tokens
            self.total_game_tokens["total_tokens"] = (
                self.total_game_tokens["input_tokens"] +
                self.total_game_tokens["output_tokens"]
            )

            # 更新上次记录的会话Token数量
            self._last_session_tokens["input_tokens"] = session_input_tokens
            self._last_session_tokens["output_tokens"] = session_output_tokens

            if new_input_tokens > 0 or new_output_tokens > 0:
                logger.info(f"Token usage - New: +{new_input_tokens}(in) +{new_output_tokens}(out), Total: {self.total_game_tokens['total_tokens']}")

    def reset_token_usage(self):
        """重置Token使用量统计（游戏重置时调用）"""
        self.total_game_tokens = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }
        self._last_session_tokens = {
            "input_tokens": 0,
            "output_tokens": 0
        }
        logger.info("Token usage statistics reset")
    
    def get_move(self, game: GomokuGame) -> Tuple[Optional[int], Optional[int], str]:
        """
        获取LLM的下棋决策

        Returns:
            Tuple[row, col, reasoning]: 行号、列号、推理过程
        """
        try:
            # 管理对话历史
            self._manage_conversation_history()

            # 构建提示词
            prompt = self._build_prompt(game)

            # 记录请求开始时间
            start_time = time.time()

            # 记录调试信息 - 请求
            if DEBUG_MODE:
                self.debug_info["last_request"] = {
                    "timestamp": start_time,
                    "prompt": prompt,
                    "schema": LLM_RESPONSE_SCHEMA,
                    "generation_config": {
                        "maxOutputTokens": MAX_OUTPUT_TOKENS,
                        "temperature": 0.7
                    }
                }

            # 使用聊天会话发送消息以保存历史，并强制JSON输出
            response = self.chat_session.send_json(
                prompt,
                schema=LLM_RESPONSE_SCHEMA,
                generation_config={
                    "maxOutputTokens": MAX_OUTPUT_TOKENS,
                    "temperature": 0.7
                }
            )

            # 计算请求时间
            end_time = time.time()
            request_time = end_time - start_time
            self.debug_info["last_request_time"] = request_time

            # 记录调试信息 - 响应
            if DEBUG_MODE:
                self.debug_info["last_response"] = {
                    "timestamp": end_time,
                    "response": response,
                    "request_time": request_time
                }

                # 保存到历史记录（最多保留最近5次）
                debug_record = {
                    "request": self.debug_info["last_request"].copy(),
                    "response": self.debug_info["last_response"].copy()
                }
                self.debug_info["request_history"].append(debug_record)
                if len(self.debug_info["request_history"]) > 5:
                    self.debug_info["request_history"].pop(0)

            # 累计Token使用量
            self._accumulate_token_usage()

            # 解析响应
            move_data = self._parse_response(response)
            if move_data:
                row, col, reasoning = move_data

                # 验证移动的有效性
                if game.is_valid_move(row, col):
                    self.conversation_count += 1
                    self.last_ai_move = (row, col)  # 记录最新落子
                    logger.info(f"LLM chose move: ({row}, {col}) - {reasoning}")
                    return row, col, reasoning
                else:
                    logger.warning(f"LLM chose invalid move: ({row}, {col})")
                    return self._fallback_move(game)
            else:
                logger.error("Failed to parse LLM response")
                return self._fallback_move(game)

        except Exception as e:
            logger.error(f"Error getting LLM move: {e}")
            return self._fallback_move(game)
    
    def _build_prompt(self, game: GomokuGame) -> str:
        """构建发送给LLM的提示词"""
        prompt = f"""请分析以下五子棋局面并选择你的下一步棋：

{game.get_board_string()}

游戏信息：
- 你是AI玩家，使用棋子2
- 对手是人类玩家，使用棋子1
- 当前轮到你下棋
- 目标：连成5子获胜

最近的移动历史：
"""
        
        # 添加最近几步的移动历史
        recent_moves = game.move_history[-6:] if len(game.move_history) > 6 else game.move_history
        for i, move in enumerate(recent_moves):
            player_name = "玩家" if move["player"] == PLAYER_SYMBOL else "AI"
            prompt += f"{i+1}. {player_name} 在 ({move['row']}, {move['col']}) 下棋\n"
        
        prompt += "\n请仔细分析局面，选择最佳位置下棋。记住必须选择空位(值为0)！"
        
        return prompt
    
    def _parse_response(self, response: Dict[str, Any]) -> Optional[Tuple[int, int, str]]:
        """解析LLM的JSON响应"""
        try:
            if "candidates" not in response or not response["candidates"]:
                logger.error("No candidates in response")
                return None

            candidate = response["candidates"][0]
            if "content" not in candidate or "parts" not in candidate["content"]:
                logger.error("No content in candidate")
                return None

            # 获取JSON文本
            json_text = candidate["content"]["parts"][0].get("text", "")
            if not json_text:
                logger.error("No text in response")
                return None

            # 清理JSON文本（移除可能的markdown格式）
            json_text = json_text.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]
            json_text = json_text.strip()

            # 解析JSON
            try:
                data = json.loads(json_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                logger.error(f"JSON text: {json_text}")
                return None

            # 提取移动信息
            if "move" not in data:
                logger.error("No move in response data")
                return None

            move = data["move"]
            row = move.get("row")
            col = move.get("col")
            reasoning = data.get("reasoning", "No reasoning provided")

            if row is None or col is None:
                logger.error("Invalid move coordinates")
                return None

            return int(row), int(col), reasoning

        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return None
    
    def _fallback_move(self, game: GomokuGame) -> Tuple[Optional[int], Optional[int], str]:
        """备用移动策略：选择中心附近的空位"""
        empty_positions = game.get_empty_positions()
        if not empty_positions:
            return None, None, "No valid moves available"
        
        # 优先选择中心附近的位置
        center = BOARD_SIZE // 2
        best_pos = None
        min_distance = float('inf')
        
        for row, col in empty_positions:
            distance = abs(row - center) + abs(col - center)
            if distance < min_distance:
                min_distance = distance
                best_pos = (row, col)
        
        if best_pos:
            return best_pos[0], best_pos[1], "Fallback move: chose position near center"
        else:
            # 如果没有找到合适位置，选择第一个空位
            pos = empty_positions[0]
            return pos[0], pos[1], "Fallback move: chose first available position"

    def get_context_info(self) -> Dict[str, Any]:
        """获取上下文信息，包括token统计"""
        # 在返回信息前累计当前会话的Token使用量
        self._accumulate_token_usage()

        context_info = {
            "llm_provider": self.provider,
            "model": self.model,
            "conversation_count": self.conversation_count,
            "max_conversation_history": MAX_CONVERSATION_HISTORY,
            "total_consumed_tokens": self.total_game_tokens["total_tokens"],
            "input_tokens": self.total_game_tokens["input_tokens"],
            "output_tokens": self.total_game_tokens["output_tokens"],
            "context_history": [],
            "last_ai_move": self.last_ai_move
        }

        if self.chat_session and hasattr(self.chat_session, 'history'):
            history = self.chat_session.history

            # 根据提供商转换历史记录格式，统一为前端可理解的格式
            if self.provider == "gemini":
                # Gemini格式：直接使用
                context_info["context_history"] = history

            elif self.provider == "lmstudio":
                # LMStudio格式：转换为前端兼容格式
                converted_history = []

                for message in history:
                    if "role" in message and "content" in message:
                        # 转换为Gemini兼容格式
                        converted_message = {
                            "role": message["role"],
                            "parts": [{"text": message["content"]}]
                        }
                        converted_history.append(converted_message)

                context_info["context_history"] = converted_history

        return context_info

    def get_debug_info(self) -> Dict[str, Any]:
        """获取调试信息"""
        if not DEBUG_MODE:
            return {"debug_enabled": False}

        return {
            "debug_enabled": True,
            "last_request": self.debug_info.get("last_request"),
            "last_response": self.debug_info.get("last_response"),
            "last_request_time": self.debug_info.get("last_request_time", 0),
            "request_history": self.debug_info.get("request_history", [])
        }


