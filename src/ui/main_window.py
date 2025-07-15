
from PySide6.QtWidgets import (QMainWindow, QFileDialog, QWidget, QHBoxLayout, QToolBar, 
                              QScrollArea, QVBoxLayout, QScrollBar, QDockWidget, QMessageBox, QDialog, QApplication, QComboBox, QLabel)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt, QTimer
from src.ui.piano_roll_widget import PianoRollWidget
from src.ui.status_bar import PyDominoStatusBar
from src.logger import get_logger
from src.ui.compact_tempo_widget import (CompactTempoWidget, CompactTimeSignatureWidget, 
                                       CompactMusicInfoWidget, CompactPlaybackInfoWidget, 
                                       ToolbarSeparator)
from src.midi_parser import load_midi_file, save_midi_file
from src.edit_modes import EditMode
from src.audio_system import initialize_audio_manager, cleanup_audio_manager, AudioSettings
from src.playback_engine import initialize_playback_engine, cleanup_playback_engine, get_playback_engine, PlaybackState
from src.midi_routing import initialize_midi_routing, cleanup_midi_routing, get_midi_routing_manager
from src.track_manager import initialize_track_manager, cleanup_track_manager, get_track_manager
from src.audio_source_manager import initialize_audio_source_manager, cleanup_audio_source_manager
from src.per_track_audio_router import initialize_per_track_audio_router, cleanup_per_track_audio_router
from src.ui.track_list_widget import TrackListWidget
from src.ui.virtual_keyboard_widget import VirtualKeyboardWidget
from src.ui.measure_bar_widget import MeasureBarWidget
from src.ui.grid_subdivision_widget import GridSubdivisionWidget
from src.logger import get_logger, print_debug

class PyDominoMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)
        self.setWindowTitle("PyDomino")
        self.setGeometry(100, 100, 800, 600) # x, y, width, height

        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0) # Remove margins
        main_layout.setSpacing(0) # Remove spacing between widgets

        # Track List Widget (left side)
        self.track_list = TrackListWidget()
        main_layout.addWidget(self.track_list)

        # Piano Roll Widget with custom scrollbars
        self.piano_roll = PianoRollWidget()
        
        # Create measure bar widget
        self.measure_bar = MeasureBarWidget()
        
        # Create container widget with scrollbars
        piano_roll_container = QWidget()
        piano_roll_layout = QVBoxLayout(piano_roll_container)
        piano_roll_layout.setContentsMargins(0, 0, 0, 0)
        piano_roll_layout.setSpacing(0)  # Remove spacing between widgets
        
        # Add measure bar at the top
        measure_bar_layout = QHBoxLayout()
        measure_bar_layout.setContentsMargins(0, 0, 0, 0)
        measure_bar_layout.setSpacing(0)  # Remove spacing
        # Add spacer to align with piano roll (account for track list width)
        measure_bar_layout.addWidget(self.measure_bar)
        piano_roll_layout.addLayout(measure_bar_layout)
        
        # Horizontal layout for piano roll and vertical scrollbar
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)  # Remove spacing
        h_layout.addWidget(self.piano_roll)
        
        # Vertical scrollbar (C-1 to B9 extended range)
        self.v_scrollbar = QScrollBar(Qt.Vertical)
        self.v_scrollbar.setMinimum(0)   # C-1 (MIDI note 0) - for keyswitches
        self.v_scrollbar.setMaximum(107) # Allow scrolling to show B9 (MIDI 119 - 12 visible notes)
        self.v_scrollbar.setValue(60)    # Start around middle C (C4)
        self.v_scrollbar.valueChanged.connect(self._on_vertical_scroll)
        h_layout.addWidget(self.v_scrollbar)
        
        piano_roll_layout.addLayout(h_layout)
        
        # Horizontal scrollbar
        self.h_scrollbar = QScrollBar(Qt.Horizontal)
        self.h_scrollbar.setMinimum(0)
        self.h_scrollbar.setMaximum(32000)  # Large value for wide scrolling
        self.h_scrollbar.setValue(0)
        self.h_scrollbar.valueChanged.connect(self._on_horizontal_scroll)
        piano_roll_layout.addWidget(self.h_scrollbar)
        
        main_layout.addWidget(piano_roll_container)
        
        # Connect scrollbars to piano roll widget
        self.piano_roll.h_scrollbar = self.h_scrollbar
        self.piano_roll.v_scrollbar = self.v_scrollbar

        self.setCentralWidget(central_widget)
        
        # Center the view on C4 after widget is properly sized
        QTimer.singleShot(100, self._center_on_c4)

        # Create status bar (simplified)
        self.status_bar = PyDominoStatusBar()
        self.setStatusBar(self.status_bar)

        self._create_menu_bar()
        self._create_toolbar()
        self._create_music_toolbar()
        
        # Initialize systems (delayed to ensure QApplication is ready)
        QTimer.singleShot(50, self._initialize_audio_system)
        QTimer.singleShot(75, self._initialize_audio_source_manager)
        QTimer.singleShot(90, self._initialize_per_track_router)
        QTimer.singleShot(100, self._initialize_midi_routing)
        QTimer.singleShot(125, self._initialize_track_manager)
        QTimer.singleShot(150, self._initialize_playback_engine)
        QTimer.singleShot(175, self._initialize_virtual_keyboard)
        QTimer.singleShot(200, self._connect_ui_signals)
        QTimer.singleShot(250, self._initial_measure_bar_sync)

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")

        open_action = file_menu.addAction("&Open...")
        open_action.triggered.connect(self._open_midi_file)
        
        file_menu.addSeparator()
        
        save_action = file_menu.addAction("&Save As...")
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_midi_file)
        
        export_action = file_menu.addAction("&Export MIDI...")
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._export_midi_file)
        
        file_menu.addSeparator()
        
        # Add test MIDI data creation
        create_test_action = file_menu.addAction("Create &Test Song")
        create_test_action.setToolTip("Create a simple test song for playback testing")
        create_test_action.triggered.connect(self._create_test_song)
        
        # Audio Menu
        audio_menu = menu_bar.addMenu("&Audio")
        
        test_audio_action = audio_menu.addAction("Test Audio (C4)")
        test_audio_action.triggered.connect(self._test_audio)
        
        audio_menu.addSeparator()
        
        midi_routing_action = audio_menu.addAction("&MIDI Routing...")
        midi_routing_action.setToolTip("Configure MIDI output routing and external connections")
        midi_routing_action.triggered.connect(self._open_midi_routing)
        
        audio_menu.addSeparator()
        
        virtual_keyboard_action = audio_menu.addAction("&Virtual Keyboard")
        virtual_keyboard_action.setShortcut("Ctrl+K")  # Use Ctrl+K (Cmd+K on Mac)
        virtual_keyboard_action.setToolTip("Open virtual keyboard for playing notes (Ctrl+K)")
        virtual_keyboard_action.triggered.connect(self._toggle_virtual_keyboard)
        
        # Playback Menu
        playback_menu = menu_bar.addMenu("&Playback")
        
        rewind_action = playback_menu.addAction("&Rewind to Start")
        rewind_action.setShortcut("Return")
        rewind_action.setToolTip("Rewind playhead to the beginning (t=0)")
        rewind_action.triggered.connect(self._rewind_playhead)
        
        playback_menu.addSeparator()
        
        play_pause_action = playback_menu.addAction("&Play/Pause")
        play_pause_action.setToolTip("Toggle playback (Space key)")
        play_pause_action.triggered.connect(self._toggle_playback)
        
        # Edit Menu
        edit_menu = menu_bar.addMenu("&Edit")
        
        undo_action = edit_menu.addAction("&Undo")
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self._undo)
        
        redo_action = edit_menu.addAction("&Redo")
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self._redo)
        
        edit_menu.addSeparator()
        
        copy_action = edit_menu.addAction("&Copy")
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self._copy)
        
        cut_action = edit_menu.addAction("Cu&t")
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(self._cut)
        
        paste_action = edit_menu.addAction("&Paste")
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self._paste)
        
        edit_menu.addSeparator()
        
        select_all_action = edit_menu.addAction("Select &All")
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self._select_all)
        
        
        # Settings Menu
        settings_menu = menu_bar.addMenu("&Settings")
        
        preferences_action = settings_menu.addAction("&Preferences...")
        preferences_action.setShortcut("Ctrl+Comma")
        preferences_action.triggered.connect(self._open_settings)
    
    def _center_on_c4(self):
        """Center the piano roll view on C4 (MIDI note 60)"""
        try:
            # Get piano roll widget height
            piano_roll_height = self.piano_roll.height()
            if piano_roll_height <= 0:
                # Widget not ready yet, try again later
                QTimer.singleShot(200, self._center_on_c4)
                return
            
            # Calculate how many pitches are visible in the current view
            pixels_per_pitch = self.piano_roll.pixels_per_pitch
            visible_pitches = piano_roll_height / pixels_per_pitch
            
            # Calculate the scroll position to center C4 (MIDI note 60)
            # We want C4 to be in the middle of the visible area
            c4_midi = 60
            center_position = c4_midi - (visible_pitches / 2)
            
            # Clamp to valid range (0 to 107)
            center_position = max(0, min(107, int(center_position)))
            
            # Set the scrollbar to center C4
            self.v_scrollbar.setValue(center_position)
            print_debug(f"Centered view on C4: scroll position {center_position}, visible pitches: {visible_pitches:.1f}")
            
        except Exception as e:
            print(f"Error centering on C4: {e}")

    def _open_midi_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("MIDI Files (*.mid *.midi)")
        file_dialog.setWindowTitle("Open MIDI File")

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                try:
                    midi_project = load_midi_file(file_path)
                    self.piano_roll.set_midi_project(midi_project)
                    
                    # Set project in playback engine
                    engine = get_playback_engine()
                    if engine:
                        engine.set_project(midi_project)
                    
                    # Set project in track manager
                    track_manager = get_track_manager()
                    if track_manager:
                        track_manager.set_project(midi_project)
                    
                    # Update UI with project settings
                    self._update_project_ui(midi_project)
                    
                    # Set project in music info widget
                    self.music_info_widget.set_project(midi_project)
                    
                    # Update horizontal scrollbar maximum based on project length
                    self.h_scrollbar.setMaximum(self.piano_roll.visible_end_tick)
                    self.h_scrollbar.setValue(0) # Reset horizontal scroll to beginning
                    
                    self.setWindowTitle(f"PyDomino - {file_path}")
                    self.status_bar.update_project_name(file_path.split('/')[-1])
                except Exception as e:
                    self.logger.info(f"Error loading MIDI file: {e}")
                    # TODO: Show error message to user
    
    def _save_midi_file(self):
        """Save current project as MIDI file"""
        if not self.piano_roll.midi_project:
            QMessageBox.warning(self, "No Project", "No project loaded to save.")
            return
        
        file_dialog = QFileDialog(self)
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        file_dialog.setNameFilter("MIDI Files (*.mid)")
        file_dialog.setDefaultSuffix("mid")
        file_dialog.setWindowTitle("Save MIDI File")
        
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                try:
                    success = save_midi_file(self.piano_roll.midi_project, file_path)
                    if success:
                        self.setWindowTitle(f"PyDomino - {file_path}")
                        self.status_bar.update_project_name(file_path.split('/')[-1])
                        self.status_bar.showMessage(f"Project saved as {file_path}", 3000)
                    else:
                        QMessageBox.critical(self, "Save Error", f"Failed to save MIDI file to {file_path}")
                except Exception as e:
                    print(f"Error saving MIDI file: {e}")
                    QMessageBox.critical(self, "Save Error", f"Error saving MIDI file: {str(e)}")
    
    def _export_midi_file(self):
        """Export current project as MIDI file (same as save for now)"""
        self._save_midi_file()
    
    def _undo(self):
        """Undo last operation"""
        self.piano_roll._undo()
    
    def _redo(self):
        """Redo last undone operation"""
        self.piano_roll._redo()
    
    def _copy(self):
        """Copy selected notes"""
        self.piano_roll._copy_selected_notes()
    
    def _cut(self):
        """Cut selected notes"""
        self.piano_roll._cut_selected_notes()
    
    def _paste(self):
        """Paste notes from clipboard"""
        self.piano_roll._paste_notes()
    
    def _select_all(self):
        """Select all notes"""
        self.piano_roll._select_all()
    
    def _open_settings(self):
        """Open settings dialog"""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self)
        dialog.settings_applied.connect(self._on_settings_applied)
        dialog.exec()
    
    def _on_settings_applied(self):
        """Handle settings being applied"""
        try:
            # Update piano roll display
            if hasattr(self, 'piano_roll') and self.piano_roll:
                self.piano_roll.update_display_settings()
            
            # Force update music info widget with current playhead position
            if (hasattr(self, 'music_info_widget') and self.music_info_widget and 
                hasattr(self, 'piano_roll') and self.piano_roll and 
                hasattr(self.piano_roll, 'midi_project') and self.piano_roll.midi_project):
                
                # Get notes at current playhead position safely
                playhead_tick = getattr(self.piano_roll, 'playhead_tick', 0)
                try:
                    notes_at_position = self.piano_roll.midi_project.get_notes_at_tick(playhead_tick)
                    if notes_at_position:
                        pitches = [note.pitch for note in notes_at_position]
                        self.music_info_widget.update_notes(pitches)
                    else:
                        self.music_info_widget.update_notes([])
                except Exception as e:
                    self.logger.info(f"Error updating music info: {e}")
                    # Fallback: just clear the display
                    self.music_info_widget.update_notes([])
            
            print_debug("Settings applied - UI components updated")
            
        except Exception as e:
            self.logger.info(f"Error in settings applied handler: {e}")
            import traceback
            traceback.print_exc()
    
    def _create_toolbar(self):
        """Create the toolbar with mode switching buttons"""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        # Note input mode button
        note_input_action = QAction("🎵 Note Input", self)
        note_input_action.setCheckable(True)
        note_input_action.setChecked(True)  # Default mode
        note_input_action.setShortcut("1")
        note_input_action.setToolTip("Note Input Mode (1)\nClick to create notes, drag to move/resize")
        note_input_action.triggered.connect(self._set_note_input_mode)
        
        # Selection mode button
        selection_action = QAction("📐 Selection", self)
        selection_action.setCheckable(True)
        selection_action.setShortcut("2")
        selection_action.setToolTip("Selection Mode (2)\nClick and drag to select notes")
        selection_action.triggered.connect(self._set_selection_mode)
        
        # Add actions to toolbar
        toolbar.addAction(note_input_action)
        toolbar.addAction(selection_action)
        
        toolbar.addSeparator()
        
        # Playback control buttons
        self.play_action = QAction("▶️ Play", self)
        self.play_action.setShortcut("Space")
        self.play_action.setToolTip("Play/Pause (Space)")
        self.play_action.triggered.connect(self._toggle_playback)
        toolbar.addAction(self.play_action)
        
        self.stop_action = QAction("⏹️ Stop", self)
        self.stop_action.setToolTip("Stop Playback")
        self.stop_action.triggered.connect(self._stop_playback)
        toolbar.addAction(self.stop_action)
        
        self.rewind_action = QAction("⏮️ Rewind", self)
        self.rewind_action.setToolTip("Return to Beginning")
        self.rewind_action.triggered.connect(self._rewind_playback)
        toolbar.addAction(self.rewind_action)
        
        toolbar.addSeparator()
        
        # Theme switching dropdown
        theme_label = QLabel("Theme:")
        toolbar.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        
        # Set current theme from settings
        from src.settings import get_settings_manager
        settings_manager = get_settings_manager()
        current_theme = settings_manager.settings.display.theme
        self.theme_combo.setCurrentText("Light" if current_theme == "light" else "Dark")
        
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        toolbar.addWidget(self.theme_combo)
        
        # Keep the rest of toolbar actions minimal
        
        # Store references for later use
        self.note_input_action = note_input_action
        self.selection_action = selection_action
        
        # Connect to mode changes
        self.piano_roll.get_edit_mode_manager().mode_changed.connect(self._on_mode_changed)
    
    def _set_note_input_mode(self):
        """Set note input mode"""
        if not self.note_input_action.isChecked():
            self.note_input_action.setChecked(True)
            return
        self.piano_roll.get_edit_mode_manager().set_mode(EditMode.NOTE_INPUT)
    
    def _set_selection_mode(self):
        """Set selection mode"""
        if not self.selection_action.isChecked():
            self.selection_action.setChecked(True)
            return
        self.piano_roll.get_edit_mode_manager().set_mode(EditMode.SELECTION)
    
    def _on_mode_changed(self, mode: EditMode):
        """Handle mode change to update toolbar buttons"""
        # Block signals to prevent recursion
        self.note_input_action.blockSignals(True)
        self.selection_action.blockSignals(True)
        
        if mode == EditMode.NOTE_INPUT:
            self.note_input_action.setChecked(True)
            self.selection_action.setChecked(False)
        elif mode == EditMode.SELECTION:
            self.note_input_action.setChecked(False)
            self.selection_action.setChecked(True)
        
        # Re-enable signals
        self.note_input_action.blockSignals(False)
        self.selection_action.blockSignals(False)
    
    def _on_theme_changed(self, theme_name: str):
        """Handle theme change from toolbar dropdown"""
        self.piano_roll.set_theme(theme_name.lower())
    
    def _initialize_audio_system(self):
        """Initialize the audio system"""
        import os
        
        # Create audio settings
        soundfont_path = os.path.join(os.path.dirname(__file__), '..', '..', 'soundfonts', 'MuseScore_General.sf2')
        soundfont_path = os.path.abspath(soundfont_path)
        
        audio_settings = AudioSettings(
            sample_rate=44100,
            buffer_size=1024,
            gain=0.5,
            soundfont_path=soundfont_path if os.path.exists(soundfont_path) else None,
            midi_device_id=None   # Will use default MIDI device
        )
        
        # Initialize audio manager
        init_result = initialize_audio_manager(audio_settings)
        if init_result:
            print_debug("Audio system initialized successfully")
        else:
            print_debug("Warning: Audio system initialization failed")
        print_debug(f"_initialize_audio_system() received: {init_result}")
    
    def _initialize_audio_source_manager(self):
        """Initialize the audio source manager"""
        import os
        
        # Get soundfont directory path
        soundfont_directory = os.path.join(os.path.dirname(__file__), '..', '..', 'soundfonts')
        soundfont_directory = os.path.abspath(soundfont_directory)
        
        # Initialize audio source manager
        audio_source_manager = initialize_audio_source_manager(soundfont_directory)
        
        self.logger.info(f"Audio source manager initialized with {len(audio_source_manager.get_available_sources())} sources")
        self.logger.info(f"  Soundfonts: {len(audio_source_manager.get_soundfont_sources())}")
        self.logger.info(f"  MIDI devices: {len(audio_source_manager.get_midi_sources())}")
    
    def _initialize_per_track_router(self):
        """Initialize the per-track audio router"""
        router = initialize_per_track_audio_router()
        
        # Ensure manager references are updated
        router._update_manager_references()
        
        # Initialize default track assignments
        if router.audio_source_manager:
            router.audio_source_manager.validate_track_assignments(8)
        
        self.logger.info("Per-track audio router initialized")
    
    def _initialize_virtual_keyboard(self):
        """Initialize the virtual keyboard"""
        self.virtual_keyboard = VirtualKeyboardWidget(self)
        
        # Connect virtual keyboard signals to audio system
        self.virtual_keyboard.note_pressed.connect(self._on_virtual_key_pressed)
        self.virtual_keyboard.note_released.connect(self._on_virtual_key_released)
        
        # Update virtual keyboard with current track info
        self._update_virtual_keyboard_track_info()
        
        self.logger.info("Virtual keyboard initialized")
    
    def _initialize_midi_routing(self):
        """Initialize the MIDI routing system"""
        init_result = initialize_midi_routing()
        if init_result:
            self.logger.info("MIDI routing system initialized successfully")
            
            # Set default routing to internal FluidSynth
            midi_router = get_midi_routing_manager()
            if midi_router:
                midi_router.set_primary_output("internal_fluidsynth")
                self.logger.info("Default MIDI routing set to internal FluidSynth")
        else:
            self.logger.info("Warning: MIDI routing system initialization failed")
    
    def _initialize_track_manager(self):
        """Initialize the track manager system"""
        # Create default project with 8 Domino-style tracks
        from src.midi_data_model import MidiProject
        default_project = MidiProject()
        default_project.ticks_per_beat = 480  # Standard MIDI resolution
        
        # Initialize track manager with default project
        track_manager = initialize_track_manager(default_project)
        
        # Connect track list widget to track manager
        self.track_list.set_track_manager(track_manager)
        
        # Connect track selection to piano roll
        self.track_list.track_selected.connect(self._on_track_selected)
        
        # Set the default project in piano roll
        self.piano_roll.set_midi_project(default_project)
        
        # Initialize unified audio routing coordinator (delayed to ensure all managers are ready)
        QTimer.singleShot(300, self._initialize_unified_audio_routing)
        
        print("Track manager initialized with 8 default tracks")
    
    def _initialize_unified_audio_routing(self):
        """Initialize unified audio routing coordinator (called with delay to ensure managers are ready)"""
        from src.audio_routing_coordinator import initialize_audio_routing_coordinator
        
        print("Initializing unified audio routing coordinator...")
        coordinator = initialize_audio_routing_coordinator()
        
        if coordinator and coordinator.state.value == "ready":
            # Set up routes for all tracks
            success_count = 0
            for track_index in range(8):
                if coordinator.setup_track_route(track_index):
                    success_count += 1
            
            print(f"Unified audio routing: initialized routes for {success_count}/8 tracks")
            
            # Print system status
            status = coordinator.get_system_status()
            print(f"Audio routing coordinator status: {status}")
        else:
            print("Warning: Unified audio routing coordinator not available or failed to initialize")
    
    def _initialize_track_audio(self):
        """Legacy track audio initialization (deprecated - kept for compatibility)"""
        from src.per_track_audio_router import get_per_track_audio_router
        per_track_router = get_per_track_audio_router()
        if per_track_router:
            print("Initializing audio for all tracks (legacy method)...")
            success_count = per_track_router.initialize_all_tracks(8)
            print(f"Track manager: initialized audio for {success_count}/8 tracks")
        else:
            print("Warning: Per-track audio router not available")
    
    def _on_track_selected(self, track_index: int):
        """Handle track selection"""
        self.logger.info(f"Track {track_index} selected")
        # Piano roll will be updated to show only this track's notes
        self.piano_roll.update()  # Refresh display
        
        # Update virtual keyboard track info
        self._update_virtual_keyboard_track_info()
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Clean up playback engine
        cleanup_playback_engine()
        self.logger.info("Playback engine cleaned up")
        
        # Clean up MIDI routing system
        cleanup_midi_routing()
        self.logger.info("MIDI routing system cleaned up")
        
        # Clean up track manager
        cleanup_track_manager()
        self.logger.info("Track manager cleaned up")
        
        # Clean up per-track audio router
        cleanup_per_track_audio_router()
        self.logger.info("Per-track audio router cleaned up")
        
        # Clean up audio source manager
        cleanup_audio_source_manager()
        self.logger.info("Audio source manager cleaned up")
        
        # Clean up virtual keyboard
        if hasattr(self, 'virtual_keyboard') and self.virtual_keyboard:
            self.virtual_keyboard.close()
            self.logger.info("Virtual keyboard cleaned up")
        
        # Clean up audio system
        cleanup_audio_manager()
        self.logger.info("Audio system cleaned up")
        
        # Accept the close event
        event.accept()
    
    def _test_audio(self):
        """Test audio by playing C4 note"""
        from src.audio_system import get_audio_manager
        
        audio_manager = get_audio_manager()
        if audio_manager:
            # Play C4 (MIDI note 60)
            success = audio_manager.play_note_preview(60, 100)
            if success:
                self.logger.info("Test audio: Playing C4")
            else:
                self.logger.info("Test audio: Failed to play note")
        else:
            self.logger.info("Test audio: Audio manager not available")
    
    def _open_midi_routing(self):
        """Open MIDI output settings dialog"""
        try:
            from src.ui.midi_output_dialog import MIDIOutputDialog
            dialog = MIDIOutputDialog(self)
            result = dialog.exec()
            
            if result == QDialog.Accepted:
                self.logger.info("MIDI output settings updated")
            
        except Exception as e:
            self.logger.info(f"Error opening MIDI output dialog: {e}")
            QMessageBox.warning(self, "Error", f"Failed to open MIDI settings:\\n{str(e)}")
    
    def _toggle_virtual_keyboard(self):
        """Toggle virtual keyboard visibility"""
        if hasattr(self, 'virtual_keyboard') and self.virtual_keyboard:
            if self.virtual_keyboard.isVisible():
                self.virtual_keyboard.hide()
            else:
                self.virtual_keyboard.show()
                self.virtual_keyboard.raise_()
                self.virtual_keyboard.activateWindow()
                # Update track info when showing
                self._update_virtual_keyboard_track_info()
        else:
            self.logger.info("Virtual keyboard not initialized")
    
    def _on_virtual_key_pressed(self, pitch: int, velocity: int):
        """Handle virtual keyboard key press"""
        from src.track_manager import get_track_manager
        from src.per_track_audio_router import get_per_track_audio_router
        from src.midi_data_model import MidiNote
        
        # Get current active track
        track_manager = get_track_manager()
        if track_manager:
            active_track_index = track_manager.get_active_track_index()
            self.logger.info(f"Virtual keyboard: Active track index: {active_track_index}")
            
            # Try per-track audio routing
            per_track_router = get_per_track_audio_router()
            if per_track_router:
                # Check track audio source
                from src.audio_source_manager import get_audio_source_manager
                audio_source_manager = get_audio_source_manager()
                if audio_source_manager:
                    track_source = audio_source_manager.get_track_source(active_track_index)
                    if track_source:
                        self.logger.info(f"Virtual keyboard: Track {active_track_index} source: {track_source.name} (type: {track_source.source_type})")
                    else:
                        self.logger.info(f"Virtual keyboard: No audio source assigned to track {active_track_index}")
                
                # Create a note for the virtual keyboard
                virtual_note = MidiNote(
                    pitch=pitch,
                    start_tick=0,
                    end_tick=100,  # Short duration
                    velocity=velocity,
                    channel=active_track_index % 16
                )
                
                self.logger.info(f"Virtual keyboard: Calling per_track_router.play_note({active_track_index}, pitch={pitch})")
                success = per_track_router.play_note(active_track_index, virtual_note)
                self.logger.info(f"Virtual keyboard: per_track_router.play_note returned: {success}")
                if success:
                    self.logger.info(f"Virtual keyboard: Playing pitch {pitch} on track {active_track_index}")
                    return
        
        # No per-track routing available - respect MIDI routing settings
        self.logger.info(f"Virtual keyboard: No per-track routing available for pitch {pitch}")
    
    def _on_virtual_key_released(self, pitch: int):
        """Handle virtual keyboard key release"""
        from src.track_manager import get_track_manager
        from src.per_track_audio_router import get_per_track_audio_router
        from src.midi_data_model import MidiNote
        
        # Get current active track
        track_manager = get_track_manager()
        if track_manager:
            active_track_index = track_manager.get_active_track_index()
            
            # Try per-track audio routing
            per_track_router = get_per_track_audio_router()
            if per_track_router:
                # Create a note for the virtual keyboard
                virtual_note = MidiNote(
                    pitch=pitch,
                    start_tick=0,
                    end_tick=100,
                    velocity=100,
                    channel=active_track_index % 16
                )
                
                success = per_track_router.stop_note(active_track_index, virtual_note)
                if success:
                    self.logger.info(f"Virtual keyboard: Stopped pitch {pitch} on track {active_track_index}")
                    return
        
        # No per-track routing available - respect MIDI routing settings
        self.logger.info(f"Virtual keyboard: No per-track routing available to stop pitch {pitch}")
    
    def _update_virtual_keyboard_track_info(self):
        """Update virtual keyboard with current track information"""
        if not hasattr(self, 'virtual_keyboard') or not self.virtual_keyboard:
            return
            
        from src.track_manager import get_track_manager
        from src.audio_source_manager import get_audio_source_manager
        
        track_manager = get_track_manager()
        audio_source_manager = get_audio_source_manager()
        
        if track_manager and audio_source_manager:
            active_track_index = track_manager.get_active_track_index()
            track_name = track_manager.get_track_name(active_track_index)
            audio_source = audio_source_manager.get_track_source(active_track_index)
            source_name = audio_source.name if audio_source else "Unknown"
            
            self.virtual_keyboard.update_track_info(track_name, source_name)
    
    def _toggle_playback(self):
        """Toggle between play and pause"""
        self.logger.info("MainWindow: _toggle_playback called")
        engine = get_playback_engine()
        if engine:
            self.logger.info(f"MainWindow: Found engine, state: {engine.get_state()}")
            engine.toggle_play_pause()
            self.logger.info(f"MainWindow: After toggle, state: {engine.get_state()}")
            self._update_playback_buttons()
        else:
            self.logger.info("MainWindow: No playback engine found!")
    
    def toggle_playback(self):
        """Public method for external access (like piano roll widget)"""
        self.logger.info("MainWindow: toggle_playback called")
        self._toggle_playback()
    
    def _rewind_playhead(self):
        """Rewind playhead to the beginning (t=0)"""
        self.logger.info("MainWindow: _rewind_playhead called")
        engine = get_playback_engine()
        if engine:
            engine.seek_to_tick(0)
            self.logger.info("MainWindow: Seeked to tick 0")
            
            # Update piano roll playhead position
            if hasattr(self, 'piano_roll') and self.piano_roll:
                self.piano_roll.playhead_position = 0
                self.piano_roll.update()
        else:
            self.logger.info("MainWindow: No playback engine found for rewind!")
    
    def update_chord_display(self, chord_info: str):
        """Update chord display in the top bar"""
        # Update the music info widget if it exists
        if hasattr(self, 'music_info_widget') and self.music_info_widget:
            self.music_info_widget.set_chord_text(chord_info)
        
        # Also update status bar as fallback
        if hasattr(self, 'status_bar') and self.status_bar:
            self.status_bar.showMessage(chord_info, 3000)  # Show for 3 seconds
        
        self.logger.info(f"Chord Display: {chord_info}")
    
    def _stop_playback(self):
        """Stop playback"""
        engine = get_playback_engine()
        if engine:
            engine.stop()
            self._update_playback_buttons()
    
    def _rewind_playback(self):
        """Rewind to beginning"""
        engine = get_playback_engine()
        if engine:
            engine.seek_to_beginning()
            self._update_playback_buttons()
    
    def _update_playback_buttons(self):
        """Update playback button states"""
        engine = get_playback_engine()
        if engine:
            state = engine.get_state()
            if state == PlaybackState.PLAYING:
                self.play_action.setText("⏸️ Pause")
                self.play_action.setToolTip("Pause (Space)")
            else:
                self.play_action.setText("▶️ Play")
                self.play_action.setToolTip("Play (Space)")
    
    def _initialize_playback_engine(self):
        """Initialize the playback engine"""
        engine = initialize_playback_engine()
        
        # Connect to playback state changes
        engine.state_changed.connect(self._on_playback_state_changed)
        
        # Connect piano roll to playback engine
        self.piano_roll.connect_playback_engine(engine)
        
        self.logger.info("Playback engine initialized")
    
    def _on_vertical_scroll(self, value):
        """Handle vertical scrollbar changes"""
        # Convert scrollbar value (pitch) to vertical offset (pixels)
        # value represents the lowest visible pitch
        # We need to convert this to pixel offset
        self.piano_roll.vertical_offset = value * self.piano_roll.pixels_per_pitch
        self.piano_roll.update()
            
    def _on_horizontal_scroll(self, value):
        """Handle horizontal scrollbar changes"""
        # Convert scrollbar value to horizontal offset in ticks
        self.piano_roll.visible_start_tick = value
        
        # Calculate visible end tick based on current window width
        grid_start_x = self.piano_roll.piano_width if self.piano_roll.show_piano_keyboard else 0
        visible_width = self.piano_roll.width() - grid_start_x
        visible_end_tick = self.piano_roll.visible_start_tick + int(visible_width / self.piano_roll.pixels_per_tick)
        
        # Check if we need to extend range when scrolling near the end
        self.piano_roll.extend_range_if_needed(visible_end_tick)
        
        # Synchronize measure bar with piano roll scrolling (do this before update)
        try:
            self.measure_bar.sync_with_piano_roll(
                self.piano_roll.visible_start_tick,
                visible_end_tick,
                self.piano_roll.pixels_per_tick
            )
        except Exception as e:
            print(f"Warning: Measure bar sync failed: {e}")
        
        self.piano_roll.update()
            
    def _on_playback_state_changed(self, state: PlaybackState):
        """Handle playback state changes"""
        self._update_playback_buttons()
        self.logger.info(f"Playback state changed to: {state.value}")
    
    def _create_music_toolbar(self):
        """Create music information and control toolbar"""
        music_toolbar = QToolBar("Music Controls", self)
        music_toolbar.setObjectName("MusicToolbar")
        music_toolbar.setMovable(True)
        
        # Tempo control
        self.tempo_widget = CompactTempoWidget()
        music_toolbar.addWidget(self.tempo_widget)
        
        music_toolbar.addWidget(ToolbarSeparator())
        
        # Time signature control
        self.time_sig_widget = CompactTimeSignatureWidget()
        music_toolbar.addWidget(self.time_sig_widget)
        
        music_toolbar.addWidget(ToolbarSeparator())
        
        # Grid subdivision control (moved to music info position)
        self.grid_subdivision_widget = GridSubdivisionWidget()
        music_toolbar.addWidget(self.grid_subdivision_widget)
        
        music_toolbar.addWidget(ToolbarSeparator())
        
        # Consolidated music info display (combines note names and chord info)
        self.music_info_widget = CompactMusicInfoWidget()
        music_toolbar.addWidget(self.music_info_widget)
        
        music_toolbar.addWidget(ToolbarSeparator())
        
        # Playback info (for playback state, time position, etc.)
        self.playback_info_widget = CompactPlaybackInfoWidget()
        music_toolbar.addWidget(self.playback_info_widget)
        
        music_toolbar.addWidget(ToolbarSeparator())
        
        # Parameter editing mode selector
        parameter_label = QLabel("Parameter:")
        music_toolbar.addWidget(parameter_label)
        
        self.parameter_combo = QComboBox()
        self.parameter_combo.addItems(["None", "Velocity", "Volume (CC7)", "Expression (CC11)"])
        self.parameter_combo.setToolTip("Select parameter to edit graphically on piano roll")
        self.parameter_combo.currentTextChanged.connect(self._on_parameter_mode_changed)
        music_toolbar.addWidget(self.parameter_combo)
        
        # Add spacer to push everything to the left
        from PySide6.QtWidgets import QWidget as SpacerWidget
        from PySide6.QtWidgets import QSizePolicy
        spacer = SpacerWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        music_toolbar.addWidget(spacer)
        
        # Add toolbar to window
        self.addToolBar(Qt.TopToolBarArea, music_toolbar)
        
        # Setup update timer for playback info
        self.playback_update_timer = QTimer()
        self.playback_update_timer.timeout.connect(self._update_playback_info)
        self.playback_update_timer.start(100)  # Update every 100ms
    
    def _initial_measure_bar_sync(self):
        """Perform initial synchronization of measure bar with piano roll"""
        # Calculate visible end tick based on current window width
        grid_start_x = self.piano_roll.piano_width if self.piano_roll.show_piano_keyboard else 0
        visible_width = self.piano_roll.width() - grid_start_x
        visible_end_tick = self.piano_roll.visible_start_tick + int(visible_width / self.piano_roll.pixels_per_tick)
        
        # Synchronize measure bar with piano roll
        self.measure_bar.sync_with_piano_roll(
            self.piano_roll.visible_start_tick,
            visible_end_tick,
            self.piano_roll.pixels_per_tick
        )
    
    def _connect_ui_signals(self):
        """Connect UI signals after initialization"""
        # Connect tempo widget to project and playback engine
        self.tempo_widget.tempo_changed.connect(self._on_tempo_changed)
        self.time_sig_widget.time_signature_changed.connect(self._on_time_signature_changed)
        
        # Connect piano roll selection changes to music info display
        if hasattr(self.piano_roll, 'selection_changed'):
            self.piano_roll.selection_changed.connect(self.music_info_widget.update_selected_notes)
        
        # Connect piano roll project changes to music info display
        if hasattr(self.piano_roll, 'project_changed'):
            self.piano_roll.project_changed.connect(self.music_info_widget.set_project)
        
        # Connect grid subdivision widget to piano roll
        self.grid_subdivision_widget.subdivision_changed.connect(self._on_grid_subdivision_changed)
        
        # Set initial project in music info widget
        if hasattr(self.piano_roll, 'midi_project') and self.piano_roll.midi_project:
            self.music_info_widget.set_project(self.piano_roll.midi_project)
