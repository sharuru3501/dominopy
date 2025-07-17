"""
PyDomino Qt Terminal Widget (独自実装)
Claude Code統合とライブコーディング支援のための純正Qtターミナル
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QPlainTextEdit, QLineEdit, QPushButton, 
                               QSplitter, QLabel, QFrame, QComboBox,
                               QTextBrowser, QProgressBar, QMenu,
                               QScrollArea, QGroupBox)
from PySide6.QtCore import Qt, QProcess, Signal, QTimer
from PySide6.QtGui import (QFont, QTextCharFormat, QColor, QTextCursor,
                          QAction, QKeySequence, QTextBlockFormat)
import os
import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Callable

class ANSIColorParser:
    """ANSI色コードをQtのテキスト形式に変換"""
    
    def __init__(self):
        self.color_map = {
            '30': '#000000',  # 黒
            '31': '#e74c3c',  # 赤
            '32': '#2ecc71',  # 緑
            '33': '#f39c12',  # 黄
            '34': '#3498db',  # 青
            '35': '#9b59b6',  # マゼンタ
            '36': '#1abc9c',  # シアン
            '37': '#ecf0f1',  # 白
            '90': '#7f8c8d',  # 明るい黒
            '91': '#e67e22',  # 明るい赤
            '92': '#27ae60',  # 明るい緑
            '93': '#f1c40f',  # 明るい黄
            '94': '#2980b9',  # 明るい青
            '95': '#8e44ad',  # 明るいマゼンタ
            '96': '#16a085',  # 明るいシアン
            '97': '#ffffff',  # 明るい白
        }
    
    def parse_ansi(self, text: str) -> str:
        """ANSI色コードをHTML形式に変換"""
        # ANSIエスケープシーケンスのパターン
        ansi_pattern = r'\x1b\[([0-9;]*)m'
        
        def replace_ansi(match):
            codes = match.group(1).split(';') if match.group(1) else ['0']
            
            for code in codes:
                if code == '0':  # リセット
                    return '</span>'
                elif code in self.color_map:
                    color = self.color_map[code]
                    return f'<span style="color: {color};">'
                elif code == '1':  # 太字
                    return '<span style="font-weight: bold;">'
            
            return ''
        
        # ANSIコードをHTMLに変換
        html_text = re.sub(ansi_pattern, replace_ansi, text)
        
        # 未閉じのspanタグを閉じる
        open_spans = html_text.count('<span') - html_text.count('</span>')
        html_text += '</span>' * open_spans
        
        return html_text

class CommandHistory:
    """コマンド履歴管理"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.history: List[str] = []
        self.current_index = 0
    
    def add(self, command: str):
        """コマンドを履歴に追加"""
        if command.strip() and (not self.history or self.history[-1] != command):
            self.history.append(command)
            if len(self.history) > self.max_size:
                self.history.pop(0)
        self.current_index = len(self.history)
    
    def get_previous(self) -> Optional[str]:
        """前のコマンドを取得"""
        if self.current_index > 0:
            self.current_index -= 1
            return self.history[self.current_index]
        return None
    
    def get_next(self) -> Optional[str]:
        """次のコマンドを取得"""
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            return self.history[self.current_index]
        elif self.current_index == len(self.history) - 1:
            self.current_index = len(self.history)
            return ""
        return None


