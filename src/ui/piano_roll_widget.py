
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPolygonF
from typing import List, Dict

from src.midi_data_model import MidiProject, MidiNote
from src.playback_engine import PlaybackState
from src.command_system import (
    CommandHistory, AddNoteCommand, DeleteNoteCommand, MoveNoteCommand,
    ResizeNoteCommand, DeleteMultipleNotesCommand, PasteNotesCommand, CutNotesCommand,
    MoveMultipleNotesCommand, ResizeMultipleNotesCommand
)
from src.clipboard_system import global_clipboard
from src.edit_modes import EditMode, EditModeManager
from src.grid_system import GridManager, GridCell
from src.audio_system import get_audio_manager
from src.track_manager import get_track_manager
from src.audio_source_manager import AudioSourceType
from src.logger import get_logger, print_debug
import copy

class PianoRollWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.setMinimumSize(600, 400)
        self.midi_project: MidiProject = None

        # Scaling factors (pixels per tick, pixels per pitch) - now configurable
        from src.settings import get_settings_manager
        self.settings_manager = get_settings_manager()
        settings = self.settings_manager.settings
        self.pixels_per_tick = settings.display.grid_width_pixels  # Now stored as pixels per tick
        self.pixels_per_pitch = settings.display.grid_height_pixels
        
        # Apply theme
        self._apply_theme()
        
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
        
        # Multi-note operation state
        self.dragging_multiple_notes: bool = False
        self.resizing_multiple_notes: bool = False
        self.multi_drag_start_positions: Dict[MidiNote, tuple] = {}  # note -> (start_tick, pitch)
        self.multi_resize_start_data: Dict[MidiNote, tuple] = {}     # note -> (start_tick, end_tick)

        # Quantization unit (e.g., 16th note by default)
        self.quantize_grid_ticks = 480 // 4 # Default to 16th note (480 ticks/beat / 4 = 120 ticks)
        
        # Grid subdivision settings
        self.grid_subdivision_type = "sixteenth"  # Default subdivision
        self.ticks_per_subdivision = 120  # Default to 16th note subdivisions
        
        # Command history for undo/redo
        self.command_history = CommandHistory()
        
        # Edit mode manager
        self.edit_mode_manager = EditModeManager()
        self.edit_mode_manager.mode_changed.connect(self._on_mode_changed)
        
        # Grid system
        self.grid_manager = GridManager()
        
        # Preview note tracking
        self.active_preview_notes = set()  # Track currently playing preview notes
        
        # Parameter automation editing
        self.parameter_edit_mode = "none"  # "none", "velocity", "volume", "expression"
        self.parameter_colors = {
            "velocity": "#FF6B6B",     # Red
            "volume": "#4ECDC4",       # Teal 
            "expression": "#45B7D1"    # Blue
        }
        
        # Parameter editing state
        self.parameter_editing = False
        self.dragging_automation_point = None  # (note, point_index) or None
        self.parameter_drag_start_pos = None
        
        # Theme colors - will be set by _apply_theme()
        self.theme_colors = None
        self.parameter_drag_start_value = None
        self.last_parameter_edit_pos = None  # For trackpad swiping
        
        # Update grid settings to match piano roll
        if self.midi_project:
            self.grid_manager.update_grid_settings(self.midi_project.ticks_per_beat, 4)
        else:
            self.grid_manager.update_grid_settings(480, 4)
        
        # Enable focus to receive keyboard events
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Parameter selection UI will be handled by the main window toolbar
        
        # Initialize with default empty project state
        self.set_midi_project(None)
        
        # Playback engine connection (will be connected after main window initializes it)
        self.playback_engine = None
        
        # Force initial update to show playhead
        self.update()
    
    def _apply_theme(self):
        """Apply current theme colors"""
        if not self.settings_manager:
            return
        
        self.theme_colors = self.settings_manager.get_theme_colors()
        
        # Update background color
        self.setStyleSheet(f"background-color: {self.theme_colors.background};")
        
        # Update parameter colors based on theme
        self.parameter_colors = {
            "velocity": self.theme_colors.param_velocity,
            "volume": self.theme_colors.param_volume,
            "expression": self.theme_colors.param_expression
        }
        
        # Force repaint to apply new colors
        self.update()
    
    def set_theme(self, theme_name: str):
        """Set theme and update display"""
        from src.settings import Theme
        if theme_name == "light":
            self.settings_manager.set_theme(Theme.LIGHT)
        else:
            self.settings_manager.set_theme(Theme.DARK)
        
        self._apply_theme()
    
    def set_parameter_edit_mode(self, mode: str):
        """Set parameter editing mode from external source (e.g., main window toolbar)"""
        valid_modes = ["none", "velocity", "volume", "expression"]
        if mode in valid_modes:
            self.parameter_edit_mode = mode
            self.logger.debug(f"Parameter edit mode changed to: {self.parameter_edit_mode}")
            
            # Force repaint to show/hide parameter layer
            self.update()
        else:
            self.logger.warning(f"Invalid parameter mode: {mode}")
    
    def get_parameter_edit_mode(self) -> str:
        """Get current parameter editing mode"""
        return self.parameter_edit_mode

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
            
            # Add generous padding for composition (8 measures)
            padding_ticks = self.midi_project.ticks_per_beat * 32  # 8 measures in 4/4
            self.visible_end_tick = max_tick + padding_ticks
            
            # Ensure a substantial minimum length for composition (64 measures)
            min_visible_ticks = self.midi_project.ticks_per_beat * 256  # 64 measures in 4/4
            if self.visible_end_tick < min_visible_ticks:
                self.visible_end_tick = min_visible_ticks
        else:
            # Default to 64 measures for empty project
            self.visible_end_tick = 480 * 256  # 64 measures at standard resolution
        self.update() # Request a repaint
        
        # Update main window scrollbar if available
        self._update_scrollbar_range()

    def _update_scrollbar_range(self):
        """Update the main window's horizontal scrollbar range"""
        if hasattr(self, 'h_scrollbar') and self.h_scrollbar:
            self.h_scrollbar.setMaximum(self.visible_end_tick)

    def extend_range_if_needed(self, tick: int):
        """Extend the visible range if the given tick is near the end"""
        # If the tick is within 4 measures of the end, extend by 8 measures
        ticks_per_beat = self.midi_project.ticks_per_beat if self.midi_project else 480
        buffer_zone = ticks_per_beat * 16  # 4 measures buffer
        extension_size = ticks_per_beat * 32  # 8 measures extension
        
        if tick >= self.visible_end_tick - buffer_zone:
            old_end = self.visible_end_tick
            self.visible_end_tick = tick + extension_size
            print(f"Extended horizontal range from {old_end} to {self.visible_end_tick} ticks")
            self._update_scrollbar_range()
            
            # Force measure bar resync after range extension
            self._sync_measure_bar()
            
            self.update()
    
    def _sync_measure_bar(self):
        """Synchronize measure bar with current piano roll state"""
        # Get parent main window to update measure bar
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'measure_bar'):
            main_window = main_window.parent()
            
        if main_window and hasattr(main_window, 'measure_bar'):
            # Calculate current visible end tick
            grid_start_x = self.piano_width if self.show_piano_keyboard else 0
            visible_width = self.width() - grid_start_x
            current_visible_end_tick = self.visible_start_tick + int(visible_width / self.pixels_per_tick)
            
            # Update measure bar
            main_window.measure_bar.sync_with_piano_roll(
                self.visible_start_tick,
                current_visible_end_tick,
                self.pixels_per_tick
            )

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
        
        # Ensure theme colors are loaded
        if not self.theme_colors:
            self._apply_theme()
        
        # Fallback to default colors if theme colors still not available
        if not self.theme_colors:
            from src.settings import DARK_THEME
            self.theme_colors = DARK_THEME
        
        # Calculate grid area (excluding piano keyboard)
        grid_start_x = self.piano_width if self.show_piano_keyboard else 0
        grid_width = width - grid_start_x

        # Draw piano keyboard first (if enabled)
        if self.show_piano_keyboard:
            self._draw_piano_keyboard(painter, height)

        # Draw grid with alternating horizontal backgrounds and lines
        # First, draw alternating background colors for better pitch visibility
        for pitch in range(0, 120): # C-1 (0) to B9 (119)
            y = self._pitch_to_y(pitch)
            note_height = self.pixels_per_pitch
            
            # Check if it's a black key or white key
            note_in_octave = pitch % 12
            is_black_key = note_in_octave in [1, 3, 6, 8, 10]  # C#, D#, F#, G#, A#
            
            # Draw background rectangle for this pitch
            if is_black_key:
                # Darker background for black key pitches
                painter.setBrush(QColor(self.theme_colors.black_key_background))
            else:
                # Lighter background for white key pitches
                painter.setBrush(QColor(self.theme_colors.white_key_background))
            
            painter.setPen(Qt.NoPen)
            painter.drawRect(grid_start_x, int(y), grid_width, int(note_height))
        
        # Then draw horizontal lines for pitches
        for pitch in range(0, 120): # C-1 (0) to B9 (119)
            y = self._pitch_to_y(pitch)
            if pitch % 12 == 0: # C notes (octaves)
                # Draw C line at the bottom of the note (not top)
                painter.setPen(QColor(self.theme_colors.grid_line_c_note))
                painter.drawLine(grid_start_x, int(y + self.pixels_per_pitch), width, int(y + self.pixels_per_pitch))
            else:
                painter.setPen(QColor(self.theme_colors.grid_line_normal))
                painter.drawLine(grid_start_x, int(y), width, int(y))

        # Vertical lines for beats and measures
        ticks_per_beat = self.midi_project.ticks_per_beat if self.midi_project else 480
        
        # Get time signature for measure calculations
        if self.midi_project and self.midi_project.time_signature_changes:
            numerator, denominator = self.midi_project.get_time_signature_at_tick(self.visible_start_tick)
        else:
            numerator, denominator = 4, 4
        
        # Calculate ticks per measure and end tick
        if self.midi_project:
            ticks_per_measure = self.midi_project.calculate_ticks_per_measure(numerator, denominator)
        else:
            # Fallback calculation
            if denominator == 8:
                beats_per_measure = numerator / 2
                ticks_per_measure = int(ticks_per_beat * beats_per_measure)
            else:
                beats_per_measure = numerator * (4 / denominator)
                ticks_per_measure = int(ticks_per_beat * beats_per_measure)
        
        # Calculate visible end tick
        grid_width = self.width() - grid_start_x
        current_visible_end_tick = self.visible_start_tick + int(grid_width / self.pixels_per_tick)
        end_tick = current_visible_end_tick + ticks_per_measure
        
        # Draw measure lines with time signature changes support
        if self.midi_project and self.midi_project.time_signature_changes:
            self._draw_measure_lines_with_time_signature_changes(painter, ticks_per_beat, grid_start_x, height, current_visible_end_tick)
        else:
            self._draw_measure_lines_simple(painter, ticks_per_beat, numerator, denominator, grid_start_x, height, current_visible_end_tick)
        
        # Draw beat lines (lighter, subdivision within measures)
        if denominator == 8:
            # For compound time, draw every eighth note
            ticks_per_subdivision = ticks_per_beat // 2  # Eighth note
        else:
            # For simple time, draw every quarter note beat
            ticks_per_subdivision = ticks_per_beat
        
        # Use the same range calculation as measure lines
        start_beat_tick = (self.visible_start_tick // ticks_per_subdivision) * ticks_per_subdivision
        
        for tick in range(start_beat_tick, end_tick, ticks_per_subdivision):
            if tick >= self.visible_start_tick - ticks_per_subdivision and tick % ticks_per_measure != 0:  # Skip measure lines
                x = self._tick_to_x(tick) + grid_start_x
                if x >= grid_start_x and x <= self.width():  # Only draw if visible
                    painter.setPen(QColor(self.theme_colors.grid_line_beat))
                    painter.drawLine(int(x), 0, int(x), height)

        # Draw subdivision lines (finest grid lines within beats)
        if hasattr(self, 'ticks_per_subdivision') and self.ticks_per_subdivision < ticks_per_beat:
            # Set up custom dashed pen for subdivision lines
            subdivision_pen = QPen(QColor(self.theme_colors.grid_line_subdivision))
            subdivision_pen.setStyle(Qt.CustomDashLine)  # Use custom dash pattern
            subdivision_pen.setDashPattern([4, 8])  # Pattern: 4 pixels on, 8 pixels off (coarser)
            subdivision_pen.setWidth(1)
            
            # Use the same range calculation as other grid lines
            start_subdivision_tick = (self.visible_start_tick // self.ticks_per_subdivision) * self.ticks_per_subdivision
            
            for tick in range(start_subdivision_tick, end_tick, self.ticks_per_subdivision):
                if tick >= self.visible_start_tick - self.ticks_per_subdivision:
                    # Skip if this tick coincides with measure or beat lines
                    if tick % ticks_per_measure == 0 or tick % ticks_per_beat == 0:
                        continue
                    
                    x = self._tick_to_x(tick) + grid_start_x
                    if x >= grid_start_x and x <= self.width():  # Only draw if visible
                        painter.setPen(subdivision_pen)  # Dashed pen for subdivisions
                        painter.drawLine(int(x), 0, int(x), height)

        # Draw MIDI notes
        if self.midi_project:
            track_manager = get_track_manager()
            
            for track_index, track in enumerate(self.midi_project.tracks):
                # Get track color from TrackManager
                track_color = "#61afef"  # Default blue color
                if track_manager:
                    track_color = track_manager.get_track_color(track_index)
                
                for note in track.notes:
                    x = self._tick_to_x(note.start_tick) + grid_start_x
                    y = self._pitch_to_y(note.pitch)
                    note_width = note.duration * self.pixels_per_tick
                    note_height = self.pixels_per_pitch

                    # Only draw if visible
                    if x < width and x + note_width > grid_start_x:
                        # Draw note rectangle with track color
                        if note in self.selected_notes:
                            # For selected notes, use theme selected color
                            painter.setBrush(QColor(self.theme_colors.note_selected))
                        else:
                            # Use track color or theme default for unselected notes
                            if track_color:
                                painter.setBrush(QColor(track_color))
                            else:
                                painter.setBrush(QColor(self.theme_colors.note_default))
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
        
        # Draw parameter automation layer (if enabled)
        if self.parameter_edit_mode != "none":
            self._draw_parameter_layer(painter, width, height, grid_start_x)
        
        # Draw mode indicator
        self._draw_mode_indicator(painter, width, height)

        painter.end()

    def _tick_to_x(self, tick: int) -> float:
        x_coord = (tick - self.visible_start_tick) * self.pixels_per_tick
        return x_coord

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
        tick = int(adjusted_x / self.pixels_per_tick) + self.visible_start_tick
        return tick

    def _y_to_pitch(self, y: int) -> int:
        # Invert the _pitch_to_y logic with vertical offset
        # y = height - ((pitch + 1) * pixels_per_pitch) + vertical_offset
        # pitch = ((height - y + vertical_offset) / pixels_per_pitch) - 1
        pitch = int((self.height() - y + self.vertical_offset) / self.pixels_per_pitch)
        # Clamp pitch to extended range (C-1 to B9)
        return max(0, min(119, pitch))

    def mousePressEvent(self, event):
        # Ensure this widget has focus for keyboard events
        if not self.hasFocus():
            self.setFocus()
        if event.button() == Qt.LeftButton:
            clicked_x = event.position().x()
            clicked_y = event.position().y()
            
            # Handle parameter editing mode first
            if self.parameter_edit_mode != "none":
                grid_start_x = self.piano_width if self.show_piano_keyboard else 0
                if clicked_x >= grid_start_x:  # Click is in grid area
                    handled = self._handle_parameter_editing_click(event, clicked_x, clicked_y, grid_start_x)
                    if handled:
                        return
            
            # Check if click is on piano keyboard
            if self.show_piano_keyboard and clicked_x < self.piano_width:
                # Handle piano key click (play note preview)
                clicked_pitch = self._y_to_pitch(clicked_y)
                
                # Get note name for feedback
                from src.music_theory import get_note_name_with_octave
                note_name = get_note_name_with_octave(clicked_pitch)
                print(f"Piano key clicked: {note_name} (MIDI {clicked_pitch})")
                
                # Use per-track audio routing for preview
                self._play_track_preview(clicked_pitch, 100)
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
            # Handle different modes (but not during parameter editing)
            if self.parameter_edit_mode != "none":
                # Parameter editing mode - disable other edit modes for better UX
                pass
            elif self.edit_mode_manager.is_note_input_mode():
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
                # Handle parameter editing mode first
                if self.parameter_edit_mode != "none":
                    handled = self._handle_parameter_right_click(clicked_x, clicked_y, grid_start_x)
                    if handled:
                        return
                
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
        if self.parameter_editing and self.dragging_automation_point:
            # Handle parameter automation point dragging
            self._handle_parameter_drag(event)
        elif self.parameter_edit_mode != "none":
            # Handle trackpad swiping for parameter editing
            self._handle_parameter_swipe(event)
        elif self.dragging_playhead:
            # Handle playhead dragging
            clicked_x = event.position().x()
            grid_start_x = self.piano_width if self.show_piano_keyboard else 0
            new_tick = self._x_to_tick(clicked_x)
            self.playhead_position = max(0, new_tick)
            self.update()
        elif self.parameter_edit_mode == "none" and self.edit_mode_manager.is_note_input_mode():
            self._handle_note_input_mode_move(event)
        elif self.parameter_edit_mode == "none" and self.edit_mode_manager.is_selection_mode():
            self._handle_selection_mode_move(event)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.parameter_editing:
            # Handle parameter editing release
            self._handle_parameter_release(event)
        elif self.dragging_playhead:
            self.dragging_playhead = False
            
            # Sync playhead position with playback engine
            if self.playback_engine:
                self.playback_engine.seek_to_tick(self.playhead_position)
            
            # Play notes at the new playhead position
            self._play_notes_at_playhead()
        elif self.parameter_edit_mode == "none" and self.edit_mode_manager.is_note_input_mode():
            self._handle_note_input_mode_release(event)
        elif self.parameter_edit_mode == "none" and self.edit_mode_manager.is_selection_mode():
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
            
            # Update playback engine after deletion
            self._update_playback_engine()
            
            self.selected_notes = [] # Clear selection
            self.update() # Repaint
    def _delete_selected_notes(self):
        """Legacy method - calls the command version"""
        self._delete_selected_notes_with_command()

    def keyPressEvent(self, event):
        # In parameter editing mode, disable most keyboard shortcuts except mode switching
        if self.parameter_edit_mode != "none":
            # Allow Tab key for mode switching even in parameter editing mode
            if event.key() == Qt.Key_Tab:
                self.edit_mode_manager.toggle_mode()
                self.update()
            # Allow Escape to exit parameter editing mode  
            elif event.key() == Qt.Key_Escape:
                self.set_parameter_edit_mode("none")
                # Notify main window to update toolbar combo box
                main_window = self.parent()
                while main_window and not hasattr(main_window, 'parameter_combo'):
                    main_window = main_window.parent()
                if main_window and hasattr(main_window, 'parameter_combo'):
                    main_window.parameter_combo.setCurrentIndex(0)
            return
        
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
            max_offset = 119 * self.pixels_per_pitch - self.height()
            self.vertical_offset = min(max_offset, self.vertical_offset)
            self.update()
        
        elif event.key() == Qt.Key_Down:
            # Vertical scroll down (show lower pitches)
            self.vertical_offset -= 50
            min_offset = 0  # Don't scroll below C-1 (MIDI 0)
            self.vertical_offset = max(min_offset, self.vertical_offset)
            self.update()
        
        # Enter/Return: Rewind playhead to start (t=0)
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self._rewind_playhead()
        
        # Space key: Toggle playback
        elif event.key() == Qt.Key_Space:
            self._toggle_playback()
        
        # Comma: Move playhead to previous measure
        elif event.key() == Qt.Key_Comma:
            self._move_playhead_to_measure(-1)
        
        # Period: Move playhead to next measure  
        elif event.key() == Qt.Key_Period:
            self._move_playhead_to_measure(1)

        super().keyPressEvent(event)
    
    def _rewind_playhead(self):
        """Rewind playhead to the beginning (t=0)"""
        print("PianoRoll: _rewind_playhead called")
        
        # Reset playhead position to 0
        self.playhead_position = 0
        
        # Seek playback engine to position 0
        if self.playback_engine:
            self.playback_engine.seek_to_tick(0)
            print("Seeked to tick 0")
        
        # Play notes at the beginning position
        self._play_notes_at_playhead()
        
        # Update display
        self.update()
    
    def _toggle_playback(self):
        """Toggle playback state"""
        print("PianoRoll: _toggle_playback called")
        
        # Find the main window by traversing the widget hierarchy
        widget = self
        main_window = None
        
        while widget:
            widget = widget.parentWidget()
            if widget and hasattr(widget, 'toggle_playback'):
                main_window = widget
                break
        
        if main_window:
            print("PianoRoll: Found main window, calling toggle_playback")
            main_window.toggle_playback()
        else:
            print("PianoRoll: Could not find main window with toggle_playback method")
    
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
        
        # Sync with playback engine
        if self.playback_engine:
            self.playback_engine.seek_to_tick(self.playhead_position)
            print(f"Moved playhead to measure, tick: {self.playhead_position}")
        
        # Play notes at the new position
        self._play_notes_at_playhead()
        
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
                max_offset = 119 * self.pixels_per_pitch - self.height()
                min_offset = 0  # Don't scroll below C-1 (MIDI 0)
                self.vertical_offset = max(min_offset, min(max_offset, self.vertical_offset))
                self.update()
        elif event.modifiers() & Qt.AltModifier:
            # Alt+Wheel: Vertical zoom
            zoom_factor = 1.1 if scroll_y > 0 else 0.9
            center_y = self.height() / 2
            self._zoom_vertical(zoom_factor, center_y)
        else:
            # Normal scroll: Auto-detect direction (both horizontal and vertical)
            # Prioritize the axis with larger movement for better UX
            abs_scroll_x = abs(scroll_x)
            abs_scroll_y = abs(scroll_y)
            
            if abs_scroll_y > abs_scroll_x:
                # Vertical movement is dominant - handle as vertical scroll
                if scroll_y != 0:
                    scroll_amount = scroll_y / 120 * 30  # Convert to reasonable scroll amount
                    self.vertical_offset += scroll_amount  # Up swipe = scroll up (to higher pitches)
                    # Limit vertical scroll range
                    max_offset = 119 * self.pixels_per_pitch - self.height()
                    min_offset = 0  # Don't scroll below C-1 (MIDI 0)
                    self.vertical_offset = max(min_offset, min(max_offset, self.vertical_offset))
                    self.update()
            else:
                # Horizontal movement is dominant - handle as horizontal scroll
                if scroll_y != 0:
                    scroll_amount = scroll_y / 120 * 50  # Convert to reasonable scroll amount
                    # Flip direction for intuitive trackpad behavior: right swipe = move right
                    self.visible_start_tick = max(0, int(self.visible_start_tick + scroll_amount))
                    
                    # Check for range extension and sync measure bar
                    self._handle_scroll_update()
                    
                elif scroll_x != 0:
                    scroll_amount = scroll_x / 120 * 50
                    # Flip direction for intuitive trackpad behavior
                    self.visible_start_tick = max(0, int(self.visible_start_tick - scroll_amount))
                    
                    # Check for range extension and sync measure bar
                    self._handle_scroll_update()
        
        event.accept()
    
    def _handle_scroll_update(self):
        """Handle updates after scrolling (range extension, measure bar sync)"""
        # Calculate current visible end tick for range extension check
        grid_start_x = self.piano_width if self.show_piano_keyboard else 0
        visible_width = self.width() - grid_start_x
        visible_end_tick = self.visible_start_tick + int(visible_width / self.pixels_per_tick)
        
        # Check for range extension
        self.extend_range_if_needed(visible_end_tick)
        
        # Sync measure bar
        self._sync_measure_bar()
        
        # Update display
        self.update()
    
    def set_grid_subdivision(self, subdivision_type: str, ticks_per_subdivision: int):
        """Set the grid subdivision for beat division lines"""
        self.grid_subdivision_type = subdivision_type
        self.ticks_per_subdivision = ticks_per_subdivision
        self.update()  # Redraw with new subdivision
    
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
            
            # Update playback engine after cutting
            self._update_playback_engine()
            
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
            
            # Check if we need to extend range for pasted notes
            if notes_to_paste:
                max_end_tick = max(note.end_tick for note in notes_to_paste)
                self.extend_range_if_needed(max_end_tick)
            
            # Update playback engine after pasting
            self._update_playback_engine()
            
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
            # Update playback engine after undo
            self._update_playback_engine()
            
            self.selected_notes = [] # Clear selection after undo
            self.update()
        else:
            pass
            
    def _redo(self):
        """Redo last undone operation"""
        if self.command_history.redo():
            # Update playback engine after redo
            self._update_playback_engine()
            
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
        
        # Show parameter editing mode if active, otherwise show normal edit mode
        if self.parameter_edit_mode != "none":
            mode_text = f"Parameter Edit: {self.parameter_edit_mode.capitalize()} (ESC to exit)"
            mode_color = QColor(self.theme_colors.param_velocity)  # Red for parameter editing
        else:
            mode_text = self.edit_mode_manager.get_mode_display_name()
            mode_color = QColor(self.theme_colors.note_selected) if self.edit_mode_manager.is_selection_mode() else QColor(self.theme_colors.note_default)
        
        painter.setPen(mode_color)
        painter.drawText(width - 350, 25, mode_text)
        
        # Draw description
        font.setPointSize(10)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor(self.theme_colors.grid_line_normal))
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

            default_duration_ticks = self.quantize_grid_ticks
            new_note = MidiNote(
                pitch=clicked_pitch,
                start_tick=clicked_tick,
                end_tick=clicked_tick + default_duration_ticks,
                velocity=100, # Default velocity
                channel=0 # Default channel
            )

            # Add to the active track using command system
            if self.midi_project and self.midi_project.tracks:
                track_manager = get_track_manager()
                if track_manager:
                    # Get active track
                    active_track = track_manager.get_active_track()
                    if active_track:
                        # Update note channel to match track
                        new_note.channel = active_track.channel
                        command = AddNoteCommand(active_track, new_note)
                        self.command_history.execute_command(command)
                    else:
                        # Fallback to first track
                        command = AddNoteCommand(self.midi_project.tracks[0], new_note)
                        self.command_history.execute_command(command)
                else:
                    # Fallback to first track
                    command = AddNoteCommand(self.midi_project.tracks[0], new_note)
                    self.command_history.execute_command(command)
                
                # Check if we need to extend the horizontal range
                self.extend_range_if_needed(new_note.end_tick)
                
                # Update playback engine with new note
                self._update_playback_engine()
                
                # Play audio feedback for the new note using track-specific audio
                self._play_track_preview(new_note.pitch, new_note.velocity)
                # Select the newly created note
                self.selected_notes = [new_note]
                self.update() # Repaint to show the new note
    
    def _handle_selection_mode_click(self, event, clicked_x, clicked_y):
        """Handle mouse click in selection mode"""
        from PySide6.QtCore import QPointF
        
        clicked_tick = self._x_to_tick(clicked_x)
        clicked_pitch = self._y_to_pitch(clicked_y)
        
        # Check if clicking on an existing note
        clicked_note = None
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
                        clicked_note = note
                        break
                if clicked_note:
                    break
        
        if clicked_note:
            # Clicked on a note - check for resize/drag operations
            grid_start_x = self.piano_width if self.show_piano_keyboard else 0
            note_x = self._tick_to_x(clicked_note.start_tick) + grid_start_x
            note_width = clicked_note.duration * self.pixels_per_tick
            resize_threshold = 8  # pixels
            
            # Check if we're clicking on the edge for resizing
            is_right_edge = clicked_x >= (note_x + note_width - resize_threshold)
            is_left_edge = clicked_x <= (note_x + resize_threshold)
            
            if clicked_note in self.selected_notes:
                # Clicked on already selected note - start operation
                if is_right_edge or is_left_edge:
                    # Start resize operation (single or multi-note)
                    self.resizing_multiple_notes = True
                    self.resizing_left_edge = is_left_edge
                    
                    # Store original data for all selected notes
                    self.multi_resize_start_data = {}
                    for note in self.selected_notes:
                        self.multi_resize_start_data[note] = (note.start_tick, note.end_tick)
                else:
                    # Start drag operation (single or multi-note)
                    self.dragging_multiple_notes = True
                    self.drag_start_pos = QPointF(clicked_x, clicked_y)
                    
                    # Store original positions for all selected notes
                    self.multi_drag_start_positions = {}
                    for note in self.selected_notes:
                        self.multi_drag_start_positions[note] = (note.start_tick, note.pitch)
            else:
                # New note clicked - update selection
                if not (event.modifiers() & Qt.ControlModifier):
                    # Clear previous selection if not holding Ctrl
                    self.selected_notes.clear()
                
                # Add clicked note to selection
                self.selected_notes.append(clicked_note)
                
                # Also start operation immediately if we're on an edge
                if is_right_edge or is_left_edge:
                    # Start resize operation
                    self.resizing_multiple_notes = True
                    self.resizing_left_edge = is_left_edge
                    
                    # Store original data
                    self.multi_resize_start_data = {}
                    for note in self.selected_notes:
                        self.multi_resize_start_data[note] = (note.start_tick, note.end_tick)
                else:
                    # Start drag operation
                    self.dragging_multiple_notes = True
                    self.drag_start_pos = QPointF(clicked_x, clicked_y)
                    
                    # Store original positions
                    self.multi_drag_start_positions = {}
                    for note in self.selected_notes:
                        self.multi_drag_start_positions[note] = (note.start_tick, note.pitch)
        else:
            # No note clicked - start rectangle selection or handle grid
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
            if self.dragging_multiple_notes:
                # Handle multi-note drag
                self._handle_multi_note_drag(event)
            elif self.resizing_multiple_notes:
                # Handle multi-note resize
                self._handle_multi_note_resize(event)
            else:
                # Handle rectangle selection
                selection_rect = self.edit_mode_manager.get_selection_rectangle()
                if selection_rect:
                    from PySide6.QtCore import QPointF
                    self.edit_mode_manager.update_selection_rectangle(QPointF(event.position().x(), event.position().y()))
                    self.update()
    
    def _handle_multi_note_drag(self, event):
        """Handle dragging multiple selected notes"""
        if not self.drag_start_pos or not self.multi_drag_start_positions:
            return
        
        # Calculate movement delta
        current_x = event.position().x()
        current_y = event.position().y()
        
        delta_x = current_x - self.drag_start_pos.x()
        delta_y = current_y - self.drag_start_pos.y()
        
        # Convert pixel deltas to tick/pitch deltas
        delta_ticks = delta_x / self.pixels_per_tick
        delta_pitch = -delta_y / self.pixels_per_pitch  # Negative because Y increases downward
        
        # Apply movement to all selected notes
        for note in self.selected_notes:
            if note in self.multi_drag_start_positions:
                original_start_tick, original_pitch = self.multi_drag_start_positions[note]
                
                # Calculate new position
                new_start_tick = original_start_tick + delta_ticks
                new_pitch = original_pitch + delta_pitch
                
                # Quantize new position
                new_start_tick = round(new_start_tick / self.quantize_grid_ticks) * self.quantize_grid_ticks
                new_pitch = max(0, min(127, int(round(new_pitch))))  # Clamp to MIDI range
                
                # Calculate duration to preserve note length
                duration = note.end_tick - note.start_tick
                
                # Apply new position
                note.start_tick = max(0, int(new_start_tick))  # Ensure non-negative
                note.end_tick = note.start_tick + duration
                note.pitch = new_pitch
        
        self.update()
    
    def _handle_multi_note_resize(self, event):
        """Handle resizing multiple selected notes with relative scaling"""
        if not self.multi_resize_start_data:
            return
        
        current_x = event.position().x()
        current_tick = self._x_to_tick(current_x)
        
        # Quantize the target tick
        quantized_tick = round(current_tick / self.quantize_grid_ticks) * self.quantize_grid_ticks
        
        # Find a reference note (first note) to calculate the scaling factor
        reference_note = None
        reference_original_data = None
        
        for note in self.selected_notes:
            if note in self.multi_resize_start_data:
                reference_note = note
                reference_original_data = self.multi_resize_start_data[note]
                break
        
        if not reference_note or not reference_original_data:
            return
        
        ref_original_start, ref_original_end = reference_original_data
        ref_original_duration = ref_original_end - ref_original_start
        
        # Calculate scaling factor based on reference note
        if self.resizing_left_edge:
            # Left edge resize - calculate new start position and scaling
            new_ref_start = max(0, quantized_tick)
            min_duration = self.quantize_grid_ticks
            
            # Ensure minimum duration for reference note
            if new_ref_start >= ref_original_end - min_duration:
                new_ref_start = ref_original_end - min_duration
            
            # Calculate scale factor based on duration change
            new_ref_duration = ref_original_end - new_ref_start
            scale_factor = new_ref_duration / ref_original_duration if ref_original_duration > 0 else 1.0
            
        else:
            # Right edge resize - calculate new end position and scaling
            new_ref_end = max(ref_original_start + self.quantize_grid_ticks, quantized_tick)
            
            # Calculate scale factor based on duration change
            new_ref_duration = new_ref_end - ref_original_start
            scale_factor = new_ref_duration / ref_original_duration if ref_original_duration > 0 else 1.0
        
        # Apply scaling to all selected notes
        for note in self.selected_notes:
            if note in self.multi_resize_start_data:
                original_start_tick, original_end_tick = self.multi_resize_start_data[note]
                original_duration = original_end_tick - original_start_tick
                
                if self.resizing_left_edge:
                    # Scale duration and adjust start position
                    new_duration = max(self.quantize_grid_ticks, int(original_duration * scale_factor))
                    note.start_tick = original_end_tick - new_duration
                    note.end_tick = original_end_tick
                    
                    # Ensure start tick is not negative
                    if note.start_tick < 0:
                        note.start_tick = 0
                        note.end_tick = new_duration
                else:
                    # Scale duration and adjust end position
                    new_duration = max(self.quantize_grid_ticks, int(original_duration * scale_factor))
                    note.start_tick = original_start_tick
                    note.end_tick = original_start_tick + new_duration
        
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
            
            # Update playback engine after moving note
            self._update_playback_engine()
            
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
            
            # Update playback engine after resizing note
            self._update_playback_engine()
            
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
        # Handle multi-note operations first
        if self.dragging_multiple_notes:
            self._finish_multi_note_drag()
        elif self.resizing_multiple_notes:
            self._finish_multi_note_resize()
        else:
            # Handle rectangle selection
            selection_rect = self.edit_mode_manager.get_selection_rectangle()
            if selection_rect:
                # Get the final selection rectangle
                final_rect = self.edit_mode_manager.finish_selection_rectangle()
                if final_rect and final_rect.width() > 5 and final_rect.height() > 5:  # Minimum size
                    # Select notes within the rectangle
                    self._select_notes_in_rectangle(final_rect, event.modifiers() & Qt.ControlModifier)
            
            self.edit_mode_manager.clear_selection_rectangle()
        
        self.update()
    
    def _finish_multi_note_drag(self):
        """Finish multi-note drag operation and create command"""
        if not self.multi_drag_start_positions:
            self.dragging_multiple_notes = False
            return
        
        # Create list of note movements for command
        notes_with_deltas = []
        for note in self.selected_notes:
            if note in self.multi_drag_start_positions:
                old_start_tick, old_pitch = self.multi_drag_start_positions[note]
                new_start_tick = note.start_tick
                new_pitch = note.pitch
                
                # Only add to command if position actually changed
                if old_start_tick != new_start_tick or old_pitch != new_pitch:
                    notes_with_deltas.append((note, old_start_tick, old_pitch, new_start_tick, new_pitch))
        
        # Create and execute command if there were changes
        if notes_with_deltas:
            command = MoveMultipleNotesCommand(notes_with_deltas)
            self.command_history.execute_command(command)
            
            # Update playback engine
            self._update_playback_engine()
        
        # Clean up state
        self.dragging_multiple_notes = False
        self.multi_drag_start_positions.clear()
        self.drag_start_pos = None
    
    def _finish_multi_note_resize(self):
        """Finish multi-note resize operation and create command"""
        if not self.multi_resize_start_data:
            self.resizing_multiple_notes = False
            return
        
        # Create list of note resizes for command
        notes_with_resize_data = []
        for note in self.selected_notes:
            if note in self.multi_resize_start_data:
                old_start_tick, old_end_tick = self.multi_resize_start_data[note]
                new_start_tick = note.start_tick
                new_end_tick = note.end_tick
                
                # Only add to command if size actually changed
                if old_start_tick != new_start_tick or old_end_tick != new_end_tick:
                    notes_with_resize_data.append((note, old_start_tick, old_end_tick, new_start_tick, new_end_tick))
        
        # Create and execute command if there were changes
        if notes_with_resize_data:
            command = ResizeMultipleNotesCommand(notes_with_resize_data)
            self.command_history.execute_command(command)
            
            # Update playback engine
            self._update_playback_engine()
        
        # Clean up state
        self.resizing_multiple_notes = False
        self.multi_resize_start_data.clear()
        self.resizing_left_edge = False
    
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
        
        # Ensure theme colors are loaded
        if not self.theme_colors:
            self._apply_theme()
        
        # Fallback to default colors if theme colors still not available
        if not self.theme_colors:
            from src.settings import DARK_THEME
            self.theme_colors = DARK_THEME
        
        # Background for piano area
        painter.fillRect(0, 0, self.piano_width, height, QColor(self.theme_colors.background))
        
        # Draw white keys first (extended range)
        for pitch in range(0, 120):
            note_index = pitch % 12
            if note_index not in black_keys:  # White key
                y = self._pitch_to_y(pitch)
                key_height = self.pixels_per_pitch
                
                # White key color
                key_color = QColor(self.theme_colors.piano_white_key)
                
                painter.fillRect(0, int(y), self.piano_width - 1, int(key_height), key_color)
                
                # Key border
                painter.setPen(QColor(self.theme_colors.piano_separator))
                painter.drawRect(0, int(y), self.piano_width - 1, int(key_height))
                
                # Note label for C notes
                if note_index == 0:  # C note
                    octave = (pitch // 12) - 1
                    font = QFont()
                    font.setPointSize(8)
                    painter.setFont(font)
                    painter.setPen(QColor(self.theme_colors.piano_black_key))
                    painter.drawText(5, int(y + key_height - 3), f"C{octave}")
        
        # Draw black keys on top (extended range)
        for pitch in range(0, 120):
            note_index = pitch % 12
            if note_index in black_keys:  # Black key
                y = self._pitch_to_y(pitch)
                key_height = self.pixels_per_pitch
                black_key_width = self.piano_width  # Make black keys full width
                
                # Black key color
                key_color = QColor(self.theme_colors.piano_black_key)
                
                painter.fillRect(0, int(y), black_key_width, int(key_height), key_color)
                
                # Key border
                painter.setPen(QColor(self.theme_colors.piano_separator))
                painter.drawRect(0, int(y), black_key_width, int(key_height))
        
        # Separator line between piano and grid
        painter.setPen(QColor(self.theme_colors.piano_separator))
        painter.drawLine(self.piano_width - 1, 0, self.piano_width - 1, height)
        
        painter.restore()
    
    def _draw_playhead(self, painter: QPainter, height: int, grid_start_x: int):
        """Draw the playhead line"""
        painter.save()
        
        # Calculate playhead x position (add grid offset for proper alignment)
        playhead_x = self._tick_to_x(self.playhead_position) + grid_start_x
        
        # Only skip drawing if playhead is way off screen
        if playhead_x < -100 or playhead_x > self.width() + 100:
            painter.restore()
            return
        
        # Draw simple playhead line
        painter.setPen(QPen(QColor(self.theme_colors.playhead), 3))
        
        painter.drawLine(int(playhead_x), 0, int(playhead_x), height)
        
        painter.restore()
    
    def _draw_parameter_layer(self, painter: QPainter, width: int, height: int, grid_start_x: int):
        """Draw the parameter automation layer"""
        if not self.midi_project:
            return
        
        painter.save()
        
        # Draw dark overlay to indicate parameter editing mode
        overlay_bg = QColor(0, 0, 0, 40)  # Dark semi-transparent overlay
        painter.fillRect(grid_start_x, 0, width - grid_start_x, height, overlay_bg)
        
        # Get active track
        from src.track_manager import get_track_manager
        track_manager = get_track_manager()
        if not track_manager:
            painter.restore()
            return
        
        active_track_index = track_manager.get_active_track_index()
        if active_track_index < 0 or active_track_index >= len(self.midi_project.tracks):
            painter.restore()
            return
        
        active_track = self.midi_project.tracks[active_track_index]
        
        # Get parameter color
        parameter_color = QColor(self.parameter_colors.get(self.parameter_edit_mode, "#FFFFFF"))
        
        # Draw parameter range indicators first
        self._draw_parameter_range_indicators(painter, parameter_color, grid_start_x, height)
        
        if self.parameter_edit_mode == "velocity":
            self._draw_velocity_automation(painter, active_track, parameter_color, grid_start_x, height)
        elif self.parameter_edit_mode == "volume":
            self._draw_volume_automation(painter, active_track, parameter_color, grid_start_x, height)
        elif self.parameter_edit_mode == "expression":
            self._draw_expression_automation(painter, active_track, parameter_color, grid_start_x, height)
        
        # Draw parameter value indicators
        self._draw_parameter_value_indicators(painter, active_track, parameter_color, grid_start_x, height)
        
        painter.restore()
    
    def _draw_parameter_range_indicators(self, painter: QPainter, color: QColor, grid_start_x: int, height: int):
        """Draw parameter range indicators (0-127 lines and labels)"""
        # Parameter editing area: 20% to 80% of height
        param_top = height * 0.2
        param_bottom = height * 0.8
        
        # Draw subtle range lines
        range_color = QColor(255, 255, 255, 60)  # Light subtle lines
        painter.setPen(QPen(range_color, 1, Qt.DotLine))
        
        # Top line (127)
        painter.drawLine(grid_start_x, int(param_top), self.width(), int(param_top))
        
        # Bottom line (0)
        painter.drawLine(grid_start_x, int(param_bottom), self.width(), int(param_bottom))
        
        # Draw labels with better visibility
        label_color = QColor(255, 255, 255, 200)  # White labels
        painter.setPen(QPen(label_color))
        painter.setFont(QFont("Arial", 12, QFont.Bold))  # Larger, bold font
        
        # Labels on the left side with background
        label_x = grid_start_x - 35
        
        # Draw label backgrounds for better readability
        bg_color = QColor(0, 0, 0, 120)
        painter.fillRect(label_x - 5, int(param_top) - 8, 30, 16, bg_color)
        painter.fillRect(label_x - 5, int(param_bottom) - 8, 30, 16, bg_color)
        
        painter.drawText(label_x, int(param_top) + 5, "127")
        painter.drawText(label_x + 5, int(param_bottom) + 5, "0")
        
        # Parameter name label with background
        param_name = self.parameter_edit_mode.capitalize()
        title_text = f"{param_name} (0-127)"
        title_width = painter.fontMetrics().horizontalAdvance(title_text)
        painter.fillRect(grid_start_x + 5, int(param_top) - 20, title_width + 10, 18, bg_color)
        painter.drawText(grid_start_x + 10, int(param_top) - 5, title_text)
    
    def _draw_parameter_value_indicators(self, painter: QPainter, track, color: QColor, grid_start_x: int, height: int):
        """Draw current parameter value indicators"""
        if not track or not track.notes:
            return
        
        # Find hovered or recently edited note to show value for
        from src.track_manager import get_track_manager
        track_manager = get_track_manager()
        if not track_manager:
            return
        
        # Show values for visible notes only
        value_color = QColor(255, 255, 255, 255)  # Bright white
        painter.setPen(QPen(value_color))
        painter.setFont(QFont("Arial", 11, QFont.Bold))  # Larger, bold font
        
        for note in track.notes:
            note_start_x = self._tick_to_x(note.start_tick) + grid_start_x
            note_end_x = self._tick_to_x(note.end_tick) + grid_start_x
            
            # Skip notes outside visible area
            if note_end_x < grid_start_x or note_start_x > self.width():
                continue
            
            # Get current parameter value
            if self.parameter_edit_mode == "velocity":
                current_value = note.velocity
                value_y = self._velocity_to_y(current_value, height)
            elif self.parameter_edit_mode == "volume":
                current_value = note.volume
                value_y = self._cc_to_y(current_value, height)
            elif self.parameter_edit_mode == "expression":
                current_value = note.expression
                value_y = self._cc_to_y(current_value, height)
            else:
                continue
            
            # Draw value label with background for better readability
            value_text = str(current_value)
            text_width = painter.fontMetrics().horizontalAdvance(value_text)
            text_height = painter.fontMetrics().height()
            
            # Position label to the right of the bar
            label_x = int(note_start_x) + 20
            label_y = int(value_y) + 4
            
            # Draw background
            bg_color = QColor(0, 0, 0, 150)
            painter.fillRect(label_x - 2, label_y - text_height + 2, text_width + 4, text_height, bg_color)
            
            # Draw text
            painter.drawText(label_x, label_y, value_text)
    
    def _draw_velocity_automation(self, painter: QPainter, track, color: QColor, grid_start_x: int, height: int):
        """Draw velocity bars for the track (simplified - no automation)"""
        # Set up semi-transparent overlay
        overlay_color = QColor(color)
        overlay_color.setAlpha(120)  # Semi-transparent
        painter.setBrush(QBrush(overlay_color))
        
        line_color = QColor(color)
        line_color.setAlpha(200)  # More opaque for lines
        painter.setPen(QPen(line_color, 2))
        
        # Draw velocity bars for each note
        for note in track.notes:
            note_start_x = self._tick_to_x(note.start_tick) + grid_start_x
            note_end_x = self._tick_to_x(note.end_tick) + grid_start_x
            note_width = note_end_x - note_start_x
            
            # Skip notes that are outside visible area
            if note_end_x < grid_start_x or note_start_x > self.width():
                continue
            
            # Draw single unified velocity bar
            velocity_y = self._velocity_to_y(note.velocity, height)
            bar_bottom = height * 0.8
            bar_height = bar_bottom - velocity_y  # Calculate height properly (bottom - top)
            
            # Draw velocity bar - make it prominent for easy editing
            bar_width = max(8, min(16, int(note_width * 0.3)))  # Wider bars for easier clicking
            
            # Draw single bar from velocity level down to bottom
            bar_color = QColor(color)
            bar_color.setAlpha(180)  # More opaque for better visibility
            painter.setBrush(QBrush(bar_color))
            painter.fillRect(int(note_start_x), int(velocity_y), bar_width, int(bar_height), bar_color)
    
    def _draw_volume_automation(self, painter: QPainter, track, color: QColor, grid_start_x: int, height: int):
        """Draw volume bars for the track (simplified - same as velocity)"""
        # Set up semi-transparent overlay
        overlay_color = QColor(color)
        overlay_color.setAlpha(180)  # More opaque for better visibility
        painter.setBrush(QBrush(overlay_color))
        
        # Draw volume bars for each note
        for note in track.notes:
            note_start_x = self._tick_to_x(note.start_tick) + grid_start_x
            note_end_x = self._tick_to_x(note.end_tick) + grid_start_x
            note_width = note_end_x - note_start_x
            
            # Skip notes that are outside visible area
            if note_end_x < grid_start_x or note_start_x > self.width():
                continue
            
            # Draw single unified volume bar
            volume_y = self._cc_to_y(note.volume, height)
            bar_bottom = height * 0.8
            bar_height = bar_bottom - volume_y  # Calculate height properly (bottom - top)
            
            # Draw volume bar - make it prominent for easy editing
            bar_width = max(8, min(16, int(note_width * 0.3)))  # Wider bars for easier clicking
            
            # Draw single bar from volume level down to bottom
            bar_color = QColor(color)
            bar_color.setAlpha(180)  # More opaque for better visibility
            painter.setBrush(QBrush(bar_color))
            painter.fillRect(int(note_start_x), int(volume_y), bar_width, int(bar_height), bar_color)
    
    def _draw_expression_automation(self, painter: QPainter, track, color: QColor, grid_start_x: int, height: int):
        """Draw expression bars for the track (simplified - same as velocity)"""
        # Set up semi-transparent overlay
        overlay_color = QColor(color)
        overlay_color.setAlpha(180)  # More opaque for better visibility
        painter.setBrush(QBrush(overlay_color))
        
        # Draw expression bars for each note
        for note in track.notes:
            note_start_x = self._tick_to_x(note.start_tick) + grid_start_x
            note_end_x = self._tick_to_x(note.end_tick) + grid_start_x
            note_width = note_end_x - note_start_x
            
            # Skip notes that are outside visible area
            if note_end_x < grid_start_x or note_start_x > self.width():
                continue
            
            # Draw single unified expression bar
            expression_y = self._cc_to_y(note.expression, height)
            bar_bottom = height * 0.8
            bar_height = bar_bottom - expression_y  # Calculate height properly (bottom - top)
            
            # Draw expression bar - make it prominent for easy editing
            bar_width = max(8, min(16, int(note_width * 0.3)))  # Wider bars for easier clicking
            
            # Draw single bar from expression level down to bottom
            bar_color = QColor(color)
            bar_color.setAlpha(180)  # More opaque for better visibility
            painter.setBrush(QBrush(bar_color))
            painter.fillRect(int(note_start_x), int(expression_y), bar_width, int(bar_height), bar_color)
    
    def _velocity_to_y(self, velocity: int, height: int) -> float:
        """Convert velocity value (0-127) to y coordinate"""
        # Velocity 0 = bottom 80% of height, Velocity 127 = top 20% of height
        velocity_ratio = velocity / 127.0
        y_range = height * 0.6  # Use 60% of height for velocity range
        return height * 0.8 - (velocity_ratio * y_range)
    
    def _y_to_velocity(self, y: float, height: int) -> int:
        """Convert y coordinate to velocity value (0-127)"""
        # Inverse of _velocity_to_y
        y_range = height * 0.6
        velocity_ratio = (height * 0.8 - y) / y_range
        velocity = int(round(velocity_ratio * 127))
        return max(0, min(127, velocity))
    
    def _cc_to_y(self, cc_value: int, height: int) -> float:
        """Convert CC value (0-127) to y coordinate"""
        # CC 0 = bottom 80% of height, CC 127 = top 20% of height
        cc_ratio = cc_value / 127.0
        y_range = height * 0.6  # Use 60% of height for CC range
        return height * 0.8 - (cc_ratio * y_range)
    
    def _y_to_cc(self, y: float, height: int) -> int:
        """Convert y coordinate to CC value (0-127)"""
        # Inverse of _cc_to_y
        y_range = height * 0.6
        cc_ratio = (height * 0.8 - y) / y_range
        cc_value = int(round(cc_ratio * 127))
        return max(0, min(127, cc_value))
    
    def _handle_parameter_editing_click(self, event, clicked_x: float, clicked_y: float, grid_start_x: int) -> bool:
        """Handle mouse click in parameter editing mode"""
        if not self.midi_project:
            return False
        
        # Get active track
        from src.track_manager import get_track_manager
        track_manager = get_track_manager()
        if not track_manager:
            return False
        
        active_track_index = track_manager.get_active_track_index()
        if active_track_index < 0 or active_track_index >= len(self.midi_project.tracks):
            return False
        
        active_track = self.midi_project.tracks[active_track_index]
        
        if self.parameter_edit_mode == "velocity":
            return self._handle_velocity_bar_editing_click(event, clicked_x, clicked_y, grid_start_x, active_track)
        elif self.parameter_edit_mode == "volume":
            return self._handle_volume_bar_editing_click(event, clicked_x, clicked_y, grid_start_x, active_track)
        elif self.parameter_edit_mode == "expression":
            return self._handle_expression_bar_editing_click(event, clicked_x, clicked_y, grid_start_x, active_track)
        
        return False
    
    def _handle_velocity_bar_editing_click(self, event, clicked_x: float, clicked_y: float, grid_start_x: int, track) -> bool:
        """Handle velocity bar editing click - edit note velocity directly"""
        clicked_velocity = self._y_to_velocity(clicked_y, self.height())
        
        # Find velocity bar at this position using precise collision detection
        clicked_note = self._find_velocity_bar_at_position(clicked_x, clicked_y, grid_start_x, track)
        if clicked_note:
            # Start dragging this velocity bar
            self.dragging_automation_point = (clicked_note, -1)
            self.parameter_drag_start_pos = (clicked_x, clicked_y)
            self.parameter_drag_start_value = clicked_note.velocity
            self.parameter_editing = True
            
            # Also immediately set the new velocity
            clicked_note.velocity = clicked_velocity
            clicked_note.velocity_automation = None  # Clear automation when editing base velocity
            self.update()
            print(f"Started dragging velocity bar: {clicked_velocity}")
            return True
        
        return False
    
    def _handle_volume_bar_editing_click(self, event, clicked_x: float, clicked_y: float, grid_start_x: int, track) -> bool:
        """Handle volume bar editing click - edit note volume directly"""
        clicked_volume = self._y_to_cc(clicked_y, self.height())
        
        # Find volume bar at this position using precise collision detection
        clicked_note = self._find_volume_bar_at_position(clicked_x, clicked_y, grid_start_x, track)
        if clicked_note:
            # Start dragging this volume bar
            self.dragging_automation_point = (clicked_note, -1)
            self.parameter_drag_start_pos = (clicked_x, clicked_y)
            self.parameter_drag_start_value = clicked_note.volume
            self.parameter_editing = True
            
            # Also immediately set the new volume
            clicked_note.volume = clicked_volume
            clicked_note.volume_automation = None  # Clear automation when editing base volume
            self.update()
            print(f"Started dragging volume bar: {clicked_volume}")
            return True
        
        return False
    
    def _handle_expression_bar_editing_click(self, event, clicked_x: float, clicked_y: float, grid_start_x: int, track) -> bool:
        """Handle expression bar editing click - edit note expression directly"""
        clicked_expression = self._y_to_cc(clicked_y, self.height())
        
        # Find expression bar at this position using precise collision detection
        clicked_note = self._find_expression_bar_at_position(clicked_x, clicked_y, grid_start_x, track)
        if clicked_note:
            # Start dragging this expression bar
            self.dragging_automation_point = (clicked_note, -1)
            self.parameter_drag_start_pos = (clicked_x, clicked_y)
            self.parameter_drag_start_value = clicked_note.expression
            self.parameter_editing = True
            
            # Also immediately set the new expression
            clicked_note.expression = clicked_expression
            clicked_note.expression_automation = None  # Clear automation when editing base expression
            self.update()
            print(f"Started dragging expression bar: {clicked_expression}")
            return True
        
        return False
    
    def _handle_velocity_editing_click(self, event, clicked_x: float, clicked_y: float, grid_start_x: int, track) -> bool:
        """Handle velocity editing click"""
        # Convert click position to tick and velocity
        clicked_tick = self._x_to_tick(clicked_x - grid_start_x)
        clicked_velocity = self._y_to_velocity(clicked_y, self.height())
        
        # First, check if clicking on an existing automation point
        clicked_point = self._find_automation_point_at_position(clicked_x, clicked_y, grid_start_x, track)
        if clicked_point:
            note, point_index = clicked_point
            self.dragging_automation_point = (note, point_index)
            self.parameter_drag_start_pos = (clicked_x, clicked_y)
            if point_index >= 0:
                self.parameter_drag_start_value = note.velocity_automation[point_index].value
            else:
                self.parameter_drag_start_value = note.velocity
            self.parameter_editing = True
            print(f"Started dragging automation point: velocity={self.parameter_drag_start_value}")
            return True
        
        # Check if clicking within a note to add automation point
        for note in track.notes:
            if note.start_tick <= clicked_tick <= note.end_tick:
                # Calculate tick offset within the note
                tick_offset = clicked_tick - note.start_tick
                
                # Add automation point
                note.add_velocity_automation_point(tick_offset, clicked_velocity)
                
                # Start dragging the newly created point
                if note.velocity_automation:
                    # Find the point we just added
                    for i, point in enumerate(note.velocity_automation):
                        if point.tick_offset == tick_offset:
                            self.dragging_automation_point = (note, i)
                            self.parameter_drag_start_pos = (clicked_x, clicked_y)
                            self.parameter_drag_start_value = clicked_velocity
                            self.parameter_editing = True
                            break
                
                self.update()  # Redraw to show new point
                print(f"Added velocity automation point: tick_offset={tick_offset}, velocity={clicked_velocity}")
                return True
        
        return False
    
    def _handle_volume_editing_click(self, event, clicked_x: float, clicked_y: float, grid_start_x: int, track) -> bool:
        """Handle volume editing click"""
        # Convert click position to tick and volume
        clicked_tick = self._x_to_tick(clicked_x - grid_start_x)
        clicked_volume = self._y_to_cc(clicked_y, self.height())
        
        # First, check if clicking on an existing automation point
        clicked_point = self._find_volume_automation_point_at_position(clicked_x, clicked_y, grid_start_x, track)
        if clicked_point:
            note, point_index = clicked_point
            self.dragging_automation_point = (note, point_index)
            self.parameter_drag_start_pos = (clicked_x, clicked_y)
            if point_index >= 0:
                self.parameter_drag_start_value = note.volume_automation[point_index].value
            else:
                self.parameter_drag_start_value = note.volume
            self.parameter_editing = True
            print(f"Started dragging volume automation point: volume={self.parameter_drag_start_value}")
            return True
        
        # Check if clicking within a note to add automation point
        for note in track.notes:
            if note.start_tick <= clicked_tick <= note.end_tick:
                # Calculate tick offset within the note
                tick_offset = clicked_tick - note.start_tick
                
                # Add automation point
                note.add_volume_automation_point(tick_offset, clicked_volume)
                
                # Start dragging the newly created point
                if note.volume_automation:
                    # Find the point we just added
                    for i, point in enumerate(note.volume_automation):
                        if point.tick_offset == tick_offset:
                            self.dragging_automation_point = (note, i)
                            self.parameter_drag_start_pos = (clicked_x, clicked_y)
                            self.parameter_drag_start_value = clicked_volume
                            self.parameter_editing = True
                            break
                
                self.update()  # Redraw to show new point
                print(f"Added volume automation point: tick_offset={tick_offset}, volume={clicked_volume}")
                return True
        
        return False
    
    def _handle_expression_editing_click(self, event, clicked_x: float, clicked_y: float, grid_start_x: int, track) -> bool:
        """Handle expression editing click"""
        # Convert click position to tick and expression
        clicked_tick = self._x_to_tick(clicked_x - grid_start_x)
        clicked_expression = self._y_to_cc(clicked_y, self.height())
        
        # First, check if clicking on an existing automation point
        clicked_point = self._find_expression_automation_point_at_position(clicked_x, clicked_y, grid_start_x, track)
        if clicked_point:
            note, point_index = clicked_point
            self.dragging_automation_point = (note, point_index)
            self.parameter_drag_start_pos = (clicked_x, clicked_y)
            if point_index >= 0:
                self.parameter_drag_start_value = note.expression_automation[point_index].value
            else:
                self.parameter_drag_start_value = note.expression
            self.parameter_editing = True
            print(f"Started dragging expression automation point: expression={self.parameter_drag_start_value}")
            return True
        
        # Check if clicking within a note to add automation point
        for note in track.notes:
            if note.start_tick <= clicked_tick <= note.end_tick:
                # Calculate tick offset within the note
                tick_offset = clicked_tick - note.start_tick
                
                # Add automation point
                note.add_expression_automation_point(tick_offset, clicked_expression)
                
                # Start dragging the newly created point
                if note.expression_automation:
                    # Find the point we just added
                    for i, point in enumerate(note.expression_automation):
                        if point.tick_offset == tick_offset:
                            self.dragging_automation_point = (note, i)
                            self.parameter_drag_start_pos = (clicked_x, clicked_y)
                            self.parameter_drag_start_value = clicked_expression
                            self.parameter_editing = True
                            break
                
                self.update()  # Redraw to show new point
                print(f"Added expression automation point: tick_offset={tick_offset}, expression={clicked_expression}")
                return True
        
        return False
    
    def _find_automation_point_at_position(self, clicked_x: float, clicked_y: float, grid_start_x: int, track) -> tuple:
        """Find velocity bar at click position for simplified velocity editing"""
        for note in track.notes:
            note_start_x = self._tick_to_x(note.start_tick) + grid_start_x
            note_end_x = self._tick_to_x(note.end_tick) + grid_start_x
            note_width = note_end_x - note_start_x
            
            # Check if click is within velocity bar area (wider tolerance for easier clicking)
            bar_width = max(8, min(16, int(note_width * 0.3)))
            if (note_start_x <= clicked_x <= note_start_x + bar_width):
                return (note, -1)  # -1 indicates velocity bar editing
        
        return None
    
    def _find_velocity_bar_at_position(self, clicked_x: float, clicked_y: float, grid_start_x: int, track):
        """Find velocity bar at click position with generous collision detection"""
        tolerance = 10  # Extra pixels for easier clicking
        
        for note in track.notes:
            note_start_x = self._tick_to_x(note.start_tick) + grid_start_x
            note_end_x = self._tick_to_x(note.end_tick) + grid_start_x
            note_width = note_end_x - note_start_x
            
            # Skip notes outside visible area
            if note_end_x < grid_start_x or note_start_x > self.width():
                continue
            
            # Calculate bar dimensions (exactly matching drawing code)
            bar_width = max(8, min(16, int(note_width * 0.3)))
            velocity_y = self._velocity_to_y(note.velocity, self.height())
            bar_bottom = self.height() * 0.8
            
            # Expanded click area for easier interaction
            click_left = note_start_x - tolerance
            click_right = note_start_x + bar_width + tolerance
            click_top = velocity_y - tolerance
            click_bottom = bar_bottom + tolerance
            
            # Check if click is within the expanded area
            if (click_left <= clicked_x <= click_right and 
                click_top <= clicked_y <= click_bottom):
                return note
        
        return None
    
    def _find_volume_bar_at_position(self, clicked_x: float, clicked_y: float, grid_start_x: int, track):
        """Find volume bar at click position with generous collision detection"""
        tolerance = 10  # Extra pixels for easier clicking
        
        for note in track.notes:
            note_start_x = self._tick_to_x(note.start_tick) + grid_start_x
            note_end_x = self._tick_to_x(note.end_tick) + grid_start_x
            note_width = note_end_x - note_start_x
            
            # Skip notes outside visible area
            if note_end_x < grid_start_x or note_start_x > self.width():
                continue
            
            # Calculate bar dimensions (exactly matching drawing code)
            bar_width = max(8, min(16, int(note_width * 0.3)))
            volume_y = self._cc_to_y(note.volume, self.height())
            bar_bottom = self.height() * 0.8
            
            # Expanded click area for easier interaction
            click_left = note_start_x - tolerance
            click_right = note_start_x + bar_width + tolerance
            click_top = volume_y - tolerance
            click_bottom = bar_bottom + tolerance
            
            # Check if click is within the expanded area
            if (click_left <= clicked_x <= click_right and 
                click_top <= clicked_y <= click_bottom):
                return note
        
        return None
    
    def _find_expression_bar_at_position(self, clicked_x: float, clicked_y: float, grid_start_x: int, track):
        """Find expression bar at click position with generous collision detection"""
        tolerance = 10  # Extra pixels for easier clicking
        
        for note in track.notes:
            note_start_x = self._tick_to_x(note.start_tick) + grid_start_x
            note_end_x = self._tick_to_x(note.end_tick) + grid_start_x
            note_width = note_end_x - note_start_x
            
            # Skip notes outside visible area
            if note_end_x < grid_start_x or note_start_x > self.width():
                continue
            
            # Calculate bar dimensions (exactly matching drawing code)
            bar_width = max(8, min(16, int(note_width * 0.3)))
            expression_y = self._cc_to_y(note.expression, self.height())
            bar_bottom = self.height() * 0.8
            
            # Expanded click area for easier interaction
            click_left = note_start_x - tolerance
            click_right = note_start_x + bar_width + tolerance
            click_top = expression_y - tolerance
            click_bottom = bar_bottom + tolerance
            
            # Check if click is within the expanded area
            if (click_left <= clicked_x <= click_right and 
                click_top <= clicked_y <= click_bottom):
                return note
        
        return None
    
    def _find_volume_automation_point_at_position(self, clicked_x: float, clicked_y: float, grid_start_x: int, track) -> tuple:
        """Find volume automation point at click position, returns (note, point_index) or None"""
        click_tolerance = 8  # pixels
        
        for note in track.notes:
            note_start_x = self._tick_to_x(note.start_tick) + grid_start_x
            
            # Check note's base volume point (at note start)
            volume_y = self._cc_to_y(note.volume, self.height())
            if (abs(clicked_x - note_start_x) <= click_tolerance and 
                abs(clicked_y - volume_y) <= click_tolerance):
                return (note, -1)  # -1 indicates base volume point
            
            # Check automation points
            if note.volume_automation:
                for i, auto_point in enumerate(note.volume_automation):
                    point_tick = note.start_tick + auto_point.tick_offset
                    point_x = self._tick_to_x(point_tick) + grid_start_x
                    point_y = self._cc_to_y(auto_point.value, self.height())
                    
                    if (abs(clicked_x - point_x) <= click_tolerance and 
                        abs(clicked_y - point_y) <= click_tolerance):
                        return (note, i)
        
        return None
    
    def _find_expression_automation_point_at_position(self, clicked_x: float, clicked_y: float, grid_start_x: int, track) -> tuple:
        """Find expression automation point at click position, returns (note, point_index) or None"""
        click_tolerance = 8  # pixels
        
        for note in track.notes:
            note_start_x = self._tick_to_x(note.start_tick) + grid_start_x
            
            # Check note's base expression point (at note start)
            expression_y = self._cc_to_y(note.expression, self.height())
            if (abs(clicked_x - note_start_x) <= click_tolerance and 
                abs(clicked_y - expression_y) <= click_tolerance):
                return (note, -1)  # -1 indicates base expression point
            
            # Check automation points
            if note.expression_automation:
                for i, auto_point in enumerate(note.expression_automation):
                    point_tick = note.start_tick + auto_point.tick_offset
                    point_x = self._tick_to_x(point_tick) + grid_start_x
                    point_y = self._cc_to_y(auto_point.value, self.height())
                    
                    if (abs(clicked_x - point_x) <= click_tolerance and 
                        abs(clicked_y - point_y) <= click_tolerance):
                        return (note, i)
        
        return None
    
    def _handle_parameter_drag(self, event):
        """Handle dragging of automation points"""
        if not self.dragging_automation_point or not self.parameter_drag_start_pos:
            return
        
        current_x = event.position().x()
        current_y = event.position().y()
        
        note, point_index = self.dragging_automation_point
        
        if self.parameter_edit_mode == "velocity":
            # Calculate new velocity based on Y movement
            new_value = self._y_to_velocity(current_y, self.height())
            
            # For velocity bar editing, always edit base velocity and clear automation
            note.velocity = new_value
            note.velocity_automation = None  # Clear automation when editing base velocity
            print(f"Updated note velocity to {new_value}")
        
        elif self.parameter_edit_mode == "volume":
            # Calculate new volume based on Y movement
            new_value = self._y_to_cc(current_y, self.height())
            
            if point_index == -1:
                # Dragging base volume of note
                note.volume = new_value
                print(f"Updated note base volume to {new_value}")
            elif point_index >= 0 and note.volume_automation:
                # Dragging automation point
                if point_index < len(note.volume_automation):
                    note.volume_automation[point_index].value = new_value
                    print(f"Updated automation point volume to {new_value}")
        
        elif self.parameter_edit_mode == "expression":
            # Calculate new expression based on Y movement
            new_value = self._y_to_cc(current_y, self.height())
            
            if point_index == -1:
                # Dragging base expression of note
                note.expression = new_value
                print(f"Updated note base expression to {new_value}")
            elif point_index >= 0 and note.expression_automation:
                # Dragging automation point
                if point_index < len(note.expression_automation):
                    note.expression_automation[point_index].value = new_value
                    print(f"Updated automation point expression to {new_value}")
        
        self.update()
    
    def _handle_parameter_swipe(self, event):
        """Handle trackpad swiping for smooth parameter drawing"""
        if not self.midi_project:
            return
        
        current_x = event.position().x()
        current_y = event.position().y()
        
        # Only process if mouse is pressed (trackpad contact)
        if not (event.buttons() & Qt.LeftButton):
            self.last_parameter_edit_pos = None
            return
        
        grid_start_x = self.piano_width if self.show_piano_keyboard else 0
        if current_x < grid_start_x:
            return
        
        # Get active track
        from src.track_manager import get_track_manager
        track_manager = get_track_manager()
        if not track_manager:
            return
        
        active_track_index = track_manager.get_active_track_index()
        if active_track_index < 0 or active_track_index >= len(self.midi_project.tracks):
            return
        
        active_track = self.midi_project.tracks[active_track_index]
        
        # Convert position to tick and parameter value
        current_tick = self._x_to_tick(current_x - grid_start_x)
        
        if self.parameter_edit_mode == "velocity":
            current_value = self._y_to_velocity(current_y, self.height())
            # For velocity bar editing, edit note velocity directly
            self._set_velocity_at_tick_if_in_note(active_track, current_tick, current_value)
        else:  # volume or expression
            current_value = self._y_to_cc(current_y, self.height())
            # For CC parameters, allow editing across note boundaries for continuous control
            if self.last_parameter_edit_pos:
                last_x, last_y = self.last_parameter_edit_pos
                last_tick = self._x_to_tick(last_x - grid_start_x)
                
                # Interpolate between last and current position
                self._draw_parameter_line(active_track, last_tick, current_tick, last_y, current_y)
            else:
                # First point, just add it
                self._add_parameter_point_at_tick(active_track, current_tick, current_value)
        
        self.last_parameter_edit_pos = (current_x, current_y)
        self.update()
    
    def _handle_parameter_release(self, event):
        """Handle mouse release for parameter editing"""
        self.parameter_editing = False
        self.dragging_automation_point = None
        self.parameter_drag_start_pos = None
        self.parameter_drag_start_value = None
        self.last_parameter_edit_pos = None
        self.logger.debug("Parameter editing released")
    
    def _draw_parameter_line(self, track, start_tick: int, end_tick: int, start_y: float, end_y: float):
        """Draw a smooth line of automation points between two positions"""
        if start_tick == end_tick:
            return
        
        # Ensure start < end
        if start_tick > end_tick:
            start_tick, end_tick = end_tick, start_tick
            start_y, end_y = end_y, start_y
        
        # Calculate step size based on pixel distance
        tick_range = end_tick - start_tick
        steps = max(1, tick_range // 30)  # One point every 30 ticks approximately
        
        for i in range(steps + 1):
            ratio = i / steps if steps > 0 else 0
            interpolated_tick = start_tick + ratio * tick_range
            interpolated_y = start_y + ratio * (end_y - start_y)
            if self.parameter_edit_mode == "velocity":
                interpolated_value = self._y_to_velocity(interpolated_y, self.height())
            else:  # volume or expression
                interpolated_value = self._y_to_cc(interpolated_y, self.height())
            
            self._add_parameter_point_at_tick(track, interpolated_tick, interpolated_value)
    
    def _add_parameter_point_at_tick(self, track, tick: int, value: int):
        """Add parameter point at specific tick position"""
        # Find note that contains this tick
        for note in track.notes:
            if note.start_tick <= tick <= note.end_tick:
                tick_offset = tick - note.start_tick
                
                if self.parameter_edit_mode == "velocity":
                    note.add_velocity_automation_point(tick_offset, value)
                elif self.parameter_edit_mode == "volume":
                    note.add_volume_automation_point(tick_offset, value)
                elif self.parameter_edit_mode == "expression":
                    note.add_expression_automation_point(tick_offset, value)
                break
    
    def _add_velocity_point_at_tick_if_in_note(self, track, tick: int, velocity: int):
        """Add velocity point only if tick is within an existing note"""
        for note in track.notes:
            if note.start_tick <= tick <= note.end_tick:
                tick_offset = tick - note.start_tick
                note.add_velocity_automation_point(tick_offset, velocity)
                break  # Only add to one note per tick
    
    def _set_velocity_at_tick_if_in_note(self, track, tick: int, velocity: int):
        """Set note velocity directly if tick is within an existing note"""
        for note in track.notes:
            if note.start_tick <= tick <= note.end_tick:
                note.velocity = velocity
                note.velocity_automation = None  # Clear automation when editing base velocity
                break  # Only edit one note per tick
    
    def _handle_parameter_right_click(self, clicked_x: float, clicked_y: float, grid_start_x: int) -> bool:
        """Handle right-click in parameter editing mode for deleting points"""
        if not self.midi_project:
            return False
        
        # Get active track
        from src.track_manager import get_track_manager
        track_manager = get_track_manager()
        if not track_manager:
            return False
        
        active_track_index = track_manager.get_active_track_index()
        if active_track_index < 0 or active_track_index >= len(self.midi_project.tracks):
            return False
        
        active_track = self.midi_project.tracks[active_track_index]
        
        if self.parameter_edit_mode == "velocity":
            return self._handle_velocity_bar_right_click(clicked_x, clicked_y, grid_start_x, active_track)
        elif self.parameter_edit_mode == "volume":
            return self._handle_volume_bar_right_click(clicked_x, clicked_y, grid_start_x, active_track)
        elif self.parameter_edit_mode == "expression":
            return self._handle_expression_bar_right_click(clicked_x, clicked_y, grid_start_x, active_track)
        
        return False
    
    def _handle_velocity_bar_right_click(self, clicked_x: float, clicked_y: float, grid_start_x: int, track) -> bool:
        """Handle right-click for velocity bar editing - reset to default"""
        # Find velocity bar at this position using precise collision detection
        clicked_note = self._find_velocity_bar_at_position(clicked_x, clicked_y, grid_start_x, track)
        if clicked_note:
            clicked_note.velocity = 100  # Reset to default velocity
            clicked_note.velocity_automation = None  # Clear any automation
            self.update()
            print(f"Reset note velocity to default (100)")
            return True
        
        return False
    
    def _handle_volume_bar_right_click(self, clicked_x: float, clicked_y: float, grid_start_x: int, track) -> bool:
        """Handle right-click for volume bar editing - reset to default"""
        # Find volume bar at this position using precise collision detection
        clicked_note = self._find_volume_bar_at_position(clicked_x, clicked_y, grid_start_x, track)
        if clicked_note:
            clicked_note.volume = 100  # Reset to default volume
            clicked_note.volume_automation = None  # Clear any automation
            self.update()
            print(f"Reset note volume to default (100)")
            return True
        
        return False
    
    def _handle_expression_bar_right_click(self, clicked_x: float, clicked_y: float, grid_start_x: int, track) -> bool:
        """Handle right-click for expression bar editing - reset to default"""
        # Find expression bar at this position using precise collision detection
        clicked_note = self._find_expression_bar_at_position(clicked_x, clicked_y, grid_start_x, track)
        if clicked_note:
            clicked_note.expression = 127  # Reset to default expression
            clicked_note.expression_automation = None  # Clear any automation
            self.update()
            print(f"Reset note expression to default (127)")
            return True
        
        return False
    
    def _handle_velocity_right_click(self, clicked_x: float, clicked_y: float, grid_start_x: int, track) -> bool:
        """Handle right-click for velocity editing - delete automation points"""
        # Find automation point at click position
        clicked_point = self._find_automation_point_at_position(clicked_x, clicked_y, grid_start_x, track)
        if not clicked_point:
            return False
        
        note, point_index = clicked_point
        
        if point_index == -1:
            # Right-clicked on base velocity point - reset to default
            note.velocity = 100  # Reset to default velocity
            note.velocity_automation = None  # Clear all automation
            print(f"Reset note velocity to default (100) and cleared automation")
        elif point_index >= 0 and note.velocity_automation:
            # Right-clicked on automation point - delete it
            if point_index < len(note.velocity_automation):
                deleted_point = note.velocity_automation.pop(point_index)
                print(f"Deleted automation point: tick_offset={deleted_point.tick_offset}, value={deleted_point.value}")
                
                # Clear automation list if empty
                if not note.velocity_automation:
                    note.velocity_automation = None
        
        self.update()
        return True
    
    def _handle_volume_right_click(self, clicked_x: float, clicked_y: float, grid_start_x: int, track) -> bool:
        """Handle right-click for volume editing - delete automation points"""
        # Find automation point at click position
        clicked_point = self._find_volume_automation_point_at_position(clicked_x, clicked_y, grid_start_x, track)
        if not clicked_point:
            return False
        
        note, point_index = clicked_point
        
        if point_index == -1:
            # Right-clicked on base volume point - reset to default
            note.volume = 100  # Reset to default volume
            note.volume_automation = None  # Clear all automation
            print(f"Reset note volume to default (100) and cleared automation")
        elif point_index >= 0 and note.volume_automation:
            # Right-clicked on automation point - delete it
            if point_index < len(note.volume_automation):
                deleted_point = note.volume_automation.pop(point_index)
                print(f"Deleted volume automation point: tick_offset={deleted_point.tick_offset}, value={deleted_point.value}")
                
                # Clear automation list if empty
                if not note.volume_automation:
                    note.volume_automation = None
        
        self.update()
        return True
    
    def _handle_expression_right_click(self, clicked_x: float, clicked_y: float, grid_start_x: int, track) -> bool:
        """Handle right-click for expression editing - delete automation points"""
        # Find automation point at click position
        clicked_point = self._find_expression_automation_point_at_position(clicked_x, clicked_y, grid_start_x, track)
        if not clicked_point:
            return False
        
        note, point_index = clicked_point
        
        if point_index == -1:
            # Right-clicked on base expression point - reset to default
            note.expression = 127  # Reset to default expression
            note.expression_automation = None  # Clear all automation
            print(f"Reset note expression to default (127) and cleared automation")
        elif point_index >= 0 and note.expression_automation:
            # Right-clicked on automation point - delete it
            if point_index < len(note.expression_automation):
                deleted_point = note.expression_automation.pop(point_index)
                print(f"Deleted expression automation point: tick_offset={deleted_point.tick_offset}, value={deleted_point.value}")
                
                # Clear automation list if empty
                if not note.expression_automation:
                    note.expression_automation = None
        
        self.update()
        return True
    
    def _play_selected_notes_as_chord(self):
        """Play selected notes as a chord"""
        if not self.selected_notes:
            return
        
        audio_manager = get_audio_manager()
        if not audio_manager:
            return
        
        # Get pitches from selected notes
        pitches = [note.pitch for note in self.selected_notes]
        
        # Play all notes simultaneously as a chord using track-specific audio
        self._play_chord_preview(pitches, 100)
        
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
            self._play_chord_preview(pitches, 100)
            
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
    
    def _play_chord_preview(self, pitches: List[int], velocity: int = 100):
        """Play multiple notes simultaneously as a chord"""
        from src.audio_routing_coordinator import get_audio_routing_coordinator
        from src.track_manager import get_track_manager
        from src.audio_source_manager import get_audio_source_manager
        
        # Stop any previous preview notes to prevent overlapping/sustained notes
        self._stop_all_preview_notes()
        
        # Get active track information
        track_manager = get_track_manager()
        if not track_manager:
            return False
        
        active_track_index = track_manager.get_active_track_index()
        
        # Check if track has audio source - skip preview for silent tracks
        audio_source_manager = get_audio_source_manager()
        if audio_source_manager:
            track_source = audio_source_manager.get_track_source(active_track_index)
            if track_source and track_source.source_type == AudioSourceType.NONE:
                print(f"PianoRoll: Track {active_track_index} has no audio source - skipping chord preview")
                return False
        
        # Get unified audio routing coordinator
        coordinator = get_audio_routing_coordinator()
        if not coordinator or coordinator.state.value != "ready":
            print(f"PianoRoll: Audio routing coordinator not ready, using legacy fallback for chord")
            return self._play_chord_preview_legacy(pitches, velocity)
        
        # Play all notes in the chord simultaneously
        from src.midi_data_model import MidiNote
        success_count = 0
        
        for pitch in pitches:
            preview_note = MidiNote(
                start_tick=0,
                end_tick=480,  # Short duration for preview
                pitch=pitch,
                velocity=velocity,
                channel=active_track_index  # Use track index as channel
            )
            
            # Use unified audio routing coordinator
            try:
                success = coordinator.play_note(active_track_index, preview_note)
                if success:
                    self.active_preview_notes.add(pitch)
                    success_count += 1
                else:
                    print(f"PianoRoll: Failed to play chord note {pitch}")
            except Exception as e:
                print(f"PianoRoll: Error playing chord note {pitch}: {e}")
        
        if success_count > 0:
            # Auto-stop all notes after 1000ms (longer for chord)
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1000, self._stop_all_preview_notes)
            print(f"PianoRoll: Chord preview with {success_count} notes playing on track {active_track_index}")
            return True
        
        return False
    
    def _play_chord_preview_legacy(self, pitches: List[int], velocity: int = 100):
        """Legacy fallback for chord preview when coordinator is not available"""
        from src.midi_routing import get_midi_routing_manager
        from src.audio_system import get_audio_manager
        from src.track_manager import get_track_manager
        from src.audio_source_manager import get_audio_source_manager
        
        print("PianoRoll: Using legacy chord preview fallback")
        
        # Get active track information
        track_manager = get_track_manager()
        if not track_manager:
            return False
        
        active_track_index = track_manager.get_active_track_index()
        
        # Get track source information
        audio_source_manager = get_audio_source_manager()
        track_source = None
        if audio_source_manager:
            track_source = audio_source_manager.get_track_source(active_track_index)
            if track_source and track_source.source_type == AudioSourceType.NONE:
                print(f"PianoRoll: Track {active_track_index} has no audio source - skipping chord preview")
                return False
        
        # Try MIDI routing for chord
        midi_router = get_midi_routing_manager()
        if midi_router and track_source:
            # Set program if available
            if track_source.program is not None:
                try:
                    program_change = [0xC0 | (track_source.channel & 0x0F), track_source.program & 0x7F]
                    midi_router.send_midi_message(program_change)
                except Exception as e:
                    print(f"PianoRoll: Could not set program for chord: {e}")
            
            # Play all notes in the chord simultaneously
            channel = track_source.channel if track_source else active_track_index
            success_count = 0
            
            for pitch in pitches:
                try:
                    midi_router.play_note(channel, pitch, velocity)
                    self.active_preview_notes.add(pitch)
                    success_count += 1
                except Exception as e:
                    print(f"PianoRoll: Error playing chord note {pitch}: {e}")
            
            if success_count > 0:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(1000, self._stop_all_preview_notes)
                print(f"PianoRoll: Legacy chord preview with {success_count} notes on channel {channel}")
                return True
        
        return False

    def _play_track_preview(self, pitch: int, velocity: int = 100):
        """Play a preview note using the current track's audio source via unified routing coordinator"""
        from src.audio_routing_coordinator import get_audio_routing_coordinator
        from src.track_manager import get_track_manager
        from src.audio_source_manager import get_audio_source_manager
        
        # Stop any previous preview notes to prevent overlapping/sustained notes
        self._stop_all_preview_notes()
        
        # Get active track information
        track_manager = get_track_manager()
        if not track_manager:
            return False
        
        active_track_index = track_manager.get_active_track_index()
        
        # Check if track has audio source - skip preview for silent tracks
        audio_source_manager = get_audio_source_manager()
        if audio_source_manager:
            track_source = audio_source_manager.get_track_source(active_track_index)
            if track_source and track_source.source_type == AudioSourceType.NONE:
                print(f"PianoRoll: Track {active_track_index} has no audio source - skipping note preview")
                return False
        
        # Get unified audio routing coordinator
        coordinator = get_audio_routing_coordinator()
        if not coordinator or coordinator.state.value != "ready":
            print(f"PianoRoll: Audio routing coordinator not ready (state: {coordinator.state.value if coordinator else 'None'})")
            
            # Try to initialize coordinator if not done
            if not coordinator:
                print("PianoRoll: Attempting to initialize audio routing coordinator...")
                from src.audio_routing_coordinator import initialize_audio_routing_coordinator
                coordinator = initialize_audio_routing_coordinator()
                if coordinator and coordinator.state.value == "ready":
                    print("PianoRoll: Successfully initialized audio routing coordinator")
                    # Continue with coordinator
                else:
                    print("PianoRoll: Failed to initialize coordinator, using legacy fallback")
                    return self._play_track_preview_legacy(pitch, velocity)
            else:
                print(f"PianoRoll: Using legacy fallback for preview on track {active_track_index}")
                return self._play_track_preview_legacy(pitch, velocity)
        
        # Create a temporary MIDI note for preview
        from src.midi_data_model import MidiNote
        preview_note = MidiNote(
            start_tick=0,
            end_tick=480,  # Short duration for preview
            pitch=pitch,
            velocity=velocity,
            channel=active_track_index  # Use track index as channel
        )
        
        # Use unified audio routing coordinator
        try:
            success = coordinator.play_note(active_track_index, preview_note)
            if success:
                self.active_preview_notes.add(pitch)
                # Auto-stop the note after 500ms
                QTimer.singleShot(500, lambda: self._stop_track_preview(pitch))
                print(f"PianoRoll: Preview note {pitch} playing on track {active_track_index} via coordinator")
                return True
            else:
                print(f"PianoRoll: Audio routing coordinator failed to play preview note {pitch} on track {active_track_index}")
                # If coordinator fails, try legacy fallback
                return self._play_track_preview_legacy(pitch, velocity)
        except Exception as e:
            print(f"PianoRoll: Audio routing coordinator error for preview note {pitch}: {e}")
            # If coordinator has error, try legacy fallback
            return self._play_track_preview_legacy(pitch, velocity)
    
    def _play_track_preview_legacy(self, pitch: int, velocity: int = 100):
        """Legacy fallback for track preview when coordinator is not available"""
        from src.midi_routing import get_midi_routing_manager
        from src.audio_system import get_audio_manager
        from src.track_manager import get_track_manager
        from src.audio_source_manager import get_audio_source_manager
        from src.per_track_audio_router import get_per_track_audio_router
        
        print("PianoRoll: Using legacy preview fallback")
        
        # Get active track information
        track_manager = get_track_manager()
        if not track_manager:
            return False
        
        active_track_index = track_manager.get_active_track_index()
        print(f"PianoRoll: Legacy preview for track {active_track_index}")
        
        # Try per-track router with track-specific source first
        per_track_router = get_per_track_audio_router()
        if per_track_router:
            from src.midi_data_model import MidiNote
            preview_note = MidiNote(0, 480, pitch, velocity, active_track_index)
            
            success = per_track_router.play_note(active_track_index, preview_note)
            if success:
                self.active_preview_notes.add(pitch)
                QTimer.singleShot(500, lambda: self._stop_track_preview_legacy(pitch))
                print(f"PianoRoll: Legacy preview via per-track router - note {pitch} on track {active_track_index}")
                return True
        
        # Get active track's audio source info for better routing
        audio_source_manager = get_audio_source_manager()
        track_source = None
        if audio_source_manager:
            track_source = audio_source_manager.get_track_source(active_track_index)
            if track_source:
                print(f"PianoRoll: Active track {active_track_index} uses source: {track_source.name} (ch: {track_source.channel}, prog: {track_source.program})")
        
        # Try MIDI routing with track's channel and program
        midi_router = get_midi_routing_manager()
        if midi_router:
            # Skip preview if track has no audio source
            if track_source and track_source.source_type == AudioSourceType.NONE:
                print(f"PianoRoll: Track {active_track_index} has no audio source - skipping note preview")
                return False
            
            # Set program for the track's channel if we have source info
            if track_source and track_source.program is not None:
                try:
                    # Send program change before note
                    program_change = [0xC0 | (track_source.channel & 0x0F), track_source.program & 0x7F]
                    midi_router.send_midi_message(program_change)
                    print(f"PianoRoll: Set program {track_source.program} on channel {track_source.channel}")
                except Exception as e:
                    print(f"PianoRoll: Could not set program: {e}")
            elif track_source and track_source.program is None:
                print(f"PianoRoll: Track {active_track_index} has no instrument - skipping note preview")
                return False
            
            # Play note on appropriate channel
            channel = track_source.channel if track_source else active_track_index
            midi_router.play_note(channel, pitch, velocity)
            self.active_preview_notes.add(pitch)
            QTimer.singleShot(500, lambda: self._stop_track_preview_legacy(pitch))
            print(f"PianoRoll: Legacy preview via MIDI routing - note {pitch} on channel {channel}")
            return True
        
        # Final fallback to direct audio manager
        audio_manager = get_audio_manager()
        if audio_manager:
            # Skip preview if track has no audio source
            if track_source and track_source.source_type == AudioSourceType.NONE:
                print(f"PianoRoll: Track {active_track_index} has no audio source - skipping audio manager preview")
                return False
            
            # Set program if we have track source info
            if track_source and track_source.program is not None:
                try:
                    audio_manager.set_program(track_source.program)
                    audio_manager.set_channel(track_source.channel)
                    print(f"PianoRoll: Set audio manager to program {track_source.program}, channel {track_source.channel}")
                except Exception as e:
                    print(f"PianoRoll: Could not configure audio manager: {e}")
            elif track_source and track_source.program is None:
                print(f"PianoRoll: Track {active_track_index} has no instrument - skipping audio manager preview")
                return False
            
            channel = track_source.channel if track_source else active_track_index
            result = audio_manager.play_note_immediate(pitch, velocity, channel)
            if result:
                self.active_preview_notes.add(pitch)
                QTimer.singleShot(500, lambda: self._stop_track_preview_legacy(pitch))
                print(f"PianoRoll: Legacy preview via audio manager - note {pitch} on channel {channel}")
            return result
        
        print("PianoRoll: No audio systems available for preview")
        return False
    
    def _stop_track_preview_legacy(self, pitch: int):
        """Legacy fallback for stopping track preview"""
        from src.midi_routing import get_midi_routing_manager
        from src.audio_system import get_audio_manager
        from src.track_manager import get_track_manager
        from src.audio_source_manager import get_audio_source_manager
        from src.per_track_audio_router import get_per_track_audio_router
        
        if pitch not in self.active_preview_notes:
            return False
        
        track_manager = get_track_manager()
        if not track_manager:
            return False
        
        active_track_index = track_manager.get_active_track_index()
        
        # Try per-track router first
        per_track_router = get_per_track_audio_router()
        if per_track_router:
            from src.midi_data_model import MidiNote
            preview_note = MidiNote(0, 480, pitch, 100, active_track_index)
            success = per_track_router.stop_note(active_track_index, preview_note)
            if success:
                self.active_preview_notes.discard(pitch)
                return True
        
        # Get track source for proper channel
        audio_source_manager = get_audio_source_manager()
        track_source = None
        if audio_source_manager:
            track_source = audio_source_manager.get_track_source(active_track_index)
        
        # Try MIDI routing with correct channel
        midi_router = get_midi_routing_manager()
        if midi_router:
            channel = track_source.channel if track_source else active_track_index
            midi_router.stop_note(channel, pitch)
            self.active_preview_notes.discard(pitch)
            return True
        
        # Fallback to direct audio manager  
        audio_manager = get_audio_manager()
        if audio_manager:
            channel = track_source.channel if track_source else active_track_index
            result = audio_manager.stop_note_immediate(pitch, channel)
            self.active_preview_notes.discard(pitch)
            return result
        
        self.active_preview_notes.discard(pitch)  # Always remove from tracking
        return False
    
    def _stop_track_preview(self, pitch: int):
        """Stop a preview note using the current track's audio source via unified routing coordinator"""
        from src.audio_routing_coordinator import get_audio_routing_coordinator
        from src.track_manager import get_track_manager
        
        if pitch not in self.active_preview_notes:
            return False  # Note is not currently playing
        
        # Get active track information
        track_manager = get_track_manager()
        if not track_manager:
            return False
        
        active_track_index = track_manager.get_active_track_index()
        
        # Get unified audio routing coordinator
        coordinator = get_audio_routing_coordinator()
        if not coordinator or coordinator.state.value != "ready":
            # Use legacy fallback if coordinator not available
            return self._stop_track_preview_legacy(pitch)
        
        # Create a temporary MIDI note for stopping
        from src.midi_data_model import MidiNote
        preview_note = MidiNote(
            start_tick=0,
            end_tick=480,
            pitch=pitch,
            velocity=100,
            channel=active_track_index
        )
        
        # Use unified audio routing coordinator
        try:
            success = coordinator.stop_note(active_track_index, preview_note)
            self.active_preview_notes.discard(pitch)  # Always remove from tracking
            if success:
                print(f"PianoRoll: Preview note {pitch} stopped on track {active_track_index}")
            else:
                print(f"PianoRoll: Audio routing coordinator failed to stop preview note {pitch}")
            return success
        except Exception as e:
            print(f"PianoRoll: Audio routing coordinator error stopping preview note {pitch}: {e}")
            self.active_preview_notes.discard(pitch)  # Always remove from tracking
            return False
    
    def _stop_all_preview_notes(self):
        """Stop all currently playing preview notes"""
        for pitch in list(self.active_preview_notes):  # Create copy to avoid modification during iteration
            self._stop_track_preview(pitch)
    
    def set_playhead_position(self, position: int):
        """Set playhead position from external source (like playback engine)"""
        self.playhead_position = position
        # print(f"Piano roll playhead updated to: {position}")  # Debug log
        self.update()
    
    def connect_playback_engine(self, engine):
        """Connect to the playback engine signals"""
        self.playback_engine = engine
        if self.playback_engine:
            self.playback_engine.position_changed.connect(self.set_playhead_position)
            self.playback_engine.state_changed.connect(self.set_playing_state)
            print("PianoRollWidget: Connected to playback engine signals.")

    def set_playing_state(self, state: PlaybackState):
        """Set playing state from external source"""
        self.is_playing = (state == PlaybackState.PLAYING)
        self.update()
    
    def _update_playback_engine(self):
        """Update playback engine with current project state"""
        if self.playback_engine and self.midi_project:
            # Preserve current playhead position during update
            self.playback_engine.set_project(self.midi_project, preserve_position=True)
    
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
    
    def _draw_measure_lines_simple(self, painter, ticks_per_beat: int, numerator: int, denominator: int, grid_start_x: int, height: int, end_tick: int):
        """Draw measure lines with a single time signature"""
        # Calculate ticks per measure using centralized method
        if self.midi_project:
            ticks_per_measure = self.midi_project.calculate_ticks_per_measure(numerator, denominator)
        else:
            # Fallback calculation
            if denominator == 8:
                beats_per_measure = numerator / 2
                ticks_per_measure = int(ticks_per_beat * beats_per_measure)
            else:
                beats_per_measure = numerator * (4 / denominator)
                ticks_per_measure = int(ticks_per_beat * beats_per_measure)
        
        # Calculate the range of measures to draw
        start_measure_tick = (self.visible_start_tick // ticks_per_measure) * ticks_per_measure
        
        for tick in range(start_measure_tick, end_tick, ticks_per_measure):
            if tick >= self.visible_start_tick - ticks_per_measure:
                x = self._tick_to_x(tick) + grid_start_x
                if x >= grid_start_x and x <= self.width():
                    painter.setPen(QColor(self.theme_colors.grid_line_measure))
                    painter.drawLine(int(x), 0, int(x), height)
    
    def _draw_measure_lines_with_time_signature_changes(self, painter, ticks_per_beat: int, grid_start_x: int, height: int, end_tick: int):
        """Draw measure lines with time signature changes support"""
        if not self.midi_project or not self.midi_project.time_signature_changes:
            return
            
        time_sig_changes = sorted(self.midi_project.time_signature_changes, key=lambda x: x.tick)
        
        for i, ts_change in enumerate(time_sig_changes):
            next_change_tick = time_sig_changes[i + 1].tick if i + 1 < len(time_sig_changes) else end_tick + 10000
            
            # Calculate ticks per measure for this time signature
            numerator, denominator = ts_change.numerator, ts_change.denominator
            if denominator == 8:
                beats_per_measure = numerator / 2
                ticks_per_measure = int(ticks_per_beat * beats_per_measure)
            else:
                beats_per_measure = numerator * (4 / denominator)
                ticks_per_measure = int(ticks_per_beat * beats_per_measure)
            
            # Draw measures for this time signature section
            section_start_tick = ts_change.tick
            section_end_tick = min(next_change_tick, end_tick)
            
            # Find the first measure boundary at or after section_start_tick
            first_measure_tick = ((section_start_tick + ticks_per_measure - 1) // ticks_per_measure) * ticks_per_measure
            
            # Draw measures in this section
            for tick in range(first_measure_tick, section_end_tick, ticks_per_measure):
                if tick >= self.visible_start_tick - ticks_per_measure:
                    x = self._tick_to_x(tick) + grid_start_x
                    if x >= grid_start_x and x <= self.width():
                        painter.setPen(QColor(self.theme_colors.grid_line_measure))
                        painter.drawLine(int(x), 0, int(x), height)

