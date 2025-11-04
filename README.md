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
* **Helpful Plotting Package (Optional):**
    * Includes functions (in the `analysis` package) to plot KPI distributions (histograms) and time-series data (step plots) using `matplotlib`.
* **Fully Tested:** High test coverage using `pytest`.

---

## Installation

This is a Git-based package.

#### 1. Standard Installation

To install the core, zero-dependency library:
```bash
pip install git+https://github.com/andrea-00/queue-framework.git@v1.1.0
```

#### 2. Full Installation (with Analysis)

To install the core library plus the optional analysis dependencies (`seaborn`, `matplotlib`), use the `[analysis]` extra:
```bash
pip install "git+https://github.com/andrea-00/queue-framework.git@v1.1.0#egg=queue_framework[analysis]"
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

## Plotting Example (Optional)
The optional `[analysis]` package provides functions to visualize KPI data from the Measure object.

See `examples/simulation_demo.ipynb` for the full, runnable code.
```python
import matplotlib.pyplot as plt
from queue_framework.analysis import plot_wait_time_histogram, plot_queue_length_over_time

# --- 1. Run a Simulation ---
# (Assume 'model' is your FIFOQueueModel after a long run)
measure_obj = model.kpi_tracker
kpis = model.get_final_kpis(simulation_end_time=sim.clock)


# --- 2. Create a Figure ---
fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(16, 6))

# Plot 1: Wait Time Distribution
plot_wait_time_histogram(
    measure=measure_obj,
    ax=axes[0]
)

# Plot 2: Queue Length Over Time
plot_queue_length_over_time(
    measure=measure_obj, 
    ax=axes[1]
)

plt.tight_layout()
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

* **Full Demo:** For a complete, runnable example, please see the `examples/simulation_demo.ipynb` notebook. It shows the full workflow, including data loading and plotting.
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