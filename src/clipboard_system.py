"""
Clipboard system for copy/paste functionality
"""
from typing import List, Optional
from src.midi_data_model import MidiNote
import copy


class ClipboardData:
    """Represents data stored in the clipboard"""
    
    def __init__(self, notes: List[MidiNote], reference_tick: int = 0, reference_pitch: int = 60):
        """
        Args:
            notes: List of notes to store
            reference_tick: Reference tick for relative positioning
            reference_pitch: Reference pitch for relative positioning
        """
        self.notes = [copy.deepcopy(note) for note in notes]
        self.reference_tick = reference_tick
        self.reference_pitch = reference_pitch
        
        # Calculate relative positions
        if self.notes:
            min_tick = min(note.start_tick for note in self.notes)
            min_pitch = min(note.pitch for note in self.notes)
            for note in self.notes:
                note.start_tick -= min_tick
                note.end_tick -= min_tick
                note.pitch -= min_pitch
    
    def get_notes_at_position(self, target_tick: int, target_pitch: int = None) -> List[MidiNote]:
        """Get notes positioned at the target tick and pitch"""
        result_notes = []
        for note in self.notes:
            new_note = copy.deepcopy(note)
            new_note.start_tick += target_tick
            new_note.end_tick += target_tick
            
            # Handle pitch positioning
            if target_pitch is not None:
                new_note.pitch += target_pitch
            else:
                # Fallback to original pitch if no target pitch specified
                new_note.pitch += self.reference_pitch
            
            result_notes.append(new_note)
        return result_notes


class Clipboard:
    """Global clipboard for note operations"""
    
    def __init__(self):
        self._data: Optional[ClipboardData] = None
    
    def copy_notes(self, notes: List[MidiNote], reference_tick: int = 0, reference_pitch: int = 60):
        """Copy notes to clipboard"""
        if notes:
            self._data = ClipboardData(notes, reference_tick, reference_pitch)
    
    def paste_notes(self, target_tick: int, target_pitch: int = None) -> List[MidiNote]:
        """Paste notes from clipboard at target position"""
        if self._data:
            return self._data.get_notes_at_position(target_tick, target_pitch)
        return []
    
    def has_data(self) -> bool:
        """Check if clipboard has data"""
        return self._data is not None
    
    def clear(self):
        """Clear clipboard"""
        self._data = None


# Global clipboard instance
global_clipboard = Clipboard()