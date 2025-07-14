
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class AutomationPoint:
    """Represents a single automation point for parameter control"""
    tick_offset: int  # Offset from note start in ticks
    value: int        # Parameter value (0-127 for MIDI compatibility)
    
    def __post_init__(self):
        # Ensure values are within MIDI range
        self.value = max(0, min(127, self.value))
    
    def __str__(self):
        return f"AutomationPoint(offset={self.tick_offset}, value={self.value})"

@dataclass
class TempoChange:
    """Represents a tempo change event"""
    tick: int
    bpm: float
    microseconds_per_beat: int
    
    @classmethod
    def from_bpm(cls, tick: int, bpm: float):
        """Create tempo change from BPM"""
        microseconds_per_beat = int(60_000_000 / bpm)
        return cls(tick, bpm, microseconds_per_beat)
    
    @classmethod
    def from_microseconds(cls, tick: int, microseconds_per_beat: int):
        """Create tempo change from microseconds per beat"""
        bpm = 60_000_000 / microseconds_per_beat
        return cls(tick, bpm, microseconds_per_beat)

@dataclass
class TimeSignatureChange:
    """Represents a time signature change event"""
    tick: int
    numerator: int
    denominator: int
    clocks_per_click: int = 24  # MIDI clocks per metronome click
    notes_per_quarter: int = 8  # 32nd notes per quarter note
    
    def __str__(self):
        return f"{self.numerator}/{self.denominator}"

