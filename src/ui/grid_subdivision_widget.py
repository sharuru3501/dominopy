"""
Grid Subdivision Widget - Controls for grid division selection
"""
from typing import Dict, List, Tuple
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

class GridSubdivisionWidget(QWidget):
    """
    Widget for selecting grid subdivision level in the piano roll.
    Allows switching between quarter notes, eighth notes, sixteenth notes, etc.
    """
    
    # Signal emitted when grid subdivision changes
    # Parameters: (subdivision_type, ticks_per_subdivision)
    subdivision_changed = Signal(str, int)
    
    def __init__(self):
        super().__init__()
        
        # Grid subdivision options
        # Format: (display_name, subdivision_type, divisions_per_beat)
        self.subdivision_options = [
            ("1/4", "quarter", 1),
            ("1/8", "eighth", 2),
            ("1/16", "sixteenth", 4),
            ("1/32", "thirty_second", 8),
            ("1/8T", "eighth_triplet", 3),
            ("1/16T", "sixteenth_triplet", 6),
        ]
        
        self.current_subdivision = "sixteenth"  # Default to 16th notes
        self.ticks_per_beat = 480  # Standard MIDI resolution
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the UI components"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)
        
        # Label
        label = QLabel("Grid:")
        label.setFont(QFont("Arial", 9))
        label.setStyleSheet("color: #6272a4;")
        layout.addWidget(label)
        
        # Subdivision combo box
        self.subdivision_combo = QComboBox()
        self.subdivision_combo.setFont(QFont("Arial", 9))
        self.subdivision_combo.setMinimumWidth(60)  # Smaller width for shorter text
        self.subdivision_combo.view().setMinimumWidth(80)  # Wider popup for readability
        
        # Populate combo box
        for display_name, subdivision_type, divisions in self.subdivision_options:
            self.subdivision_combo.addItem(display_name, subdivision_type)
        
        # Set default selection (16th notes)
        default_index = self._find_subdivision_index("sixteenth")
        if default_index >= 0:
            self.subdivision_combo.setCurrentIndex(default_index)
        
        # Connect signal
        self.subdivision_combo.currentTextChanged.connect(self._on_subdivision_changed)
        
        layout.addWidget(self.subdivision_combo)
        
        # Styling
        self.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1px solid #6272a4;
                border-radius: 3px;
                padding: 2px 5px;
                color: black;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #6272a4;
                selection-background-color: #6272a4;
                color: black;
            }
        """)
    
    def _find_subdivision_index(self, subdivision_type: str) -> int:
        """Find the index of a subdivision type in the combo box"""
        for i in range(self.subdivision_combo.count()):
            if self.subdivision_combo.itemData(i) == subdivision_type:
                return i
        return -1
    
    def _on_subdivision_changed(self):
        """Handle subdivision selection change"""
        current_index = self.subdivision_combo.currentIndex()
        if current_index >= 0:
            subdivision_type = self.subdivision_combo.itemData(current_index)
            self.current_subdivision = subdivision_type
            
            # Calculate ticks per subdivision
            ticks_per_subdivision = self._calculate_ticks_per_subdivision(subdivision_type)
            
            # Emit signal
            self.subdivision_changed.emit(subdivision_type, ticks_per_subdivision)
            
            print(f"Grid subdivision changed to: {subdivision_type} ({ticks_per_subdivision} ticks)")
    
    def _calculate_ticks_per_subdivision(self, subdivision_type: str) -> int:
        """Calculate ticks per subdivision for given type"""
        # Find the subdivision in our options
        for _, sub_type, divisions_per_beat in self.subdivision_options:
            if sub_type == subdivision_type:
                if "triplet" in subdivision_type:
                    # Triplets divide the beat into 3 or 6 parts
                    return self.ticks_per_beat // divisions_per_beat
                else:
                    # Regular subdivisions (powers of 2)
                    return self.ticks_per_beat // divisions_per_beat
        
        # Default fallback
        return self.ticks_per_beat // 4  # 16th note
    
    def set_ticks_per_beat(self, ticks_per_beat: int):
        """Update ticks per beat (when tempo/project changes)"""
        self.ticks_per_beat = ticks_per_beat
        # Re-emit current subdivision with new tick calculation
        if hasattr(self, 'subdivision_combo'):
            self._on_subdivision_changed()
    
    def get_current_subdivision(self) -> Tuple[str, int]:
        """Get current subdivision type and ticks per subdivision"""
        ticks_per_subdivision = self._calculate_ticks_per_subdivision(self.current_subdivision)
        return self.current_subdivision, ticks_per_subdivision
    
    def set_subdivision(self, subdivision_type: str):
        """Programmatically set the subdivision"""
        index = self._find_subdivision_index(subdivision_type)
        if index >= 0:
            self.subdivision_combo.setCurrentIndex(index)