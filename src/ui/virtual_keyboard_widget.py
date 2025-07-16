"""
Virtual Keyboard Widget
Provides a virtual piano keyboard that can be played using computer keyboard keys
"""
from typing import Dict, Optional, Set, List
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
        
        # Chord display panel
        chord_panel = self._create_chord_display_panel()
        layout.addWidget(chord_panel)
        
        # Chord analysis panel (additional info)
        analysis_panel = self._create_analysis_panel()
        layout.addWidget(analysis_panel)
        
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
    
    def _create_chord_display_panel(self):
        """Create chord name display panel"""
        group = QGroupBox("Chord Display")
        layout = QVBoxLayout(group)
        
        # Chord name label (large font)
        self.chord_name_label = QLabel("---")
        self.chord_name_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.chord_name_label.setAlignment(Qt.AlignCenter)
        self.chord_name_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 2px solid #ddd;
                border-radius: 8px;
                padding: 10px;
                min-height: 40px;
            }
        """)
        layout.addWidget(self.chord_name_label)
        
        # Chord notes label (smaller font)
        self.chord_notes_label = QLabel("Press keys to see chord")
        self.chord_notes_label.setFont(QFont("Arial", 10))
        self.chord_notes_label.setAlignment(Qt.AlignCenter)
        self.chord_notes_label.setStyleSheet("""
            QLabel {
                color: #666;
                padding: 5px;
            }
        """)
        layout.addWidget(self.chord_notes_label)
        
        return group
    
    def _create_analysis_panel(self):
        """Create additional harmonic analysis panel"""
        group = QGroupBox("Harmonic Analysis")
        layout = QVBoxLayout(group)
        
        # Interval analysis label
        self.interval_analysis_label = QLabel("---")
        self.interval_analysis_label.setFont(QFont("Arial", 9))
        self.interval_analysis_label.setAlignment(Qt.AlignCenter)
        self.interval_analysis_label.setStyleSheet("""
            QLabel {
                color: #888;
                padding: 5px;
                background-color: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.interval_analysis_label)
        
        # Key suggestion label
        self.key_suggestion_label = QLabel("Possible keys: ---")
        self.key_suggestion_label.setFont(QFont("Arial", 8))
        self.key_suggestion_label.setAlignment(Qt.AlignCenter)
        self.key_suggestion_label.setStyleSheet("""
            QLabel {
                color: #666;
                padding: 3px;
            }
        """)
        layout.addWidget(self.key_suggestion_label)
        
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
                self._update_chord_display()
        
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
                self._update_chord_display()
        
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
        self._update_chord_display()
    
    def _update_chord_display(self):
        """Update chord name display with enhanced detail based on currently pressed notes"""
        try:
            if not self.pressed_notes:
                # No notes pressed - clear display
                self.chord_name_label.setText("---")
                self.chord_notes_label.setText("Press keys to see chord")
                self._clear_analysis_display()
                return
            
            # Convert MIDI pitches to sorted list
            pitches = sorted(list(self.pressed_notes))
            
            if len(pitches) == 1:
                # Single note - show note name with octave
                from src.music_theory import get_note_name_with_octave
                note_name = get_note_name_with_octave(pitches[0])
                self.chord_name_label.setText(note_name)
                self.chord_notes_label.setText("Single note")
                self._update_single_note_analysis(pitches[0])
                return
            
            # Multiple notes - detect chord with enhanced analysis
            from src.music_theory import detect_chord, get_note_name_with_octave, analyze_harmony
            
            chord = detect_chord(pitches)
            if chord:
                # Display enhanced chord name
                chord_display_name = chord.name
                
                # Add chord type information for clarity
                chord_type_info = ""
                if "13" in chord.name:
                    chord_type_info = " (13th chord)"
                elif "11" in chord.name:
                    chord_type_info = " (11th chord)"
                elif "9" in chord.name:
                    chord_type_info = " (9th chord)"
                elif "maj7" in chord.name or "7" in chord.name:
                    chord_type_info = " (7th chord)"
                elif "6" in chord.name:
                    chord_type_info = " (6th chord)"
                elif "sus" in chord.name:
                    chord_type_info = " (suspended)"
                elif "dim" in chord.name:
                    chord_type_info = " (diminished)"
                elif "aug" in chord.name:
                    chord_type_info = " (augmented)"
                elif "add" in chord.name:
                    chord_type_info = " (added note)"
                elif chord.chord_type == "major":
                    chord_type_info = " (major triad)"
                elif chord.chord_type == "minor":
                    chord_type_info = " (minor triad)"
                
                self.chord_name_label.setText(chord_display_name + chord_type_info)
                
                # Display detailed chord analysis
                actual_pitches = [get_note_name_with_octave(p) for p in pitches[:8]]
                if len(pitches) > 8:
                    actual_pitches.append("...")
                
                # Show both theoretical chord notes and actual played notes
                theoretical_notes = [note.name for note in chord.notes[:6]]
                if len(chord.notes) > 6:
                    theoretical_notes.append("...")
                
                notes_text = f"Theory: {', '.join(theoretical_notes)} | Played: {', '.join([p.replace(str(p)[-1:], '') for p in actual_pitches if p != '...'])}"
                if len(notes_text) > 60:  # Truncate if too long
                    notes_text = f"Played: {', '.join([p.replace(str(p)[-1:], '') for p in actual_pitches[:6] if p != '...'])}"
                
                self.chord_notes_label.setText(notes_text)
                
                # Enhanced logging for debugging
                intervals = [(p % 12) for p in pitches]
                unique_intervals = sorted(set(intervals))
                normalized_intervals = [(i - intervals[0]) % 12 for i in unique_intervals]
                print(f"Virtual Keyboard Chord: {chord.name} | Type: {chord.chord_type} | Intervals: {normalized_intervals}")
                
                # Update analysis panel
                self._update_harmonic_analysis(pitches, chord)
                
            else:
                # No chord detected - show detailed individual note analysis
                note_names = []
                for pitch in pitches[:8]:  # Show more notes
                    note_name = get_note_name_with_octave(pitch)
                    note_names.append(note_name.replace(str(note_name)[-1:], ''))  # Remove octave for brevity
                
                if len(pitches) > 8:
                    note_names.append("...")
                
                # Try to provide some harmonic analysis even if no chord detected
                intervals = [(p % 12) for p in pitches]
                unique_intervals = sorted(set(intervals))
                normalized_intervals = [(i - intervals[0]) % 12 for i in unique_intervals]
                
                harmony_hint = ""
                if 4 in normalized_intervals and 7 in normalized_intervals:
                    harmony_hint = " (major-like)"
                elif 3 in normalized_intervals and 7 in normalized_intervals:
                    harmony_hint = " (minor-like)"
                elif 3 in normalized_intervals and 6 in normalized_intervals:
                    harmony_hint = " (diminished-like)"
                elif 4 in normalized_intervals and 8 in normalized_intervals:
                    harmony_hint = " (augmented-like)"
                elif 5 in normalized_intervals:
                    harmony_hint = " (suspended-like)"
                
                self.chord_name_label.setText(f"Complex{harmony_hint} ({len(pitches)} notes)")
                self.chord_notes_label.setText(f"Notes: {', '.join(note_names)}")
                
                print(f"Virtual Keyboard - No standard chord detected. Notes: {note_names}, Intervals: {normalized_intervals}")
                
                # Update analysis panel for unrecognized chords
                self._update_unrecognized_analysis(pitches)
                
        except Exception as e:
            print(f"Error in enhanced chord detection: {e}")
            import traceback
            traceback.print_exc()
            # Fallback display
            self.chord_name_label.setText("Analysis Error")
            self.chord_notes_label.setText(f"{len(self.pressed_notes)} notes - detection failed")
    
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
        
        # Clear chord display
        if hasattr(self, 'chord_name_label'):
            self.chord_name_label.setText("---")
        if hasattr(self, 'chord_notes_label'):
            self.chord_notes_label.setText("Closed")
            
        super().closeEvent(event)
    
    def _clear_analysis_display(self):
        """Clear harmonic analysis display"""
        if hasattr(self, 'interval_analysis_label'):
            self.interval_analysis_label.setText("---")
        if hasattr(self, 'key_suggestion_label'):
            self.key_suggestion_label.setText("Possible keys: ---")
    
    def _update_single_note_analysis(self, pitch: int):
        """Update analysis for single note"""
        try:
            from src.music_theory import get_note_name_with_octave, analyze_harmony
            
            note_name = get_note_name_with_octave(pitch)
            
            if hasattr(self, 'interval_analysis_label'):
                self.interval_analysis_label.setText(f"Root note: {note_name}")
            
            if hasattr(self, 'key_suggestion_label'):
                # Show keys that contain this note
                analysis = analyze_harmony([pitch])
                if analysis["key_suggestions"]:
                    keys_text = ", ".join(analysis["key_suggestions"][:5])
                    self.key_suggestion_label.setText(f"Possible keys: {keys_text}")
                else:
                    self.key_suggestion_label.setText("Possible keys: All keys contain this note")
                    
        except Exception as e:
            print(f"Error in single note analysis: {e}")
            self._clear_analysis_display()
    
    def _update_harmonic_analysis(self, pitches: List[int], chord):
        """Update harmonic analysis for detected chord"""
        try:
            from src.music_theory import analyze_harmony
            
            # Calculate intervals from root
            intervals = [(p % 12) for p in pitches]
            unique_intervals = sorted(set(intervals))
            root_interval = unique_intervals[0]
            normalized_intervals = [(i - root_interval) % 12 for i in unique_intervals]
            
            # Create interval description
            interval_names = {0: "R", 1: "b9", 2: "9", 3: "m3", 4: "M3", 5: "11", 6: "b5", 
                             7: "5", 8: "#5", 9: "13", 10: "b7", 11: "M7"}
            
            interval_desc = [interval_names.get(i, str(i)) for i in normalized_intervals]
            
            if hasattr(self, 'interval_analysis_label'):
                self.interval_analysis_label.setText(f"Intervals: {' - '.join(interval_desc)}")
            
            # Key analysis
            if hasattr(self, 'key_suggestion_label'):
                analysis = analyze_harmony(pitches)
                if analysis["key_suggestions"]:
                    keys_text = ", ".join(analysis["key_suggestions"][:4])
                    self.key_suggestion_label.setText(f"Likely keys: {keys_text}")
                else:
                    self.key_suggestion_label.setText("Key analysis: Complex harmony")
                    
        except Exception as e:
            print(f"Error in harmonic analysis: {e}")
            if hasattr(self, 'interval_analysis_label'):
                self.interval_analysis_label.setText("Analysis error")
            if hasattr(self, 'key_suggestion_label'):
                self.key_suggestion_label.setText("Key analysis: Error")
    
    def _update_unrecognized_analysis(self, pitches: List[int]):
        """Update analysis for unrecognized chord patterns"""
        try:
            from src.music_theory import analyze_harmony
            
            # Basic interval analysis
            intervals = [(p % 12) for p in pitches]
            unique_intervals = sorted(set(intervals))
            root_interval = unique_intervals[0]
            normalized_intervals = [(i - root_interval) % 12 for i in unique_intervals]
            
            # Simplified interval description for complex chords
            basic_intervals = []
            if 3 in normalized_intervals:
                basic_intervals.append("m3")
            if 4 in normalized_intervals:
                basic_intervals.append("M3")
            if 7 in normalized_intervals:
                basic_intervals.append("5th")
            elif 6 in normalized_intervals:
                basic_intervals.append("b5")
            elif 8 in normalized_intervals:
                basic_intervals.append("#5")
            if 10 in normalized_intervals:
                basic_intervals.append("b7")
            if 11 in normalized_intervals:
                basic_intervals.append("M7")
            
            if hasattr(self, 'interval_analysis_label'):
                if basic_intervals:
                    self.interval_analysis_label.setText(f"Contains: {', '.join(basic_intervals)}")
                else:
                    self.interval_analysis_label.setText(f"Complex: {len(normalized_intervals)} different notes")
            
            # Key analysis for complex chords
            if hasattr(self, 'key_suggestion_label'):
                analysis = analyze_harmony(pitches)
                if analysis["key_suggestions"]:
                    keys_text = ", ".join(analysis["key_suggestions"][:3])
                    self.key_suggestion_label.setText(f"Possible keys: {keys_text}")
                else:
                    self.key_suggestion_label.setText("Key analysis: Very complex harmony")
                    
        except Exception as e:
            print(f"Error in unrecognized analysis: {e}")
            if hasattr(self, 'interval_analysis_label'):
                self.interval_analysis_label.setText("Complex harmony")
            if hasattr(self, 'key_suggestion_label'):
                self.key_suggestion_label.setText("Key analysis: Unknown")


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
        """Paint the piano keyboard with chromatic layout"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate dimensions
        widget_width = self.width()
        widget_height = self.height()
        
        # Draw all 12 chromatic notes in order for each octave
        total_semitones = 12 * self.visible_octaves
        semitone_width = widget_width / total_semitones
        
        for octave in range(self.visible_octaves):
            for semitone in range(12):  # 12 semitones per octave
                midi_note = (self.base_octave + octave) * 12 + semitone
                x = (octave * 12 + semitone) * semitone_width
                
                # Determine if it's a black key
                is_black_key = semitone in [1, 3, 6, 8, 10]  # C#, D#, F#, G#, A#
                
                if is_black_key:
                    # Draw black key
                    key_width = semitone_width
                    key_height = widget_height * 0.6  # Black keys are shorter
                    self._draw_black_key(painter, x, key_width, key_height, midi_note)
                else:
                    # Draw white key
                    key_width = semitone_width
                    key_height = widget_height
                    self._draw_white_key(painter, x, key_width, key_height, midi_note)
    
    def _draw_white_keys(self, painter: QPainter, key_width: float, key_height: float):
        """Draw white piano keys with realistic 3D effect"""
        white_key_pattern = [0, 2, 4, 5, 7, 9, 11]  # C D E F G A B
        
        for octave in range(self.visible_octaves):
            for i, note_offset in enumerate(white_key_pattern):
                midi_note = (self.base_octave + octave) * 12 + note_offset
                x = (octave * 7 + i) * key_width
                
                # Choose base color
                if midi_note in self.pressed_notes:
                    base_color = self.pressed_color
                    # Darker shadow when pressed
                    shadow_color = QColor(base_color.red() - 30, base_color.green() - 30, base_color.blue() - 30)
                else:
                    base_color = self.white_key_color
                    # Light gray shadow for unpressed keys
                    shadow_color = QColor(220, 220, 220)
                
                # Draw main key surface
                painter.setPen(QPen(self.border_color, 1))
                painter.setBrush(QBrush(base_color))
                painter.drawRect(int(x), 0, int(key_width), int(key_height))
                
                # Draw subtle right edge shadow for 3D effect
                shadow_width = 2
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(shadow_color))
                painter.drawRect(int(x + key_width - shadow_width), 0, shadow_width, int(key_height))
                
                # Draw subtle bottom edge shadow
                painter.drawRect(int(x), int(key_height - shadow_width), int(key_width), shadow_width)
    
    def _draw_black_keys(self, painter: QPainter, white_key_width: float, 
                        black_key_width: float, black_key_height: float):
        """Draw black piano keys with authentic positioning like real piano"""
        
        for octave in range(self.visible_octaves):
            octave_x_offset = octave * 7 * white_key_width
            
            # C# - between C and D (closer to D)
            midi_note = (self.base_octave + octave) * 12 + 1
            x = octave_x_offset + (0.7 * white_key_width) - black_key_width / 2
            self._draw_single_black_key(painter, x, black_key_width, black_key_height, midi_note)
            
            # D# - between D and E (closer to D)
            midi_note = (self.base_octave + octave) * 12 + 3
            x = octave_x_offset + (1.3 * white_key_width) - black_key_width / 2
            self._draw_single_black_key(painter, x, black_key_width, black_key_height, midi_note)
            
            # No black key between E and F (natural gap in piano layout)
            
            # F# - between F and G (closer to G)
            midi_note = (self.base_octave + octave) * 12 + 6
            x = octave_x_offset + (3.7 * white_key_width) - black_key_width / 2
            self._draw_single_black_key(painter, x, black_key_width, black_key_height, midi_note)
            
            # G# - between G and A (centered)
            midi_note = (self.base_octave + octave) * 12 + 8
            x = octave_x_offset + (4.5 * white_key_width) - black_key_width / 2
            self._draw_single_black_key(painter, x, black_key_width, black_key_height, midi_note)
            
            # A# - between A and B (closer to A)
            midi_note = (self.base_octave + octave) * 12 + 10
            x = octave_x_offset + (5.3 * white_key_width) - black_key_width / 2
            self._draw_single_black_key(painter, x, black_key_width, black_key_height, midi_note)
            
            # No black key between B and C (natural gap in piano layout)
    
    def _draw_single_black_key(self, painter: QPainter, x: float, width: float, height: float, midi_note: int):
        """Draw a single black key with 3D effect"""
        # Choose base color
        if midi_note in self.pressed_notes:
            base_color = self.pressed_color
            # Even darker shadow when pressed
            shadow_color = QColor(max(0, base_color.red() - 40), 
                                 max(0, base_color.green() - 40), 
                                 max(0, base_color.blue() - 40))
        else:
            base_color = self.black_key_color
            # Very dark shadow for black keys
            shadow_color = QColor(10, 10, 10)
        
        # Draw main key surface
        painter.setPen(QPen(QColor(60, 60, 60), 1))  # Dark border for black keys
        painter.setBrush(QBrush(base_color))
        painter.drawRect(int(x), 0, int(width), int(height))
        
        # Draw subtle right edge shadow for 3D effect
        shadow_width = 1
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(shadow_color))
        painter.drawRect(int(x + width - shadow_width), 0, shadow_width, int(height))
        
        # Draw subtle bottom edge shadow
        painter.drawRect(int(x), int(height - shadow_width), int(width), shadow_width)
    
    def _draw_white_key(self, painter: QPainter, x: float, width: float, height: float, midi_note: int):
        """Draw a single white key"""
        # Choose base color
        if midi_note in self.pressed_notes:
            base_color = self.pressed_color
            shadow_color = QColor(base_color.red() - 30, base_color.green() - 30, base_color.blue() - 30)
        else:
            base_color = self.white_key_color
            shadow_color = QColor(220, 220, 220)
        
        # Draw main key surface
        painter.setPen(QPen(self.border_color, 1))
        painter.setBrush(QBrush(base_color))
        painter.drawRect(int(x), 0, int(width), int(height))
        
        # Draw subtle right edge shadow for 3D effect
        shadow_width = 1
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(shadow_color))
        painter.drawRect(int(x + width - shadow_width), 0, shadow_width, int(height))
        
        # Draw subtle bottom edge shadow
        painter.drawRect(int(x), int(height - shadow_width), int(width), shadow_width)
    
    def _draw_black_key(self, painter: QPainter, x: float, width: float, height: float, midi_note: int):
        """Draw a single black key"""
        # Choose base color
        if midi_note in self.pressed_notes:
            base_color = self.pressed_color
            shadow_color = QColor(max(0, base_color.red() - 40), 
                                 max(0, base_color.green() - 40), 
                                 max(0, base_color.blue() - 40))
        else:
            base_color = self.black_key_color
            shadow_color = QColor(10, 10, 10)
        
        # Draw main key surface
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        painter.setBrush(QBrush(base_color))
        painter.drawRect(int(x), 0, int(width), int(height))
        
        # Draw subtle right edge shadow for 3D effect
        shadow_width = 1
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(shadow_color))
        painter.drawRect(int(x + width - shadow_width), 0, shadow_width, int(height))
        
        # Draw subtle bottom edge shadow
        painter.drawRect(int(x), int(height - shadow_width), int(width), shadow_width)