class MidiNote:
    def __init__(self, pitch: int, start_tick: int, end_tick: int, velocity: int, channel: int = 0):
        self.pitch = pitch  # MIDI note number (0-127)
        self.start_tick = start_tick # Start time in MIDI ticks
        self.end_tick = end_tick    # End time in MIDI ticks
        self.velocity = velocity  # Velocity (0-127)
        self.channel = channel    # MIDI channel (0-15)
        
        # Automation data for graphical parameter editing
        self.velocity_automation: Optional[List[AutomationPoint]] = None
        self.volume_automation: Optional[List[AutomationPoint]] = None      # CC7 automation
        self.expression_automation: Optional[List[AutomationPoint]] = None  # CC11 automation
        
        # Default CC values (when no automation exists)
        self.volume = 100        # Default volume (CC7)
        self.expression = 127    # Default expression (CC11)

    @property
    def duration(self):
        return self.end_tick - self.start_tick
    
    def get_velocity_at_tick_offset(self, tick_offset: int) -> int:
        """Get interpolated velocity value at a specific tick offset from note start"""
        if not self.velocity_automation:
            return self.velocity
        
        # Ensure tick_offset is within note bounds
        tick_offset = max(0, min(self.duration, tick_offset))
        
        # If no automation points, return base velocity
        if not self.velocity_automation:
            return self.velocity
        
        # Sort points by tick_offset
        sorted_points = sorted(self.velocity_automation, key=lambda p: p.tick_offset)
        
        # If tick_offset is before first point, return base velocity
        if tick_offset < sorted_points[0].tick_offset:
            return self.velocity
        
        # If tick_offset is after last point, return last point value
        if tick_offset >= sorted_points[-1].tick_offset:
            return sorted_points[-1].value
        
        # Find the two points to interpolate between
        for i in range(len(sorted_points) - 1):
            p1 = sorted_points[i]
            p2 = sorted_points[i + 1]
            
            if p1.tick_offset <= tick_offset < p2.tick_offset:
                # Linear interpolation
                ratio = (tick_offset - p1.tick_offset) / (p2.tick_offset - p1.tick_offset)
                interpolated_value = p1.value + ratio * (p2.value - p1.value)
                return int(round(interpolated_value))
        
        # Fallback to base velocity
        return self.velocity
    
    def add_velocity_automation_point(self, tick_offset: int, value: int):
        """Add or update a velocity automation point"""
        if self.velocity_automation is None:
            self.velocity_automation = []
        
        # Ensure tick_offset is within note bounds
        tick_offset = max(0, min(self.duration, tick_offset))
        value = max(0, min(127, value))
        
        # Check if point already exists at this tick_offset
        for point in self.velocity_automation:
            if point.tick_offset == tick_offset:
                point.value = value
                return
        
        # Add new point
        self.velocity_automation.append(AutomationPoint(tick_offset, value))
        
        # Keep sorted by tick_offset
        self.velocity_automation.sort(key=lambda p: p.tick_offset)
    
    def remove_velocity_automation_point(self, tick_offset: int):
        """Remove velocity automation point at specific tick offset"""
        if not self.velocity_automation:
            return
        
        self.velocity_automation = [p for p in self.velocity_automation if p.tick_offset != tick_offset]
        
        # Clear automation list if empty
        if not self.velocity_automation:
            self.velocity_automation = None
    
    def get_volume_at_tick_offset(self, tick_offset: int) -> int:
        """Get interpolated volume value at a specific tick offset from note start"""
        if not self.volume_automation:
            return self.volume
        
        # Ensure tick_offset is within note bounds
        tick_offset = max(0, min(self.duration, tick_offset))
        
        # Sort points by tick_offset
        sorted_points = sorted(self.volume_automation, key=lambda p: p.tick_offset)
        
        # If tick_offset is before first point, return base volume
        if tick_offset < sorted_points[0].tick_offset:
            return self.volume
        
        # If tick_offset is after last point, return last point value
        if tick_offset >= sorted_points[-1].tick_offset:
            return sorted_points[-1].value
        
        # Find the two points to interpolate between
        for i in range(len(sorted_points) - 1):
            p1 = sorted_points[i]
            p2 = sorted_points[i + 1]
            
            if p1.tick_offset <= tick_offset < p2.tick_offset:
                # Linear interpolation
                ratio = (tick_offset - p1.tick_offset) / (p2.tick_offset - p1.tick_offset)
                interpolated_value = p1.value + ratio * (p2.value - p1.value)
                return int(round(interpolated_value))
        
        # Fallback to base volume
        return self.volume
    
    def add_volume_automation_point(self, tick_offset: int, value: int):
        """Add or update a volume automation point"""
        if self.volume_automation is None:
            self.volume_automation = []
        
        # Ensure tick_offset is within note bounds
        tick_offset = max(0, min(self.duration, tick_offset))
        value = max(0, min(127, value))
        
        # Check if point already exists at this tick_offset
        for point in self.volume_automation:
            if point.tick_offset == tick_offset:
                point.value = value
                return
        
        # Add new point
        self.volume_automation.append(AutomationPoint(tick_offset, value))
        
        # Keep sorted by tick_offset
        self.volume_automation.sort(key=lambda p: p.tick_offset)
    
    def remove_volume_automation_point(self, tick_offset: int):
        """Remove volume automation point at specific tick offset"""
        if not self.volume_automation:
            return
        
        self.volume_automation = [p for p in self.volume_automation if p.tick_offset != tick_offset]
        
        # Clear automation list if empty
        if not self.volume_automation:
            self.volume_automation = None
    
    def get_expression_at_tick_offset(self, tick_offset: int) -> int:
        """Get interpolated expression value at a specific tick offset from note start"""
        if not self.expression_automation:
            return self.expression
        
        # Ensure tick_offset is within note bounds
        tick_offset = max(0, min(self.duration, tick_offset))
        
        # Sort points by tick_offset
        sorted_points = sorted(self.expression_automation, key=lambda p: p.tick_offset)
        
        # If tick_offset is before first point, return base expression
        if tick_offset < sorted_points[0].tick_offset:
            return self.expression
        
        # If tick_offset is after last point, return last point value
        if tick_offset >= sorted_points[-1].tick_offset:
            return sorted_points[-1].value
        
        # Find the two points to interpolate between
        for i in range(len(sorted_points) - 1):
            p1 = sorted_points[i]
            p2 = sorted_points[i + 1]
            
            if p1.tick_offset <= tick_offset < p2.tick_offset:
                # Linear interpolation
                ratio = (tick_offset - p1.tick_offset) / (p2.tick_offset - p1.tick_offset)
                interpolated_value = p1.value + ratio * (p2.value - p1.value)
                return int(round(interpolated_value))
        
        # Fallback to base expression
        return self.expression
    
    def add_expression_automation_point(self, tick_offset: int, value: int):
        """Add or update an expression automation point"""
        if self.expression_automation is None:
            self.expression_automation = []
        
        # Ensure tick_offset is within note bounds
        tick_offset = max(0, min(self.duration, tick_offset))
        value = max(0, min(127, value))
        
        # Check if point already exists at this tick_offset
        for point in self.expression_automation:
            if point.tick_offset == tick_offset:
                point.value = value
                return
        
        # Add new point
        self.expression_automation.append(AutomationPoint(tick_offset, value))
        
        # Keep sorted by tick_offset
        self.expression_automation.sort(key=lambda p: p.tick_offset)
    
    def remove_expression_automation_point(self, tick_offset: int):
        """Remove expression automation point at specific tick offset"""
        if not self.expression_automation:
            return
        
        self.expression_automation = [p for p in self.expression_automation if p.tick_offset != tick_offset]
        
        # Clear automation list if empty
        if not self.expression_automation:
            self.expression_automation = None

