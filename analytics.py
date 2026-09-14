"""Analítica de Inventory usando pandas, numpy y matplotlib."""
from collections import defaultdict
from datetime import datetime, timedelta

import matplotlib
import numpy as np
import pandas as pd



def _parse_fecha(value):
    if isinstance(value, datetime):
        return value
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).replace(tzinfo=None)
    except ValueError:
        return datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S")


def _pendiente_relativa(valores):
    """Pendiente de regresión lineal normalizada por el promedio."""
    y = np.asarray(valores[-60:], dtype=float)
    n = y.size
    if n < 3:
        return 0.0
    promedio = float(np.mean(y))
    if promedio <= 0:
        return 0.0
    x = np.arange(n, dtype=float)
    pendiente = float(np.polyfit(x, y, 1)[0])
    return pendiente / max(promedio, 0.01)


def _clasificar_tendencia(serie):
    y = np.asarray(serie, dtype=float)
    if y.size < 3:
        return "estable"
    if float(np.mean(y)) == 0 or float(np.std(y)) == 0:
        return "estable"
    pendiente_relativa = _pendiente_relativa(y)
    if pendiente_relativa > 0.03:
        return "subiendo"
    if pendiente_relativa < -0.03:
        return "bajando"
    return "estable"


def metricas_por_producto(ventas_raw, productos):
    """Devuelve métricas en registros de Python, calculadas con pandas/numpy."""
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Pandas permite normalizar y agrupar las ventas sin mantener lógica de
    # tablas manual para cada consulta. Si no hay ventas, mantenemos el flujo
    # completamente compatible con una base recién creada.
    ventas_df = pd.DataFrame(ventas_raw, columns=["producto_id", "fecha", "cantidad"])
    por_producto = defaultdict(dict)
    if not ventas_df.empty:
        ventas_df["fecha"] = pd.to_datetime(ventas_df["fecha"], errors="coerce")
        ventas_df["cantidad"] = pd.to_numeric(ventas_df["cantidad"], errors="coerce")
        ventas_df = ventas_df.dropna(subset=["fecha", "cantidad"])
        if not ventas_df.empty:
            ventas_df["dia"] = ventas_df["fecha"].dt.normalize()
            agrupadas = ventas_df.groupby(["producto_id", "dia"], as_index=False)["cantidad"].sum()
            for row in agrupadas.itertuples(index=False):
                dia = row.dia.to_pydatetime().replace(tzinfo=None)
                por_producto[row.producto_id][dia] = float(row.cantidad)

    filas = []
    for prod in productos:
        pid = prod["id"]
        stock_actual = prod["stock_actual"]
        stock_minimo = prod.get("stock_minimo", 0) if isinstance(prod, dict) else prod["stock_minimo"]
        ventas = por_producto.get(pid, {})

        if not ventas:
            filas.append({
                "id": pid,
                "nombre": prod["nombre"],
                "stock_actual": stock_actual,
                "stock_minimo": stock_minimo,
                "venta_semanal_estimada": 0.0,
                "dias_para_agotarse": None,
                "tendencia": "sin datos",
                "alerta": bool(stock_actual <= stock_minimo),
            })
            continue

        primera_fecha = min(min(ventas), hoy)
        dias = (hoy - primera_fecha).days
        serie = np.array(
            [ventas.get(primera_fecha + timedelta(days=i), 0.0) for i in range(dias + 1)],
            dtype=float,
        )
        promedio_diario = float(np.mean(serie)) if serie.size else 0.0
        venta_semanal = round(promedio_diario * 7, 1)
        dias_agotarse = round(float(stock_actual) / promedio_diario, 1) if promedio_diario > 0 else None
        alerta = bool((dias_agotarse is not None and dias_agotarse <= 7) or stock_actual <= stock_minimo)

        filas.append({
            "id": pid,
            "nombre": prod["nombre"],
            "stock_actual": stock_actual,
            "stock_minimo": stock_minimo,
            "venta_semanal_estimada": venta_semanal,
            "dias_para_agotarse": dias_agotarse,
            "tendencia": _clasificar_tendencia(serie),
            "alerta": alerta,
        })
    return filas


def top_productos_por_venta(metricas, n=5):
    """Ordena usando un DataFrame de pandas y devuelve registros normales."""
    if not metricas:
        return []
    frame = pd.DataFrame(metricas)
    frame = frame.sort_values("venta_semanal_estimada", ascending=False).head(n)
    return frame.to_dict("records")
