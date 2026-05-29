# =========================================================
# ANALISIS DE ARMADURAS MEDIANTE FEM EN PYTHON
# VERSION REFACTORIZADA (ELIMINACIÓN DE DOFs)
# + EVALUACIÓN DE ESFUERZOS AXIALES OK / FAIL
# =========================================================

import numpy as np
import matplotlib.pyplot as plt

# =========================================================
# ---- UTILIDADES GENERALES ----
# =========================================================

def dof_map(node_id):
    return [2*(node_id-1), 2*(node_id-1)+1]


def dof_map_3d(node_id):
    return [3*(node_id-1), 3*(node_id-1)+1, 3*(node_id-1)+2]


# =========================================================
# ---- MATRICES DE RIGIDEZ ----
# =========================================================

def element_stiffness_2d(node_i, node_j, A, E):
    xi, yi = node_i
    xj, yj = node_j

    dx = xj - xi
    dy = yj - yi

    L = np.sqrt(dx**2 + dy**2)

    if L == 0:
        raise ValueError("Elemento con longitud cero detectado en análisis 2D.")

    c = dx / L
    s = dy / L

    k = (A * E / L) * np.array([
        [ c*c,  c*s, -c*c, -c*s],
        [ c*s,  s*s, -c*s, -s*s],
        [-c*c, -c*s,  c*c,  c*s],
        [-c*s, -s*s,  c*s,  s*s]
    ])

    return k


def element_stiffness_3d(node_i, node_j, A, E):
    xi, yi, zi = node_i
    xj, yj, zj = node_j

    dx = xj - xi
    dy = yj - yi
    dz = zj - zi

    L = np.sqrt(dx**2 + dy**2 + dz**2)

    if L == 0:
        raise ValueError("Elemento con longitud cero detectado en análisis 3D.")

    l = dx / L
    m = dy / L
    n = dz / L

    k = (A * E / L) * np.array([
        [ l*l,  l*m,  l*n, -l*l, -l*m, -l*n ],
        [ l*m,  m*m,  m*n, -l*m, -m*m, -m*n ],
        [ l*n,  m*n,  n*n, -l*n, -m*n, -n*n ],
        [-l*l, -l*m, -l*n,  l*l,  l*m,  l*n ],
        [-l*m, -m*m, -m*n,  l*m,  m*m,  m*n ],
        [-l*n, -m*n, -n*n,  l*n,  m*n,  n*n ]
    ])

    return k


# =========================================================
# ---- ENSAMBLAJE ----
# =========================================================

def assemble(K_global, k_element, ni, nj):
    dofs = dof_map(ni) + dof_map(nj)

    for i in range(4):
        for j in range(4):
            K_global[dofs[i], dofs[j]] += k_element[i, j]


def assemble_3d(K_global, k_element, ni, nj):
    dofs = dof_map_3d(ni) + dof_map_3d(nj)

    for i in range(6):
        for j in range(6):
            K_global[dofs[i], dofs[j]] += k_element[i, j]


# =========================================================
# ---- SOLVER POR ELIMINACIÓN ----
# =========================================================

