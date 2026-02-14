# -*- coding: utf-8 -*-
import asyncio
import httpx
import os
import re
import sys
from typing import List, Tuple, Optional

from textual.app import App, ComposeResult
from textual import work
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Button, Header, Footer, RichLog, Input, Static
from textual.reactive import var
from textual.screen import Screen


# --- 配置 ---
# 请替换为你的实际API端点和默认模型
API_ENDPOINT = "https://api.modelarts-maas.com/v1/chat/completions"
DEFAULT_MODEL = "DeepSeek-R1" # 或者你使用的其他模型名称

# --- 围棋逻辑 ---
EMPTY = 0
BLACK = 1
WHITE = 2

def coord_to_move(x: int, y: int) -> str:
    """将数组坐标 (0-18) 转换为围棋坐标 (A1-T19)，过滤掉 'I'"""
    if not (0 <= x <= 18 and 0 <= y <= 18):
        return ""
    col_letter = chr(ord('A') + x + (1 if x >= 8 else 0)) # 跳过 'I'
    row_number = str(19 - y)
    return f"{col_letter}{row_number}"

def move_to_coord(move: str) -> Tuple[Optional[int], Optional[int]]:
    """将围棋坐标 (A1-T19) 转换为数组坐标 (0-18)"""
    move = move.strip().upper()
    if not re.match(r'^[A-HJ-T][1-9][0-9]?$|^I[1-9][0-9]?$|^[A-HJ-T]1[0-9]$|^I1[0-9]$|^[A-HJ-T]20$|^I20$', move):
        return None, None
    col_char, row_str = move[0], move[1:]
    
    # 处理列，跳过 'I'
    if col_char >= 'I':
        x = ord(col_char) - ord('A') - 1
    else:
        x = ord(col_char) - ord('A')
        
    y = 19 - int(row_str)
    
    if 0 <= x <= 18 and 0 <= y <= 18:
        return x, y
    return None, None

class GoBoard(Static):
    """用于显示围棋棋盘的Widget"""
    def __init__(self, board_size: int = 19, **kwargs) -> None:
        super().__init__(**kwargs)
        self.board_size = board_size
        self.board = [[EMPTY for _ in range(board_size)] for _ in range(board_size)]

    def update_board(self, board: List[List[int]]) -> None:
        self.board = board
        self.refresh()

    def render(self) -> str:
        """使用Unicode字符绘制棋盘"""
        board_str = ""
        # 顶部列标识
        board_str += "   "
        for i in range(self.board_size):
            if i == 8: # 跳过 'I'
                board_str += "  "
            board_str += chr(ord('A') + i + (1 if i >= 8 else 0)) + " "
        board_str += "\n"

        for y in range(self.board_size):
            # 左侧行号
            row_label = f"{19 - y:2d}"
            board_str += row_label + " "
            for x in range(self.board_size):
                char = " · " # 空点
                if self.board[y][x] == BLACK:
                    char = " ● "
                elif self.board[y][x] == WHITE:
                    char = " ○ "
                
                # 绘制网格线
                if x == 0 and y == 0:
                    char = char.rstrip() + "┌─"
                elif x == self.board_size - 1 and y == 0:
                    char = "─┐"
                elif x == 0 and y == self.board_size - 1:
                    char = char.rstrip() + "└─"
                elif x == self.board_size - 1 and y == self.board_size - 1:
                    char = "─┘"
                elif x == 0:
                    char = char.rstrip() + "├─"
                elif x == self.board_size - 1:
                    char = "─┤"
                elif y == 0:
                    char = "─┬─"
                elif y == self.board_size - 1:
                    char = "─┴─"
                else:
                    char = "─┼─"

                # 星位点
                if (x, y) in [(3, 3), (3, 9), (3, 15), (9, 3), (9, 9), (9, 15), (15, 3), (15, 9), (15, 15)]:
                    if char == "─┼─":
                        char = "─◆─"
                    elif char == " · ":
                        char = " ◆ "

                board_str += char
            # 右侧行号
            board_str += row_label + "\n"
        # 底部列标识
        board_str += "   "
        for i in range(self.board_size):
            if i == 8:
                board_str += "  "
            board_str += chr(ord('A') + i + (1 if i >= 8 else 0)) + " "
        board_str += "\n"
        return board_str

