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
        self.setFixedHeight(22)  # Fixed height for measure bar
        self.setMinimumWidth(800)
        
        # Piano roll synchronization
        self.visible_start_tick = 0
        self.visible_end_tick = 3840  # Default: 8 measures at 480 ticks per beat
        self.grid_width_pixels = 0.15  # Pixels per tick (zoom level)
        self.piano_width = 80  # Width of piano keyboard (must match piano roll)
        self.grid_start_x = self.piano_width  # Left offset to align with piano roll grid
        
        # MIDI project reference
        self.midi_project: Optional[MidiProject] = None
        
        # Styling (match track list background)
        self.setStyleSheet("""
            MeasureBarWidget {
                background-color: #F5F5F5;
                border-bottom: 1px solid #CCCCCC;
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
    
    def on_time_signature_changed(self):
        """Handle time signature changes - proper notification method"""
        # Simply trigger a repaint with the updated time signature data
        # The midi_project reference already contains the updated time signature
        self.update()
    
    def _tick_to_x(self, tick: int) -> float:
        """Convert MIDI tick to X coordinate (same as piano roll)"""
        return (tick - self.visible_start_tick) * self.grid_width_pixels
    
    def paintEvent(self, event):
        """Draw measure numbers in horizontal bar"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Clear background (match track list)
        painter.fillRect(self.rect(), QColor("#F5F5F5"))
        
        # Draw piano keyboard area (match background color)
        painter.fillRect(0, 0, self.piano_width, self.height(), QColor("#F5F5F5"))
        painter.setPen(QColor("#CCCCCC"))
        painter.drawLine(self.piano_width - 1, 0, self.piano_width - 1, self.height())
        
        # Get time signature information
        ticks_per_beat = self.midi_project.ticks_per_beat if self.midi_project else 480
        
        # Set up font
        font = QFont("Arial", 11)
        font.setBold(True)
        painter.setFont(font)
        
        # Get current time signature dynamically
        if self.midi_project:
            numerator, denominator = self.midi_project.get_current_time_signature()
        else:
            numerator, denominator = 4, 4
        
        # Draw measure lines and numbers with time signature changes support
        if self.midi_project and self.midi_project.time_signature_changes:
            self._draw_measures_with_time_signature_changes(painter, ticks_per_beat)
        else:
            self._draw_measures_simple(painter, ticks_per_beat, numerator, denominator)
    
    def _draw_measures_simple(self, painter: QPainter, ticks_per_beat: int, numerator: int, denominator: int):
        """Draw measures with a single time signature"""
        # Use centralized calculation method
        if self.midi_project:
            ticks_per_measure = self.midi_project.calculate_ticks_per_measure(numerator, denominator)
        else:
            # Fallback calculation for when midi_project is not available
            if denominator == 8:
                beats_per_measure = numerator / 2
                ticks_per_measure = int(ticks_per_beat * beats_per_measure)
            else:
                beats_per_measure = numerator * (4 / denominator)
                ticks_per_measure = int(ticks_per_beat * beats_per_measure)
        
        # Calculate the range of measures to draw
        start_measure_tick = (self.visible_start_tick // ticks_per_measure) * ticks_per_measure
        end_tick = self.visible_end_tick + ticks_per_measure
        
        for tick in range(start_measure_tick, end_tick, ticks_per_measure):
            # Calculate the actual measure number (1-based)
            measure_number = (tick // ticks_per_measure) + 1
            
            # Only draw if this measure line is visible
            if tick >= self.visible_start_tick - ticks_per_measure:
                self._draw_measure_line_and_number(painter, tick, measure_number)
    
    def _draw_measures_with_time_signature_changes(self, painter: QPainter, ticks_per_beat: int):
        """Draw measures with time signature changes support"""
        current_tick = 0
        measure_number = 1
        
        # Get all time signature changes sorted by tick
        time_sig_changes = sorted(self.midi_project.time_signature_changes, key=lambda x: x.tick)
        
        for i, ts_change in enumerate(time_sig_changes):
            # Get the next time signature change tick, or use a large number if this is the last one
            next_change_tick = time_sig_changes[i + 1].tick if i + 1 < len(time_sig_changes) else max(self.visible_end_tick + 10000, 100000)
            
            # Calculate ticks per measure for this time signature
            numerator, denominator = ts_change.numerator, ts_change.denominator
            ticks_per_measure = self.midi_project.calculate_ticks_per_measure(numerator, denominator)
            
            # Draw measures for this time signature section
            section_start_tick = ts_change.tick
            section_end_tick = min(next_change_tick, self.visible_end_tick + ticks_per_measure)
            
            # Align to measure boundaries
            if section_start_tick > current_tick:
                # If there's a gap, fill it with the previous time signature
                current_tick = section_start_tick
            
            # Find the first measure boundary at or after section_start_tick
            first_measure_tick = ((section_start_tick + ticks_per_measure - 1) // ticks_per_measure) * ticks_per_measure
            
            # Calculate measure number for the first measure in this section
            if section_start_tick == 0:
                measure_number = 1
            else:
                # Count measures from the beginning up to this point
                measure_number = self._calculate_measure_number_at_tick(section_start_tick, ticks_per_beat)
            
            # Draw measures in this section
            for tick in range(first_measure_tick, section_end_tick, ticks_per_measure):
                if tick >= self.visible_start_tick - ticks_per_measure and tick <= self.visible_end_tick + ticks_per_measure:
                    # Calculate correct measure number for this tick
                    actual_measure_number = self._calculate_measure_number_at_tick(tick, ticks_per_beat)
                    self._draw_measure_line_and_number(painter, tick, actual_measure_number)
    
    def _calculate_measure_number_at_tick(self, target_tick: int, ticks_per_beat: int) -> int:
        """Calculate the measure number at a given tick, considering time signature changes"""
        if not self.midi_project or not self.midi_project.time_signature_changes:
            # Fallback to simple calculation
            return (target_tick // (ticks_per_beat * 4)) + 1
        
        current_tick = 0
        measure_number = 1
        time_sig_changes = sorted(self.midi_project.time_signature_changes, key=lambda x: x.tick)
        
        for i, ts_change in enumerate(time_sig_changes):
            next_change_tick = time_sig_changes[i + 1].tick if i + 1 < len(time_sig_changes) else float('inf')
            
            # Calculate ticks per measure for this time signature
            numerator, denominator = ts_change.numerator, ts_change.denominator
            ticks_per_measure = self.midi_project.calculate_ticks_per_measure(numerator, denominator)
            
            # Determine the section boundaries
            section_start = max(current_tick, ts_change.tick)
            section_end = min(next_change_tick, target_tick)
            
            # If the target tick is within this section
            if section_start <= target_tick < next_change_tick:
                # Count complete measures from section start to target tick
                if section_start < target_tick:
                    ticks_from_section_start = target_tick - section_start
                    complete_measures_in_section = ticks_from_section_start // ticks_per_measure
                    measure_number += complete_measures_in_section
                return measure_number
            
            # If the target tick is beyond this section, count all measures in this section
            if target_tick >= next_change_tick:
                if section_start < next_change_tick:
                    ticks_in_section = next_change_tick - section_start
                    complete_measures_in_section = ticks_in_section // ticks_per_measure
                    measure_number += complete_measures_in_section
                    current_tick = next_change_tick
        
        return measure_number
    
    def _draw_measure_line_and_number(self, painter: QPainter, tick: int, measure_number: int):
        """Draw a single measure line and number"""
        x = self._tick_to_x(tick) + self.grid_start_x
        
        # Only draw if the x position is within the visible area
        if x >= self.grid_start_x and x <= self.width():
            # Draw black vertical measure line
            painter.setPen(QColor("#000000"))  # Black line
            painter.drawLine(int(x), 0, int(x), self.height())
            
            # Draw measure number
            painter.setPen(QColor("#000000"))  # Black text
            text_rect = painter.fontMetrics().boundingRect(str(measure_number))
            
            # Position text just to the right of the measure line
            text_x = int(x) + 3  # Small offset from the line
            text_y = (self.height() + text_rect.height()) // 2 - 2
            
            # Only draw text if it fits within the widget bounds
            if text_x + text_rect.width() <= self.width():
                painter.drawText(text_x, text_y, str(measure_number))