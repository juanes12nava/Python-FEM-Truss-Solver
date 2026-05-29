"""
Funciones de postproceso para el software FEM de armaduras.

Este módulo concentra lógica que antes estaba mezclada con la GUI:
- normalización de resultados de esfuerzos,
- cálculo de esfuerzos de respaldo desde F/A,
- resúmenes críticos por caso,
- preparación segura de desplazamientos para visualización.
"""

import numpy as np


def obtener_stress_results(resultados):
    """Devuelve el bloque de esfuerzos del resultado FEM, aceptando varios nombres."""
    for key in ["stress", "stresses", "stress_results", "stress_check", "checks"]:
        if key in resultados and resultados[key] is not None:
            return resultados[key]
    return {}


def obtener_dato_stress(info, claves, default=None):
    """Lee un valor de esfuerzo de forma robusta, aceptando varios aliases."""
    if isinstance(info, dict):
        for key in claves:
            if key in info:
                return info[key]
    return default


def normalizar_stress_items(stress_results):
    """
    Convierte la salida de esfuerzos a una lista uniforme:
    (elemento, sigma, sigma_allowable, dc_ratio, status, tipo)
    """
    items = []

    if stress_results is None:
        return items

    if isinstance(stress_results, dict):
        iterable = stress_results.items()
    elif isinstance(stress_results, list):
        iterable = []
        for i, info in enumerate(stress_results, start=1):
            eid = obtener_dato_stress(info, ["element", "elemento", "id", "eid"], i)
            iterable.append((eid, info))
    else:
        return items

    for eid, info in iterable:
        if isinstance(info, dict):
            sigma = obtener_dato_stress(
                info,
                ["sigma", "stress", "esfuerzo", "Esfuerzo", "axial_stress", "sigma_axial"],
                0.0,
            )
            sigma_allow = obtener_dato_stress(
                info,
                [
                    "sigma_allowable",
                    "allowable",
                    "esfuerzo_admisible",
                    "Esfuerzo_admisible",
                    "sigma_adm",
                ],
                None,
            )
            dc = obtener_dato_stress(
                info,
                ["D/C", "dc", "dc_ratio", "ratio", "Relacion_D_C", "demanda_capacidad"],
                None,
            )
            status = obtener_dato_stress(
                info,
                ["status", "estado", "Estado", "ok_fail", "OK_FAIL"],
                None,
            )
            tipo = obtener_dato_stress(
                info,
                ["type", "tipo", "Tipo", "classification", "clasificacion"],
                None,
            )
        else:
            sigma = info
            sigma_allow = None
            dc = None
            status = None
            tipo = None

        sigma = float(sigma) if sigma is not None else 0.0

        if tipo is None:
            if sigma > 1e-9:
                tipo = "Tracción"
            elif sigma < -1e-9:
                tipo = "Compresión"
            else:
                tipo = "Neutro"

        if sigma_allow is not None:
            sigma_allow = float(sigma_allow)

        if dc is None and sigma_allow not in [None, 0]:
            dc = abs(sigma) / sigma_allow
        elif dc is not None:
            dc = float(dc)

        if status is None:
            if dc is None:
                status = "-"
            elif dc <= 1.0:
                status = "OK"
            else:
                status = "FAIL"

        items.append((eid, sigma, sigma_allow, dc, str(status).upper(), tipo))

    return items


def obtener_area_elemento(element):
    """Obtiene el área del elemento aceptando varios nombres posibles."""
    for key in ["A", "area", "Area", "AREA"]:
        if key in element and element[key] not in [None, ""]:
            try:
                return float(element[key])
            except Exception:
                pass
    return None


