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
        self.visible_keys = 11  # Show only the keys that are actually mapped
        
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
        
        # Enable keyboard focus - critical for key events
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_KeyCompression, False)  # Disable key compression
        self.setTabOrder(None, None)  # Remove from tab order to prevent focus stealing
        
        # Auto-stop timer for note releases
        self.note_stop_timer = QTimer()
        self.note_stop_timer.timeout.connect(self._auto_stop_notes)
        self.note_stop_timer.setSingleShot(False)
        
        # Install event filter to catch Tab key
        self.installEventFilter(self)
        
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
            (Qt.Key_Colon, ":", 17), # F (JIS keyboard friendly)
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
            Qt.Key_Tab: "sustain_toggle",
        }
        
        # Sustain state
        self.sustain_active = False
        self.sustained_notes: Set[int] = set()  # Notes held by sustain pedal
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Control panel
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)
        
        # Piano keyboard display
        self.piano_display = PianoKeyboardDisplay(self, self.key_mappings)
        self.piano_display.setMinimumHeight(120)
        layout.addWidget(self.piano_display)
        
        # Key mapping display
        mapping_panel = self._create_mapping_panel()
        layout.addWidget(mapping_panel)
        
        # Chord display and analysis panels side by side
        chord_analysis_layout = QHBoxLayout()
        
        # Chord display panel
        chord_panel = self._create_chord_display_panel()
        chord_analysis_layout.addWidget(chord_panel, 1)  # Give equal weight
        
        # Chord analysis panel (additional info)
        analysis_panel = self._create_analysis_panel()
        chord_analysis_layout.addWidget(analysis_panel, 1)  # Give equal weight
        
        # Add the horizontal layout to main layout
        layout.addLayout(chord_analysis_layout)
        
        # Update display
        self._update_piano_display()
    
    def _create_control_panel(self):
        """Create control panel with octave and velocity controls"""
        group = QGroupBox("Controls")
        layout = QHBoxLayout(group)
        
        # Current track info
        self.track_info_label = QLabel("Track: --")
        self.track_info_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(self.track_info_label)
        
        # Sustain indicator
        self.sustain_label = QLabel("Sustain: OFF")
        self.sustain_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.sustain_label.setStyleSheet("color: #666; padding: 2px;")
        layout.addWidget(self.sustain_label)
        
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
        """Create control panel with improved horizontal layout and keyboard key visualization"""
        group = QGroupBox("Controls")
        group.setFont(QFont("Arial", 11, QFont.Bold))
        main_layout = QVBoxLayout(group)
        
        # Create horizontal layout for all controls
        controls_layout = QHBoxLayout()
        
        # Octave controls
        octave_widget = QWidget()
        octave_layout = QVBoxLayout(octave_widget)
        octave_layout.setContentsMargins(0, 0, 0, 0)
        
        octave_label = QLabel("Octave:")
        octave_label.setFont(QFont("Arial", 12, QFont.Bold))
        octave_layout.addWidget(octave_label)
        
        octave_keys = self._create_keyboard_key_display(["Z", "X"], ["−", "+"])
        octave_layout.addWidget(octave_keys)
        
        controls_layout.addWidget(octave_widget)
        
        # Velocity controls
        velocity_widget = QWidget()
        velocity_layout = QVBoxLayout(velocity_widget)
        velocity_layout.setContentsMargins(0, 0, 0, 0)
        
        velocity_label = QLabel("Velocity:")
        velocity_label.setFont(QFont("Arial", 12, QFont.Bold))
        velocity_layout.addWidget(velocity_label)
        
        velocity_keys = self._create_keyboard_key_display(["C", "V"], ["−", "+"])
        velocity_layout.addWidget(velocity_keys)
        
        controls_layout.addWidget(velocity_widget)
        
        # Sustain controls
        sustain_widget = QWidget()
        sustain_layout = QVBoxLayout(sustain_widget)
        sustain_layout.setContentsMargins(0, 0, 0, 0)
        
        sustain_label = QLabel("Sustain:")
        sustain_label.setFont(QFont("Arial", 12, QFont.Bold))
        sustain_layout.addWidget(sustain_label)
        
        sustain_keys = self._create_keyboard_key_display(["Tab"], ["Toggle"])
        sustain_layout.addWidget(sustain_keys)
        
        controls_layout.addWidget(sustain_widget)
        
        # Add less stretch to use more space effectively
        controls_layout.addStretch(1)  # Reduced stretch factor
        
        main_layout.addLayout(controls_layout)
        return group
    
    def _create_keyboard_key_display(self, keys, functions):
        """Create visual keyboard key display with intuitive key-function pairing"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(25)  # Good spacing between different control groups
        
        for i, (key, func) in enumerate(zip(keys, functions)):
            # Create a group container for each key-function pair
            group_container = QWidget()
            group_layout = QHBoxLayout(group_container)
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.setSpacing(3)  # Very close spacing between key and function
            
            # Create keyboard key visual
            key_widget = QWidget()
            key_widget.setFixedSize(50, 32)
            key_widget.setStyleSheet("""
                QWidget {
                    background-color: #f8f8f8;
                    border: 2px solid #aaa;
                    border-radius: 6px;
                    font-weight: bold;
                }
            """)
            
            key_layout = QVBoxLayout(key_widget)
            key_layout.setContentsMargins(3, 3, 3, 3)
            
            key_label = QLabel(key)
            key_label.setFont(QFont("Arial", 12, QFont.Bold))
            key_label.setAlignment(Qt.AlignCenter)
            key_layout.addWidget(key_label)
            
            group_layout.addWidget(key_widget)
            
            # Add function symbol directly next to the key with larger font
            if i < len(functions):
                func_label = QLabel(func)
                func_label.setFont(QFont("Arial", 18, QFont.Bold))  # Much larger function symbol
                func_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                func_label.setStyleSheet("color: #222; font-weight: bold; margin-left: 2px;")
                group_layout.addWidget(func_label)
            
            layout.addWidget(group_container)
        
        return container
    
    def _create_chord_display_panel(self):
        """Create chord name display panel"""
        group = QGroupBox("Chord Display")
        layout = QVBoxLayout(group)
        
        # Chord name label (large font) - unified design
        self.chord_name_label = QLabel("---")
        self.chord_name_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.chord_name_label.setAlignment(Qt.AlignCenter)
        self.chord_name_label.setStyleSheet("""
            QLabel {
                color: #222;
                background-color: #f5f5f5;
                border: 2px solid #ccc;
                border-radius: 6px;
                padding: 12px;
                min-height: 40px;
            }
        """)
        layout.addWidget(self.chord_name_label)
        
        # Chord notes label (unified with harmonic analysis design)
        self.chord_notes_label = QLabel("Press keys to see chord")
        self.chord_notes_label.setFont(QFont("Arial", 14, QFont.Weight.DemiBold))
        self.chord_notes_label.setAlignment(Qt.AlignCenter)
        self.chord_notes_label.setStyleSheet("""
            QLabel {
                color: #444;
                padding: 10px;
                background-color: #fafafa;
                border-radius: 6px;
                min-height: 35px;
            }
        """)
        layout.addWidget(self.chord_notes_label)
        
        return group
    
    def _create_analysis_panel(self):
        """Create additional harmonic analysis panel"""
        group = QGroupBox("Harmonic Analysis")
        layout = QVBoxLayout(group)
        
        # Interval analysis label with improved visibility
        self.interval_analysis_label = QLabel("---")
        self.interval_analysis_label.setFont(QFont("Arial", 15, QFont.Weight.DemiBold))
        self.interval_analysis_label.setAlignment(Qt.AlignCenter)
        self.interval_analysis_label.setStyleSheet("""
            QLabel {
                color: #333;
                padding: 12px;
                background-color: #f5f5f5;
                border: 2px solid #ccc;
                border-radius: 6px;
                min-height: 40px;
            }
        """)
        layout.addWidget(self.interval_analysis_label)
        
        # Key suggestion label with better contrast
        self.key_suggestion_label = QLabel("Possible keys: ---")
        self.key_suggestion_label.setFont(QFont("Arial", 14, QFont.Weight.DemiBold))
        self.key_suggestion_label.setAlignment(Qt.AlignCenter)
        self.key_suggestion_label.setStyleSheet("""
            QLabel {
                color: #444;
                padding: 10px;
                background-color: #fafafa;
                border-radius: 6px;
                min-height: 35px;
            }
        """)
        layout.addWidget(self.key_suggestion_label)
        
        return group
    
    def _update_piano_display(self):
        """Update piano keyboard visual display"""
        if hasattr(self, 'piano_display'):
            self.piano_display.set_base_octave(self.base_octave)
            self.piano_display.set_visible_keys(self.visible_keys)
            # Show both pressed notes and sustained notes
            all_active_notes = self.pressed_notes | self.sustained_notes
            self.piano_display.set_pressed_notes(all_active_notes)
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
        
        # Debug output for troubleshooting
        print(f"Virtual Keyboard: Key pressed - code: {key_code}, text: '{event.text()}', key: {hex(key_code)}")
        
        # Prevent key repeat
        if event.isAutoRepeat():
            return
            
        # Check if key is already pressed
        if key_code in self.pressed_keys:
            return
            
        self.pressed_keys.add(key_code)
        
        # Handle control keys
        if key_code in self.control_keys:
            print(f"Virtual Keyboard: Control key detected - {self.control_keys[key_code]}")
            self._handle_control_key(self.control_keys[key_code])
            event.accept()  # Mark event as handled
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
                
                # Check if sustain is active
                if self.sustain_active:
                    # Add to sustained notes instead of releasing immediately
                    self.sustained_notes.add(midi_pitch)
                    print(f"Virtual Keyboard: Note {midi_pitch} sustained (key released)")
                else:
                    # Normal release
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
        elif control_action == "sustain_toggle":
            self.sustain_active = not self.sustain_active
            self._update_sustain_display()
            self._send_sustain_message()
            
            # If turning sustain OFF, release all sustained notes
            if not self.sustain_active:
                self._release_sustained_notes()
    
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
            # Consider both pressed notes and sustained notes for chord analysis
            all_active_notes = self.pressed_notes | self.sustained_notes
            if not all_active_notes:
                # No notes pressed - clear display
                self.chord_name_label.setText("---")
                self.chord_notes_label.setText("Press keys to see chord")
                self._clear_analysis_display()
                return
            
            # Convert MIDI pitches to sorted list
            pitches = sorted(list(all_active_notes))
            
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
            self.chord_notes_label.setText(f"{len(all_active_notes)} notes - detection failed")
    
    def update_track_info(self, track_name: str, source_name: str = ""):
        """Update current track information display"""
        info_text = f"Track: {track_name}"
        if source_name:
            info_text += f" • {source_name}"
        self.track_info_label.setText(info_text)
    
    def _update_sustain_display(self):
        """Update sustain indicator display"""
        if self.sustain_active:
            self.sustain_label.setText("Sustain: ON")
            self.sustain_label.setStyleSheet("color: #00a000; font-weight: bold; padding: 2px;")
        else:
            self.sustain_label.setText("Sustain: OFF")
            self.sustain_label.setStyleSheet("color: #666; padding: 2px;")
    
    def _send_sustain_message(self):
        """Send sustain pedal MIDI message"""
        try:
            # MIDI Control Change 64 (Sustain Pedal)
            # Value 127 = ON, Value 0 = OFF
            sustain_value = 127 if self.sustain_active else 0
            
            # Emit sustain control change on all channels for compatibility
            from src.audio_routing_coordinator import get_audio_routing_coordinator
            
            coordinator = get_audio_routing_coordinator()
            if coordinator:
                # Send sustain CC to active track
                coordinator.send_control_change(0, 64, sustain_value)  # CC64 = Sustain
                print(f"Sustain {'ON' if self.sustain_active else 'OFF'}: CC64 = {sustain_value}")
            
        except Exception as e:
            print(f"Error sending sustain message: {e}")
    
    def _release_sustained_notes(self):
        """Release all notes that are being held by sustain pedal"""
        for pitch in list(self.sustained_notes):
            self.note_released.emit(pitch)
            print(f"Virtual Keyboard: Released sustained note {pitch}")
        
        self.sustained_notes.clear()
        self._update_piano_display()
        self._update_chord_display()
    
    def showEvent(self, event):
        """Handle show event"""
        super().showEvent(event)
        self.setFocus(Qt.OtherFocusReason)  # Ensure keyboard focus
        self.activateWindow()  # Bring to front
        print("Virtual Keyboard: Focus set and window activated")
    
    def closeEvent(self, event):
        """Handle close event"""
        # Stop all notes when closing
        for pitch in list(self.pressed_notes):
            self.note_released.emit(pitch)
        self.pressed_notes.clear()
        
        # Turn off sustain when closing
        if self.sustain_active:
            self.sustain_active = False
            self._send_sustain_message()
            self._release_sustained_notes()
        
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
    
    def eventFilter(self, obj, event):
        """Event filter to catch Tab key events"""
        if event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key_Tab:
                print("Virtual Keyboard: Tab key caught by event filter")
                if not event.isAutoRepeat() and Qt.Key_Tab not in self.pressed_keys:
                    self.pressed_keys.add(Qt.Key_Tab)
                    self._handle_control_key("sustain_toggle")
                return True  # Event handled
        elif event.type() == event.Type.KeyRelease:
            if event.key() == Qt.Key_Tab:
                self.pressed_keys.discard(Qt.Key_Tab)
                return True  # Event handled
        
        return super().eventFilter(obj, event)


class PianoKeyboardDisplay(QWidget):
    """Visual display of piano keyboard with key highlighting"""
    
    def __init__(self, parent=None, key_mappings=None):
        super().__init__(parent)
        self.base_octave = 4
        self.pressed_notes: Set[int] = set()
        self.visible_keys = 11  # Number of white keys to display
        self.key_mappings = key_mappings or {}
        
        # Modern color scheme
        self.white_key_color = QColor(250, 250, 250)
        self.white_key_pressed = QColor(64, 158, 255)
        self.black_key_color = QColor(45, 45, 50)
        self.black_key_pressed = QColor(100, 180, 255)
        self.border_color = QColor(200, 200, 200)
        self.shadow_color = QColor(0, 0, 0, 30)
        
        # Special key styling
        self.special_key_bg = QColor(255, 255, 255, 200)
        self.special_key_border = QColor(100, 100, 100)
        
        # Create reverse mapping from MIDI note to key name
        self.note_to_key = {}
        if self.key_mappings:
            for key_code, mapping in self.key_mappings.items():
                self.note_to_key[mapping.midi_note] = mapping.key_name
    
    def set_base_octave(self, octave: int):
        """Set base octave for display"""
        self.base_octave = octave
        self.update()
    
    def set_visible_keys(self, keys: int):
        """Set number of visible white keys"""
        self.visible_keys = keys
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
        white_key_width = widget_width / self.visible_keys
        white_key_height = widget_height
        black_key_width = white_key_width * 0.6
        black_key_height = white_key_height * 0.6
        
        # Draw white keys first
        self._draw_white_keys(painter, white_key_width, white_key_height)
        
        # Draw black keys on top
        self._draw_black_keys(painter, white_key_width, black_key_width, black_key_height)
    
    def _draw_white_keys(self, painter: QPainter, key_width: float, key_height: float):
        """Draw white piano keys - exactly 11 keys to match keyboard mapping"""
        # Define the 11 white keys in order: C D E F G A B C D E F
        white_key_offsets = [0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17]  # 1 octave + 4 keys
        
        for i in range(min(self.visible_keys, len(white_key_offsets))):
            note_offset = white_key_offsets[i]
            midi_note = self.base_octave * 12 + note_offset
            x = i * key_width
            
            # Choose color
            if midi_note in self.pressed_notes:
                color = self.white_key_pressed
            else:
                color = self.white_key_color
            
            # Draw key with modern styling
            key_rect = int(x), 0, int(key_width), int(key_height)
            
            # Draw shadow first
            shadow_rect = (int(x + 2), 2, int(key_width), int(key_height))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self.shadow_color))
            painter.drawRect(*shadow_rect)
            
            # Draw main key
            painter.setPen(QPen(self.border_color, 1.5))
            painter.setBrush(QBrush(color))
            painter.drawRect(*key_rect)
            
            # Draw key letter if mapping exists
            key_letter = self.note_to_key.get(note_offset, "")
            if key_letter:
                self._draw_key_label(painter, key_letter, x, key_height, key_width, True)
    
    def _draw_black_keys(self, painter: QPainter, white_key_width: float, 
                        black_key_width: float, black_key_height: float):
        """Draw black piano keys - 7 keys to match our 11 white key layout"""
        # Black key positions and offsets for our 11-key layout: C D E F G A B C D E F
        # Positions: after 1st, 2nd, 4th, 5th, 6th, 8th, 9th white keys
        black_key_positions = [0.7, 1.7, 3.7, 4.7, 5.7, 7.7, 8.7]  # Relative positions
        black_note_offsets = [1, 3, 6, 8, 10, 13, 15]  # C# D# F# G# A# C# D#
        
        for i, (pos, note_offset) in enumerate(zip(black_key_positions, black_note_offsets)):
            # Only draw black keys that fit within our visible keys
            if pos < self.visible_keys - 0.5:  # Leave space for black key width
                midi_note = self.base_octave * 12 + note_offset
                x = pos * white_key_width - black_key_width / 2
                
                # Choose color
                if midi_note in self.pressed_notes:
                    color = self.black_key_pressed
                else:
                    color = self.black_key_color
                
                # Draw black key with modern styling
                black_key_rect = int(x), 0, int(black_key_width), int(black_key_height)
                
                # Draw shadow
                shadow_rect = (int(x + 1), 1, int(black_key_width), int(black_key_height))
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(0, 0, 0, 40)))
                painter.drawRect(*shadow_rect)
                
                # Draw main black key
                painter.setPen(QPen(QColor(30, 30, 35), 1.5))
                painter.setBrush(QBrush(color))
                painter.drawRect(*black_key_rect)
                
                # Draw key letter if mapping exists
                key_letter = self.note_to_key.get(note_offset, "")
                if key_letter:
                    self._draw_key_label(painter, key_letter, x, black_key_height, black_key_width, False)
    
    def _draw_key_label(self, painter: QPainter, key_letter: str, x: float, 
                       key_height: float, key_width: float, is_white_key: bool):
        """Draw key letter label with modern styling"""
        # Font sizing based on key type and special characters
        if key_letter in [";", ":"]:
            # Special styling for semicolon and colon keys
            font_size = 16 if is_white_key else 14
            font = QFont("Arial", font_size, QFont.Bold)
        else:
            # Regular keys
            font_size = 14 if is_white_key else 12
            font = QFont("Arial", font_size, QFont.Bold)
        
        painter.setFont(font)
        
        # Color scheme based on key type
        if is_white_key:
            if key_letter in [";", ":"]:
                # Special styling for punctuation on white keys
                text_color = QColor(50, 50, 150)  # Deep blue for visibility
                bg_color = QColor(255, 255, 255, 180)  # Semi-transparent white background
                border_color = QColor(100, 100, 150)
            else:
                # Regular white key styling
                text_color = QColor(60, 60, 60)  # Dark gray
                bg_color = QColor(255, 255, 255, 120)  # Light background
                border_color = QColor(180, 180, 180)
        else:
            # Black key styling
            if key_letter in [";", ":"]:
                # Special styling for punctuation on black keys
                text_color = QColor(255, 255, 100)  # Bright yellow for contrast
                bg_color = QColor(0, 0, 0, 100)  # Semi-transparent black
                border_color = QColor(200, 200, 100)
            else:
                # Regular black key styling
                text_color = QColor(255, 255, 255)  # White text
                bg_color = QColor(0, 0, 0, 80)  # Dark background
                border_color = QColor(150, 150, 150)
        
        # Calculate text position
        text_rect = painter.fontMetrics().boundingRect(key_letter)
        text_x = x + (key_width - text_rect.width()) / 2
        text_y = key_height - 15 if is_white_key else key_height - 10
        
        # No background border needed - current font size is sufficient for visibility
        
        # Draw text
        painter.setPen(QPen(text_color))
        painter.setBrush(Qt.NoBrush)
        painter.drawText(int(text_x), int(text_y), key_letter)