# Fair Division Lab

A game-theoretic system for fair rent allocation and behavioral data collection.

---

## Overview

Fair Division Lab addresses a common real-world problem: how to fairly split rent among roommates when rooms differ in size, lighting, and amenities.

Each user submits private valuations for available rooms. The system computes an allocation and pricing scheme that satisfies an approximate envy-free condition, ensuring no participant prefers another room at the assigned price.

The platform also collects structured preference data, enabling analysis of fairness, conflict, and willingness to pay.

---

## Features

- Game-theoretic room allocation using the Hungarian algorithm  
- Envy-free pricing via constrained optimization  
- Anonymous multi-user input (V2 design)  
- Conflict index and behavioral insights  
- Local data storage using SQLite  

---

## Mathematical Model

The problem combines:

- Assignment optimization (maximum-weight matching)  
- Envy-free constraints  
- Constrained nonlinear optimization (SLSQP)

For each user i:

v_i(x_i) - p(x_i) >= v_i(x_j) - p(x_j)

---

## Tech Stack

- Python  
- Streamlit  
- NumPy / SciPy  
- SQLite  

---

## Run Locally

git clone https://github.com/lucaluo925/fair_division_lab.git  
cd fair_division_lab  

python3 -m venv .venv  
source .venv/bin/activate  

pip install streamlit numpy scipy pandas  

streamlit run app.py  

---

## Motivation

This project explores whether formal mathematical models can reduce perceived unfairness in real-life allocation problems. It also serves as a platform for collecting empirical data on human preferences.

---

## Future Work

- Room feature modeling (size, bathroom, lighting)  
- Regression analysis of willingness to pay  
- Multi-user synchronization  
- Public deployment  

---

## Author

Independent project combining applied mathematics, optimization, and behavioral analysis.
