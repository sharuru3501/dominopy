"""
Audio Source Selection Dialog
Allows users to select audio sources for tracks (soundfonts, external MIDI, etc.)
"""
from typing import Optional, List
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QListWidget, QListWidgetItem, QGroupBox,
                              QButtonGroup, QRadioButton, QTextEdit, QSplitter)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon

from src.audio_source_manager import AudioSource, AudioSourceType, get_audio_source_manager
from src.gm_instruments import get_gm_instrument_name

class AudioSourceDialog(QDialog):
    """Dialog for selecting audio sources for tracks"""
    
    # Signals
    source_selected = Signal(str)  # source_id
    
    def __init__(self, track_index: int, parent=None):
        super().__init__(parent)
        self.track_index = track_index
        self.selected_source_id = None
        self.audio_source_manager = get_audio_source_manager()
        
        self.setWindowTitle(f"Audio Source - Track{track_index:02d}")
        self.setMinimumSize(500, 400)
        
        self.setup_ui()
        self.load_sources()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel(f"Select Audio Source for Track{self.track_index:02d}")
        header_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Main content area
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Left side - Source categories
        self.setup_source_categories(splitter)
        
        # Right side - Source details
        self.setup_source_details(splitter)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("🔄 Refresh")
        self.refresh_button.clicked.connect(self.refresh_sources)
        button_layout.addWidget(self.refresh_button)
        
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.select_button = QPushButton("Select")
        self.select_button.clicked.connect(self.accept_selection)
        self.select_button.setDefault(True)
        button_layout.addWidget(self.select_button)
        
        layout.addLayout(button_layout)
    
    def setup_source_categories(self, splitter):
        """Setup source category selection"""
        category_widget = QVBoxLayout()
        category_container = QGroupBox("Audio Sources")
        category_container.setLayout(category_widget)
        
        # Source type selection
        self.source_type_group = QButtonGroup()
        
        self.internal_radio = QRadioButton("🎵 Internal FluidSynth")
        self.internal_radio.setChecked(True)
        self.internal_radio.toggled.connect(self.on_source_type_changed)
        self.source_type_group.addButton(self.internal_radio, 0)
        category_widget.addWidget(self.internal_radio)
        
        self.soundfont_radio = QRadioButton("🎼 Soundfont Files")
        self.soundfont_radio.toggled.connect(self.on_source_type_changed)
        self.source_type_group.addButton(self.soundfont_radio, 1)
        category_widget.addWidget(self.soundfont_radio)
        
        self.midi_radio = QRadioButton("🔌 External MIDI")
        self.midi_radio.toggled.connect(self.on_source_type_changed)
        self.source_type_group.addButton(self.midi_radio, 2)
        category_widget.addWidget(self.midi_radio)
        
        # Source list
        self.source_list = QListWidget()
        self.source_list.itemSelectionChanged.connect(self.on_source_selection_changed)
        self.source_list.itemDoubleClicked.connect(self.accept_selection)
        category_widget.addWidget(self.source_list)
        
        splitter.addWidget(category_container)
    
    def setup_source_details(self, splitter):
        """Setup source details panel"""
        details_widget = QVBoxLayout()
        details_container = QGroupBox("Source Details")
        details_container.setLayout(details_widget)
        
        # Source name
        self.details_name = QLabel("No source selected")
        self.details_name.setFont(QFont("Arial", 11, QFont.Bold))
        details_widget.addWidget(self.details_name)
        
        # Source type
        self.details_type = QLabel("")
        self.details_type.setStyleSheet("color: #666666;")
        details_widget.addWidget(self.details_type)
        
        # Source information
        self.details_info = QTextEdit()
        self.details_info.setReadOnly(True)
        self.details_info.setMaximumHeight(150)
        details_widget.addWidget(self.details_info)
        
        # GM Instrument selection button (only shown for Internal FluidSynth)
        self.gm_instrument_button = QPushButton("🎹 Select GM Instrument...")
        self.gm_instrument_button.clicked.connect(self._open_gm_instrument_dialog)
        self.gm_instrument_button.hide()  # Hidden by default
        details_widget.addWidget(self.gm_instrument_button)
        
        details_widget.addStretch()
        
        splitter.addWidget(details_container)
        
        # Set splitter proportions
        splitter.setSizes([300, 200])
    
    def load_sources(self):
        """Load available audio sources"""
        if not self.audio_source_manager:
            return
        
        # Get current assignment
        current_source_id = self.audio_source_manager.get_track_source_id(self.track_index)
        
        # Load sources and select current one
        self.refresh_sources()
        self.select_current_source(current_source_id)
    
    def refresh_sources(self):
        """Refresh the list of available sources"""
        if not self.audio_source_manager:
            return
        
        self.audio_source_manager.refresh_sources()
        self.on_source_type_changed()
    
    def on_source_type_changed(self):
        """Handle source type selection change"""
        self.source_list.clear()
        
        if not self.audio_source_manager:
            return
        
        sources = []
        
        if self.internal_radio.isChecked():
            # Internal FluidSynth
            internal_source = self.audio_source_manager.available_sources.get("internal_fluidsynth")
            if internal_source:
                sources = [internal_source]
        elif self.soundfont_radio.isChecked():
            # Soundfont sources
            sources = self.audio_source_manager.get_soundfont_sources()
        elif self.midi_radio.isChecked():
            # External MIDI sources
            sources = self.audio_source_manager.get_midi_sources()
        
        # Populate list
        for source in sources:
            item = QListWidgetItem(source.name)
            item.setData(Qt.UserRole, source.id)
            
            # Add icon based on type
            if source.source_type == AudioSourceType.SOUNDFONT:
                item.setText(f"🎼 {source.name}")
            elif source.source_type == AudioSourceType.EXTERNAL_MIDI:
                item.setText(f"🔌 {source.name}")
            else:
                item.setText(f"🎵 {source.name}")
            
            self.source_list.addItem(item)
    
    def on_source_selection_changed(self):
        """Handle source selection change"""
        current_item = self.source_list.currentItem()
        if not current_item:
            self.update_details(None)
            return
        
        source_id = current_item.data(Qt.UserRole)
        source = self.audio_source_manager.available_sources.get(source_id)
        self.update_details(source)
    
    def update_details(self, source: Optional[AudioSource]):
        """Update the details panel"""
        if not source:
            self.details_name.setText("No source selected")
            self.details_type.setText("")
            self.details_info.setText("")
            self.gm_instrument_button.hide()
            return
        
        self.details_name.setText(source.name)
        
        # Type information
        type_text = {
            AudioSourceType.SOUNDFONT: "Soundfont File (.sf2)",
            AudioSourceType.EXTERNAL_MIDI: "External MIDI Device",
            AudioSourceType.INTERNAL_FLUIDSYNTH: "Internal FluidSynth"
        }.get(source.source_type, "Unknown")
        
        self.details_type.setText(type_text)
        
        # Detailed information
        info_text = f"Source ID: {source.id}\n"
        info_text += f"Type: {source.source_type.value}\n"
        
        if source.file_path:
            import os
            file_size = os.path.getsize(source.file_path) / (1024 * 1024)
            info_text += f"File: {source.file_path}\n"
            info_text += f"Size: {file_size:.1f} MB\n"
        
        if source.midi_port_name:
            info_text += f"MIDI Port: {source.midi_port_name}\n"
        
        info_text += f"Program: {source.program}\n"
        info_text += f"Channel: {source.channel}\n"
        
        if source.source_type == AudioSourceType.SOUNDFONT:
            soundfont_info = self.audio_source_manager.get_soundfont_info(source.file_path)
            if soundfont_info:
                info_text += f"Available Programs: {len(soundfont_info.programs)}\n"
        
        # Show GM instrument information for Internal FluidSynth
        if source.source_type == AudioSourceType.INTERNAL_FLUIDSYNTH:
            gm_instrument_name = get_gm_instrument_name(source.program)
            info_text += f"GM Instrument: {gm_instrument_name}\n"
            self.gm_instrument_button.show()
        else:
            self.gm_instrument_button.hide()
        
        self.details_info.setText(info_text)
    
    def select_current_source(self, source_id: str):
        """Select the current source in the UI"""
        if not self.audio_source_manager:
            return
        
        source = self.audio_source_manager.available_sources.get(source_id)
        if not source:
            return
        
        # Select correct radio button
        if source.source_type == AudioSourceType.SOUNDFONT:
            self.soundfont_radio.setChecked(True)
        elif source.source_type == AudioSourceType.EXTERNAL_MIDI:
            self.midi_radio.setChecked(True)
        else:
            self.internal_radio.setChecked(True)
        
        # Select item in list
        for i in range(self.source_list.count()):
            item = self.source_list.item(i)
            if item.data(Qt.UserRole) == source_id:
                self.source_list.setCurrentItem(item)
                break
    
    def accept_selection(self):
        """Accept the current selection"""
        # Use the stored selected_source_id if it was set by GM instrument selection
        if self.selected_source_id:
            self.source_selected.emit(self.selected_source_id)
            self.accept()
            return
        
        # Fallback to current item selection
        current_item = self.source_list.currentItem()
        if current_item:
            self.selected_source_id = current_item.data(Qt.UserRole)
            self.source_selected.emit(self.selected_source_id)
            self.accept()
    
    def get_selected_source_id(self) -> Optional[str]:
        """Get the selected source ID"""
        return self.selected_source_id
    
    def _open_gm_instrument_dialog(self):
        """Open GM instrument selection dialog"""
        current_item = self.source_list.currentItem()
        if not current_item:
            return
        
        source_id = current_item.data(Qt.UserRole)
        source = self.audio_source_manager.available_sources.get(source_id)
        if not source or source.source_type != AudioSourceType.INTERNAL_FLUIDSYNTH:
            return
        
        from src.ui.gm_instrument_dialog import GMInstrumentDialog
        
        dialog = GMInstrumentDialog(source.program, self)
        dialog.instrument_selected.connect(self._on_gm_instrument_selected)
        dialog.exec()
    
    def _on_gm_instrument_selected(self, program: int):
        """Handle GM instrument selection"""
        current_item = self.source_list.currentItem()
        if not current_item:
            return
        
        source_id = current_item.data(Qt.UserRole)
        source = self.audio_source_manager.available_sources.get(source_id)
        if not source or source.source_type != AudioSourceType.INTERNAL_FLUIDSYNTH:
            return
        
        # Update the track's program setting in TrackManager
        from src.track_manager import get_track_manager
        track_manager = get_track_manager()
        if track_manager:
            success = track_manager.set_track_program(self.track_index, program)
            if success:
                print(f"✅ Updated track {self.track_index} default program to {program}")
            else:
                print(f"❌ Failed to update track {self.track_index} program")
        
        # Invalidate existing audio route to force recreation with new program
        from src.audio_routing_coordinator import get_audio_routing_coordinator
        coordinator = get_audio_routing_coordinator()
        if coordinator:
            coordinator.invalidate_track_route(self.track_index)
            print(f"🔄 Invalidated audio route for track {self.track_index} to apply new instrument")
        
        # Create or update a track-specific internal FluidSynth source
        track_specific_id = f"internal_fluidsynth_ch{self.track_index}"
        
        # Create a track-specific audio source with the selected program
        track_source = AudioSource(
            id=track_specific_id,
            name=f"GM: {get_gm_instrument_name(program)}",
            source_type=AudioSourceType.INTERNAL_FLUIDSYNTH,
            program=program,
            channel=self.track_index % 16
        )
        
        # Store it in available sources for this session
        self.audio_source_manager.available_sources[track_specific_id] = track_source
        print(f"📝 Created track-specific source: {track_specific_id} with program {program}")
        
        # Update the selected source ID to the track-specific one
        self.selected_source_id = track_specific_id
        
        # Update the display
        self.update_details(track_source)
        
        print(f"Track {self.track_index} GM instrument changed to: Program {program} - {get_gm_instrument_name(program)}")