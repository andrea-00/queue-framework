# Queue Framework

[![Python CI (Test & Lint)](https://github.com/andrea-00/queue-framework/actions/workflows/python-test.yml/badge.svg)](https://github.com/andrea-00/queue-framework/actions/workflows/python-test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)

A lightweight, Python-native, zero-dependency library for simulating and analyzing resource-queue systems within a custom Discrete Event Simulator (DES).

## Core Philosophy: A "Headless" Design

This framework is intentionally **"headless"**—it **does not manage time or an event calendar**.

Its sole responsibility is to manage **state** (who is in the queue, who is being served) and **KPIs** (wait times, utilization, etc.). It is designed to be a "black box" component that you "plug in" to your own DES engine.

Your simulator handles the "when" (the event loop); this framework handles the "what" (the queueing logic).

---

## Key Features

* **Zero-Dependency Core:** The core logic (`FIFOQueueModel`, `Measure`, etc.) requires no external libraries.
* **Extensible & Object-Oriented:** Built on an abstract `BaseQueueModel` (Strategy Pattern), allowing you to easily add new queueing logic.
* **Pre-built Models:**
    * `FIFOQueueModel`: Standard First-In, First-Out (G/G/c).
    * `PriorityQueueModel`: A priority-based queue (using `heapq`).
    * `FiniteCapacityModel`: A FIFO queue with a limited waiting room (G/G/c/K), which rejects arrivals when full.
* **Rich KPI Tracking:** The `Measure` class automatically tracks 20+ key statistics, including:
    * Observation-based stats (wait times, service times) with confidence intervals.
    * Time-weighted stats (queue length, server utilization).
* **Powerful Analysis Package (Optional):**
    * **Advanced Plotting:** Includes functions to plot KPI evolution, moving averages, and Welch plots.
    * **Automatic Transient Detection:** Includes functions to automatically find the end of the warm-up period ($k^*$) using robust heuristics.
* **Fully Tested:** High test coverage using `pytest`.

---

## Installation

This is a Git-based package.

#### 1. Standard Installation

To install the core, zero-dependency library:
```bash
pip install git+https://github.com/andrea-00/queue-framework.git@v0.1.0
```

#### 2. Full Installation (with Analysis)

To install the core library plus the optional analysis dependencies (`numpy`, `pandas`, `matplotlib`), use the `[analysis]` extra:
```bash
pip install "git+https://github.com/andrea-00/queue-framework.git@v0.1.0#egg=queue_framework[analysis]"
```

#### 3. For Local Development

1. Clone this repository.
2. Install in "editable" mode with all extras:

```bash
git clone https://github.com/andrea-00/queue-framework.git
cd queue-framework
pip install -e ".[analysis,dev]"
```

---

## Quick Start: The Core "Contract"
This example shows how your simulator engine interacts with the framework.

```python
from queue_framework import FIFOQueueModel, EntityState, RequestResult

# 1. A mock entity (must have a .state attribute)
class MyEntity:
    def __init__(self, name):
        self.name = name
        self.state = EntityState.IDLE
    def __repr__(self):
        return self.name

# 2. Instantiate a model (e.g., 1 server)
model = FIFOQueueModel(capacity=1, start_time=0.0)

e1 = MyEntity("Entity 1")
e2 = MyEntity("Entity 2")

# --- Your Simulation Loop ---

# Time 0.0: e1 arrives.
# Your simulator calls request()
result_1 = model.request(entity=e1, current_time=0.0)

print(f"T=0.0: {e1.name} requests. Result: {result_1}")
# Output: T=0.0: Entity 1 requests. Result: RequestResult.SERVED_IMMEDIATELY
print(f"   -> {e1.name} state: {e1.state}")
# Output:   -> Entity 1 state: EntityState.IN_SERVICE

# Time 1.0: e2 arrives.
result_2 = model.request(entity=e2, current_time=1.0)

print(f"T=1.0: {e2.name} requests. Result: {result_2}")
# Output: T=1.0: Entity 2 requests. Result: RequestResult.QUEUED
print(f"   -> {e2.name} state: {e2.state}")
# Output:   -> Entity 2 state: EntityState.WAITING_FOR_RESOURCE

# Time 5.0: e1 finishes service.
# Your simulator calls release()
next_entity = model.release(entity=e1, current_time=5.0)

print(f"T=5.0: {e1.name} releases. State: {e1.state}")
# Output: T=5.0: Entity 1 releases. State: EntityState.IDLE

# The model automatically served e2 from the queue and returns it
print(f"   -> Model served: {next_entity}")
# Output:   -> Model served: Entity 2
print(f"   -> {e2.name} state: {e2.state}")
# Output:   -> Entity 2 state: EntityState.IN_SERVICE

# --- End of Simulation ---
kpis = model.get_final_kpis(simulation_end_time=10.0)

import pprint
pprint.pprint(kpis['wait_time'])
# Output:
# {'confidence_interval_95': (0.0, 0.0),
#  'count': 2,
#  'mean': 2.0,
#  'std_dev': 2.8284271247461903}
# (e1 waited 0.0s, e2 waited 4.0s. Mean = 2.0s)
```

---

## Advanced Analysis: Plotting & Transient Detection
The `analysis` package lets you automatically process and visualize the results from a `Measure` object.

See `examples/simulation_demo.ipynb` for the full, runnable code.
```python
import matplotlib.pyplot as plt
from queue_framework.analysis import (
    calculate_transient_data, 
    find_transient_end,
    plot_batch_means_over_time,
    plot_transient_analysis
)

# --- 1. Run a Long Simulation ---
# (Assume 'long_run_model' is your model after a 50,000-user run)
measure_obj = long_run_model.kpi_tracker
kpi_to_analyze = "wait_times"

# --- 2. Calculate Transient Data (Once) ---
# This does the heavy lifting (batching, xk_bar, Rk, etc.)
transient_data = calculate_transient_data(
    measure_obj, 
    kpi_key=kpi_to_analyze,
    num_batches=100
)

# --- 3. Find k* Automatically ---
# Find the batch index where |Rk| stays < 5% for 5 batches
k_star = find_transient_end(transient_data, threshold=0.05, patience=5)

print(f"Transient phase auto-detected to end at batch: k* = {k_star}")

# --- 4. Plot a Combined Analysis Figure ---
fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(14, 16))

# Plot 1: Moving Average (to visually confirm k*)
plot_batch_means_over_time(
    transient_data=transient_data,
    t_star_k=k_star,
    moving_avg_window=20,
    ax=axes[0]
)

# Plot 2: Relative Error (to quantify error)
plot_transient_analysis(
    transient_data=transient_data, 
    t_star_k=k_star,
    ax=axes[1]
)

plt.show()
```
This will produce a professional, two-panel chart showing the KPI evolution and the convergence analysis.

### Running Tests
To run the full test suite:

1. Ensure you have installed the development dependencies:
```bash
pip install -e ".[dev]"
```
2. Run `pytest` from the root directory:
```bash
pytest
```

---

## Where Users Can Get Help

* **Full Demo:** For a complete, runnable example, please see the `examples/tsp_demo.ipynb` notebook. It shows the full workflow, including data loading and plotting.
* **Bug Reports & Feature Requests:** If you find a bug or have an idea for a new strategy, please **[open an issue](https://github.com/andrea-00/queue-framework/issues)** on this repository.

## Who Maintains and Contributes

This project is currently maintained by **[Andrea Di Felice/andrea-00]**.

We welcome contributions! If you would like to contribute, please follow these steps:
1.  **Fork** this repository.
2.  Create a new branch.
3.  Commit your changes.
4.  Open a **Pull Request** with a clear description of your changes.

For more details, please see our (future) `CONTRIBUTING.md` file.

---

## License

This project is licensed under the **MIT License**. See the `LICENSE` file for full details.

`Copyright (c) 2025 Andrea Di Felice <andrealav2901@gmail.com>`