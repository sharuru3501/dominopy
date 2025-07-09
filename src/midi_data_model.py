
from typing import List, Dict

class MidiNote:
    def __init__(self, pitch: int, start_tick: int, end_tick: int, velocity: int, channel: int = 0):
        self.pitch = pitch  # MIDI note number (0-127)
        self.start_tick = start_tick # Start time in MIDI ticks
        self.end_tick = end_tick    # End time in MIDI ticks
        self.velocity = velocity  # Velocity (0-127)
        self.channel = channel    # MIDI channel (0-15)

    @property
    def duration(self):
        return self.end_tick - self.start_tick

class MidiTrack:
    def __init__(self, name: str = "New Track", channel: int = 0, program: int = 0):
        self.name = name
        self.channel = channel
        self.program = program # MIDI program number (instrument)
        self.notes: List[MidiNote] = []
        # Add other MIDI events later (e.g., CC, Pitch Bend)

class MidiProject:
    def __init__(self):
        self.tracks: List[MidiTrack] = []
        self.tempo_map: List[Dict[str, int]] = [] # [{'tick': 0, 'tempo': 500000}] (microseconds per beat)
        self.time_signature_map: List[Dict[str, int]] = [] # [{'tick': 0, 'numerator': 4, 'denominator': 4}]
        self.ticks_per_beat: int = 480 # Default for MIDI files
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
