from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QFont
from typing import Optional

from src.midi_data_model import MidiProject


class MeasureBarWidget(QWidget):
    """
    Horizontal bar that displays measure numbers above the piano roll.
    Synchronizes with piano roll scrolling and time signature changes.
    """
    
    def __init__(self):
        super().__init__()
        self.setFixedHeight(30)  # Fixed height for measure bar
        self.setMinimumWidth(800)
        
        # Piano roll synchronization
        self.visible_start_tick = 0
        self.visible_end_tick = 3840  # Default: 8 measures at 480 ticks per beat
        self.grid_width_pixels = 0.15  # Pixels per tick (zoom level)
        self.piano_width = 80  # Width of piano keyboard (must match piano roll)
        self.grid_start_x = self.piano_width  # Left offset to align with piano roll grid
        
        # MIDI project reference
        self.midi_project: Optional[MidiProject] = None
        
        # Styling (match grid background)
        self.setStyleSheet("""
            MeasureBarWidget {
                background-color: #282c34;
                border-bottom: 1px solid #44475a;
            }
        """)
    
    def set_midi_project(self, midi_project: MidiProject):
        """Set the MIDI project for time signature information"""
        self.midi_project = midi_project
        self.update()
    
    def sync_with_piano_roll(self, visible_start_tick: int, visible_end_tick: int, 
                           grid_width_pixels: float):
        """Synchronize display parameters with the piano roll"""
        self.visible_start_tick = visible_start_tick
        self.visible_end_tick = visible_end_tick
        self.grid_width_pixels = grid_width_pixels
        # grid_start_x is fixed to piano_width for alignment
        self.update()
    
    def _tick_to_x(self, tick: int) -> float:
        """Convert MIDI tick to X coordinate (same as piano roll)"""
        return tick * self.grid_width_pixels
    
    def paintEvent(self, event):
        """Draw measure numbers in horizontal bar"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Clear background (match piano roll)
        painter.fillRect(self.rect(), QColor("#282c34"))
        
        # Draw piano keyboard area (to match piano roll)
        painter.fillRect(0, 0, self.piano_width, self.height(), QColor("#1e1e1e"))
        painter.setPen(QColor("#44475a"))
        painter.drawLine(self.piano_width - 1, 0, self.piano_width - 1, self.height())
        
        # Get time signature information
        ticks_per_beat = self.midi_project.ticks_per_beat if self.midi_project else 480
        
        if self.midi_project:
            numerator, denominator = self.midi_project.get_current_time_signature()
        else:
            numerator, denominator = 4, 4  # Default 4/4
        
        # Calculate ticks per measure (same logic as piano roll)
        if denominator == 8:
            # For compound time (6/8, 9/8, 12/8), group eighth notes
            beats_per_measure = numerator / 2  # 6/8 = 3 beats, 9/8 = 4.5 beats
            ticks_per_measure = int(ticks_per_beat * beats_per_measure)
        else:
            # For simple time (4/4, 3/4, 2/4, 5/4)
            beats_per_measure = numerator * (4 / denominator)  # Normalize to quarter note beats
            ticks_per_measure = int(ticks_per_beat * beats_per_measure)
        
        # Set up font
        font = QFont("Arial", 11)
        font.setBold(True)
        painter.setFont(font)
        
        # Draw measure numbers aligned with pink measure lines
        measure_number = 1
        for tick in range(0, self.visible_end_tick + ticks_per_measure, ticks_per_measure):
            if tick >= self.visible_start_tick:
                x = self._tick_to_x(tick) + self.grid_start_x
                
                # Draw measure number directly at the pink measure line position
                painter.setPen(QColor("#000000"))  # Black text
                text_rect = painter.fontMetrics().boundingRect(str(measure_number))
                
                # Position text just to the right of the measure line
                text_x = int(x) + 3  # Small offset from the line
                text_y = (self.height() + text_rect.height()) // 2 - 2
                
                painter.drawText(text_x, text_y, str(measure_number))
                measure_number += 1