def obtener_esfuerzo_admisible(data, element=None):
    """Obtiene sigma admisible desde el elemento o desde datos globales."""
    element = element or {}

    for key in ["sigma_allowable", "sigma_adm", "allowable", "esfuerzo_admisible"]:
        if key in element and element[key] not in [None, ""]:
            try:
                return float(element[key])
            except Exception:
                pass

    for key in ["sigma_allowable", "sigma_adm", "allowable", "esfuerzo_admisible"]:
        if key in data and data[key] not in [None, ""]:
            try:
                return float(data[key])
            except Exception:
                pass

    fy = None
    fs = None
    for key in ["Fy", "fy", "FY"]:
        if key in element and element[key] not in [None, ""]:
            fy = element[key]
            break
        if key in data and data[key] not in [None, ""]:
            fy = data[key]
            break

    for key in ["FS", "fs", "factor_seguridad", "safety_factor"]:
        if key in element and element[key] not in [None, ""]:
            fs = element[key]
            break
        if key in data and data[key] not in [None, ""]:
            fs = data[key]
            break

    try:
        if fy is not None and fs not in [None, 0, ""]:
            return float(fy) / float(fs)
    except Exception:
        pass

    return None


def calcular_stress_items_desde_fuerzas(data, resultados):
    """Calcula sigma = F/A si el solver no entrega esfuerzos utilizables."""
    items = []
    forces = resultados.get("forces", {})

    for element in data.get("elements", []):
        eid = element.get("id")
        if eid not in forces:
            continue

        force = float(forces[eid])
        area = obtener_area_elemento(element)
        sigma = 0.0 if area in [None, 0] else force / area

        sigma_allow = obtener_esfuerzo_admisible(data, element)
        dc = None if sigma_allow in [None, 0] else abs(sigma) / sigma_allow

        if abs(sigma) <= 1e-9:
            tipo = "Neutro"
        elif sigma > 0:
            tipo = "Tracción"
        else:
            tipo = "Compresión"

        if dc is None:
            status = "-"
        elif dc <= 1.0:
            status = "OK"
        else:
            status = "FAIL"

        items.append((eid, sigma, sigma_allow, dc, status, tipo))

    return items


def obtener_stress_items(data, resultados):
    """Usa esfuerzos del solver; si vienen vacíos/cero, recalcula desde F/A."""
    stress_items = normalizar_stress_items(obtener_stress_results(resultados))
    hay_esfuerzo_real = any(abs(float(item[1])) > 1e-12 for item in stress_items)

    if not stress_items or not hay_esfuerzo_real:
        stress_items = calcular_stress_items_desde_fuerzas(data, resultados)

    return stress_items


def color_por_estado_stress(force, stress_info=None):
    """Color estándar para barras: FAIL, tracción, compresión o neutro."""
    status = None
    tipo = None

    if stress_info is not None:
        if isinstance(stress_info, dict):
            status = obtener_dato_stress(stress_info, ["status", "estado", "Estado", "ok_fail", "OK_FAIL"], None)
            tipo = obtener_dato_stress(stress_info, ["type", "tipo", "Tipo", "classification", "clasificacion"], None)
        elif isinstance(stress_info, tuple) and len(stress_info) >= 6:
            status = stress_info[4]
            tipo = stress_info[5]

    if status is not None and str(status).upper() == "FAIL":
        return "red"

    if tipo is not None:
        tipo_txt = str(tipo).lower()
        if "trac" in tipo_txt or "tens" in tipo_txt:
            return "orange"
        if "comp" in tipo_txt:
            return "blue"
        return "gray"

    if force > 1e-3:
        return "orange"
    if force < -1e-3:
        return "blue"
    return "gray"


def calcular_escala_deformada(nodes, U, dim):
    """Calcula escala automática para que la deformada no se salga de la gráfica."""
    try:
        coords = np.array(list(nodes.values()), dtype=float)
        if coords.size == 0:
            return 1.0

        geom_size = float(np.max(np.ptp(coords, axis=0)))
        if geom_size <= 0:
            geom_size = 1.0

        ndof = 2 if dim == 2 else 3
        U_arr = np.array(U, dtype=float).reshape((-1, ndof))
        max_u = float(np.max(np.linalg.norm(U_arr, axis=1)))

        if max_u <= 0 or not np.isfinite(max_u):
            return 1.0

        return 0.08 * geom_size / max_u
    except Exception:
        return 1.0


