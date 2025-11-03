# src/queue_framework/constants.py

"""
Defines core enumerations used across the queueing framework.

This module provides abstract, generalized constants to define the state
of entities and the results of operations within the queueing model.
These enums act as a clean interface, ensuring the framework remains
domain-agnostic.
"""

from enum import Enum, auto

class EntityState(Enum):
    """
    Represents the standardized states an entity can be in
    relative to a queueing model.
    
    The QueueModel itself manages and assigns these states to the
    entities it processes.
    """
    
    # Represents an entity that is not currently interacting with
    # this specific queueing model.
    IDLE = auto()
    
    # Represents an entity that has requested a resource but must wait
    # as all resources are currently busy.
    WAITING_FOR_RESOURCE = auto()
    
    # Represents an entity that has successfully acquired a resource
    # and is currently being "served".
    IN_SERVICE = auto()

    # TODO: Consider adding more states in the future, such as:
    # REJECTED = auto()

class RequestResult(Enum):
    """
    Represents the possible outcomes of an entity's `request` for a resource.
    
    This enum is the return value for the `QueueModel.request()` method and
    is used by the external simulator to make decisions (e.g., whether to
    schedule a "service end" event).
    """
    
    # The entity was served immediately upon request, as a
    # resource was available.
    SERVED_IMMEDIATELY = auto()
    
    # No resources were available; the entity has been placed
    # in the queue to wait.
    QUEUED = auto()

    # No resources were available, and the queue was also full.
    # The entity was rejected and has left the system (balking).
    REJECTED_QUEUE_FULL = auto()