# --- API交互逻辑 ---
async def get_ai_move(board: List[List[int]], api_key: str, model: str, conversation_history: List[dict]) -> Tuple[Optional[str], Optional[str]]:
    """
    调用OpenAI风格API获取AI的下一步棋和解说
    :param board: 当前棋盘状态
    :param api_key: API密钥
    :param model: 模型名称
    :param conversation_history: 对话历史
    :return: (解说文本, 落子坐标字符串)
    """
    # 将棋盘转换为坐标列表字符串
    moves_str = ""
    for y in range(19):
        for x in range(19):
            if board[y][x] == BLACK:
                moves_str += f"B:{coord_to_move(x, y)} "
            elif board[y][x] == WHITE:
                moves_str += f"W:{coord_to_move(x, y)} "
    
    current_board_state = f"当前棋局: {moves_str.strip() if moves_str else '空棋盘'}"

    # 构建发送给AI的提示
    system_prompt = (
        "你是一位专业的围棋教练和对手。你的任务是分析当前棋局，作为黑棋（●）进行下一步，并提供专业、简洁的解说。"
        "请严格遵守以下输出格式：\n"
        "1. 首先，用1-3句话解释你的落子思路和策略。\n"
        "2. 然后，用一行单独写出你的落子坐标，格式为 '落子坐标: <坐标>'，例如 '落子坐标: Q16'。\n"
        "请不要使用markdown或其他格式，严格按照上述文本格式回复。"
    )

    user_prompt = f"{current_board_state}\n请作为黑棋给出你的下一步和解说。"

    # 更新对话历史
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(API_ENDPOINT, headers=headers, json=data, timeout=60.0)
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()

            # 解析AI回复
            lines = content.split('\n')
            move_line = None
            commentary_lines = []
            for line in lines:
                if line.startswith("落子坐标:"):
                    move_line = line
                else:
                    commentary_lines.append(line)
            
            commentary = '\n'.join(commentary_lines).strip()
            move_str = move_line.split(":", 1)[1].strip() if move_line else None

            # 将此次对话加入历史
            conversation_history.append({"role": "user", "content": user_prompt})
            conversation_history.append({"role": "assistant", "content": content})

            return commentary, move_str
    except Exception as e:
        return f"调用API时出错: {e}", None


