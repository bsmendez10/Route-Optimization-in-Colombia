# Mathematical Model

This project models the delivery route as an **Asymmetric Traveling Salesman Path Problem (ATSPP)**. One truck leaves Armenia, visits each of the 19 delivery municipalities exactly once, and finishes in Bogotá.

## Sets and decision variables

| Symbol | Meaning |
| --- | --- |
| $s = 0$ | Origin in Armenia |
| $t = 20$ | Final destination in Bogotá |
| $D = \{1, \ldots, 19\}$ | Delivery nodes |
| $A$ | Set of 380 allowed directed arcs |
| $c_{ij}$ | Estimated driving time, in minutes, from node $i$ to node $j$ |
| $x_{ij}$ | Binary variable equal to 1 when arc $(i,j)$ is selected and 0 otherwise |
| $u_i$ | Continuous ordering variable for delivery node $i$, bounded between 1 and 19 |

The arc set contains 19 movements from Armenia to a delivery, 342 between distinct deliveries, and 19 from a delivery to Bogotá. Each direction has its own travel-time estimate.

## Objective

$$
\min Z = \sum_{(i,j)\in A} c_{ij}x_{ij}
$$

The objective minimizes the sum of the 20 selected driving legs. It excludes unloading, waiting, and rest.

## Fixed endpoints

$$
\sum_{j\in D} x_{sj} = 1
\qquad
\sum_{i\in D} x_{it} = 1
$$

Exactly one selected arc leaves Armenia and one enters Bogotá.

## One arrival and one departure per delivery

$$
\sum_{i:\,(i,j)\in A} x_{ij} = 1
\qquad \forall j\in D
$$

$$
\sum_{j:\,(i,j)\in A} x_{ij} = 1
\qquad \forall i\in D
$$

The first equation fixes a delivery node and counts the selected arcs that enter it. The second fixes a delivery node and counts the selected arcs that leave it.

**Example from the Colombian case.** In the sequence **Armenia → La Victoria → Obando**, the first leg is the single selected arrival at La Victoria. The second is its single selected departure. Every other candidate arc entering or leaving La Victoria has a value of zero.

## Subtour elimination

$$
u_i - u_j + 19x_{ij} \leq 18
\qquad \forall (i,j)\in A \text{ with } i,j\in D
$$

When a leg between deliveries is selected, the Miller–Tucker–Zemlin (MTZ) constraint requires $u_j \geq u_i + 1$. A separate cycle would require the order to keep increasing until it returned to its starting value. The MTZ constraints prevent those cycles, leaving one connected route from Armenia to Bogotá.

## Implementation in Pyomo and HiGHS

| Function | What it does |
| --- | --- |
| `crear_modelo` | Defines the variables, objective, degree constraints, and MTZ constraints in Pyomo. |
| `resolver` | Runs HiGHS through APPSI and records the best objective, lower bound, and relative gap. |
| `reconstruir` | Follows the selected arcs from the origin to the destination. |
| `exportar` | Writes the ordered route to `ruta_optima.csv`. |

See [the optimizer source](../03-optimization/optimizar_ruta.py).

The optimality certificate applies to the saved travel-time matrix. Customer time windows, unloading, driver rest, and truck access require additional operational constraints. The public demo uses synthetic locations and travel times.
