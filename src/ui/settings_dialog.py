"""
Settings dialog for DominoPy application
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                              QWidget, QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
                              QCheckBox, QPushButton, QGroupBox, QFormLayout,
                              QSlider, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from src.settings import get_settings_manager, OctaveStandard, save_settings

class DisplaySettingsWidget(QWidget):
    """Widget for display and UI settings"""
    
    settings_changed = Signal()
    
    def __init__(self):
        super().__init__()
        self.settings_manager = get_settings_manager()
        self.setup_ui()
        self.load_current_settings()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Octave Standard Group
        octave_group = QGroupBox("音高基準設定 (Octave Standard)")
        octave_layout = QFormLayout(octave_group)
        
        self.octave_combo = QComboBox()
        self.octave_combo.addItem("Roland/Scientific (C4 = Middle C)", OctaveStandard.ROLAND.value)
        self.octave_combo.addItem("Yamaha (C3 = Middle C)", OctaveStandard.YAMAHA.value)
        self.octave_combo.currentTextChanged.connect(self.on_settings_changed)
        
        octave_layout.addRow("音高表記基準:", self.octave_combo)
        
        # Add explanation
        explanation = QLabel("• Roland/Scientific: 中央C = C4 (MIDI 60)\n• Yamaha: 中央C = C3 (MIDI 60)")
        explanation.setStyleSheet("color: #6272a4; font-size: 11px;")
        octave_layout.addRow("", explanation)
        
        layout.addWidget(octave_group)
        
        # Grid Settings Group
        grid_group = QGroupBox("グリッド設定 (Grid Settings)")
        grid_layout = QFormLayout(grid_group)
        
        # Horizontal zoom (pixels per tick) - use 100x multiplier for slider precision
        self.h_zoom_slider = QSlider(Qt.Horizontal)
        self.h_zoom_slider.setRange(8, 25)  # 0.08 to 0.25 pixels/tick (100x multiplier)
        self.h_zoom_slider.setValue(15)     # 0.15 default (current optimal value)
        self.h_zoom_slider.valueChanged.connect(self.on_settings_changed)
        
        self.h_zoom_label = QLabel("0.15")
        h_zoom_layout = QHBoxLayout()
        h_zoom_layout.addWidget(self.h_zoom_slider)
        h_zoom_layout.addWidget(self.h_zoom_label)
        
        grid_layout.addRow("水平ズーム (Horizontal Zoom):", h_zoom_layout)
        
        # Vertical zoom (pixels per semitone)
        self.v_zoom_slider = QSlider(Qt.Horizontal)
        self.v_zoom_slider.setRange(8, 25)  # 8px to 25px per semitone
        self.v_zoom_slider.setValue(15)     # 15 default (current optimal value)
        self.v_zoom_slider.valueChanged.connect(self.on_settings_changed)
        
        self.v_zoom_label = QLabel("15")
        v_zoom_layout = QHBoxLayout()
        v_zoom_layout.addWidget(self.v_zoom_slider)
        v_zoom_layout.addWidget(self.v_zoom_label)
        
        grid_layout.addRow("垂直ズーム (Vertical Zoom):", v_zoom_layout)
        
        # Connect sliders to labels with proper value conversion
        self.h_zoom_slider.valueChanged.connect(lambda v: self.h_zoom_label.setText(f"{v/100:.2f}"))
        self.v_zoom_slider.valueChanged.connect(lambda v: self.v_zoom_label.setText(str(v)))
        
        layout.addWidget(grid_group)
        
        # Display Options Group
        display_group = QGroupBox("表示オプション (Display Options)")
        display_layout = QFormLayout(display_group)
        
        self.show_note_names_cb = QCheckBox("音名表示")
        self.show_note_names_cb.stateChanged.connect(self.on_settings_changed)
        display_layout.addRow("", self.show_note_names_cb)
        
        self.show_grid_lines_cb = QCheckBox("グリッド線表示")
        self.show_grid_lines_cb.stateChanged.connect(self.on_settings_changed)
        display_layout.addRow("", self.show_grid_lines_cb)
        
        self.snap_to_grid_cb = QCheckBox("グリッドにスナップ")
        self.snap_to_grid_cb.stateChanged.connect(self.on_settings_changed)
        display_layout.addRow("", self.snap_to_grid_cb)
        
        layout.addWidget(display_group)
        
        # Preview Group
        preview_group = QGroupBox("プレビュー (Preview)")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_label = QLabel("設定プレビューがここに表示されます")
        self.preview_label.setStyleSheet("background-color: #44475a; padding: 10px; border-radius: 5px;")
        self.preview_label.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.preview_label)
        
        layout.addWidget(preview_group)
        
        layout.addStretch()
    
    def load_current_settings(self):
        """Load current settings into UI"""
        settings = self.settings_manager.settings.display
        
        # Octave standard
        for i in range(self.octave_combo.count()):
            if self.octave_combo.itemData(i) == settings.octave_standard:
                self.octave_combo.setCurrentIndex(i)
                break
        
        # Grid settings - convert pixels per tick to slider value (100x multiplier)
        self.h_zoom_slider.setValue(int(settings.grid_width_pixels * 100))
        self.v_zoom_slider.setValue(int(settings.grid_height_pixels))
        
        # Display options
        self.show_note_names_cb.setChecked(settings.show_note_names)
        self.show_grid_lines_cb.setChecked(settings.show_grid_lines)
        self.snap_to_grid_cb.setChecked(settings.snap_to_grid)
        
        self.update_preview()
    
    def on_settings_changed(self):
        """Handle settings change"""
        self.apply_settings()
        self.update_preview()
        self.settings_changed.emit()
    
    def apply_settings(self):
        """Apply current UI values to settings"""
        settings = self.settings_manager.settings.display
        
        settings.octave_standard = self.octave_combo.currentData()
        settings.grid_width_pixels = float(self.h_zoom_slider.value()) / 100.0  # Convert back from slider
        settings.grid_height_pixels = float(self.v_zoom_slider.value())
        settings.show_note_names = self.show_note_names_cb.isChecked()
        settings.show_grid_lines = self.show_grid_lines_cb.isChecked()
        settings.snap_to_grid = self.snap_to_grid_cb.isChecked()
    
    def update_preview(self):
        """Update preview display"""
        # Show example note name with current octave standard
        example_midi = 60  # Middle C
        note_name = self.settings_manager.get_octave_display_name(example_midi)
        
        h_zoom = self.h_zoom_slider.value() / 100.0  # Convert to actual pixels per tick
        v_zoom = self.v_zoom_slider.value()
        
        # Calculate display dimensions
        beat_width = h_zoom * 480  # 480 ticks per beat
        measure_width = beat_width * 4  # 4 beats per measure
        
        preview_text = f"中央C表記: {note_name}\n"
        preview_text += f"水平ズーム: {h_zoom:.2f} px/tick (1拍 = {beat_width:.1f}px)\n"
        preview_text += f"垂直ズーム: {v_zoom}px/半音"
        
        self.preview_label.setText(preview_text)

class AudioSettingsWidget(QWidget):
    """Widget for audio settings"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        audio_group = QGroupBox("オーディオ設定 (Audio Settings)")
        audio_layout = QFormLayout(audio_group)
        
        # Sample rate
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["44100", "48000", "96000"])
        audio_layout.addRow("サンプルレート:", self.sample_rate_combo)
        
        # Buffer size
        self.buffer_size_combo = QComboBox()
        self.buffer_size_combo.addItems(["512", "1024", "2048", "4096"])
        audio_layout.addRow("バッファサイズ:", self.buffer_size_combo)
        
        # Gain
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.setRange(0, 100)
        self.gain_slider.setValue(50)
        audio_layout.addRow("ゲイン:", self.gain_slider)
        
        layout.addWidget(audio_group)
        layout.addStretch()

