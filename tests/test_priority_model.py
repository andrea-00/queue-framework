# tests/test_priority_model.py

"""
Unit tests for the PriorityQueueModel class.

This file tests the core state logic of the PriorityQueueModel.
It verifies that:
1. The model serves entities based on the lowest priority number.
2. The model uses FIFO as a tie-breaker for entities with the
   same priority.
3. The model correctly fails if an entity lacks a '.priority' attribute.
4. The model correctly tracks per-priority KPIs.
"""

import pytest

# Import the classes we are testing and the constants
from queue_framework import (
    PriorityQueueModel,
    EntityState,
    RequestResult
)



class MockEntity:
    """
    A mock entity that satisfies the contract for
    PriorityQueueModel: a mutable .state attribute AND
    a .priority attribute.
    """
    def __init__(self, name="", priority=1):
        self.state = EntityState.IDLE
        self.name = name
        self.priority = priority  # Required by this model
    
    def __repr__(self):
        return f"MockEntity(name='{self.name}', p={self.priority})"



@pytest.fixture
def model_cap1() -> PriorityQueueModel:
    """Returns a fresh, single-server (capacity=1) PriorityQueueModel."""
    return PriorityQueueModel(capacity=1, start_time=0.0)



def test_initialization(model_cap1: PriorityQueueModel):
    """Test that the model initializes with its specific trackers."""
    assert model_cap1.capacity == 1
    assert len(model_cap1.queue) == 0  # The heap is a list
    assert len(model_cap1.users) == 0
    # Check that it has both the main and the priority-specific tracker
    assert hasattr(model_cap1, "kpi_tracker")
    assert hasattr(model_cap1, "priority_kpi_trackers")


def test_request_server_free(model_cap1: PriorityQueueModel):
    """Test 'request' when a server is available."""
    entity = MockEntity("e1", priority=1)
    result = model_cap1.request(entity, current_time=10.0)
    
    assert result == RequestResult.SERVED_IMMEDIATELY
    assert entity.state == EntityState.IN_SERVICE
    assert entity in model_cap1.users


def test_request_server_busy(model_cap1: PriorityQueueModel):
    """Test 'request' when the server is busy."""
    e1 = MockEntity("e1_server", priority=1)
    e2 = MockEntity("e2_queue", priority=5)
    
    model_cap1.request(e1, current_time=10.0) # Fill server
    result = model_cap1.request(e2, current_time=11.0) # Queue e2
    
    assert result == RequestResult.QUEUED
    assert e2.state == EntityState.WAITING_FOR_RESOURCE
    assert len(model_cap1.queue) == 1
    # Check heap structure: (priority, time, entity)
    assert model_cap1.queue[0] == (5, 11.0, e2)


def test_release_queue_empty(model_cap1: PriorityQueueModel):
    """Test 'release' when the queue is empty."""
    entity = MockEntity("e1", priority=1)
    model_cap1.request(entity, current_time=10.0)
    
    next_entity = model_cap1.release(entity, current_time=15.0)
    
    assert next_entity is None
    assert entity.state == EntityState.IDLE
    assert len(model_cap1.users) == 0


def test_priority_logic_over_fifo(model_cap1: PriorityQueueModel):
    """
    Test the core priority logic.
    - e1 fills the server.
    - e2 (LOW prio) enters the queue first.
    - e3 (HIGH prio) enters the queue second.
    - When e1 releases, e3 should be served (not e2).
    """
    e1 = MockEntity("e1_server", priority=1)
    e2 = MockEntity("e2_low_prio", priority=5)
    e3 = MockEntity("e3_high_prio", priority=1) # Higher prio (lower num)
    
    # Action (Phase 1: Load the system)
    model_cap1.request(e1, current_time=10.0)
    model_cap1.request(e2, current_time=11.0) # e2 (prio 5) enters queue
    model_cap1.request(e3, current_time=12.0) # e3 (prio 1) enters queue
    
    # Pre-check: The heap's top item (index 0) should be e3
    assert len(model_cap1.queue) == 2
    assert model_cap1.queue[0] == (1, 12.0, e3) # e3 is at the front
    
    # Action (Phase 2: Release and check Priority)
    next_entity = model_cap1.release(e1, current_time=15.0)
    
    # Assertions
    assert next_entity == e3  # Verifies Priority > FIFO
    assert e1.state == EntityState.IDLE
    assert e3.state == EntityState.IN_SERVICE
    assert e2.state == EntityState.WAITING_FOR_RESOURCE
    assert len(model_cap1.users) == 1
    assert e3 in model_cap1.users
    assert len(model_cap1.queue) == 1
    assert model_cap1.queue[0][2] == e2 # e2 is now at the front


