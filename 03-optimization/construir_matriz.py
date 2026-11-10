"""Matriz dirigida reanudable. Por defecto solo valida, sin usar la red."""
import argparse
import csv
import logging
import math
import os
from pathlib import Path
import random
import time

import pandas as pd
import requests
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent
URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
COLUMNAS = ["origen_id", "destino_id", "origen", "destino", "minutos", "kilometros"]
LOG = logging.getLogger(__name__)


class ErrorMatriz(RuntimeError):
    pass


def pares_esperados():
    return {(i, j) for i in range(20) for j in range(1, 21)
            if i != j and (i != 0 or j != 20)}


def cargar_nodos(path):
    nodos = pd.read_csv(path, sep=";", encoding="utf-8-sig")
    if len(nodos) != 21 or set(nodos["id"]) != set(range(21)):
        raise ErrorMatriz("Se requieren 21 nodos con IDs únicos de 0 a 20")
    for campo, limite in [("latitud", 90), ("longitud", 180)]:
        if not nodos[campo].map(lambda x: math.isfinite(float(x)) and abs(float(x)) <= limite).all():
            raise ErrorMatriz(f"Coordenadas inválidas: {campo}")
    return nodos.set_index("id")


def cargar_completados(path):
    if not path.exists():
        return set()
    with path.open(encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        if lector.fieldnames != COLUMNAS:
            raise ErrorMatriz("Cabecera de matriz inválida; archivo conservado")
        completados = set()
        for fila in lector:
            try:
                par = (int(fila["origen_id"]), int(fila["destino_id"]))
                valores = [float(fila[c]) for c in ("minutos", "kilometros")]
                if par not in pares_esperados() or par in completados or not all(
                    math.isfinite(v) and v > 0 for v in valores
                ) or None in fila or not fila["origen"] or not fila["destino"]:
                    raise ValueError()
            except (ValueError, TypeError, KeyError):
                raise ErrorMatriz(f"Fila inválida o duplicada {lector.line_num}; archivo conservado") from None
            completados.add(par)
    return completados


def waypoint(nodos, identificador):
    nodo = nodos.loc[identificador]
    return {"waypoint": {"location": {"latLng": {
        "latitude": float(nodo["latitud"]), "longitude": float(nodo["longitud"])
    }}}}


def validar_respuesta(datos, destinos):
    if not isinstance(datos, list):
        raise ErrorMatriz("Respuesta no es una lista")
    validos, vistos = {}, set()
    for elemento in datos:
        if not isinstance(elemento, dict):
            raise ErrorMatriz("Elemento inválido")
        indice = elemento.get("destinationIndex", 0)
        if type(indice) is not int or not 0 <= indice < len(destinos) or indice in vistos:
            raise ErrorMatriz("Índice de destino inválido o duplicado")
        vistos.add(indice)
        if elemento.get("originIndex", 0) != 0:
            raise ErrorMatriz("Índice de origen inválido")
        try:
            if elemento.get("status", {}).get("code", 0) != 0 or elemento.get("condition") != "ROUTE_EXISTS":
                raise ValueError()
            duracion = elemento["duration"]
            if not isinstance(duracion, str) or not duracion.endswith("s"):
                raise ValueError()
            segundos = float(duracion[:-1])
            metros = float(elemento["distanceMeters"])
            if not all(math.isfinite(v) and v > 0 for v in (segundos, metros)):
                raise ValueError()
            validos[destinos[indice]] = (segundos / 60, metros / 1000)
        except (KeyError, ValueError, TypeError, AttributeError):
            LOG.warning("Destino %s sin resultado válido", destinos[indice])
    return validos


def guardar(path, filas):
    # Solo append: los bytes de las conexiones existentes nunca se reescriben.
    nueva = not path.exists()
    if not nueva:
        with path.open("rb") as archivo:
            archivo.seek(-1, os.SEEK_END)
            if archivo.read(1) not in (b"\n", b"\r"):
                raise ErrorMatriz("CSV sin salto de línea final; revisar antes de continuar")
    with path.open("a", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
        if nueva:
            escritor.writeheader()
        for fila in filas:
            escritor.writerow(fila)
            archivo.flush()
            os.fsync(archivo.fileno())


def consultar_origen(nodos, origen, destinos, path, completados, session, api_key,
                     max_intentos=5, dormir=time.sleep):
    if not 1 <= len(destinos) <= 5 or len(set(destinos)) != len(destinos):
        raise ValueError("Cada lote debe tener entre 1 y 5 destinos únicos")
    pendientes = [d for d in destinos if (origen, d) not in completados]
    for intento in range(1, max_intentos + 1):
        if not pendientes:
            return
        motivo = "respuesta incompleta"
        try:
            with session.post(URL, headers={
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,status,condition",
            }, json={"origins": [waypoint(nodos, origen)],
                     "destinations": [waypoint(nodos, d) for d in pendientes],
                     "travelMode": "DRIVE", "routingPreference": "TRAFFIC_AWARE"},
                     timeout=(10, 120), verify=True) as respuesta:
                if respuesta.status_code >= 400:
                    codigo = respuesta.status_code
                    LOG.error("HTTP %s origen=%s intento=%s", codigo, origen, intento)
                    if codigo not in {408, 429, 500, 502, 503, 504}:
                        raise ErrorMatriz(f"HTTP {codigo}; corregir configuración antes de reanudar")
                    motivo = f"HTTP {codigo}"
                    resultados = {}
                else:
                    resultados = validar_respuesta(respuesta.json(), pendientes)
        except (requests.exceptions.RequestException, ValueError) as error:
            # No registrar texto de excepciones, URL, cabeceras ni cuerpo: pueden contener secretos.
            motivo = type(error).__name__
            resultados = {}
        filas = [{"origen_id": origen, "destino_id": d,
                  "origen": nodos.loc[origen, "municipio"],
                  "destino": nodos.loc[d, "municipio"],
                  "minutos": valores[0], "kilometros": valores[1]}
                 for d, valores in resultados.items()]
        if filas:
            guardar(path, filas)
            completados.update((origen, f["destino_id"]) for f in filas)
        pendientes = [d for d in pendientes if (origen, d) not in completados]
        if pendientes:
            LOG.warning("Origen=%s pendientes=%s intento=%s/%s causa=%s",
                        origen, pendientes, intento, max_intentos, motivo)
            if intento < max_intentos:
                dormir(min(60, 2 ** (intento - 1)) + random.uniform(0, 1))
    if pendientes:
        raise ErrorMatriz(f"Intentos agotados para origen {origen}, destinos {pendientes}; avance conservado")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consultar-google", action="store_true", help="Autoriza consultas facturables")
    parser.add_argument("--max-intentos", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.max_intentos <= 10:
        parser.error("--max-intentos debe estar entre 1 y 10")
    logging.basicConfig(filename=BASE / "matriz_errores.log", encoding="utf-8",
                        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        nodos = cargar_nodos(BASE / "nodos_completos.csv")
        path = BASE / "matriz_tiempos.csv"
        completados = cargar_completados(path)
        esperados = pares_esperados()
        print(f"Conexiones válidas: {len(completados)}/{len(esperados)}. Pendientes: {len(esperados - completados)}")
        if not args.consultar_google or completados == esperados:
            return 0
        load_dotenv(BASE / ".env", override=False)
        clave = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
        if not clave:
            raise ErrorMatriz("Falta GOOGLE_MAPS_API_KEY en el entorno o .env")
        # Exclusión entre procesos cooperantes; un cierre abrupto puede dejar este archivo.
        lock = BASE / ".matriz.lock"
        with lock.open("x") as archivo_lock:
            try:
                completados = cargar_completados(path)
                with requests.Session() as session:
                    for origen in range(20):
                        pendientes = sorted(d for o, d in esperados - completados if o == origen)
                        for inicio in range(0, len(pendientes), 5):
                            consultar_origen(nodos, origen, pendientes[inicio:inicio + 5], path,
                                             completados, session, clave, args.max_intentos)
                if cargar_completados(path) != esperados:
                    raise ErrorMatriz("La matriz aún está incompleta")
                print("Matriz completa y validada: 380 conexiones")
            finally:
                archivo_lock.close()
                lock.unlink()
        return 0
    except (ErrorMatriz, OSError, ValueError, KeyError) as error:
        LOG.error("Generación detenida: %s", type(error).__name__)
        print(f"Error: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

