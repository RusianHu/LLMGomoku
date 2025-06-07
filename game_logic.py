"""
五子棋游戏逻辑
Gomoku game logic
"""

from typing import List, Tuple, Optional, Dict, Any
import json
import copy
from config import BOARD_SIZE, WIN_LENGTH, PLAYER_SYMBOL, AI_SYMBOL, EMPTY_SYMBOL


class GomokuGame:
    """五子棋游戏类"""
    
    def __init__(self):
        self.board = [[EMPTY_SYMBOL for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.current_player = PLAYER_SYMBOL  # 玩家先手
        self.game_over = False
        self.winner = None
        self.move_history = []
    
    def reset_game(self):
        """重置游戏"""
        self.board = [[EMPTY_SYMBOL for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.current_player = PLAYER_SYMBOL
        self.game_over = False
        self.winner = None
        self.move_history = []
    
    def is_valid_move(self, row: int, col: int) -> bool:
        """检查移动是否有效"""
        if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
            return False
        return self.board[row][col] == EMPTY_SYMBOL
    
    def make_move(self, row: int, col: int, player: int) -> bool:
        """执行移动"""
        if not self.is_valid_move(row, col) or self.game_over:
            return False
        
        self.board[row][col] = player
        self.move_history.append({"row": row, "col": col, "player": player})
        
        # 检查是否获胜
        if self.check_winner(row, col, player):
            self.game_over = True
            self.winner = player
        elif self.is_board_full():
            self.game_over = True
            self.winner = 0  # 平局
        else:
            # 切换玩家
            self.current_player = AI_SYMBOL if player == PLAYER_SYMBOL else PLAYER_SYMBOL
        
        return True
    
    def check_winner(self, row: int, col: int, player: int) -> bool:
        """检查是否有玩家获胜"""
        directions = [
            (0, 1),   # 水平
            (1, 0),   # 垂直
            (1, 1),   # 主对角线
            (1, -1)   # 副对角线
        ]
        
        for dr, dc in directions:
            count = 1  # 包含当前棋子
            
            # 向一个方向检查
            r, c = row + dr, col + dc
            while (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and 
                   self.board[r][c] == player):
                count += 1
                r, c = r + dr, c + dc
            
            # 向相反方向检查
            r, c = row - dr, col - dc
            while (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and 
                   self.board[r][c] == player):
                count += 1
                r, c = r - dr, c - dc
            
            if count >= WIN_LENGTH:
                return True
        
        return False
    
    def is_board_full(self) -> bool:
        """检查棋盘是否已满"""
        for row in self.board:
            if EMPTY_SYMBOL in row:
                return False
        return True
    
    def get_empty_positions(self) -> List[Tuple[int, int]]:
        """获取所有空位置"""
        positions = []
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if self.board[i][j] == EMPTY_SYMBOL:
                    positions.append((i, j))
        return positions
    
    def to_json(self) -> Dict[str, Any]:
        """将游戏状态转换为JSON格式"""
        return {
            "board": self.board,
            "current_player": self.current_player,
            "game_over": self.game_over,
            "winner": self.winner,
            "move_history": self.move_history,
            "board_size": BOARD_SIZE
        }
    
    def from_json(self, data: Dict[str, Any]):
        """从JSON格式恢复游戏状态"""
        self.board = data["board"]
        self.current_player = data["current_player"]
        self.game_over = data["game_over"]
        self.winner = data["winner"]
        self.move_history = data["move_history"]
    
    def get_board_string(self) -> str:
        """获取棋盘的字符串表示，用于LLM理解"""
        board_str = "当前棋盘状态 (0=空位, 1=玩家, 2=AI):\n"
        board_str += "   " + " ".join([f"{i:2d}" for i in range(BOARD_SIZE)]) + "\n"
        
        for i, row in enumerate(self.board):
            board_str += f"{i:2d} " + " ".join([f"{cell:2d}" for cell in row]) + "\n"
        
        return board_str
    
    def clone(self) -> 'GomokuGame':
        """创建游戏状态的副本"""
        new_game = GomokuGame()
        new_game.board = copy.deepcopy(self.board)
        new_game.current_player = self.current_player
        new_game.game_over = self.game_over
        new_game.winner = self.winner
        new_game.move_history = copy.deepcopy(self.move_history)
        return new_game