def solve_elimination(K, F, supports, dim):
    """
    Solver estable por eliminación de DOFs.

    Filosofía de esta versión:
    - Mantener el comportamiento que antes sí corría.
    - Resolver con np.linalg.solve() cuando la estructura es estable.
    - Si Kff es singular o casi singular, usar np.linalg.pinv() como respaldo.
    - NO bloquear el análisis por mecanismos/inestabilidad académica.
    - Guardar advertencias para que la GUI o el reporte puedan mostrarlas.
    """
    ndof = len(F)
    warnings = []

    fixed_dofs = []

    for node, restr in supports.items():
        node_index = int(node) - 1

        if dim == 2:
            if len(restr) >= 1 and restr[0] == 1:
                fixed_dofs.append(node_index * 2 + 0)
            if len(restr) >= 2 and restr[1] == 1:
                fixed_dofs.append(node_index * 2 + 1)

        elif dim == 3:
            if len(restr) >= 1 and restr[0] == 1:
                fixed_dofs.append(node_index * 3 + 0)
            if len(restr) >= 2 and restr[1] == 1:
                fixed_dofs.append(node_index * 3 + 1)
            if len(restr) >= 3 and restr[2] == 1:
                fixed_dofs.append(node_index * 3 + 2)

    fixed_dofs = sorted(set(fixed_dofs))
    all_dofs = list(range(ndof))
    free_dofs = [d for d in all_dofs if d not in fixed_dofs]

    if len(free_dofs) == 0:
        raise ValueError("No existen grados de libertad libres para resolver el sistema.")

    K_ff = K[np.ix_(free_dofs, free_dofs)]
    F_f = F[free_dofs]

    if not np.all(np.isfinite(K_ff)):
        raise ValueError(
            "La matriz de rigidez contiene valores no válidos. "
            "Revise áreas, módulos de elasticidad, longitudes o conectividad."
        )

    if not np.all(np.isfinite(F_f)):
        raise ValueError(
            "El vector de cargas contiene valores no válidos. "
            "Revise la hoja de cargas del archivo Excel."
        )

    rank = np.linalg.matrix_rank(K_ff)
    n = K_ff.shape[0]

    try:
        cond_number = float(np.linalg.cond(K_ff))
    except Exception:
        cond_number = np.inf

    metodo = "solve"

    try:
        # Primero se intenta el método normal, que es el correcto para estructuras estables.
        U_f = np.linalg.solve(K_ff, F_f)
    except np.linalg.LinAlgError:
        metodo = "pinv"
        warnings.append(
            "La matriz reducida Kff es singular. Se usó pseudoinversa np.linalg.pinv(). "
            "Los resultados pueden corresponder a una estructura inestable o con mecanismos."
        )
        U_f = np.linalg.pinv(K_ff) @ F_f

    # Si la matriz no falló en solve(), pero está mal condicionada, no se bloquea.
    if rank < n and metodo != "pinv":
        warnings.append(
            f"Advertencia: Kff tiene rango menor al tamaño ({rank}/{n}). "
            "La estructura puede tener mecanismos."
        )

    if (not np.isfinite(cond_number)) or cond_number > 1e12:
        warnings.append(
            f"Advertencia: número de condición alto o no finito ({cond_number:.3e}). "
            "Puede existir inestabilidad numérica."
        )

    if not np.all(np.isfinite(U_f)):
        metodo = "pinv"
        warnings.append(
            "El método directo produjo desplazamientos no finitos. Se recalculó con pseudoinversa."
        )
        U_f = np.linalg.pinv(K_ff) @ F_f

    max_disp = float(np.max(np.abs(U_f))) if len(U_f) > 0 else 0.0
    if np.isfinite(max_disp) and max_disp > 1.0:
        warnings.append(
            f"Advertencia: desplazamiento máximo elevado ({max_disp:.3e} m). "
            "Revise apoyos, conectividad o unidades."
        )

    U = np.zeros(ndof)
    U[free_dofs] = U_f

    R = K @ U - F

    info = {
        "fixed_dofs": fixed_dofs,
        "free_dofs": free_dofs,
        "rank_Kff": int(rank),
        "size_Kff": int(n),
        "cond_Kff": cond_number,
        "method": metodo,
        "warnings": warnings,
    }

    return U, R, info


# =========================================================
# ---- FUERZAS INTERNAS ----
# =========================================================

