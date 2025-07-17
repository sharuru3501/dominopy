"""
JavaScript Terminal Widget for PyDomino (PROTOTYPE)
Provides a terminal-like interface for executing JavaScript code with Node.js
This is an experimental feature for live coding integration.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QPlainTextEdit, QTextEdit, QPushButton, 
                               QSplitter, QLabel, QFrame)
from PySide6.QtCore import Qt, QProcess, Signal, QTimer
from PySide6.QtGui import QFont, QTextCharFormat, QColor, QSyntaxHighlighter
import os
import tempfile
from datetime import datetime

class JavaScriptHighlighter(QSyntaxHighlighter):
    """Simple JavaScript syntax highlighter"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_highlighting_rules()
    
    def setup_highlighting_rules(self):
        """Set up basic syntax highlighting rules"""
        self.highlighting_rules = []
        
        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569cd6"))
        keyword_format.setFontWeight(QFont.Bold)
        
        keywords = ['function', 'var', 'let', 'const', 'if', 'else', 'for', 
                   'while', 'return', 'true', 'false', 'null', 'undefined',
                   'console']
        
        for keyword in keywords:
            pattern = f'\\b{keyword}\\b'
            self.highlighting_rules.append((pattern, keyword_format))
        
        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#ce9178"))
        self.highlighting_rules.append((r'"[^"]*"', string_format))
        self.highlighting_rules.append((r"'[^']*'", string_format))
        
        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6a9955"))
        self.highlighting_rules.append((r'//.*', comment_format))
    
    def highlightBlock(self, text):
        """Apply highlighting to text"""
        import re
        for pattern, format_obj in self.highlighting_rules:
            for match in re.finditer(pattern, text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, format_obj)