class MidiTrack:
    def __init__(self, name: str = "New Track", channel: int = 0, program: int = None, color: str = "#FF6B6B"):
        self.name = name
        self.channel = channel
        self.program = program # MIDI program number (instrument), None for empty tracks
        self.color = color     # Track color for visual distinction
        self.notes: List[MidiNote] = []
        # Add other MIDI events later (e.g., CC, Pitch Bend)

class MidiProject:
    def __init__(self):
        self.tracks: List[MidiTrack] = []
        self.tempo_changes: List[TempoChange] = []
        self.time_signature_changes: List[TimeSignatureChange] = []
        self.ticks_per_beat: int = 480 # Default for MIDI files
        
        # Initialize with default tempo and time signature
        self.tempo_changes.append(TempoChange.from_bpm(0, 120.0))
        self.time_signature_changes.append(TimeSignatureChange(0, 4, 4))
        
        if not self.tracks:
            self.add_track(MidiTrack(name="Track 1")) # Add a default track

    def add_track(self, track: MidiTrack):
        self.tracks.append(track)

    def get_notes_in_range(self, start_tick: int, end_tick: int) -> List[MidiNote]:
        all_notes = []
        for track in self.tracks:
            for note in track.notes:
                if not (note.end_tick <= start_tick or note.start_tick >= end_tick):
                    all_notes.append(note)
        return all_notes
    
    def get_notes_at_tick(self, tick: int) -> List[MidiNote]:
        """Get all notes that are playing at the specified tick"""
        playing_notes = []
        for track in self.tracks:
            for note in track.notes:
                if note.start_tick <= tick < note.end_tick:
                    playing_notes.append(note)
        return playing_notes
    
    def get_notes_starting_at_tick(self, tick: int, tolerance: int = 10) -> List[MidiNote]:
        """Get all notes that start at or near the specified tick"""
        starting_notes = []
        for track in self.tracks:
            for note in track.notes:
                if abs(note.start_tick - tick) <= tolerance:
                    starting_notes.append(note)
        return starting_notes
    
    def add_tempo_change(self, tick: int, bpm: float):
        """Add a tempo change at the specified tick"""
        tempo_change = TempoChange.from_bpm(tick, bpm)
        
        # Remove any existing tempo change at the same tick
        self.tempo_changes = [tc for tc in self.tempo_changes if tc.tick != tick]
        
        # Add new tempo change and sort by tick
        self.tempo_changes.append(tempo_change)
        self.tempo_changes.sort(key=lambda tc: tc.tick)
    
    def add_time_signature_change(self, tick: int, numerator: int, denominator: int):
        """Add a time signature change at the specified tick"""
        time_sig_change = TimeSignatureChange(tick, numerator, denominator)
        
        # Remove any existing time signature change at the same tick
        self.time_signature_changes = [tsc for tsc in self.time_signature_changes if tsc.tick != tick]
        
        # Add new time signature change and sort by tick
        self.time_signature_changes.append(time_sig_change)
        self.time_signature_changes.sort(key=lambda tsc: tsc.tick)
    
    def get_tempo_at_tick(self, tick: int) -> float:
        """Get the tempo (BPM) at the specified tick"""
        current_tempo = 120.0  # Default
        
        for tempo_change in self.tempo_changes:
            if tempo_change.tick <= tick:
                current_tempo = tempo_change.bpm
            else:
                break
        
        return current_tempo
    
    def get_time_signature_at_tick(self, tick: int) -> Tuple[int, int]:
        """Get the time signature at the specified tick"""
        current_time_sig = (4, 4)  # Default
        
        for time_sig_change in self.time_signature_changes:
            if time_sig_change.tick <= tick:
                current_time_sig = (time_sig_change.numerator, time_sig_change.denominator)
            else:
                break
        
        return current_time_sig
    
    def get_current_tempo(self) -> float:
        """Get the current tempo (first tempo change)"""
        if self.tempo_changes:
            return self.tempo_changes[0].bpm
        return 120.0
    
    def get_current_time_signature(self) -> Tuple[int, int]:
        """Get the current time signature (first time signature change)"""
        if self.time_signature_changes:
            ts = self.time_signature_changes[0]
            return (ts.numerator, ts.denominator)
        return (4, 4)
    
    def set_global_tempo(self, bpm: float):
        """Set global tempo (updates the first tempo change)"""
        if self.tempo_changes:
            self.tempo_changes[0] = TempoChange.from_bpm(0, bpm)
        else:
            self.tempo_changes.append(TempoChange.from_bpm(0, bpm))
    
    def set_global_time_signature(self, numerator: int, denominator: int):
        """Set global time signature (updates the first time signature change)"""
        if self.time_signature_changes:
            self.time_signature_changes[0] = TimeSignatureChange(0, numerator, denominator)
        else:
            self.time_signature_changes.append(TimeSignatureChange(0, numerator, denominator))
