import pandas as pd
import numpy as np


# =========================================================
# DATAFRAME DE ESFUERZOS
# =========================================================

def stress_to_dataframe(stress_results):

    data = []

    for elem_id, values in stress_results.items():

        data.append({
            "Elemento": elem_id,
            "Fuerza axial (N)": values["Fuerza"],
            "Area (m2)": values["Area"],
            "Esfuerzo axial (Pa)": values["Esfuerzo"],
            "Esfuerzo axial (MPa)": values["Esfuerzo"] / 1e6,
            "Esfuerzo admisible (MPa)": values["Esfuerzo_admisible"] / 1e6,
            "Relacion D/C": values["Relacion_D_C"],
            "Tipo": values["Tipo"],
            "Estado": values["Estado"]
        })

    return pd.DataFrame(data)


# =========================================================
# EXPORTAR UN SOLO CASO
# =========================================================

def export_results_to_excel(resultados, file_path="resultados.xlsx"):

    # =========================
    # DESPLAZAMIENTOS
    # =========================
    U = resultados["U"]

    df_U = pd.DataFrame(
        U,
        columns=["Desplazamiento"]
    )

    # =========================
    # REACCIONES
    # =========================
    R = resultados["R"]

    df_R = pd.DataFrame(
        R,
        columns=["Reaccion"]
    )

    # =========================
    # FUERZAS
    # =========================
    forces = resultados["forces"]

    df_forces = pd.DataFrame(
        list(forces.items()),
        columns=["Elemento", "Fuerza"]
    )

    # =========================
    # ESFUERZOS
    # =========================
    stress_results = resultados["stress"]

    df_stress = stress_to_dataframe(stress_results)

    # =========================
    # EXPORTAR
    # =========================
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:

        df_U.to_excel(
            writer,
            sheet_name="Desplazamientos",
            index=False
        )

        df_R.to_excel(
            writer,
            sheet_name="Reacciones",
            index=False
        )

        df_forces.to_excel(
            writer,
            sheet_name="Fuerzas",
            index=False
        )

        df_stress.to_excel(
            writer,
            sheet_name="Stress_Check",
            index=False
        )

    print(f"\n✅ Resultados exportados a: {file_path}")


# =========================================================
# EXPORTAR TODOS LOS CASOS
# =========================================================

def export_all_cases_to_excel(
    all_results,
    file_path="resultados_casos.xlsx"
):

    summary_data = []

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:

        # =====================================================
        # RECORRER CASOS
        # =====================================================
        for case_name, resultados in all_results.items():

            U = resultados["U"]
            R = resultados["R"]
            forces = resultados["forces"]
            stress_results = resultados["stress"]

            # =================================================
            # DESPLAZAMIENTOS
            # =================================================
            df_U = pd.DataFrame(
                U,
                columns=["Desplazamiento"]
            )

            # =================================================
            # REACCIONES
            # =================================================
            df_R = pd.DataFrame(
                R,
                columns=["Reaccion"]
            )

            # =================================================
            # FUERZAS
            # =================================================
            df_forces = pd.DataFrame(
                list(forces.items()),
                columns=["Elemento", "Fuerza"]
            )

            # =================================================
            # ESFUERZOS
            # =================================================
            df_stress = stress_to_dataframe(stress_results)

            # =================================================
            # EXPORTAR HOJAS
            # =================================================
            df_U.to_excel(
                writer,
                sheet_name=f"disp_{case_name}",
                index=False
            )

            df_R.to_excel(
                writer,
                sheet_name=f"react_{case_name}",
                index=False
            )

            df_forces.to_excel(
                writer,
                sheet_name=f"forces_{case_name}",
                index=False
            )

            df_stress.to_excel(
                writer,
                sheet_name=f"stress_{case_name}",
                index=False
            )

            # =================================================
            # RESUMEN DEL CASO
            # =================================================
            max_disp = float(np.max(np.abs(U)))

            max_force = max(
                abs(float(f))
                for f in forces.values()
            )

            elem_critico = max(
                forces,
                key=lambda k: abs(float(forces[k]))
            )

            # =================================================
            # ELEMENTO CRÍTICO POR ESFUERZO
            # =================================================
            elem_stress_critico = max(
                stress_results,
                key=lambda k: abs(
                    float(stress_results[k]["Esfuerzo"])
                )
            )

            max_stress = abs(
                float(
                    stress_results[
                        elem_stress_critico
                    ]["Esfuerzo"]
                )
            ) / 1e6

            # =================================================
            # CONTAR FAILS
            # =================================================
            n_fail = sum(
                1
                for v in stress_results.values()
                if v["Estado"] == "FAIL"
            )

            summary_data.append({

                "Caso": case_name,

                "Umax (m)": max_disp,

                "Fmax (N)": max_force,

                "Elemento crítico fuerza": elem_critico,

                "Stress max (MPa)": max_stress,

                "Elemento crítico stress":
                    elem_stress_critico,

                "Cantidad FAIL":
                    n_fail
            })

        # =====================================================
        # TABLA RESUMEN
        # =====================================================
        df_summary = pd.DataFrame(summary_data)

        df_summary.to_excel(
            writer,
            sheet_name="summary_cases",
            index=False
        )

    print(f"\n✅ Todos los casos exportados a: {file_path}")