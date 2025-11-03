# src/queue_framework/models/finite_capacity_model.py

"""
Implements a concrete FIFO queue model with a finite queue capacity.

This module provides the `FiniteCapacityModel`, which is based on
the FIFO logic but adds a "balking" mechanism. If an entity
arrives when all resources (servers) are busy *and* the
waiting queue is full, the entity is rejected.
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


class FiniteCapacityModel(BaseQueueModel):
    """
    A concrete implementation of BaseQueueModel for a G/G/c/K system.
    
    This model has a finite-sized waiting queue. It uses a FIFO
    discipline for the queue.

    K = capacity + queue_capacity
    """

    def __init__(self, capacity: int, queue_capacity: int,
                 start_time: float = 0.0):
        """
        Initializes the finite capacity queueing model.

        Args:
            capacity (int): The number of parallel resources (servers).
            queue_capacity (int): The maximum number of entities
                                  allowed to wait in the queue.
            start_time (float, optional): The simulation time at which
                                          the model starts. Defaults to 0.0.
        """
        # Initialize common attributes from the base class
        super().__init__(capacity, start_time)
        
        if queue_capacity < 0:
            raise ValueError("queue_capacity cannot be negative.")
            
        self.queue_capacity: int = queue_capacity
        
        # Internal State Tracking (FIFO-based)
        self.queue: Deque[Tuple[Any, float]] = deque()
        self.users: Set[Any] = set()
        self.entity_arrival_time: Dict[Any, float] = {}
        self.entity_service_start_time: Dict[Any, float] = {}

        # Components
        self.kpi_tracker: Measure = Measure(capacity, start_time)
        
        # Model-specific KPI
        self.total_rejections: int = 0
        
        log.info(f"FiniteCapacityModel initialized: "
                 f"Capacity={self.capacity}, "
                 f"QueueCapacity={self.queue_capacity}, "
                 f"StartTime={start_time:.2f}")

    

    def request(self, entity: Any, current_time: float) -> RequestResult:
        """
        An entity requests a resource. It is served, queued, or
        rejected based on server and queue availability.
        """
        log.debug(f"T={current_time:.2f}: Request from entity {entity}...")
        self.kpi_tracker.log_arrival(current_time)

        # Check for available server
        if len(self.users) < self.capacity:
            # Resource Available
            log.debug(f"T={current_time:.2f}: Resource available for {entity}.")
            self._serve_entity(entity, 
                               arrival_time=current_time, 
                               start_time=current_time)
            return RequestResult.SERVED_IMMEDIATELY
        
        # Servers are full, check queue capacity
        if len(self.queue) < self.queue_capacity:
            # Queue has space
            log.debug(f"T={current_time:.2f}: Resource busy. "
                      f"Queue has space ({len(self.queue)}/"
                      f"{self.queue_capacity}). Queuing {entity}.")
            
            self.queue.append((entity, current_time))
            self._set_entity_state(entity, EntityState.WAITING_FOR_RESOURCE)
            
            self.kpi_tracker.log_queue_entry(
                time=current_time,
                current_queue_length=len(self.queue)
            )
            return RequestResult.QUEUED
        
        # Servers are full AND queue is full
        log.debug(f"T={current_time:.2f}: Resource busy. "
                  f"Queue is FULL ({len(self.queue)}/"
                  f"{self.queue_capacity}). REJECTING {entity}.")
        
        self.total_rejections += 1
        # The entity's state remains IDLE (or unchanged).
        # It never enters the system.
        return RequestResult.REJECTED_QUEUE_FULL


    def release(self, entity: Any, current_time: float) -> Optional[Any]:
        """
        An entity releases a resource. This logic is identical to
        the FIFO model: it frees a resource and serves the next
        entity from the (FIFO) queue if one is waiting.
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
        """
        Gets the final KPI report, including the total rejections.
        """
        log.info(f"Calculating final KPIs at T={simulation_end_time:.2f}")

        # Get the main, overall KPIs
        main_kpis = self.kpi_tracker.get_final_kpis(simulation_end_time)

        # Add our model-specific KPIs
        main_kpis["arrivals_and_throughput"]["total_rejections"] = \
            self.total_rejections
        
        # Calculate probability of rejection
        total_arrivals = main_kpis["arrivals_and_throughput"]["total_arrivals"]
        prob_rejection = (self.total_rejections / total_arrivals) \
            if total_arrivals > 0 else 0.0
        main_kpis["arrivals_and_throughput"]["probability_of_rejection"] = \
            prob_rejection

        return main_kpis

    

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