# src/queue_framework/models/fifo_model.py

"""
Implements the concrete FIFO (First-In, First-Out) queue model.

This module provides the `FIFOQueueModel` class, which is the most
common queueing discipline. It inherits from `BaseQueueModel` and
uses a `collections.deque` for efficient O(1) appends and pops
from both ends.
"""

import logging
from collections import deque
from typing import Any, Optional, Set, Dict, Deque, Tuple

# Local package imports
from ..base_model import BaseQueueModel
from ..constants import EntityState, RequestResult
from ..measure import Measure

# Set up the module-level logger
log = logging.getLogger(__name__)


class FIFOQueueModel(BaseQueueModel):
    """
    A concrete implementation of BaseQueueModel for a G/G/c
    system with a First-In, First-Out (FIFO) queueing discipline.
    """

    def __init__(self, capacity: int, start_time: float = 0.0):
        """
        Initializes the FIFO queueing model.

        Args:
            capacity (int): The number of parallel resources (servers).
            start_time (float, optional): The simulation time at which
                                          the model starts. Defaults to 0.0.
        """
        # Initialize common attributes from the base class
        super().__init__(capacity, start_time)
        
        # Internal State Tracking (FIFO-specific)
        # Use a deque for O(1) FIFO operations
        self.queue: Deque[Tuple[Any, float]] = deque()
        
        self.users: Set[Any] = set()
        self.entity_arrival_time: Dict[Any, float] = {}
        self.entity_service_start_time: Dict[Any, float] = {}

        # Components 
        self.kpi_tracker: Measure = Measure(capacity, start_time)
        
        log.info(f"FIFOQueueModel initialized: Capacity={self.capacity}, "
                 f"StartTime={start_time:.2f}")

    

    def request(self, entity: Any, current_time: float) -> RequestResult:
        """
        An entity requests a resource. It is served immediately if
        capacity allows, otherwise it is enqueued (FIFO).
        """
        log.debug(f"T={current_time:.2f}: Request from entity {entity}...")
        self.kpi_tracker.log_arrival(current_time)

        if len(self.users) < self.capacity:
            # Resource Available
            log.debug(f"T={current_time:.2f}: Resource available for {entity}.")
            self._serve_entity(entity, 
                               arrival_time=current_time, 
                               start_time=current_time)
            return RequestResult.SERVED_IMMEDIATELY
        
        else:
            # Resource Busy -> Enqueue
            log.debug(f"T={current_time:.2f}: Resource busy. Queuing {entity}.")
            
            # FIFO logic: append to the right
            self.queue.append((entity, current_time))
            self._set_entity_state(entity, EntityState.WAITING_FOR_RESOURCE)
            
            self.kpi_tracker.log_queue_entry(
                time=current_time,
                current_queue_length=len(self.queue)
            )
            return RequestResult.QUEUED

    def release(self, entity: Any, current_time: float) -> Optional[Any]:
        """
        An entity releases a resource. If the queue is not empty,
        the next entity (FIFO) is dequeued and served.
        """
        log.debug(f"T={current_time:.2f}: Release by entity {entity}...")
        
        if entity not in self.users:
            log.error(f"T={current_time:.2f}: Entity {entity} tried to "
                      f"release a resource it does not possess.")
            raise ValueError(f"Entity {entity} not in active users set.")

        # Log KPIs for the departing entity
        service_start_time = self.entity_service_start_time.pop(entity)
        arrival_time = self.entity_arrival_time.pop(entity)
        service_time = current_time - service_start_time
        system_time = current_time - arrival_time
        
        # Update State
        self.users.remove(entity)
        self._set_entity_state(entity, EntityState.IDLE)

        self.kpi_tracker.log_service_end(
            time=current_time,
            service_time=service_time,
            system_time=system_time,
            current_busy_servers=len(self.users)
        )
        
        log.debug(f"T={current_time:.2f}: Entity {entity} "
                  f"released resource. ServiceTime={service_time:.2f}")

        # Check Queue for Next Entity
        if len(self.queue) > 0:
            # FIFO logic: pop from the left
            next_entity, next_arrival_time = self.queue.popleft()
            
            log.debug(f"T={current_time:.2f}: Queue not empty. "
                      f"Serving next entity {next_entity} (FIFO).")
            
            self._serve_entity(entity=next_entity,
                               arrival_time=next_arrival_time,
                               start_time=current_time)
            return next_entity
        
        else:
            log.debug(f"T={current_time:.2f}: Resource freed. "
                      f"Queue is empty.")
            return None

    def get_final_kpis(self, simulation_end_time: float) -> Dict[str, Any]:
        """Pass-through method to get the final KPI report."""
        log.info(f"Calculating final KPIs at T={simulation_end_time:.2f}")
        return self.kpi_tracker.get_final_kpis(simulation_end_time)

    

    def _serve_entity(self, entity: Any, arrival_time: float,
                      start_time: float):
        """Internal helper to move an entity into the IN_SERVICE state."""
        wait_time = start_time - arrival_time
        
        self.users.add(entity)
        self.entity_arrival_time[entity] = arrival_time
        self.entity_service_start_time[entity] = start_time
        self._set_entity_state(entity, EntityState.IN_SERVICE)

        self.kpi_tracker.log_service_start(
            time=start_time,
            wait_time=wait_time,
            current_queue_length=len(self.queue),
            current_busy_servers=len(self.users)
        )
    
    def _set_entity_state(self, entity: Any, state: EntityState):
        """Safely sets the entity's state attribute."""
        try:
            entity.state = state
        except AttributeError:
            log.warning(f"Entity {entity} does not have a '.state' "
                        f"attribute or it is not mutable.")