def compute_element_forces(nodes, elements, U):
    forces = {}

    for element in elements:
        ni, nj = element["ni"], element["nj"]
        A, E = element["A"], element["E"]

        xi, yi = nodes[ni]
        xj, yj = nodes[nj]

        dx, dy = xj-xi, yj-yi
        L = np.sqrt(dx**2 + dy**2)

        if L == 0:
            raise ValueError(f"Elemento {element['id']} con longitud cero.")

        c, s = dx/L, dy/L

        dofs = dof_map(ni) + dof_map(nj)
        u_e = U[dofs]

        # Vector de transformación axial.
        # Convención:
        # fuerza positiva = tracción
        # fuerza negativa = compresión
        T = np.array([-c, -s, c, s])

        force = (A*E/L) * T @ u_e
        forces[element["id"]] = force

    return forces


def compute_element_forces_3d(nodes, elements, U):
    forces = {}

    for element in elements:
        ni, nj = element["ni"], element["nj"]
        A, E = element["A"], element["E"]

        xi, yi, zi = nodes[ni]
        xj, yj, zj = nodes[nj]

        dx, dy, dz = xj-xi, yj-yi, zj-zi
        L = np.sqrt(dx**2 + dy**2 + dz**2)

        if L == 0:
            raise ValueError(f"Elemento {element['id']} con longitud cero.")

        l, m, n = dx/L, dy/L, dz/L

        dofs = dof_map_3d(ni) + dof_map_3d(nj)
        u_e = U[dofs]

        # Convención:
        # fuerza positiva = tracción
        # fuerza negativa = compresión
        T = np.array([-l, -m, -n, l, m, n])

        force = (A*E/L) * T @ u_e
        forces[element["id"]] = force

    return forces


# =========================================================
# ---- EVALUACIÓN DE ESFUERZOS AXIALES OK / FAIL ----
# =========================================================

def evaluate_axial_stress(forces, elements, sigma_allowable=None, Fy=None, FS=1.5):
    """
    Calcula esfuerzo axial y verificación OK/FAIL para cada barra.

    Parámetros
    ----------
    forces : dict
        Diccionario de fuerzas internas por elemento.
        Ejemplo: {1: 12000.0, 2: -8000.0}

    elements : list[dict]
        Lista de elementos. Cada elemento debe tener:
        id, ni, nj, A, E

    sigma_allowable : float, opcional
        Esfuerzo admisible directo en Pa.
        Si se entrega este valor, se usa directamente.

    Fy : float, opcional
        Esfuerzo de fluencia del material en Pa.
        Si no se entrega sigma_allowable, se calcula:
        sigma_allowable = Fy / FS

    FS : float
        Factor de seguridad.

    Retorna
    -------
    stress_results : dict
        Diccionario con fuerza, área, esfuerzo, esfuerzo admisible,
        relación demanda/capacidad, tipo de fuerza y estado.
    """

    if sigma_allowable is None:
        if Fy is None:
            raise ValueError(
                "Debe ingresar sigma_allowable o Fy para evaluar esfuerzos OK/FAIL."
            )
        sigma_allowable = Fy / FS

    if sigma_allowable <= 0:
        raise ValueError("El esfuerzo admisible debe ser mayor que cero.")

    stress_results = {}

    for element in elements:
        elem_id = element["id"]
        A = element["A"]

        if A <= 0:
            raise ValueError(f"Área inválida en el elemento {elem_id}.")

        if elem_id not in forces:
            raise ValueError(f"No existe fuerza interna calculada para el elemento {elem_id}.")

        F = forces[elem_id]

        # Esfuerzo axial
        sigma = F / A

        # Relación demanda/capacidad
        demand_capacity = abs(sigma) / sigma_allowable

        # Estado
        if abs(sigma) <= sigma_allowable:
            status = "OK"
        else:
            status = "FAIL"

        # Tipo de fuerza
        if F > 0:
            force_type = "Tension"
        elif F < 0:
            force_type = "Compression"
        else:
            force_type = "Neutral"

        # Se guardan nombres en español y aliases en inglés/minúscula.
        # Esto evita romper la GUI o el writer si alguno espera otra convención.
        stress_results[elem_id] = {
            "Fuerza": F,
            "force": F,
            "Area": A,
            "area": A,
            "Esfuerzo": sigma,
            "sigma": sigma,
            "stress": sigma,
            "Esfuerzo_admisible": sigma_allowable,
            "sigma_allowable": sigma_allowable,
            "allowable": sigma_allowable,
            "Relacion_D_C": demand_capacity,
            "D/C": demand_capacity,
            "dc_ratio": demand_capacity,
            "Tipo": force_type,
            "tipo": force_type,
            "type": force_type,
            "Estado": status,
            "status": status
        }

    return stress_results


