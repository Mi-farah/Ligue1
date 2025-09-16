# Mathematical Formalization (Corrected Version)

> **Note:** In the Ligue 1 system, only the visiting team makes a round trip (the home club does not travel). Below is a corrected mathematical reformulation of the problem, which is more faithful to reality and simpler to model.

---

## 1. Problem Data

### Sets

- **T**: Set of teams (e.g., 20 teams)
- **W**: Set of weeks/matchdays (e.g., 38)
- **M**: Set of matches (each team plays 1 match per week, alternating home/away)

### Parameters

For each pair of teams $(i, j) \in T \times T$ with $i \neq j$:

- $e_{ij}^a$: CO₂ emissions for a round trip by plane from $j \rightarrow i \rightarrow j$
- $e_{ij}^t$: CO₂ emissions for a round trip by train from $j \rightarrow i \rightarrow j$
- $t_{ij}^a$: Travel time by plane for the round trip $j \rightarrow i \rightarrow j$
- $t_{ij}^t$: Travel time by train for the round trip $j \rightarrow i \rightarrow j$
- $X$: Target reduction in total emissions (in %)

### Decision Variables

- $x_{ijkw} \in \{0,1\}$: 1 if team $i$ hosts team $j$ in week $w$, 0 otherwise
- $y_{ijw}^a \in \{0,1\}$: 1 if team $j$ travels to $i$ by plane in week $w$, 0 otherwise
- $y_{ijw}^t \in \{0,1\}$: 1 if team $j$ travels to $i$ by train in week $w$, 0 otherwise

---

## 2. Constraints

- **Each team plays exactly one match per week (either home or away):**

  $$
  \sum_{j \in T, j \neq i} x_{ijkw} + \sum_{j \in T, j \neq i} x_{jikw} = 1 \quad \forall i \in T, \forall w \in W
  $$
- **Each team faces every other team exactly once at home and once away during the season:**

  $$
  \sum_{w \in W} x_{ijkw} = 1 \quad \forall i, j \in T, i \neq j
  $$
- **Choice of transport mode for the visiting team:**

  $$
  y_{ijw}^a + y_{ijw}^t = x_{ijkw} \quad \forall i, j \in T, i \neq j, \forall w \in W
  $$

  (If $x_{ijkw} = 1$, then team $j$ travels to $i$ either by plane or by train.)
- **No team plays against itself:**

  $$
  x_{iikw} = 0 \quad \forall i \in T, \forall w \in W
  $$

---

## 3. Objective Function

- **Minimize total CO₂ emissions:**

  $$
  \text{Minimize} \quad \sum_{i, j \in T, i \neq j} \sum_{w \in W} \left( y_{ijw}^a \cdot e_{ij}^a + y_{ijw}^t \cdot e_{ij}^t \right)
  $$

  **Subject to:**

  $$
  \sum_{i, j \in T, i \neq j} \sum_{w \in W} \left( y_{ijw}^a \cdot e_{ij}^a + y_{ijw}^t \cdot e_{ij}^t \right) \leq (1 - X/100) \cdot E_{\text{total initial}}
  $$

  Where $E_{\text{total initial}}$ is the total emissions without optimization.
- **Optional:** Minimize total travel time:

  $$
  \text{Minimize} \quad \sum_{i, j \in T, i \neq j} \sum_{w \in W} \left( y_{ijw}^a \cdot t_{ij}^a + y_{ijw}^t \cdot t_{ij}^t \right)
  $$

---

## 4. Complexity and Solution Approaches

- **Complexity:** NP-hard problem, similar to the Travelling Tournament Problem (TTP).
- **Recommended Approaches:**
  - Mixed Integer Linear Programming (MILP): With PuLP or Pyomo + solver (Gurobi, CBC)
  - Genetic Algorithms: With DEAP to explore the solution space
  - Simulated Annealing: To avoid local minima
  - Specific heuristics: Such as "large neighborhood search" algorithms
