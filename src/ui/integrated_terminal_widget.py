"""
PyDomino統合ターミナルウィジェット (完全独自実装)
エディタ統合型マルチシェル対応ターミナル
"""

import os
import sys
import pty
import select
import signal
import subprocess
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QTextEdit, QComboBox, QPushButton, 
                               QTabWidget, QLabel, QFrame, QSplitter,
                               QMessageBox, QProgressBar)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QProcess, QSize
from PySide6.QtGui import (QFont, QColor, QTextCursor, QTextCharFormat,
                          QKeySequence, QAction, QIcon, QPalette)
import re

class ANSIProcessor:
    """ANSIエスケープシーケンス処理クラス"""
    
    def __init__(self):
        # ANSI色コードマップ
        self.color_map = {
            '30': '#000000',  # 黒
            '31': '#ff0000',  # 赤
            '32': '#00ff00',  # 緑
            '33': '#ffff00',  # 黄
            '34': '#0000ff',  # 青
            '35': '#ff00ff',  # マゼンタ
            '36': '#00ffff',  # シアン
            '37': '#ffffff',  # 白
            '90': '#808080',  # 明るい黒
            '91': '#ff8080',  # 明るい赤
            '92': '#80ff80',  # 明るい緑
            '93': '#ffff80',  # 明るい黄
            '94': '#8080ff',  # 明るい青
            '95': '#ff80ff',  # 明るいマゼンタ
            '96': '#80ffff',  # 明るいシアン
            '97': '#ffffff',  # 明るい白
        }
        
        # 背景色コードマップ
        self.bg_color_map = {
            '40': '#000000',  # 背景黒
            '41': '#800000',  # 背景赤
            '42': '#008000',  # 背景緑
            '43': '#808000',  # 背景黄
            '44': '#000080',  # 背景青
            '45': '#800080',  # 背景マゼンタ
            '46': '#008080',  # 背景シアン
            '47': '#c0c0c0',  # 背景白
        }
    
    def process_ansi(self, text: str) -> str:
        """ANSIエスケープシーケンスをHTMLに変換"""
        # まずエスケープシーケンスを処理
        text = self._convert_ansi_to_html(text)
        
        # それから制御文字をクリーンアップ
        text = self._clean_control_chars(text)
        
        return text
    
    def _clean_control_chars(self, text: str) -> str:
        """制御文字をクリーンアップ"""
        # 表示可能文字、改行、タブ以外を除去
        cleaned = ''
        i = 0
        while i < len(text):
            char = text[i]
            if char.isprintable() or char in ['\n', '\r', '\t']:
                cleaned += char
            elif ord(char) == 8:  # バックスペース
                if cleaned:
                    cleaned = cleaned[:-1]
            elif ord(char) == 13:  # キャリッジリターン
                # 行の先頭に戻る（上書き）
                last_newline = cleaned.rfind('\n')
                if last_newline != -1:
                    cleaned = cleaned[:last_newline + 1]
                else:
                    cleaned = ''
            # その他の制御文字は無視
            i += 1
        return cleaned
    
    def _convert_ansi_to_html(self, text: str) -> str:
        """ANSIエスケープシーケンスをHTMLに変換"""
        
        # まず最も問題のあるOSCシーケンスを除去
        # OSC 7 (Working Directory) sequences - ターミナル統合用
        text = re.sub(r'\x1b\]7;[^\x07\x1b]*[\x07]', '', text)  # OSC 7 with BEL termination
        text = re.sub(r'\x1b\]7;[^\x1b]*\x1b\\', '', text)  # OSC 7 with ST termination
        
        # 他のOSCシーケンスも除去
        text = re.sub(r'\x1b\][0-9]*;[^\x07\x1b]*[\x07]', '', text)  # OSC with BEL
        text = re.sub(r'\x1b\][0-9]*;[^\x1b]*\x1b\\', '', text)  # OSC with ST
        
        # DEC Private Mode sequences (bracketed paste mode など)
        text = re.sub(r'\x1b\[\?[0-9]+[hl]', '', text)  # DEC private mode set/reset
        text = re.sub(r'\x1b\[\?[0-9]+[;0-9]*[hl]', '', text)  # Multiple DEC modes
        
        # Application/Normal keypad modes
        text = re.sub(r'\x1b=', '', text)  # Set application keypad mode
        text = re.sub(r'\x1b>', '', text)  # Set numeric keypad mode
        
        # 色付きエスケープシーケンス（例: \x1b[31m）の処理
        color_pattern = r'\x1b\[([0-9;]*)m'
        
        def replace_color(match):
            codes = match.group(1).split(';') if match.group(1) else ['0']
            html = ''
            
            for code in codes:
                if code == '0' or code == '':  # リセット
                    html += '</span>'
                elif code == '1':  # 太字
                    html += '<span style="font-weight: bold;">'
                elif code == '7':  # 反転表示
                    html += '<span style="background-color: #cccccc; color: #000000;">'
                elif code == '27':  # 反転表示解除
                    html += '</span>'
                elif code == '24':  # 下線解除
                    html += '</span>'
                elif code in self.color_map:  # 前景色
                    color = self.color_map[code]
                    html += f'<span style="color: {color};">'
                elif code in self.bg_color_map:  # 背景色
                    bg_color = self.bg_color_map[code]
                    html += f'<span style="background-color: {bg_color};">'
            
            return html
        
        # 色コードを変換
        text = re.sub(color_pattern, replace_color, text)
        
        # カーソル制御シーケンス
        text = re.sub(r'\x1b\[[0-9]*[ABCD]', '', text)  # カーソル移動（上下左右）
        text = re.sub(r'\x1b\[\d+;\d+[Hf]', '', text)  # カーソル位置設定
        text = re.sub(r'\x1b\[[0-9]*[HF]', '', text)  # カーソル位置設定（行のみ）
        text = re.sub(r'\x1b\[s', '', text)  # カーソル位置保存
        text = re.sub(r'\x1b\[u', '', text)  # カーソル位置復元
        
        # 画面制御シーケンス
        text = re.sub(r'\x1b\[[0-9]*[JK]', '', text)  # 画面クリア、行クリア
        text = re.sub(r'\x1b\[[0-9]*X', '', text)  # 文字消去
        text = re.sub(r'\x1b\[[0-9]*P', '', text)  # 文字削除
        text = re.sub(r'\x1b\[[0-9]*@', '', text)  # 文字挿入
        text = re.sub(r'\x1b\[[0-9]*L', '', text)  # 行挿入
        text = re.sub(r'\x1b\[[0-9]*M', '', text)  # 行削除
        
        # VT100エスケープシーケンス
        text = re.sub(r'\x1b\[c', '', text)  # デバイス属性要求
        text = re.sub(r'\x1b\[\d*n', '', text)  # ステータス報告
        
        # 残りの未処理エスケープシーケンス（万能パターン）
        text = re.sub(r'\x1b\[[!-~]*[a-zA-Z]', '', text)  # CSI sequences
        text = re.sub(r'\x1b[P-_][!-~]*\x1b\\', '', text)  # DCS sequences
        text = re.sub(r'\x1b[^\x1b]*', '', text)  # その他のエスケープシーケンス
        
        # Unicode box drawing characters の正規化（Claude用）
        box_chars = {
            '╭': '┌', '╮': '┐', '╯': '┘', '╰': '└',
            '│': '│', '─': '─', '╱': '/', '╲': '\\'
        }
        for old, new in box_chars.items():
            text = text.replace(old, new)
        
        # 改行文字をHTMLブレークに変換
        text = text.replace('\n', '<br>')
        text = text.replace('\r\n', '<br>')  # Windows改行対応
        text = text.replace('\r', '')  # キャリッジリターンのみは除去
        
        # 連続する改行を正規化
        text = re.sub(r'(<br>){3,}', '<br><br>', text)  # 3つ以上の連続改行を2つに
        
        # 開いたspanタグを閉じる
        open_spans = text.count('<span') - text.count('</span>')
        text += '</span>' * max(0, open_spans)
        
        return text

