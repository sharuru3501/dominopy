"""
Application settings management for PyDomino
"""
import json
import os
from typing import Dict, Any
from enum import Enum
from dataclasses import dataclass, asdict

class OctaveStandard(Enum):
    """MIDI octave naming standards"""
    YAMAHA = "yamaha"      # C3 = MIDI note 60 (Middle C)
    ROLAND = "roland"      # C4 = MIDI note 60 (Middle C) - Default
    SCIENTIFIC = "scientific"  # C4 = MIDI note 60 (Scientific pitch notation)

@dataclass
class DisplaySettings:
    """Display and UI settings"""
    # Grid dimensions - using pixels per tick for more intuitive control
    grid_width_pixels: float = 0.15      # Pixels per tick (horizontal zoom) - optimal value
    grid_height_pixels: float = 8.0      # Pixels per semitone (vertical zoom) - show more range
    
    # Note display
    octave_standard: str = OctaveStandard.ROLAND.value
    
    # Piano roll appearance
    show_note_names: bool = True
    show_grid_lines: bool = True
    snap_to_grid: bool = True
    
    # Colors (hex values)
    background_color: str = "#282c34"
    grid_color: str = "#44475a"
    note_color: str = "#50fa7b"
    selected_note_color: str = "#ffb86c"

@dataclass
class AudioSettings:
    """Audio system settings"""
    sample_rate: int = 44100
    buffer_size: int = 1024
    gain: float = 0.5
    soundfont_path: str = ""
    midi_device_id: int = -1

@dataclass
class AppSettings:
    """Main application settings"""
    display: DisplaySettings
    audio: AudioSettings
    
    # Window state
    window_width: int = 1200
    window_height: int = 800
    window_maximized: bool = False

class SettingsManager:
    """Manages application settings"""
    
    def __init__(self):
        self.settings_file = os.path.expanduser("~/.pydomino_settings.json")
        self.settings = self._load_default_settings()
        self.load_settings()
    
    def _load_default_settings(self) -> AppSettings:
        """Load default settings"""
        return AppSettings(
            display=DisplaySettings(),
            audio=AudioSettings()
        )
    
    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                
                # Parse display settings
                display_data = data.get('display', {})
                display = DisplaySettings(**display_data)
                
                # Parse audio settings
                audio_data = data.get('audio', {})
                audio = AudioSettings(**audio_data)
                
                # Parse main settings
                self.settings = AppSettings(
                    display=display,
                    audio=audio,
                    window_width=data.get('window_width', 1200),
                    window_height=data.get('window_height', 800),
                    window_maximized=data.get('window_maximized', False)
                )
                
                print(f"Settings loaded from {self.settings_file}")
        except Exception as e:
            print(f"Error loading settings: {e}")
            self.settings = self._load_default_settings()
    
    def save_settings(self):
        """Save settings to file"""
        try:
            data = {
                'display': asdict(self.settings.display),
                'audio': asdict(self.settings.audio),
                'window_width': self.settings.window_width,
                'window_height': self.settings.window_height,
                'window_maximized': self.settings.window_maximized
            }
            
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"Settings saved to {self.settings_file}")
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get_midi_to_octave_offset(self) -> int:
        """Get the octave offset for MIDI note to octave conversion"""
        standard = OctaveStandard(self.settings.display.octave_standard)
        if standard == OctaveStandard.YAMAHA:
            return -2  # YAMAHA: C3 = MIDI 60, so offset is -2
        elif standard == OctaveStandard.ROLAND:
            return -1  # ROLAND: C4 = MIDI 60, so offset is -1 (default)
        else:  # SCIENTIFIC
            return -1  # Same as Roland
    
    def get_octave_display_name(self, midi_pitch: int) -> str:
        """Get octave display name based on current standard"""
        octave = midi_pitch // 12 + self.get_midi_to_octave_offset()
        note_index = midi_pitch % 12
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return f"{note_names[note_index]}{octave}"

# Global settings manager instance
_settings_manager = None

def get_settings_manager() -> SettingsManager:
    """Get the global settings manager instance"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager

def get_settings() -> AppSettings:
    """Get current application settings"""
    return get_settings_manager().settings

def save_settings():
    """Save current settings to file"""
    get_settings_manager().save_settings()