"""
Utilities for maintaining per-machine and global map representations.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from queue import Empty, Queue
from typing import Any, Dict, List, Optional, Tuple

from app.logger import logger


@dataclass
class MapCell:
    """Represents a single grid cell observed by a machine."""

    x: int
    y: int
    terrain: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the cell to a serializable dictionary."""
        payload = {
            "x": self.x,
            "y": self.y,
            "terrain": self.terrain,
            "source": self.source,
            "updated_at": self.updated_at,
        }
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


@dataclass
class MapObservation:
    """Observation payload produced after a machine movement."""

    machine_id: str
    position: Tuple[int, int]
    view: List[List[Dict[str, Any]]]
    timestamp: float = field(default_factory=time.time)


class MapManager:
    """Background worker that merges machine observations into maps."""

    def __init__(self) -> None:
        self._machine_maps: Dict[str, Dict[Tuple[int, int], MapCell]] = defaultdict(dict)
        self._global_map: Dict[Tuple[int, int], MapCell] = {}
        self._machine_positions: Dict[str, Tuple[int, int]] = {}
        self._queue: "Queue[MapObservation]" = Queue()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        self._worker = threading.Thread(
            target=self._run_worker, name="MapManagerWorker", daemon=True
        )
        self._worker.start()

    def register_machine(self, machine_id: str, position: Tuple[float, float]) -> None:
        """Ensure a machine has a map entry and tracked position."""
        int_position = (int(round(position[0])), int(round(position[1])))
        with self._lock:
            if machine_id not in self._machine_maps:
                self._machine_maps[machine_id] = {}
            self._machine_positions[machine_id] = int_position

    def submit_observation(self, observation: MapObservation) -> None:
        """Enqueue a new observation for background processing."""
        self._queue.put(observation)

    def get_machine_map_snapshot(self, machine_id: str) -> Dict[str, Any]:
        """Return a serializable snapshot of a machine's known map."""
        with self._lock:
            cells = [
                cell.to_dict()
                for cell in self._machine_maps.get(machine_id, {}).values()
            ]
            position = self._machine_positions.get(machine_id)
        return {
            "machine_id": machine_id,
            "known_cells": cells,
            "last_position": position,
            "generated_at": time.time(),
        }

    def get_global_map_snapshot(self) -> Dict[str, Any]:
        """Return a serializable snapshot of the combined map."""
        with self._lock:
            cells = [cell.to_dict() for cell in self._global_map.values()]
            machine_positions = dict(self._machine_positions)
        return {
            "known_cells": cells,
            "machine_positions": machine_positions,
            "generated_at": time.time(),
        }

    def _run_worker(self) -> None:
        """Continuously process observation events."""
        while not self._stop_event.is_set():
            try:
                observation = self._queue.get(timeout=0.5)
            except Empty:
                continue

            try:
                self._apply_observation(observation)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("MapManager failed to apply observation: %s", exc)
            finally:
                self._queue.task_done()

    def _apply_observation(self, observation: MapObservation) -> None:
        view = observation.view
        if not view:
            return

        view_height = len(view)
        view_width = len(view[0]) if view_height else 0
        if view_width == 0:
            return

        center_x = int(round(observation.position[0]))
        center_y = int(round(observation.position[1]))

        x_offsets = list(range(-(view_width // 2), view_width - (view_width // 2)))
        y_offsets = list(range(-(view_height // 2), view_height - (view_height // 2)))
        y_offsets.reverse()  # Top row corresponds to positive Y direction

        now = observation.timestamp
        updated_cells: Dict[Tuple[int, int], MapCell] = {}

        for row_index, row in enumerate(view):
            for col_index, cell_data in enumerate(row):
                offset_x = x_offsets[col_index]
                offset_y = y_offsets[row_index]
                abs_x = center_x + offset_x
                abs_y = center_y + offset_y

                terrain = "unknown"
                metadata: Dict[str, Any] = {}

                if isinstance(cell_data, dict):
                    terrain = cell_data.get("terrain", cell_data.get("content", "unknown"))
                    metadata = {
                        key: value
                        for key, value in cell_data.items()
                        if key not in {"terrain", "content", "x", "y"}
                    }
                elif isinstance(cell_data, str):
                    terrain = cell_data

                map_cell = MapCell(
                    x=abs_x,
                    y=abs_y,
                    terrain=terrain,
                    metadata=metadata,
                    source=observation.machine_id,
                    updated_at=now,
                )
                updated_cells[(abs_x, abs_y)] = map_cell

        with self._lock:
            machine_map = self._machine_maps.setdefault(observation.machine_id, {})
            machine_map.update(updated_cells)
            self._machine_positions[observation.machine_id] = (center_x, center_y)

            for coordinate, cell in updated_cells.items():
                current_cell = self._global_map.get(coordinate)
                if not current_cell or cell.updated_at >= current_cell.updated_at:
                    self._global_map[coordinate] = cell

    def stop(self) -> None:
        """Signal the worker to stop. Primarily used in tests."""
        self._stop_event.set()
        self._worker.join(timeout=1)


# Shared instance used by Human and Machine agents
map_manager = MapManager()

