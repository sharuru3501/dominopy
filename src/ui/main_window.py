
from PySide6.QtWidgets import (QMainWindow, QFileDialog, QWidget, QHBoxLayout, QToolBar, 
                              QScrollArea, QVBoxLayout, QScrollBar, QDockWidget, QMessageBox)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt, QTimer
from src.ui.piano_roll_widget import PianoRollWidget
from src.ui.status_bar import PyDominoStatusBar
from src.ui.compact_tempo_widget import (CompactTempoWidget, CompactTimeSignatureWidget, 
                                       CompactMusicInfoWidget, CompactPlaybackInfoWidget, 
                                       ToolbarSeparator)
from src.midi_parser import load_midi_file
from src.edit_modes import EditMode
from src.audio_system import initialize_audio_manager, cleanup_audio_manager, AudioSettings
from src.playback_engine import initialize_playback_engine, cleanup_playback_engine, get_playback_engine, PlaybackState
from src.midi_routing import initialize_midi_routing, cleanup_midi_routing, get_midi_routing_manager
from src.track_manager import initialize_track_manager, cleanup_track_manager, get_track_manager
from src.ui.track_list_widget import TrackListWidget

class PyDominoMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
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
        
        # Create container widget with scrollbars
        piano_roll_container = QWidget()
        piano_roll_layout = QVBoxLayout(piano_roll_container)
        piano_roll_layout.setContentsMargins(0, 0, 0, 0)
        
        # Horizontal layout for piano roll and vertical scrollbar
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.addWidget(self.piano_roll)
        
        # Vertical scrollbar
        self.v_scrollbar = QScrollBar(Qt.Vertical)
        self.v_scrollbar.setMinimum(0)
        self.v_scrollbar.setMaximum(118)  # 128 notes - 10 visible notes
        self.v_scrollbar.setValue(0)
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

        # Create status bar (simplified)
        self.status_bar = PyDominoStatusBar()
        self.setStatusBar(self.status_bar)

        self._create_menu_bar()
        self._create_toolbar()
        self._create_music_toolbar()
        
        # Initialize systems (delayed to ensure QApplication is ready)
        QTimer.singleShot(50, self._initialize_audio_system)
        QTimer.singleShot(100, self._initialize_midi_routing)
        QTimer.singleShot(125, self._initialize_track_manager)
        QTimer.singleShot(150, self._initialize_playback_engine)
        QTimer.singleShot(200, self._connect_ui_signals)

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")

        open_action = file_menu.addAction("&Open...")
        open_action.triggered.connect(self._open_midi_file)
        
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
                    print(f"Error loading MIDI file: {e}")
                    # TODO: Show error message to user
    
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
                    print(f"Error updating music info: {e}")
                    # Fallback: just clear the display
                    self.music_info_widget.update_notes([])
            
            print("Settings applied - UI components updated")
            
        except Exception as e:
            print(f"Error in settings applied handler: {e}")
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
            print("Audio system initialized successfully")
        else:
            print("Warning: Audio system initialization failed")
        print(f"_initialize_audio_system() received: {init_result}")
    
    def _initialize_midi_routing(self):
        """Initialize the MIDI routing system"""
        init_result = initialize_midi_routing()
        if init_result:
            print("MIDI routing system initialized successfully")
            
            # Set default routing to internal FluidSynth
            midi_router = get_midi_routing_manager()
            if midi_router:
                midi_router.set_primary_output("internal_fluidsynth")
                print("Default MIDI routing set to internal FluidSynth")
        else:
            print("Warning: MIDI routing system initialization failed")
    
    def _initialize_track_manager(self):
        """Initialize the track manager system"""
        # Initialize with no project initially
        track_manager = initialize_track_manager()
        
        # Connect track list widget to track manager
        self.track_list.set_track_manager(track_manager)
        
        # Connect track selection to piano roll
        self.track_list.track_selected.connect(self._on_track_selected)
        
        print("Track manager initialized successfully")
    
    def _on_track_selected(self, track_index: int):
        """Handle track selection"""
        print(f"Track {track_index} selected")
        # Piano roll will be updated to show only this track's notes
        self.piano_roll.update()  # Refresh display
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Clean up playback engine
        cleanup_playback_engine()
        print("Playback engine cleaned up")
        
        # Clean up MIDI routing system
        cleanup_midi_routing()
        print("MIDI routing system cleaned up")
        
        # Clean up track manager
        cleanup_track_manager()
        print("Track manager cleaned up")
        
        # Clean up audio system
        cleanup_audio_manager()
        print("Audio system cleaned up")
        
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
                print("Test audio: Playing C4")
            else:
                print("Test audio: Failed to play note")
        else:
            print("Test audio: Audio manager not available")
    
    def _open_midi_routing(self):
        """Open MIDI output settings dialog"""
        try:
            from src.ui.midi_output_dialog import MIDIOutputDialog
            dialog = MIDIOutputDialog(self)
            result = dialog.exec()
            
            if result == dialog.Accepted:
                print("MIDI output settings updated")
            
        except Exception as e:
            print(f"Error opening MIDI output dialog: {e}")
            QMessageBox.warning(self, "Error", f"Failed to open MIDI settings:\\n{str(e)}")
    
    def _toggle_playback(self):
        """Toggle between play and pause"""
        print("MainWindow: _toggle_playback called")
        engine = get_playback_engine()
        if engine:
            print(f"MainWindow: Found engine, state: {engine.get_state()}")
            engine.toggle_play_pause()
            print(f"MainWindow: After toggle, state: {engine.get_state()}")
            self._update_playback_buttons()
        else:
            print("MainWindow: No playback engine found!")
    
    def toggle_playback(self):
        """Public method for external access (like piano roll widget)"""
        print("MainWindow: toggle_playback called")
        self._toggle_playback()
    
    def _rewind_playhead(self):
        """Rewind playhead to the beginning (t=0)"""
        print("MainWindow: _rewind_playhead called")
        engine = get_playback_engine()
        if engine:
            engine.seek_to_tick(0)
            print("MainWindow: Seeked to tick 0")
            
            # Update piano roll playhead position
            if hasattr(self, 'piano_roll') and self.piano_roll:
                self.piano_roll.playhead_position = 0
                self.piano_roll.update()
        else:
            print("MainWindow: No playback engine found for rewind!")
    
    def update_chord_display(self, chord_info: str):
        """Update chord display in the top bar"""
        # Update the music info widget if it exists
        if hasattr(self, 'music_info_widget') and self.music_info_widget:
            self.music_info_widget.set_chord_text(chord_info)
        
        # Also update status bar as fallback
        if hasattr(self, 'status_bar') and self.status_bar:
            self.status_bar.showMessage(chord_info, 3000)  # Show for 3 seconds
        
        print(f"Chord Display: {chord_info}")
    
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
        
        print("Playback engine initialized")
    
    def _on_vertical_scroll(self, value):
        """Handle vertical scrollbar changes"""
        # Convert scrollbar value to vertical offset
        self.piano_roll.vertical_offset = value
        self.piano_roll.update()
            
    def _on_horizontal_scroll(self, value):
        """Handle horizontal scrollbar changes"""
        # Convert scrollbar value to horizontal offset in ticks
        self.piano_roll.visible_start_tick = value
        self.piano_roll.update()
            
    def _on_playback_state_changed(self, state: PlaybackState):
        """Handle playback state changes"""
        self._update_playback_buttons()
        print(f"Playback state changed to: {state.value}")
    
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
        
        # Music info display
        self.music_info_widget = CompactMusicInfoWidget()
        music_toolbar.addWidget(self.music_info_widget)
        
        music_toolbar.addWidget(ToolbarSeparator())
        
        # Playback info
        self.playback_info_widget = CompactPlaybackInfoWidget()
        music_toolbar.addWidget(self.playback_info_widget)
        
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
        
        # Set initial project in music info widget
        if hasattr(self.piano_roll, 'midi_project') and self.piano_roll.midi_project:
            self.music_info_widget.set_project(self.piano_roll.midi_project)
