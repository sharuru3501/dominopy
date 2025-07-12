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
        
        # Styling
        self.setStyleSheet("""
            MeasureBarWidget {
                background-color: #44475a;
                border-bottom: 1px solid #6272a4;
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
        
        # Clear background
        painter.fillRect(self.rect(), QColor("#44475a"))
        
        # Draw piano keyboard area (to match piano roll)
        painter.fillRect(0, 0, self.piano_width, self.height(), QColor("#1e1e1e"))
        painter.setPen(QColor("#6272a4"))
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
        
        # Draw measure numbers
        measure_number = 1
        for tick in range(0, self.visible_end_tick + ticks_per_measure, ticks_per_measure):
            if tick >= self.visible_start_tick:
                x = self._tick_to_x(tick) + self.grid_start_x
                
                # Draw measure separator line
                painter.setPen(QColor("#6272a4"))  # Subtle line
                painter.drawLine(int(x), 0, int(x), self.height())
                
                # Draw measure number
                painter.setPen(QColor("#000000"))  # Black text
                text_rect = painter.fontMetrics().boundingRect(str(measure_number))
                
                # Center text in measure
                if measure_number == 1:
                    # First measure: start from grid start
                    text_x = self.grid_start_x + 5
                else:
                    # Other measures: center between current and previous lines
                    prev_x = self._tick_to_x(tick - ticks_per_measure) + self.grid_start_x
                    text_x = int((prev_x + x) / 2 - text_rect.width() / 2)
                
                text_y = (self.height() + text_rect.height()) // 2 - 2
                painter.drawText(text_x, text_y, str(measure_number))
                measure_number += 1