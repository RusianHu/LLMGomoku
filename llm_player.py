"""
LLM 玩家逻辑
LLM player logic using Gemini API
"""

import json
import logging
from typing import Dict, Any, Tuple, Optional
from gemini_api import GeminiAPI
from game_logic import GomokuGame
from config import (
    GEMINI_API_KEY, GEMINI_MODEL, SYSTEM_PROMPT,
    LLM_RESPONSE_SCHEMA, MAX_CONVERSATION_HISTORY, MAX_OUTPUT_TOKENS,
    AI_SYMBOL, PLAYER_SYMBOL, BOARD_SIZE
)

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMPlayer:
    """LLM 驱动的五子棋玩家"""
    
    def __init__(self):
        self.gemini = GeminiAPI(GEMINI_API_KEY)
        self.chat_session = None
        self.conversation_count = 0
        self._init_chat_session()
    
    def _init_chat_session(self):
        """初始化聊天会话"""
        generation_config = {
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
            "temperature": 0.7,
            "topP": 0.8,
            "topK": 40
        }
        
        self.chat_session = self.gemini.start_chat(
            model=GEMINI_MODEL,
            system_prompt=SYSTEM_PROMPT,
            generation_config=generation_config
        )
        self.conversation_count = 0
        logger.info("LLM chat session initialized")
    
    def _manage_conversation_history(self):
        """管理对话历史，保持在限制范围内"""
        if self.conversation_count >= MAX_CONVERSATION_HISTORY * 2:  # *2 因为每轮包含用户和AI消息
            # 重新初始化会话，但保留系统提示
            logger.info("Conversation history limit reached, reinitializing session")
            self._init_chat_session()
    
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
            
            # 调用LLM获取JSON响应
            response = self.gemini.single_turn_json(
                model=GEMINI_MODEL,
                text=prompt,
                schema=LLM_RESPONSE_SCHEMA,
                generation_config={
                    "maxOutputTokens": MAX_OUTPUT_TOKENS,
                    "temperature": 0.7
                }
            )
            
            # 解析响应
            move_data = self._parse_response(response)
            if move_data:
                row, col, reasoning = move_data
                
                # 验证移动的有效性
                if game.is_valid_move(row, col):
                    self.conversation_count += 1
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
