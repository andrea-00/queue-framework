# src/queue_framework/models/__init__.py

"""
Initializes the 'models' sub-package.

This file "lifts" the concrete queue model implementations
from their individual modules to this package level. This
allows for cleaner imports for users who wish to
access models directly from the sub-package, e.g.:

from queue_framework.models import FIFOQueueModel
"""

# Import concrete model classes from their respective modules
from .fifo_model import FIFOQueueModel
from .priority_model import PriorityQueueModel
from .finite_capacity_model import FiniteCapacityModel

# Define the public API of this sub-package for 'import *'
__all__ = [
    "FIFOQueueModel",
    "PriorityQueueModel",
    "FiniteCapacityModel"
]