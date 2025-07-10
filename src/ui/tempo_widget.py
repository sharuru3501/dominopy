"""
Tempo and time signature control widget for PyDomino
"""
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                              QSpinBox, QComboBox, QPushButton, QGroupBox)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
from typing import Tuple

from src.playback_engine import get_playback_engine
from src.midi_data_model import MidiProject


class TempoWidget(QWidget):
    """Widget for tempo control"""
    
    tempo_changed = Signal(float)  # BPM changed
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.current_tempo = 120.0
    
    def setup_ui(self):
        """Setup the UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Tempo label
        tempo_label = QLabel("Tempo:")
        tempo_label.setFont(QFont("Arial", 9))
        layout.addWidget(tempo_label)
        
        # BPM spinbox
        self.bpm_spinbox = QSpinBox()
        self.bpm_spinbox.setRange(20, 300)
        self.bpm_spinbox.setValue(120)
        self.bpm_spinbox.setSuffix(" BPM")
        self.bpm_spinbox.setMinimumWidth(80)
        self.bpm_spinbox.valueChanged.connect(self._on_tempo_changed)
        layout.addWidget(self.bpm_spinbox)
        
        # Preset tempo buttons
        preset_tempos = [
            ("Slow", 60),
            ("Moderate", 120),
            ("Fast", 140),
            ("Very Fast", 180)
        ]
        
        for name, bpm in preset_tempos:
            btn = QPushButton(name)
            btn.setMaximumWidth(60)
            btn.clicked.connect(lambda checked, b=bpm: self.set_tempo(b))
            layout.addWidget(btn)
    
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


class TimeSignatureWidget(QWidget):
    """Widget for time signature control"""
    
    time_signature_changed = Signal(int, int)  # numerator, denominator
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.current_time_signature = (4, 4)
    
    def setup_ui(self):
        """Setup the UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Time signature label
        ts_label = QLabel("Time Sig:")
        ts_label.setFont(QFont("Arial", 9))
        layout.addWidget(ts_label)
        
        # Time signature combo box
        self.time_sig_combo = QComboBox()
        self.time_sig_combo.addItems([
            "4/4", "3/4", "2/4", "6/8", "9/8", "12/8",
            "5/4", "7/8", "11/8", "2/2", "3/8"
        ])
        self.time_sig_combo.setCurrentText("4/4")
        self.time_sig_combo.currentTextChanged.connect(self._on_time_signature_changed)
        layout.addWidget(self.time_sig_combo)
        
        # Custom time signature
        layout.addWidget(QLabel("/"))
        
        self.numerator_spinbox = QSpinBox()
        self.numerator_spinbox.setRange(1, 32)
        self.numerator_spinbox.setValue(4)
        self.numerator_spinbox.setMaximumWidth(50)
        self.numerator_spinbox.valueChanged.connect(self._on_custom_time_sig_changed)
        layout.addWidget(self.numerator_spinbox)
        
        layout.addWidget(QLabel("/"))
        
        self.denominator_spinbox = QSpinBox()
        self.denominator_spinbox.setRange(1, 32)
        self.denominator_spinbox.setValue(4)
        self.denominator_spinbox.setMaximumWidth(50)
        self.denominator_spinbox.valueChanged.connect(self._on_custom_time_sig_changed)
        layout.addWidget(self.denominator_spinbox)
    
    def _on_time_signature_changed(self, text: str):
        """Handle time signature combo change"""
        try:
            parts = text.split('/')
            numerator = int(parts[0])
            denominator = int(parts[1])
            
            self.numerator_spinbox.setValue(numerator)
            self.denominator_spinbox.setValue(denominator)
            
            self.current_time_signature = (numerator, denominator)
            self.time_signature_changed.emit(numerator, denominator)
            
        except (ValueError, IndexError):
            pass
    
    def _on_custom_time_sig_changed(self):
        """Handle custom time signature change"""
        numerator = self.numerator_spinbox.value()
        denominator = self.denominator_spinbox.value()
        
        # Update combo box if it matches a preset
        preset_text = f"{numerator}/{denominator}"
        index = self.time_sig_combo.findText(preset_text)
        if index >= 0:
            self.time_sig_combo.setCurrentIndex(index)
        else:
            self.time_sig_combo.setCurrentText(preset_text)
        
        self.current_time_signature = (numerator, denominator)
        self.time_signature_changed.emit(numerator, denominator)
    
    def set_time_signature(self, numerator: int, denominator: int):
        """Set time signature programmatically"""
        self.numerator_spinbox.setValue(numerator)
        self.denominator_spinbox.setValue(denominator)
    
    def get_time_signature(self) -> Tuple[int, int]:
        """Get current time signature"""
        return self.current_time_signature