def get_critical_stress_summary(stress_results):
    """
    Genera un resumen rápido del elemento crítico por esfuerzo axial.

    Retorna:
    - elemento crítico
    - esfuerzo máximo absoluto
    - relación D/C máxima
    - cantidad de elementos fallados
    - estado global de la estructura
    """

    if not stress_results:
        return {
            "Elemento_critico": None,
            "Esfuerzo_max_abs": 0.0,
            "Relacion_D_C_max": 0.0,
            "Elementos_FAIL": 0,
            "Estado_global": "SIN DATOS"
        }

    critical_elem = max(
        stress_results,
        key=lambda eid: abs(stress_results[eid]["Esfuerzo"])
    )

    max_dc_elem = max(
        stress_results,
        key=lambda eid: stress_results[eid]["Relacion_D_C"]
    )

    fail_count = sum(
        1 for values in stress_results.values()
        if values["Estado"] == "FAIL"
    )

    global_status = "OK" if fail_count == 0 else "FAIL"

    return {
        "Elemento_critico": critical_elem,
        "Esfuerzo_max_abs": abs(stress_results[critical_elem]["Esfuerzo"]),
        "Elemento_D_C_max": max_dc_elem,
        "Relacion_D_C_max": stress_results[max_dc_elem]["Relacion_D_C"],
        "Elementos_FAIL": fail_count,
        "Estado_global": global_status
    }


# =========================================================
# ---- SOLVER PRINCIPAL 2D ----
# =========================================================

def run_2d_analysis(
    nodes,
    elements,
    loads,
    supports,
    sigma_allowable=None,
    Fy=250e6,
    FS=1.5
):
    n_dof = 2 * len(nodes)
    K_global = np.zeros((n_dof, n_dof))

    for element in elements:
        k = element_stiffness_2d(
            nodes[element["ni"]],
            nodes[element["nj"]],
            element["A"],
            element["E"]
        )
        assemble(K_global, k, element["ni"], element["nj"])

    F = np.zeros(n_dof)

    for node, (Fx, Fy_load) in loads.items():
        dofs = dof_map(node)

        # Se usa += para permitir acumular cargas si más adelante
        # se procesan varias cargas sobre el mismo nodo.
        F[dofs[0]] += Fx
        F[dofs[1]] += Fy_load

    U, R, solver_info = solve_elimination(K_global, F, supports, dim=2)

    forces = compute_element_forces(nodes, elements, U)

    stress = evaluate_axial_stress(
        forces=forces,
        elements=elements,
        sigma_allowable=sigma_allowable,
        Fy=Fy,
        FS=FS
    )

    stress_summary = get_critical_stress_summary(stress)

    return {
        "U": U,
        "R": R,
        "forces": forces,
        "stress": stress,
        "stress_summary": stress_summary,
        "solver_info": solver_info,
        "warnings": solver_info.get("warnings", [])
    }


# =========================================================
# ---- SOLVER PRINCIPAL 3D ----
# =========================================================

