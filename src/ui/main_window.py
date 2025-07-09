
from PySide6.QtWidgets import QMainWindow, QFileDialog, QWidget, QHBoxLayout, QToolBar
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt
from src.ui.piano_roll_widget import PianoRollWidget
from src.ui.piano_keyboard_widget import PianoKeyboardWidget
from src.midi_parser import load_midi_file
from src.edit_modes import EditMode
from src.audio_system import initialize_audio_manager, cleanup_audio_manager, AudioSettings

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

        # Piano Keyboard Widget
        self.piano_keyboard = PianoKeyboardWidget(pixels_per_pitch=10) # Pass pixels_per_pitch
        main_layout.addWidget(self.piano_keyboard)

        # Piano Roll Widget
        self.piano_roll = PianoRollWidget()
        main_layout.addWidget(self.piano_roll)

        self.setCentralWidget(central_widget)

        self._create_menu_bar()
        self._create_toolbar()
        
        # Initialize audio system
        self._initialize_audio_system()

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")

        open_action = file_menu.addAction("&Open...")
        open_action.triggered.connect(self._open_midi_file)
        
        # Audio Menu
        audio_menu = menu_bar.addMenu("&Audio")
        
        test_audio_action = audio_menu.addAction("Test Audio (C4)")
        test_audio_action.triggered.connect(self._test_audio)
        
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
                    self.setWindowTitle(f"PyDomino - {file_path}")
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
        
        # Quick access buttons
        toggle_mode_action = QAction("⇄ Toggle Mode", self)
        toggle_mode_action.setShortcut("Tab")
        toggle_mode_action.setToolTip("Toggle Mode (Tab)")
        toggle_mode_action.triggered.connect(self._toggle_mode)
        toolbar.addAction(toggle_mode_action)
        
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
    
    def _toggle_mode(self):
        """Toggle between modes"""
        self.piano_roll.get_edit_mode_manager().toggle_mode()
    
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
        success = initialize_audio_manager(audio_settings)
        if success:
            print("Audio system initialized successfully")
        else:
            print("Warning: Audio system initialization failed")
    
    def closeEvent(self, event):
        """Handle window close event"""
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

