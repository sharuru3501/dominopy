"""
Terminal Dock Widget for PyDomino (PROTOTYPE)
Provides flexible docking functionality for the JavaScript terminal.
"""

from PySide6.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
                               QTabWidget, QPushButton, QLabel, QFrame,
                               QMainWindow)
from PySide6.QtCore import Qt, Signal, QSettings
from .javascript_terminal_widget import JavaScriptTerminalWidget

class TerminalDockWidget(QDockWidget):
    """
    PROTOTYPE: Dockable terminal widget with flexible positioning
    """
    
    # Signals
    layout_changed = Signal(str)  # layout_type
    terminal_toggled = Signal(bool)  # visible
    
    def __init__(self, parent=None):
        super().__init__("Code Terminal (Prototype)", parent)
        
        self.main_window = parent
        self.terminal_widget = None
        self.settings = QSettings("PyDomino", "TerminalDock")
        
        self.init_dock()
        self.setup_terminal()
        self.restore_settings()
    
    def init_dock(self):
        """Initialize dock widget properties"""
        # Allow docking on multiple sides
        self.setAllowedAreas(
            Qt.RightDockWidgetArea | 
            Qt.BottomDockWidgetArea |
            Qt.LeftDockWidgetArea
        )
        
        # Enable floating
        self.setFeatures(
            QDockWidget.DockWidgetClosable |
            QDockWidget.DockWidgetMovable |
            QDockWidget.DockWidgetFloatable
        )
        
        # Connect signals
        self.dockLocationChanged.connect(self._on_dock_location_changed)
        self.topLevelChanged.connect(self._on_floating_changed)
        self.visibilityChanged.connect(self._on_visibility_changed)
    
    def setup_terminal(self):
        """Set up the terminal widget with controls"""
        # Main container
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Control bar
        self.create_control_bar(layout)
        
        # Terminal widget
        self.terminal_widget = JavaScriptTerminalWidget()
        layout.addWidget(self.terminal_widget)
        
        # Set as dock widget
        self.setWidget(container)
        
        # Connect terminal signals
        self.terminal_widget.code_executed.connect(self._on_code_executed)
    
    def create_control_bar(self, parent_layout):
        """Create control bar with positioning options"""
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.StyledPanel)
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(4, 4, 4, 4)
        
        # Position label
        self.position_label = QLabel("📍 Position:")
        control_layout.addWidget(self.position_label)
        
        # Position buttons
        self.right_button = QPushButton("→ Right")
        self.right_button.clicked.connect(lambda: self.set_dock_position("right"))
        self.right_button.setCheckable(True)
        
        self.bottom_button = QPushButton("↓ Bottom")
        self.bottom_button.clicked.connect(lambda: self.set_dock_position("bottom"))
        self.bottom_button.setCheckable(True)
        
        self.float_button = QPushButton("🪟 Float")
        self.float_button.clicked.connect(lambda: self.set_dock_position("float"))
        self.float_button.setCheckable(True)
        
        self.tab_button = QPushButton("📂 Tab")
        self.tab_button.clicked.connect(lambda: self.set_dock_position("tab"))
        self.tab_button.setCheckable(True)
        
        control_layout.addWidget(self.right_button)
        control_layout.addWidget(self.bottom_button)
        control_layout.addWidget(self.float_button)
        control_layout.addWidget(self.tab_button)
        
        control_layout.addStretch()
        
        # Hide/Show toggle
        self.toggle_button = QPushButton("🙈 Hide")
        self.toggle_button.clicked.connect(self.toggle_visibility)
        control_layout.addWidget(self.toggle_button)
        
        parent_layout.addWidget(control_frame)
        
        # Style the control bar
        control_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d30;
                border: 1px solid #464647;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #464647;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #4c4c4c;
            }
            QPushButton:checked {
                background-color: #4ec9b0;
                color: #1e1e1e;
                font-weight: bold;
            }
            QLabel {
                color: #cccccc;
                font-weight: bold;
            }
        """)
    
    def set_dock_position(self, position):
        """Set dock position and update UI"""
        if not self.main_window:
            return
        
        # Reset all button states
        self.right_button.setChecked(False)
        self.bottom_button.setChecked(False)
        self.float_button.setChecked(False)
        self.tab_button.setChecked(False)
        
        if position == "right":
            self.setFloating(False)
            self.main_window.addDockWidget(Qt.RightDockWidgetArea, self)
            self.right_button.setChecked(True)
            
        elif position == "bottom":
            self.setFloating(False)
            self.main_window.addDockWidget(Qt.BottomDockWidgetArea, self)
            self.bottom_button.setChecked(True)
            
        elif position == "float":
            self.setFloating(True)
            self.float_button.setChecked(True)
            
        elif position == "tab":
            # Tab integration (simplified for prototype)
            self.setFloating(False)
            self.main_window.addDockWidget(Qt.BottomDockWidgetArea, self)
            self.tab_button.setChecked(True)
            # Note: Full tab integration would require modification to main window
        
        self.layout_changed.emit(position)
        self.save_settings()
        
        # Update terminal output
        if self.terminal_widget:
            self.terminal_widget.append_output(f"Position changed to {position}", "info")
    
    def toggle_visibility(self):
        """Toggle terminal visibility"""
        if self.isVisible():
            self.hide()
            self.toggle_button.setText("👁 Show")
        else:
            self.show()
            self.toggle_button.setText("🙈 Hide")
        
        self.terminal_toggled.emit(self.isVisible())
    
    def _on_dock_location_changed(self, area):
        """Handle dock location change"""
        area_names = {
            Qt.LeftDockWidgetArea: "left",
            Qt.RightDockWidgetArea: "right",
            Qt.TopDockWidgetArea: "top",
            Qt.BottomDockWidgetArea: "bottom"
        }
        
        area_name = area_names.get(area, "unknown")
        
        # Update button states
        self.right_button.setChecked(area == Qt.RightDockWidgetArea)
        self.bottom_button.setChecked(area == Qt.BottomDockWidgetArea)
        self.float_button.setChecked(False)
        
        self.layout_changed.emit(area_name)
        self.save_settings()
    
    def _on_floating_changed(self, floating):
        """Handle floating state change"""
        self.float_button.setChecked(floating)
        
        if floating:
            self.right_button.setChecked(False)
            self.bottom_button.setChecked(False)
            self.tab_button.setChecked(False)
            self.layout_changed.emit("float")
        
        self.save_settings()
    
    def _on_visibility_changed(self, visible):
        """Handle visibility change"""
        self.toggle_button.setText("🙈 Hide" if visible else "👁 Show")
        self.terminal_toggled.emit(visible)
    
    def _on_code_executed(self, code, result):
        """Handle code execution from terminal"""
        # This could be connected to PyDomino's main functionality
        # For now, just emit a signal or log
        print(f"Terminal executed code: {len(code)} characters")
    
    def save_settings(self):
        """Save dock settings"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("floating", self.isFloating())
        
        if not self.isFloating() and self.main_window:
            # Save dock area
            for area in [Qt.LeftDockWidgetArea, Qt.RightDockWidgetArea, 
                        Qt.TopDockWidgetArea, Qt.BottomDockWidgetArea]:
                if self.main_window.dockWidgetArea(self) == area:
                    self.settings.setValue("dock_area", area.value)
                    break
    
    def restore_settings(self):
        """Restore dock settings"""
        # Restore geometry
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # Restore floating state
        floating = self.settings.value("floating", False, type=bool)
        if floating:
            self.setFloating(True)
            self.float_button.setChecked(True)
        else:
            # Restore dock area
            dock_area = self.settings.value("dock_area", Qt.RightDockWidgetArea.value, type=int)
            if self.main_window:
                self.main_window.addDockWidget(Qt.DockWidgetArea(dock_area), self)
                
                # Update button states
                if dock_area == Qt.RightDockWidgetArea.value:
                    self.right_button.setChecked(True)
                elif dock_area == Qt.BottomDockWidgetArea.value:
                    self.bottom_button.setChecked(True)
    
    def get_terminal_widget(self):
        """Get the terminal widget instance"""
        return self.terminal_widget
    
    def execute_code(self, code):
        """Execute code in the terminal"""
        if self.terminal_widget:
            self.terminal_widget.set_code(code)
            self.terminal_widget.execute_code()
    
    def clear_terminal(self):
        """Clear terminal output"""
        if self.terminal_widget:
            self.terminal_widget.clear_output()
    
    def closeEvent(self, event):
        """Handle close event"""
        self.save_settings()
        super().closeEvent(event)

