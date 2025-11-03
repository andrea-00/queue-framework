# src/queue_framework/models/priority_model.py

"""
Implements a concrete Priority-based queue model.

This module provides the `PriorityQueueModel` class. It inherits from
`BaseQueueModel` and uses Python's `heapq` module to manage the
queue, serving entities with a lower priority number first.

**Key Feature:**
This class also demonstrates how to extend the framework's KPI
tracking. In addition to the main `Measure` tracker (for overall
stats), it maintains a separate `Measure` object for *each*
priority level, providing a detailed statistical breakdown.

**Entity Contract:**
Entities processed by this model *must* have a `.priority` attribute
(e.g., `entity.priority = 1`). A lower number means a higher priority.
"""

import logging
import heapq
from typing import Any, Optional, Set, Dict, List, Tuple
from collections import defaultdict

# Local package imports
from ..base_model import BaseQueueModel
from ..constants import EntityState, RequestResult
from ..measure import Measure

# Set up the module-level logger
log = logging.getLogger(__name__)


class PriorityQueueModel(BaseQueueModel):
    """
    A concrete implementation of BaseQueueModel for a G/G/c
    system with a priority-based queueing discipline.

    The queue serves entities with the lowest priority number first.
    Within the same priority, entities are served in FIFO order.
    """

    def __init__(self, capacity: int, start_time: float = 0.0):
        """
        Initializes the priority queueing model.

        Args:
            capacity (int): The number of parallel resources (servers).
            start_time (float, optional): The simulation time at which
                                          the model starts. Defaults to 0.0.
        """
        # Initialize common attributes from the base class
        super().__init__(capacity, start_time)

        # Internal State Tracking (Priority-specific)

        # The queue is a standard list managed by heapq.
        # It stores tuples: (priority, arrival_time, entity)
        # This structure ensures sorting by priority, then by arrival
        # time (FIFO within priority), and avoids comparing entities.
        self.queue: List[Tuple[float, float, Any]] = []

        self.users: Set[Any] = set()
        
        # We need to track the priority of entities in service
        # to log their service-end KPIs to the correct tracker.
        self.user_data: Dict[Any, Dict[str, Any]] = {}
        # Example: {entity: {"priority": 1, "arrival_time": 10.5, ...}}

        # KPI Tracking
        
        # Main tracker (for overall system KPIs)
        # This fulfills the BaseQueueModel contract.
        self.kpi_tracker: Measure = Measure(capacity, start_time)

        # Additional KPI trackers (for priority-specific KPIs)
        # We use a defaultdict to create new Measure trackers
        # on-the-fly as new priority levels are encountered.
        self.priority_kpi_trackers: Dict[Any, Measure] = defaultdict(
            lambda: Measure(capacity=self.capacity, start_time=self.start_time)
        )

        log.info(f"PriorityQueueModel initialized: Capacity={self.capacity}, "
                 f"StartTime={start_time:.2f}")

    

    def request(self, entity: Any, current_time: float) -> RequestResult:
        """
        An entity requests a resource. It is served immediately if
        capacity allows, otherwise it is enqueued based on its priority.
        
        This method *requires* the entity to have a `.priority` attribute.
        """
        log.debug(f"T={current_time:.2f}: Request from entity {entity}...")

        # Get Priority (New Contract)
        try:
            priority = entity.priority
        except AttributeError:
            log.exception(f"Entity {entity} does not have a '.priority' "
                          f"attribute. Cannot process in PriorityQueueModel.")
            raise
        
        # Log arrival in *both* trackers
        self.kpi_tracker.log_arrival(current_time)
        self.priority_kpi_trackers[priority].log_arrival(current_time)

        if len(self.users) < self.capacity:
            # Resource Available
            log.debug(f"T={current_time:.2f}: Resource available for {entity} "
                      f"(P={priority}).")
            self._serve_entity(entity, priority,
                               arrival_time=current_time,
                               start_time=current_time)
            return RequestResult.SERVED_IMMEDIATELY

        else:
            # Resource Busy -> Enqueue
            log.debug(f"T={current_time:.2f}: Resource busy. Queuing {entity} "
                      f"(P={priority}).")

            # Priority logic: push onto the heap
            heapq.heappush(self.queue, (priority, current_time, entity))
            self._set_entity_state(entity, EntityState.WAITING_FOR_RESOURCE)

            # Log queue entry in *both* trackers
            q_len = len(self.queue)
            self.kpi_tracker.log_queue_entry(current_time, q_len)
            self.priority_kpi_trackers[priority].log_queue_entry(
                current_time,
                # NOTE: This is the *total* queue length, not per-priority
                # A more advanced tracker could log per-priority q_len.
                current_queue_length=q_len 
            )
            return RequestResult.QUEUED

    def release(self, entity: Any, current_time: float) -> Optional[Any]:
        """
        An entity releases a resource. If the queue is not empty,
        the next entity (highest priority) is dequeued and served.
        """
        log.debug(f"T={current_time:.2f}: Release by entity {entity}...")

        if entity not in self.users:
            log.error(f"T={current_time:.2f}: Entity {entity} tried to "
                      f"release a resource it does not possess.")
            raise ValueError(f"Entity {entity} not in active users set.")

        # Retrieve stored data for the departing entity
        entity_data = self.user_data.pop(entity)
        priority = entity_data["priority"]
        arrival_time = entity_data["arrival_time"]
        service_start_time = entity_data["service_start_time"]
        
        service_time = current_time - service_start_time
        system_time = current_time - arrival_time

        # Update State
        self.users.remove(entity)
        self._set_entity_state(entity, EntityState.IDLE)
        
        busy_servers = len(self.users)

        # Log service end in *both* trackers
        self.kpi_tracker.log_service_end(
            time=current_time, service_time=service_time,
            system_time=system_time, current_busy_servers=busy_servers
        )
        self.priority_kpi_trackers[priority].log_service_end(
            time=current_time, service_time=service_time,
            system_time=system_time, current_busy_servers=busy_servers
        )

        log.debug(f"T={current_time:.2f}: Entity {entity} (P={priority}) "
                  f"released resource. ServiceTime={service_time:.2f}")

        # --- Check Queue for Next Entity ---
        if len(self.queue) > 0:
            # Priority logic: pop from the heap
            next_priority, next_arrival_time, next_entity = heapq.heappop(
                self.queue)

            log.debug(f"T={current_time:.2f}: Queue not empty. "
                      f"Serving next entity {next_entity} (P={next_priority}).")

            self._serve_entity(entity=next_entity, priority=next_priority,
                               arrival_time=next_arrival_time,
                               start_time=current_time)
            return next_entity

        else:
            log.debug(f"T={current_time:.2f}: Resource freed. "
                      f"Queue is empty.")
            return None

    def get_final_kpis(self, simulation_end_time: float) -> Dict[str, Any]:
        """
        Gets the final KPI report, including the priority breakdown.

        This overrides the base method to *add* the priority-specific
        KPIs to the final report.
        """
        log.info(f"Calculating final KPIs at T={simulation_end_time:.2f}")

        # Get the main, overall KPIs
        main_kpis = self.kpi_tracker.get_final_kpis(simulation_end_time)

        # Build the priority breakdown
        priority_breakdown = {}
        for priority, tracker in self.priority_kpi_trackers.items():
            log.debug(f"Calculating KPIs for priority level {priority}...")
            priority_kpis = tracker.get_final_kpis(simulation_end_time)
            priority_breakdown[priority] = priority_kpis
        
        # Add the breakdown to the main report
        main_kpis["priority_breakdown"] = priority_breakdown
        
        return main_kpis

    

    def _serve_entity(self, entity: Any, priority: float, arrival_time: float,
                      start_time: float):
        """Internal helper to move an entity into the IN_SERVICE state."""
        wait_time = start_time - arrival_time

        # Update State
        self.users.add(entity)
        # Store all data needed upon release
        self.user_data[entity] = {
            "priority": priority,
            "arrival_time": arrival_time,
            "service_start_time": start_time
        }
        self._set_entity_state(entity, EntityState.IN_SERVICE)
        
        busy_servers = len(self.users)
        q_len = len(self.queue)

        # Log KPIs in *both* trackers
        self.kpi_tracker.log_service_start(
            time=start_time, wait_time=wait_time,
            current_queue_length=q_len,
            current_busy_servers=busy_servers
        )
        self.priority_kpi_trackers[priority].log_service_start(
            time=start_time, wait_time=wait_time,
            current_queue_length=q_len,
            current_busy_servers=busy_servers
        )

    def _set_entity_state(self, entity: Any, state: EntityState):
        """Safely sets the entity's state attribute."""
        try:
            entity.state = state
        except AttributeError:
            log.warning(f"Entity {entity} does not have a '.state' "
                        f"attribute or it is not mutable.")