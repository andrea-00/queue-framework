# src/queue_framework/analysis/plotting.py

"""
Provides optional plotting utilities for visualizing KPI data.

This module depends on 'matplotlib', 'seaborn', and 'pandas', which
are not part of the core framework's dependencies. These are
intended to be installed via the '[analysis]' extra:

    pip install queue-framework[analysis]

All functions are designed to work with a 'Measure' object as
their primary data source.
"""

import logging
from typing import Optional, List, Tuple, Dict, Any

# Optional Dependency Handling
try:
    import matplotlib.pyplot as plt 
    import matplotlib.axes          
    import seaborn as sns           
    from matplotlib.ticker import PercentFormatter
except ImportError:
    log = logging.getLogger(__name__)
    log.error("Analysis dependencies (matplotlib, seaborn, pandas, numpy) not found.")
    log.error("Please install them with: pip install queue-framework[analysis]")
    # We re-raise the error to stop execution if these functions are called
    raise

from ..measure import Measure

log = logging.getLogger(__name__)

# Set a nice default style for the plots
sns.set_theme(style="whitegrid")


def plot_wait_time_histogram(
    measure: Measure, 
    ax: Optional[matplotlib.axes.Axes] = None, 
    bins: int = 50, 
    kde: bool = True
) -> matplotlib.axes.Axes:
    """
    Generates a histogram and KDE plot of the recorded wait times.

    This is often the most important plot for understanding queue
    performance from an entity's perspective.

    Args:
        measure (Measure): The finalized Measure object containing data.
        ax (Optional[matplotlib.axes.Axes]): The matplotlib Axes
            on which to draw the plot. If None, a new Figure/Axes is created.
        bins (int): The number of bins for the histogram.
        kde (bool): Whether to overlay a Kernel Density Estimate plot.

    Returns:
        matplotlib.axes.Axes: The Axes object with the plot.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))

    if not measure.wait_times:
        log.warning("No wait times recorded. Plotting an empty histogram.")
        ax.set_title("Wait Time Distribution (No Data)")
        return ax

    wait_stats = measure.get_final_kpis(measure.last_update_time)['wait_time']
    mean_wait = wait_stats['mean']

    sns.histplot(
        measure.wait_times, 
        bins=bins, 
        kde=kde, 
        ax=ax,
        label="Wait Time Distribution"
    )
    
    ax.axvline(
        mean_wait, 
        color='red', 
        linestyle='--', 
        label=f"Mean Wait: {mean_wait:.2f}"
    )
    
    ax.set_title("Distribution of Wait Times")
    ax.set_xlabel("Wait Time (units)")
    ax.set_ylabel("Frequency / Density")
    ax.legend()
    
    log.debug(f"Plotted wait time histogram (n={wait_stats['count']})")
    
    return ax


def plot_queue_length_over_time(
    measure: Measure, 
    ax: Optional[matplotlib.axes.Axes] = None
) -> matplotlib.axes.Axes:
    """
    Generates a step plot showing the queue length over simulation time.

    This plot is excellent for visualizing the system's dynamic
    behavior and identifying periods of high congestion.

    Args:
        measure (Measure): The finalized Measure object containing data.
        ax (Optional[matplotlib.axes.Axes]): The matplotlib Axes
            on which to draw the plot. If None, a new Figure/Axes is created.

    Returns:
        matplotlib.axes.Axes: The Axes object with the plot.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 6))

    if len(measure.queue_length_log) < 2:
        log.warning("Not enough queue length data to plot. Plot will be empty.")
        ax.set_title("Queue Length Over Time (No Data)")
        return ax

    # A step plot requires x and y data.
    # We extract (timestamp, queue_length) from the log.
    data = measure.queue_length_log
    
    # We also need to add a final point at the end_time
    # to make the plot "complete" to the end of the simulation.
    end_time = measure.last_update_time
    if data[-1][0] < end_time:
        data.append((end_time, data[-1][1]))

    # Unzip the list of tuples into two lists
    times, lengths = zip(*data)

    ax.step(times, lengths, where='post')
    
    q_stats = measure.get_final_kpis(end_time)['queue_length']
    avg_len = q_stats['time_weighted_average']
    
    ax.axhline(
        avg_len,
        color='red',
        linestyle='--',
        label=f"Time-Avg Length: {avg_len:.2f}"
    )

    ax.set_title("Queue Length Over Time")
    ax.set_xlabel("Simulation Time")
    ax.set_ylabel("Entities in Queue")
    ax.set_ylim(bottom=0) # Queue length cannot be negative
    ax.set_xlim(left=measure.start_time)
    ax.legend()
    
    log.debug("Plotted queue length over time.")
    
    return ax