class ShellProcess(QThread):
    """シェルプロセス管理クラス"""
    
    output_ready = Signal(str)
    process_finished = Signal(int)
    
    def __init__(self, shell_command: str, working_dir: str = None):
        super().__init__()
        self.shell_command = shell_command
        self.working_dir = working_dir or os.getcwd()
        self.master_fd = None
        self.slave_fd = None
        self.pid = None
        self.running = False
        
    def run(self):
        """シェルプロセスを開始"""
        try:
            # 疑似端末を作成
            self.master_fd, self.slave_fd = pty.openpty()
            
            # 子プロセスを作成
            self.pid = os.fork()
            
            if self.pid == 0:
                # 子プロセス側
                os.close(self.master_fd)
                os.setsid()
                os.dup2(self.slave_fd, 0)  # stdin
                os.dup2(self.slave_fd, 1)  # stdout
                os.dup2(self.slave_fd, 2)  # stderr
                os.close(self.slave_fd)
                
                # 作業ディレクトリを設定
                os.chdir(self.working_dir)
                
                # シェルを実行
                os.execvp(self.shell_command, [self.shell_command])
                
            else:
                # 親プロセス側
                os.close(self.slave_fd)
                self.running = True
                
                # ターミナルサイズを設定（デフォルト: 24行 x 80列）
                self.resize_terminal(24, 80)
                
                # 出力を継続監視
                while self.running:
                    try:
                        ready, _, _ = select.select([self.master_fd], [], [], 0.1)
                        if ready:
                            data = os.read(self.master_fd, 1024)
                            if data:
                                try:
                                    output = data.decode('utf-8', errors='replace')
                                    self.output_ready.emit(output)
                                except UnicodeDecodeError:
                                    # バイナリデータの場合は無視
                                    pass
                            else:
                                break
                    except (OSError, ValueError):
                        break
                
                # プロセス終了処理
                try:
                    _, status = os.waitpid(self.pid, os.WNOHANG)
                    exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
                    self.process_finished.emit(exit_code)
                except OSError:
                    self.process_finished.emit(-1)
                    
        except Exception as e:
            print(f"Shell process error: {e}")
            self.process_finished.emit(-1)
    
    def send_input(self, data: str):
        """入力をシェルに送信"""
        if self.master_fd and self.running:
            try:
                encoded_data = data.encode('utf-8', errors='replace')
                os.write(self.master_fd, encoded_data)
            except (OSError, UnicodeEncodeError):
                pass
    
    def resize_terminal(self, rows: int, cols: int):
        """ターミナルサイズを変更"""
        if self.master_fd and self.running:
            try:
                import fcntl
                import termios
                import struct
                
                # サイズ変更
                s = struct.pack('HHHH', rows, cols, 0, 0)
                fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, s)
                
                # SIGWINCH送信
                if self.pid:
                    os.kill(self.pid, signal.SIGWINCH)
            except (ImportError, OSError):
                pass
    
    def stop_process(self):
        """プロセスを停止"""
        self.running = False
        if self.pid:
            try:
                # まずSIGTERMで優雅な終了を試行
                os.kill(self.pid, signal.SIGTERM)
                
                # 3秒待機
                import time
                for _ in range(30):  # 3秒間待機
                    try:
                        pid, status = os.waitpid(self.pid, os.WNOHANG)
                        if pid != 0:
                            break
                    except OSError:
                        break
                    time.sleep(0.1)
                else:
                    # まだ動いている場合は強制終了
                    try:
                        os.kill(self.pid, signal.SIGKILL)
                    except OSError:
                        pass
            except OSError:
                pass
        
        if self.master_fd:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
        
        # スレッド終了の確保
        if self.isRunning():
            self.quit()
            if not self.wait(3000):  # 3秒待機
                self.terminate()

