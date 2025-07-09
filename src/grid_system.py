"""
Grid and cell selection system for piano roll
"""
from typing import List, Optional, Tuple, Set
from dataclasses import dataclass
from PySide6.QtCore import QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt


@dataclass
class GridCell:
    """Represents a single cell in the piano roll grid"""
    start_tick: int
    end_tick: int
    pitch: int
    
    def __hash__(self):
        return hash((self.start_tick, self.end_tick, self.pitch))
    
    def __eq__(self, other):
        if not isinstance(other, GridCell):
            return False
        return (self.start_tick == other.start_tick and 
                self.end_tick == other.end_tick and 
                self.pitch == other.pitch)
    
    def contains_tick(self, tick: int) -> bool:
        """Check if a tick is within this cell"""
        return self.start_tick <= tick < self.end_tick
    
    def overlaps_with(self, other_cell: 'GridCell') -> bool:
        """Check if this cell overlaps with another cell"""
        return (self.pitch == other_cell.pitch and
                not (self.end_tick <= other_cell.start_tick or 
                     self.start_tick >= other_cell.end_tick))


class GridManager:
    """Manages the grid system for piano roll"""
    
    def __init__(self, ticks_per_beat: int = 480, grid_division: int = 4):
        """
        Args:
            ticks_per_beat: MIDI ticks per beat
            grid_division: Grid division (4 = 16th notes, 8 = 32nd notes)
        """
        self.ticks_per_beat = ticks_per_beat
        self.grid_division = grid_division
        self.grid_ticks = ticks_per_beat // grid_division
        self.selected_cells: Set[GridCell] = set()
        self.paste_target_cell: Optional[GridCell] = None
    
    def get_grid_cell_at_position(self, tick: int, pitch: int) -> GridCell:
        """Get the grid cell at a specific tick and pitch"""
        # Snap to grid
        grid_start = (tick // self.grid_ticks) * self.grid_ticks
        grid_end = grid_start + self.grid_ticks
        
        return GridCell(
            start_tick=grid_start,
            end_tick=grid_end,
            pitch=pitch
        )
    
    def get_grid_cells_in_range(self, start_tick: int, end_tick: int, 
                                start_pitch: int, end_pitch: int) -> List[GridCell]:
        """Get all grid cells in a specified range"""
        cells = []
        
        # Snap to grid boundaries
        grid_start = (start_tick // self.grid_ticks) * self.grid_ticks
        grid_end = ((end_tick + self.grid_ticks - 1) // self.grid_ticks) * self.grid_ticks
        
        # Ensure pitch range is correct
        min_pitch = min(start_pitch, end_pitch)
        max_pitch = max(start_pitch, end_pitch)
        
        # Generate all cells in the range
        current_tick = grid_start
        while current_tick < grid_end:
            for pitch in range(min_pitch, max_pitch + 1):
                cell = GridCell(
                    start_tick=current_tick,
                    end_tick=current_tick + self.grid_ticks,
                    pitch=pitch
                )
                cells.append(cell)
            current_tick += self.grid_ticks
        
        return cells
    
    def select_cell(self, cell: GridCell):
        """Select a single cell"""
        self.selected_cells.add(cell)
    
    def select_cells(self, cells: List[GridCell]):
        """Select multiple cells"""
        self.selected_cells.update(cells)
    
    def deselect_cell(self, cell: GridCell):
        """Deselect a single cell"""
        self.selected_cells.discard(cell)
    
    def toggle_cell_selection(self, cell: GridCell):
        """Toggle selection of a cell"""
        if cell in self.selected_cells:
            self.selected_cells.remove(cell)
        else:
            self.selected_cells.add(cell)
    
    def clear_selection(self):
        """Clear all selected cells"""
        self.selected_cells.clear()
    
    def set_paste_target(self, cell: GridCell):
        """Set the target cell for paste operations"""
        self.paste_target_cell = cell
    
    def clear_paste_target(self):
        """Clear the paste target"""
        self.paste_target_cell = None
    
    def get_selected_cells(self) -> Set[GridCell]:
        """Get all selected cells"""
        return self.selected_cells.copy()
    
    def get_paste_target_cell(self) -> Optional[GridCell]:
        """Get the current paste target cell"""
        return self.paste_target_cell
    
    def is_cell_selected(self, cell: GridCell) -> bool:
        """Check if a cell is selected"""
        return cell in self.selected_cells
    
    def draw_grid_cells(self, painter: QPainter, pixels_per_tick: float, 
                       pixels_per_pitch: float, height: int, visible_start_tick: int):
        """Draw selected grid cells and paste target"""
        # Draw selected cells
        for cell in self.selected_cells:
            self._draw_cell(painter, cell, pixels_per_tick, pixels_per_pitch, 
                          height, visible_start_tick, 
                          QColor(100, 200, 255, 60), QColor(100, 200, 255, 120))
        
        # Draw paste target cell
        if self.paste_target_cell:
            self._draw_cell(painter, self.paste_target_cell, pixels_per_tick, 
                          pixels_per_pitch, height, visible_start_tick,
                          QColor(255, 200, 100, 60), QColor(255, 200, 100, 160))
    
    def _draw_cell(self, painter: QPainter, cell: GridCell, pixels_per_tick: float,
                   pixels_per_pitch: float, height: int, visible_start_tick: int,
                   fill_color: QColor, border_color: QColor):
        """Draw a single grid cell"""
        # Calculate position
        x = (cell.start_tick - visible_start_tick) * pixels_per_tick
        y = height - ((cell.pitch + 1) * pixels_per_pitch)
        width = (cell.end_tick - cell.start_tick) * pixels_per_tick
        cell_height = pixels_per_pitch
        
        # Draw cell
        painter.setBrush(fill_color)
        painter.setPen(QPen(border_color, 2))
        painter.drawRect(int(x), int(y), int(width), int(cell_height))
    
    def update_grid_settings(self, ticks_per_beat: int, grid_division: int):
        """Update grid settings"""
        self.ticks_per_beat = ticks_per_beat
        self.grid_division = grid_division
        self.grid_ticks = ticks_per_beat // grid_division
        # Clear selection when grid changes
        self.clear_selection()
        self.clear_paste_target()