# Mathematical model

The asymmetric traveling salesman path problem has origin 0, destination 20, and delivery nodes 1–19. The 380 allowed arcs consist of 19 origin-to-delivery arcs, 342 arcs between distinct deliveries, and 19 delivery-to-destination arcs.

The binary variable x[i,j] selects arc i → j. The objective minimizes the sum of c[i,j] × x[i,j], where c is estimated driving time. Exactly one selected arc leaves the origin and one enters the destination. Each delivery has one incoming and one outgoing arc.

For arcs between deliveries, the MTZ inequality is u[i] − u[j] + 19 x[i,j] ≤ 18, where 1 ≤ u[i] ≤ 19. On a selected arc, the order must increase. This excludes disconnected cycles and leaves a single path of 20 selected legs.

In optimizar_ruta.py, crear_modelo builds the Pyomo model, resolver invokes HiGHS through APPSI, reconstruir follows the selected arcs, and exportar writes the route. resultado_atsp.json records the objective, lower bound, and relative gap. The certificate applies to the saved matrix. Service windows, unloading, driver rest, and truck access belong to a separate operational model.
