# src/queue_framework/__init__.py

"""
Initializes the 'queue_framework' package.

This file sets up the package-level logger and "lifts" the
most important classes and enums to the top-level namespace.
This allows users to import core components directly, e.g.:

from queue_framework import BaseQueueModel, FIFOQueueModel, EntityState
"""

import logging

# Setup Package-Level Logger
# 1. Get a logger for the package.
# 2. Add a NullHandler to it by default.
#
# This prevents log messages (e.g., from log.debug()) from
# being printed to the console or stderr unless the *user*
# of the library explicitly configures their own logging setup.
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# Lift constants
from .constants import EntityState, RequestResult

# Lift the base class and KPI tracker
from .base_model import BaseQueueModel
from .measure import Measure

# Lift the concrete model implementations from the 'models' sub-package
from .models import (
    FIFOQueueModel,
    PriorityQueueModel,
    FiniteCapacityModel
)


# Define Public API with __all__
# This controls what 'from queue_framework import *' imports.
# It's a clean way to define what is public vs. internal.
__all__ = [
    # Constants
    "EntityState",
    "RequestResult",
    
    # Core Classes
    "BaseQueueModel",
    "Measure",
    
    # Concrete Models
    "FIFOQueueModel",
    "PriorityQueueModel",
    "FiniteCapacityModel"
]