def preparar_desplazamientos_para_grafica(nodes, U, dim):
    """Prepara desplazamientos solo para graficar, sin alterar resultados reales."""
    try:
        U_plot = np.array(U, dtype=float).copy()
        coords = np.array(list(nodes.values()), dtype=float)
        geom_size = float(np.max(np.ptp(coords, axis=0))) if coords.size > 0 else 1.0

        if geom_size <= 0 or not np.isfinite(geom_size):
            geom_size = 1.0

        ndof = 2 if dim == 2 else 3
        U_arr = U_plot.reshape((-1, ndof))
        max_u = float(np.max(np.linalg.norm(U_arr, axis=1)))

        if not np.isfinite(max_u):
            return np.zeros_like(U_plot), 0.0, "Desplazamientos no finitos. Se grafica la estructura original."

        if max_u <= 0:
            return U_plot, 1.0, None

        if max_u > 10 * geom_size or max_u > 1e3:
            return (
                np.zeros_like(U_plot),
                0.0,
                "Posible mecanismo/inestabilidad: desplazamientos excesivos. Se muestra la geometría original coloreada.",
            )

        scale = calcular_escala_deformada(nodes, U_plot, dim)
        return U_plot, scale, None
    except Exception:
        return np.array(U, dtype=float).copy(), 1.0, None


def obtener_resumen_caso(resultados, dim, data=None):
    """Resumen numérico del caso: desplazamiento, fuerza, esfuerzo y FAIL."""
    U = resultados["U"]
    forces = resultados["forces"]
    stress_items = obtener_stress_items(data, resultados) if data is not None else normalizar_stress_items(obtener_stress_results(resultados))

    ndof_node = 2 if dim == 2 else 3
    num_nodes = len(U) // ndof_node

    max_disp = 0.0
    nodo_critico = 0

    for i in range(num_nodes):
        if dim == 2:
            ux = float(U[2 * i])
            uy = float(U[2 * i + 1])
            uz = 0.0
        else:
            ux = float(U[3 * i])
            uy = float(U[3 * i + 1])
            uz = float(U[3 * i + 2])

        mag = float(np.sqrt(ux**2 + uy**2 + uz**2))
        if mag > max_disp:
            max_disp = mag
            nodo_critico = i + 1

    max_force = 0.0
    elem_critico = None
    for eid, force in forces.items():
        abs_force = abs(float(force))
        if abs_force > max_force:
            max_force = abs_force
            elem_critico = eid

    max_stress = 0.0
    elem_stress = "-"
    num_fail = 0
    for eid, sigma, sigma_allow, dc, status, tipo in stress_items:
        abs_sigma = abs(float(sigma))
        if abs_sigma > max_stress:
            max_stress = abs_sigma
            elem_stress = eid
        if str(status).upper() == "FAIL":
            num_fail += 1

    return max_disp, nodo_critico, max_force, elem_critico, max_stress, elem_stress, num_fail


def resumen_casos_dataframe(all_results, data):
    """Genera un DataFrame con el resumen comparativo de todos los casos."""
    import pandas as pd

    rows = []
    dim = data["dim"]
    for case_name, resultados in all_results.items():
        max_disp, nodo, max_force, elem_force, max_stress, elem_stress, fails = obtener_resumen_caso(resultados, dim, data)
        rows.append(
            {
                "Caso": case_name,
                "U máx (m)": max_disp,
                "Nodo crítico": nodo,
                "F máx (N)": max_force,
                "Elem. F crítico": elem_force,
                "σ máx (Pa)": max_stress,
                "Elem. σ crítico": elem_stress,
                "FAIL": fails,
            }
        )
    return pd.DataFrame(rows)