class TerminalPane(QWidget):
    """単一ターミナルペイン"""
    
    def __init__(self, shell_name: str, shell_command: str, working_dir: str = None):
        super().__init__()
        self.shell_name = shell_name
        self.shell_command = shell_command
        self.working_dir = working_dir or os.getcwd()
        self.shell_process = None
        self.ansi_processor = ANSIProcessor()
        
        self.init_ui()
        self.start_shell()
    
    def init_ui(self):
        """UI初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # ターミナル表示
        self.terminal_view = QTextEdit()
        self.terminal_view.setAcceptRichText(True)  # HTMLを有効に
        self.terminal_view.setReadOnly(True)  # 読み取り専用に設定（重要！）
        self.terminal_view.setLineWrapMode(QTextEdit.NoWrap)
        self.terminal_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.terminal_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # ターミナルフォント
        terminal_font = QFont("Monaco", 12)
        if not terminal_font.exactMatch():
            terminal_font = QFont("Consolas", 12)
        if not terminal_font.exactMatch():
            terminal_font = QFont("monospace", 12)
        
        self.terminal_view.setFont(terminal_font)
        
        # キー入力処理 - カスタムQTextEditでオーバーライド
        self.terminal_view.installEventFilter(self)
        
        layout.addWidget(self.terminal_view)
        
        # ターミナル風スタイル
        self.apply_terminal_style()
    
    def apply_terminal_style(self):
        """ターミナルスタイルを適用"""
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #cccccc;
                border: none;
                selection-background-color: #264f78;
                font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
            }
        """)
    
    def start_shell(self):
        """シェルを開始"""
        try:
            self.shell_process = ShellProcess(self.shell_command, self.working_dir)
            self.shell_process.output_ready.connect(self.on_output_received)
            self.shell_process.process_finished.connect(self.on_process_ended)
            self.shell_process.start()
            
            # 開始メッセージ
            self.add_output(f"🖥️  {self.shell_name} terminal started<br>")
            
        except Exception as e:
            self.add_output(f"Failed to start {self.shell_name}: {str(e)}<br>")
    
    def eventFilter(self, obj, event):
        """イベントフィルター - キー入力を処理"""
        if obj == self.terminal_view and event.type() == event.Type.KeyPress:
            return self.handle_key_input(event)
        return super().eventFilter(obj, event)
    
    def handle_key_input(self, event):
        """キー入力処理"""
        if not self.shell_process or not self.shell_process.running:
            return False  # 標準処理に委ねる
        
        key = event.key()
        modifiers = event.modifiers()
        text = event.text()
        
        # 特殊キー処理
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            self.shell_process.send_input('\r')
            return True  # イベントを消費
        elif key == Qt.Key_Backspace:
            self.shell_process.send_input('\x7f')
            return True
        elif key == Qt.Key_Tab:
            self.shell_process.send_input('\t')
            return True
        elif key == Qt.Key_Escape:
            self.shell_process.send_input('\x1b')
            return True
        elif modifiers & Qt.ControlModifier:
            # Ctrl+キー処理
            if key == Qt.Key_C:
                self.shell_process.send_input('\x03')  # Ctrl+C
                return True
            elif key == Qt.Key_D:
                self.shell_process.send_input('\x04')  # Ctrl+D
                return True
            elif key == Qt.Key_Z:
                self.shell_process.send_input('\x1a')  # Ctrl+Z
                return True
            elif key == Qt.Key_L:
                self.shell_process.send_input('\x0c')  # Ctrl+L
                return True
        elif key == Qt.Key_Up:
            self.shell_process.send_input('\x1b[A')  # 上矢印
            return True
        elif key == Qt.Key_Down:
            self.shell_process.send_input('\x1b[B')  # 下矢印
            return True
        elif key == Qt.Key_Right:
            self.shell_process.send_input('\x1b[C')  # 右矢印
            return True
        elif key == Qt.Key_Left:
            self.shell_process.send_input('\x1b[D')  # 左矢印
            return True
        elif text and text.isprintable():
            # 印刷可能な文字のみ
            self.shell_process.send_input(text)
            return True
        
        # 処理しないキーは標準処理に委ねる
        return False
    
    def on_output_received(self, output: str):
        """出力受信処理"""
        # ANSIエスケープシーケンスを処理
        processed_output = self.ansi_processor.process_ansi(output)
        self.add_output(processed_output)
    
    def on_process_ended(self, exit_code: int):
        """プロセス終了処理"""
        self.add_output(f"<br>🔴 {self.shell_name} process ended (exit code: {exit_code})<br>")
        self.shell_process = None
    
    def add_output(self, text: str):
        """出力をターミナルに追加"""
        cursor = self.terminal_view.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # HTMLとして挿入
        if '<span' in text or '</span>' in text:
            cursor.insertHtml(text)
        else:
            # 改行を<br>に変換
            text = text.replace('\n', '<br>')
            cursor.insertHtml(text)
        
        self.terminal_view.setTextCursor(cursor)
        
        # 自動スクロール
        scrollbar = self.terminal_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_terminal(self):
        """ターミナルをクリア"""
        self.terminal_view.clear()
    
    def get_shell_name(self) -> str:
        """シェル名を取得"""
        return self.shell_name
    
    def closeEvent(self, event):
        """終了時処理"""
        if self.shell_process:
            # シグナル切断
            try:
                self.shell_process.output_ready.disconnect()
                self.shell_process.process_finished.disconnect()
            except:
                pass
            
            if self.shell_process.running:
                self.shell_process.stop_process()
                self.shell_process.wait(3000)
        super().closeEvent(event)

