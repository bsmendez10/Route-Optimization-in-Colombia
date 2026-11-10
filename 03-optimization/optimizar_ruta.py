"""ATSP abierto: Armenia -> 19 entregas -> Bogotá, sin restricciones horarias."""
import argparse
import csv
import json
import math
from pathlib import Path

import pyomo.environ as pyo
from pyomo.core.expr.numeric_expr import LinearExpression
from pyomo.contrib.appsi.solvers import Highs

from construir_matriz import cargar_nodos, cargar_completados

BASE = Path(__file__).resolve().parent


def cargar_datos(nodos_path, matriz_path):
    nodos = cargar_nodos(Path(nodos_path))
    cargar_completados(Path(matriz_path))  # Detecta filas inválidas y duplicadas.
    with Path(matriz_path).open(encoding='utf-8-sig', newline='') as archivo:
        arcos = {(int(f['origen_id']), int(f['destino_id'])):
                 (float(f['minutos']), float(f['kilometros']))
                 for f in csv.DictReader(archivo)}
    if not arcos:
        raise ValueError('La matriz no contiene conexiones')
    if nodos.loc[0, 'tipo'] != 'ORIGEN' or nodos.loc[20, 'tipo'] != 'DESTINO_FINAL':
        raise ValueError('Tipos de origen/destino incorrectos')
    if not (nodos.loc[list(range(1, 20)), 'tipo'] == 'ENTREGA').all():
        raise ValueError('Se requieren 19 nodos de entrega')
    return nodos, arcos


def crear_modelo(arcos):
    m = pyo.ConcreteModel(name='ATSP abierto Armenia-Bogotá')
    m.N = pyo.RangeSet(0, 20)
    m.D = pyo.RangeSet(1, 19)
    m.A = pyo.Set(dimen=2, initialize=sorted(arcos))
    m.x = pyo.Var(m.A, domain=pyo.Binary)
    m.u = pyo.Var(m.D, bounds=(1, 19))
    m.costo = pyo.Objective(expr=sum(arcos[i, j][0] * m.x[i, j] for i, j in m.A))
    # Grados fijan los extremos y una entrada/salida en cada entrega.
    m.entrada = pyo.Constraint(m.N, rule=lambda m, j:
        sum((m.x[i, k] for i, k in m.A if k == j), LinearExpression())
        == (0 if j == 0 else 1))
    m.salida = pyo.Constraint(m.N, rule=lambda m, i:
        sum((m.x[k, j] for k, j in m.A if k == i), LinearExpression())
        == (0 if i == 20 else 1))
    # MTZ: un arco entre entregas seleccionadas incrementa su orden.
    m.mtz = pyo.ConstraintList()
    for i, j in m.A:
        if i in m.D and j in m.D:
            m.mtz.add(m.u[i] - m.u[j] + 19 * m.x[i, j] <= 18)
    return m


def validar_ruta(ruta, arcos):
    if len(ruta) != 21 or ruta[0] != 0 or ruta[-1] != 20:
        raise ValueError('Extremos o longitud de ruta incorrectos')
    if len(set(ruta)) != 21 or set(ruta[1:-1]) != set(range(1, 20)):
        raise ValueError('Las 19 entregas deben visitarse exactamente una vez')
    if any((i, j) not in arcos for i, j in zip(ruta, ruta[1:])):
        raise ValueError('La ruta usa una conexión no disponible')


def reconstruir(m, arcos):
    seleccionados = [(i, j) for i, j in m.A if pyo.value(m.x[i, j]) > 0.5]
    sucesores = dict(seleccionados)
    if len(seleccionados) != 20 or len(sucesores) != 20:
        raise ValueError('Solución con grados inválidos')
    ruta = [0]
    while ruta[-1] != 20:
        siguiente = sucesores.get(ruta[-1])
        if siguiente is None or siguiente in ruta:
            raise ValueError('Solución desconectada o con subcircuito')
        ruta.append(siguiente)
    validar_ruta(ruta, arcos)
    return ruta


def resolver(arcos, limite=300):
    if limite <= 0:
        raise ValueError('El límite debe ser positivo')
    m = crear_modelo(arcos)
    solver = Highs()
    solver.config.time_limit = limite
    solver.config.mip_gap = 0.0
    solver.config.load_solution = False
    resultado = solver.solve(m)
    objetivo = resultado.best_feasible_objective
    cota = resultado.best_objective_bound
    informe = {'solver': 'HiGHS', 'terminacion': resultado.termination_condition.name,
               'objetivo_minutos': objetivo, 'cota_inferior_minutos': cota,
               'brecha_relativa': None, 'limite_segundos': limite,
               'incluye_restricciones_dos_jornadas': False}
    if objetivo is None or not math.isfinite(objetivo):
        raise RuntimeError(f'Sin solución factible: {informe}')
    informe['brecha_relativa'] = (abs(objetivo - cota) / max(abs(objetivo), 1e-10)
                                  if cota is not None and math.isfinite(cota) else None)
    resultado.solution_loader.load_vars()
    ruta = reconstruir(m, arcos)
    costo = sum(arcos[i, j][0] for i, j in zip(ruta, ruta[1:]))
    if not math.isclose(costo, objetivo, abs_tol=1e-5):
        raise ValueError('El costo reconstruido no coincide con el objetivo')
    return ruta, informe


def exportar(ruta, nodos, arcos, path):
    validar_ruta(ruta, arcos)
    acumulado = 0.0
    with Path(path).open('w', encoding='utf-8-sig', newline='') as archivo:
        campos = ['orden', 'nodo_id', 'municipio', 'tipo', 'minutos_desde_anterior',
                  'kilometros_desde_anterior', 'minutos_acumulados']
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        for orden, nodo in enumerate(ruta):
            minutos, km = arcos[ruta[orden - 1], nodo] if orden else (0.0, 0.0)
            acumulado += minutos
            escritor.writerow(dict(orden=orden, nodo_id=nodo, municipio=nodos.loc[nodo, 'municipio'],
                                   tipo=nodos.loc[nodo, 'tipo'], minutos_desde_anterior=minutos,
                                   kilometros_desde_anterior=km, minutos_acumulados=acumulado))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limite-segundos', type=float, default=300)
    args = parser.parse_args()
    nodos, arcos = cargar_datos(BASE / 'nodos_completos.csv', BASE / 'matriz_tiempos.csv')
    ruta, informe = resolver(arcos, args.limite_segundos)
    exportar(ruta, nodos, arcos, BASE / 'ruta_optima.csv')
    (BASE / 'resultado_atsp.json').write_text(json.dumps(informe, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(informe, indent=2, ensure_ascii=False))
    print(' -> '.join(nodos.loc[i, 'municipio'] for i in ruta))


if __name__ == '__main__':
    main()

