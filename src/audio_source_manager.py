"""
Audio Source Manager for Per-Track Audio Sources
Manages soundfont and external MIDI device sources for individual tracks
"""
import os
import glob
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from PySide6.QtCore import QObject, Signal

class AudioSourceType(Enum):
    """Types of audio sources available"""
    SOUNDFONT = "soundfont"
    EXTERNAL_MIDI = "external_midi"
    INTERNAL_FLUIDSYNTH = "internal_fluidsynth"

@dataclass
class AudioSource:
    """Represents an audio source for a track"""
    id: str
    name: str
    source_type: AudioSourceType
    file_path: Optional[str] = None  # For soundfonts
    midi_port_name: Optional[str] = None  # For external MIDI
    program: int = 1  # MIDI program number
    channel: int = 0  # MIDI channel
    
    def __str__(self):
        if self.source_type == AudioSourceType.SOUNDFONT:
            return f"{self.name} (SF2)"
        elif self.source_type == AudioSourceType.EXTERNAL_MIDI:
            return f"{self.name} (MIDI)"
        else:
            return f"{self.name} (Internal)"

@dataclass 
class SoundfontInfo:
    """Information about a soundfont file"""
    file_path: str
    name: str
    size: int
    programs: List[int]  # Available program numbers
    
class AudioSourceManager(QObject):
    """
    Manages audio sources for tracks including soundfonts and external MIDI devices
    """
    
    # Signals
    sources_updated = Signal()
    soundfont_loaded = Signal(str)  # soundfont_path
    
    def __init__(self, soundfont_directory: str = None):
        super().__init__()
        
        # Default soundfont directory
        if soundfont_directory is None:
            self.soundfont_directory = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "soundfonts"
            )
        else:
            self.soundfont_directory = soundfont_directory
        
        # Available audio sources
        self.available_sources: Dict[str, AudioSource] = {}
        self.soundfonts: Dict[str, SoundfontInfo] = {}
        
        # Track audio source assignments
        self.track_sources: Dict[int, str] = {}  # track_index -> source_id
        
        # Initialize sources
        self._discover_soundfonts()
        self._discover_external_midi_devices()
        self._create_default_sources()
    
    def _discover_soundfonts(self):
        """Discover soundfont files in the soundfonts directory"""
        if not os.path.exists(self.soundfont_directory):
            print(f"Soundfont directory not found: {self.soundfont_directory}")
            return
        
        # Search for .sf2 files
        sf2_pattern = os.path.join(self.soundfont_directory, "*.sf2")
        sf2_files = glob.glob(sf2_pattern)
        
        for sf2_file in sf2_files:
            try:
                file_name = os.path.basename(sf2_file)
                name = os.path.splitext(file_name)[0]
                size = os.path.getsize(sf2_file)
                
                # Create soundfont info
                soundfont_info = SoundfontInfo(
                    file_path=sf2_file,
                    name=name,
                    size=size,
                    programs=list(range(1, 129))  # GM programs 1-128
                )
                
                self.soundfonts[sf2_file] = soundfont_info
                
                # Create audio source for this soundfont
                source_id = f"sf2_{name}"
                audio_source = AudioSource(
                    id=source_id,
                    name=name,
                    source_type=AudioSourceType.SOUNDFONT,
                    file_path=sf2_file
                )
                
                self.available_sources[source_id] = audio_source
                print(f"Discovered soundfont: {name} ({size / 1024 / 1024:.1f} MB)")
                
            except Exception as e:
                print(f"Error processing soundfont {sf2_file}: {e}")
    
    def _discover_external_midi_devices(self):
        """Discover external MIDI output devices"""
        try:
            import rtmidi
            
            midi_out = rtmidi.MidiOut()
            available_ports = midi_out.get_ports()
            
            for i, port_name in enumerate(available_ports):
                # Fix encoding issues for port names
                try:
                    # Handle the specific macOS encoding issue
                    if isinstance(port_name, str):
                        # Remove problematic Unicode characters
                        import re
                        # Replace common macOS garbage characters with readable names
                        if "IAC" in port_name and ("Bus" in port_name or "„" in port_name):
                            # Extract bus number if possible
                            bus_match = re.search(r'(\d+)', port_name)
                            if bus_match:
                                clean_name = f"IAC Driver Bus {bus_match.group(1)}"
                            else:
                                clean_name = f"IAC Driver Bus {i+1}"
                        elif "Dualshock" in port_name:
                            clean_name = "Dualshock4 MIDI"
                        elif "FluidSynth" in port_name:
                            clean_name = f"FluidSynth Virtual Port {i}"
                        else:
                            # Remove all non-ASCII characters and clean up
                            clean_name = re.sub(r'[^\x20-\x7E]', '', port_name)
                            clean_name = re.sub(r'\s+', ' ', clean_name).strip()
                            
                            # If name becomes empty or too short, use a generic name
                            if len(clean_name) < 3:
                                clean_name = f"MIDI Device {i+1}"
                    else:
                        clean_name = f"MIDI Device {i+1}"
                    
                except Exception as e:
                    clean_name = f"MIDI Device {i+1}"
                
                # Skip IAC Driver Bus (but allow it for testing)
                # if "IAC Driver" not in clean_name:
                source_id = f"midi_{i}"
                audio_source = AudioSource(
                    id=source_id,
                    name=clean_name,
                    source_type=AudioSourceType.EXTERNAL_MIDI,
                    midi_port_name=clean_name
                )
                
                self.available_sources[source_id] = audio_source
                print(f"Discovered MIDI device: {clean_name}")
            
            midi_out.close_port()
            del midi_out
            
        except Exception as e:
            print(f"Error discovering MIDI devices: {e}")
    
    def _create_default_sources(self):
        """Create default internal audio sources"""
        # Internal FluidSynth source
        internal_source = AudioSource(
            id="internal_fluidsynth",
            name="Internal FluidSynth",
            source_type=AudioSourceType.INTERNAL_FLUIDSYNTH
        )
        
        self.available_sources["internal_fluidsynth"] = internal_source
    
    def get_available_sources(self) -> List[AudioSource]:
        """Get list of all available audio sources"""
        return list(self.available_sources.values())
    
    def get_soundfont_sources(self) -> List[AudioSource]:
        """Get list of soundfont audio sources"""
        return [source for source in self.available_sources.values() 
                if source.source_type == AudioSourceType.SOUNDFONT]
    
    def get_midi_sources(self) -> List[AudioSource]:
        """Get list of external MIDI audio sources"""
        return [source for source in self.available_sources.values() 
                if source.source_type == AudioSourceType.EXTERNAL_MIDI]
    
    def assign_source_to_track(self, track_index: int, source_id: str) -> bool:
        """Assign an audio source to a track"""
        if source_id not in self.available_sources:
            print(f"Audio source not found: {source_id}")
            return False
        
        self.track_sources[track_index] = source_id
        
        # For soundfont sources, apply track-specific program
        source = self.available_sources[source_id]
        if source.source_type == AudioSourceType.SOUNDFONT:
            try:
                from src.track_manager import DEFAULT_TRACK_PROGRAMS
                if track_index < len(DEFAULT_TRACK_PROGRAMS):
                    # Update the source with track-specific program
                    source.program = DEFAULT_TRACK_PROGRAMS[track_index]
                    source.channel = track_index % 16
                    print(f"Applied track {track_index} program {source.program} to soundfont {source.name}")
            except ImportError:
                pass
        
        print(f"Assigned {source_id} to track {track_index}")
        return True
    
    def get_track_source(self, track_index: int) -> Optional[AudioSource]:
        """Get the audio source assigned to a track"""
        source_id = self.track_sources.get(track_index)
        if source_id:
            source = self.available_sources.get(source_id)
            if source:
                # Apply track-specific program if using internal FluidSynth
                if source.source_type == AudioSourceType.INTERNAL_FLUIDSYNTH:
                    # Get track-specific program from track manager
                    try:
                        from src.track_manager import DEFAULT_TRACK_PROGRAMS
                        if track_index < len(DEFAULT_TRACK_PROGRAMS):
                            # Create a copy with track-specific program
                            import copy
                            track_source = copy.copy(source)
                            track_source.program = DEFAULT_TRACK_PROGRAMS[track_index]
                            track_source.channel = track_index % 16  # Use different channels
                            return track_source
                    except ImportError:
                        pass
                return source
        
        # Default to internal FluidSynth
        default_source = self.available_sources.get("internal_fluidsynth")
        if default_source and track_index == 0:
            return default_source
        elif default_source:
            # Create track-specific version for non-zero tracks
            try:
                from src.track_manager import DEFAULT_TRACK_PROGRAMS
                if track_index < len(DEFAULT_TRACK_PROGRAMS):
                    import copy
                    track_source = copy.copy(default_source)
                    track_source.program = DEFAULT_TRACK_PROGRAMS[track_index]
                    track_source.channel = track_index % 16
                    return track_source
            except ImportError:
                pass
        
        return default_source
    
    def get_track_source_id(self, track_index: int) -> str:
        """Get the source ID assigned to a track"""
        return self.track_sources.get(track_index, "internal_fluidsynth")
    
    def refresh_sources(self):
        """Refresh the list of available audio sources"""
        self.available_sources.clear()
        self.soundfonts.clear()
        
        self._discover_soundfonts()
        self._discover_external_midi_devices()
        self._create_default_sources()
        
        self.sources_updated.emit()
    
    def get_soundfont_info(self, soundfont_path: str) -> Optional[SoundfontInfo]:
        """Get information about a specific soundfont"""
        return self.soundfonts.get(soundfont_path)
    
    def validate_track_assignments(self, max_tracks: int):
        """Validate track assignments and set defaults for unassigned tracks"""
        for track_index in range(max_tracks):
            if track_index not in self.track_sources:
                # Assign default source with unique channel per track
                self.track_sources[track_index] = f"internal_fluidsynth_ch{track_index}"

# Global audio source manager instance
_audio_source_manager: Optional[AudioSourceManager] = None

def get_audio_source_manager() -> Optional[AudioSourceManager]:
    """Get the global audio source manager instance"""
    return _audio_source_manager

def initialize_audio_source_manager(soundfont_directory: str = None) -> AudioSourceManager:
    """Initialize the global audio source manager"""
    global _audio_source_manager
    _audio_source_manager = AudioSourceManager(soundfont_directory)
    return _audio_source_manager

def cleanup_audio_source_manager():
    """Clean up the global audio source manager"""
    global _audio_source_manager
    _audio_source_manager = None