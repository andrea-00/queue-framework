# src/queue_framework/measure.py

"""
Provides the Measure class, a data collection and statistical analysis
tool for the QueueModel.

This module is responsible for logging all state changes and events
(like arrivals, services, etc.) and calculating a comprehensive
set of Key Performance Indicators (KPIs) from that data.

It is designed to be a passive component; it only records data
when its 'log_...' methods are called by the QueueModel.
"""

import logging
import math
from typing import List, Tuple, Dict, Any, Optional

# Set up the module-level logger
log = logging.getLogger(__name__)


class Measure:
    """
    Collects, stores, and calculates KPIs for a queueing system.

    This class tracks individual observations (like wait times) and
    time-series data (like queue length over time) to provide a
    full statistical summary of a simulation run.

    Attributes:
        capacity (int): The total number of servers/resources in the model.
                        Required for calculating utilization.
        start_time (float): The simulation timestamp when this tracker was
                            initialized.
        
        # Observation-based data lists
        wait_times (List[float]): A list of all wait times recorded.
        service_times (List[float]): A list of all service times recorded.
        system_times (List[float]): A list of all total system sojourn times
                                   (wait + service).
        
        # Time-weighted data logs
        queue_length_log (List[Tuple[float, int]]): 
            A log of (timestamp, new_queue_length) tuples.
        server_busy_log (List[Tuple[float, int]]):
            A log of (timestamp, new_busy_server_count) tuples.

        # Simple counters
        total_arrivals (int): Total number of entities that arrived.
        total_waited (int): Total number of entities that had to wait (wait > 0).
        total_served (int): Total number of entities that completed service.
        
        last_update_time (float): The timestamp of the last logged event.
    """

    def __init__(self, capacity: int, start_time: float = 0.0):
        """
        Initializes the KPI tracker.

        Args:
            capacity (int): The total number of parallel resources (servers).
                            Must be > 0 to calculate utilization.
            start_time (float, optional): The simulation time at which
                                          tracking begins. Defaults to 0.0.
        """
        if capacity <= 0:
            log.warning(f"Measure initialized with capacity <= 0 ({capacity}). "
                        "Utilization KPIs will be zero.")
        
        self.capacity: int = capacity
        self.start_time: float = start_time
        self.last_update_time: float = start_time

        # Data Storage
        # Observation-based lists
        self.wait_times: List[float] = []
        self.service_times: List[float] = []
        self.system_times: List[float] = []

        # Time-weighted logs. Add initial state at start_time to
        # "anchor" the time-weighted calculations.
        self.queue_length_log: List[Tuple[float, int]] = [(start_time, 0)]
        self.server_busy_log: List[Tuple[float, int]] = [(start_time, 0)]

        # Simple counters
        self.total_arrivals: int = 0
        self.total_waited: int = 0
        self.total_served: int = 0
        
        log.debug(f"Measure tracker initialized (Capacity={capacity}, "
                  f"StartTime={start_time})")



    def log_arrival(self, time: float):
        """Logs the arrival of a new entity."""
        self.total_arrivals += 1
        self._update_last_time(time)
        log.debug(f"T={time:.2f}: Entity arrival logged. "
                  f"Total arrivals: {self.total_arrivals}")

    def log_queue_entry(self, time: float, current_queue_length: int):
        """Logs an entity entering the queue."""
        self.total_waited += 1
        self.queue_length_log.append((time, current_queue_length))
        self._update_last_time(time)
        log.debug(f"T={time:.2f}: Entity queued. "
                  f"New queue length: {current_queue_length}")
        
    def log_service_start(self, time: float, wait_time: float,
                          current_queue_length: int,
                          current_busy_servers: int):
        """Logs an entity starting service (after 0 or more wait)."""
        self.wait_times.append(wait_time)
        
        # Log state changes
        self.queue_length_log.append((time, current_queue_length))
        self.server_busy_log.append((time, current_busy_servers))
        self._update_last_time(time)
        log.debug(f"T={time:.2f}: Entity service started. "
                  f"Wait: {wait_time:.2f}, Q_len: {current_queue_length}, "
                  f"Busy: {current_busy_servers}")

    def log_service_end(self, time: float, service_time: float, 
                        system_time: float, current_busy_servers: int):
        """Logs an entity finishing service."""
        self.service_times.append(service_time)
        self.system_times.append(system_time)
        self.total_served += 1
        
        # Log state change
        self.server_busy_log.append((time, current_busy_servers))
        self._update_last_time(time)
        log.debug(f"T={time:.2f}: Entity service ended. "
                  f"Service time: {service_time:.2f}, "
                  f"Busy: {current_busy_servers}")
        
    

    def _update_last_time(self, time: float):
        """Internal helper to keep track of the latest event time."""
        self.last_update_time = max(self.last_update_time, time)

    def _calculate_statistical_summary(
        self, data: List[float], confidence: float = 0.95
    ) -> Dict[str, Any]:
        """
        Calculates a full statistical summary for a list of observations.
        
        Includes mean, std_dev, count, and confidence interval.
        Uses Z-score (1.96) for 95% CI, assuming n > 30, which is
        typical for simulation.
        """
        n = len(data)
        if n == 0:
            return {
                "mean": 0.0, "std_dev": 0.0, "count": 0,
                "confidence_interval_95": (0.0, 0.0)
            }

        mean = sum(data) / n
        
        if n > 1:
            variance = sum((x - mean) ** 2 for x in data) / (n - 1)
            std_dev = math.sqrt(variance)
        else:
            std_dev = 0.0 # Cannot calculate variance with one sample

        # --- Calculate Confidence Interval ---
        # Using Z-score for simplicity, which is a good approximation
        # for n > 30.
        # TODO: Could be extended to use t-distribution for smaller n
        
        z_score = 1.96  # For 95% confidence
        if confidence != 0.95:
            # This is a placeholder. A real implementation would use
            # a lookup table or math.erf to find other Z-scores.
            log.warning(f"CI calculation for confidence {confidence} "
                        "not implemented, defaulting to 95% (Z=1.96).")
            
        if n > 0:
            margin_of_error = z_score * (std_dev / math.sqrt(n))
            ci_low = mean - margin_of_error
            ci_high = mean + margin_of_error
        else:
            margin_of_error = 0.0
            ci_low = 0.0
            ci_high = 0.0

        return {
            "mean": mean,
            "std_dev": std_dev,
            "count": n,
            "confidence_interval_95": (ci_low, ci_high)
        }

    def _calculate_time_weighted_average(
        self, log_data: List[Tuple[float, int]], total_duration: float
    ) -> float:
        """
        Calculates the time-weighted average for a state variable.
        
        This computes the integral of (value * time_duration) over the
        total simulation, then divides by the total duration.
        """
        if total_duration == 0:
            return 0.0
        
        integral = 0.0
        last_time, last_value = self.start_time, 0
        
        # Use the provided log, starting from the initial state
        for time, value in log_data:
            duration = time - last_time
            integral += last_value * duration
            last_time, last_value = time, value
            
        # Add the final interval (from last event to end of simulation)
        final_duration = total_duration - (last_time - self.start_time)
        integral += last_value * final_duration
        
        return integral / total_duration

    

    def get_final_kpis(self, simulation_end_time: Optional[float] = None
                       ) -> Dict[str, Any]:
        """
        Calculates and returns the final dictionary of all KPIs.

        This method should be called *after* the simulation is complete.

        Args:
            simulation_end_time (Optional[float]): The final timestamp
                of the simulation. If not provided, uses the time of the
                last recorded event.

        Returns:
            Dict[str, Any]: A nested dictionary containing all KPIs.
        """
        if simulation_end_time is None:
            end_time = self.last_update_time
            log.warning(f"simulation_end_time not provided to "
                        f"get_final_kpis(). Using last event time "
                        f"{end_time}, which may skew time-weighted stats.")
        else:
            end_time = simulation_end_time

        total_duration = end_time - self.start_time
        if total_duration <= 0:
            log.warning("Total simulation duration is 0. Returning empty stats.")
            return {"error": "Total duration is 0"}

        log.info(f"Calculating final KPIs for total duration: "
                 f"{total_duration:.2f} (from {self.start_time:.2f} "
                 f"to {end_time:.2f})")

        
        # Observation-based stats
        wait_stats = self._calculate_statistical_summary(self.wait_times)
        service_stats = self._calculate_statistical_summary(self.service_times)
        system_stats = self._calculate_statistical_summary(self.system_times)
        
        # Time-weighted stats
        avg_queue_length = self._calculate_time_weighted_average(
            self.queue_length_log, total_duration)
        max_queue_length = max(val for _, val in self.queue_length_log) \
            if self.queue_length_log else 0
        
        avg_servers_busy = self._calculate_time_weighted_average(
            self.server_busy_log, total_duration)
        
        # Simple ratios
        avg_utilization = (avg_servers_busy / self.capacity) \
            if self.capacity > 0 else 0.0
            
        prob_wait = (self.total_waited / self.total_arrivals) \
            if self.total_arrivals > 0 else 0.0

        # Assemble Final Report
        return {
            "simulation_summary": {
                "start_time": self.start_time,
                "end_time": end_time,
                "total_duration": total_duration,
                "total_capacity": self.capacity
            },
            "arrivals_and_throughput": {
                "total_arrivals": self.total_arrivals,
                "total_served": self.total_served,
                "total_who_waited": self.total_waited,
                "probability_of_waiting": prob_wait
            },
            "wait_time": wait_stats,
            "service_time": service_stats,
            "system_time": system_stats,
            "queue_length": {
                "time_weighted_average": avg_queue_length,
                "max_observed": max_queue_length
            },
            "server_utilization": {
                "time_weighted_average_busy_servers": avg_servers_busy,
                "average_utilization_percentage": avg_utilization
            }
        }