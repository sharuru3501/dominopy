"""
Simple MIDI Output Port Selection Dialog
"""
from typing import List, Optional
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QComboBox, QPushButton, QGroupBox, QCheckBox,
                              QMessageBox, QTextEdit, QFormLayout)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from src.midi_routing import get_midi_routing_manager, MIDIOutputDevice, MIDIOutputType

class MIDIOutputDialog(QDialog):
    """Simple dialog for selecting MIDI output port"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.midi_router = get_midi_routing_manager()
        self.available_devices = []
        
        self.setWindowTitle("MIDI Output Settings")
        self.setModal(True)
        self.resize(500, 400)
        
        self._setup_ui()
        self._refresh_devices()
    
    def _setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Select MIDI Output Port")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header_label)
        
        # Main settings group
        settings_group = QGroupBox("MIDI Output Configuration")
        settings_layout = QFormLayout(settings_group)
        
        # Primary output selection
        self.output_combo = QComboBox()
        self.output_combo.setMinimumHeight(30)
        settings_layout.addRow("MIDI Output Port:", self.output_combo)
        
        # Enable external routing checkbox
        self.enable_external_cb = QCheckBox("Enable External MIDI Routing")
        self.enable_external_cb.setToolTip("Send MIDI to external devices/software")
        settings_layout.addRow("", self.enable_external_cb)
        
        # Keep internal audio checkbox  
        self.keep_internal_cb = QCheckBox("Keep Internal Audio (FluidSynth)")
        self.keep_internal_cb.setToolTip("Continue playing audio through built-in synthesizer")
        self.keep_internal_cb.setChecked(True)
        settings_layout.addRow("", self.keep_internal_cb)
        
        layout.addWidget(settings_group)
        
        # Status display
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(100)
        self.status_text.setStyleSheet("background-color: #f0f0f0; font-family: monospace; font-size: 11px;")
        status_layout.addWidget(self.status_text)
        
        layout.addWidget(status_group)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh")
        self.test_btn = QPushButton("Test")
        self.apply_btn = QPushButton("Apply")
        self.close_btn = QPushButton("Close")
        
        # Style buttons
        for btn in [self.refresh_btn, self.test_btn, self.apply_btn, self.close_btn]:
            btn.setMinimumHeight(30)
        
        self.apply_btn.setStyleSheet("font-weight: bold;")
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.test_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        # Connect signals
        self.refresh_btn.clicked.connect(self._refresh_devices)
        self.test_btn.clicked.connect(self._test_output)
        self.apply_btn.clicked.connect(self._apply_settings)
        self.close_btn.clicked.connect(self.accept)
        
        self.output_combo.currentTextChanged.connect(self._on_output_changed)
    
    def _refresh_devices(self):
        """Refresh the list of available MIDI devices"""
        self._update_status("Refreshing MIDI devices...")
        
        if not self.midi_router:
            self._update_status("❌ MIDI routing system not available")
            return
        
        # Get devices from MIDI router
        self.midi_router.refresh_devices()
        self.available_devices = self.midi_router.get_available_devices()
        
        # Clear and populate combo box
        self.output_combo.clear()
        
        current_primary = None
        if self.midi_router.settings.primary_output:
            current_primary = self.midi_router.settings.primary_output
        
        selected_index = 0
        
        for i, device in enumerate(self.available_devices):
            # Create display name with status icon
            if device.output_type == MIDIOutputType.INTERNAL_FLUIDSYNTH:
                icon = "🔊"
                type_text = "Internal"
            elif device.output_type == MIDIOutputType.EXTERNAL_DEVICE:
                icon = "🎹"
                type_text = "External"
            else:
                icon = "🔌"
                type_text = "Virtual"
            
            display_name = f"{icon} {device.name} ({type_text})"
            self.output_combo.addItem(display_name, device.id)
            
            # Set current selection
            if device.id == current_primary:
                selected_index = i
        
        if self.output_combo.count() > 0:
            self.output_combo.setCurrentIndex(selected_index)
        
        # Update settings checkboxes
        if self.midi_router.settings:
            self.enable_external_cb.setChecked(self.midi_router.settings.enable_external_routing)
            self.keep_internal_cb.setChecked(self.midi_router.settings.enable_internal_audio)
        
        self._update_status(f"✅ Found {len(self.available_devices)} MIDI devices")
        
        # Display device summary
        internal_count = sum(1 for d in self.available_devices if d.output_type == MIDIOutputType.INTERNAL_FLUIDSYNTH)
        external_count = sum(1 for d in self.available_devices if d.output_type == MIDIOutputType.EXTERNAL_DEVICE)
        virtual_count = len(self.available_devices) - internal_count - external_count
        
        self._update_status(f"📊 Internal: {internal_count}, External: {external_count}, Virtual: {virtual_count}")
    
    def _update_status(self, message: str):
        """Update status display"""
        import time
        timestamp = time.strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")
        
        # Auto-scroll to bottom
        scrollbar = self.status_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _on_output_changed(self, device_name: str):
        """Handle output device selection change"""
        if device_name:
            device_id = self.output_combo.currentData()
            if device_id:
                device = next((d for d in self.available_devices if d.id == device_id), None)
                if device:
                    self._update_status(f"🎯 Selected: {device.name}")
    
    def _test_output(self):
        """Test the current MIDI output configuration"""
        if not self.midi_router:
            QMessageBox.warning(self, "Test Failed", "MIDI routing system not available")
            return
        
        device_id = self.output_combo.currentData()
        if not device_id:
            QMessageBox.information(self, "No Selection", "Please select a MIDI output device first")
            return
        
        self._update_status("🎵 Testing MIDI output...")
        
        try:
            # Temporarily apply settings for test
            old_primary = self.midi_router.settings.primary_output
            
            # Set test device as primary
            self.midi_router.set_primary_output(device_id)
            
            # Play test note (C4)
            self.midi_router.play_note(0, 60, 100)  # Channel 0, C4, velocity 100
            
            # Stop the note after delay
            def stop_test_note():
                try:
                    self.midi_router.stop_note(0, 60)
                    self._update_status("✅ Test completed successfully")
                except Exception as e:
                    self._update_status(f"⚠️ Error stopping test note: {e}")
            
            QTimer.singleShot(800, stop_test_note)
            
            self._update_status("✅ Test note sent successfully")
            
        except Exception as e:
            self._update_status(f"❌ Test failed: {str(e)}")
            QMessageBox.warning(self, "Test Failed", f"MIDI test failed:\\n{str(e)}")
    
    def _apply_settings(self):
        """Apply the current MIDI routing settings"""
        if not self.midi_router:
            QMessageBox.warning(self, "Apply Failed", "MIDI routing system not available")
            return
        
        device_id = self.output_combo.currentData()
        if not device_id:
            QMessageBox.information(self, "No Selection", "Please select a MIDI output device first")
            return
        
        try:
            # Apply primary output
            if self.midi_router.set_primary_output(device_id):
                device_name = self.output_combo.currentText()
                self._update_status(f"✅ Primary output set to: {device_name}")
            else:
                self._update_status("❌ Failed to set primary output")
                QMessageBox.warning(self, "Apply Failed", "Failed to set primary MIDI output")
                return
            
            # Apply settings
            self.midi_router.settings.enable_external_routing = self.enable_external_cb.isChecked()
            self.midi_router.settings.enable_internal_audio = self.keep_internal_cb.isChecked()
            
            self._update_status("✅ Settings applied successfully")
            
            # Show success message
            device = next((d for d in self.available_devices if d.id == device_id), None)
            if device:
                message = f"MIDI output configured successfully!\\n\\n"
                message += f"Primary Output: {device.name}\\n"
                message += f"External Routing: {'Enabled' if self.enable_external_cb.isChecked() else 'Disabled'}\\n"
                message += f"Internal Audio: {'Enabled' if self.keep_internal_cb.isChecked() else 'Disabled'}"
                
                QMessageBox.information(self, "Settings Applied", message)
            
        except Exception as e:
            self._update_status(f"❌ Error applying settings: {str(e)}")
            QMessageBox.warning(self, "Apply Failed", f"Failed to apply settings:\\n{str(e)}")
    
    def get_current_settings(self):
        """Get the current dialog settings"""
        return {
            'device_id': self.output_combo.currentData(),
            'device_name': self.output_combo.currentText(),
            'enable_external': self.enable_external_cb.isChecked(),
            'keep_internal': self.keep_internal_cb.isChecked()
        }