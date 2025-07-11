"""
Playback engine for MIDI sequencer
"""
import time
from typing import List, Optional, Dict, Set
from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QObject, Signal, QTimer, QThread
from src.midi_data_model import MidiNote, MidiProject
from src.audio_system import get_audio_manager

class PlaybackState(Enum):
    """Playback state enumeration"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"

@dataclass
class PlaybackEvent:
    """Represents a MIDI event to be played"""
    timestamp: float  # Absolute time in seconds
    tick: int        # MIDI tick position
    note: MidiNote   # The note to play
    event_type: str  # "note_on" or "note_off"

class PlaybackEngine(QObject):
    """Core playback engine for MIDI sequences"""
    
    # Signals
    state_changed = Signal(PlaybackState)  # Playback state changed
    position_changed = Signal(int)         # Current tick position changed
    tempo_changed = Signal(float)          # Tempo changed (BPM)
    playback_finished = Signal()           # Playback reached the end
    
    def __init__(self):
        super().__init__()
        
        # Playback state
        self.state = PlaybackState.STOPPED
        self.current_tick = 0
        self.start_time = 0.0
        self.pause_tick = 0
        
        # Tempo and timing
        self.tempo_bpm = 120.0  # Default tempo
        self.ticks_per_beat = 480  # Default MIDI resolution
        self.ticks_per_second = self.tempo_bpm * self.ticks_per_beat / 60.0
        
        # Project and events
        self.project: Optional[MidiProject] = None
        self.events: List[PlaybackEvent] = []
        self.active_notes: Set[int] = set()  # Currently playing note pitches
        
        # Playback timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_playback)
        self.timer_interval = 10  # Update every 10ms for smooth playback
        # Timer will be started/stopped as needed
        
        # Lookahead for scheduling
        self.lookahead_ms = 100  # Schedule events 100ms ahead
        self.next_event_index = 0
    
    def set_project(self, project: Optional[MidiProject], preserve_position: bool = False):
        """Set the MIDI project to play"""
        old_tick = self.current_tick if preserve_position else 0
        
        self.project = project
        self.stop()
        
        if not preserve_position:
            self.current_tick = 0
        
        if project:
            self.ticks_per_beat = project.ticks_per_beat
            self._update_ticks_per_second()
            self._prepare_events()
        else:
            self.events = []
        
        if preserve_position:
            self.current_tick = old_tick
        
        self.position_changed.emit(self.current_tick)
    
    def set_tempo(self, bpm: float):
        """Set playback tempo in BPM"""
        self.tempo_bpm = max(1.0, min(300.0, bpm))  # Clamp between 1-300 BPM
        self._update_ticks_per_second()
        self.tempo_changed.emit(self.tempo_bpm)
    
    def _update_ticks_per_second(self):
        """Update ticks per second based on current tempo"""
        self.ticks_per_second = self.tempo_bpm * self.ticks_per_beat / 60.0
    
    def _prepare_events(self):
        """Prepare playback events from the project"""
        self.events = []
        
        if not self.project:
            return
        
        # Collect all notes from all tracks
        all_notes = []
        for track in self.project.tracks:
            all_notes.extend(track.notes)
        
        # Sort notes by start time
        all_notes.sort(key=lambda note: note.start_tick)
        
        # Create note on/off events
        for note in all_notes:
            # Note on event
            note_on_time = note.start_tick / self.ticks_per_second
            self.events.append(PlaybackEvent(
                timestamp=note_on_time,
                tick=note.start_tick,
                note=note,
                event_type="note_on"
            ))
            
            # Note off event
            note_off_time = note.end_tick / self.ticks_per_second
            self.events.append(PlaybackEvent(
                timestamp=note_off_time,
                tick=note.end_tick,
                note=note,
                event_type="note_off"
            ))
        
        # Sort events by timestamp
        self.events.sort(key=lambda event: event.timestamp)
        self.next_event_index = 0
        
        print(f"Prepared {len(self.events)} playback events. First event: {self.events[0] if self.events else 'N/A'}")
    
    def play(self):
        """Start or resume playback"""
        if self.state == PlaybackState.PLAYING:
            return
        
        if not self.project or not self.events:
            print("No project or events to play")
            return
        
        if self.state == PlaybackState.STOPPED:
            # Start from beginning
            self.current_tick = 0
            self.next_event_index = 0
            self._stop_all_notes()
        elif self.state == PlaybackState.PAUSED:
            # Resume from pause position
            self.current_tick = self.pause_tick
            self._find_next_event_index()
        
        self.start_time = time.time() - (self.current_tick / self.ticks_per_second)
        self.state = PlaybackState.PLAYING
        self.timer.start(self.timer_interval)
        self.state_changed.emit(self.state)
        
        print(f"Playback started from tick {self.current_tick}. start_time: {self.start_time}")
    
    def pause(self):
        """Pause playback"""
        if self.state != PlaybackState.PLAYING:
            return
        
        self.timer.stop()
        self.pause_tick = self.current_tick
        self.state = PlaybackState.PAUSED
        self._stop_all_notes()
        self.state_changed.emit(self.state)
        
        print(f"Playback paused at tick {self.current_tick}")
    
    def stop(self):
        """Stop playback and return to beginning"""
        if self.state == PlaybackState.STOPPED:
            return
        
        self.timer.stop()
        self.current_tick = 0
        self.pause_tick = 0
        self.next_event_index = 0
        self.state = PlaybackState.STOPPED
        self._stop_all_notes()
        self.state_changed.emit(self.state)
        self.position_changed.emit(self.current_tick)
        
        print("Playback stopped")
    
    def toggle_play_pause(self):
        """Toggle between play and pause"""
        if self.state == PlaybackState.PLAYING:
            self.pause()
        else:
            self.play()
    
    def seek_to_tick(self, tick: int):
        """Seek to a specific tick position"""
        was_playing = self.state == PlaybackState.PLAYING
        
        if was_playing:
            self.pause()
        
        self.current_tick = max(0, tick)
        self.pause_tick = self.current_tick
        self._find_next_event_index()
        self.position_changed.emit(self.current_tick)
        
        if was_playing:
            self.play()
        
        print(f"Seeked to tick {self.current_tick}")
    
    def seek_to_beginning(self):
        """Seek to the beginning"""
        self.seek_to_tick(0)
    
    def _find_next_event_index(self):
        """Find the next event index for current position"""
        current_time = self.current_tick / self.ticks_per_second
        
        for i, event in enumerate(self.events):
            if event.timestamp > current_time:
                self.next_event_index = i
                return
        
        self.next_event_index = len(self.events)
    
    def _update_playback(self):
        """Update playback position and schedule events"""
        if self.state != PlaybackState.PLAYING:
            return
        
        # Calculate current position
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        self.current_tick = int(elapsed_time * self.ticks_per_second)
        
        # Emit position update
        self.position_changed.emit(self.current_tick)
        
        # Schedule events within lookahead window
        lookahead_time = current_time + (self.lookahead_ms / 1000.0)
        
        while (self.next_event_index < len(self.events) and 
               self.events[self.next_event_index].timestamp <= lookahead_time):
            
            event = self.events[self.next_event_index]
            
            # Calculate absolute event time
            event_absolute_time = self.start_time + event.timestamp
            
            # Only schedule if event time has arrived (within tolerance)
            if current_time >= event_absolute_time - 0.02:  # 20ms early tolerance
                self._schedule_event(event)
                self.next_event_index += 1
            else:
                # Event is not ready yet, stop processing
                break
        
        # Check if playback is finished
        if self.next_event_index >= len(self.events):
            # Check if all notes have finished
            max_end_tick = 0
            if self.project:
                for track in self.project.tracks:
                    for note in track.notes:
                        max_end_tick = max(max_end_tick, note.end_tick)
            
            if self.current_tick >= max_end_tick:
                self.stop()
                self.playback_finished.emit()
    
    def _schedule_event(self, event: PlaybackEvent):
        """Schedule a MIDI event for playback"""
        audio_manager = get_audio_manager()
        if not audio_manager:
            print("PlaybackEngine: AudioManager not available.")
            return
        
        if event.event_type == "note_on":
            success = audio_manager.play_note_immediate(event.note.pitch, event.note.velocity)
            if success:
                self.active_notes.add(event.note.pitch)
                print(f"PlaybackEngine: Playing note {event.note.pitch} at tick {event.tick}, velocity {event.note.velocity}")
            else:
                print(f"PlaybackEngine: Failed to play note {event.note.pitch} at tick {event.tick}")
        
        elif event.event_type == "note_off":
            if event.note.pitch in self.active_notes:
                success = audio_manager.stop_note_immediate(event.note.pitch)
                if success:
                    self.active_notes.discard(event.note.pitch)
                    print(f"PlaybackEngine: Stopping note {event.note.pitch} at tick {event.tick}")
                else:
                    print(f"PlaybackEngine: Failed to stop note {event.note.pitch} at tick {event.tick}")
    
    def _stop_all_notes(self):
        """Stop all currently playing notes"""
        audio_manager = get_audio_manager()
        if not audio_manager:
            return
        
        for pitch in list(self.active_notes):
            audio_manager.stop_note_immediate(pitch)
        
        self.active_notes.clear()
    
    def get_state(self) -> PlaybackState:
        """Get current playback state"""
        return self.state
    
    def get_current_tick(self) -> int:
        """Get current playback position in ticks"""
        return self.current_tick
    
    def get_tempo(self) -> float:
        """Get current tempo in BPM"""
        return self.tempo_bpm
    
    def is_playing(self) -> bool:
        """Check if currently playing"""
        return self.state == PlaybackState.PLAYING
    
    def cleanup(self):
        """Clean up resources"""
        self.stop()
        self.timer.stop()
        print("Playback engine cleaned up")

# Global playback engine instance
playback_engine: Optional[PlaybackEngine] = None

def get_playback_engine() -> Optional[PlaybackEngine]:
    """Get the global playback engine instance"""
    return playback_engine

def initialize_playback_engine() -> PlaybackEngine:
    """Initialize the global playback engine"""
    global playback_engine
    
    if playback_engine is not None:
        playback_engine.cleanup()
    
    playback_engine = PlaybackEngine()
    return playback_engine

def cleanup_playback_engine():
    """Clean up the global playback engine"""
    global playback_engine
    
    if playback_engine:
        playback_engine.cleanup()
        playback_engine = None