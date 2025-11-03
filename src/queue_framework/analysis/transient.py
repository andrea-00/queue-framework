# src/queue_framework/analysis/transient.py

"""
Provides functions for transient analysis of simulation output.

This module contains the logic for:
1. Processing raw simulation output (from a Measure object) into
   batched data and key statistical metrics (xk_bar, Rk).
2. Automatically detecting the end of the transient phase (warm-up)
   using a stabilization heuristic.

This module requires 'numpy', which is an optional dependency for
the [analysis] feature set.
"""

import logging
from typing import Any, Dict, Optional

# Optional Dependency Handling
try:
    import numpy as np
except ImportError:
    log = logging.getLogger(__name__)
    log.error("NumPy dependency not found.")
    log.error("Please install it with: pip install queue-framework[analysis]")
    raise

from ..measure import Measure

log = logging.getLogger(__name__)


def calculate_transient_data(
    measure: Measure, 
    kpi_key: str = "wait_times", 
    num_batches: int = 100
) -> Optional[Dict[str, Any]]:
    """
    Calculates all necessary arrays for transient analysis from raw data.

    This function performs the "calculate-once" step. It takes the
    raw data list from a Measure object, batches it, and calculates
    the batch means, global mean, inverse cumulative mean (xk_bar),
    and relative error (Rk).

    Args:
        measure (Measure): The finalized Measure object containing the raw data.
        kpi_key (str): The string key of the raw data list to analyze
                       (e.g., "wait_times", "system_times").
        num_batches (int): The number of batches to split the raw data into.

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing the calculated
        NumPy arrays ('k_indices', 'batch_means', 'global_mean',
        'xk_bar', 'Rk'). Returns None if calculation fails
        (e.g., insufficient data).
    """
    
    log.debug(f"Calculating transient data for '{kpi_key}' "
              f"with {num_batches} batches...")
    
    # Data Extraction and Validation
    try:
        raw_data = np.array(getattr(measure, kpi_key))
        if len(raw_data) < num_batches:
            raise ValueError(
                f"Not enough data. Requested {num_batches} batches, "
                f"but only {len(raw_data)} total observations."
            )
    except (AttributeError, ValueError) as e:
        log.warning(f"Could not calculate transient data for '{kpi_key}': {e}")
        return None

    # Batching
    batches = np.array_split(raw_data, num_batches)
    batch_means = np.array([np.mean(b) for b in batches if b.size > 0])
    
    b = len(batch_means)  # Effective number of batches
    k_indices = np.arange(b)

    # Statistical Calculations
    # x_bar: Global mean of all batch means
    x_bar_global = np.mean(batch_means)

    # xk_bar: Inverse cumulative mean (mean of data[k:])
    cumsum_inv = np.cumsum(batch_means[::-1])[::-1]
    counts_inv = np.arange(b, 0, -1)
    xk_bar = cumsum_inv / counts_inv

    # Rk: Relative error of xk_bar vs x_bar_global
    if x_bar_global == 0:
        Rk = np.zeros_like(xk_bar) 
    else:
        Rk = (xk_bar - x_bar_global) / x_bar_global

    log.debug("Transient data calculation complete.")
    
    # Return Data Dictionary
    return {
        "k_indices": k_indices,
        "batch_means": batch_means,
        "global_mean": x_bar_global,
        "xk_bar": xk_bar,
        "Rk": Rk
    }


def find_transient_end(
    transient_data: Dict[str, Any], 
    threshold: float = 0.05, 
    patience: int = 5
) -> int:
    """
    Finds the transient end point (k*) using a robust heuristic.

    This heuristic finds the first batch index 'k' where the
    relative error |Rk| (compared to the global mean) drops
    below a given 'threshold' and *stays* below that threshold
    for a 'patience' number of subsequent batches.

    This avoids false positives from random noise.

    Args:
        transient_data (Dict[str, Any]): The data dictionary produced
            by calculate_transient_data().
        threshold (float): The relative error threshold to check against
            (e.g., 0.05 for 5%).
        patience (int): The number of subsequent batches that must also
            stay below the threshold to confirm stability.

    Returns:
        int: The estimated transient end batch index (k*).
             Returns 0 if no stable point is found.
    """
    
    try:
        Rk = transient_data['Rk']
        # We can't check the very end, as 'patience' would go out of bounds
        search_range = len(Rk) - patience
        
        if search_range <= 0:
            log.warning("Not enough data to run heuristic with "
                        f"patience={patience}. Returning k*=0.")
            return 0
            
        for k in range(search_range):
            # Check the window from k to k + patience
            window = Rk[k : k + patience]
            
            # If all values in the window are below the threshold...
            if np.all(np.abs(window) < threshold):
                log.debug(f"Heuristic found stable point at k*={k} "
                          f"(threshold={threshold}, patience={patience})")
                return k  # This is our stable point
                
        # If the loop finishes, no stable point was found
        log.warning(f"Heuristic could not find a stable point. "
                    "System may be unstable or run is too short. "
                    "Returning k*=0.")
        return 0

    except (KeyError, TypeError):
        log.error("Invalid transient_data dictionary passed to "
                  "find_transient_end. Returning k*=0.")
        return 0