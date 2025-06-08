"""
LLMGomoku FastAPI 主应用
Main FastAPI application for LLMGomoku
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import logging
import os
import sys
from typing import Dict, Any

# 检查配置文件是否存在
if not os.path.exists("config.py"):
    if os.path.exists("config.py.env"):
        print("错误: 配置文件 config.py 不存在。")
        print("请将 config.py.env 重命名为 config.py, 并填写必要的配置信息 (例如 GEMINI_API_KEY)。")
        sys.exit(1)
    else:
        print("错误: 找不到配置文件 config.py 或模板文件 config.py.env。")
        sys.exit(1)

from game_logic import GomokuGame
from llm_player import LLMPlayer
from config import HOST, PORT, DEBUG, PLAYER_SYMBOL, AI_SYMBOL, DEBUG_MODE

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(title="LLMGomoku", description="LLM驱动的五子棋游戏", version="1.0.0")

# 全局游戏状态
game = GomokuGame()
llm_player = LLMPlayer()

# 创建static目录（如果不存在）
if not os.path.exists("static"):
    os.makedirs("static")

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")


class MoveRequest(BaseModel):
    row: int
    col: int


class GameResponse(BaseModel):
    success: bool
    message: str
    game_state: Dict[str, Any]
    ai_move: Dict[str, Any] = None


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """返回主页面"""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <head><title>LLMGomoku</title></head>
            <body>
                <h1>LLMGomoku</h1>
                <p>游戏界面正在加载中...</p>
                <p>请确保static/index.html文件存在。</p>
            </body>
        </html>
        """)


@app.get("/api/game/state")
async def get_game_state():
    """获取当前游戏状态"""
    game_state = game.to_json()
    # 添加回合数统计
    game_state["round_number"] = len(game.move_history) // 2 + 1
    # 添加AI最新落子信息
    game_state["last_ai_move"] = llm_player.last_ai_move
    return JSONResponse(content=game_state)


@app.post("/api/game/reset")
async def reset_game():
    """重置游戏"""
    global game, llm_player
    game.reset_game()
    # 重新初始化LLM玩家以清除对话历史和Token统计
    llm_player = LLMPlayer()
    logger.info("Game reset - Token usage statistics cleared")
    return JSONResponse(content={
        "success": True,
        "message": "游戏已重置",
        "game_state": game.to_json()
    })


@app.post("/api/game/move", response_model=GameResponse)
async def make_move(move_request: MoveRequest):
    """玩家下棋"""
    try:
        row, col = move_request.row, move_request.col
        
        # 检查游戏是否结束
        if game.game_over:
            raise HTTPException(status_code=400, detail="游戏已结束")
        
        # 检查是否轮到玩家
        if game.current_player != PLAYER_SYMBOL:
            raise HTTPException(status_code=400, detail="现在不是你的回合")
        
        # 执行玩家移动
        if not game.make_move(row, col, PLAYER_SYMBOL):
            raise HTTPException(status_code=400, detail="无效的移动")
        
        logger.info(f"Player move: ({row}, {col})")
        
        # 检查游戏是否结束
        if game.game_over:
            winner_text = "玩家获胜！" if game.winner == PLAYER_SYMBOL else "平局！"
            return GameResponse(
                success=True,
                message=f"游戏结束 - {winner_text}",
                game_state=game.to_json()
            )
        
        # AI回合
        ai_row, ai_col, ai_reasoning = llm_player.get_move(game)
        
        if ai_row is None or ai_col is None:
            raise HTTPException(status_code=500, detail="AI无法选择移动")
        
        # 执行AI移动
        if not game.make_move(ai_row, ai_col, AI_SYMBOL):
            raise HTTPException(status_code=500, detail="AI选择了无效的移动")
        
        logger.info(f"AI move: ({ai_row}, {ai_col}) - {ai_reasoning}")
        
        # 检查游戏是否结束
        if game.game_over:
            winner_text = "AI获胜！" if game.winner == AI_SYMBOL else "平局！"
            message = f"游戏结束 - {winner_text}"
        else:
            message = "移动成功，轮到你了"
        
        return GameResponse(
            success=True,
            message=message,
            game_state=game.to_json(),
            ai_move={
                "row": ai_row,
                "col": ai_col,
                "reasoning": ai_reasoning
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in make_move: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


@app.get("/api/game/ai-move")
async def get_ai_move():
    """获取AI的下一步移动（仅用于测试）"""
    try:
        if game.game_over:
            raise HTTPException(status_code=400, detail="游戏已结束")
        
        if game.current_player != AI_SYMBOL:
            raise HTTPException(status_code=400, detail="现在不是AI的回合")
        
        ai_row, ai_col, ai_reasoning = llm_player.get_move(game)
        
        return JSONResponse(content={
            "row": ai_row,
            "col": ai_col,
            "reasoning": ai_reasoning,
            "valid": game.is_valid_move(ai_row, ai_col) if ai_row is not None else False
        })
        
    except Exception as e:
        logger.error(f"Error getting AI move: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


@app.get("/api/game/context")
async def get_context_info():
    """获取LLM上下文信息"""
    try:
        context_info = llm_player.get_context_info()
        return JSONResponse(content=context_info)
    except Exception as e:
        logger.error(f"Error getting context info: {e}")
        raise HTTPException(status_code=500, detail=f"获取上下文信息失败: {str(e)}")


@app.get("/api/game/debug")
async def get_debug_info():
    """获取调试信息"""
    try:
        if not DEBUG_MODE:
            raise HTTPException(status_code=404, detail="调试模式未启用")

        debug_info = llm_player.get_debug_info()
        return JSONResponse(content=debug_info)
    except Exception as e:
        logger.error(f"Error getting debug info: {e}")
        raise HTTPException(status_code=500, detail=f"获取调试信息失败: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {str(exc)}"}
    )


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting LLMGomoku server on {HOST}:{PORT}")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=DEBUG)