class MetronomeWidget(QWidget):
    """Widget for metronome control"""
    
    metronome_toggled = Signal(bool)
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.metronome_enabled = False
        
        # Metronome timer
        self.metronome_timer = QTimer()
        self.metronome_timer.timeout.connect(self._metronome_tick)
        self.current_beat = 0
    
    def setup_ui(self):
        """Setup the UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Metronome button
        self.metronome_btn = QPushButton("🥁 Metronome")
        self.metronome_btn.setCheckable(True)
        self.metronome_btn.clicked.connect(self._toggle_metronome)
        layout.addWidget(self.metronome_btn)
        
        # Beat indicator
        self.beat_label = QLabel("♩")
        self.beat_label.setFont(QFont("Arial", 16))
        self.beat_label.setStyleSheet("color: #6272a4;")
        layout.addWidget(self.beat_label)
    
    def _toggle_metronome(self, checked: bool):
        """Toggle metronome on/off"""
        self.metronome_enabled = checked
        self.metronome_toggled.emit(checked)
        
        if checked:
            self.metronome_btn.setText("🔇 Metronome")
            self.metronome_btn.setStyleSheet("background-color: #50fa7b; color: black;")
            self._start_metronome()
        else:
            self.metronome_btn.setText("🥁 Metronome")
            self.metronome_btn.setStyleSheet("")
            self._stop_metronome()
    
    def _start_metronome(self):
        """Start metronome timer"""
        # Calculate interval based on current tempo
        engine = get_playback_engine()
        if engine:
            tempo = engine.get_tempo()
            interval_ms = int(60000 / tempo)  # milliseconds per beat
            self.metronome_timer.start(interval_ms)
            self.current_beat = 0
    
    def _stop_metronome(self):
        """Stop metronome timer"""
        self.metronome_timer.stop()
        self.beat_label.setStyleSheet("color: #6272a4;")
    
    def _metronome_tick(self):
        """Handle metronome tick"""
        self.current_beat = (self.current_beat + 1) % 4
        
        # Visual feedback
        if self.current_beat == 0:
            # Downbeat - stronger visual
            self.beat_label.setText("♩")
            self.beat_label.setStyleSheet("color: #ff79c6; font-weight: bold;")
        else:
            # Regular beat
            self.beat_label.setText("♪")
            self.beat_label.setStyleSheet("color: #8be9fd;")
        
        # TODO: Add audio click sound
        print(f"Metronome tick: beat {self.current_beat + 1}")
    
    def update_tempo(self, tempo: float):
        """Update metronome tempo"""
        if self.metronome_enabled:
            interval_ms = int(60000 / tempo)
            self.metronome_timer.setInterval(interval_ms)


class TempoTimeSignatureWidget(QWidget):
    """Combined tempo and time signature control widget"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup the UI"""
        # Main group box
        group = QGroupBox("Tempo & Time Signature")
        group.setFont(QFont("Arial", 9, QFont.Bold))
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(group)
        
        # Group content
        group_layout = QVBoxLayout(group)
        
        # Top row: Tempo and time signature
        top_layout = QHBoxLayout()
        
        self.tempo_widget = TempoWidget()
        top_layout.addWidget(self.tempo_widget)
        
        # Separator
        separator = QLabel("|")
        separator.setStyleSheet("color: #6272a4;")
        top_layout.addWidget(separator)
        
        self.time_sig_widget = TimeSignatureWidget()
        top_layout.addWidget(self.time_sig_widget)
        
        top_layout.addStretch()
        group_layout.addLayout(top_layout)
        
        # Bottom row: Metronome
        self.metronome_widget = MetronomeWidget()
        group_layout.addWidget(self.metronome_widget)
    
    def connect_signals(self):
        """Connect widget signals"""
        self.tempo_widget.tempo_changed.connect(self.metronome_widget.update_tempo)
    
    def get_tempo(self) -> float:
        """Get current tempo"""
        return self.tempo_widget.get_tempo()
    
    def get_time_signature(self) -> Tuple[int, int]:
        """Get current time signature"""
        return self.time_sig_widget.get_time_signature()
    
    def set_tempo(self, bpm: float):
        """Set tempo"""
        self.tempo_widget.set_tempo(bpm)
    
    def set_time_signature(self, numerator: int, denominator: int):
        """Set time signature"""
        self.time_sig_widget.set_time_signature(numerator, denominator)