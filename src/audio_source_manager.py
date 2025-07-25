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

@dataclass
class AudioSource:
    """Represents an audio source for a track"""
    id: str
    name: str
    source_type: AudioSourceType
    file_path: Optional[str] = None  # For soundfonts
    midi_port_name: Optional[str] = None  # For external MIDI
    program: int = 0  # MIDI program number (0-based, 0-127)
    channel: int = 0  # MIDI channel
    
    def __str__(self):
        if self.source_type == AudioSourceType.SOUNDFONT:
            return f"{self.name} (SF2)"
        elif self.source_type == AudioSourceType.EXTERNAL_MIDI:
            return f"{self.name} (MIDI)"
        else:
            return f"{self.name} (Unknown)"

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
        # No default sources - users must add soundfonts manually
        pass
    
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
            # GM Instrumentダイアログで作成されたソースはプログラム保持
            if not source_id.startswith("internal_fluidsynth_ch"):
                try:
                    from src.track_manager import get_track_program_for_soundfont
                    # Update the source with track-specific program based on soundfont type
                    source.program = get_track_program_for_soundfont(track_index, source.name)
                    source.channel = track_index % 16
                    print(f"Applied track {track_index} program {source.program} to soundfont {source.name}")
                except ImportError:
                    pass
            else:
                # GM専用ソースはプログラム番号を保持
                source.channel = track_index % 16  # チャンネルのみ更新
                print(f"Preserved GM instrument program {source.program} for track {track_index}")
        
        # Emit signal to notify UI of source assignment change
        self.sources_updated.emit()
        
        print(f"📌 Assigned {source_id} to track {track_index} (program: {source.program})")
        return True
    
    def get_track_source(self, track_index: int) -> Optional[AudioSource]:
        """Get the audio source assigned to a track"""
        source_id = self.track_sources.get(track_index)
        print(f"🔍 Getting track {track_index} source: {source_id}")
        if source_id:
            # First check if the source exists in available_sources
            source = self.available_sources.get(source_id)
            if source:
                print(f"🎯 Found source {source_id}: program={source.program}, name={source.name}")
                return source
            
            # Handle legacy channel-specific internal FluidSynth identifiers (for compatibility)
            if source_id.startswith("internal_fluidsynth_ch"):
                try:
                    channel = int(source_id.split("ch")[1])
                except (ValueError, IndexError):
                    channel = track_index
                
                # No default program - internal FluidSynth starts without instrument
                program = None
                
                return AudioSource(
                    id=source_id,
                    name=f"Internal FluidSynth Ch{channel}",
                    source_type=AudioSourceType.INTERNAL_FLUIDSYNTH,
                    channel=channel,
                    program=program,
                    file_path=None,
                    midi_port_name=None
                )
        
        # No default source - return None if no source is assigned
        return None
    
    def get_track_source_id(self, track_index: int) -> Optional[str]:
        """Get the source ID assigned to a track"""
        return self.track_sources.get(track_index, None)
    
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
                # No default assignment - tracks start without audio source
                pass
    
    def add_soundfont_file(self, file_path: str) -> bool:
        """Add a new soundfont file to the available sources"""
        import shutil
        
        try:
            if not os.path.exists(file_path):
                print(f"Soundfont file not found: {file_path}")
                return False
            
            if not file_path.lower().endswith('.sf2'):
                print(f"Invalid soundfont file extension: {file_path}")
                return False
            
            # Get filename and create destination path
            filename = os.path.basename(file_path)
            destination_path = os.path.join(self.soundfont_directory, filename)
            
            # Check if file already exists
            if os.path.exists(destination_path):
                print(f"Soundfont already exists: {filename}")
                # Still return True as it's technically available
                return True
            
            # Ensure soundfont directory exists
            os.makedirs(self.soundfont_directory, exist_ok=True)
            
            # Copy file to soundfonts directory
            shutil.copy2(file_path, destination_path)
            print(f"Copied soundfont to: {destination_path}")
            
            # Create soundfont info and audio source
            file_name = os.path.basename(destination_path)
            name = os.path.splitext(file_name)[0]
            size = os.path.getsize(destination_path)
            
            # Create soundfont info
            soundfont_info = SoundfontInfo(
                file_path=destination_path,
                name=name,
                size=size,
                programs=list(range(128))  # Assume all 128 GM programs available
            )
            
            self.soundfonts[destination_path] = soundfont_info
            
            # Create default audio source for this soundfont
            source_id = f"soundfont_{name.lower().replace(' ', '_')}"
            source = AudioSource(
                id=source_id,
                name=name,
                source_type=AudioSourceType.SOUNDFONT,
                file_path=destination_path,
                program=0,  # Default to piano
                channel=0
            )
            
            self.available_sources[source_id] = source
            
            # Emit signals
            self.sources_updated.emit()
            self.soundfont_loaded.emit(destination_path)
            
            print(f"Successfully added soundfont: {name}")
            return True
            
        except Exception as e:
            print(f"Error adding soundfont {file_path}: {e}")
            return False
    
    def remove_soundfont_file(self, source_id: str) -> bool:
        """サウンドフォントファイルを削除する"""
        import os
        
        try:
            # ソースが存在するか確認
            if source_id not in self.available_sources:
                print(f"Audio source not found: {source_id}")
                return False
            
            source = self.available_sources[source_id]
            
            # サウンドフォントタイプかチェック
            if source.source_type != AudioSourceType.SOUNDFONT:
                print(f"Source {source_id} is not a soundfont")
                return False
            
            file_path = source.file_path
            if not file_path or not os.path.exists(file_path):
                print(f"Soundfont file not found: {file_path}")
                # ファイルが見つからなくてもソースは削除
            else:
                # ファイルを削除
                os.remove(file_path)
                print(f"Deleted soundfont file: {file_path}")
            
            # available_sourcesから削除
            del self.available_sources[source_id]
            
            # soundfontsからも削除
            if file_path in self.soundfonts:
                del self.soundfonts[file_path]
            
            # このソースを使用しているトラックがあれば割り当てを削除
            tracks_to_update = []
            for track_index, assigned_source_id in self.track_sources.items():
                if assigned_source_id == source_id:
                    tracks_to_update.append(track_index)
            
            for track_index in tracks_to_update:
                del self.track_sources[track_index]
                print(f"Track {track_index} audio source assignment removed")
            
            # シグナルを発信
            self.sources_updated.emit()
            
            print(f"Successfully removed soundfont: {source.name}")
            return True
            
        except Exception as e:
            print(f"Error removing soundfont {source_id}: {e}")
            return False

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