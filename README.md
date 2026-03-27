# 🏠 FairShare: Mechanism Design for Constrained Room Allocation

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-FF4B4B.svg)](https://streamlit.io/)
[![SciPy](https://img.shields.io/badge/SciPy-Optimization-8CAAE6.svg)](https://scipy.org/)

**Live Demo:** https://fairdivisionlab-fd6majrlizgnvoa3y5fnui.streamlit.app/

---

## 📌 Problem: Allocation Under Fixed Pricing Constraints

In many real-world housing systems, especially student rentals, pricing is externally fixed by landlords through individual leases. However, agents exhibit heterogeneous preferences over non-price attributes such as space, lighting, noise, and private facilities.

This creates a structural mismatch:

> **Market prices are rigid, but subjective utilities are not.**

As a result, resource allocation becomes inefficient and often leads to interpersonal conflict.

---

## 🧠 Approach: Preference Alignment via Mechanism Design

FairShare reframes the problem as a **constrained allocation and compensation problem** rather than a pricing problem.

The system operates in three steps:

1. **Preference Elicitation**  
   Each agent submits a valuation vector representing their willingness to pay for each room.

2. **Optimal Assignment**  
   The allocation is computed using **Maximum Weight Bipartite Matching (Hungarian Algorithm)** to maximize total utility.

3. **Envy-Free Approximation**  
   Using **Sequential Least Squares Programming (SLSQP)**, the system finds a price vector that approximates an envy-free equilibrium.

4. **Side Payment Mechanism**  
   A zero-sum transfer scheme is computed to reconcile fixed market prices with subjective valuations, reducing envy and improving perceived fairness.

---

## ✨ Features

- Bilingual interface (English / Chinese)
- Minimalist UI for low-friction input
- Anonymous preference submission (designed for real roommate scenarios)
- Behavioral feedback (conflict index, compromise score)
- Local data storage for preference analysis

---

## ⚙️ Tech Stack

- Frontend: Streamlit  
- Optimization: SciPy (`linear_sum_assignment`, `minimize`)  
- Data: NumPy, Pandas  
- Storage: SQLite  

---

## 🔬 Research Perspective

This project explores how classical fair division concepts can be adapted to environments with **exogenous price constraints**.

It highlights the gap between:
- market-defined pricing  
- user-defined utility  

and proposes a practical mechanism to reduce inefficiency through preference alignment and decentralized compensation.

---

## 📎 Notes

This is not a pricing tool.  
It is a decision-support system for resolving allocation conflicts under real-world constraints.