class JavaScriptTerminalWidget(QWidget):
    """
    PROTOTYPE: JavaScript Terminal Widget
    Simple terminal for executing JavaScript code using Node.js
    """
    
    # Signals
    code_executed = Signal(str, str)  # code, result
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.node_process = None
        self.temp_files = []
        
        self.init_ui()
        self.check_nodejs()
        
        # Cleanup timer
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self.cleanup_temp_files)
        self.cleanup_timer.start(30000)  # 30 seconds
    
    def init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header
        self.create_header(layout)
        
        # Main content
        self.create_main_content(layout)
        
        # Status bar
        self.create_status_bar(layout)
        
        # Apply styling
        self.apply_styling()
    
    def create_header(self, parent_layout):
        """Create header with title and controls"""
        header = QFrame()
        header.setFrameStyle(QFrame.StyledPanel)
        header_layout = QHBoxLayout(header)
        
        # Title
        title = QLabel("🖥️ JavaScript Terminal (Prototype)")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #4ec9b0;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Buttons
        self.run_button = QPushButton("▶ Run")
        self.run_button.clicked.connect(self.execute_code)
        self.run_button.setShortcut("Ctrl+Return")
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_output)
        
        header_layout.addWidget(self.run_button)
        header_layout.addWidget(self.clear_button)
        
        parent_layout.addWidget(header)
    
    def create_main_content(self, parent_layout):
        """Create main content area"""
        splitter = QSplitter(Qt.Horizontal)
        
        # Code editor
        self.create_code_editor(splitter)
        
        # Output area
        self.create_output_area(splitter)
        
        # Set proportions (60% code, 40% output)
        splitter.setSizes([600, 400])
        
        parent_layout.addWidget(splitter)
    
    def create_code_editor(self, parent):
        """Create code editor with syntax highlighting"""
        editor_frame = QFrame()
        editor_frame.setFrameStyle(QFrame.StyledPanel)
        editor_layout = QVBoxLayout(editor_frame)
        
        editor_layout.addWidget(QLabel("📝 Code"))
        
        self.code_editor = QPlainTextEdit()
        self.code_editor.setPlaceholderText(
            "// JavaScript Terminal - Type your code here\n"
            "console.log('Hello from PyDomino!');\n\n"
            "// Example:\n"
            "const notes = ['C', 'D', 'E', 'F'];\n"
            "console.log('Notes:', notes);"
        )
        
        # Set font
        font = QFont("Monaco", 12)  # macOS
        if not font.exactMatch():
            font = QFont("Consolas", 12)  # Windows
        if not font.exactMatch():
            font = QFont("monospace", 12)  # Fallback
        self.code_editor.setFont(font)
        
        # Add syntax highlighting
        self.highlighter = JavaScriptHighlighter(self.code_editor.document())
        
        editor_layout.addWidget(self.code_editor)
        parent.addWidget(editor_frame)
    
    def create_output_area(self, parent):
        """Create output display area"""
        output_frame = QFrame()
        output_frame.setFrameStyle(QFrame.StyledPanel)
        output_layout = QVBoxLayout(output_frame)
        
        output_layout.addWidget(QLabel("📤 Output"))
        
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setFont(self.code_editor.font())
        
        # Welcome message
        self.append_output("JavaScript Terminal ready! 🚀", "success")
        self.append_output("Type JavaScript code and press 'Run' or Ctrl+Enter", "info")
        
        output_layout.addWidget(self.output_display)
        parent.addWidget(output_frame)
    
    def create_status_bar(self, parent_layout):
        """Create status bar"""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel)
        status_layout = QHBoxLayout(status_frame)
        
        self.status_label = QLabel("Checking Node.js...")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        parent_layout.addWidget(status_frame)
    
    def apply_styling(self):
        """Apply dark terminal-like styling"""
        self.setStyleSheet("""
            JavaScriptTerminalWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QFrame {
                background-color: #252526;
                border: 1px solid #464647;
                border-radius: 4px;
            }
            QPlainTextEdit, QTextEdit {
                background-color: #1e1e1e;
                color: #cccccc;
                border: 1px solid #464647;
                border-radius: 4px;
                padding: 8px;
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
                padding: 4px;
            }
        """)
    
    def check_nodejs(self):
        """Check if Node.js is available"""
        try:
            process = QProcess()
            process.start("node", ["--version"])
            process.waitForFinished(3000)
            
            if process.exitCode() == 0:
                version = process.readAllStandardOutput().data().decode().strip()
                self.status_label.setText(f"Ready - Node.js {version} 🟢")
                self.append_output(f"Node.js {version} detected", "success")
            else:
                self.status_label.setText("Node.js not found 🔴")
                self.run_button.setEnabled(False)
                self.append_output("❌ Node.js not found. Please install Node.js to use this feature.", "error")
                
        except Exception as e:
            self.status_label.setText("Node.js error 🔴")
            self.run_button.setEnabled(False)
            self.append_output(f"❌ Error checking Node.js: {e}", "error")
    
    def execute_code(self):
        """Execute JavaScript code"""
        code = self.code_editor.toPlainText().strip()
        
        if not code:
            self.append_output("⚠️ No code to execute", "warning")
            return
        
        self.append_output("🔄 Executing...", "info")
        self._run_javascript(code)
    
    def _run_javascript(self, code):
        """Run JavaScript code using Node.js"""
        try:
            # Disable run button
            self.run_button.setEnabled(False)
            self.run_button.setText("⏳ Running...")
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(code)
                temp_file = f.name
                self.temp_files.append(temp_file)
            
            # Run Node.js
            self.node_process = QProcess(self)
            self.node_process.finished.connect(
                lambda: self._on_finished(temp_file)
            )
            self.node_process.start("node", [temp_file])
            
            # Timeout after 5 seconds
            QTimer.singleShot(5000, lambda: self._check_timeout(temp_file))
            
        except Exception as e:
            self.append_output(f"❌ Execution error: {e}", "error")
            self._reset_ui()
    
    def _on_finished(self, temp_file):
        """Handle process completion"""
        try:
            if self.node_process:
                stdout = self.node_process.readAllStandardOutput().data().decode()
                stderr = self.node_process.readAllStandardError().data().decode()
                exit_code = self.node_process.exitCode()
                
                if stdout.strip():
                    self.append_output(stdout.strip(), "output")
                
                if stderr.strip():
                    self.append_output(stderr.strip(), "error")
                
                if exit_code == 0:
                    self.append_output("✅ Completed", "success")
                    self.code_executed.emit(self.code_editor.toPlainText(), stdout)
                else:
                    self.append_output(f"❌ Failed (exit code: {exit_code})", "error")
                
        except Exception as e:
            self.append_output(f"❌ Error: {e}", "error")
        finally:
            self._cleanup_execution(temp_file)
    
    def _check_timeout(self, temp_file):
        """Check for execution timeout"""
        if self.node_process and self.node_process.state() == QProcess.Running:
            self.append_output("⏰ Timeout (5 seconds)", "warning")
            self.node_process.kill()
            self._cleanup_execution(temp_file)
    
    def _cleanup_execution(self, temp_file):
        """Clean up after execution"""
        self._reset_ui()
        
        # Remove temp file
        try:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            if temp_file in self.temp_files:
                self.temp_files.remove(temp_file)
        except:
            pass
    
    def _reset_ui(self):
        """Reset UI state"""
        self.run_button.setEnabled(True)
        self.run_button.setText("▶ Run")
        
        if self.node_process:
            self.node_process.deleteLater()
            self.node_process = None
    
    def append_output(self, text, output_type="normal"):
        """Append formatted output"""
        colors = {
            "normal": "#cccccc",
            "output": "#ffffff", 
            "error": "#f48771",
            "warning": "#dcdcaa",
            "success": "#4ec9b0",
            "info": "#9cdcfe"
        }
        
        color = colors.get(output_type, colors["normal"])
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        formatted = f'<span style="color: #6a9955;">[{timestamp}]</span> <span style="color: {color};">{text}</span>'
        self.output_display.append(formatted)
        
        # Auto-scroll
        cursor = self.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.output_display.setTextCursor(cursor)
    
    def clear_output(self):
        """Clear output display"""
        self.output_display.clear()
        self.append_output("Output cleared", "success")
    
    def cleanup_temp_files(self):
        """Clean up old temporary files"""
        for temp_file in self.temp_files[:]:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                self.temp_files.remove(temp_file)
            except:
                continue
    
    def closeEvent(self, event):
        """Clean up on close"""
        # Clean up temp files
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
        
        # Kill process
        if self.node_process and self.node_process.state() == QProcess.Running:
            self.node_process.kill()
        
        super().closeEvent(event)