"""
Track List Widget for Multi-Track Support
Displays and manages the list of tracks with color coding
"""
from typing import Optional, List
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QScrollArea, QFrame, QColorDialog,
                              QLineEdit, QMenu, QMessageBox)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QIcon, QFont

from src.track_manager import TrackManager, get_track_manager

class ColorIndicator(QWidget):
    """Small colored square to indicate track color"""
    
    color_clicked = Signal()
    
    def __init__(self, color: str = "#FF6B6B", size: int = 20):
        super().__init__()
        self.color = QColor(color)
        self.size = size
        self.setFixedSize(size, size)
        self.setToolTip("Click to change track color")
        self.setCursor(Qt.PointingHandCursor)
    
    def set_color(self, color: str):
        """Update the color"""
        self.color = QColor(color)
        self.update()
    
    def paintEvent(self, event):
        """Paint the color indicator"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw filled rectangle with border
        painter.setBrush(QBrush(self.color))
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.drawRoundedRect(1, 1, self.size-2, self.size-2, 3, 3)
    
    def mousePressEvent(self, event):
        """Handle mouse click to open color picker"""
        if event.button() == Qt.LeftButton:
            self.color_clicked.emit()

class TrackItemWidget(QFrame):
    """Widget representing a single track in the list"""
    
    track_selected = Signal(int)
    track_renamed = Signal(int, str)
    track_color_changed = Signal(int, str)
    track_removed = Signal(int)
    track_duplicated = Signal(int)
    
    def __init__(self, track_index: int, track_name: str, track_color: str, is_active: bool = False):
        super().__init__()
        self.track_index = track_index
        self.is_active = is_active
        self.track_manager = get_track_manager()
        
        self.setFixedHeight(45)
        self.setFrameStyle(QFrame.Box)
        self.setup_ui(track_name, track_color)
        self.update_style()
    
    def setup_ui(self, track_name: str, track_color: str):
        """Setup the UI components"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Color indicator
        self.color_indicator = ColorIndicator(track_color, 20)
        self.color_indicator.color_clicked.connect(self._open_color_picker)
        layout.addWidget(self.color_indicator)
        
        # Track name (editable label)
        self.name_label = QLabel(track_name)
        self.name_label.setFont(QFont("Arial", 10))
        self.name_label.setMinimumWidth(100)
        layout.addWidget(self.name_label)
        
        # Name editor (hidden by default)
        self.name_editor = QLineEdit(track_name)
        self.name_editor.setFont(QFont("Arial", 10))
        self.name_editor.hide()
        self.name_editor.editingFinished.connect(self._finish_rename)
        self.name_editor.returnPressed.connect(self._finish_rename)
        layout.addWidget(self.name_editor)
        
        # Spacer
        layout.addStretch()
        
        # Track info
        track_info = self.track_manager.get_track_info(self.track_index) if self.track_manager else {}
        note_count = track_info.get('note_count', 0)
        program = track_info.get('program', 1)
        audio_source_name = track_info.get('audio_source_name', 'Internal FluidSynth')
        
        # Create info layout
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # Note count
        self.info_label = QLabel(f"{note_count} notes")
        self.info_label.setFont(QFont("Arial", 8))
        self.info_label.setStyleSheet("color: #666666;")
        info_layout.addWidget(self.info_label)
        
        # Instrument (MIDI program)
        self.program_label = QLabel(f"Prg {program}")
        self.program_label.setFont(QFont("Arial", 7))
        self.program_label.setStyleSheet("color: #888888;")
        info_layout.addWidget(self.program_label)
        
        # Audio source
        self.audio_source_label = QLabel(f"{audio_source_name[:12]}...")
        self.audio_source_label.setFont(QFont("Arial", 7))
        self.audio_source_label.setStyleSheet("color: #4A90E2;")  # Blue color for audio source
        self.audio_source_label.setToolTip(f"Audio Source: {audio_source_name}")
        info_layout.addWidget(self.audio_source_label)
        
        layout.addLayout(info_layout)
    
    def update_style(self):
        """Update the visual style based on active state"""
        if self.is_active:
            self.setStyleSheet("""
                TrackItemWidget {
                    background-color: #E3F2FD;
                    border: 2px solid #2196F3;
                    border-radius: 4px;
                }
            """)
        else:
            self.setStyleSheet("""
                TrackItemWidget {
                    background-color: #F5F5F5;
                    border: 1px solid #CCCCCC;
                    border-radius: 4px;
                }
                TrackItemWidget:hover {
                    background-color: #EEEEEE;
                    border: 1px solid #AAAAAA;
                }
            """)
    
    def set_active(self, active: bool):
        """Set the active state"""
        if self.is_active != active:
            self.is_active = active
            self.update_style()
    
    def update_info(self, note_count: int, program: int = None, audio_source_name: str = None):
        """Update track information display"""
        self.info_label.setText(f"{note_count} notes")
        if program is not None and hasattr(self, 'program_label'):
            self.program_label.setText(f"Prg {program}")
        if audio_source_name is not None and hasattr(self, 'audio_source_label'):
            display_name = f"{audio_source_name[:12]}..." if len(audio_source_name) > 12 else audio_source_name
            self.audio_source_label.setText(display_name)
            self.audio_source_label.setToolTip(f"Audio Source: {audio_source_name}")
    
    def update_color(self, color: str):
        """Update the track color"""
        self.color_indicator.set_color(color)
    
    def update_name(self, name: str):
        """Update the track name"""
        self.name_label.setText(name)
        if not self.name_editor.hasFocus():
            self.name_editor.setText(name)
    
    def start_rename(self):
        """Start renaming the track"""
        self.name_label.hide()
        self.name_editor.show()
        self.name_editor.setFocus()
        self.name_editor.selectAll()
    
    def _finish_rename(self):
        """Finish renaming the track"""
        new_name = self.name_editor.text().strip()
        if new_name and new_name != self.name_label.text():
            self.track_renamed.emit(self.track_index, new_name)
        
        self.name_editor.hide()
        self.name_label.show()
    
    def _open_color_picker(self):
        """Open color picker dialog"""
        current_color = QColor(self.color_indicator.color)
        color = QColorDialog.getColor(current_color, self, "Select Track Color")
        
        if color.isValid():
            color_hex = color.name()
            self.track_color_changed.emit(self.track_index, color_hex)
    
    def mousePressEvent(self, event):
        """Handle mouse click to select track"""
        if event.button() == Qt.LeftButton:
            self.track_selected.emit(self.track_index)
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click to rename"""
        if event.button() == Qt.LeftButton:
            self.start_rename()
        super().mouseDoubleClickEvent(event)
    
    def _show_context_menu(self, pos):
        """Show right-click context menu"""
        menu = QMenu(self)
        
        rename_action = menu.addAction("Rename Track")
        rename_action.triggered.connect(self.start_rename)
        
        color_action = menu.addAction("Change Color")
        color_action.triggered.connect(self._open_color_picker)
        
        audio_source_action = menu.addAction("Audio Source...")
        audio_source_action.triggered.connect(self._open_audio_source_selector)
        
        menu.addSeparator()
        
        duplicate_action = menu.addAction("Duplicate Track")
        duplicate_action.triggered.connect(lambda: self.track_duplicated.emit(self.track_index))
        
        menu.addSeparator()
        
        remove_action = menu.addAction("Remove Track")
        remove_action.triggered.connect(self._confirm_remove)
        
        # Disable remove if it's the only track
        if self.track_manager and self.track_manager.get_track_count() <= 1:
            remove_action.setEnabled(False)
        
        menu.exec(pos)
    
    def _confirm_remove(self):
        """Confirm track removal"""
        reply = QMessageBox.question(
            self, 
            "Remove Track", 
            f"Are you sure you want to remove '{self.name_label.text()}'?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.track_removed.emit(self.track_index)
    
    def _open_audio_source_selector(self):
        """Open audio source selection dialog"""
        from src.ui.audio_source_dialog import AudioSourceDialog
        
        dialog = AudioSourceDialog(self.track_index, self)
        dialog.source_selected.connect(self._on_audio_source_selected)
        dialog.exec()
    
    def _on_audio_source_selected(self, source_id: str):
        """Handle audio source selection"""
        from src.audio_source_manager import get_audio_source_manager
        from src.per_track_audio_router import get_per_track_audio_router
        
        # Stop any currently playing notes to prevent pop noise
        self._stop_all_notes_on_track()
        
        audio_source_manager = get_audio_source_manager()
        if audio_source_manager:
            success = audio_source_manager.assign_source_to_track(self.track_index, source_id)
            if success:
                # Update display
                source = audio_source_manager.get_track_source(self.track_index)
                if source and hasattr(self, 'audio_source_label'):
                    display_name = f"{source.name[:12]}..." if len(source.name) > 12 else source.name
                    self.audio_source_label.setText(display_name)
                    self.audio_source_label.setToolTip(f"Audio Source: {source.name}")
                    print(f"Track {self.track_index} audio source changed to: {source.name}")
                
                # Use a short delay to prevent audio artifacts before reinitializing
                QTimer.singleShot(50, lambda: self._reinitialize_track_audio(source.name))
            else:
                print(f"❌ Failed to assign audio source {source_id} to track {self.track_index}")
        else:
            print("❌ Audio source manager not available")
    
    def _stop_all_notes_on_track(self):
        """Stop all currently playing notes on this track to prevent pop noise"""
        try:
            from src.audio_routing_coordinator import get_audio_routing_coordinator
            coordinator = get_audio_routing_coordinator()
            if coordinator:
                route = coordinator.track_routes.get(self.track_index)
                if route:
                    # Stop all active notes on this track's channel
                    channel_state = coordinator.channel_states.get(route.channel)
                    if channel_state and channel_state.active_notes:
                        for pitch in list(channel_state.active_notes):
                            from src.midi_data_model import MidiNote
                            dummy_note = MidiNote(0, 480, pitch, 100, route.channel)
                            coordinator.stop_note(self.track_index, dummy_note)
                        print(f"Stopped {len(channel_state.active_notes)} active notes on track {self.track_index}")
        except Exception as e:
            print(f"Warning: Could not stop notes on track {self.track_index}: {e}")
    
    def _reinitialize_track_audio(self, source_name: str):
        """Reinitialize track audio after a short delay"""
        from src.per_track_audio_router import get_per_track_audio_router
        from src.audio_routing_coordinator import get_audio_routing_coordinator
        
        # Try unified coordinator first
        coordinator = get_audio_routing_coordinator()
        if coordinator:
            success = coordinator.setup_track_route(self.track_index)
            if success:
                print(f"✅ Track {self.track_index} audio routing reinitialized for {source_name}")
                return
        
        # Fallback to per-track router
        per_track_router = get_per_track_audio_router()
        if per_track_router:
            router_success = per_track_router.initialize_track_audio(self.track_index)
            if router_success:
                print(f"✅ Track {self.track_index} audio routing initialized for {source_name}")
            else:
                print(f"❌ Failed to initialize audio routing for track {self.track_index}")
        else:
            print("❌ Per-track router not available")

class TrackListWidget(QWidget):
    """Main track list widget with scrolling support"""
    
    # Signals
    track_selected = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.track_manager: Optional[TrackManager] = None
        self.track_items: List[TrackItemWidget] = []
        
        self.setup_ui()
        
        # Connect to track manager if available
        track_manager = get_track_manager()
        if track_manager:
            self.set_track_manager(track_manager)
    
    def setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Header
        header_label = QLabel("Tracks")
        header_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Scroll area for tracks
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Container widget for track items
        self.tracks_container = QWidget()
        self.tracks_layout = QVBoxLayout(self.tracks_container)
        self.tracks_layout.setContentsMargins(0, 0, 0, 0)
        self.tracks_layout.setSpacing(2)
        self.tracks_layout.addStretch()  # Push tracks to top
        
        self.scroll_area.setWidget(self.tracks_container)
        layout.addWidget(self.scroll_area)
        
        # Add track button
        self.add_track_button = QPushButton("+ Add Track")
        self.add_track_button.setFixedHeight(30)
        self.add_track_button.clicked.connect(self._add_track)
        layout.addWidget(self.add_track_button)
        
        # Set fixed width
        self.setFixedWidth(220)
    
    def set_track_manager(self, track_manager: TrackManager):
        """Set the track manager and connect signals"""
        self.track_manager = track_manager
        
        # Connect signals
        track_manager.active_track_changed.connect(self._on_active_track_changed)
        track_manager.track_added.connect(self._on_track_added)
        track_manager.track_removed.connect(self._on_track_removed)
        track_manager.track_renamed.connect(self._on_track_renamed)
        track_manager.track_color_changed.connect(self._on_track_color_changed)
        track_manager.project_changed.connect(self._on_project_changed)
        
        # Refresh the display
        self.refresh_tracks()
    
    def refresh_tracks(self):
        """Refresh the entire track list"""
        # Clear existing items
        for item in self.track_items:
            item.setParent(None)
        self.track_items.clear()
        
        if not self.track_manager:
            return
        
        # Add track items
        track_count = self.track_manager.get_track_count()
        active_index = self.track_manager.get_active_track_index()
        
        for i in range(track_count):
            track_info = self.track_manager.get_track_info(i)
            self._create_track_item(i, track_info, i == active_index)
    
    def _create_track_item(self, track_index: int, track_info: dict, is_active: bool):
        """Create a new track item widget"""
        item = TrackItemWidget(
            track_index,
            track_info['name'],
            track_info['color'],
            is_active
        )
        
        # Connect signals
        item.track_selected.connect(self._on_track_item_selected)
        item.track_renamed.connect(self._on_track_item_renamed)
        item.track_color_changed.connect(self._on_track_item_color_changed)
        item.track_removed.connect(self._on_track_item_removed)
        item.track_duplicated.connect(self._on_track_item_duplicated)
        
        # Update info
        item.update_info(
            track_info['note_count'], 
            track_info.get('program'), 
            track_info.get('audio_source_name')
        )
        
        # Add to layout (before the stretch)
        position = len(self.track_items)
        self.tracks_layout.insertWidget(position, item)
        self.track_items.append(item)
    
    def _add_track(self):
        """Add a new track"""
        if self.track_manager:
            self.track_manager.add_track()
    
    def _on_active_track_changed(self, track_index: int):
        """Handle active track change"""
        for i, item in enumerate(self.track_items):
            item.set_active(i == track_index)
        
        self.track_selected.emit(track_index)
    
    def _on_track_added(self, track_index: int):
        """Handle track addition"""
        self.refresh_tracks()
    
    def _on_track_removed(self, track_index: int):
        """Handle track removal"""
        self.refresh_tracks()
    
    def _on_track_renamed(self, track_index: int, new_name: str):
        """Handle track rename"""
        if track_index < len(self.track_items):
            self.track_items[track_index].update_name(new_name)
    
    def _on_track_color_changed(self, track_index: int, new_color: str):
        """Handle track color change"""
        if track_index < len(self.track_items):
            self.track_items[track_index].update_color(new_color)
    
    def _on_project_changed(self):
        """Handle project change"""
        self.refresh_tracks()
    
    def _on_track_item_selected(self, track_index: int):
        """Handle track item selection"""
        if self.track_manager:
            self.track_manager.set_active_track(track_index)
    
    def _on_track_item_renamed(self, track_index: int, new_name: str):
        """Handle track item rename"""
        if self.track_manager:
            self.track_manager.rename_track(track_index, new_name)
    
    def _on_track_item_color_changed(self, track_index: int, new_color: str):
        """Handle track item color change"""
        if self.track_manager:
            self.track_manager.set_track_color(track_index, new_color)
    
    def _on_track_item_removed(self, track_index: int):
        """Handle track item removal"""
        if self.track_manager:
            self.track_manager.remove_track(track_index)
    
    def _on_track_item_duplicated(self, track_index: int):
        """Handle track item duplication"""
        if self.track_manager:
            self.track_manager.duplicate_track(track_index)
    
    def update_track_info(self):
        """Update track information (note counts, etc.)"""
        if not self.track_manager:
            return
        
        for i, item in enumerate(self.track_items):
            track_info = self.track_manager.get_track_info(i)
            item.update_info(
                track_info['note_count'],
                track_info.get('program'),
                track_info.get('audio_source_name')
            )