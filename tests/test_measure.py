# tests/test_measure.py

"""
Unit tests for the Measure class (src/queue_framework/measure.py).

This file tests the statistical calculation logic of the Measure
class in isolation, ensuring that KPIs like means, confidence
intervals, and time-weighted averages are calculated correctly.
"""

import pytest
from pytest import approx  # Import approx for floating point comparison

# Import the class we are testing
from queue_framework.measure import Measure


@pytest.fixture
def empty_measure() -> Measure:
    """Returns a default Measure object with capacity=1."""
    return Measure(capacity=1, start_time=0.0)


@pytest.fixture
def simple_measure() -> Measure:
    """
    Returns a Measure object with a few data points
    for testing statistical calculations.
    """
    m = Measure(capacity=1, start_time=0.0)
    
    # Manually add data for testing calculation functions
    # This data represents:
    # - 3 entities served
    # - Wait times: 5, 10, 15 (mean=10)
    m.wait_times = [5.0, 10.0, 15.0]
    
    # - Service times: 8, 10, 12 (mean=10)
    m.service_times = [8.0, 10.0, 12.0]
    
    # - System times: 13, 20, 27 (mean=20)
    m.system_times = [13.0, 20.0, 27.0]
    
    # - Queue log:
    #   - 0 at T=0
    #   - 1 at T=5
    #   - 0 at T=10
    # Integral = (0*5) + (1*5) = 5
    # Avg over 20s = 5 / 20 = 0.25
    m.queue_length_log = [
        (0.0, 0),
        (5.0, 1),
        (10.0, 0)
    ]
    
    # - Server log:
    #   - 0 at T=0
    #   - 1 at T=2
    #   - 0 at T=12
    # Integral = (0*2) + (1*10) = 10
    # Avg over 20s = 10 / 20 = 0.5
    m.server_busy_log = [
        (0.0, 0),
        (2.0, 1),
        (12.0, 0)
    ]
    
    m.last_update_time = 20.0 # Define end time
    return m



def test_measure_initialization():
    """Test that the Measure class initializes correctly."""
    m = Measure(capacity=5, start_time=10.0)
    
    assert m.capacity == 5
    assert m.start_time == 10.0
    assert m.last_update_time == 10.0
    assert m.total_arrivals == 0
    assert m.wait_times == []
    
    # Check that initial state is logged
    assert m.queue_length_log == [(10.0, 0)]
    assert m.server_busy_log == [(10.0, 0)]


def test_get_final_kpis_on_empty_data(empty_measure: Measure):
    """
    Test that get_final_kpis() runs without errors (e.g.,
    division by zero) when no data has been logged.
    """
    # Call KPIs at T=100
    kpis = empty_measure.get_final_kpis(simulation_end_time=100.0)

    # Check that all core stats are 0, not crashing
    assert kpis["simulation_summary"]["total_duration"] == 100.0
    assert kpis["arrivals_and_throughput"]["total_arrivals"] == 0
    assert kpis["arrivals_and_throughput"]["total_served"] == 0
    
    # Check wait time stats
    wait_stats = kpis["wait_time"]
    assert wait_stats["mean"] == 0.0
    assert wait_stats["std_dev"] == 0.0
    assert wait_stats["count"] == 0
    assert wait_stats["confidence_interval_95"] == (0.0, 0.0)
    
    # Check time-weighted stats
    assert kpis["queue_length"]["time_weighted_average"] == 0.0
    assert kpis["server_utilization"]["average_utilization_percentage"] == 0.0


def test_internal_statistical_summary(empty_measure: Measure):
    """
    Test the _calculate_statistical_summary helper function
    with a known dataset.
    """
    data = [10.0, 12.0, 15.0, 11.0, 13.0] # n=5, mean=12.2
    
    # (Variance = 3.7, std_dev = 1.923538...)
    # (Margin of Error (95%) = 1.96 * (1.923538 / sqrt(5)) = 1.68605...)
    # (CI = 12.2 +/- 1.68605 -> [10.5139, 13.8860])

    stats = empty_measure._calculate_statistical_summary(data)

    assert stats["count"] == 5
    assert stats["mean"] == approx(12.2)
    assert stats["std_dev"] == approx(1.923538, abs=1e-5)

    ci_low, ci_high = stats["confidence_interval_95"]
    
    assert ci_low == approx(10.51394, abs=1e-5) 
    assert ci_high == approx(13.88605, abs=1e-5)


def test_internal_time_weighted_average(empty_measure: Measure):
    """
    Test the _calculate_time_weighted_average helper function
    with a known log.
    
    Log:
    - T=0 to T=10: value = 5 (Duration 10) -> Integral = 50
    - T=10 to T=15: value = 2 (Duration 5)  -> Integral = 10
    - T=15 to T=20: value = 8 (Duration 5)  -> Integral = 40
    
    Total Integral = 100
    Total Duration = 20
    Time-Weighted Average = 100 / 20 = 5.0
    """
    log_data = [
        (0.0, 5),   # Starts at 5
        (10.0, 2),  # Drops to 2 at T=10
        (15.0, 8)   # Rises to 8 at T=15
    ]
    total_duration = 20.0
    
    avg = empty_measure._calculate_time_weighted_average(log_data, total_duration)
    
    assert avg == approx(5.0)


def test_get_final_kpis_with_data(simple_measure: Measure):
    """
    Test the final KPI report generation using the
    'simple_measure' fixture which contains pre-populated data.
    """
    # Get KPIs at T=20 (as defined in the fixture)
    kpis = simple_measure.get_final_kpis(simulation_end_time=20.0)
    
    # Test Observation-Based Stats
    # Wait times: [5, 10, 15] -> mean=10
    assert kpis["wait_time"]["mean"] == approx(10.0)
    assert kpis["wait_time"]["count"] == 3
    
    # Service times: [8, 10, 12] -> mean=10
    assert kpis["service_time"]["mean"] == approx(10.0)
    
    # System times: [13, 20, 27] -> mean=20
    assert kpis["system_time"]["mean"] == approx(20.0)

    # Test Time-Weighted Stats
    # See fixture for calculation logic
    
    # Queue Length (Integral=5, Duration=20 -> Avg=0.25)
    assert kpis["queue_length"]["time_weighted_average"] == approx(0.25)
    
    # Server Utilization (Integral=10, Duration=20 -> AvgBusy=0.5)
    util_stats = kpis["server_utilization"]
    assert util_stats["time_weighted_average_busy_servers"] == approx(0.5)
    # (Capacity=1, AvgBusy=0.5 -> Utilization=50%)
    assert util_stats["average_utilization_percentage"] == approx(0.5)