# --- 主应用 ---
class GoGameApp(App):

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
    ]

    # 使用var创建响应式变量
    board_data = var([[EMPTY for _ in range(19)] for _ in range(19)])
    game_over = var(False)
    api_key = var("")
    model = var(DEFAULT_MODEL)
    conversation_history = var([])

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with Container(id="game-container"):
            yield GoBoard(id="board")
            with Vertical(id="info-panel"):
                yield RichLog(id="commentary", markup=True)
                yield Input(placeholder="输入你的白棋落子 (例如: Q4), 按Enter确认", id="user-input")
                with Horizontal(id="button-row"):
                    yield Button("开始新游戏", id="new-game", variant="primary")
                    yield Button("悔棋", id="undo", variant="warning")

    def on_mount(self) -> None:
        self.title = "围棋对弈 - 与AI教练"
        self.sub_title = "执白子与AI对弈"
        self.query_one("#user-input").disabled = True
        self.print_to_commentary("欢迎来到围棋对弈！请先在终端中输入API密钥和模型名称。", "system")

    async def on_ready(self) -> None:
        await self.push_screen_wait(APIConfigScreen())

    def print_to_commentary(self, message: str, sender: str = "system") -> None:
        """向解说区域添加消息"""
        log = self.query_one("#commentary", RichLog)
        if sender == "user":
            log.write(f"[bold green]你:[/bold green] {message}", shrink=False)
        elif sender == "ai":
            log.write(f"[bold magenta]AI教练:[/bold magenta] {message}", shrink=False)
        else:
            log.write(f"[bold yellow]{message}[/bold yellow]", shrink=False)
        log.scroll_end()

    async def make_ai_move(self) -> None:
        """处理AI行棋逻辑"""
        if self.game_over:
            return

        self.query_one("#user-input").disabled = True
        self.print_to_commentary("AI教练正在思考...", "system")
        
        try:
            commentary, move_str = await get_ai_move(
                self.board_data, self.api_key, self.model, self.conversation_history
            )
            
            if move_str:
                x, y = move_to_coord(move_str)
                if x is not None and y is not None and self.board_data[y][x] == EMPTY:
                    self.board_data[y][x] = BLACK
                    self.query_one("#board", GoBoard).update_board(self.board_data)
                    self.print_to_commentary(f"{commentary}\n---\n落子: {move_str}", "ai")
                else:
                    self.print_to_commentary(f"AI返回了无效落子: {move_str} 或坐标解析错误。", "system")
                    self.game_over = True
            else:
                self.print_to_commentary(f"AI未能提供有效落子。回复: {commentary}", "system")
                self.game_over = True
        except Exception as e:
            self.print_to_commentary(f"发生未预期的错误: {e}", "system")
            self.game_over = True
        finally:
            if not self.game_over:
                self.query_one("#user-input").disabled = False
                self.query_one("#user-input").focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new-game":
            self.board_data = [[EMPTY for _ in range(19)] for _ in range(19)]
            self.game_over = False
            self.conversation_history = []
            self.query_one("#board", GoBoard).update_board(self.board_data)
            self.query_one("#commentary", RichLog).clear()
            self.query_one("#user-input").disabled = False
            self.print_to_commentary("新游戏开始！你执白子，请先落子。", "system")
            self.query_one("#user-input").focus()
        elif event.button.id == "undo":
            self.print_to_commentary("悔棋功能尚未实现。", "system")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if self.game_over or not event.input.value:
            return

        move_str = event.input.value.strip()
        x, y = move_to_coord(move_str)

        if x is None or y is None:
            self.print_to_commentary(f"无效坐标: {move_str}", "system")
            event.input.value = ""
            return

        if self.board_data[y][x] != EMPTY:
            self.print_to_commentary(f"位置 {move_str} 已有棋子！", "system")
            event.input.value = ""
            return

        # 更新棋盘 - 用户落子
        self.board_data[y][x] = WHITE
        self.query_one("#board", GoBoard).update_board(self.board_data)
        self.print_to_commentary(move_str, "user")
        event.input.value = ""

        # 触发AI行棋
        await self.make_ai_move()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark


class APIConfigScreen(Screen):
    """用于在应用启动时配置API密钥和模型的屏幕"""
    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("请输入API配置", id="config-title"),
            Input(placeholder="API Key", password=True, id="api-key-input"),
            Input(placeholder="模型名称 (例如: gpt-4-turbo)", id="model-input"),
            Button("确认", id="confirm-btn", variant="primary"),
            id="config-container"
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-btn":
            api_key = self.query_one("#api-key-input").value
            model = self.query_one("#model-input").value or DEFAULT_MODEL
            if not api_key:
                self.app.bell()
                return

            self.app.api_key = api_key
            self.app.model = model
            self.app.query_one("#user-input").disabled = False
            self.app.print_to_commentary(f"配置已加载。使用模型: {model}", "system")
            self.app.print_to_commentary("游戏开始！你执白子，请先落子。", "system")
            await self.dismiss(None)

if __name__ == "__main__":
    app = GoGameApp()
    app.run()

