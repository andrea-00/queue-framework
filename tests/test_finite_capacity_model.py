# tests/test_finite_capacity_model.py

"""
Unit tests for the FiniteCapacityModel class.

This file tests the core state logic of the FiniteCapacityModel.
It verifies two main things:
1. That the model correctly REJECTS new arrivals when the
   system (servers + queue) is full.
2. That the model *still* uses FIFO logic for its internal
   queue when space is available.
"""

import pytest

# Import the classes we are testing and the constants
from queue_framework import (
    FiniteCapacityModel,
    EntityState,
    RequestResult
)



class MockEntity:
    """A minimal mock entity with a .state attribute."""
    def __init__(self, name=""):
        self.state = EntityState.IDLE
        self.name = name
    
    def __repr__(self):
        return f"MockEntity(name='{self.name}')"



@pytest.fixture
def model_1_1() -> FiniteCapacityModel:
    """
    Returns a model with:
    - 1 server (capacity=1)
    - 1 queue slot (queue_capacity=1)
    Total system capacity (K) = 2
    """
    return FiniteCapacityModel(capacity=1, queue_capacity=1, start_time=0.0)

@pytest.fixture
def model_2_2() -> FiniteCapacityModel:
    """
    Returns a model with:
    - 2 servers (capacity=2)
    - 2 queue slots (queue_capacity=2)
    Total system capacity (K) = 4
    """
    return FiniteCapacityModel(capacity=2, queue_capacity=2, start_time=0.0)




def test_initialization():
    """Test that the model initializes with both capacity args."""
    model = FiniteCapacityModel(capacity=5, queue_capacity=10)
    
    assert model.capacity == 5
    assert model.queue_capacity == 10
    assert len(model.queue) == 0
    assert len(model.users) == 0

def test_initialization_zero_queue():
    """Test that a model with a zero-size queue is valid (G/G/c/c)."""
    model = FiniteCapacityModel(capacity=1, queue_capacity=0)
    e1 = MockEntity("e1")
    e2 = MockEntity("e2")
    
    # First entity should be served
    res1 = model.request(e1, 0.0)
    assert res1 == RequestResult.SERVED_IMMEDIATELY
    
    # Second entity should be rejected (no queue space)
    res2 = model.request(e2, 1.0)
    assert res2 == RequestResult.REJECTED_QUEUE_FULL


def test_request_server_free(model_1_1: FiniteCapacityModel):
    """Test the 'request' method when a server is free."""
    entity = MockEntity()
    result = model_1_1.request(entity, current_time=10.0)
    
    assert result == RequestResult.SERVED_IMMEDIATELY
    assert entity.state == EntityState.IN_SERVICE
    assert entity in model_1_1.users
    assert len(model_1_1.queue) == 0


def test_request_server_busy_queue_available(model_1_1: FiniteCapacityModel):
    """
    Test 'request' when the server is busy but the queue has space.
    - Entity should be QUEUED.
    """
    e1 = MockEntity("e1_server")
    e2 = MockEntity("e2_queue")
    
    # Action (Fill the server)
    model_1_1.request(e1, current_time=10.0)
    
    # Action (Request with a full server)
    result = model_1_1.request(e2, current_time=11.0)
    
    # Assertions
    assert result == RequestResult.QUEUED
    assert e2.state == EntityState.WAITING_FOR_RESOURCE
    assert len(model_1_1.users) == 1
    assert len(model_1_1.queue) == 1
    assert model_1_1.queue[0][0] == e2 # Check queue content


def test_release_queue_empty(model_1_1: FiniteCapacityModel):
    """Test 'release' when the queue is empty."""
    entity = MockEntity()
    model_1_1.request(entity, current_time=10.0)
    
    # Action
    next_entity = model_1_1.release(entity, current_time=15.0)
    
    # Assertions
    assert next_entity is None
    assert entity.state == EntityState.IDLE
    assert len(model_1_1.users) == 0
    assert len(model_1_1.queue) == 0


def test_request_reject_on_full_queue(model_1_1: FiniteCapacityModel):
    """
    Test the core "balking" (rejection) logic.
    - Model has cap=1, q_cap=1.
    - e1 should take the server.
    - e2 should take the queue slot.
    - e3 should be REJECTED.
    """
    e1 = MockEntity("e1_server")
    e2 = MockEntity("e2_queue")
    e3 = MockEntity("e3_rejected")
    
    # Action (Fill the system)
    model_1_1.request(e1, current_time=10.0) # Fills server
    model_1_1.request(e2, current_time=11.0) # Fills queue
    
    # Pre-check
    assert e1.state == EntityState.IN_SERVICE
    assert e2.state == EntityState.WAITING_FOR_RESOURCE
    assert len(model_1_1.users) == 1
    assert len(model_1_1.queue) == 1
    
    # Action (Request with a full system)
    result = model_1_1.request(e3, current_time=12.0)
    
    # Assertions
    assert result == RequestResult.REJECTED_QUEUE_FULL
    assert e3.state == EntityState.IDLE # State was never changed
    
    # Check that the model state is unchanged
    assert len(model_1_1.users) == 1
    assert len(model_1_1.queue) == 1
    assert model_1_1.queue[0][0] == e2 # e3 was not added


def test_fifo_logic_is_preserved(model_2_2: FiniteCapacityModel):
    """
    Test that the *internal queue* still obeys FIFO logic.
    - We use a (cap=2, q_cap=2) model.
    - e1, e2 fill servers.
    - e3, e4 fill queue (e3 enters first).
    - When e1 releases, e3 should be served (not e4).
    """
    e1 = MockEntity("e1_server")
    e2 = MockEntity("e2_server")
    e3 = MockEntity("e3_first_in_queue")
    e4 = MockEntity("e4_second_in_queue")
    
    # Action (Phase 1: Load the system)
    model_2_2.request(e1, current_time=10.0)
    model_2_2.request(e2, current_time=11.0)
    model_2_2.request(e3, current_time=12.0) # e3 enters queue
    model_2_2.request(e4, current_time=13.0) # e4 enters queue
    
    # Pre-check
    assert len(model_2_2.users) == 2
    assert len(model_2_2.queue) == 2
    assert model_2_2.queue[0][0] == e3 # e3 is at the front
    
    # Action (Release and check FIFO)
    next_entity = model_2_2.release(e1, current_time=15.0)
    
    # Assertions
    assert next_entity == e3  # Verifies FIFO
    assert e1.state == EntityState.IDLE
    assert e3.state == EntityState.IN_SERVICE
    assert e4.state == EntityState.WAITING_FOR_RESOURCE
    assert len(model_2_2.users) == 2 # e2 and e3
    assert len(model_2_2.queue) == 1
    assert model_2_2.queue[0][0] == e4 # e4 is now at the front