
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPolygonF
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

        # Scaling factors (pixels per tick, pixels per pitch) - now configurable
        from src.settings import get_settings
        settings = get_settings()
        self.pixels_per_tick = settings.display.grid_width_pixels  # Now stored as pixels per tick
        self.pixels_per_pitch = settings.display.grid_height_pixels
        
        # Piano keyboard settings
        self.piano_width = 80  # Width of piano keyboard on the left
        self.show_piano_keyboard = True
        
        # Playhead settings
        self.playhead_position = 0  # Current playhead position in ticks
        self.is_playing = False
        self.dragging_playhead = False
        self.playhead_drag_start_x = 0
        
        # Vertical scroll settings
        self.vertical_offset = 0  # Vertical scroll offset in pixels

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
        
        # Timer for playback updates
        self.playback_update_timer = QTimer()
        self.playback_update_timer.timeout.connect(self._update_playback_state)
        self.playback_update_timer.start(50)  # Update every 50ms

        # Initialize with default empty project state
        self.set_midi_project(None)
        
        # Force initial update to show playhead
        self.update() 

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
        else:
            self.visible_end_tick = 480 * 32 # Default to 32 beats if no project
        self.update() # Request a repaint

    def update_display_settings(self):
        """Update display settings and refresh"""
        from src.settings import get_settings
        settings = get_settings()
        
        # Update scaling factors
        self.pixels_per_tick = settings.display.grid_width_pixels
        self.pixels_per_pitch = settings.display.grid_height_pixels
        
        # Refresh display
        self.update()
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        
        # Calculate grid area (excluding piano keyboard)
        grid_start_x = self.piano_width if self.show_piano_keyboard else 0
        grid_width = width - grid_start_x

        # Draw piano keyboard first (if enabled)
        if self.show_piano_keyboard:
            self._draw_piano_keyboard(painter, height)

        # Draw grid (simplified for now)
        # Horizontal lines for pitches (every MIDI note)
        for pitch in range(0, 128): # All 128 MIDI pitches
            y = self._pitch_to_y(pitch)
            if pitch % 12 == 0: # C notes (octaves)
                painter.setPen(QColor("#8be9fd")) # Light blue for C notes
            else:
                painter.setPen(QColor("#3e4452")) # Lighter for other notes
            painter.drawLine(grid_start_x, int(y), width, int(y))

        # Vertical lines for beats and measures
        ticks_per_beat = self.midi_project.ticks_per_beat if self.midi_project else 480
        ticks_per_measure = ticks_per_beat * 4  # Assuming 4/4 time signature
        
        # Draw measure lines (1 measure intervals)
        for tick in range(0, self.visible_end_tick + ticks_per_measure, ticks_per_measure):
            if tick >= self.visible_start_tick:
                x = self._tick_to_x(tick) + grid_start_x
                painter.setPen(QColor("#ff79c6"))  # Pink/magenta for measures
                painter.drawLine(int(x), 0, int(x), height)
        
        # Draw beat lines (lighter, every beat)
        for tick in range(0, self.visible_end_tick + ticks_per_beat, ticks_per_beat):
            if tick >= self.visible_start_tick and tick % ticks_per_measure != 0:  # Skip measure lines
                x = self._tick_to_x(tick) + grid_start_x
                painter.setPen(QColor("#3e4452"))  # Lighter for beats
                painter.drawLine(int(x), 0, int(x), height)

        # Draw MIDI notes
        if self.midi_project:
            for track in self.midi_project.tracks:
                for note in track.notes:
                    x = self._tick_to_x(note.start_tick) + grid_start_x
                    y = self._pitch_to_y(note.pitch)
                    note_width = note.duration * self.pixels_per_tick
                    note_height = self.pixels_per_pitch

                    # Only draw if visible
                    if x < width and x + note_width > grid_start_x:
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
        
        # Draw playhead
        self._draw_playhead(painter, height, grid_start_x)
        
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
        return self.height() - ((pitch + 1) * self.pixels_per_pitch) + self.vertical_offset

    def _x_to_tick(self, x: int) -> int:
        grid_start_x = self.piano_width if self.show_piano_keyboard else 0
        adjusted_x = x - grid_start_x
        return int(adjusted_x / self.pixels_per_tick) + self.visible_start_tick

    def _y_to_pitch(self, y: int) -> int:
        # Invert the _pitch_to_y logic with vertical offset
        # y = height - ((pitch + 1) * pixels_per_pitch) + vertical_offset
        # pitch = ((height - y + vertical_offset) / pixels_per_pitch) - 1
        pitch = int(((self.height() - y + self.vertical_offset) / self.pixels_per_pitch) - 1)
        # Clamp pitch to valid MIDI range
        return max(0, min(127, pitch))

    def mousePressEvent(self, event):
        # Ensure this widget has focus for keyboard events
        if not self.hasFocus():
            self.setFocus()
        if event.button() == Qt.LeftButton:
            clicked_x = event.position().x()
            clicked_y = event.position().y()
            
            # Check if click is on piano keyboard
            if self.show_piano_keyboard and clicked_x < self.piano_width:
                # Handle piano key click (play note preview)
                clicked_pitch = self._y_to_pitch(clicked_y)
                
                # Get note name for feedback
                from src.music_theory import get_note_name_with_octave
                note_name = get_note_name_with_octave(clicked_pitch)
                print(f"Piano key clicked: {note_name} (MIDI {clicked_pitch})")
                
                audio_manager = get_audio_manager()
                if audio_manager:
                    audio_manager.play_note_preview(clicked_pitch, 100)
                return
            
            # Check if clicking on playhead (always check regardless of mode)
            grid_start_x = self.piano_width if self.show_piano_keyboard else 0
            playhead_x = self._tick_to_x(self.playhead_position) + grid_start_x
            if abs(clicked_x - playhead_x) <= 5:  # 5 pixel tolerance
                self.dragging_playhead = True
                self.playhead_drag_start_x = clicked_x
                return
            
            clicked_tick = self._x_to_tick(clicked_x)
            clicked_pitch = self._y_to_pitch(clicked_y)

            # Quantize clicked_tick to the nearest grid unit
            clicked_tick = round(clicked_tick / self.quantize_grid_ticks) * self.quantize_grid_ticks

            # Ensure clicked_tick is not negative
            clicked_tick = max(0, clicked_tick)
            # Handle different modes
            if self.edit_mode_manager.is_note_input_mode():
                self._handle_note_input_mode_click(event, clicked_x, clicked_y, clicked_tick, clicked_pitch)
            elif self.edit_mode_manager.is_selection_mode():
                self._handle_selection_mode_click(event, clicked_x, clicked_y)

            self.update() # Request repaint

        elif event.button() == Qt.RightButton:
            clicked_x = event.position().x()
            clicked_y = event.position().y()
            
            # Check if clicking in grid area (not piano keyboard)
            grid_start_x = self.piano_width if self.show_piano_keyboard else 0
            if clicked_x >= grid_start_x:
                # Convert click to tick position
                clicked_tick = self._x_to_tick(clicked_x)
                
                # Move playhead to clicked position and play chord
                self.playhead_position = max(0, clicked_tick)
                
                # Play notes at playhead position (like the original behavior)
                self._play_notes_at_playhead()
                
                self.update()
                return

            # If right-clicking outside grid area, handle normally
            self.update() # Request repaint

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging_playhead:
            # Handle playhead dragging
            clicked_x = event.position().x()
            grid_start_x = self.piano_width if self.show_piano_keyboard else 0
            new_tick = self._x_to_tick(clicked_x)
            self.playhead_position = max(0, new_tick)
            self.update()
        elif self.edit_mode_manager.is_note_input_mode():
            self._handle_note_input_mode_move(event)
        elif self.edit_mode_manager.is_selection_mode():
            self._handle_selection_mode_move(event)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragging_playhead:
            self.dragging_playhead = False
        elif self.edit_mode_manager.is_note_input_mode():
            self._handle_note_input_mode_release(event)
        elif self.edit_mode_manager.is_selection_mode():
            self._handle_selection_mode_release(event)

        super().mouseReleaseEvent(event)

    def _delete_selected_notes_with_command(self):
        """Delete selected notes using command system"""
        if not self.midi_project or not self.selected_notes:
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
    def _delete_selected_notes(self):
        """Legacy method - calls the command version"""
        self._delete_selected_notes_with_command()

    def keyPressEvent(self, event):
        # Delete selected notes
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            self._delete_selected_notes_with_command()
        
        # Copy selected notes
        elif event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
            self._copy_selected_notes()
        
        # Cut selected notes
        elif event.key() == Qt.Key_X and event.modifiers() == Qt.ControlModifier:
            self._cut_selected_notes()
        
        # Paste notes
        elif event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier:
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
        
        # Zoom shortcuts - improved detection for different keyboards
        elif (event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal or 
              event.text() == '+' or event.text() == '='):
            center_x = self.width() / 2
            center_y = self.height() / 2
            if event.modifiers() & Qt.ShiftModifier:
                self._zoom_vertical(1.1, center_y)
            else:
                self._zoom_horizontal(1.1, center_x)
        
        elif (event.key() == Qt.Key_Minus or event.key() == Qt.Key_Underscore or 
              event.text() == '-' or event.text() == '_'):
            center_x = self.width() / 2
            center_y = self.height() / 2
            if event.modifiers() & Qt.ShiftModifier:
                self._zoom_vertical(0.9, center_y)
            else:
                self._zoom_horizontal(0.9, center_x)
        
        # Arrow key scrolling
        elif event.key() == Qt.Key_Left:
            scroll_amount = 100  # Scroll by 100 ticks
            self.visible_start_tick = max(0, self.visible_start_tick - scroll_amount)
            self.update()
        
        elif event.key() == Qt.Key_Right:
            scroll_amount = 100  # Scroll by 100 ticks
            self.visible_start_tick += scroll_amount
            self.update()
        
        elif event.key() == Qt.Key_Up:
            # Vertical scroll up (show higher pitches)
            self.vertical_offset += 50
            max_offset = 127 * self.pixels_per_pitch - self.height()
            self.vertical_offset = min(max_offset, self.vertical_offset)
            self.update()
        
        elif event.key() == Qt.Key_Down:
            # Vertical scroll down (show lower pitches)
            self.vertical_offset -= 50
            min_offset = -20 * self.pixels_per_pitch
            self.vertical_offset = max(min_offset, self.vertical_offset)
            self.update()
        
        # Enter/Return: Toggle playback
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self._toggle_playback()
        
        # Space key: Move playhead to beginning
        elif event.key() == Qt.Key_Space:
            self.playhead_position = 0
            self.update()
        
        # Comma: Move playhead to previous measure
        elif event.key() == Qt.Key_Comma:
            self._move_playhead_to_measure(-1)
        
        # Period: Move playhead to next measure  
        elif event.key() == Qt.Key_Period:
            self._move_playhead_to_measure(1)

        super().keyPressEvent(event)
    
    def _toggle_playback(self):
        """Toggle playback state"""
        print("PianoRoll: _toggle_playback called")
        
        # Try multiple methods to find the playback system
        main_window = self.parent()
        attempts = 0
        while main_window and attempts < 10:  # Prevent infinite loop
            attempts += 1
            print(f"PianoRoll: Checking parent {attempts}: {type(main_window).__name__}")
            
            # Check for different possible method names
            if hasattr(main_window, 'toggle_playback'):
                print("PianoRoll: Found toggle_playback method")
                main_window.toggle_playback()
                return
            elif hasattr(main_window, '_toggle_playback'):
                print("PianoRoll: Found _toggle_playback method")
                main_window._toggle_playback()
                return
            elif hasattr(main_window, 'play_pause_action'):
                print("PianoRoll: Found play_pause_action")
                main_window.play_pause_action.trigger()
                return
            elif hasattr(main_window, 'playback_controls'):
                if hasattr(main_window.playback_controls, 'toggle_playback'):
                    print("PianoRoll: Found playback_controls.toggle_playback")
                    main_window.playback_controls.toggle_playback()
                    return
            main_window = main_window.parent()
        
        # Direct engine access fallback
        print("PianoRoll: Trying direct engine access")
        from src.playback_engine import get_playback_engine
        engine = get_playback_engine()
        if engine:
            print(f"PianoRoll: Found engine, current state: {engine.get_state()}")
            engine.toggle_play_pause()
            print(f"PianoRoll: After toggle, state: {engine.get_state()}")
            return
        
        # Final fallback: toggle local state
        self.is_playing = not self.is_playing
        self.update()
        print(f"Playback toggle requested (local state only: {'Playing' if self.is_playing else 'Stopped'})")
    
    def _move_playhead_to_measure(self, direction: int):
        """Move playhead to nearest measure line (direction: -1 for previous, 1 for next)"""
        ticks_per_beat = self.midi_project.ticks_per_beat if self.midi_project else 480
        ticks_per_measure = ticks_per_beat * 4  # 4/4 time signature
        
        if direction < 0:
            # Move to previous measure
            target_measure = (self.playhead_position // ticks_per_measure)
            if self.playhead_position % ticks_per_measure == 0 and self.playhead_position > 0:
                target_measure -= 1  # If exactly on measure, go to previous
            self.playhead_position = max(0, target_measure * ticks_per_measure)
        else:
            # Move to next measure
            target_measure = (self.playhead_position // ticks_per_measure) + 1
            self.playhead_position = target_measure * ticks_per_measure
        
        # Just move playhead, no sound
        
        self.update()
    
    def wheelEvent(self, event):
        """Handle mouse wheel and trackpad events for zooming and scrolling"""
        # Use angleDelta for both mouse wheel and trackpad - more reliable
        delta = event.angleDelta()
        
        if delta.isNull():
            return
        
        # Get scroll amount
        scroll_y = delta.y()
        scroll_x = delta.x()
        
        # Check modifiers for zoom
        if event.modifiers() & Qt.ControlModifier:
            # Ctrl+Wheel: Horizontal zoom
            zoom_factor = 1.1 if scroll_y > 0 else 0.9
            center_x = self.width() / 2
            self._zoom_horizontal(zoom_factor, center_x)
        elif event.modifiers() & Qt.ShiftModifier:
            # Shift+Wheel: Vertical scrolling
            if scroll_y != 0:
                scroll_amount = scroll_y / 120 * 30  # Convert to reasonable scroll amount
                self.vertical_offset += scroll_amount
                # Limit vertical scroll range
                max_offset = 127 * self.pixels_per_pitch - self.height()
                min_offset = -20 * self.pixels_per_pitch  # Show some notes below MIDI 0
                self.vertical_offset = max(min_offset, min(max_offset, self.vertical_offset))
                self.update()
        elif event.modifiers() & Qt.AltModifier:
            # Alt+Wheel: Vertical zoom
            zoom_factor = 1.1 if scroll_y > 0 else 0.9
            center_y = self.height() / 2
            self._zoom_vertical(zoom_factor, center_y)
        else:
            # Normal scroll: Horizontal timeline movement
            if scroll_y != 0:
                scroll_amount = scroll_y / 120 * 50  # Convert to reasonable scroll amount
                self.visible_start_tick = max(0, int(self.visible_start_tick - scroll_amount))
                self.update()
            elif scroll_x != 0:
                scroll_amount = scroll_x / 120 * 50
                self.visible_start_tick = max(0, int(self.visible_start_tick + scroll_amount))
                self.update()
        
        event.accept()
    
    def _copy_selected_notes(self):
        """Copy selected notes to clipboard"""
        if self.selected_notes:
            # Calculate reference tick and pitch (earliest note's start tick and lowest pitch)
            reference_tick = min(note.start_tick for note in self.selected_notes)
            reference_pitch = min(note.pitch for note in self.selected_notes)
            global_clipboard.copy_notes(self.selected_notes, reference_tick, reference_pitch)
    def _cut_selected_notes(self):
        """Cut selected notes to clipboard"""
        if not self.selected_notes:
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
    def _paste_notes(self):
        """Paste notes from clipboard"""
        if not global_clipboard.has_data():
            return
        
        if not self.midi_project or not self.midi_project.tracks:
            return
        
        # Debug: Show current state
        paste_target = self.grid_manager.get_paste_target_cell()
        selected_cells = self.grid_manager.get_selected_cells()

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
        # Quantize target tick
        target_tick = round(target_tick / self.quantize_grid_ticks) * self.quantize_grid_ticks
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
        else:
            pass
            
    def _undo(self):
        """Undo last operation"""
        if self.command_history.undo():
            self.selected_notes = [] # Clear selection after undo
            self.update()
        else:
            pass
            
    def _redo(self):
        """Redo last undone operation"""
        if self.command_history.redo():
            self.selected_notes = [] # Clear selection after redo
            self.update()
        else:
            pass
            
    def _select_all(self):
        """Select all notes in the project"""
        if not self.midi_project:
            return
        
        all_notes = []
        for track in self.midi_project.tracks:
            all_notes.extend(track.notes)
        
        self.selected_notes = all_notes
        self.update()
    def _on_mode_changed(self, mode: EditMode):
        """Handle mode change"""

        paste_target_before = self.grid_manager.get_paste_target_cell()
        self.edit_mode_manager.clear_selection_rectangle()
        # Don't clear grid selection when changing modes
        paste_target_after = self.grid_manager.get_paste_target_cell()
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
                    grid_start_x = self.piano_width if self.show_piano_keyboard else 0
                    note_x = self._tick_to_x(note.start_tick) + grid_start_x
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
                    grid_start_x = self.piano_width if self.show_piano_keyboard else 0
                    note_x = self._tick_to_x(note.start_tick) + grid_start_x
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

                # Test immediate paste target retrieval
                test_target = self.grid_manager.get_paste_target_cell()
                if test_target:
                    pass
                else:
                    pass
            elif event.modifiers() & Qt.ControlModifier:
                # Ctrl+click: Toggle grid cell selection
                self.grid_manager.toggle_cell_selection(grid_cell)
                selected_cells = self.grid_manager.get_selected_cells()

                for cell in selected_cells:
                    pass
                # Test immediate cell selection retrieval
                test_cells = self.grid_manager.get_selected_cells()
            else:
                # Regular click: Start rectangle selection
                self.edit_mode_manager.start_selection_rectangle(QPointF(clicked_x, clicked_y))
                # Clear selections if not holding Ctrl
                self.selected_notes = []
                self.grid_manager.clear_selection()
                self.grid_manager.clear_paste_target()
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
                grid_start_x = self.piano_width if self.show_piano_keyboard else 0
                note_x = self._tick_to_x(note.start_tick) + grid_start_x
                note_y = self._pitch_to_y(note.pitch)
                note_width = note.duration * self.pixels_per_tick
                note_height = self.pixels_per_pitch
                
                # Check if note overlaps with selection rectangle
                note_rect = QRectF(note_x, note_y, note_width, note_height)
                if rect.intersects(note_rect):
                    if note not in self.selected_notes:
                        self.selected_notes.append(note)
    def get_edit_mode_manager(self):
        """Get the edit mode manager (for external access)"""
        return self.edit_mode_manager
    
    def _draw_piano_keyboard(self, painter: QPainter, height: int):
        """Draw piano keyboard on the left side"""
        # Note names and black key pattern
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        black_keys = [1, 3, 6, 8, 10]  # C#, D#, F#, G#, A#
        
        painter.save()
        
        # Background for piano area
        painter.fillRect(0, 0, self.piano_width, height, QColor("#1e1e1e"))
        
        # Draw white keys first
        for pitch in range(0, 128):
            note_index = pitch % 12
            if note_index not in black_keys:  # White key
                y = self._pitch_to_y(pitch)
                key_height = self.pixels_per_pitch
                
                # White key color - always white
                key_color = QColor("#f8f8f2")
                
                painter.fillRect(0, int(y), self.piano_width - 1, int(key_height), key_color)
                
                # Key border
                painter.setPen(QColor("#44475a"))
                painter.drawRect(0, int(y), self.piano_width - 1, int(key_height))
                
                # Note label for C notes
                if note_index == 0:  # C note
                    octave = (pitch // 12) - 1
                    font = QFont()
                    font.setPointSize(8)
                    painter.setFont(font)
                    painter.setPen(QColor("#282a36"))
                    painter.drawText(5, int(y + key_height - 3), f"C{octave}")
        
        # Draw black keys on top
        for pitch in range(0, 128):
            note_index = pitch % 12
            if note_index in black_keys:  # Black key
                y = self._pitch_to_y(pitch)
                key_height = self.pixels_per_pitch
                black_key_width = int(self.piano_width * 0.5)  # Make black keys shorter
                
                # Black key color - always black
                key_color = QColor("#282a36")
                
                painter.fillRect(0, int(y), black_key_width, int(key_height), key_color)
                
                # Key border
                painter.setPen(QColor("#6272a4"))
                painter.drawRect(0, int(y), black_key_width, int(key_height))
        
        # Separator line between piano and grid
        painter.setPen(QColor("#6272a4"))
        painter.drawLine(self.piano_width - 1, 0, self.piano_width - 1, height)
        
        painter.restore()
    
    def _draw_playhead(self, painter: QPainter, height: int, grid_start_x: int):
        """Draw the playhead line"""
        painter.save()
        
        # Calculate playhead x position
        playhead_x = self._tick_to_x(self.playhead_position) + grid_start_x
        
        # Only skip drawing if playhead is way off screen
        if playhead_x < -100 or playhead_x > self.width() + 100:
            painter.restore()
            return
        
        # Draw simple playhead line
        if self.is_playing:
            painter.setPen(QPen(QColor("#50fa7b"), 3))  # Green when playing
        else:
            painter.setPen(QPen(QColor("#bd93f9"), 3))  # Purple when stopped
        
        painter.drawLine(int(playhead_x), 0, int(playhead_x), height)
        
        painter.restore()
    
    def _play_selected_notes_as_chord(self):
        """Play selected notes as a chord"""
        if not self.selected_notes:
            return
        
        audio_manager = get_audio_manager()
        if not audio_manager:
            return
        
        # Get pitches from selected notes
        pitches = [note.pitch for note in self.selected_notes]
        
        # Play all notes simultaneously
        for pitch in pitches:
            audio_manager.play_note_preview(pitch, 100)
        
        # Analyze and display chord information
        from src.music_theory import detect_chord, get_note_name_with_octave
        
        chord = detect_chord(pitches)
        if chord:
            # Get chord notes and format with構成音
            chord_notes = [note.name for note in chord.notes[:6]]  # First 6 notes
            if len(chord.notes) > 6:
                chord_notes.append("...")
            chord_info = f"{chord.name} ({', '.join(chord_notes)})"
            print(f"Selected Chord: {chord_info}")
            self._display_chord_info(chord_info)
        else:
            note_names = [get_note_name_with_octave(pitch) for pitch in sorted(pitches)]
            notes_info = f"{', '.join(note_names)}"
            print(f"Selected Notes: {notes_info}")
            self._display_chord_info(notes_info)
    
    def _play_notes_at_playhead(self):
        """Play all notes at the current playhead position as a chord"""
        if not self.midi_project:
            return
            
        # Find all notes that are playing at the playhead position
        notes_at_playhead = []
        for track in self.midi_project.tracks:
            for note in track.notes:
                if note.start_tick <= self.playhead_position < note.end_tick:
                    notes_at_playhead.append(note)
        
        if not notes_at_playhead:
            print(f"No notes playing at position {self.playhead_position}")
            return
        
        # Play the notes as a chord
        audio_manager = get_audio_manager()
        if audio_manager:
            pitches = [note.pitch for note in notes_at_playhead]
            for pitch in pitches:
                audio_manager.play_note_preview(pitch, 100)
            
            # Analyze and display chord information
            from src.music_theory import detect_chord, get_note_name_with_octave
            
            chord = detect_chord(pitches)
            if chord:
                # Get chord notes and format
                chord_notes = [note.name for note in chord.notes[:6]]  # First 6 notes
                if len(chord.notes) > 6:
                    chord_notes.append("...")
                chord_info = f"{chord.name} ({', '.join(chord_notes)})"
                print(f"Chord at playhead: {chord_info}")
                self._display_chord_info(chord_info)
            else:
                note_names = [get_note_name_with_octave(pitch) for pitch in sorted(pitches)]
                notes_info = f"{', '.join(note_names)}"
                print(f"Notes at playhead: {notes_info}")
                self._display_chord_info(notes_info)
    
    def _display_chord_info(self, info: str):
        """Display chord information in the top bar (placeholder)"""
        # This should communicate with the main window to update the top bar
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'update_chord_display'):
            main_window = main_window.parent()
        
        if main_window and hasattr(main_window, 'update_chord_display'):
            main_window.update_chord_display(info)
        else:
            # Fallback: just print for now
            print(f"Chord Info: {info}")
    
    def set_playhead_position(self, position: int):
        """Set playhead position from external source (like playback engine)"""
        self.playhead_position = position
        self.update()
    
    def set_playing_state(self, is_playing: bool):
        """Set playing state from external source"""
        self.is_playing = is_playing
        self.update()
    
    def _update_playback_state(self):
        """Update playback state from playback engine"""
        from src.playback_engine import get_playback_engine
        
        engine = get_playback_engine()
        if engine:
            old_position = self.playhead_position
            old_playing = self.is_playing
            
            self.playhead_position = engine.get_current_tick()
            self.is_playing = engine.is_playing()
            
            # Only update if something changed
            if old_position != self.playhead_position or old_playing != self.is_playing:
                self.update()
    
    def _zoom_horizontal(self, zoom_factor: float, center_x: float):
        """Zoom horizontally around the specified center point"""
        try:
            from src.settings import get_settings
            settings = get_settings()
            
            # Calculate new zoom level
            new_pixels_per_tick = self.pixels_per_tick * zoom_factor
            
            # Apply bounds based on optimal range (0.08 to 0.25 pixels per tick)
            min_pixels_per_tick = 0.08
            max_pixels_per_tick = 0.25
            new_pixels_per_tick = max(min_pixels_per_tick, min(max_pixels_per_tick, new_pixels_per_tick))
            
            # Only update if the value actually changed
            if abs(new_pixels_per_tick - self.pixels_per_tick) > 0.001:
                # Update zoom
                self.pixels_per_tick = new_pixels_per_tick
                settings.display.grid_width_pixels = new_pixels_per_tick
                
                # Safe update
                if self.isVisible():
                    self.update()
        except Exception as e:
            pass  # Silent fail for stability
    
    def _zoom_vertical(self, zoom_factor: float, center_y: float):
        """Zoom vertically around the specified center point"""
        try:
            from src.settings import get_settings
            settings = get_settings()
            
            # Calculate new zoom level
            new_pixels_per_pitch = self.pixels_per_pitch * zoom_factor
            
            # Apply bounds based on optimal range (8 to 25 pixels per semitone)
            min_pixels_per_pitch = 8.0
            max_pixels_per_pitch = 25.0
            new_pixels_per_pitch = max(min_pixels_per_pitch, min(max_pixels_per_pitch, new_pixels_per_pitch))
            
            # Only update if the value actually changed
            if abs(new_pixels_per_pitch - self.pixels_per_pitch) > 0.1:
                # Update zoom
                self.pixels_per_pitch = new_pixels_per_pitch
                settings.display.grid_height_pixels = new_pixels_per_pitch
                
                # Safe update
                if self.isVisible():
                    self.update()
        except Exception as e:
            pass  # Silent fail for stability

