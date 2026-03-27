# 🏠 FairShare: Mechanism Design for Constrained Room Allocation

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-FF4B4B.svg)](https://streamlit.io/)
[![SciPy](https://img.shields.io/badge/SciPy-Optimization-8CAAE6.svg)](https://scipy.org/)

**Live Demo:** https://fairdivisionlab-fd6majrlizgnvoa3y5fnui.streamlit.app/

---

## 📌 Background & Motivation

Standard microeconomic models often assume flexible pricing and idealized market conditions. In practice, however, many real-world systems operate under rigid constraints. 

In student housing, for example, rents are typically fixed through individual leases, while roommates may value rooms very differently based on qualitative factors such as privacy, natural light, or noise.

This creates a mismatch between market pricing and subjective utility.

FairShare was built to explore this gap. Rather than rejecting standard models, the project focuses on understanding their limits and extending them to constrained environments.

---

## 🧠 Approach

FairShare models room allocation as a **constrained assignment problem with compensation**.

The system follows four steps:

1. **Preference Elicitation**  
   Each user submits a valuation vector representing their willingness to pay for each room.

2. **Optimal Assignment**  
   A **Maximum Weight Bipartite Matching (Hungarian Algorithm)** is used to maximize total utility.

3. **Envy-Free Approximation**  
   A price vector is computed using **Sequential Least Squares Programming (SLSQP)** to approximate envy-free conditions.

4. **Side Payments**  
   A zero-sum transfer scheme is calculated to align fixed lease prices with subjective valuations.

---

## 📊 Observations

Initial use of the system highlights several consistent patterns:

- Rooms with similar market prices can have significantly different subjective values  
- Qualitative features (e.g., quietness, privacy) are often undervalued in fixed pricing  
- Small side payments can improve perceived fairness in constrained settings  

These observations suggest that allocation conflicts are often driven more by preference differences than by price levels themselves.

---

## 🔬 Behavioral Patterns

User valuation data shows **structured heterogeneity** in preferences:

- Some users focus on maximizing overall value  
- Others exhibit strong preferences for specific features  

This variation helps explain why simple equal splits often fail, and why compensation mechanisms can improve outcomes.

---

## ⚙️ Tech Stack

- Frontend: Streamlit (English / Chinese)  
- Optimization: SciPy (`linear_sum_assignment`, `minimize`)  
- Data: NumPy, Pandas  
- Storage: SQLite  

---

## 📎 Note

FairShare is both a practical tool and an exploratory project in applied optimization and mechanism design. It demonstrates how mathematical models can be used to support decision-making and reduce conflict in real-world constrained systems.