class IntegratedTerminalWidget(QWidget):
    """PyDomino統合ターミナルウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 利用可能シェル検出
        self.available_shells = self.detect_shells()
        self.terminal_panes = []
        self.current_terminal = None
        
        self.init_ui()
        self.create_default_terminal()
    
    def detect_shells(self) -> Dict[str, str]:
        """利用可能なシェルを検出"""
        shells = {}
        
        # 1. /etc/shellsから検出（Unix系）
        if os.path.exists('/etc/shells'):
            try:
                with open('/etc/shells', 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and os.path.exists(line):
                            shell_name = os.path.basename(line)
                            if shell_name not in shells:
                                shells[shell_name] = line
            except (IOError, OSError):
                pass
        
        # 2. PATH環境変数から一般的なシェルを検索
        shell_names = ['zsh', 'bash', 'fish', 'tcsh', 'csh', 'ksh', 'dash', 'mksh', 'ash', 'sh']
        if sys.platform == 'win32':
            shell_names.extend(['powershell', 'pwsh', 'cmd'])
        
        path_env = os.environ.get('PATH', '')
        if path_env:
            for path_dir in path_env.split(os.pathsep):
                if not path_dir:
                    continue
                for shell_name in shell_names:
                    if shell_name in shells:
                        continue
                    
                    shell_executable = shell_name
                    if sys.platform == 'win32' and not shell_name.endswith('.exe'):
                        shell_executable += '.exe'
                    
                    shell_path = os.path.join(path_dir, shell_executable)
                    if os.path.isfile(shell_path) and os.access(shell_path, os.X_OK):
                        shells[shell_name] = shell_path
        
        # 3. 固定パスでの追加検索（フォールバック）
        shell_candidates = {
            'zsh': ['/bin/zsh', '/usr/bin/zsh', '/usr/local/bin/zsh'],
            'bash': ['/bin/bash', '/usr/bin/bash', '/usr/local/bin/bash'],
            'fish': ['/usr/local/bin/fish', '/opt/homebrew/bin/fish', '/usr/bin/fish'],
            'tcsh': ['/bin/tcsh', '/usr/bin/tcsh'],
            'csh': ['/bin/csh', '/usr/bin/csh'],
            'ksh': ['/bin/ksh', '/usr/bin/ksh'],
            'dash': ['/bin/dash', '/usr/bin/dash'],
            'mksh': ['/bin/mksh', '/usr/bin/mksh'],
            'ash': ['/bin/ash', '/usr/bin/ash'],
            'sh': ['/bin/sh', '/usr/bin/sh']
        }
        
        if sys.platform == 'win32':
            shell_candidates.update({
                'powershell': ['powershell.exe', 'pwsh.exe'],
                'cmd': ['cmd.exe']
            })
        
        for shell_name, paths in shell_candidates.items():
            if shell_name in shells:
                continue
            for path in paths:
                if os.path.exists(path):
                    shells[shell_name] = path
                    break
        
        return shells
    
    def init_ui(self):
        """UI初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # 上部ツールバー
        self.create_toolbar(layout)
        
        # タブ式ターミナル
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_terminal)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        layout.addWidget(self.tab_widget)
        
        # 下部ステータス
        self.create_status_bar(layout)
        
        # スタイル適用
        self.apply_integrated_style()
    
    def create_toolbar(self, parent_layout):
        """ツールバー作成"""
        toolbar_frame = QFrame()
        toolbar_layout = QHBoxLayout(toolbar_frame)
        
        # タイトル
        title_label = QLabel("🖥️ PyDomino Terminal")
        title_label.setStyleSheet("font-weight: bold; color: #cccccc;")
        toolbar_layout.addWidget(title_label)
        
        toolbar_layout.addStretch()
        
        # シェル選択
        self.shell_selector = QComboBox()
        self.shell_selector.addItems(list(self.available_shells.keys()))
        self.shell_selector.setMinimumWidth(120)  # 最小幅を設定
        self.shell_selector.setSizeAdjustPolicy(QComboBox.AdjustToContents)  # コンテンツに合わせて調整
        default_shell = 'zsh' if 'zsh' in self.available_shells else 'bash'
        self.shell_selector.setCurrentText(default_shell)
        toolbar_layout.addWidget(QLabel("Shell:"))
        toolbar_layout.addWidget(self.shell_selector)
        
        # 新規ターミナル
        new_btn = QPushButton("+ New")
        new_btn.clicked.connect(self.create_new_terminal)
        toolbar_layout.addWidget(new_btn)
        
        # 分割表示
        split_btn = QPushButton("Split")
        split_btn.clicked.connect(self.split_terminal)
        toolbar_layout.addWidget(split_btn)
        
        # クリア
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_current_terminal)
        toolbar_layout.addWidget(clear_btn)
        
        parent_layout.addWidget(toolbar_frame)
    
    def create_status_bar(self, parent_layout):
        """ステータスバー作成"""
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #cccccc;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        # アクティブターミナル表示
        self.active_info = QLabel("No active terminal")
        self.active_info.setStyleSheet("color: #9cdcfe;")
        status_layout.addWidget(self.active_info)
        
        parent_layout.addWidget(status_frame)
    
    def apply_integrated_style(self):
        """統合スタイルを適用"""
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #cccccc;
            }
            QFrame {
                background-color: #252526;
                border: 1px solid #464647;
                border-radius: 4px;
            }
            QTabWidget::pane {
                border: 1px solid #464647;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d30;
                color: #cccccc;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #ffffff;
                border-bottom: 2px solid #4ec9b0;
            }
            QTabBar::tab:hover {
                background-color: #3c3c3c;
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
            QComboBox {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #464647;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QLabel {
                color: #cccccc;
                padding: 4px;
            }
        """)
    
    def create_default_terminal(self):
        """デフォルトターミナル作成"""
        self.create_new_terminal()
    
    def create_new_terminal(self):
        """新しいターミナル作成"""
        selected_shell = self.shell_selector.currentText()
        shell_command = self.available_shells.get(selected_shell)
        
        if not shell_command:
            QMessageBox.warning(self, "Error", f"Shell '{selected_shell}' not available")
            return
        
        # ターミナルペイン作成
        terminal = TerminalPane(selected_shell, shell_command)
        
        # タブに追加
        tab_index = self.tab_widget.addTab(terminal, f"{selected_shell} #{len(self.terminal_panes) + 1}")
        self.tab_widget.setCurrentIndex(tab_index)
        
        # リストに追加
        self.terminal_panes.append(terminal)
        self.current_terminal = terminal
        
        # ステータス更新
        self.update_status()
    
    def split_terminal(self):
        """ターミナル分割（新規作成）"""
        self.create_new_terminal()
    
    def clear_current_terminal(self):
        """現在のターミナルをクリア"""
        if self.current_terminal:
            self.current_terminal.clear_terminal()
    
    def close_terminal(self, tab_index: int):
        """ターミナルを閉じる"""
        if 0 <= tab_index < len(self.terminal_panes):
            terminal = self.terminal_panes[tab_index]
            
            # プロセス終了
            if terminal.shell_process and terminal.shell_process.running:
                terminal.shell_process.stop_process()
            
            # タブ削除
            self.tab_widget.removeTab(tab_index)
            self.terminal_panes.pop(tab_index)
            
            # 現在のターミナル更新
            current_index = self.tab_widget.currentIndex()
            if current_index >= 0 and current_index < len(self.terminal_panes):
                self.current_terminal = self.terminal_panes[current_index]
            else:
                self.current_terminal = None
            
            # ステータス更新
            self.update_status()
            
            # 最後のターミナルが閉じられた場合
            if not self.terminal_panes:
                self.create_new_terminal()
    
    def on_tab_changed(self, index: int):
        """タブ変更処理"""
        if 0 <= index < len(self.terminal_panes):
            self.current_terminal = self.terminal_panes[index]
            self.update_status()
    
    def update_status(self):
        """ステータス更新"""
        if self.current_terminal:
            shell_name = self.current_terminal.get_shell_name()
            self.active_info.setText(f"Active: {shell_name}")
            self.status_label.setText(f"Terminal ready ({len(self.terminal_panes)} active)")
        else:
            self.active_info.setText("No active terminal")
            self.status_label.setText("No terminals")
    
    def closeEvent(self, event):
        """終了時処理"""
        print("🧹 Cleaning up integrated terminal...")
        
        try:
            # すべてのターミナルプロセスを停止
            for terminal in self.terminal_panes:
                if terminal.shell_process and terminal.shell_process.running:
                    # シグナル切断
                    try:
                        terminal.shell_process.output_ready.disconnect()
                        terminal.shell_process.process_finished.disconnect()
                    except:
                        pass
                    terminal.shell_process.stop_process()
            
            # プロセス終了を待機
            for terminal in self.terminal_panes:
                if terminal.shell_process:
                    terminal.shell_process.wait(3000)
            
            # リソースクリーンアップ
            self.terminal_panes.clear()
            self.current_terminal = None
            
            print("✅ Integrated terminal cleanup completed")
        except Exception as e:
            print(f"Error during terminal cleanup: {e}")
        
        super().closeEvent(event)