class QtTerminalWidget(QWidget):
    """
    PyDomino用Qt純正ターミナルウィジェット
    Claude Code統合とライブコーディング支援機能付き
    """
    
    # シグナル
    command_executed = Signal(str, int)  # command, exit_code
    claude_code_generated = Signal(str)  # generated_code
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 設定
        self.working_directory = os.getcwd()
        self.current_process = None
        self.interactive_claude_session = None
        self.in_claude_session = False
        
        # 履歴管理
        self.command_history = CommandHistory()
        
        # 色解析
        self.ansi_parser = ANSIColorParser()
        
        # UI初期化
        self.init_ui()
        self.setup_shortcuts()
        self.setup_context_menu()
        
        # 初期メッセージ
        self.append_output("🖥️  PyDomino Terminal Ready", "system")
        self.append_output(f"📁 Working Directory: {self.working_directory}", "info")
        self.append_output("💡 Type 'help' for available commands", "info")
    
    def init_ui(self):
        """UI初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        
        # ヘッダー
        self.create_header(layout)
        
        # メインエリア
        self.create_main_area(layout)
        
        # 入力エリア
        self.create_input_area(layout)
        
        # ステータスバー
        self.create_status_bar(layout)
        
        # スタイル適用
        self.apply_terminal_style()
    
    def create_header(self, parent_layout):
        """ヘッダー作成"""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_layout = QHBoxLayout(header_frame)
        
        # タイトル
        title_label = QLabel("🖥️ PyDomino Terminal")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #4ec9b0;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # 作業ディレクトリ表示
        self.working_dir_label = QLabel(f"📁 {os.path.basename(self.working_directory)}")
        self.working_dir_label.setStyleSheet("color: #9cdcfe; font-size: 12px;")
        header_layout.addWidget(self.working_dir_label)
        
        # クリアボタン
        clear_button = QPushButton("Clear")
        clear_button.setMaximumWidth(60)
        clear_button.clicked.connect(self.clear_terminal)
        header_layout.addWidget(clear_button)
        
        parent_layout.addWidget(header_frame)
    
    def create_main_area(self, parent_layout):
        """メインエリア作成"""
        # 出力エリア
        self.output_area = QTextBrowser()
        self.output_area.setAcceptRichText(True)
        self.output_area.setOpenExternalLinks(False)
        self.output_area.setContextMenuPolicy(Qt.CustomContextMenu)
        self.output_area.customContextMenuRequested.connect(self.show_context_menu)
        
        # フォント設定
        terminal_font = QFont("Monaco", 12)
        if not terminal_font.exactMatch():
            terminal_font = QFont("Consolas", 12)
        if not terminal_font.exactMatch():
            terminal_font = QFont("monospace", 12)
        
        self.output_area.setFont(terminal_font)
        
        parent_layout.addWidget(self.output_area)
    
    def create_input_area(self, parent_layout):
        """入力エリア作成"""
        input_frame = QFrame()
        input_frame.setFrameStyle(QFrame.StyledPanel)
        input_layout = QHBoxLayout(input_frame)
        
        # プロンプト表示
        self.prompt_label = QLabel("$")
        self.prompt_label.setStyleSheet("color: #4ec9b0; font-weight: bold;")
        input_layout.addWidget(self.prompt_label)
        
        # コマンド入力
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command or 'claude \"prompt\"' for AI assistance...")
        self.command_input.returnPressed.connect(self.execute_command)
        input_layout.addWidget(self.command_input)
        
        # 実行ボタン
        execute_button = QPushButton("Run")
        execute_button.setMaximumWidth(60)
        execute_button.clicked.connect(self.execute_command)
        input_layout.addWidget(execute_button)
        
        parent_layout.addWidget(input_frame)
    
    def create_status_bar(self, parent_layout):
        """ステータスバー作成"""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel)
        status_layout = QHBoxLayout(status_frame)
        
        # ステータス表示
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #4ec9b0;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        # プロセス情報
        self.process_label = QLabel("No process")
        self.process_label.setStyleSheet("color: #cccccc; font-size: 11px;")
        status_layout.addWidget(self.process_label)
        
        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(100)
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        parent_layout.addWidget(status_frame)
    
    def setup_shortcuts(self):
        """キーボードショートカット設定"""
        # 履歴ナビゲーション
        self.command_input.keyPressEvent = self.handle_key_press
    
    def setup_context_menu(self):
        """コンテキストメニュー設定"""
        self.context_menu = QMenu(self)
        
        # Copy
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self.copy_selected_text)
        self.context_menu.addAction(copy_action)
        
        # Clear
        clear_action = QAction("Clear Terminal", self)
        clear_action.triggered.connect(self.clear_terminal)
        self.context_menu.addAction(clear_action)
        
        self.context_menu.addSeparator()
        
        # Claude Code actions
        claude_action = QAction("Generate with Claude Code", self)
        claude_action.triggered.connect(self.prompt_claude_code)
        self.context_menu.addAction(claude_action)
    
    def handle_key_press(self, event):
        """キーイベント処理"""
        if event.key() == Qt.Key_Up:
            # 履歴から前のコマンドを取得
            prev_command = self.command_history.get_previous()
            if prev_command is not None:
                self.command_input.setText(prev_command)
            return
        
        elif event.key() == Qt.Key_Down:
            # 履歴から次のコマンドを取得
            next_command = self.command_history.get_next()
            if next_command is not None:
                self.command_input.setText(next_command)
            return
        
        elif event.key() == Qt.Key_Tab:
            # 簡単なタブ補完（将来実装）
            self.handle_tab_completion()
            return
        
        # デフォルトの処理
        QLineEdit.keyPressEvent(self.command_input, event)
    
    def handle_tab_completion(self):
        """タブ補完処理（基本実装）"""
        current_text = self.command_input.text()
        
        # 基本的なコマンド補完
        basic_commands = ['claude', 'help', 'clear', 'ls', 'cd', 'pwd']
        
        matches = [cmd for cmd in basic_commands if cmd.startswith(current_text)]
        
        if len(matches) == 1:
            self.command_input.setText(matches[0])
        elif len(matches) > 1:
            self.append_output(f"Possible completions: {', '.join(matches)}", "info")
    
    def execute_command(self):
        """コマンド実行"""
        command = self.command_input.text().strip()
        
        if not command:
            return
        
        # 履歴に追加
        self.command_history.add(command)
        
        # 入力をクリア
        self.command_input.clear()
        
        # Claude Codeセッション中の場合
        if self.in_claude_session:
            if command.lower() == 'exit':
                self.stop_claude_session()
                return
            
            # コマンドをエコー（Claude Codeセッション用）
            self.append_output(f"claude> {command}", "command")
            
            # Claude Codeセッションにメッセージ送信
            self.send_to_claude_session(command)
        else:
            # 通常モード
            # コマンドをエコー
            self.append_output(f"$ {command}", "command")
            
            # コマンド解析と実行
            self.parse_and_execute(command)
    
    def parse_and_execute(self, command: str):
        """コマンド解析と実行"""
        parts = command.split()
        
        if not parts:
            return
        
        cmd = parts[0].lower()
        
        # 内蔵コマンド
        if cmd == 'help':
            self.show_help()
        elif cmd == 'clear':
            self.clear_terminal()
        elif cmd == 'pwd':
            self.append_output(self.working_directory, "output")
        elif cmd == 'cd':
            self.change_directory(parts[1] if len(parts) > 1 else os.path.expanduser("~"))
        elif cmd == 'claude':
            if len(parts) == 1:
                # 引数なしの場合は対話セッション開始
                self.start_interactive_claude()
            else:
                # 引数ありの場合は一度だけ実行
                self.execute_claude_code(' '.join(parts[1:]))
        else:
            # 外部コマンド実行
            self.execute_external_command(cmd, parts[1:])
    
    def execute_claude_code(self, prompt: str):
        """Claude Code実行"""
        if not prompt.strip():
            self.append_output("Usage: claude \"your prompt here\"", "error")
            return
        
        self.append_output("🤖 Calling Claude Code...", "info")
        self.set_status("Executing Claude Code...")
        
        try:
            # 前のプロセスが実行中の場合は停止
            if self.current_process:
                self.current_process.kill()
                self.current_process = None
            
            # 新しいプロセスを作成
            self.current_process = QProcess(self)
            self.current_process.setWorkingDirectory(self.working_directory)
            
            # シグナル接続
            self.current_process.readyReadStandardOutput.connect(self._on_claude_stdout)
            self.current_process.readyReadStandardError.connect(self._on_claude_stderr)
            self.current_process.finished.connect(self._on_claude_finished)
            
            # プロセス開始
            self.current_process.start('claude', ['--print', prompt])
            
        except Exception as e:
            self.append_output(f"Failed to execute Claude Code: {str(e)}", "error")
            self.set_status("Claude Code failed")
    
    def start_interactive_claude(self):
        """対話型Claude Codeセッション開始"""
        if self.in_claude_session:
            self.append_output("Claude session already running. Type 'exit' to quit.", "warning")
            return
        
        self.append_output("🤖 Starting interactive Claude Code session...", "info")
        self.append_output("Type 'exit' to quit Claude session", "info")
        self.set_status("Claude Code session starting...")
        
        try:
            # 対話型Claude Codeプロセスを開始
            self.interactive_claude_session = QProcess(self)
            self.interactive_claude_session.setWorkingDirectory(self.working_directory)
            
            # シグナル接続
            self.interactive_claude_session.readyReadStandardOutput.connect(self._on_interactive_claude_stdout)
            self.interactive_claude_session.readyReadStandardError.connect(self._on_interactive_claude_stderr)
            self.interactive_claude_session.finished.connect(self._on_interactive_claude_finished)
            
            # 対話型Claude Codeを開始
            self.interactive_claude_session.start('claude', [])
            
            if self.interactive_claude_session.waitForStarted(5000):
                self.in_claude_session = True
                self.set_status("Claude Code session active")
                self.update_prompt_for_claude_session()
            else:
                self.append_output("Failed to start Claude Code session", "error")
                self.set_status("Claude Code session failed")
                
        except Exception as e:
            self.append_output(f"Failed to start Claude Code session: {str(e)}", "error")
            self.set_status("Claude Code session failed")
    
    def send_to_claude_session(self, message: str):
        """対話型Claude Codeセッションにメッセージ送信"""
        if not self.in_claude_session or not self.interactive_claude_session:
            return
        
        try:
            # メッセージを送信
            self.interactive_claude_session.write(message.encode('utf-8') + b'\n')
        except Exception as e:
            self.append_output(f"Failed to send message to Claude: {str(e)}", "error")
    
    def stop_claude_session(self):
        """対話型Claude Codeセッション終了"""
        if not self.in_claude_session:
            return
        
        self.append_output("Stopping Claude Code session...", "info")
        
        if self.interactive_claude_session:
            self.interactive_claude_session.terminate()
            if not self.interactive_claude_session.waitForFinished(3000):
                self.interactive_claude_session.kill()
        
        self.in_claude_session = False
        self.interactive_claude_session = None
        self.set_status("Claude Code session stopped")
        self.update_prompt_for_normal_mode()
    
    def update_prompt_for_claude_session(self):
        """Claude Codeセッション用プロンプトに更新"""
        self.prompt_label.setText("claude>")
        self.prompt_label.setStyleSheet("color: #9cdcfe; font-weight: bold;")
        self.command_input.setPlaceholderText("Enter message for Claude (type 'exit' to quit session)")
    
    def update_prompt_for_normal_mode(self):
        """通常モード用プロンプトに更新"""
        self.prompt_label.setText("$")
        self.prompt_label.setStyleSheet("color: #4ec9b0; font-weight: bold;")
        self.command_input.setPlaceholderText("Enter command or 'claude \"prompt\"' for AI assistance...")
    
    def _on_interactive_claude_stdout(self):
        """対話型Claude Code標準出力を処理"""
        if self.interactive_claude_session:
            data = self.interactive_claude_session.readAllStandardOutput().data().decode('utf-8', errors='ignore')
            # Claude Codeの出力を表示
            self.append_output(data, "claude_output")
            
            # Strudelコードの検出
            if 'strudel' in data.lower() or '$:' in data or 'sound(' in data:
                self.claude_code_generated.emit(data)
                self.append_output("🎵 Strudel code detected in session!", "success")
    
    def _on_interactive_claude_stderr(self):
        """対話型Claude Code標準エラーを処理"""
        if self.interactive_claude_session:
            data = self.interactive_claude_session.readAllStandardError().data().decode('utf-8', errors='ignore')
            self.append_output(data, "error")
    
    def _on_interactive_claude_finished(self, exit_code):
        """対話型Claude Code完了時の処理"""
        self.append_output(f"Claude Code session ended (exit code: {exit_code})", "info")
        self.in_claude_session = False
        self.interactive_claude_session = None
        self.set_status("Claude Code session ended")
        self.update_prompt_for_normal_mode()
    
    def execute_external_command(self, command: str, args: List[str]):
        """外部コマンド実行"""
        self.set_status(f"Executing: {command}")
        
        try:
            # 前のプロセスが実行中の場合は停止
            if self.current_process:
                self.current_process.kill()
                self.current_process = None
            
            # 新しいプロセスを作成
            self.current_process = QProcess(self)
            self.current_process.setWorkingDirectory(self.working_directory)
            
            # シグナル接続
            self.current_process.readyReadStandardOutput.connect(self._on_stdout)
            self.current_process.readyReadStandardError.connect(self._on_stderr)
            self.current_process.finished.connect(self._on_finished)
            
            # プロセス開始
            self.current_process.start(command, args)
            
        except Exception as e:
            self.append_output(f"Failed to execute command: {str(e)}", "error")
            self.set_status("Command failed")
    
    def _on_stdout(self):
        """標準出力を処理"""
        if self.current_process:
            data = self.current_process.readAllStandardOutput().data().decode('utf-8', errors='ignore')
            self.append_output(data, "output")
    
    def _on_stderr(self):
        """標準エラーを処理"""
        if self.current_process:
            data = self.current_process.readAllStandardError().data().decode('utf-8', errors='ignore')
            self.append_output(data, "error")
    
    def _on_finished(self, exit_code):
        """プロセス完了時の処理"""
        self.set_status(f"Process completed (exit code: {exit_code})")
        self.command_executed.emit("process", exit_code)
        if self.current_process:
            self.current_process.deleteLater()
            self.current_process = None
    
    def _on_claude_stdout(self):
        """Claude Code標準出力を処理"""
        if self.current_process:
            data = self.current_process.readAllStandardOutput().data().decode('utf-8', errors='ignore')
            # Strudelコードの検出
            if 'strudel' in data.lower() or '$:' in data or 'sound(' in data:
                self.claude_code_generated.emit(data)
                self.append_output("🎵 Strudel code generated!", "success")
            self.append_output(data, "claude_output")
    
    def _on_claude_stderr(self):
        """Claude Code標準エラーを処理"""
        if self.current_process:
            data = self.current_process.readAllStandardError().data().decode('utf-8', errors='ignore')
            self.append_output(data, "error")
    
    def _on_claude_finished(self, exit_code):
        """Claude Code完了時の処理"""
        self.set_status("Claude Code completed")
        self.command_executed.emit("claude", exit_code)
        if self.current_process:
            self.current_process.deleteLater()
            self.current_process = None
    
    
    def change_directory(self, path: str):
        """ディレクトリ変更"""
        try:
            new_path = os.path.abspath(os.path.expanduser(path))
            if os.path.isdir(new_path):
                self.working_directory = new_path
                self.working_dir_label.setText(f"📁 {os.path.basename(new_path)}")
                self.append_output(f"Changed to: {new_path}", "success")
            else:
                self.append_output(f"Directory not found: {path}", "error")
        except Exception as e:
            self.append_output(f"Error changing directory: {str(e)}", "error")
    
    def show_help(self):
        """ヘルプ表示"""
        help_text = """