def test_fifo_logic_within_priority(model_cap1: PriorityQueueModel):
    """
    Test the FIFO "tie-breaking" logic.
    - e1 fills the server.
    - e2 (prio 5) enters the queue first.
    - e3 (prio 5) enters the queue second.
    - When e1 releases, e2 should be served (not e3).
    """
    e1 = MockEntity("e1_server", priority=1)
    e2 = MockEntity("e2_prio5_first", priority=5)
    e3 = MockEntity("e3_prio5_second", priority=5)
    
    # Action (Load the system)
    model_cap1.request(e1, current_time=10.0)
    model_cap1.request(e2, current_time=11.0) # e2 (prio 5, time 11)
    model_cap1.request(e3, current_time=12.0) # e3 (prio 5, time 12)
    
    # Pre-check: The heap's top item should be e2 (due to earlier time)
    assert len(model_cap1.queue) == 2
    assert model_cap1.queue[0] == (5, 11.0, e2)
    
    # Action (Release and check FIFO)
    next_entity = model_cap1.release(e1, current_time=15.0)
    
    # Assertions
    assert next_entity == e2  # Verifies FIFO within priority
    assert e1.state == EntityState.IDLE
    assert e2.state == EntityState.IN_SERVICE
    assert e3.state == EntityState.WAITING_FOR_RESOURCE
    assert len(model_cap1.queue) == 1
    assert model_cap1.queue[0][2] == e3


def test_kpi_breakdown_exists(model_cap1: PriorityQueueModel):
    """
    Test that the per-priority KPI trackers are being populated.
    """
    e1 = MockEntity("e1_prio1", priority=1)
    e2 = MockEntity("e2_prio5", priority=5)
    
    # Run a mini-simulation
    model_cap1.request(e1, 1.0) # Served
    model_cap1.request(e2, 2.0) # Queued
    model_cap1.release(e1, 3.0) # e2 served
    model_cap1.release(e2, 4.0) # e2 released
    
    # Get final KPIs
    kpis = model_cap1.get_final_kpis(simulation_end_time=5.0)
    
    # Check that the breakdown structure exists and was populated
    assert "priority_breakdown" in kpis
    assert 1 in kpis["priority_breakdown"] # Key for prio 1
    assert 5 in kpis["priority_breakdown"] # Key for prio 5
    
    # Check that the trackers recorded the arrivals
    p1_stats = kpis["priority_breakdown"][1]
    p5_stats = kpis["priority_breakdown"][5]
    assert p1_stats["arrivals_and_throughput"]["total_arrivals"] == 1
    assert p5_stats["arrivals_and_throughput"]["total_arrivals"] == 1


def test_missing_priority_attribute(model_cap1: PriorityQueueModel):
    """
    Test that the model raises an AttributeError if the
    entity does not have the required '.priority' attribute.
    """
    # This mock entity is "bad" - it lacks '.priority'
    class BadEntity:
        def __init__(self):
            self.state = EntityState.IDLE
            
    bad_entity = BadEntity()
    
    # Using pytest.raises to assert that an error *is* thrown
    with pytest.raises(AttributeError):
        model_cap1.request(bad_entity, current_time=10.0)