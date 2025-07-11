"""
Command pattern implementation for Undo/Redo system
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from src.midi_data_model import MidiNote, MidiTrack, MidiProject


class Command(ABC):
    """Abstract base class for all commands"""
    
    @abstractmethod
    def execute(self):
        """Execute the command"""
        pass
    
    @abstractmethod
    def undo(self):
        """Undo the command"""
        pass


class AddNoteCommand(Command):
    """Command to add a note to a track"""
    
    def __init__(self, track: MidiTrack, note: MidiNote):
        self.track = track
        self.note = note
    
    def execute(self):
        self.track.notes.append(self.note)
    
    def undo(self):
        if self.note in self.track.notes:
            self.track.notes.remove(self.note)


class DeleteNoteCommand(Command):
    """Command to delete a note from a track"""
    
    def __init__(self, track: MidiTrack, note: MidiNote):
        self.track = track
        self.note = note
    
    def execute(self):
        if self.note in self.track.notes:
            self.track.notes.remove(self.note)
    
    def undo(self):
        self.track.notes.append(self.note)


class MoveNoteCommand(Command):
    """Command to move a note"""
    
    def __init__(self, note: MidiNote, old_start_tick: int, old_pitch: int, 
                 new_start_tick: int, new_pitch: int):
        self.note = note
        self.old_start_tick = old_start_tick
        self.old_pitch = old_pitch
        self.new_start_tick = new_start_tick
        self.new_pitch = new_pitch
        self.old_end_tick = note.end_tick
        self.duration = note.duration
    
    def execute(self):
        self.note.start_tick = self.new_start_tick
        self.note.pitch = self.new_pitch
        self.note.end_tick = self.new_start_tick + self.duration
    
    def undo(self):
        self.note.start_tick = self.old_start_tick
        self.note.pitch = self.old_pitch
        self.note.end_tick = self.old_end_tick


class ResizeNoteCommand(Command):
    """Command to resize a note"""
    
    def __init__(self, note: MidiNote, old_start_tick: int, old_end_tick: int,
                 new_start_tick: int, new_end_tick: int):
        self.note = note
        self.old_start_tick = old_start_tick
        self.old_end_tick = old_end_tick
        self.new_start_tick = new_start_tick
        self.new_end_tick = new_end_tick
    
    def execute(self):
        self.note.start_tick = self.new_start_tick
        self.note.end_tick = self.new_end_tick
    
    def undo(self):
        self.note.start_tick = self.old_start_tick
        self.note.end_tick = self.old_end_tick


class DeleteMultipleNotesCommand(Command):
    """Command to delete multiple notes"""
    
    def __init__(self, track_note_pairs: List[tuple]):
        """
        Args:
            track_note_pairs: List of (track, note) tuples
        """
        self.track_note_pairs = track_note_pairs
    
    def execute(self):
        for track, note in self.track_note_pairs:
            if note in track.notes:
                track.notes.remove(note)
    
    def undo(self):
        for track, note in self.track_note_pairs:
            track.notes.append(note)


class PasteNotesCommand(Command):
    """Command to paste notes"""
    
    def __init__(self, track: MidiTrack, notes: List[MidiNote]):
        self.track = track
        self.notes = notes
    
    def execute(self):
        for note in self.notes:
            self.track.notes.append(note)
    
    def undo(self):
        for note in self.notes:
            if note in self.track.notes:
                self.track.notes.remove(note)


class CutNotesCommand(Command):
    """Command to cut notes (copy + delete)"""
    
    def __init__(self, track_note_pairs: List[tuple]):
        """
        Args:
            track_note_pairs: List of (track, note) tuples
        """
        self.track_note_pairs = track_note_pairs
    
    def execute(self):
        for track, note in self.track_note_pairs:
            if note in track.notes:
                track.notes.remove(note)
    
    def undo(self):
        for track, note in self.track_note_pairs:
            track.notes.append(note)


class CommandHistory:
    """Manages command history for undo/redo functionality"""
    
    def __init__(self):
        self.commands: List[Command] = []
        self.current_index = -1
    
    def execute_command(self, command: Command):
        """Execute a command and add it to history"""
        command.execute()
        
        # Remove any commands after current index (for redo after undo)
        self.commands = self.commands[:self.current_index + 1]
        
        # Add new command
        self.commands.append(command)
        self.current_index += 1
    
    def undo(self) -> bool:
        """Undo the last command"""
        if self.current_index >= 0:
            command = self.commands[self.current_index]
            command.undo()
            self.current_index -= 1
            return True
        return False
    
    def redo(self) -> bool:
        """Redo the next command"""
        if self.current_index < len(self.commands) - 1:
            self.current_index += 1
            command = self.commands[self.current_index]
            command.execute()
            return True
        return False
    
    def can_undo(self) -> bool:
        """Check if undo is possible"""
        return self.current_index >= 0
    
    def can_redo(self) -> bool:
        """Check if redo is possible"""
        return self.current_index < len(self.commands) - 1
    
    def clear(self):
        """Clear command history"""
        self.commands.clear()
        self.current_index = -1

class MoveMultipleNotesCommand(Command):
    """Command to move multiple notes"""
    
    def __init__(self, notes_with_deltas: List[tuple]):
        """
        Initialize with list of (note, old_start_tick, old_pitch, new_start_tick, new_pitch) tuples
        """
        self.notes_with_deltas = notes_with_deltas
    
    def execute(self):
        """Execute the move command"""
        for note, old_start_tick, old_pitch, new_start_tick, new_pitch in self.notes_with_deltas:
            # Calculate duration to preserve note length
            duration = note.end_tick - note.start_tick
            
            # Apply new position
            note.start_tick = new_start_tick
            note.end_tick = new_start_tick + duration
            note.pitch = new_pitch
    
    def undo(self):
        """Undo the move command"""
        for note, old_start_tick, old_pitch, new_start_tick, new_pitch in self.notes_with_deltas:
            # Calculate duration to preserve note length
            duration = note.end_tick - note.start_tick
            
            # Restore original position
            note.start_tick = old_start_tick
            note.end_tick = old_start_tick + duration
            note.pitch = old_pitch

class ResizeMultipleNotesCommand(Command):
    """Command to resize multiple notes"""
    
    def __init__(self, notes_with_resize_data: List[tuple]):
        """
        Initialize with list of (note, old_start_tick, old_end_tick, new_start_tick, new_end_tick) tuples
        """
        self.notes_with_resize_data = notes_with_resize_data
    
    def execute(self):
        """Execute the resize command"""
        for note, old_start_tick, old_end_tick, new_start_tick, new_end_tick in self.notes_with_resize_data:
            note.start_tick = new_start_tick
            note.end_tick = new_end_tick
    
    def undo(self):
        """Undo the resize command"""
        for note, old_start_tick, old_end_tick, new_start_tick, new_end_tick in self.notes_with_resize_data:
            note.start_tick = old_start_tick
            note.end_tick = old_end_tick