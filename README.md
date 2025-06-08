# LLMGomoku - AI驱动的五子棋游戏

[![GitHub license](https://img.shields.io/github/license/RusianHu/LLMGomoku)](https://github.com/RusianHu/LLMGomoku/blob/main/LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Framework](https://img.shields.io/badge/Framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![GitHub stars](https://img.shields.io/github/stars/RusianHu/LLMGomoku)](https://github.com/RusianHu/LLMGomoku/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/RusianHu/LLMGomoku)](https://github.com/RusianHu/LLMGomoku/network)

[English](README.en.md)

一个使用 Gemini AI 驱动的五子棋游戏，采用 FastAPI + 前端 Web 界面实现。

## 技术栈

- **后端**: Python + FastAPI
- **AI**: Google Gemini API
- **前端**: HTML + CSS + JavaScript

## 安装和运行

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置 API Key：
将 `config.py.env` 重命名为 `config.py`，并编辑配置文件。

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
├── main.py                 # FastAPI 主应用
├── config.py               # 配置文件
├── game_logic.py           # 五子棋游戏逻辑
├── llm_player.py           # LLM 玩家逻辑
├── gemini_api.py           # Gemini API 工具类
├── requirements.txt        # 依赖列表
└── static/                 # 静态文件
    ├── index.html          # 主页面
    ├── style.css           # 样式文件
    └── script.js           # 前端逻辑
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

所有配置项均在 `config.py` 文件中设置。

-   **LLM 提供商 (`LLM_PROVIDER`)**: 选择使用的 LLM 服务。
    -   `"gemini"`: 使用 Google Gemini API (默认)。
    -   `"lmstudio"`: 使用本地运行的 LMStudio 服务。
-   **Gemini API 配置**:
    -   `GEMINI_API_KEY`: 你的 Google Gemini API 密钥。
    -   `GEMINI_MODEL`: 使用的 Gemini 模型 (例如: `"gemini-1.5-flash-preview-0514"`)。
-   **LMStudio 配置**:
    -   `LMSTUDIO_BASE_URL`: LMStudio 服务的地址 (例如: `"http://localhost:1234/v1"`)。
    -   `LMSTUDIO_MODEL`: 使用的本地模型名称。
-   **LLM 对话配置**:
    -   `MAX_CONVERSATION_HISTORY`: 保留的对话历史轮数。
    -   `MAX_OUTPUT_TOKENS`: LLM 生成内容的最大长度。
-   **棋盘配置**:
    -   `BOARD_SIZE`: 棋盘大小 (例如: `15` 代表 15x15)。
    -   `WIN_LENGTH`: 获胜所需的连续棋子数量 (例如: `5`)。
-   **游戏配置**:
    -   `PLAYER_SYMBOL`, `AI_SYMBOL`, `EMPTY_SYMBOL`: 分别定义玩家、AI和空格在棋盘上的表示符号。
-   **服务器配置**:
    -   `HOST`: 服务器监听地址。
    -   `PORT`: 服务器监听端口。
    -   `DEBUG`: 是否开启 FastAPI 的调试模式。
-   **调试模式 (`DEBUG_MODE`)**:
    -   `True`: 启用游戏内调试窗口和更详细的日志输出。
-   **系统提示词 (`SYSTEM_PROMPT`)**:
    -   用于指导 AI 行为的详细系统提示。
-   **LLM 响应格式 (`LLM_RESPONSE_SCHEMA`)**:
    -   定义了要求 LLM 返回的 JSON 对象的结构。

## 开发说明

项目采用模块化设计：
- `game_logic.py`: 纯粹的游戏逻辑，不依赖外部服务
- `llm_player.py`: LLM 玩家实现，处理与 AI 的交互
- `main.py`: Web 服务器和 API 路由
- `static/`: 前端界面文件

## 许可证

[MIT License](LICENSE)
