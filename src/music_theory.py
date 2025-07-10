"""
Music theory utilities for PyDomino
Handles note names, chord detection, and music analysis
"""
from typing import List, Set, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class NoteQuality(Enum):
    """Note quality enumeration"""
    NATURAL = "natural"
    SHARP = "sharp"
    FLAT = "flat"

@dataclass
class Note:
    """Represents a musical note"""
    pitch: int  # MIDI pitch (0-127)
    name: str   # Note name (C, C#, Db, etc.)
    octave: int # Octave number
    
    def __str__(self):
        return f"{self.name}{self.octave}"

@dataclass
class Chord:
    """Represents a musical chord"""
    root_note: Note
    chord_type: str  # "major", "minor", "7th", etc.
    name: str        # Full chord name (C, Am, F7, etc.)
    notes: List[Note]
    
    def __str__(self):
        return self.name

class MusicTheory:
    """Main music theory processing class"""
    
    # Standard note names (chromatic scale)
    CHROMATIC_NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    FLAT_NOTES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
    
    # Common chord patterns (intervals from root)
    # Ordered by specificity - exact matches first, then less specific
    CHORD_PATTERNS = {
        # 13th chords (most complex, need exact match)
        "major13": [0, 4, 7, 11, 2, 5, 9],     # C maj13: C-E-G-B-D-F-A
        "minor13": [0, 3, 7, 10, 2, 5, 9],     # C m13: C-Eb-G-Bb-D-F-A
        "dominant13": [0, 4, 7, 10, 2, 5, 9],  # C13: C-E-G-Bb-D-F-A
        
        # Specific altered chords first
        "diminished7": [0, 3, 6, 9],           # C dim7: C-Eb-Gb-A
        "minor7flat5": [0, 3, 6, 10],          # C m7b5: C-Eb-Gb-Bb (half-diminished)
        "major7sharp11": [0, 4, 7, 11, 6],     # C maj7#11: C-E-G-B-F#
        "dominant7sharp11": [0, 4, 7, 10, 6],  # C7#11: C-E-G-Bb-F#
        "dominant7flat9": [0, 4, 7, 10, 1],    # C7b9: C-E-G-Bb-Db
        "dominant7sharp9": [0, 4, 7, 10, 3],   # C7#9: C-E-G-Bb-Eb
        "major7flat5": [0, 4, 6, 11],          # C maj7b5: C-E-Gb-B
        "dominant7flat5": [0, 4, 6, 10],       # C7b5: C-E-Gb-Bb
        "augmented7": [0, 4, 8, 10],           # C aug7: C-E-G#-Bb
        "augmented_major7": [0, 4, 8, 11],     # C aug maj7: C-E-G#-B
        
        # 11th chords
        "major11": [0, 4, 7, 11, 2, 5],        # C maj11: C-E-G-B-D-F
        "minor11": [0, 3, 7, 10, 2, 5],        # C m11: C-Eb-G-Bb-D-F
        "dominant11": [0, 4, 7, 10, 2, 5],     # C11: C-E-G-Bb-D-F
        
        # 9th chords - exact patterns first
        "major9": [0, 4, 7, 11, 2],            # C maj9: C-E-G-B-D
        "minor9": [0, 3, 7, 10, 2],            # C m9: C-Eb-G-Bb-D
        "dominant9": [0, 4, 7, 10, 2],         # C9: C-E-G-Bb-D
        
        # 9th chords without 5th
        "major9_no5": [0, 4, 11, 2],           # C maj9 (no 5th): C-E-B-D
        "minor9_no5": [0, 3, 10, 2],           # C m9 (no 5th): C-Eb-Bb-D
        "dominant9_no5": [0, 4, 10, 2],        # C9 (no 5th): C-E-Bb-D
        "add11": [0, 4, 7, 5],                 # C add11: C-E-G-F
        "add13": [0, 4, 7, 9],                 # C add13: C-E-G-A
        
        # Standard 7th chords
        "major7": [0, 4, 7, 11],      # C maj7: C-E-G-B
        "minor7": [0, 3, 7, 10],      # C min7: C-Eb-G-Bb
        "dominant7": [0, 4, 7, 10],   # C7: C-E-G-Bb
        
        # Sus and add chords
        "sus4_7": [0, 5, 7, 10],      # C sus4 7: C-F-G-Bb
        "sus2_7": [0, 2, 7, 10],      # C sus2 7: C-D-G-Bb
        "add9": [0, 2, 4, 7],         # C add9: C-D-E-G
        "sus4": [0, 5, 7],            # C sus4: C-F-G
        "sus2": [0, 2, 7],            # C sus2: C-D-G
        
        # Basic triads and altered
        "diminished": [0, 3, 6],      # C dim: C-Eb-Gb
        "augmented": [0, 4, 8],       # C aug: C-E-G#
        "major": [0, 4, 7],           # C major: C-E-G
        "minor": [0, 3, 7],           # C minor: C-Eb-G
    }
    
    # Chord name suffixes
    CHORD_SUFFIXES = {
        # Extended/Tension chords
        "major13": "maj13",
        "minor13": "m13",
        "dominant13": "13",
        "major11": "maj11",
        "minor11": "m11",
        "dominant11": "11",
        "major9": "maj9",
        "minor9": "m9",
        "dominant9": "9",
        "major9_no5": "maj9",
        "minor9_no5": "m9", 
        "dominant9_no5": "9",
        "add11": "add11",
        "add13": "add13",
        "major7sharp11": "maj7#11",
        "dominant7sharp11": "7#11",
        "dominant7flat9": "7b9",
        "dominant7sharp9": "7#9",
        "minor7flat5": "m7b5",
        "diminished7": "dim7",
        "major7flat5": "maj7b5",
        "dominant7flat5": "7b5",
        "augmented7": "aug7",
        "augmented_major7": "augmaj7",
        
        # Standard chords
        "major7": "maj7",
        "minor7": "m7",
        "dominant7": "7",
        "sus4_7": "sus47",
        "sus2_7": "sus27",
        "add9": "add9",
        "sus4": "sus4",
        "sus2": "sus2",
        "diminished": "dim",
        "augmented": "aug",
        "major": "",
        "minor": "m",
    }
    
    @classmethod
    def midi_to_note(cls, midi_pitch: int, use_flats: bool = False, octave_offset: int = -1) -> Note:
        """Convert MIDI pitch to Note object with configurable octave offset
        
        Args:
            midi_pitch: MIDI pitch value (0-127)
            use_flats: Whether to use flat notation instead of sharps
            octave_offset: Octave offset for different standards
                          -1 = Roland/Scientific (C4 = MIDI 60)
                          -2 = Yamaha (C3 = MIDI 60)
        """
        if midi_pitch < 0 or midi_pitch > 127:
            raise ValueError(f"MIDI pitch must be 0-127, got {midi_pitch}")
        
        octave = midi_pitch // 12 + octave_offset
        note_index = midi_pitch % 12
        
        note_names = cls.FLAT_NOTES if use_flats else cls.CHROMATIC_NOTES
        note_name = note_names[note_index]
        
        return Note(pitch=midi_pitch, name=note_name, octave=octave)
    
    @classmethod
    def note_to_midi(cls, note_name: str, octave: int) -> int:
        """Convert note name and octave to MIDI pitch"""
        # Handle both sharp and flat notation
        if note_name in cls.CHROMATIC_NOTES:
            note_index = cls.CHROMATIC_NOTES.index(note_name)
        elif note_name in cls.FLAT_NOTES:
            note_index = cls.FLAT_NOTES.index(note_name)
        else:
            raise ValueError(f"Invalid note name: {note_name}")
        
        return (octave + 1) * 12 + note_index
    
    @classmethod
    def get_note_name(cls, midi_pitch: int, use_flats: bool = False, octave_offset: int = -1) -> str:
        """Get simple note name from MIDI pitch"""
        note = cls.midi_to_note(midi_pitch, use_flats, octave_offset)
        return note.name
    
    @classmethod
    def get_note_name_with_octave(cls, midi_pitch: int, use_flats: bool = False, octave_offset: int = -1) -> str:
        """Get note name with octave from MIDI pitch"""
        note = cls.midi_to_note(midi_pitch, use_flats, octave_offset)
        return str(note)
    
    @classmethod
    def detect_chord(cls, midi_pitches: List[int]) -> Optional[Chord]:
        """Detect chord from a list of MIDI pitches"""
        if len(midi_pitches) < 2:
            return None
        
        # Remove duplicates and sort
        unique_pitches = sorted(set(midi_pitches))
        
        # Convert to note classes (0-11)
        note_classes = [pitch % 12 for pitch in unique_pitches]
        unique_note_classes = sorted(set(note_classes))
        
        if len(unique_note_classes) < 2:
            return None
        
        # Try each note as potential root
        for root_class in unique_note_classes:
            chord = cls._try_chord_with_root(unique_note_classes, root_class, unique_pitches[0])
            if chord:
                return chord
        
        # If no standard chord found, return generic chord name
        root_note = cls.midi_to_note(unique_pitches[0])
        notes = [cls.midi_to_note(pitch) for pitch in unique_pitches]
        return Chord(
            root_note=root_note,
            chord_type="custom",
            name=f"{root_note.name}({len(unique_pitches)})",
            notes=notes
        )
    
    @classmethod
    def _try_chord_with_root(cls, note_classes: List[int], root: int, base_pitch: int) -> Optional[Chord]:
        """Try to identify chord with given root note"""
        # Normalize intervals relative to root
        intervals = [(note - root) % 12 for note in note_classes]
        intervals = sorted(set(intervals))
        
        # Check against known chord patterns (in order of complexity)
        for chord_type, pattern in cls.CHORD_PATTERNS.items():
            if cls._matches_pattern(intervals, pattern):
                # Find appropriate octave for root note
                root_pitch = base_pitch
                while (root_pitch % 12) != root:
                    root_pitch += 1
                    if root_pitch > 127:  # Safety check
                        root_pitch = root + 60  # Default to middle C octave
                        break
                
                root_note = cls.midi_to_note(root_pitch)
                chord_name = f"{root_note.name}{cls.CHORD_SUFFIXES[chord_type]}"
                
                # Build chord notes from pattern for consistent display
                chord_notes = []
                for interval in pattern:
                    chord_pitch = root_note.pitch + interval
                    if chord_pitch <= 127:
                        chord_notes.append(cls.midi_to_note(chord_pitch))
                
                return Chord(
                    root_note=root_note,
                    chord_type=chord_type,
                    name=chord_name,
                    notes=chord_notes
                )
        
        return None
    
    @classmethod
    def _matches_pattern(cls, intervals: List[int], pattern: List[int]) -> bool:
        """Check if interval set matches chord pattern - simplified and more accurate"""
        interval_set = set(intervals)
        pattern_set = set(pattern)
        
        # Exact match gets highest priority
        if interval_set == pattern_set:
            return True
        
        # For subset matching - pattern must be completely contained in intervals
        if pattern_set.issubset(interval_set):
            # Calculate how well the pattern fits the input
            pattern_coverage = len(pattern_set) / len(interval_set)
            
            # Prefer patterns that cover most of the input notes
            if pattern_coverage >= 0.8:  # Pattern accounts for 80%+ of input
                return True
            elif len(pattern_set) >= 4 and pattern_coverage >= 0.6:  # For complex chords, allow 60%
                return True
            elif len(pattern_set) == len(interval_set) - 1:  # Only 1 extra note in input
                return True
        
        return False
    
    @classmethod
    def analyze_harmony(cls, midi_pitches: List[int]) -> Dict[str, any]:
        """Comprehensive harmony analysis"""
        if not midi_pitches:
            return {"notes": [], "chord": None, "key_suggestions": []}
        
        # Individual notes
        notes = [cls.midi_to_note(pitch) for pitch in midi_pitches]
        
        # Chord detection
        chord = cls.detect_chord(midi_pitches)
        
        # Key suggestions (simplified)
        key_suggestions = cls._suggest_keys(midi_pitches)
        
        return {
            "notes": notes,
            "chord": chord,
            "key_suggestions": key_suggestions,
            "note_count": len(set(midi_pitches))
        }
    
    @classmethod
    def _suggest_keys(cls, midi_pitches: List[int]) -> List[str]:
        """Suggest possible keys based on notes"""
        # Simplified key detection - just return major keys that contain most notes
        note_classes = set(pitch % 12 for pitch in midi_pitches)
        
        # Major scale patterns
        major_scales = {}
        for root in range(12):
            scale_notes = {(root + interval) % 12 for interval in [0, 2, 4, 5, 7, 9, 11]}
            key_name = cls.CHROMATIC_NOTES[root]
            major_scales[key_name] = scale_notes
        
        # Score each key by how many notes it contains
        key_scores = []
        for key_name, scale_notes in major_scales.items():
            score = len(note_classes.intersection(scale_notes))
            if score > 0:
                key_scores.append((key_name, score))
        
        # Sort by score and return top suggestions
        key_scores.sort(key=lambda x: x[1], reverse=True)
        return [key for key, score in key_scores[:3]]

# Convenience functions for common operations
def get_note_name(midi_pitch: int, use_flats: bool = False) -> str:
    """Get note name from MIDI pitch"""
    return MusicTheory.get_note_name(midi_pitch, use_flats)

def get_note_name_with_octave(midi_pitch: int, use_flats: bool = False) -> str:
    """Get note name with octave from MIDI pitch"""
    return MusicTheory.get_note_name_with_octave(midi_pitch, use_flats)

def detect_chord(midi_pitches: List[int]) -> Optional[Chord]:
    """Detect chord from MIDI pitches"""
    return MusicTheory.detect_chord(midi_pitches)

def analyze_harmony(midi_pitches: List[int]) -> Dict[str, any]:
    """Analyze harmony from MIDI pitches"""
    return MusicTheory.analyze_harmony(midi_pitches)