def run_3d_analysis(
    nodes,
    elements,
    loads,
    supports,
    sigma_allowable=None,
    Fy=250e6,
    FS=1.5
):
    n_dof = 3 * len(nodes)
    K_global = np.zeros((n_dof, n_dof))

    for element in elements:
        k = element_stiffness_3d(
            nodes[element["ni"]],
            nodes[element["nj"]],
            element["A"],
            element["E"]
        )
        assemble_3d(K_global, k, element["ni"], element["nj"])

    F = np.zeros(n_dof)

    for node, (Fx, Fy_load, Fz) in loads.items():
        dofs = dof_map_3d(node)

        # Se usa += para permitir acumular cargas si más adelante
        # se procesan varias cargas sobre el mismo nodo.
        F[dofs[0]] += Fx
        F[dofs[1]] += Fy_load
        F[dofs[2]] += Fz

    U, R, solver_info = solve_elimination(K_global, F, supports, dim=3)

    forces = compute_element_forces_3d(nodes, elements, U)

    stress = evaluate_axial_stress(
        forces=forces,
        elements=elements,
        sigma_allowable=sigma_allowable,
        Fy=Fy,
        FS=FS
    )

    stress_summary = get_critical_stress_summary(stress)

    return {
        "U": U,
        "R": R,
        "forces": forces,
        "stress": stress,
        "stress_summary": stress_summary,
        "solver_info": solver_info,
        "warnings": solver_info.get("warnings", [])
    }


# =========================================================
# ---- FUNCION GENERAL ----
# =========================================================

def run_fem_analysis(data):
    """
    Ejecuta el análisis FEM según la dimensión indicada en data["dim"].

    Entradas opcionales en data:
    - Fy: esfuerzo de fluencia en Pa. Por defecto 250e6 Pa.
    - FS: factor de seguridad. Por defecto 1.5.
    - sigma_allowable: esfuerzo admisible directo en Pa.
    """

    Fy = data.get("Fy", 250e6)
    FS = data.get("FS", 1.5)
    sigma_allowable = data.get("sigma_allowable", None)

    if data["dim"] == 2:
        return run_2d_analysis(
            data["nodes"],
            data["elements"],
            data["loads"],
            data["supports"],
            sigma_allowable=sigma_allowable,
            Fy=Fy,
            FS=FS
        )

    elif data["dim"] == 3:
        return run_3d_analysis(
            data["nodes"],
            data["elements"],
            data["loads"],
            data["supports"],
            sigma_allowable=sigma_allowable,
            Fy=Fy,
            FS=FS
        )

    else:
        raise ValueError("La dimensión del modelo debe ser 2 o 3.")


# =========================================================
# PRUEBA
# =========================================================

if __name__ == "__main__":

    nodes = {
        1: (0, 0),
        2: (4, 0),
        3: (2, 3)
    }

    elements = [
        {"id": 1, "ni": 1, "nj": 2, "A": 0.003, "E": 200e9},
        {"id": 2, "ni": 1, "nj": 3, "A": 0.003, "E": 200e9},
        {"id": 3, "ni": 2, "nj": 3, "A": 0.003, "E": 200e9}
    ]

    loads = {
        3: (0, -10000)
    }

    supports = {
        1: (1, 1),
        2: (1, 1)
    }

    data = {
        "nodes": nodes,
        "elements": elements,
        "loads": loads,
        "supports": supports,
        "dim": 2,

        # Parámetros para OK/FAIL
        "Fy": 250e6,   # Pa
        "FS": 1.5
    }

    res = run_fem_analysis(data)

    print("\nDesplazamientos:")
    print(res["U"])

    print("\nReacciones:")
    print(res["R"])

    print("\nFuerzas internas:")
    print(res["forces"])

    print("\nChequeo de esfuerzos OK/FAIL:")
    for elem_id, values in res["stress"].items():
        print(
            f"Elemento {elem_id}: "
            f"F = {values['Fuerza']:.3f} N | "
            f"sigma = {values['Esfuerzo']/1e6:.3f} MPa | "
            f"D/C = {values['Relacion_D_C']:.3f} | "
            f"{values['Tipo']} | "
            f"{values['Estado']}"
        )

    print("\nResumen crítico:")
    print(res["stress_summary"])
