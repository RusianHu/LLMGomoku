// LLMGomoku 前端 JavaScript

class GomokuUI {
    constructor() {
        this.gameState = null;
        this.isPlayerTurn = true;
        this.isGameOver = false;
        this.boardElement = document.getElementById('gameBoard');
        
        this.initializeElements();
        this.bindEvents();
        this.loadGameState();
    }

    initializeElements() {
        // 获取DOM元素
        this.currentPlayerElement = document.getElementById('currentPlayer');
        this.gameStatusElement = document.getElementById('gameStatus');
        this.aiThinkingElement = document.getElementById('aiThinking');
        this.aiAnalysisElement = document.getElementById('aiAnalysis');
        this.aiMoveElement = document.getElementById('aiMove');
        this.aiReasoningElement = document.getElementById('aiReasoning');
        this.messageToast = document.getElementById('messageToast');
        this.gameOverModal = document.getElementById('gameOverModal');
        this.resetBtn = document.getElementById('resetBtn');
        this.playAgainBtn = document.getElementById('playAgainBtn');
    }

    bindEvents() {
        // 绑定事件
        this.resetBtn.addEventListener('click', () => this.resetGame());
        this.playAgainBtn.addEventListener('click', () => this.resetGame());
        
        // 点击模态框外部关闭
        this.gameOverModal.addEventListener('click', (e) => {
            if (e.target === this.gameOverModal) {
                this.hideGameOverModal();
            }
        });
    }

    async loadGameState() {
        try {
            const response = await fetch('/api/game/state');
            const gameState = await response.json();
            this.updateGameState(gameState);
            this.renderBoard();
        } catch (error) {
            console.error('Failed to load game state:', error);
            this.showMessage('加载游戏状态失败', 'error');
        }
    }

    updateGameState(gameState) {
        this.gameState = gameState;
        this.isPlayerTurn = gameState.current_player === 1;
        this.isGameOver = gameState.game_over;
        
        // 更新UI显示
        this.currentPlayerElement.textContent = this.isPlayerTurn ? '玩家' : 'AI';
        
        if (this.isGameOver) {
            let statusText = '游戏结束';
            if (gameState.winner === 1) {
                statusText = '玩家获胜！';
            } else if (gameState.winner === 2) {
                statusText = 'AI获胜！';
            } else {
                statusText = '平局！';
            }
            this.gameStatusElement.textContent = statusText;
        } else {
            this.gameStatusElement.textContent = '进行中';
        }
    }

    renderBoard() {
        if (!this.gameState) return;
        
        // 清空棋盘
        this.boardElement.innerHTML = '';
        
        // 创建棋盘格子
        for (let row = 0; row < 15; row++) {
            for (let col = 0; col < 15; col++) {
                const cell = document.createElement('div');
                cell.className = 'cell';
                cell.dataset.row = row;
                cell.dataset.col = col;
                
                // 设置棋子状态
                const cellValue = this.gameState.board[row][col];
                if (cellValue === 1) {
                    cell.classList.add('player');
                } else if (cellValue === 2) {
                    cell.classList.add('ai');
                }
                
                // 绑定点击事件
                if (cellValue === 0 && !this.isGameOver && this.isPlayerTurn) {
                    cell.addEventListener('click', () => this.makeMove(row, col));
                }
                
                this.boardElement.appendChild(cell);
            }
        }
    }

    async makeMove(row, col) {
        if (!this.isPlayerTurn || this.isGameOver) return;
        
        try {
            // 显示AI思考状态
            this.showAIThinking();
            
            const response = await fetch('/api/game/move', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ row, col }),
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '移动失败');
            }
            
            const result = await response.json();
            
            // 更新游戏状态
            this.updateGameState(result.game_state);
            this.renderBoard();
            
            // 隐藏AI思考状态
            this.hideAIThinking();
            
            // 显示AI分析
            if (result.ai_move) {
                this.showAIAnalysis(result.ai_move);
            }
            
            // 显示消息
            this.showMessage(result.message, result.success ? 'success' : 'error');
            
            // 检查游戏是否结束
            if (this.isGameOver) {
                setTimeout(() => this.showGameOverModal(), 1000);
            }
            
        } catch (error) {
            console.error('Move failed:', error);
            this.showMessage(error.message, 'error');
            this.hideAIThinking();
        }
    }

    async resetGame() {
        try {
            const response = await fetch('/api/game/reset', {
                method: 'POST',
            });
            
            if (!response.ok) {
                throw new Error('重置游戏失败');
            }
            
            const result = await response.json();
            this.updateGameState(result.game_state);
            this.renderBoard();
            this.hideGameOverModal();
            this.hideAIAnalysis();
            this.showMessage('游戏已重置', 'success');
            
        } catch (error) {
            console.error('Reset failed:', error);
            this.showMessage(error.message, 'error');
        }
    }

    showAIThinking() {
        this.aiThinkingElement.style.display = 'block';
        this.aiAnalysisElement.style.display = 'none';
    }

    hideAIThinking() {
        this.aiThinkingElement.style.display = 'none';
    }

    showAIAnalysis(aiMove) {
        this.aiMoveElement.textContent = `(${aiMove.row}, ${aiMove.col})`;
        this.aiReasoningElement.textContent = aiMove.reasoning;
        this.aiAnalysisElement.style.display = 'block';
    }

    hideAIAnalysis() {
        this.aiAnalysisElement.style.display = 'none';
    }

    showMessage(text, type = 'info') {
        const toastIcon = this.messageToast.querySelector('.toast-icon');
        const toastText = this.messageToast.querySelector('.toast-text');
        
        // 设置图标和样式
        let iconClass = 'fas fa-info-circle';
        let bgColor = '#3498db';
        
        switch (type) {
            case 'success':
                iconClass = 'fas fa-check-circle';
                bgColor = '#2ecc71';
                break;
            case 'error':
                iconClass = 'fas fa-exclamation-circle';
                bgColor = '#e74c3c';
                break;
            case 'warning':
                iconClass = 'fas fa-exclamation-triangle';
                bgColor = '#f39c12';
                break;
        }
        
        toastIcon.className = iconClass;
        toastIcon.style.color = bgColor;
        toastText.textContent = text;
        
        // 显示消息
        this.messageToast.classList.add('show');
        
        // 3秒后自动隐藏
        setTimeout(() => {
            this.messageToast.classList.remove('show');
        }, 3000);
    }

    showGameOverModal() {
        const title = document.getElementById('gameOverTitle');
        const message = document.getElementById('gameOverMessage');
        const icon = document.getElementById('resultIcon');
        
        if (this.gameState.winner === 1) {
            title.textContent = '恭喜获胜！';
            message.textContent = '你成功击败了AI！';
            icon.className = 'fas fa-trophy result-icon';
            icon.style.color = '#f39c12';
        } else if (this.gameState.winner === 2) {
            title.textContent = '很遗憾...';
            message.textContent = 'AI获得了胜利，再接再厉！';
            icon.className = 'fas fa-robot result-icon';
            icon.style.color = '#e74c3c';
        } else {
            title.textContent = '平局！';
            message.textContent = '势均力敌的对决！';
            icon.className = 'fas fa-handshake result-icon';
            icon.style.color = '#3498db';
        }
        
        this.gameOverModal.classList.add('show');
    }

    hideGameOverModal() {
        this.gameOverModal.classList.remove('show');
    }
}

// 页面加载完成后初始化游戏
document.addEventListener('DOMContentLoaded', () => {
    new GomokuUI();
});