class SettingsDialog(QDialog):
    """Main settings dialog"""
    
    settings_applied = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("設定 (Settings)")
        self.setModal(True)
        self.resize(500, 600)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Display settings tab
        self.display_widget = DisplaySettingsWidget()
        self.display_widget.settings_changed.connect(self.on_settings_changed)
        self.tab_widget.addTab(self.display_widget, "表示 (Display)")
        
        # Audio settings tab
        self.audio_widget = AudioSettingsWidget()
        self.tab_widget.addTab(self.audio_widget, "オーディオ (Audio)")
        
        layout.addWidget(self.tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.apply_button = QPushButton("適用 (Apply)")
        self.apply_button.clicked.connect(self.apply_settings)
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept_and_apply)
        
        self.cancel_button = QPushButton("キャンセル (Cancel)")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def on_settings_changed(self):
        """Handle settings changes"""
        self.apply_button.setEnabled(True)
    
    def apply_settings(self):
        """Apply settings and save"""
        save_settings()
        self.settings_applied.emit()
        self.apply_button.setEnabled(False)
        print("Settings applied and saved")
    
    def accept_and_apply(self):
        """Accept dialog and apply settings"""
        self.apply_settings()
        self.accept()
    
    def reject(self):
        """Cancel dialog without saving"""
        # Reload settings to discard changes
        get_settings_manager().load_settings()
        super().reject()