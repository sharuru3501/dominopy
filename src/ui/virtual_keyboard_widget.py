"""
Virtual Keyboard Widget
Provides a virtual piano keyboard that can be played using computer keyboard keys
"""
from typing import Dict, Optional, Set
from dataclasses import dataclass
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QSlider, QSpinBox, QGroupBox,
                              QDialog, QApplication)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QKeyEvent, QPen, QBrush

@dataclass
class KeyMapping:
    """Represents a key mapping from computer key to MIDI note"""
    key_code: int  # Qt key code
    key_name: str  # Display name (e.g., "A", "W")
    midi_note: int  # MIDI note number (relative to base octave)
    is_black_key: bool = False

class VirtualKeyboardWidget(QDialog):
    """
    Virtual keyboard widget for playing notes using computer keyboard
    """
    
    # Signals
    note_pressed = Signal(int, int)  # pitch, velocity
    note_released = Signal(int)      # pitch
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuration
        self.base_octave = 4  # C4 = middle C
        self.current_velocity = 100
        self.visible_octaves = 2  # Show 2 octaves worth of keys
        
        # State tracking
        self.pressed_keys: Set[int] = set()  # Currently pressed computer keys
        self.pressed_notes: Set[int] = set()  # Currently pressed MIDI notes
        
        # Initialize key mappings
        self._setup_key_mappings()
        
        # Setup UI
        self.setWindowTitle("Virtual Keyboard")
        self.setMinimumSize(800, 300)
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        
        self.setup_ui()
        
        # Enable keyboard focus
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Auto-stop timer for note releases
        self.note_stop_timer = QTimer()
        self.note_stop_timer.timeout.connect(self._auto_stop_notes)
        self.note_stop_timer.setSingleShot(False)
        
    def _setup_key_mappings(self):
        """Setup keyboard mappings for piano keys"""
        # Standard DAW keyboard mapping
        # White keys: A W S E D F T G Y H U J K L
        # Black keys: 2 3   6 7 9 0 -
        
        self.key_mappings: Dict[int, KeyMapping] = {}
        
        # White keys (C, D, E, F, G, A, B pattern)
        white_keys = [
            (Qt.Key_A, "A", 0),   # C
            (Qt.Key_S, "S", 2),   # D  
            (Qt.Key_D, "D", 4),   # E
            (Qt.Key_F, "F", 5),   # F
            (Qt.Key_G, "G", 7),   # G
            (Qt.Key_H, "H", 9),   # A
            (Qt.Key_J, "J", 11),  # B
            (Qt.Key_K, "K", 12),  # C (next octave)
            (Qt.Key_L, "L", 14),  # D
            (Qt.Key_Semicolon, ";", 16), # E
            (Qt.Key_Apostrophe, "'", 17), # F
        ]
        
        # Black keys  
        black_keys = [
            (Qt.Key_W, "W", 1),   # C#
            (Qt.Key_E, "E", 3),   # D#
            (Qt.Key_T, "T", 6),   # F#
            (Qt.Key_Y, "Y", 8),   # G#
            (Qt.Key_U, "U", 10),  # A#
            (Qt.Key_O, "O", 13),  # C# (next octave)
            (Qt.Key_P, "P", 15),  # D#
        ]
        
        # Add white keys
        for key_code, key_name, note_offset in white_keys:
            self.key_mappings[key_code] = KeyMapping(
                key_code=key_code,
                key_name=key_name, 
                midi_note=note_offset,
                is_black_key=False
            )
        
        # Add black keys
        for key_code, key_name, note_offset in black_keys:
            self.key_mappings[key_code] = KeyMapping(
                key_code=key_code,
                key_name=key_name,
                midi_note=note_offset, 
                is_black_key=True
            )
        
        # Special control keys
        self.control_keys = {
            Qt.Key_Z: "octave_down",
            Qt.Key_X: "octave_up", 
            Qt.Key_C: "velocity_down",
            Qt.Key_V: "velocity_up",
        }
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Control panel
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)
        
        # Piano keyboard display
        self.piano_display = PianoKeyboardDisplay(self)
        self.piano_display.setMinimumHeight(120)
        layout.addWidget(self.piano_display)
        
        # Key mapping display
        mapping_panel = self._create_mapping_panel()
        layout.addWidget(mapping_panel)
        
        # Update display
        self._update_piano_display()
    
    def _create_control_panel(self):
        """Create control panel with octave and velocity controls"""
        group = QGroupBox("Controls")
        layout = QHBoxLayout(group)
        
        # Current track info
        self.track_info_label = QLabel("Track: --")
        self.track_info_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(self.track_info_label)
        
        layout.addStretch()
        
        # Octave control
        layout.addWidget(QLabel("Octave:"))
        self.octave_spinbox = QSpinBox()
        self.octave_spinbox.setRange(0, 8)
        self.octave_spinbox.setValue(self.base_octave)
        self.octave_spinbox.valueChanged.connect(self._on_octave_changed)
        layout.addWidget(self.octave_spinbox)
        
        # Velocity control
        layout.addWidget(QLabel("Velocity:"))
        self.velocity_slider = QSlider(Qt.Horizontal)
        self.velocity_slider.setRange(1, 127)
        self.velocity_slider.setValue(self.current_velocity)
        self.velocity_slider.valueChanged.connect(self._on_velocity_changed)
        layout.addWidget(self.velocity_slider)
        
        self.velocity_label = QLabel(str(self.current_velocity))
        self.velocity_label.setMinimumWidth(30)
        layout.addWidget(self.velocity_label)
        
        return group
    
    def _create_mapping_panel(self):
        """Create key mapping reference panel"""
        group = QGroupBox("Keyboard Mapping")
        layout = QVBoxLayout(group)
        
        # White keys
        white_label = QLabel("White Keys: A S D F G H J K L ; '")
        white_label.setFont(QFont("Courier", 9))
        layout.addWidget(white_label)
        
        # Black keys  
        black_label = QLabel("Black Keys: W E   T Y U   O P")
        black_label.setFont(QFont("Courier", 9))
        layout.addWidget(black_label)
        
        # Controls
        control_label = QLabel("Controls: Z/X (Octave) • C/V (Velocity)")
        control_label.setFont(QFont("Courier", 8))
        layout.addWidget(control_label)
        
        return group
    
    def _update_piano_display(self):
        """Update piano keyboard visual display"""
        if hasattr(self, 'piano_display'):
            self.piano_display.set_base_octave(self.base_octave)
            self.piano_display.set_pressed_notes(self.pressed_notes)
            self.piano_display.update()
    
    def _on_octave_changed(self, octave: int):
        """Handle octave change"""
        self.base_octave = octave
        self._update_piano_display()
    
    def _on_velocity_changed(self, velocity: int):
        """Handle velocity change"""
        self.current_velocity = velocity
        self.velocity_label.setText(str(velocity))
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events"""
        key_code = event.key()
        
        # Prevent key repeat
        if event.isAutoRepeat():
            return
            
        # Check if key is already pressed
        if key_code in self.pressed_keys:
            return
            
        self.pressed_keys.add(key_code)
        
        # Handle control keys
        if key_code in self.control_keys:
            self._handle_control_key(self.control_keys[key_code])
            return
        
        # Handle note keys
        if key_code in self.key_mappings:
            mapping = self.key_mappings[key_code]
            midi_pitch = (self.base_octave * 12) + mapping.midi_note
            
            # Clamp to valid MIDI range
            if 0 <= midi_pitch <= 127:
                self.pressed_notes.add(midi_pitch)
                self.note_pressed.emit(midi_pitch, self.current_velocity)
                self._update_piano_display()
        
        super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event: QKeyEvent):
        """Handle key release events"""
        key_code = event.key()
        
        # Ignore auto-repeat
        if event.isAutoRepeat():
            return
            
        # Remove from pressed keys
        self.pressed_keys.discard(key_code)
        
        # Handle note release
        if key_code in self.key_mappings:
            mapping = self.key_mappings[key_code]
            midi_pitch = (self.base_octave * 12) + mapping.midi_note
            
            if 0 <= midi_pitch <= 127 and midi_pitch in self.pressed_notes:
                self.pressed_notes.discard(midi_pitch)
                self.note_released.emit(midi_pitch)
                self._update_piano_display()
        
        super().keyReleaseEvent(event)
    
    def _handle_control_key(self, control_action: str):
        """Handle control key actions"""
        if control_action == "octave_down":
            new_octave = max(0, self.base_octave - 1)
            self.octave_spinbox.setValue(new_octave)
        elif control_action == "octave_up":
            new_octave = min(8, self.base_octave + 1) 
            self.octave_spinbox.setValue(new_octave)
        elif control_action == "velocity_down":
            new_velocity = max(1, self.current_velocity - 10)
            self.velocity_slider.setValue(new_velocity)
        elif control_action == "velocity_up":
            new_velocity = min(127, self.current_velocity + 10)
            self.velocity_slider.setValue(new_velocity)
    
    def _auto_stop_notes(self):
        """Auto-stop notes that may be stuck"""
        # This is a safety mechanism for stuck notes
        for pitch in list(self.pressed_notes):
            self.note_released.emit(pitch)
        self.pressed_notes.clear()
        self._update_piano_display()
    
    def update_track_info(self, track_name: str, source_name: str = ""):
        """Update current track information display"""
        info_text = f"Track: {track_name}"
        if source_name:
            info_text += f" • {source_name}"
        self.track_info_label.setText(info_text)
    
    def showEvent(self, event):
        """Handle show event"""
        super().showEvent(event)
        self.setFocus()  # Ensure keyboard focus
    
    def closeEvent(self, event):
        """Handle close event"""
        # Stop all notes when closing
        for pitch in list(self.pressed_notes):
            self.note_released.emit(pitch)
        self.pressed_notes.clear()
        super().closeEvent(event)


class PianoKeyboardDisplay(QWidget):
    """Visual display of piano keyboard with key highlighting"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_octave = 4
        self.pressed_notes: Set[int] = set()
        self.visible_octaves = 2
        
        # Colors
        self.white_key_color = QColor(255, 255, 255)
        self.black_key_color = QColor(40, 40, 40)
        self.pressed_color = QColor(100, 150, 255)
        self.border_color = QColor(180, 180, 180)
    
    def set_base_octave(self, octave: int):
        """Set base octave for display"""
        self.base_octave = octave
        self.update()
    
    def set_pressed_notes(self, notes: Set[int]):
        """Set currently pressed notes"""
        self.pressed_notes = notes
        self.update()
    
    def paintEvent(self, event):
        """Paint the piano keyboard"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate dimensions
        widget_width = self.width()
        widget_height = self.height()
        
        # Piano key dimensions
        total_white_keys = 7 * self.visible_octaves  # 7 white keys per octave
        white_key_width = widget_width / total_white_keys
        white_key_height = widget_height
        black_key_width = white_key_width * 0.6
        black_key_height = white_key_height * 0.6
        
        # Draw white keys first
        self._draw_white_keys(painter, white_key_width, white_key_height)
        
        # Draw black keys on top
        self._draw_black_keys(painter, white_key_width, black_key_width, black_key_height)
    
    def _draw_white_keys(self, painter: QPainter, key_width: float, key_height: float):
        """Draw white piano keys"""
        white_key_pattern = [0, 2, 4, 5, 7, 9, 11]  # C D E F G A B
        
        for octave in range(self.visible_octaves):
            for i, note_offset in enumerate(white_key_pattern):
                midi_note = (self.base_octave + octave) * 12 + note_offset
                x = (octave * 7 + i) * key_width
                
                # Choose color
                if midi_note in self.pressed_notes:
                    color = self.pressed_color
                else:
                    color = self.white_key_color
                
                # Draw key
                painter.setPen(QPen(self.border_color, 1))
                painter.setBrush(QBrush(color))
                painter.drawRect(int(x), 0, int(key_width), int(key_height))
    
    def _draw_black_keys(self, painter: QPainter, white_key_width: float, 
                        black_key_width: float, black_key_height: float):
        """Draw black piano keys"""
        # Black key positions relative to white keys: after C, D, F, G, A
        black_key_pattern = [0.7, 1.7, 3.7, 4.7, 5.7]  # Relative positions
        black_note_offsets = [1, 3, 6, 8, 10]  # C# D# F# G# A#
        
        for octave in range(self.visible_octaves):
            for i, (pos, note_offset) in enumerate(zip(black_key_pattern, black_note_offsets)):
                midi_note = (self.base_octave + octave) * 12 + note_offset
                x = (octave * 7 + pos) * white_key_width - black_key_width / 2
                
                # Choose color
                if midi_note in self.pressed_notes:
                    color = self.pressed_color
                else:
                    color = self.black_key_color
                
                # Draw key
                painter.setPen(QPen(self.border_color, 1))
                painter.setBrush(QBrush(color))
                painter.drawRect(int(x), 0, int(black_key_width), int(black_key_height))