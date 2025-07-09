"""
Edit modes for piano roll editor
"""
from enum import Enum
from typing import List, Optional, Tuple
from PySide6.QtCore import QObject, QRectF, QPointF, Signal
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt

class EditMode(Enum):
    """Edit modes for piano roll"""
    NOTE_INPUT = "note_input"
    SELECTION = "selection"

class SelectionRectangle:
    """Represents a selection rectangle"""
    
    def __init__(self, start_pos: QPointF, end_pos: QPointF = None):
        self.start_pos = start_pos
        self.end_pos = end_pos or start_pos
        self.active = True
    
    def update_end_pos(self, end_pos: QPointF):
        """Update the end position of the rectangle"""
        self.end_pos = end_pos
    
    def get_rect(self) -> QRectF:
        """Get the QRectF representation of the selection"""
        x1, y1 = self.start_pos.x(), self.start_pos.y()
        x2, y2 = self.end_pos.x(), self.end_pos.y()
        
        # Ensure proper rectangle (top-left to bottom-right)
        left = min(x1, x2)
        top = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        
        return QRectF(left, top, width, height)
    
    def contains_point(self, point: QPointF) -> bool:
        """Check if a point is inside the selection rectangle"""
        return self.get_rect().contains(point)
    
    def draw(self, painter: QPainter):
        """Draw the selection rectangle"""
        if not self.active:
            return
            
        rect = self.get_rect()
        
        # Draw selection rectangle
        painter.setPen(QPen(QColor("#50c7e3"), 2, Qt.DashLine))
        painter.setBrush(QColor(80, 199, 227, 30))  # Semi-transparent fill
        painter.drawRect(rect)

class EditModeManager(QObject):
    """Manages edit modes for piano roll"""
    
    mode_changed = Signal(EditMode)
    
    def __init__(self):
        super().__init__()
        self._current_mode = EditMode.NOTE_INPUT
        self._selection_rectangle: Optional[SelectionRectangle] = None
    
    @property
    def current_mode(self) -> EditMode:
        """Get current edit mode"""
        return self._current_mode
    
    def set_mode(self, mode: EditMode):
        """Set current edit mode"""
        if self._current_mode != mode:
            self._current_mode = mode
            self.clear_selection_rectangle()
            self.mode_changed.emit(mode)
    
    def toggle_mode(self):
        """Toggle between note input and selection modes"""
        if self._current_mode == EditMode.NOTE_INPUT:
            self.set_mode(EditMode.SELECTION)
        else:
            self.set_mode(EditMode.NOTE_INPUT)
    
    def is_note_input_mode(self) -> bool:
        """Check if in note input mode"""
        return self._current_mode == EditMode.NOTE_INPUT
    
    def is_selection_mode(self) -> bool:
        """Check if in selection mode"""
        return self._current_mode == EditMode.SELECTION
    
    def start_selection_rectangle(self, start_pos: QPointF):
        """Start a new selection rectangle"""
        self._selection_rectangle = SelectionRectangle(start_pos)
    
    def update_selection_rectangle(self, end_pos: QPointF):
        """Update the selection rectangle"""
        if self._selection_rectangle:
            self._selection_rectangle.update_end_pos(end_pos)
    
    def finish_selection_rectangle(self) -> Optional[QRectF]:
        """Finish the selection rectangle and return its bounds"""
        if self._selection_rectangle:
            rect = self._selection_rectangle.get_rect()
            self._selection_rectangle.active = False
            return rect
        return None
    
    def clear_selection_rectangle(self):
        """Clear the selection rectangle"""
        self._selection_rectangle = None
    
    def get_selection_rectangle(self) -> Optional[SelectionRectangle]:
        """Get the current selection rectangle"""
        return self._selection_rectangle
    
    def get_mode_display_name(self) -> str:
        """Get display name for current mode"""
        if self._current_mode == EditMode.NOTE_INPUT:
            return "Note Input Mode"
        elif self._current_mode == EditMode.SELECTION:
            return "Selection Mode"
        return "Unknown Mode"
    
    def get_mode_description(self) -> str:
        """Get description for current mode"""
        if self._current_mode == EditMode.NOTE_INPUT:
            return "Click to create notes, drag to move/resize"
        elif self._current_mode == EditMode.SELECTION:
            return "Click and drag to select notes"
        return ""