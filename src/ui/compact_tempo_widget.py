"""
Compact tempo and time signature widgets for toolbar integration
"""
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QSpinBox, 
                              QComboBox, QPushButton, QFrame)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
from typing import Tuple

from src.playback_engine import get_playback_engine


class CompactTempoWidget(QWidget):
    """Compact tempo control widget for toolbar"""
    
    tempo_changed = Signal(float)
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.current_tempo = 120.0
    
    def setup_ui(self):
        """Setup compact UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)
        
        # Tempo label
        tempo_label = QLabel("🎵")
        tempo_label.setToolTip("Tempo (BPM)")
        layout.addWidget(tempo_label)
        
        # BPM spinbox
        self.bpm_spinbox = QSpinBox()
        self.bpm_spinbox.setRange(20, 300)
        self.bpm_spinbox.setValue(120)
        self.bpm_spinbox.setSuffix(" BPM")
        self.bpm_spinbox.setMaximumWidth(85)
        self.bpm_spinbox.setToolTip("Set tempo in beats per minute")
        self.bpm_spinbox.valueChanged.connect(self._on_tempo_changed)
        layout.addWidget(self.bpm_spinbox)
    
    def _on_tempo_changed(self, value: int):
        """Handle tempo change"""
        self.current_tempo = float(value)
        self.tempo_changed.emit(self.current_tempo)
        
        # Update playback engine
        engine = get_playback_engine()
        if engine:
            engine.set_tempo(self.current_tempo)
    
    def set_tempo(self, bpm: float):
        """Set tempo programmatically"""
        self.bpm_spinbox.setValue(int(bpm))
    
    def get_tempo(self) -> float:
        """Get current tempo"""
        return self.current_tempo


class CompactTimeSignatureWidget(QWidget):
    """Compact time signature control widget for toolbar"""
    
    time_signature_changed = Signal(int, int)
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.current_time_signature = (4, 4)
    
    def setup_ui(self):
        """Setup compact UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)
        
        # Time signature label
        ts_label = QLabel("🎼")
        ts_label.setToolTip("Time Signature")
        layout.addWidget(ts_label)
        
        # Time signature combo box
        self.time_sig_combo = QComboBox()
        self.time_sig_combo.addItems([
            "4/4", "3/4", "2/4", "6/8", "9/8", "12/8", "5/4", "7/8"
        ])
        self.time_sig_combo.setCurrentText("4/4")
        self.time_sig_combo.setMaximumWidth(80)
        self.time_sig_combo.setToolTip("Set time signature")
        self.time_sig_combo.currentTextChanged.connect(self._on_time_signature_changed)
        layout.addWidget(self.time_sig_combo)
    
    def _on_time_signature_changed(self, text: str):
        """Handle time signature combo change"""
        try:
            parts = text.split('/')
            numerator = int(parts[0])
            denominator = int(parts[1])
            
            self.current_time_signature = (numerator, denominator)
            self.time_signature_changed.emit(numerator, denominator)
            
        except (ValueError, IndexError):
            pass
    
    def set_time_signature(self, numerator: int, denominator: int):
        """Set time signature programmatically"""
        preset_text = f"{numerator}/{denominator}"
        index = self.time_sig_combo.findText(preset_text)
        if index >= 0:
            self.time_sig_combo.setCurrentIndex(index)
        else:
            self.time_sig_combo.addItem(preset_text)
            self.time_sig_combo.setCurrentText(preset_text)
    
    def get_time_signature(self) -> Tuple[int, int]:
        """Get current time signature"""
        return self.current_time_signature


