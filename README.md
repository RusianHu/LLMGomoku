# LLMGomoku - AI驱动的五子棋游戏

一个使用 Gemini AI 驱动的五子棋游戏，采用 FastAPI + 前端 Web 界面实现。

## 功能特点

- 🤖 **AI 对手**: 使用 Google Gemini API 驱动的智能 AI 玩家
- 🎮 **Web 界面**: 基于 FastAPI 的现代化 Web 界面
- 🎨 **二次元风格**: 精美的界面设计
- 📊 **实时分析**: 显示 AI 的思考过程和决策理由
- 🔄 **JSON 通信**: 标准化的棋盘状态和移动格式

## 技术栈

- **后端**: Python + FastAPI
- **AI**: Google Gemini API
- **前端**: HTML + CSS + JavaScript
- **样式**: 现代化二次元风格设计

## 安装和运行

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置 API Key：
编辑 `config.py` 文件中的 `GEMINI_API_KEY`

3. 启动服务器：
```bash
python main.py
```

4. 打开浏览器访问：
```
http://127.0.0.1:8000
```

## 项目结构

```
LLMGomoku/
├── main.py              # FastAPI 主应用
├── config.py            # 配置文件
├── game_logic.py        # 五子棋游戏逻辑
├── llm_player.py        # LLM 玩家逻辑
├── gemini_api.py        # Gemini API 工具类
├── requirements.txt     # 依赖列表
└── static/             # 静态文件
    ├── index.html      # 主页面
    ├── style.css       # 样式文件
    └── script.js       # 前端逻辑
```

## 游戏规则

- 15x15 标准五子棋棋盘
- 玩家使用黑子（数字1），AI使用白子（数字2）
- 先连成5子者获胜
- 支持横、竖、斜四个方向

## API 接口

- `GET /` - 游戏主页面
- `GET /api/game/state` - 获取游戏状态
- `POST /api/game/move` - 玩家下棋
- `POST /api/game/reset` - 重置游戏

## 配置说明

在 `config.py` 中可以配置：
- Gemini API Key 和模型
- 棋盘大小和获胜条件
- LLM 对话历史长度
- 服务器端口等

## 开发说明

项目采用模块化设计：
- `game_logic.py`: 纯粹的游戏逻辑，不依赖外部服务
- `llm_player.py`: LLM 玩家实现，处理与 AI 的交互
- `main.py`: Web 服务器和 API 路由
- `static/`: 前端界面文件

## 许可证

[MIT License](LICENSE)
