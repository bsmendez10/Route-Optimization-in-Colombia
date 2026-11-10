# Route Optimization in Colombia

**Coffee Region and Valle del Cauca**

A logistics engineering case study on optimizing a delivery route from Armenia, through 19 municipalities in Valle del Cauca, to Bogotá. The project combines geospatial data, mathematical optimization, and a web application for the driver.

Select a numbered stop, mark a delivery complete, and watch the progress bar update. The demo uses fictional stops and travel times.

![Regional map of the earlier driver-facing application showing numbered stops and a road trace from Armenia to Bogotá](docs/case-study-map.png)

*Screenshot of the earlier driver-facing application. Road trace by OSRM. Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright).*

## Case study at a glance

The operation involved one truck delivering 1,007 water filters to 19 municipalities. The team previously sequenced deliveries manually. The project introduced a repeatable way to calculate the visit order from estimated driving times and give the driver a web interface to consult the route.

| Metric | Result |
| --- | --- |
| Delivery stops | 19 |
| Directed legs evaluated | 380 |
| Estimated driving time in the modular run | 1,549.02 minutes |
| HiGHS optimality gap for the saved matrix | 0% |

When both visit orders were evaluated on the same travel-time matrix, the later optimized order was **5 min 43 s shorter in estimated driving time** than the earlier optimized order. This was a comparison between two computed routes. Actual driving time and savings relative to manual planning were not measured.

## My contribution

I implemented a modular route-planning workflow in four stages: geocoding delivery addresses, building a directed travel-time matrix, solving for the visit order with Pyomo and HiGHS, and deploying an interactive route viewer to Netlify. I reviewed the delivery coordinates before generating the matrix, compared both optimized visit orders using the same travel-time estimates, and documented the mathematical model and reproduction steps.

## Workflow

| Stage | Input | Output |
| --- | --- | --- |
| 01 Geocoding | Delivery addresses and endpoint references | Reviewed coordinates and stable node IDs |
| 02 Travel-time matrix | 21 geocoded nodes | Estimated minutes and kilometers for 380 directed legs |
| 03 Optimization | Fixed endpoints, delivery nodes, and travel times | Optimized visit order and HiGHS solve report |
| 04 Web application | Ordered stops and delivery information | Map and delivery checklist served through Netlify |

The operational project used Google Geocoding and Routes API to obtain coordinates and estimated travel times. Pyomo formulates the asymmetric traveling salesman path problem, and HiGHS solves it. The web application displays the precomputed route.

## Run the synthetic example

**[Open the live demo](https://bsmendez10.github.io/Route-Optimization-in-Colombia/04-web-app/)** to explore the route diagram, inspect stops, and filter pending or completed deliveries. Progress is saved in your browser.

![Synthetic demo showing numbered stops, a selected delivery, and delivery progress](docs/route-demo.png)

*Screenshot of the synthetic demo with 8 of 19 deliveries marked complete.*

To reproduce the synthetic solution locally, use **Python 3.14** and run the following commands in PowerShell from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\03-optimization\optimizar_ruta.py
```

Dependency installation requires internet access. The optimization run uses the included synthetic files and makes no Google API calls. It writes `ruta_optima.csv` and `resultado_atsp.json` to `03-optimization`.

The demo has the same 21-node structure as the Colombian case, with fictional locations, labels, and costs. To view the precomputed demo locally, open `04-web-app/index.html` in your browser.

## What to inspect

- [Mathematical model and implementation](docs/model.md)
- [Pyomo and HiGHS optimizer](03-optimization/optimizar_ruta.py)
- [Matrix acquisition and validation code](03-optimization/construir_matriz.py)

The public example excludes operational addresses, credentials, and Google-derived datasets. The case-study results and synthetic demo are reported separately.
