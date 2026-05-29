"""Gráficas Matplotlib reutilizables para app Streamlit o GUI."""

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from fem_postprocess import (
    color_por_estado_stress,
    obtener_stress_items,
    preparar_desplazamientos_para_grafica,
)


def plot_structure(data, resultados, case_name="BASE", show_forces=True):
    """Retorna una figura Matplotlib de la estructura original y deformada."""
    nodes = data["nodes"]
    elements = data["elements"]
    U = resultados["U"]
    forces = resultados["forces"]
    dim = data["dim"]

    stress_items = obtener_stress_items(data, resultados)
    stress_lookup = {item[0]: item for item in stress_items}

    U_plot, scale, visual_warning = preparar_desplazamientos_para_grafica(nodes, U, dim)

    fig = plt.figure(figsize=(8, 5.5))

    if dim == 2:
        ax = fig.add_subplot(111)

        for element in elements:
            ni = element["ni"]
            nj = element["nj"]
            xi, yi = nodes[ni]
            xj, yj = nodes[nj]

            ax.plot([xi, xj], [yi, yj], linestyle="--", color="gray", linewidth=1)

            dof_i = [2 * (ni - 1), 2 * (ni - 1) + 1]
            dof_j = [2 * (nj - 1), 2 * (nj - 1) + 1]

            xi_def = xi + U_plot[dof_i[0]] * scale
            yi_def = yi + U_plot[dof_i[1]] * scale
            xj_def = xj + U_plot[dof_j[0]] * scale
            yj_def = yj + U_plot[dof_j[1]] * scale

            force = float(forces[element["id"]])
            color = color_por_estado_stress(force, stress_lookup.get(element["id"]))

            ax.plot([xi_def, xj_def], [yi_def, yj_def], color=color, linewidth=3)

            if show_forces:
                xm = (xi_def + xj_def) / 2
                ym = (yi_def + yj_def) / 2
                ax.text(
                    xm,
                    ym,
                    f"{force:.2f} N",
                    fontsize=8,
                    bbox=dict(facecolor="white", alpha=0.7, edgecolor="none", pad=1.5),
                )

        ax.set_title(f"Deformada 2D - Caso {case_name}")
        ax.axis("equal")
        ax.grid(True)

        if visual_warning:
            ax.text(
                0.02,
                0.02,
                "⚠ " + visual_warning,
                transform=ax.transAxes,
                fontsize=9,
                verticalalignment="bottom",
                bbox=dict(facecolor="white", alpha=0.85, edgecolor="orange", pad=4),
            )

    else:
        ax = fig.add_subplot(111, projection="3d")

        for element in elements:
            ni = element["ni"]
            nj = element["nj"]
            xi, yi, zi = nodes[ni]
            xj, yj, zj = nodes[nj]

            ax.plot([xi, xj], [yi, yj], [zi, zj], linestyle="--", color="gray", linewidth=1)

            dof_i = [3 * (ni - 1), 3 * (ni - 1) + 1, 3 * (ni - 1) + 2]
            dof_j = [3 * (nj - 1), 3 * (nj - 1) + 1, 3 * (nj - 1) + 2]

            xi_def = xi + U_plot[dof_i[0]] * scale
            yi_def = yi + U_plot[dof_i[1]] * scale
            zi_def = zi + U_plot[dof_i[2]] * scale
            xj_def = xj + U_plot[dof_j[0]] * scale
            yj_def = yj + U_plot[dof_j[1]] * scale
            zj_def = zj + U_plot[dof_j[2]] * scale

            force = float(forces[element["id"]])
            color = color_por_estado_stress(force, stress_lookup.get(element["id"]))

            ax.plot([xi_def, xj_def], [yi_def, yj_def], [zi_def, zj_def], color=color, linewidth=3)

            if show_forces:
                xm = (xi_def + xj_def) / 2
                ym = (yi_def + yj_def) / 2
                zm = (zi_def + zj_def) / 2
                ax.text(xm, ym, zm, f"{force:.2f} N", fontsize=8)

        ax.set_title(f"Deformada 3D - Caso {case_name}")

        if visual_warning:
            ax.text2D(
                0.02,
                0.02,
                "⚠ " + visual_warning,
                transform=ax.transAxes,
                fontsize=9,
                verticalalignment="bottom",
                bbox=dict(facecolor="white", alpha=0.85, edgecolor="orange", pad=4),
            )

    legend_elements = [
        Line2D([0], [0], color="red", lw=3, label="FAIL"),
        Line2D([0], [0], color="orange", lw=3, label="Tracción OK"),
        Line2D([0], [0], color="blue", lw=3, label="Compresión OK"),
        Line2D([0], [0], color="gray", lw=3, label="Neutro"),
        Line2D([0], [0], color="gray", lw=2, linestyle="--", label="Estructura original"),
    ]
    ax.legend(handles=legend_elements, loc="upper right")
    fig.tight_layout()
    return fig
