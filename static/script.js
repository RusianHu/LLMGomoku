// LLMGomoku 前端 JavaScript

class GomokuUI {
    constructor() {
        this.gameState = null;
        this.isPlayerTurn = true;
        this.isGameOver = false;
        this.boardElement = document.getElementById('gameBoard');
        this.lastHighlightedCell = null; // 记录上次高亮的格子

        this.initializeElements();
        this.bindEvents();
        this.loadGameState();
    }

    initializeElements() {
        // 获取DOM元素
        this.currentPlayerElement = document.getElementById('currentPlayer');
        this.gameStatusElement = document.getElementById('gameStatus');
        this.roundNumberElement = document.getElementById('roundNumber');
        this.tokenCountElement = document.getElementById('tokenCount');
        this.aiThinkingElement = document.getElementById('aiThinking');
        this.aiAnalysisElement = document.getElementById('aiAnalysis');
        this.aiMoveElement = document.getElementById('aiMove');
        this.aiReasoningElement = document.getElementById('aiReasoning');
        this.messageToast = document.getElementById('messageToast');
        this.gameOverModal = document.getElementById('gameOverModal');
        this.contextModal = document.getElementById('contextModal');
        this.resetBtn = document.getElementById('resetBtn');
        this.playAgainBtn = document.getElementById('playAgainBtn');
        this.contextBtn = document.getElementById('contextBtn');
        this.closeContextBtn = document.getElementById('closeContextBtn');

        // 调试窗口元素
        this.debugPanel = document.getElementById('debugPanel');
        this.toggleDebugBtn = document.getElementById('toggleDebugBtn');
        this.refreshDebugBtn = document.getElementById('refreshDebugBtn');
        this.debugRequestTime = document.getElementById('debugRequestTime');
        this.debugRequest = document.getElementById('debugRequest');
        this.debugResponse = document.getElementById('debugResponse');
    }

    bindEvents() {
        // 绑定事件
        this.resetBtn.addEventListener('click', () => this.resetGame());
        this.playAgainBtn.addEventListener('click', () => this.resetGame());
        this.contextBtn.addEventListener('click', () => this.showContextModal());
        this.closeContextBtn.addEventListener('click', () => this.hideContextModal());

        // 调试窗口事件
        if (this.toggleDebugBtn) {
            this.toggleDebugBtn.addEventListener('click', () => this.toggleDebugPanel());
        }
        if (this.refreshDebugBtn) {
            this.refreshDebugBtn.addEventListener('click', () => this.refreshDebugInfo());
        }

        // 点击模态框外部关闭
        this.gameOverModal.addEventListener('click', (e) => {
            if (e.target === this.gameOverModal) {
                this.hideGameOverModal();
            }
        });

        this.contextModal.addEventListener('click', (e) => {
            if (e.target === this.contextModal) {
                this.hideContextModal();
            }
        });
    }