🖥️  PyDomino Terminal Help

Built-in Commands:
  help                    Show this help message
  clear                   Clear terminal output
  pwd                     Print working directory
  cd <path>               Change directory
  claude "prompt"         Generate code with Claude Code

External Commands:
  Any system command (ls, node, python, etc.)

Claude Code Examples:
  claude "Create a house beat in Strudel"
  claude "Generate a bassline pattern"
  claude "Make ambient music code"

Keyboard Shortcuts:
  Up/Down arrows         Navigate command history
  Tab                    Auto-completion
  Ctrl+C                 Copy selected text
        """
        self.append_output(help_text, "help")
    
    def clear_terminal(self):
        """ターミナルクリア"""
        self.output_area.clear()
        self.append_output("Terminal cleared", "system")
    
    def copy_selected_text(self):
        """選択テキストをコピー"""
        if self.output_area.textCursor().hasSelection():
            self.output_area.copy()
    
    def show_context_menu(self, position):
        """コンテキストメニュー表示"""
        self.context_menu.exec_(self.output_area.mapToGlobal(position))
    
    def prompt_claude_code(self):
        """Claude Codeプロンプト"""
        # 簡単なプロンプト入力ダイアログ（将来実装）
        self.command_input.setText('claude "')
        self.command_input.setFocus()
        cursor = self.command_input.textCursor()
        cursor.setPosition(len(self.command_input.text()) - 1)
        self.command_input.setTextCursor(cursor)
    
    def append_output(self, text: str, output_type: str = "normal"):
        """出力追加"""
        colors = {
            "normal": "#cccccc",
            "command": "#9cdcfe",
            "output": "#ffffff",
            "error": "#f48771",
            "success": "#4ec9b0",
            "info": "#dcdcaa",
            "system": "#569cd6",
            "help": "#ce9178",
            "claude_output": "#d4d4aa"
        }
        
        color = colors.get(output_type, colors["normal"])
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # ANSIコードを解析
        parsed_text = self.ansi_parser.parse_ansi(text)
        
        # HTMLフォーマット
        formatted = f'<span style="color: #6a9955;">[{timestamp}]</span> <span style="color: {color};">{parsed_text}</span>'
        
        # 出力に追加
        self.output_area.append(formatted)
        
        # 自動スクロール
        cursor = self.output_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.output_area.setTextCursor(cursor)
    
    def set_status(self, message: str):
        """ステータス設定"""
        self.status_label.setText(message)
    
    def apply_terminal_style(self):
        """ターミナルスタイル適用"""
        self.setStyleSheet("""
            QtTerminalWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QFrame {
                background-color: #252526;
                border: 1px solid #464647;
                border-radius: 4px;
            }
            QTextBrowser {
                background-color: #1e1e1e;
                color: #cccccc;
                border: 1px solid #464647;
                border-radius: 4px;
                padding: 8px;
                selection-background-color: #3e3e42;
            }
            QLineEdit {
                background-color: #2d2d30;
                color: #cccccc;
                border: 1px solid #464647;
                border-radius: 4px;
                padding: 6px;
                font-family: 'Monaco', 'Consolas', monospace;
            }
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:pressed {
                background-color: #0d5a8a;
            }
            QLabel {
                color: #cccccc;
                padding: 2px;
            }
            QProgressBar {
                border: 1px solid #464647;
                border-radius: 3px;
                text-align: center;
                background-color: #2d2d30;
            }
            QProgressBar::chunk {
                background-color: #4ec9b0;
                border-radius: 2px;
            }
        """)
    
    def closeEvent(self, event):
        """終了時の処理"""
        if self.current_process:
            self.current_process.terminate()
            self.current_process.waitForFinished(3000)
        
        if self.interactive_claude_session:
            self.interactive_claude_session.terminate()
            self.interactive_claude_session.waitForFinished(3000)
        
        super().closeEvent(event)