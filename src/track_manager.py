"""
Track Manager for Multi-Track Support
Handles track management, active track selection, and track operations
"""
from typing import List, Optional, Dict, Any
from PySide6.QtCore import QObject, Signal
from src.midi_data_model import MidiProject, MidiTrack, MidiNote

# Default color palette for tracks (16 colors with good contrast)
DEFAULT_TRACK_COLORS = [
    "#FF6B6B",  # Red
    "#4ECDC4",  # Teal
    "#45B7D1",  # Blue
    "#96CEB4",  # Green
    "#FFEAA7",  # Yellow
    "#DDA0DD",  # Plum
    "#98D8C8",  # Mint
    "#F7DC6F",  # Light Yellow
    "#BB8FCE",  # Light Purple
    "#85C1E9",  # Light Blue
    "#F8C471",  # Orange
    "#82E0AA",  # Light Green
    "#F1948A",  # Light Red
    "#D7DBDD",  # Light Gray
    "#AED6F1",  # Sky Blue
    "#D5A6BD",  # Pink
]

# Default track names (numbered format)
DEFAULT_TRACK_NAMES = [
    "Track00",
    "Track01",
    "Track02",
    "Track03",
    "Track04",
    "Track05",
    "Track06",
    "Track07",
    "Track08",
    "Track09",
    "Track10",
    "Track11",
    "Track12",
    "Track13",
    "Track14",
    "Track15",
]

# Default MIDI programs (General MIDI instruments)
DEFAULT_TRACK_PROGRAMS = [
    1,   # Piano (Acoustic Grand Piano)
    49,  # Strings (String Ensemble 1)
    57,  # Brass (Trumpet)
    65,  # Woodwinds (Soprano Sax)
    115, # Percussion (Woodblock)
    33,  # Bass (Electric Bass)
    25,  # Guitar (Acoustic Guitar)
    53,  # Vocals (Voice Oohs)
    1,   # Track 9 (Piano)
    1,   # Track 10 (Piano)
    1,   # Track 11 (Piano)
    1,   # Track 12 (Piano)
    1,   # Track 13 (Piano)
    1,   # Track 14 (Piano)
    1,   # Track 15 (Piano)
    1,   # Track 16 (Piano)
]