    async loadGameState() {
        try {
            const response = await fetch('/api/game/state');
            const gameState = await response.json();
            this.updateGameState(gameState);
            this.renderBoard();
            this.updateTokenCount();
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

        // 更新回合数
        if (gameState.round_number) {
            this.roundNumberElement.textContent = gameState.round_number;
        }

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

        // 获取AI最新落子位置
        const lastAiMove = this.gameState.last_ai_move;

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

        // 清除之前的高亮效果
        if (this.lastHighlightedCell) {
            this.lastHighlightedCell.classList.remove('ai-latest');
            this.lastHighlightedCell = null;
        }

        // 在DOM更新后添加AI最新落子高亮效果
        if (lastAiMove) {
            setTimeout(() => {
                const targetCell = this.boardElement.querySelector(
                    `[data-row="${lastAiMove[0]}"][data-col="${lastAiMove[1]}"]`
                );
                if (targetCell && targetCell.classList.contains('ai')) {
                    targetCell.classList.add('ai-latest');
                    this.lastHighlightedCell = targetCell;
                }
            }, 50);
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
            
            // 直接从服务器加载最新的、最权威的游戏状态
            // 这将确保玩家的落子和AI的落子都被正确渲染
            await this.loadGameState();
            
            // 隐藏AI思考状态
            this.hideAIThinking();
            
            // 显示AI分析 (result 仍然有用)
            if (result.ai_move) {
                this.showAIAnalysis(result.ai_move);
            }

            // 刷新调试信息（如果调试窗口打开）
            if (this.debugPanel && this.debugPanel.classList.contains('open')) {
                this.refreshDebugInfo();
            }

            // 显示消息
            this.showMessage(result.message, result.success ? 'success' : 'error');

            // 检查游戏是否结束 (loadGameState 已经更新了 isGameOver)
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
            this.updateTokenCount();
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

    async updateTokenCount() {
        try {
            const response = await fetch('/api/game/context');
            const contextInfo = await response.json();
            this.tokenCountElement.textContent = contextInfo.total_consumed_tokens || 0;
        } catch (error) {
            console.error('Failed to update token count:', error);
            this.tokenCountElement.textContent = '?';
        }
    }

    async showContextModal() {
        try {
            const response = await fetch('/api/game/context');
            const contextInfo = await response.json();

            // 更新统计信息
            document.getElementById('contextLlmProvider').textContent = contextInfo.llm_provider || '-';
            document.getElementById('contextModel').textContent = contextInfo.model || '-';
            document.getElementById('contextConversationCount').textContent = contextInfo.conversation_count || 0;
            document.getElementById('contextMaxHistory').textContent = contextInfo.max_conversation_history || 5;
            document.getElementById('contextTokenCount').textContent = contextInfo.total_consumed_tokens || 0;

            // 更新对话历史
            const historyContent = document.getElementById('contextHistoryContent');
            historyContent.innerHTML = '';

            if (contextInfo.context_history && contextInfo.context_history.length > 0) {
                contextInfo.context_history.forEach((message, index) => {
                    const messageDiv = document.createElement('div');
                    messageDiv.className = `history-message ${message.role}`;

                    const roleSpan = document.createElement('span');
                    roleSpan.className = 'message-role';
                    roleSpan.textContent = message.role === 'user' ? '用户' :
                                          message.role === 'model' ? 'AI' : '系统';

                    const contentDiv = document.createElement('div');
                    contentDiv.className = 'message-content';

                    if (message.parts && message.parts.length > 0) {
                        message.parts.forEach(part => {
                            if (part.text) {
                                const textP = document.createElement('p');
                                textP.textContent = part.text.length > 200 ?
                                    part.text.substring(0, 200) + '...' : part.text;
                                contentDiv.appendChild(textP);
                            }
                        });
                    }

                    messageDiv.appendChild(roleSpan);
                    messageDiv.appendChild(contentDiv);
                    historyContent.appendChild(messageDiv);
                });
            } else {
                const emptyDiv = document.createElement('div');
                emptyDiv.className = 'empty-history';
                emptyDiv.textContent = '暂无对话历史';
                historyContent.appendChild(emptyDiv);
            }

            this.contextModal.classList.add('show');

        } catch (error) {
            console.error('Failed to load context info:', error);
            this.showMessage('加载上下文信息失败', 'error');
        }
    }

    hideContextModal() {
        this.contextModal.classList.remove('show');
    }

    toggleDebugPanel() {
        if (this.debugPanel) {
            this.debugPanel.classList.toggle('open');
            const icon = this.toggleDebugBtn.querySelector('i');
            if (this.debugPanel.classList.contains('open')) {
                icon.className = 'fas fa-times';
                this.refreshDebugInfo(); // 打开时自动刷新
            } else {
                icon.className = 'fas fa-bug';
            }
        }
    }

    async refreshDebugInfo() {
        if (!this.debugPanel) return;

        try {
            const response = await fetch('/api/game/debug');
            if (!response.ok) {
                if (response.status === 404) {
                    this.debugRequestTime.textContent = '调试模式未启用';
                    this.debugRequest.textContent = '调试模式未启用';
                    this.debugResponse.textContent = '调试模式未启用';
                    return;
                }
                throw new Error('获取调试信息失败');
            }

            const debugInfo = await response.json();

            if (!debugInfo.debug_enabled) {
                this.debugRequestTime.textContent = '调试模式未启用';
                this.debugRequest.textContent = '调试模式未启用';
                this.debugResponse.textContent = '调试模式未启用';
                return;
            }

            // 更新请求时间
            if (debugInfo.last_request_time) {
                this.debugRequestTime.textContent = `${(debugInfo.last_request_time * 1000).toFixed(2)} ms`;
            } else {
                this.debugRequestTime.textContent = '暂无数据';
            }

            // 更新请求信息
            if (debugInfo.last_request) {
                this.debugRequest.textContent = JSON.stringify(debugInfo.last_request, null, 2);
            } else {
                this.debugRequest.textContent = '暂无数据';
            }

            // 更新响应信息
            if (debugInfo.last_response) {
                this.debugResponse.textContent = JSON.stringify(debugInfo.last_response, null, 2);
            } else {
                this.debugResponse.textContent = '暂无数据';
            }

        } catch (error) {
            console.error('Failed to refresh debug info:', error);
            this.debugRequestTime.textContent = '获取失败';
            this.debugRequest.textContent = '获取失败: ' + error.message;
            this.debugResponse.textContent = '获取失败: ' + error.message;
        }
    }
}

// 页面加载完成后初始化游戏
document.addEventListener('DOMContentLoaded', () => {
    new GomokuUI();
});
