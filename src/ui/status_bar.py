"""
Status bar for DominoPy
Displays real-time information about notes, chords, tempo, and playback
"""
from PySide6.QtWidgets import QStatusBar, QLabel, QWidget, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from typing import List, Optional

from src.music_theory import MusicTheory, analyze_harmony
from src.midi_data_model import MidiNote
from src.playback_engine import get_playback_engine, PlaybackState


class MusicInfoWidget(QWidget):
    """Widget to display music information (notes, chords)"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.current_notes: List[int] = []
        self.selected_notes: List[MidiNote] = []
    
    def setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(1)
        
        # Note names display
        self.note_label = QLabel("No notes")
        self.note_label.setFont(QFont("Arial", 9))
        self.note_label.setStyleSheet("color: #8be9fd; font-weight: bold;")
        layout.addWidget(self.note_label)
        
        # Chord display
        self.chord_label = QLabel("No chord")
        self.chord_label.setFont(QFont("Arial", 8))
        self.chord_label.setStyleSheet("color: #f1fa8c;")
        layout.addWidget(self.chord_label)
    
    def update_notes(self, midi_pitches: List[int]):
        """Update displayed notes"""
        self.current_notes = midi_pitches
        self._update_display()
    
    def update_selected_notes(self, selected_notes: List[MidiNote]):
        """Update from selected notes"""
        self.selected_notes = selected_notes
        pitches = [note.pitch for note in selected_notes]
        self.update_notes(pitches)
    
    def _update_display(self):
        """Update the display labels"""
        if not self.current_notes:
            self.note_label.setText("No notes")
            self.chord_label.setText("No chord")
            return
        
        # Analyze harmony
        harmony = analyze_harmony(self.current_notes)
        
        # Display individual notes
        if len(self.current_notes) == 1:
            note_name = MusicTheory.get_note_name_with_octave(self.current_notes[0])
            self.note_label.setText(f"♪ {note_name}")
        else:
            note_names = [MusicTheory.get_note_name(pitch) for pitch in self.current_notes]
            unique_names = list(dict.fromkeys(note_names))  # Preserve order, remove duplicates
            self.note_label.setText(f"♪ {', '.join(unique_names)}")
        
        # Display chord
        if harmony["chord"]:
            chord = harmony["chord"]
            self.chord_label.setText(f"🎵 {chord.name}")
        else:
            if len(self.current_notes) > 1:
                self.chord_label.setText("🎵 Custom chord")
            else:
                self.chord_label.setText("No chord")


class PlaybackInfoWidget(QWidget):
    """Widget to display playback information"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
        # Timer for updating playback info
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_playback_info)
        self.update_timer.start(100)  # Update every 100ms
    
    def setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(1)
        
        # Playback state and position
        self.state_label = QLabel("⏹️ Stopped")
        self.state_label.setFont(QFont("Arial", 9))
        self.state_label.setStyleSheet("color: #ff79c6; font-weight: bold;")
        layout.addWidget(self.state_label)
        
        # Position and tempo
        self.position_label = QLabel("0:00 | 120 BPM")
        self.position_label.setFont(QFont("Arial", 8))
        self.position_label.setStyleSheet("color: #50fa7b;")
        layout.addWidget(self.position_label)
    
    def update_playback_info(self):
        """Update playback information"""
        engine = get_playback_engine()
        if not engine:
            return
        
        # Update state
        state = engine.get_state()
        state_icons = {
            PlaybackState.STOPPED: "⏹️",
            PlaybackState.PLAYING: "▶️",
            PlaybackState.PAUSED: "⏸️"
        }
        
        icon = state_icons.get(state, "⏹️")
        self.state_label.setText(f"{icon} {state.value.title()}")
        
        # Update position and tempo
        current_tick = engine.get_current_tick()
        tempo_bpm = engine.get_tempo()
        
        # Convert ticks to time (simplified)
        ticks_per_beat = 480  # Default
        beats = current_tick / ticks_per_beat
        minutes = int(beats / tempo_bpm)
        seconds = int((beats / tempo_bpm * 60) % 60)
        
        self.position_label.setText(f"{minutes}:{seconds:02d} | {tempo_bpm:.0f} BPM")


class DominoPyStatusBar(QStatusBar):
    """Simplified status bar for DominoPy - only shows project info"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the simplified status bar layout"""
        # Project information
        self.project_label = QLabel("New Project")
        self.project_label.setFont(QFont("Arial", 9))
        self.project_label.setStyleSheet("color: #bd93f9; font-weight: bold; padding: 2px;")
        self.addPermanentWidget(self.project_label)
        
        # Set overall styling
        self.setStyleSheet("""
            QStatusBar {
                background-color: #282a36;
                color: #f8f8f2;
                border-top: 1px solid #44475a;
                min-height: 20px;
            }
            QStatusBar::item {
                border: none;
            }
        """)
    
    def update_project_name(self, name: str):
        """Update project name display"""
        self.project_label.setText(name)
    
    def show_message(self, message: str, timeout: int = 2000):
        """Show temporary message"""
        super().showMessage(message, timeout)