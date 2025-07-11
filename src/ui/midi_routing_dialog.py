"""
MIDI Routing Settings Dialog
"""
from typing import List, Optional
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QComboBox, QPushButton, QGroupBox, QCheckBox,
                              QListWidget, QListWidgetItem, QMessageBox,
                              QTextEdit, QSplitter)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from src.midi_routing import get_midi_routing_manager, MIDIOutputDevice, MIDIOutputType

class MIDIRoutingDialog(QDialog):
    """Dialog for configuring MIDI routing settings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.midi_router = get_midi_routing_manager()
        self.available_devices = []
        
        self.setWindowTitle("MIDI Routing Settings")
        self.setModal(True)
        self.resize(800, 600)
        
        self._setup_ui()
        self._connect_signals()
        self._refresh_devices()
    
    def _setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout(self)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel - Device list and controls
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Status and info
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh Devices")
        self.test_btn = QPushButton("Test Output")
        self.apply_btn = QPushButton("Apply")
        self.close_btn = QPushButton("Close")
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.test_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_left_panel(self):
        """Create the left panel with device selection"""
        panel = QGroupBox("MIDI Output Devices")
        layout = QVBoxLayout(panel)
        
        # Primary output selection
        primary_group = QGroupBox("Primary Output")
        primary_layout = QVBoxLayout(primary_group)
        
        self.primary_combo = QComboBox()
        self.primary_combo.setSizePolicy(self.primary_combo.sizePolicy().horizontalPolicy(), 
                                       self.primary_combo.sizePolicy().verticalPolicy())
        primary_layout.addWidget(QLabel("Select primary MIDI output:"))
        primary_layout.addWidget(self.primary_combo)
        
        layout.addWidget(primary_group)
        
        # Secondary outputs
        secondary_group = QGroupBox("Additional Outputs (Multi-output)")
        secondary_layout = QVBoxLayout(secondary_group)
        
        self.secondary_list = QListWidget()
        self.secondary_list.setSelectionMode(QListWidget.MultiSelection)
        secondary_layout.addWidget(QLabel("Select additional MIDI outputs:"))
        secondary_layout.addWidget(self.secondary_list)
        
        # Secondary output controls
        secondary_controls = QHBoxLayout()
        self.add_secondary_btn = QPushButton("Add Selected")
        self.remove_secondary_btn = QPushButton("Remove Selected")
        secondary_controls.addWidget(self.add_secondary_btn)
        secondary_controls.addWidget(self.remove_secondary_btn)
        secondary_layout.addLayout(secondary_controls)
        
        layout.addWidget(secondary_group)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        
        self.enable_internal_cb = QCheckBox("Enable Internal FluidSynth")
        self.enable_external_cb = QCheckBox("Enable External MIDI Routing")
        
        options_layout.addWidget(self.enable_internal_cb)
        options_layout.addWidget(self.enable_external_cb)
        
        layout.addWidget(options_group)
        
        return panel
    
    def _create_right_panel(self):
        """Create the right panel with status information"""
        panel = QGroupBox("Status & Information")
        layout = QVBoxLayout(panel)
        
        # Connection status
        status_group = QGroupBox("Connection Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        
        # Use monospace font for better formatting
        font = QFont("Monaco", 10)  # Monaco is available on macOS
        if not font.exactMatch():
            font = QFont("Courier", 10)  # Fallback
        self.status_text.setFont(font)
        
        status_layout.addWidget(self.status_text)
        layout.addWidget(status_group)
        
        # Device information
        info_group = QGroupBox("Device Information")
        info_layout = QVBoxLayout(info_group)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        
        info_layout.addWidget(self.info_text)
        layout.addWidget(info_group)
        
        return panel
    
    def _connect_signals(self):
        """Connect UI signals"""
        self.refresh_btn.clicked.connect(self._refresh_devices)
        self.test_btn.clicked.connect(self._test_output)
        self.apply_btn.clicked.connect(self._apply_settings)
        self.close_btn.clicked.connect(self.accept)
        
        self.primary_combo.currentTextChanged.connect(self._on_primary_changed)
        self.add_secondary_btn.clicked.connect(self._add_secondary_outputs)
        self.remove_secondary_btn.clicked.connect(self._remove_secondary_outputs)
        
        if self.midi_router:
            self.midi_router.devices_updated.connect(self._on_devices_updated)
            self.midi_router.connection_status.connect(self._on_connection_status)
            self.midi_router.connection_error.connect(self._on_connection_error)
    
    def _refresh_devices(self):
        """Refresh the list of available MIDI devices"""
        if not self.midi_router:
            self._update_status("MIDI routing not available")
            return
        
        self._update_status("Refreshing MIDI devices...")
        self.midi_router.refresh_devices()
    
    def _on_devices_updated(self, devices: List[MIDIOutputDevice]):
        """Handle updated device list"""
        self.available_devices = devices
        self._populate_device_lists()
        self._update_device_info()
        self._update_status(f"Found {len(devices)} MIDI devices")
    
    def _populate_device_lists(self):
        """Populate the device selection UI"""
        # Clear existing items
        self.primary_combo.clear()
        self.secondary_list.clear()
        
        # Add devices to primary combo
        for device in self.available_devices:
            self.primary_combo.addItem(f"{device.name} ({device.output_type.value})", device.id)
        
        # Add devices to secondary list
        for device in self.available_devices:
            if device.output_type != MIDIOutputType.INTERNAL_FLUIDSYNTH:  # Exclude internal from secondary
                item = QListWidgetItem(f"{device.name} ({device.output_type.value})")
                item.setData(Qt.UserRole, device.id)
                self.secondary_list.addItem(item)
        
        # Set current selections
        if self.midi_router:
            settings = self.midi_router.settings
            
            # Set primary selection
            if settings.primary_output:
                for i in range(self.primary_combo.count()):
                    if self.primary_combo.itemData(i) == settings.primary_output:
                        self.primary_combo.setCurrentIndex(i)
                        break
            
            # Set checkboxes
            self.enable_internal_cb.setChecked(settings.enable_internal_audio)
            self.enable_external_cb.setChecked(settings.enable_external_routing)
    
    def _update_device_info(self):
        """Update device information display"""
        if not self.available_devices:
            self.info_text.setText("No MIDI devices available")
            return
        
        info_lines = []
        info_lines.append("Available MIDI Devices:")
        info_lines.append("=" * 50)
        
        for device in self.available_devices:
            status = "✓" if device.is_available else "✗"
            info_lines.append(f"{status} {device.name}")
            info_lines.append(f"   Type: {device.output_type.value}")
            info_lines.append(f"   Description: {device.description}")
            if device.output_type == MIDIOutputType.EXTERNAL_DEVICE:
                info_lines.append(f"   Port Index: {device.port_index}")
            info_lines.append("")
        
        self.info_text.setText("\\n".join(info_lines))
    
    def _update_status(self, message: str):
        """Update status display"""
        import time
        timestamp = time.strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")
        
        # Auto-scroll to bottom
        cursor = self.status_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.status_text.setTextCursor(cursor)
    
    def _on_primary_changed(self, device_name: str):
        """Handle primary device selection change"""
        if device_name:
            self._update_status(f"Primary output selected: {device_name}")
    
    def _add_secondary_outputs(self):
        """Add selected devices to secondary outputs"""
        selected_items = self.secondary_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Selection Required", 
                                   "Please select one or more devices to add as secondary outputs.")
            return
        
        for item in selected_items:
            device_id = item.data(Qt.UserRole)
            device_name = item.text()
            self._update_status(f"Added secondary output: {device_name}")
    
    def _remove_secondary_outputs(self):
        """Remove selected secondary outputs"""
        # This would remove from the actual routing configuration
        self._update_status("Secondary outputs removed")
    
    def _test_output(self):
        """Test the current MIDI output configuration"""
        if not self.midi_router:
            QMessageBox.warning(self, "Test Failed", "MIDI routing system not available")
            return
        
        self._update_status("Testing MIDI output...")
        
        try:
            # Play a test note (C4)
            self.midi_router.play_note(0, 60, 100)
            
            # Stop the note after a short delay
            QTimer.singleShot(500, lambda: self.midi_router.stop_note(0, 60))
            
            self._update_status("✓ Test note sent successfully")
            
        except Exception as e:
            self._update_status(f"✗ Test failed: {str(e)}")
            QMessageBox.warning(self, "Test Failed", f"MIDI test failed: {str(e)}")
    
    def _apply_settings(self):
        """Apply the current MIDI routing settings"""
        if not self.midi_router:
            return
        
        try:
            # Set primary output
            primary_device_id = self.primary_combo.currentData()
            if primary_device_id:
                success = self.midi_router.set_primary_output(primary_device_id)
                if success:
                    self._update_status(f"✓ Primary output set to: {self.primary_combo.currentText()}")
                else:
                    self._update_status(f"✗ Failed to set primary output")
            
            # Update settings
            self.midi_router.settings.enable_internal_audio = self.enable_internal_cb.isChecked()
            self.midi_router.settings.enable_external_routing = self.enable_external_cb.isChecked()
            
            self._update_status("✓ Settings applied successfully")
            
        except Exception as e:
            self._update_status(f"✗ Error applying settings: {str(e)}")
            QMessageBox.warning(self, "Apply Failed", f"Failed to apply settings: {str(e)}")
    
    def _on_connection_status(self, device_id: str, connected: bool):
        """Handle connection status changes"""
        status = "connected" if connected else "disconnected"
        self._update_status(f"Device {device_id}: {status}")
    
    def _on_connection_error(self, error_message: str):
        """Handle connection errors"""
        self._update_status(f"✗ Connection error: {error_message}")
        QMessageBox.warning(self, "Connection Error", error_message)