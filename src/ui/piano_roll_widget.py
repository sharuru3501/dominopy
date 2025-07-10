
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QFont
from typing import List

from src.midi_data_model import MidiProject, MidiNote
from src.command_system import (
    CommandHistory, AddNoteCommand, DeleteNoteCommand, MoveNoteCommand,
    ResizeNoteCommand, DeleteMultipleNotesCommand, PasteNotesCommand, CutNotesCommand
)
from src.clipboard_system import global_clipboard
from src.edit_modes import EditMode, EditModeManager
from src.grid_system import GridManager, GridCell
from src.audio_system import get_audio_manager
import copy

class PianoRollWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        self.setStyleSheet("background-color: #282c34;") # Dark background
        self.midi_project: MidiProject = None

        # Scaling factors (pixels per tick, pixels per pitch)
        self.pixels_per_tick = 0.12 # Adjust as needed
        self.pixels_per_pitch = 10 # Adjust as needed

        # Visible range (in ticks)
        self.visible_start_tick = 0
        self.visible_end_tick = 0 # Will be calculated dynamically

        self.selected_notes: List[MidiNote] = []
        self.dragging_note: MidiNote = None
        self.drag_start_pos = None # QPointF
        self.drag_start_note_pos = None # (start_tick, pitch)
        self.resizing_note: MidiNote = None
        self.resize_start_tick: int = 0
        self.resizing_left_edge: bool = False # New flag for left edge resizing
        self.drag_original_duration: int = 0 # Store original duration for dragging

        # Quantization unit (e.g., 16th note by default)
        self.quantize_grid_ticks = 480 // 4 # Default to 16th note (480 ticks/beat / 4 = 120 ticks)
        
        # Command history for undo/redo
        self.command_history = CommandHistory()
        
        # Edit mode manager
        self.edit_mode_manager = EditModeManager()
        self.edit_mode_manager.mode_changed.connect(self._on_mode_changed)
        
        # Grid system
        self.grid_manager = GridManager()
        
        # Update grid settings to match piano roll
        if self.midi_project:
            self.grid_manager.update_grid_settings(self.midi_project.ticks_per_beat, 4)
        else:
            self.grid_manager.update_grid_settings(480, 4)
        
        # Enable focus to receive keyboard events
        self.setFocusPolicy(Qt.StrongFocus)

        # Initialize with default empty project state
        self.set_midi_project(None) 

    def set_midi_project(self, project: MidiProject):
        self.midi_project = project
        self.selected_notes = [] # Clear selection on new project
        self.dragging_note = None
        self.resizing_note = None
        self.resizing_left_edge = False # Clear flag
        self.command_history.clear() # Clear command history on new project
        self.edit_mode_manager.clear_selection_rectangle() # Clear selection rectangle
        self.grid_manager.clear_selection() # Clear grid selection
        self.grid_manager.clear_paste_target() # Clear paste target
        
        # Update grid settings
        if self.midi_project:
            self.grid_manager.update_grid_settings(self.midi_project.ticks_per_beat, 4)
        else:
            self.grid_manager.update_grid_settings(480, 4)
        
        if self.midi_project:
            max_tick = 0
            for track in self.midi_project.tracks:
                for note in track.notes:
                    if note.end_tick > max_tick:
                        max_tick = note.end_tick
            # Add some padding (e.g., 4 beats) to the end
            padding_ticks = self.midi_project.ticks_per_beat * 4
            self.visible_end_tick = max_tick + padding_ticks
            # Ensure a minimum visible length, e.g., 32 beats
            min_visible_ticks = self.midi_project.ticks_per_beat * 32
            if self.visible_end_tick < min_visible_ticks:
                self.visible_end_tick = min_visible_ticks
            print(f"DEBUG: visible_end_tick = {self.visible_end_tick}") # DEBUG
        else:
            self.visible_end_tick = 480 * 32 # Default to 32 beats if no project
            print(f"DEBUG: visible_end_tick (no project) = {self.visible_end_tick}") # DEBUG
        self.update() # Request a repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        # Draw grid (simplified for now)
        # Horizontal lines for pitches (every MIDI note)
        for pitch in range(0, 128): # All 128 MIDI pitches
            y = self._pitch_to_y(pitch)
            if pitch % 12 == 0: # C notes (octaves)
                painter.setPen(QColor("#8be9fd")) # Light blue for C notes
            else:
                painter.setPen(QColor("#3e4452")) # Lighter for other notes
            painter.drawLine(0, int(y), width, int(y))

        # Vertical lines for beats and subdivisions
        ticks_per_beat = self.midi_project.ticks_per_beat if self.midi_project else 480
        # Draw lines for every beat (quarter note)
        for tick in range(self.visible_start_tick, self.visible_end_tick + ticks_per_beat, ticks_per_beat):
            x = self._tick_to_x(tick)
            if tick % (ticks_per_beat * 4) == 0: # Every measure (assuming 4/4)
                painter.setPen(QColor("#ff79c6")) # Pink/magenta for measures
            else:
                painter.setPen(QColor("#3e4452")) # Lighter for beats
            painter.drawLine(int(x), 0, int(x), height)

        painter.drawLine(int(x), 0, int(x), height)

        # Draw MIDI notes
        if self.midi_project:
            for track in self.midi_project.tracks:
                for note in track.notes:
                    x = self._tick_to_x(note.start_tick)
                    y = self._pitch_to_y(note.pitch)
                    note_width = note.duration * self.pixels_per_tick
                    note_height = self.pixels_per_pitch

                    # Only draw if visible
                    if x < width and x + note_width > 0:
                        # Draw note rectangle
                        if note in self.selected_notes:
                            painter.setBrush(QColor("#f1fa8c")) # Yellow for selected notes
                        else:
                            painter.setBrush(QColor("#61afef")) # Blue for unselected notes
                        painter.setPen(Qt.NoPen)
                        painter.drawRect(int(x), int(y), int(note_width), int(note_height))

        # Draw grid cells (selected cells and paste target)
        self.grid_manager.draw_grid_cells(painter, self.pixels_per_tick, 
                                        self.pixels_per_pitch, height, 
                                        self.visible_start_tick)
        
        # Draw selection rectangle if in selection mode
        selection_rect = self.edit_mode_manager.get_selection_rectangle()
        if selection_rect:
            selection_rect.draw(painter)
        
        # Draw mode indicator
        self._draw_mode_indicator(painter, width, height)

        painter.end()

    def _tick_to_x(self, tick: int) -> float:
        return (tick - self.visible_start_tick) * self.pixels_per_tick

    def _pitch_to_y(self, pitch: int) -> float:
        # Map MIDI pitch to Y-coordinate. Higher pitch should be higher on screen.
        # We want pitch 0 at the bottom, pitch 127 at the top.
        # Y-axis in Qt goes from top (0) to bottom (height).
        # So, higher pitch should have a smaller Y value.
        # We want to draw from the top of the note's cell.
        return self.height() - ((pitch + 1) * self.pixels_per_pitch)

    def _x_to_tick(self, x: int) -> int:
        return int(x / self.pixels_per_tick) + self.visible_start_tick

    def _y_to_pitch(self, y: int) -> int:
        # Invert the _pitch_to_y logic
        # y = height - ((pitch + 1) * pixels_per_pitch)
        # (pitch + 1) * pixels_per_pitch = height - y
        # pitch + 1 = (height - y) / pixels_per_pitch
        # pitch = (height - y) / pixels_per_pitch - 1
        pitch = int((self.height() - y) / self.pixels_per_pitch)
        # Clamp pitch to valid MIDI range
        return max(0, min(127, pitch))

    def mousePressEvent(self, event):
        # Ensure this widget has focus for keyboard events
        if not self.hasFocus():
            self.setFocus()
            print("DEBUG: Setting focus to piano roll widget")
        
        if event.button() == Qt.LeftButton:
            clicked_x = event.position().x()
            clicked_y = event.position().y()
            clicked_tick = self._x_to_tick(clicked_x)
            clicked_pitch = self._y_to_pitch(clicked_y)

            # Quantize clicked_tick to the nearest grid unit
            clicked_tick = round(clicked_tick / self.quantize_grid_ticks) * self.quantize_grid_ticks

            # Ensure clicked_tick is not negative
            clicked_tick = max(0, clicked_tick)

            print(f"DEBUG: Mouse clicked at tick {clicked_tick}, pitch {clicked_pitch}")

            # Handle different modes
            if self.edit_mode_manager.is_note_input_mode():
                self._handle_note_input_mode_click(event, clicked_x, clicked_y, clicked_tick, clicked_pitch)
            elif self.edit_mode_manager.is_selection_mode():
                self._handle_selection_mode_click(event, clicked_x, clicked_y)

            self.update() # Request repaint

        elif event.button() == Qt.RightButton:
            print(f"DEBUG: Right-click detected at ({event.position().x()}, {event.position().y()})") # DEBUG
            clicked_x = event.position().x()
            clicked_y = event.position().y()

            note_found_for_deletion = False
            if self.midi_project:
                for track in self.midi_project.tracks:
                    for note in track.notes:
                        note_x = self._tick_to_x(note.start_tick)
                        note_y = self._pitch_to_y(note.pitch)
                        note_width = note.duration * self.pixels_per_tick
                        note_height = self.pixels_per_pitch

                        if note_x <= clicked_x < (note_x + note_width) and \
                           note_y <= clicked_y < (note_y + note_height):
                            print(f"DEBUG: Note {note} found under right-click.") # DEBUG
                            self.selected_notes = [note] # Select the note for deletion
                            self._delete_selected_notes_with_command() # Delete it immediately
                            note_found_for_deletion = True
                            break # Note found and deleted, stop searching
                    if note_found_for_deletion:
                        break
            
            if not note_found_for_deletion:
                print("DEBUG: No note found under right-click. Clearing selection.") # DEBUG
                self.selected_notes = [] # Clear selection if no note was right-clicked

            self.update() # Request repaint

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.edit_mode_manager.is_note_input_mode():
            self._handle_note_input_mode_move(event)
        elif self.edit_mode_manager.is_selection_mode():
            self._handle_selection_mode_move(event)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.edit_mode_manager.is_note_input_mode():
            self._handle_note_input_mode_release(event)
        elif self.edit_mode_manager.is_selection_mode():
            self._handle_selection_mode_release(event)

        super().mouseReleaseEvent(event)

    def _delete_selected_notes_with_command(self):
        """Delete selected notes using command system"""
        print(f"DEBUG: _delete_selected_notes_with_command called. Selected notes: {self.selected_notes}") # DEBUG
        if not self.midi_project or not self.selected_notes:
            print("DEBUG: No project or no selected notes to delete.") # DEBUG
            return

        # Find track-note pairs for deletion
        track_note_pairs = []
        for note_to_delete in self.selected_notes:
            for track in self.midi_project.tracks:
                if note_to_delete in track.notes:
                    track_note_pairs.append((track, note_to_delete))
                    break
        
        if track_note_pairs:
            command = DeleteMultipleNotesCommand(track_note_pairs)
            self.command_history.execute_command(command)
            self.selected_notes = [] # Clear selection
            self.update() # Repaint
            print("DEBUG: _delete_selected_notes_with_command finished. UI updated.") # DEBUG
    
    def _delete_selected_notes(self):
        """Legacy method - calls the command version"""
        self._delete_selected_notes_with_command()

    def keyPressEvent(self, event):
        print(f"DEBUG: keyPressEvent received key: {event.key()}, modifiers: {event.modifiers()}") # DEBUG
        print(f"DEBUG: Widget has focus: {self.hasFocus()}")
        
        # Delete selected notes
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            print(f"DEBUG: Delete/Backspace key detected. Selected notes: {self.selected_notes}") # DEBUG
            self._delete_selected_notes_with_command()
        
        # Copy selected notes
        elif event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
            self._copy_selected_notes()
        
        # Cut selected notes
        elif event.key() == Qt.Key_X and event.modifiers() == Qt.ControlModifier:
            self._cut_selected_notes()
        
        # Paste notes
        elif event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier:
            print("DEBUG: Ctrl+V pressed - calling _paste_notes()")
            self._paste_notes()
        
        # Undo
        elif event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
            self._undo()
        
        # Redo
        elif event.key() == Qt.Key_Y and event.modifiers() == Qt.ControlModifier:
            self._redo()
        
        # Select all
        elif event.key() == Qt.Key_A and event.modifiers() == Qt.ControlModifier:
            self._select_all()
        
        # Toggle mode (Tab key)
        elif event.key() == Qt.Key_Tab:
            self.edit_mode_manager.toggle_mode()
        
        # Switch to note input mode (1 key)
        elif event.key() == Qt.Key_1:
            self.edit_mode_manager.set_mode(EditMode.NOTE_INPUT)
        
        # Switch to selection mode (2 key)
        elif event.key() == Qt.Key_2:
            self.edit_mode_manager.set_mode(EditMode.SELECTION)

        super().keyPressEvent(event)
    
    def _copy_selected_notes(self):
        """Copy selected notes to clipboard"""
        if self.selected_notes:
            # Calculate reference tick and pitch (earliest note's start tick and lowest pitch)
            reference_tick = min(note.start_tick for note in self.selected_notes)
            reference_pitch = min(note.pitch for note in self.selected_notes)
            global_clipboard.copy_notes(self.selected_notes, reference_tick, reference_pitch)
            print(f"DEBUG: Copied {len(self.selected_notes)} notes to clipboard with reference tick {reference_tick}, pitch {reference_pitch}")
    
    def _cut_selected_notes(self):
        """Cut selected notes to clipboard"""
        if not self.selected_notes:
            print("DEBUG: No notes selected for cutting")
            return
        
        # Copy to clipboard first
        self._copy_selected_notes()
        
        # Find track-note pairs for cutting
        track_note_pairs = []
        for note_to_cut in self.selected_notes:
            for track in self.midi_project.tracks:
                if note_to_cut in track.notes:
                    track_note_pairs.append((track, note_to_cut))
                    break
        
        if track_note_pairs:
            command = CutNotesCommand(track_note_pairs)
            self.command_history.execute_command(command)
            self.selected_notes = [] # Clear selection after cutting
            self.update()
            print(f"DEBUG: Cut {len(track_note_pairs)} notes to clipboard")
    
    def _paste_notes(self):
        """Paste notes from clipboard"""
        if not global_clipboard.has_data():
            print("DEBUG: No data in clipboard to paste")
            return
        
        if not self.midi_project or not self.midi_project.tracks:
            print("DEBUG: No project or tracks to paste into")
            return
        
        # Debug: Show current state
        paste_target = self.grid_manager.get_paste_target_cell()
        selected_cells = self.grid_manager.get_selected_cells()
        print(f"DEBUG: Paste target cell: {paste_target}")
        print(f"DEBUG: Selected cells count: {len(selected_cells)}")
        print(f"DEBUG: Selected notes count: {len(self.selected_notes)}")
        
        # Determine paste target (both tick and pitch)
        target_tick = 0
        target_pitch = None
        source_description = "default position"
        
        # Priority 1: Use paste target cell if set
        if paste_target:
            target_tick = paste_target.start_tick
            target_pitch = paste_target.pitch
            source_description = f"paste target cell at tick {target_tick}, pitch {target_pitch}"
        
        # Priority 2: Use first selected grid cell
        elif selected_cells:
            first_cell = min(selected_cells, key=lambda c: c.start_tick)
            target_tick = first_cell.start_tick
            target_pitch = first_cell.pitch
            source_description = f"first selected grid cell at tick {target_tick}, pitch {target_pitch}"
        
        # Priority 3: Use selected notes position
        elif self.selected_notes:
            target_tick = min(note.start_tick for note in self.selected_notes)
            target_pitch = min(note.pitch for note in self.selected_notes)
            source_description = f"selected notes position at tick {target_tick}, pitch {target_pitch}"
        
        print(f"DEBUG: Using {source_description}")
        
        # Quantize target tick
        target_tick = round(target_tick / self.quantize_grid_ticks) * self.quantize_grid_ticks
        print(f"DEBUG: Quantized target tick: {target_tick}, target pitch: {target_pitch}")
        
        # Get notes from clipboard
        notes_to_paste = global_clipboard.paste_notes(target_tick, target_pitch)
        
        if notes_to_paste:
            # Use command system to paste notes
            command = PasteNotesCommand(self.midi_project.tracks[0], notes_to_paste)
            self.command_history.execute_command(command)
            
            # Select pasted notes
            self.selected_notes = notes_to_paste
            
            # Clear paste target after use, but keep selected cells
            self.grid_manager.clear_paste_target()
            # Don't clear grid selection automatically - let user decide
            
            self.update()
            print(f"DEBUG: Successfully pasted {len(notes_to_paste)} notes at tick {target_tick}, pitch {target_pitch}")
        else:
            print("DEBUG: No notes to paste from clipboard")
    
    def _undo(self):
        """Undo last operation"""
        if self.command_history.undo():
            self.selected_notes = [] # Clear selection after undo
            self.update()
            print("DEBUG: Undo performed")
        else:
            print("DEBUG: Nothing to undo")
    
    def _redo(self):
        """Redo last undone operation"""
        if self.command_history.redo():
            self.selected_notes = [] # Clear selection after redo
            self.update()
            print("DEBUG: Redo performed")
        else:
            print("DEBUG: Nothing to redo")
    
    def _select_all(self):
        """Select all notes in the project"""
        if not self.midi_project:
            return
        
        all_notes = []
        for track in self.midi_project.tracks:
            all_notes.extend(track.notes)
        
        self.selected_notes = all_notes
        self.update()
        print(f"DEBUG: Selected all {len(all_notes)} notes")
    
    def _on_mode_changed(self, mode: EditMode):
        """Handle mode change"""
        print(f"DEBUG: Mode changing to {mode.value}")
        print(f"DEBUG: Grid selected cells before mode change: {len(self.grid_manager.get_selected_cells())}")
        paste_target_before = self.grid_manager.get_paste_target_cell()
        print(f"DEBUG: Paste target before mode change: {paste_target_before}")
        
        self.edit_mode_manager.clear_selection_rectangle()
        # Don't clear grid selection when changing modes
        
        print(f"DEBUG: Grid selected cells after mode change: {len(self.grid_manager.get_selected_cells())}")
        paste_target_after = self.grid_manager.get_paste_target_cell()
        print(f"DEBUG: Paste target after mode change: {paste_target_after}")
        
        self.update()
    
    def _draw_mode_indicator(self, painter: QPainter, width: int, height: int):
        """Draw mode indicator in top-right corner"""
        painter.save()
        
        # Set font and color
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        
        mode_text = self.edit_mode_manager.get_mode_display_name()
        mode_color = QColor("#50c7e3") if self.edit_mode_manager.is_selection_mode() else QColor("#f39c12")
        
        painter.setPen(mode_color)
        painter.drawText(width - 200, 25, mode_text)
        
        # Draw description
        font.setPointSize(10)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#aaaaaa"))
        painter.drawText(width - 200, 45, self.edit_mode_manager.get_mode_description())
        
        painter.restore()
    
    def _handle_note_input_mode_click(self, event, clicked_x, clicked_y, clicked_tick, clicked_pitch):
        """Handle mouse click in note input mode"""
        # Check if an existing note was clicked or its right edge was clicked for resizing
        clicked_on_note = False
        if self.midi_project:
            for track in self.midi_project.tracks:
                for note in track.notes:
                    note_x = self._tick_to_x(note.start_tick)
                    note_y = self._pitch_to_y(note.pitch)
                    note_width = note.duration * self.pixels_per_tick
                    note_height = self.pixels_per_pitch

                    # Check if click is within note bounds
                    if note_x <= clicked_x < (note_x + note_width) and \
                       note_y <= clicked_y < (note_y + note_height):
                        # Check if click is near the right edge for resizing
                        resize_threshold = 5 # pixels
                        if clicked_x >= (note_x + note_width - resize_threshold):
                            self.resizing_note = note
                            self.resize_start_tick = note.start_tick
                            self.dragging_note = None # Not dragging, but resizing
                            self.selected_notes = [note] # Select note when resizing
                            clicked_on_note = True
                            break
                        # Check if click is near the left edge for resizing
                        elif clicked_x <= (note_x + resize_threshold):
                            print("DEBUG: Left edge resize detected!") # DEBUG
                            self.resizing_left_edge = True
                            self.resizing_note = note
                            self.resize_start_tick = note.start_tick
                            self.dragging_note = None
                            self.selected_notes = [note]
                            clicked_on_note = True
                            break
                        else:
                            # Select the note for dragging
                            self.selected_notes = [note] # For now, single selection
                            self.dragging_note = note
                            self.drag_start_pos = event.position()
                            self.drag_start_note_pos = (note.start_tick, note.pitch)
                            self.drag_original_duration = note.duration # Store original duration
                            clicked_on_note = True
                            break # Found a note, stop searching
                if clicked_on_note:
                    break

        if not clicked_on_note:
            # If no note was clicked, clear selection and create a new note
            self.selected_notes = []

            # If no project is loaded, create a new one
            if self.midi_project is None:
                self.set_midi_project(MidiProject()) # This will also add a default track

            default_duration_ticks = self.midi_project.ticks_per_beat if self.midi_project else 480
            new_note = MidiNote(
                pitch=clicked_pitch,
                start_tick=clicked_tick,
                end_tick=clicked_tick + default_duration_ticks,
                velocity=100, # Default velocity
                channel=0 # Default channel
            )

            # Add to the first track of the current project using command system
            if self.midi_project and self.midi_project.tracks:
                command = AddNoteCommand(self.midi_project.tracks[0], new_note)
                self.command_history.execute_command(command)
                
                # Play audio feedback for the new note
                audio_manager = get_audio_manager()
                if audio_manager:
                    audio_manager.play_note_preview(new_note.pitch, new_note.velocity)
                    print(f"DEBUG: Playing note preview - pitch: {new_note.pitch}, velocity: {new_note.velocity}")
                
                # Select the newly created note
                self.selected_notes = [new_note]
                self.update() # Repaint to show the new note
    
    def _handle_selection_mode_click(self, event, clicked_x, clicked_y):
        """Handle mouse click in selection mode"""
        from PySide6.QtCore import QPointF
        
        clicked_tick = self._x_to_tick(clicked_x)
        clicked_pitch = self._y_to_pitch(clicked_y)
        
        # Check if clicking on an existing note
        clicked_on_note = False
        if self.midi_project:
            for track in self.midi_project.tracks:
                for note in track.notes:
                    note_x = self._tick_to_x(note.start_tick)
                    note_y = self._pitch_to_y(note.pitch)
                    note_width = note.duration * self.pixels_per_tick
                    note_height = self.pixels_per_pitch

                    # Check if click is within note bounds
                    if note_x <= clicked_x < (note_x + note_width) and \
                       note_y <= clicked_y < (note_y + note_height):
                        # Toggle note selection
                        if note in self.selected_notes:
                            self.selected_notes.remove(note)
                        else:
                            self.selected_notes.append(note)
                        clicked_on_note = True
                        break
                if clicked_on_note:
                    break
        
        if not clicked_on_note:
            # Check if clicking on a grid cell
            grid_cell = self.grid_manager.get_grid_cell_at_position(clicked_tick, clicked_pitch)
            
            # Handle grid cell selection
            if event.modifiers() & Qt.ShiftModifier:
                # Shift+click: Set paste target
                self.grid_manager.set_paste_target(grid_cell)
                print(f"DEBUG: Set paste target at tick {grid_cell.start_tick}, pitch {grid_cell.pitch}")
                print(f"DEBUG: Paste target cell: {self.grid_manager.get_paste_target_cell()}")
                
                # Test immediate paste target retrieval
                test_target = self.grid_manager.get_paste_target_cell()
                if test_target:
                    print(f"DEBUG: Immediate paste target test: tick {test_target.start_tick}")
                else:
                    print("DEBUG: ERROR - Paste target is None immediately after setting!")
                    
            elif event.modifiers() & Qt.ControlModifier:
                # Ctrl+click: Toggle grid cell selection
                self.grid_manager.toggle_cell_selection(grid_cell)
                selected_cells = self.grid_manager.get_selected_cells()
                print(f"DEBUG: Toggled grid cell selection at tick {grid_cell.start_tick}, pitch {grid_cell.pitch}")
                print(f"DEBUG: Total selected cells: {len(selected_cells)}")
                for cell in selected_cells:
                    print(f"DEBUG: Selected cell: tick {cell.start_tick}, pitch {cell.pitch}")
                    
                # Test immediate cell selection retrieval
                test_cells = self.grid_manager.get_selected_cells()
                print(f"DEBUG: Immediate cell selection test: {len(test_cells)} cells")
                    
            else:
                # Regular click: Start rectangle selection
                self.edit_mode_manager.start_selection_rectangle(QPointF(clicked_x, clicked_y))
                # Clear selections if not holding Ctrl
                self.selected_notes = []
                self.grid_manager.clear_selection()
                self.grid_manager.clear_paste_target()
                print("DEBUG: Started rectangle selection, cleared all selections")
    
    def _handle_note_input_mode_move(self, event):
        """Handle mouse move in note input mode"""
        if self.dragging_note and event.buttons() == Qt.LeftButton:
            # Calculate delta from start of drag
            delta_x = event.position().x() - self.drag_start_pos.x()
            delta_y = event.position().y() - self.drag_start_pos.y()

            # Convert delta pixels to delta ticks and pitches
            delta_ticks = int(delta_x / self.pixels_per_tick)
            delta_pitch = int(delta_y / self.pixels_per_pitch) # Note: y-axis is inverted for pitch

            # Update note position
            new_start_tick = self.drag_start_note_pos[0] + delta_ticks
            # Quantize new_start_tick for dragging
            new_start_tick = round(new_start_tick / self.quantize_grid_ticks) * self.quantize_grid_ticks

            new_pitch = self.drag_start_note_pos[1] - delta_pitch # Invert delta_pitch for actual pitch

            # Clamp values to valid ranges
            new_start_tick = max(0, new_start_tick)
            new_pitch = max(0, min(127, new_pitch))

            # Store original position for command system
            if not hasattr(self, '_drag_original_start_tick'):
                self._drag_original_start_tick = self.drag_start_note_pos[0]
                self._drag_original_pitch = self.drag_start_note_pos[1]

            # Update note
            self.dragging_note.start_tick = new_start_tick
            self.dragging_note.end_tick = new_start_tick + self.drag_original_duration # Use original duration
            self.dragging_note.pitch = new_pitch

            self.update() # Repaint

        elif self.resizing_left_edge and event.buttons() == Qt.LeftButton:
            # Calculate new start_tick based on current mouse position
            current_tick_at_mouse = self._x_to_tick(event.position().x())

            # Quantize new start_tick
            new_start_tick = round(current_tick_at_mouse / self.quantize_grid_ticks) * self.quantize_grid_ticks

            # Ensure new_start_tick is not negative
            new_start_tick = max(0, new_start_tick)

            # Calculate new duration
            original_end_tick = self.resizing_note.end_tick # Store original end_tick
            new_duration = original_end_tick - new_start_tick

            # Ensure minimum duration
            min_duration_ticks = self.quantize_grid_ticks
            if new_duration < min_duration_ticks:
                new_start_tick = original_end_tick - min_duration_ticks # Adjust start_tick to maintain min duration
                new_duration = min_duration_ticks

            # Store original size for command system
            if not hasattr(self, '_resize_original_start_tick'):
                self._resize_original_start_tick = self.resizing_note.start_tick
                self._resize_original_end_tick = self.resizing_note.end_tick
            
            self.resizing_note.start_tick = new_start_tick
            self.resizing_note.end_tick = new_start_tick + new_duration
            self.update() # Repaint

        elif self.resizing_note and event.buttons() == Qt.LeftButton:
            # Calculate new end_tick based on current mouse position
            current_tick_at_mouse = self._x_to_tick(event.position().x())

            # Quantize new end_tick
            new_end_tick = round(current_tick_at_mouse / self.quantize_grid_ticks) * self.quantize_grid_ticks

            # Ensure minimum duration (e.g., 1 tick)
            min_duration_ticks = self.quantize_grid_ticks # At least one quantized unit
            if new_end_tick <= self.resizing_note.start_tick:
                new_end_tick = self.resizing_note.start_tick + min_duration_ticks

            # Store original size for command system
            if not hasattr(self, '_resize_original_start_tick'):
                self._resize_original_start_tick = self.resizing_note.start_tick
                self._resize_original_end_tick = self.resizing_note.end_tick
            
            self.resizing_note.end_tick = new_end_tick
            self.update() # Repaint
    
    def _handle_selection_mode_move(self, event):
        """Handle mouse move in selection mode"""
        if event.buttons() == Qt.LeftButton:
            selection_rect = self.edit_mode_manager.get_selection_rectangle()
            if selection_rect:
                from PySide6.QtCore import QPointF
                self.edit_mode_manager.update_selection_rectangle(QPointF(event.position().x(), event.position().y()))
                self.update()
    
    def _handle_note_input_mode_release(self, event):
        """Handle mouse release in note input mode"""
        # Create commands for completed operations
        if self.dragging_note and hasattr(self, '_drag_original_start_tick'):
            # Create move command
            command = MoveNoteCommand(
                self.dragging_note,
                self._drag_original_start_tick,
                self._drag_original_pitch,
                self.dragging_note.start_tick,
                self.dragging_note.pitch
            )
            self.command_history.execute_command(command)
            delattr(self, '_drag_original_start_tick')
            delattr(self, '_drag_original_pitch')
        
        if self.resizing_note and hasattr(self, '_resize_original_start_tick'):
            # Create resize command
            command = ResizeNoteCommand(
                self.resizing_note,
                self._resize_original_start_tick,
                self._resize_original_end_tick,
                self.resizing_note.start_tick,
                self.resizing_note.end_tick
            )
            self.command_history.execute_command(command)
            delattr(self, '_resize_original_start_tick')
            delattr(self, '_resize_original_end_tick')
        
        self.dragging_note = None
        self.drag_start_pos = None
        self.drag_start_note_pos = None
        self.resizing_note = None # Clear resizing state
        self.resizing_left_edge = False # Clear left edge resizing state
        self.update() # Repaint to clear any drag artifacts
    
    def _handle_selection_mode_release(self, event):
        """Handle mouse release in selection mode"""
        selection_rect = self.edit_mode_manager.get_selection_rectangle()
        if selection_rect:
            # Get the final selection rectangle
            final_rect = self.edit_mode_manager.finish_selection_rectangle()
            if final_rect and final_rect.width() > 5 and final_rect.height() > 5:  # Minimum size
                # Select notes within the rectangle
                self._select_notes_in_rectangle(final_rect, event.modifiers() & Qt.ControlModifier)
        
        self.edit_mode_manager.clear_selection_rectangle()
        self.update()
    
    def _select_notes_in_rectangle(self, rect, add_to_selection=False):
        """Select notes within the given rectangle"""
        if not self.midi_project:
            return
        
        if not add_to_selection:
            self.selected_notes = []
        
        for track in self.midi_project.tracks:
            for note in track.notes:
                note_x = self._tick_to_x(note.start_tick)
                note_y = self._pitch_to_y(note.pitch)
                note_width = note.duration * self.pixels_per_tick
                note_height = self.pixels_per_pitch
                
                # Check if note overlaps with selection rectangle
                note_rect = QRectF(note_x, note_y, note_width, note_height)
                if rect.intersects(note_rect):
                    if note not in self.selected_notes:
                        self.selected_notes.append(note)
        
        print(f"DEBUG: Selected {len(self.selected_notes)} notes in rectangle")
    
    def get_edit_mode_manager(self):
        """Get the edit mode manager (for external access)"""
        return self.edit_mode_manager

