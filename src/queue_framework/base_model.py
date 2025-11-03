# src/queue_framework/base_model.py

"""
Defines the Abstract Base Class (ABC) for all queueing models.

This module provides the 'BaseQueueModel', which establishes the
essential interface that any concrete queueing implementation must 
adhere to. This ensures that the simulator can interact with any 
queue type (FIFO, LIFO, Priority, etc.) in a consistent, standardized way.
"""

import abc
from typing import Any, Optional, Dict

# Local package imports
from .constants import RequestResult


class BaseQueueModel(abc.ABC):
    """
    Abstract Base Class for queueing model implementations.

    This class defines the standard public API:
    - `request(entity, time)`: To handle an entity's arrival.
    - `release(entity, time)`: To handle an entity's departure.
    - `get_final_kpis(time)`: To retrieve the final simulation report.

    A concrete implementation (e.g., FIFOQueueModel) must inherit from
    this class and implement all its abstract methods.
    """

    def __init__(self, capacity: int, start_time: float = 0.0):
        """
        Initializes the base attributes common to all queue models.

        Args:
            capacity (int): The number of parallel resources (servers).
            start_time (float, optional): The simulation time at which
                                          the model starts. Defaults to 0.0.
        
        Raises:
            ValueError: If capacity is 0 or less.
        """
        if capacity <= 0:
            # We enforce this at the base level, as no valid queue
            # model can operate with non-positive capacity.
            raise ValueError("QueueModel capacity must be > 0.")
            
        self.capacity: int = capacity
        self.start_time: float = start_time
        # NOTE: KPI tracker or queue structures are NOT initialized here.
        # They are the responsibility of the concrete implementation.

    @abc.abstractmethod
    def request(self, entity: Any, current_time: float) -> RequestResult:
        """
        Handles an entity's request for a resource.

        The implementation must decide whether to serve the entity
        immediately or place it in a queue, based on its specific
        queueing discipline (FIFO, LIFO, etc.).

        Args:
            entity (Any): The entity (e.g., User, Car) requesting service.
            current_time (float): The current simulation time.

        Returns:
            RequestResult: Enum indicating if the entity was
                           SERVED_IMMEDIATELY or QUEUED.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def release(self, entity: Any, current_time: float) -> Optional[Any]:
        """
        Handles an entity's release of a resource.

        The implementation must free the resource and, if the queue
        is not empty, select the next entity to serve based on its
        specific queueing discipline.

        Args:
            entity (Any): The entity (e.g., User, Car) releasing service.
            current_time (float): The current simulation time.

        Returns:
            Optional[Any]: The `next_entity` from the queue that was
                           just served, if any. Returns `None` if no
                           entity was served (i.e., queue was empty).
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_final_kpis(self, simulation_end_time: float) -> Dict[str, Any]:
        """
        Retrieves the final statistical report from the model.

        The implementation must call its internal KPI tracker and
        return the resulting data dictionary.

        Args:
            simulation_end_time (float): The final timestamp of the
                                         simulation.

        Returns:
            Dict[str, Any]: A nested dictionary of all calculated KPIs.
        """
        raise NotImplementedError