class CompactMusicInfoWidget(QWidget):
    """Compact music info widget for toolbar"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.current_notes = []
        self.current_project = None
        
        # Update timer for playhead position
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_playhead_info)
        self.update_timer.start(100)  # Update every 100ms
# print("DEBUG: CompactMusicInfoWidget timer started")
    
    def setup_ui(self):
        """Setup compact UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)
        
        # Unified music info frame
        music_frame = QFrame()
        music_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        music_layout = QHBoxLayout(music_frame)
        music_layout.setContentsMargins(5, 2, 5, 2)
        
        self.music_label = QLabel("♪ No notes")
        self.music_label.setFont(QFont("Arial", 9))
        self.music_label.setStyleSheet("color: #000000; font-weight: bold; background-color: #f0f0f0; padding: 2px;")
        self.music_label.setMinimumWidth(200)  # Unified wider width
        music_layout.addWidget(self.music_label)
        
        layout.addWidget(music_frame)
    
    def update_notes(self, midi_pitches):
        """Update displayed notes in unified format"""
        from src.music_theory import MusicTheory, analyze_harmony
        from src.settings import get_settings_manager
        
        if not midi_pitches:
            self.music_label.setText("♪ No notes")
            return
        
        # Get octave offset from settings
        settings_manager = get_settings_manager()
        octave_offset = settings_manager.get_midi_to_octave_offset()
        
        # Analyze harmony
        harmony = analyze_harmony(midi_pitches)
        
        # Create unified display
        if len(midi_pitches) == 1:
            # Single note
            note_name = MusicTheory.get_note_name_with_octave(midi_pitches[0], octave_offset=octave_offset)
            self.music_label.setText(f"♪ {note_name}")
        else:
            # Multiple notes - show chord info if available
            if harmony["chord"]:
                chord = harmony["chord"]
                # Get note names for the chord
                sorted_pitches = sorted(set(midi_pitches))
                note_names = [MusicTheory.get_note_name(pitch, octave_offset=octave_offset) for pitch in sorted_pitches]
                unique_names = list(dict.fromkeys(note_names))  # Preserve order, remove duplicates
                
                if len(unique_names) > 4:
                    notes_str = ', '.join(unique_names[:4]) + "..."
                else:
                    notes_str = ', '.join(unique_names)
                
                # Show chord name with constituent notes
                self.music_label.setText(f"🎵 {chord.name} ({notes_str})")
            else:
                # No chord detected - just show notes
                sorted_pitches = sorted(set(midi_pitches))
                note_names = [MusicTheory.get_note_name(pitch, octave_offset=octave_offset) for pitch in sorted_pitches]
                unique_names = list(dict.fromkeys(note_names))  # Preserve order, remove duplicates
                
                if len(unique_names) > 4:
                    notes_str = ', '.join(unique_names[:4]) + "..."
                else:
                    notes_str = ', '.join(unique_names)
                
                self.music_label.setText(f"♪ {notes_str} ({len(set(midi_pitches))} notes)")
    
    def update_selected_notes(self, selected_notes):
        """Update from selected notes (only if no playback is active)"""
        engine = get_playback_engine()
        if engine and engine.is_playing():
            # During playback, show playhead info instead
            return
        
        pitches = [note.pitch for note in selected_notes]
        self.update_notes(pitches)
    
    def set_project(self, project):
        """Set the current MIDI project"""
        self.current_project = project
        # Project updated silently
    
    def set_chord_text(self, chord_info: str):
        """Set chord text directly (for external updates)"""
        self.music_label.setText(f"🎵 {chord_info}")
    
    def _update_playhead_info(self):
        """Update information based on playhead position"""
        engine = get_playback_engine()
        
        if not engine or not self.current_project:
            return
        
        is_playing = engine.is_playing()
        
        if is_playing:
            # During playback, show playhead info
            current_tick = engine.get_current_tick()
            
            # Get notes currently playing at this position
            playing_notes = self.current_project.get_notes_at_tick(current_tick)
            
            if playing_notes:
                # Show currently playing notes
                pitches = [note.pitch for note in playing_notes]
                self.update_notes(pitches)
            else:
                # No notes playing, show "Playing..." 
                self.music_label.setText("♪ Playing...")
        else:
            # Not playing - check if we need to revert to "No notes" state
            if self.music_label.text() == "♪ Playing...":
                self.music_label.setText("♪ No notes")


class CompactPlaybackInfoWidget(QWidget):
    """Compact playback info widget for toolbar"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup compact UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)
        
        # Position label with icon
        position_frame = QFrame()
        position_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        position_layout = QHBoxLayout(position_frame)
        position_layout.setContentsMargins(5, 2, 5, 2)
        
        # Time icon
        time_icon = QLabel("🕐")
        time_icon.setToolTip("Playback Position")
        position_layout.addWidget(time_icon)
        
        # Position
        self.position_label = QLabel("0:00")
        self.position_label.setFont(QFont("Arial", 9))
        self.position_label.setStyleSheet("color: #000000; font-weight: bold;")
        self.position_label.setMinimumWidth(40)
        self.position_label.setToolTip("Playback Position")
        position_layout.addWidget(self.position_label)
        
        layout.addWidget(position_frame)
    
    def update_playback_info(self, state, current_tick, tempo_bpm):
        """Update playback information"""        
        # Update position
        ticks_per_beat = 480  # Default
        beats = current_tick / ticks_per_beat
        minutes = int(beats / tempo_bpm)
        seconds = int((beats / tempo_bpm * 60) % 60)
        
        self.position_label.setText(f"{minutes}:{seconds:02d}")


class ToolbarSeparator(QFrame):
    """Vertical separator for toolbar"""
    
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)
        self.setStyleSheet("color: #6272a4;")
        self.setMaximumHeight(30)