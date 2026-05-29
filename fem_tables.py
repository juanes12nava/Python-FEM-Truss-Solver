"""Conversión de resultados FEM a DataFrames para Streamlit/Excel."""

import numpy as np
import pandas as pd

from fem_postprocess import obtener_stress_items


def displacements_dataframe(resultados, dim):
    U = resultados["U"]
    ndof = 2 if dim == 2 else 3
    rows = []
    for i in range(len(U) // ndof):
        ux = float(U[ndof * i])
        uy = float(U[ndof * i + 1])
        uz = 0.0 if dim == 2 else float(U[ndof * i + 2])
        row = {"Nodo": i + 1, "Ux (m)": ux, "Uy (m)": uy, "|U| (m)": float(np.sqrt(ux**2 + uy**2 + uz**2))}
        if dim == 3:
            row["Uz (m)"] = uz
            row = {"Nodo": row["Nodo"], "Ux (m)": ux, "Uy (m)": uy, "Uz (m)": uz, "|U| (m)": row["|U| (m)"]}
        rows.append(row)
    return pd.DataFrame(rows)


def reactions_dataframe(resultados):
    return pd.DataFrame({"DOF": range(1, len(resultados["R"]) + 1), "Reacción": resultados["R"]})


def forces_dataframe(resultados):
    rows = []
    for eid, force in resultados["forces"].items():
        force = float(force)
        if force > 1e-3:
            estado = "Tracción"
        elif force < -1e-3:
            estado = "Compresión"
        else:
            estado = "Neutro"
        rows.append({"Elemento": eid, "Fuerza (N)": force, "|F| (N)": abs(force), "Tipo": estado})
    return pd.DataFrame(rows)


def stress_dataframe(data, resultados):
    rows = []
    for eid, sigma, sigma_allow, dc, status, tipo in obtener_stress_items(data, resultados):
        rows.append(
            {
                "Elemento": eid,
                "σ axial (Pa)": sigma,
                "σ axial (MPa)": sigma / 1e6,
                "σ adm (Pa)": sigma_allow,
                "σ adm (MPa)": None if sigma_allow is None else sigma_allow / 1e6,
                "D/C": dc,
                "Estado": status,
                "Tipo": tipo,
            }
        )
    return pd.DataFrame(rows)