def plot_system_time_histogram(
    measure: Measure, 
    ax: Optional[matplotlib.axes.Axes] = None, 
    bins: int = 50, 
    kde: bool = True
) -> matplotlib.axes.Axes:
    """
    Generates a histogram and KDE plot of the recorded system times.

    "System time" (or "sojourn time") is the total time an entity
    spends in the system (wait time + service time). This is a key
    metric for the total entity experience.

    Args:
        measure (Measure): The finalized Measure object containing data.
        ax (Optional[matplotlib.axes.Axes]): The matplotlib Axes
            on which to draw the plot. If None, a new Figure/Axes is created.
        bins (int): The number of bins for the histogram.
        kde (bool): Whether to overlay a Kernel Density Estimate plot.

    Returns:
        matplotlib.axes.Axes: The Axes object with the plot.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))

    if not measure.system_times:
        log.warning("No system times recorded. Plotting an empty histogram.")
        ax.set_title("System Time Distribution (No Data)")
        return ax

    # Retrieve pre-calculated stats from the measure object
    system_stats = measure.get_final_kpis(measure.last_update_time)['system_time']
    mean_system_time = system_stats['mean']

    sns.histplot(
        measure.system_times, 
        bins=bins, 
        kde=kde, 
        ax=ax,
        label="System Time Distribution"
    )
    
    # Draw the mean line for reference
    ax.axvline(
        mean_system_time, 
        color='red', 
        linestyle='--', 
        label=f"Mean Time: {mean_system_time:.2f}"
    )
    
    ax.set_title("Distribution of Total Time in System")
    ax.set_xlabel("Time in System (units)")
    ax.set_ylabel("Frequency / Density")
    ax.legend()
    
    log.debug(f"Plotted system time histogram (n={system_stats['count']})")
    
    return ax


def plot_server_utilization_over_time(
    measure: Measure, 
    as_percentage: bool = True,
    ax: Optional[matplotlib.axes.Axes] = None
) -> matplotlib.axes.Axes:
    """
    Generates a step plot showing server utilization over simulation time.

    This plot shows the number of busy servers, either as an
    absolute count or as a percentage of total capacity. It is
    invaluable for understanding resource efficiency.

    Args:
        measure (Measure): The finalized Measure object containing data.
        as_percentage (bool): If True, plots utilization as a percentage
            (0.0 to 1.0). If False, plots the absolute count
            of busy servers (0 to capacity).
        ax (Optional[matplotlib.axes.Axes]): The matplotlib Axes
            on which to draw the plot. If None, a new Figure/Axes is created.

    Returns:
        matplotlib.axes.Axes: The Axes object with the plot.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 6))

    if len(measure.server_busy_log) < 2:
        log.warning("Not enough server utilization data to plot. Plot will be empty.")
        ax.set_title("Server Utilization Over Time (No Data)")
        return ax

    # Extract data from the log
    data = measure.server_busy_log
    end_time = measure.last_update_time
    
    # Add a final data point to make the step plot span the full time
    if data and data[-1][0] < end_time:
        data.append((end_time, data[-1][1]))

    times, busy_counts = zip(*data)

    # Determine data to plot (percentage or absolute)
    if as_percentage:
        if measure.capacity == 0:
            log.warning("Cannot plot utilization as percentage; capacity is 0.")
            util_data = [0.0] * len(busy_counts)
        else:
            # Convert absolute counts to percentages
            util_data = [count / measure.capacity for count in busy_counts]
        
        y_label = "Server Utilization (%)"
        y_limit = 1.0
        avg_stats = measure.get_final_kpis(end_time)['server_utilization']
        avg_line_val = avg_stats['average_utilization_percentage']
        avg_label = f"Time-Avg Utilization: {avg_line_val:.1%}"

    else:
        util_data = busy_counts
        y_label = "Busy Servers (Count)"
        y_limit = measure.capacity or 1.0 # Set reasonable upper limit
        avg_stats = measure.get_final_kpis(end_time)['server_utilization']
        avg_line_val = avg_stats['time_weighted_average_busy_servers']
        avg_label = f"Time-Avg Busy: {avg_line_val:.2f}"

    # Draw the main step plot
    ax.step(times, util_data, where='post')

    # Draw the time-weighted average line
    ax.axhline(
        avg_line_val,
        color='red',
        linestyle='--',
        label=avg_label
    )

    ax.set_title("Server Utilization Over Time")
    ax.set_xlabel("Simulation Time")
    ax.set_ylabel(y_label)
    ax.set_ylim(bottom=0, top=y_limit * 1.1) # Add 10% padding to top
    ax.set_xlim(left=measure.start_time)
    
    # If plotting percentage, format the y-axis ticks
    if as_percentage:
        ax.yaxis.set_major_formatter(PercentFormatter(1.0))

    ax.legend()
    
    log.debug("Plotted server utilization over time.")
    
    return ax