# Debug output removed for cleaner logs
        
        self.logger.info("UI signals connected")
    
    def _on_tempo_changed(self, bpm: float):
        """Handle tempo changes from UI"""
        # Update the current project
        if hasattr(self.piano_roll, 'midi_project') and self.piano_roll.midi_project:
            self.piano_roll.midi_project.set_global_tempo(bpm)
        
        self.logger.info(f"Tempo changed to {bpm} BPM")
    
    def _on_time_signature_changed(self, numerator: int, denominator: int):
        """Handle time signature changes from UI"""
        # Update the current project
        if hasattr(self.piano_roll, 'midi_project') and self.piano_roll.midi_project:
            self.piano_roll.midi_project.set_global_time_signature(numerator, denominator)
            # Force piano roll to redraw with new time signature
            self.piano_roll.update()
            # Update measure bar as well
            self.measure_bar.update()
        
        self.logger.info(f"Time signature changed to {numerator}/{denominator}")
    
    def _on_parameter_mode_changed(self, selected_text: str):
        """Handle parameter editing mode changes from toolbar dropdown"""
        # Map display text to internal mode names
        mode_mapping = {
            "None": "none",
            "Velocity": "velocity", 
            "Volume (CC7)": "volume",
            "Expression (CC11)": "expression"
        }
        
        internal_mode = mode_mapping.get(selected_text, "none")
        self.piano_roll.set_parameter_edit_mode(internal_mode)
        self.logger.debug(f"Parameter editing mode changed to: {internal_mode}")
    
    def _on_grid_subdivision_changed(self, subdivision_type: str, ticks_per_subdivision: int):
        """Handle grid subdivision changes from subdivision widget"""
        if hasattr(self.piano_roll, 'set_grid_subdivision'):
            self.piano_roll.set_grid_subdivision(subdivision_type, ticks_per_subdivision)
        print(f"Grid subdivision changed to {subdivision_type} ({ticks_per_subdivision} ticks)")
    
    def _update_project_ui(self, midi_project):
        """Update UI elements when a new project is loaded"""
        if midi_project:
            # Update tempo and time signature widgets
            tempo = midi_project.get_current_tempo()
            time_sig = midi_project.get_current_time_signature()
            
            self.tempo_widget.set_tempo(tempo)
            self.time_sig_widget.set_time_signature(time_sig[0], time_sig[1])
            
            # Update measure bar with new project
            self.measure_bar.set_midi_project(midi_project)
            
            self.logger.info(f"Updated UI: Tempo={tempo} BPM, Time Signature={time_sig[0]}/{time_sig[1]}")
    
    def _update_playback_info(self):
        """Update playback information in toolbar"""
        engine = get_playback_engine()
        if engine:
            state = engine.get_state()
            current_tick = engine.get_current_tick()
            tempo_bpm = engine.get_tempo()
            
            self.playback_info_widget.update_playback_info(state, current_tick, tempo_bpm)
    
    def _create_test_song(self):
        """Create a colorful test song to demonstrate track colors"""
        from src.midi_data_model import MidiProject, MidiTrack, MidiNote
        
        # Create new project
        project = MidiProject()
        project.ticks_per_beat = 480  # Standard MIDI resolution
        
        # Update track manager with new project first to get 8 tracks
        track_manager = get_track_manager()
        if track_manager:
            track_manager.set_project(project)
        
        # Now add colorful demo notes to different tracks
        if project.tracks and len(project.tracks) >= 4:
            # Piano track (red) - Main melody
            piano_notes = [
                MidiNote(pitch=60, start_tick=0, end_tick=480, velocity=100, channel=0),      # C4
                MidiNote(pitch=64, start_tick=480, end_tick=960, velocity=100, channel=0),    # E4
                MidiNote(pitch=67, start_tick=960, end_tick=1440, velocity=100, channel=0),   # G4
                MidiNote(pitch=72, start_tick=1440, end_tick=1920, velocity=100, channel=0),  # C5
            ]
            project.tracks[0].notes.extend(piano_notes)
            
            # Strings track (teal) - Harmony
            strings_notes = [
                MidiNote(pitch=48, start_tick=0, end_tick=1920, velocity=80, channel=1),      # Long C3
                MidiNote(pitch=52, start_tick=960, end_tick=2880, velocity=80, channel=1),    # Long E3
            ]
            project.tracks[1].notes.extend(strings_notes)
            
            # Brass track (blue) - Accent notes
            brass_notes = [
                MidiNote(pitch=67, start_tick=1920, end_tick=2400, velocity=110, channel=2),  # G4
                MidiNote(pitch=64, start_tick=2400, end_tick=2880, velocity=110, channel=2),  # E4
                MidiNote(pitch=60, start_tick=2880, end_tick=3360, velocity=110, channel=2),  # C4
            ]
            project.tracks[2].notes.extend(brass_notes)
            
            # Bass track - Low notes
            if len(project.tracks) >= 6:
                bass_notes = [
                    MidiNote(pitch=36, start_tick=0, end_tick=960, velocity=90, channel=5),    # C2
                    MidiNote(pitch=40, start_tick=1920, end_tick=2880, velocity=90, channel=5), # E2
                    MidiNote(pitch=36, start_tick=2880, end_tick=3360, velocity=90, channel=5), # C2
                ]
                project.tracks[5].notes.extend(bass_notes)
        
        # Set project in piano roll
        self.piano_roll.set_midi_project(project)
        
        # Update playback engine with new project
        engine = get_playback_engine()
        if engine:
            engine.set_project(project)
            self.logger.info("Colorful test song created and loaded into playback engine")
        
        # Update UI
        self._update_project_ui(project)
        
        self.logger.info("🎨 Colorful test song created with notes in multiple tracks!")
        self.logger.info("   Track00 (Red): Main melody C4-E4-G4-C5")
        self.logger.info("   Track01 (Teal): Long harmony notes")
        self.logger.info("   Track02 (Blue): Accent notes")
        self.logger.info("   Track05 (Purple): Low bass notes")
    
    def resizeEvent(self, event):
        """Handle window resize events to keep measure bar synchronized"""
        super().resizeEvent(event)
        
        # Update measure bar sync after a brief delay to allow layout updates
        QTimer.singleShot(50, self._initial_measure_bar_sync)