class TrackManager(QObject):
    """
    Manages multiple tracks, active track selection, and track operations
    """
    
    # Signals
    active_track_changed = Signal(int)          # track_index
    track_added = Signal(int)                   # track_index
    track_removed = Signal(int)                 # track_index
    track_renamed = Signal(int, str)            # track_index, new_name
    track_color_changed = Signal(int, str)      # track_index, new_color
    track_settings_changed = Signal(int)        # track_index
    project_changed = Signal()                  # project updated
    
    def __init__(self, project: Optional[MidiProject] = None):
        super().__init__()
        self.project = None
        self.active_track_index = 0
        self.track_colors: Dict[int, str] = {}  # track_index -> color
        
        # Initialize with project if provided
        if project:
            self.set_project(project)
    
    def set_project(self, project: Optional[MidiProject]):
        """Set the MIDI project and initialize track management"""
        self.project = project
        self.active_track_index = 0
        self.track_colors.clear()
        
        if self.project:
            self._initialize_track_colors()
            # Initialize with Domino-style track setup (8 tracks minimum)
            if not self.project.tracks:
                self._create_default_tracks()
            elif len(self.project.tracks) < 8:
                self._ensure_minimum_tracks()
        
        self.active_track_changed.emit(self.active_track_index)
        self.project_changed.emit()
    
    def _initialize_track_colors(self):
        """Initialize colors for existing tracks"""
        if not self.project:
            return
        
        for i, track in enumerate(self.project.tracks):
            # Use existing color if available, otherwise assign from palette
            if hasattr(track, 'color') and track.color:
                self.track_colors[i] = track.color
            else:
                self.track_colors[i] = DEFAULT_TRACK_COLORS[i % len(DEFAULT_TRACK_COLORS)]
                # Store color in track object
                track.color = self.track_colors[i]
    
    def _create_default_tracks(self):
        """Create default Domino-style track setup (8 tracks)"""
        print("TrackManager: Creating default 8-track setup")
        for i in range(8):
            name = DEFAULT_TRACK_NAMES[i]
            color = DEFAULT_TRACK_COLORS[i % len(DEFAULT_TRACK_COLORS)]
            program = DEFAULT_TRACK_PROGRAMS[i]
            
            track = MidiTrack(name=name, channel=i, program=program, color=color)
            self.project.tracks.append(track)
            self.track_colors[i] = color
    
    def _ensure_minimum_tracks(self):
        """Ensure minimum 8 tracks exist"""
        current_count = len(self.project.tracks)
        print(f"TrackManager: Ensuring minimum tracks. Current: {current_count}")
        
        # First, fix existing tracks to use Domino names and settings
        for i in range(min(current_count, 8)):
            track = self.project.tracks[i]
            track.name = DEFAULT_TRACK_NAMES[i]
            track.program = DEFAULT_TRACK_PROGRAMS[i]
            track.channel = i
            track.color = DEFAULT_TRACK_COLORS[i % len(DEFAULT_TRACK_COLORS)]
            self.track_colors[i] = track.color
        
        # Then add any missing tracks
        for i in range(current_count, 8):
            name = DEFAULT_TRACK_NAMES[i]
            color = DEFAULT_TRACK_COLORS[i % len(DEFAULT_TRACK_COLORS)]
            program = DEFAULT_TRACK_PROGRAMS[i]
            
            track = MidiTrack(name=name, channel=i, program=program, color=color)
            self.project.tracks.append(track)
            self.track_colors[i] = color
    
    def get_track_count(self) -> int:
        """Get the number of tracks"""
        if not self.project:
            return 0
        return len(self.project.tracks)
    
    def get_active_track_index(self) -> int:
        """Get the currently active track index"""
        return self.active_track_index
    
    def get_active_track(self) -> Optional[MidiTrack]:
        """Get the currently active track"""
        if not self.project or not self.project.tracks:
            return None
        if self.active_track_index >= len(self.project.tracks):
            self.active_track_index = 0
        return self.project.tracks[self.active_track_index]
    
    def set_active_track(self, track_index: int) -> bool:
        """Set the active track by index"""
        if not self.project or track_index < 0 or track_index >= len(self.project.tracks):
            return False
        
        if self.active_track_index != track_index:
            self.active_track_index = track_index
            self.active_track_changed.emit(track_index)
        return True
    
    def get_track(self, track_index: int) -> Optional[MidiTrack]:
        """Get a track by index"""
        if not self.project or track_index < 0 or track_index >= len(self.project.tracks):
            return None
        return self.project.tracks[track_index]
    
    def get_track_name(self, track_index: int) -> str:
        """Get track name by index"""
        track = self.get_track(track_index)
        return track.name if track else f"Track {track_index + 1}"
    
    def get_track_color(self, track_index: int) -> str:
        """Get track color by index"""
        return self.track_colors.get(track_index, DEFAULT_TRACK_COLORS[0])
    
    def set_track_color(self, track_index: int, color: str):
        """Set track color by index"""
        if track_index < 0 or not self.project or track_index >= len(self.project.tracks):
            return
        
        self.track_colors[track_index] = color
        
        # Store in track object
        track = self.project.tracks[track_index]
        track.color = color
        
        self.track_color_changed.emit(track_index, color)
    
    def add_track(self, name: str = None, color: str = None, program: int = None) -> int:
        """Add a new track and return its index"""
        if not self.project:
            return -1
        
        track_index = len(self.project.tracks)
        
        # Generate default name if not provided
        if not name:
            if track_index < len(DEFAULT_TRACK_NAMES):
                name = DEFAULT_TRACK_NAMES[track_index]
            else:
                name = f"Track {track_index + 1}"
        
        # Assign color from palette if not provided
        if not color:
            color = DEFAULT_TRACK_COLORS[track_index % len(DEFAULT_TRACK_COLORS)]
        
        # Assign default program if not provided
        if program is None:
            if track_index < len(DEFAULT_TRACK_PROGRAMS):
                program = DEFAULT_TRACK_PROGRAMS[track_index]
            else:
                program = 1  # Default to piano
        
        # Create new track
        new_track = MidiTrack(name=name, channel=track_index % 16, program=program, color=color)
        
        # Add to project
        self.project.tracks.append(new_track)
        self.track_colors[track_index] = color
        
        self.track_added.emit(track_index)
        return track_index
    
    def remove_track(self, track_index: int) -> bool:
        """Remove a track by index"""
        if not self.project or track_index < 0 or track_index >= len(self.project.tracks):
            return False
        
        # Don't allow removing the last track
        if len(self.project.tracks) <= 1:
            return False
        
        # Remove track
        del self.project.tracks[track_index]
        
        # Update colors dict (shift indices down)
        new_colors = {}
        for i, color in self.track_colors.items():
            if i < track_index:
                new_colors[i] = color
            elif i > track_index:
                new_colors[i - 1] = color
        self.track_colors = new_colors
        
        # Adjust active track index
        if self.active_track_index >= track_index:
            self.active_track_index = max(0, self.active_track_index - 1)
        
        self.track_removed.emit(track_index)
        self.active_track_changed.emit(self.active_track_index)
        return True
    
    def rename_track(self, track_index: int, new_name: str) -> bool:
        """Rename a track"""
        track = self.get_track(track_index)
        if not track:
            return False
        
        track.name = new_name
        self.track_renamed.emit(track_index, new_name)
        return True
    
    def duplicate_track(self, track_index: int) -> int:
        """Duplicate a track and return the new track index"""
        source_track = self.get_track(track_index)
        if not source_track:
            return -1
        
        # Create new track with copied properties
        new_name = f"{source_track.name} Copy"
        new_color = self.get_track_color(track_index)
        new_track_index = self.add_track(new_name, new_color)
        
        if new_track_index >= 0:
            new_track = self.get_track(new_track_index)
            if new_track:
                # Copy track properties
                new_track.program = source_track.program
                new_track.channel = new_track_index % 16  # Assign new channel
                
                # Copy all notes
                for note in source_track.notes:
                    new_note = MidiNote(
                        pitch=note.pitch,
                        start_tick=note.start_tick,
                        end_tick=note.end_tick,
                        velocity=note.velocity,
                        channel=new_track.channel
                    )
                    new_track.notes.append(new_note)
        
        return new_track_index
    
    def get_notes_for_track(self, track_index: int) -> List[MidiNote]:
        """Get all notes for a specific track"""
        track = self.get_track(track_index)
        return track.notes if track else []
    
    def add_note_to_active_track(self, note: MidiNote):
        """Add a note to the currently active track"""
        active_track = self.get_active_track()
        if active_track:
            # Set the note's channel to match the track
            note.channel = active_track.channel
            active_track.notes.append(note)
    
    def get_track_info(self, track_index: int) -> Dict[str, Any]:
        """Get comprehensive track information"""
        track = self.get_track(track_index)
        if not track:
            return {}
        
        return {
            'index': track_index,
            'name': track.name,
            'color': self.get_track_color(track_index),
            'channel': track.channel,
            'program': track.program,
            'note_count': len(track.notes),
            'is_active': track_index == self.active_track_index
        }
    
    def get_all_tracks_info(self) -> List[Dict[str, Any]]:
        """Get information for all tracks"""
        return [self.get_track_info(i) for i in range(self.get_track_count())]

# Global track manager instance
_track_manager: Optional[TrackManager] = None

def get_track_manager() -> Optional[TrackManager]:
    """Get the global track manager instance"""
    return _track_manager

def initialize_track_manager(project: Optional[MidiProject] = None) -> TrackManager:
    """Initialize the global track manager"""
    global _track_manager
    _track_manager = TrackManager(project)
    return _track_manager

def cleanup_track_manager():
    """Clean up the global track manager"""
    global _track_manager
    _track_manager = None