# Debug output removed for cleaner logs
        
        print("UI signals connected")
    
    def _on_tempo_changed(self, bpm: float):
        """Handle tempo changes from UI"""
        # Update the current project
        if hasattr(self.piano_roll, 'midi_project') and self.piano_roll.midi_project:
            self.piano_roll.midi_project.set_global_tempo(bpm)
        
        print(f"Tempo changed to {bpm} BPM")
    
    def _on_time_signature_changed(self, numerator: int, denominator: int):
        """Handle time signature changes from UI"""
        # Update the current project
        if hasattr(self.piano_roll, 'midi_project') and self.piano_roll.midi_project:
            self.piano_roll.midi_project.set_global_time_signature(numerator, denominator)
        
        print(f"Time signature changed to {numerator}/{denominator}")
    
    def _update_project_ui(self, midi_project):
        """Update UI elements when a new project is loaded"""
        if midi_project:
            # Update tempo and time signature widgets
            tempo = midi_project.get_current_tempo()
            time_sig = midi_project.get_current_time_signature()
            
            self.tempo_widget.set_tempo(tempo)
            self.time_sig_widget.set_time_signature(time_sig[0], time_sig[1])
            
            print(f"Updated UI: Tempo={tempo} BPM, Time Signature={time_sig[0]}/{time_sig[1]}")
    
    def _update_playback_info(self):
        """Update playback information in toolbar"""
        engine = get_playback_engine()
        if engine:
            state = engine.get_state()
            current_tick = engine.get_current_tick()
            tempo_bpm = engine.get_tempo()
            
            self.playback_info_widget.update_playback_info(state, current_tick, tempo_bpm)
    
    def _create_test_song(self):
        """Create a simple test song for playback verification"""
        from src.midi_data_model import MidiProject, MidiTrack, MidiNote
        
        # Create new project
        project = MidiProject()
        project.ticks_per_beat = 480  # Standard MIDI resolution
        
        # Create a track
        track = MidiTrack(name="Test Track")
        
        # Create a simple melody: C4-E4-G4-C5 progression
        # Each note is one beat (480 ticks) long
        test_notes = [
            MidiNote(pitch=60, start_tick=0, end_tick=480, velocity=100),      # C4 - Beat 1
            MidiNote(pitch=64, start_tick=480, end_tick=960, velocity=100),    # E4 - Beat 2  
            MidiNote(pitch=67, start_tick=960, end_tick=1440, velocity=100),   # G4 - Beat 3
            MidiNote(pitch=72, start_tick=1440, end_tick=1920, velocity=100),  # C5 - Beat 4
            MidiNote(pitch=67, start_tick=1920, end_tick=2400, velocity=100),  # G4 - Beat 5
            MidiNote(pitch=64, start_tick=2400, end_tick=2880, velocity=100),  # E4 - Beat 6
            MidiNote(pitch=60, start_tick=2880, end_tick=3360, velocity=100),  # C4 - Beat 7
        ]
        
        # Add notes to track
        for note in test_notes:
            track.notes.append(note)
        
        # Add track to project
        project.add_track(track)
        
        # Set project in piano roll and playback engine
        self.piano_roll.set_midi_project(project)
        
        # Update playback engine with new project
        engine = get_playback_engine()
        if engine:
            engine.set_project(project)
            print("Test song created and loaded into playback engine")
        
        # Update track manager with new project
        track_manager = get_track_manager()
        if track_manager:
            track_manager.set_project(project)
        
        # Update UI
        self._update_project_ui(project)
        
        print("Test song created: C4-E4-G4-C5-G4-E4-C4 melody")

