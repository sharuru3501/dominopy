
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt

class PianoKeyboardWidget(QWidget):
    def __init__(self, pixels_per_pitch: int = 10, parent=None):
        super().__init__(parent)
        self.pixels_per_pitch = pixels_per_pitch
        self.setFixedWidth(50) # Fixed width for the keyboard
        self.setStyleSheet("background-color: #1e1e1e;") # Dark background for keyboard

        # Define which MIDI notes are black keys
        self.white_keys_in_octave = {0, 2, 4, 5, 7, 9, 11} # C, D, E, F, G, A, B

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        # Draw all 128 keys (rows)
        for midi_note in range(128): # MIDI notes 0 to 127
            y_top = height - ((midi_note + 1) * self.pixels_per_pitch)

            note_in_octave = midi_note % 12
            is_white_key = note_in_octave in self.white_keys_in_octave

            if is_white_key:
                painter.setBrush(QColor(Qt.white))
                painter.setPen(QColor(Qt.gray))
            else:
                painter.setBrush(QColor("#333333")) # Dark gray for black keys
                painter.setPen(QColor("#555555")) # Slightly lighter border

            # Draw the full-width rectangle for each key (row)
            painter.drawRect(0, int(y_top), width, self.pixels_per_pitch)

            # Optional: Draw MIDI note number for debugging C position
            if midi_note % 12 == 0: # It's a C note
                octave_number = (midi_note // 12) - 2 # Adjust for MIDI 60 = C3 convention
                c_label = f"C{octave_number}"
                painter.setPen(QColor(Qt.red))
                painter.drawText(5, int(y_top + self.pixels_per_pitch / 2 + 5), c_label)

        painter.end()
