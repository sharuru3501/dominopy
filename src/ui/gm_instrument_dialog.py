"""
GM Instrument Selection Dialog
Allows users to select General MIDI instruments for Internal FluidSynth tracks
"""
from typing import Optional
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QListWidget, QListWidgetItem, QGroupBox,
                              QSplitter, QTextEdit)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from src.gm_instruments import GM_INSTRUMENTS, get_gm_instrument_name
from src.audio_system import get_audio_manager

class GMInstrumentDialog(QDialog):
    """Dialog for selecting GM instruments"""
    
    # Signals
    instrument_selected = Signal(int)  # program number
    
    def __init__(self, current_program: int = 1, parent=None):
        super().__init__(parent)
        self.current_program = current_program
        self.selected_program = current_program
        
        self.setWindowTitle("Select GM Instrument")
        self.setMinimumSize(600, 450)
        
        self.setup_ui()
        self.load_instruments()
        self.select_current_instrument()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Select General MIDI Instrument")
        header_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Main content area
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Left side - Categories
        self.setup_categories(splitter)
        
        # Right side - Instruments
        self.setup_instruments(splitter)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.preview_button = QPushButton("🎵 Preview")
        self.preview_button.clicked.connect(self.preview_instrument)
        button_layout.addWidget(self.preview_button)
        
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.select_button = QPushButton("Select")
        self.select_button.clicked.connect(self.accept_selection)
        self.select_button.setDefault(True)
        button_layout.addWidget(self.select_button)
        
        layout.addLayout(button_layout)
    
    def setup_categories(self, splitter):
        """Setup category list"""
        category_widget = QVBoxLayout()
        category_container = QGroupBox("Categories")
        category_container.setLayout(category_widget)
        
        self.category_list = QListWidget()
        self.category_list.itemSelectionChanged.connect(self.on_category_changed)
        category_widget.addWidget(self.category_list)
        
        splitter.addWidget(category_container)
    
    def setup_instruments(self, splitter):
        """Setup instrument list and details"""
        right_widget = QVBoxLayout()
        right_container = QGroupBox("Instruments")
        right_container.setLayout(right_widget)
        
        # Instrument list
        self.instrument_list = QListWidget()
        self.instrument_list.itemSelectionChanged.connect(self.on_instrument_changed)
        self.instrument_list.itemDoubleClicked.connect(self.accept_selection)
        right_widget.addWidget(self.instrument_list)
        
        # Instrument details
        details_layout = QVBoxLayout()
        details_group = QGroupBox("Details")
        details_group.setLayout(details_layout)
        details_group.setMaximumHeight(120)
        
        self.details_name = QLabel("No instrument selected")
        self.details_name.setFont(QFont("Arial", 11, QFont.Bold))
        details_layout.addWidget(self.details_name)
        
        self.details_program = QLabel("")
        self.details_program.setStyleSheet("color: #666666;")
        details_layout.addWidget(self.details_program)
        
        self.details_category = QLabel("")
        self.details_category.setStyleSheet("color: #666666;")
        details_layout.addWidget(self.details_category)
        
        right_widget.addWidget(details_group)
        
        splitter.addWidget(right_container)
        
        # Set splitter proportions
        splitter.setSizes([200, 400])
    
    def load_instruments(self):
        """Load GM instrument categories"""
        self.category_list.clear()
        
        for category in GM_INSTRUMENTS.keys():
            item = QListWidgetItem(category)
            self.category_list.addItem(item)
        
        # Select first category by default
        if self.category_list.count() > 0:
            self.category_list.setCurrentRow(0)
    
    def on_category_changed(self):
        """Handle category selection change"""
        current_item = self.category_list.currentItem()
        if not current_item:
            return
        
        category = current_item.text()
        self.load_instruments_for_category(category)
    
    def load_instruments_for_category(self, category: str):
        """Load instruments for selected category"""
        self.instrument_list.clear()
        
        instruments = GM_INSTRUMENTS.get(category, [])
        for program, name in instruments:
            item = QListWidgetItem(f"{program:3d} - {name}")
            item.setData(Qt.UserRole, program)
            self.instrument_list.addItem(item)
    
    def on_instrument_changed(self):
        """Handle instrument selection change"""
        current_item = self.instrument_list.currentItem()
        if not current_item:
            self.update_details(None, None, None)
            return
        
        program = current_item.data(Qt.UserRole)
        name = get_gm_instrument_name(program)
        category = self.category_list.currentItem().text() if self.category_list.currentItem() else ""
        
        self.selected_program = program
        self.update_details(name, program, category)
    
    def update_details(self, name: Optional[str], program: Optional[int], category: Optional[str]):
        """Update the details panel"""
        if name is None:
            self.details_name.setText("No instrument selected")
            self.details_program.setText("")
            self.details_category.setText("")
            return
        
        self.details_name.setText(name)
        self.details_program.setText(f"Program Number: {program}")
        self.details_category.setText(f"Category: {category}")
    
    def select_current_instrument(self):
        """Select the current instrument in the UI"""
        # Find and select the category containing the current program
        for category, instruments in GM_INSTRUMENTS.items():
            for program, name in instruments:
                if program == self.current_program:
                    # Select category
                    for i in range(self.category_list.count()):
                        if self.category_list.item(i).text() == category:
                            self.category_list.setCurrentRow(i)
                            break
                    
                    # Select instrument
                    for i in range(self.instrument_list.count()):
                        item = self.instrument_list.item(i)
                        if item.data(Qt.UserRole) == program:
                            self.instrument_list.setCurrentItem(item)
                            break
                    return
    
    def preview_instrument(self):
        """Preview the selected instrument"""
        current_item = self.instrument_list.currentItem()
        if not current_item:
            return
        
        program = current_item.data(Qt.UserRole)
        audio_manager = get_audio_manager()
        if audio_manager:
            # Temporarily set program and play a preview note
            old_program = audio_manager.current_program
            audio_manager.set_program(program)
            audio_manager.play_note_preview(60, 100)  # Middle C
            
            # Restore original program after a short delay
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1000, lambda: audio_manager.set_program(old_program))
    
    def accept_selection(self):
        """Accept the current selection"""
        current_item = self.instrument_list.currentItem()
        if current_item:
            self.selected_program = current_item.data(Qt.UserRole)
            self.instrument_selected.emit(self.selected_program)
            self.accept()
    
    def get_selected_program(self) -> int:
        """Get the selected program number"""
        return self.selected_program