class TerminalTabWidget(QTabWidget):
    """
    PROTOTYPE: Tab-based terminal integration
    Alternative to dock widget for tab-style layout
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.terminal_widget = None
        self.piano_roll_widget = None
        
        self.setup_tabs()
    
    def setup_tabs(self):
        """Set up tab interface"""
        self.setTabPosition(QTabWidget.North)
        self.setMovable(True)
        self.setTabsClosable(False)  # Don't allow closing main tabs
        
        # Style the tabs
        self.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #464647;
                background-color: #252526;
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
                background-color: #4ec9b0;
                color: #1e1e1e;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #3c3c3c;
            }
        """)
    
    def add_piano_roll_tab(self, piano_roll_widget):
        """Add piano roll as a tab"""
        self.piano_roll_widget = piano_roll_widget
        self.addTab(piano_roll_widget, "🎹 Piano Roll")
    
    def add_terminal_tab(self):
        """Add terminal as a tab"""
        self.terminal_widget = JavaScriptTerminalWidget()
        self.addTab(self.terminal_widget, "🖥️ Terminal")
        return self.terminal_widget
    
    def switch_to_terminal(self):
        """Switch to terminal tab"""
        if self.terminal_widget:
            terminal_index = self.indexOf(self.terminal_widget)
            if terminal_index >= 0:
                self.setCurrentIndex(terminal_index)
    
    def switch_to_piano_roll(self):
        """Switch to piano roll tab"""
        if self.piano_roll_widget:
            piano_roll_index = self.indexOf(self.piano_roll_widget)
            if piano_roll_index >= 0:
                self.setCurrentIndex(piano_roll_index)
    
    def get_terminal_widget(self):
        """Get terminal widget"""
        return self.terminal_widget