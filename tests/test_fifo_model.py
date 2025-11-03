# tests/test_fifo_model.py

"""
Unit tests for the FIFOQueueModel class.

This file tests the core state logic of the FIFOQueueModel,
ensuring that entities are served, queued, and released
correctly according to FIFO rules.

These tests run in isolation and do not require the
full simulation engine.
"""

import pytest

# Import the classes we are testing and the constants
from queue_framework import (
    FIFOQueueModel,
    EntityState,
    RequestResult
)

class MockEntity:
    """
    A minimal mock entity that satisfies the "contract"
    required by the QueueModel (a mutable .state attribute).
    """
    def __init__(self, name=""):
        self.state = EntityState.IDLE
        self.name = name  # For easier debugging in test outputs
        # Note: No .priority attribute is needed for the FIFO model
    
    def __repr__(self):
        return f"MockEntity(name='{self.name}')"



@pytest.fixture
def model_cap1() -> FIFOQueueModel:
    """
    Returns a fresh, single-server (capacity=1)
    FIFOQueueModel for each test.
    """
    return FIFOQueueModel(capacity=1, start_time=0.0)

@pytest.fixture
def model_cap2() -> FIFOQueueModel:
    """
    Returns a fresh, two-server (capacity=2)
    FIFOQueueModel for each test.
    """
    return FIFOQueueModel(capacity=2, start_time=0.0)




def test_initialization():
    """Test that the model initializes with correct default values."""
    model = FIFOQueueModel(capacity=5)
    
    assert model.capacity == 5
    assert model.start_time == 0.0
    assert len(model.queue) == 0
    assert len(model.users) == 0
    assert isinstance(model.kpi_tracker, object) # Check that it has a tracker


def test_request_server_free(model_cap1: FIFOQueueModel):
    """
    Test the 'request' method when a server is available.
    - Entity should be served immediately.
    - Entity state should change to IN_SERVICE.
    - Model 'users' should contain the entity.
    """
    entity = MockEntity()
    
    # Action
    result = model_cap1.request(entity, current_time=10.0)
    
    # Assertions
    assert result == RequestResult.SERVED_IMMEDIATELY
    assert entity.state == EntityState.IN_SERVICE
    assert len(model_cap1.users) == 1
    assert entity in model_cap1.users
    assert len(model_cap1.queue) == 0


def test_request_server_busy(model_cap1: FIFOQueueModel):
    """
    Test the 'request' method when the server is busy.
    - Entity should be queued.
    - Entity state should change to WAITING_FOR_RESOURCE.
    - Model 'queue' should contain the entity.
    """
    entity1 = MockEntity("e1")
    entity2 = MockEntity("e2")
    
    # Action (Fill the server)
    model_cap1.request(entity1, current_time=10.0)
    
    # Action (Request with a full server)
    result = model_cap1.request(entity2, current_time=11.0)
    
    # Assertions
    assert result == RequestResult.QUEUED
    assert entity1.state == EntityState.IN_SERVICE  # Original entity
    assert entity2.state == EntityState.WAITING_FOR_RESOURCE # New entity
    assert len(model_cap1.users) == 1
    assert len(model_cap1.queue) == 1
    assert model_cap1.queue[0][0] == entity2 # Check queue content


def test_release_queue_empty(model_cap1: FIFOQueueModel):
    """
    Test the 'release' method when the queue is empty.
    - The released entity's state should be IDLE.
    - The server pool ('users') should become empty.
    - The method should return None (no one was served from queue).
    """
    entity = MockEntity()
    model_cap1.request(entity, current_time=10.0)
    
    # Pre-check
    assert len(model_cap1.users) == 1
    
    # Action
    next_entity = model_cap1.release(entity, current_time=15.0)
    
    # Assertions
    assert next_entity is None
    assert entity.state == EntityState.IDLE
    assert len(model_cap1.users) == 0
    assert len(model_cap1.queue) == 0


def test_fifo_logic(model_cap1: FIFOQueueModel):
    """
    Test the core FIFO (First-In, First-Out) logic.
    - e1 fills the server.
    - e2 enters the queue first.
    - e3 enters the queue second.
    - When e1 releases, e2 should be served (not e3).
    """
    e1 = MockEntity("e1_server")
    e2 = MockEntity("e2_first_in_queue")
    e3 = MockEntity("e3_second_in_queue")
    
    # Action (Load the system)
    model_cap1.request(e1, current_time=10.0)
    model_cap1.request(e2, current_time=11.0)
    model_cap1.request(e3, current_time=12.0)
    
    # Pre-check
    assert e1.state == EntityState.IN_SERVICE
    assert e2.state == EntityState.WAITING_FOR_RESOURCE
    assert e3.state == EntityState.WAITING_FOR_RESOURCE
    assert len(model_cap1.queue) == 2
    assert model_cap1.queue[0][0] == e2 # e2 is at the front
    
    # Action (Release and check FIFO)
    next_entity = model_cap1.release(e1, current_time=15.0)
    
    # Assertions
    assert next_entity == e2  # Verifies FIFO
    assert e1.state == EntityState.IDLE
    assert e2.state == EntityState.IN_SERVICE
    assert e3.state == EntityState.WAITING_FOR_RESOURCE
    assert len(model_cap1.users) == 1
    assert e2 in model_cap1.users
    assert len(model_cap1.queue) == 1
    assert model_cap1.queue[0][0] == e3 # e3 is now at the front


def test_multi_capacity_logic(model_cap2: FIFOQueueModel):
    """
    Test that a model with capacity > 1 works correctly.
    - e1 and e2 should be served immediately.
    - e3 should be queued.
    - Releasing e1 should serve e3.
    """
    e1 = MockEntity("e1")
    e2 = MockEntity("e2")
    e3 = MockEntity("e3")
    
    # Action (Fill servers)
    res1 = model_cap2.request(e1, current_time=10.0)
    res2 = model_cap2.request(e2, current_time=11.0)
    
    assert res1 == RequestResult.SERVED_IMMEDIATELY
    assert res2 == RequestResult.SERVED_IMMEDIATELY
    assert len(model_cap2.users) == 2
    assert e1 in model_cap2.users and e2 in model_cap2.users

    # Action (Queue)
    res3 = model_cap2.request(e3, current_time=12.0)
    
    assert res3 == RequestResult.QUEUED
    assert len(model_cap2.queue) == 1
    
    # Action (Release)
    next_entity = model_cap2.release(e1, current_time=15.0)
    
    assert next_entity == e3
    assert len(model_cap2.users) == 2 # e2 and e3
    assert e3 in model_cap2.users
    assert len(model_cap2.queue) == 0


def test_release_invalid_entity(model_cap1: FIFOQueueModel):
    """Test that releasing an entity not in service raises a ValueError."""
    e1 = MockEntity("e1")
    e2 = MockEntity("e2_not_in_service")
    
    model_cap1.request(e1, 10.0) # e1 is in service
    
    # Attempt to release e2, which was never in service
    with pytest.raises(ValueError):
        model_cap1.release(e2, 15.0)