import tempfile
from pathlib import Path

import streamlit as st

from fem_excel_reader import read_excel_input
from fem_excel_writer import export_all_cases_to_excel, export_results_to_excel
from fem_plotter import plot_structure
from fem_postprocess import obtener_resumen_caso, resumen_casos_dataframe
from fem_solver import run_fem_analysis
from fem_tables import displacements_dataframe, forces_dataframe, reactions_dataframe, stress_dataframe


st.set_page_config(page_title="FEM Solver - Armaduras 2D/3D", layout="wide")
st.title("Análisis FEM de Armaduras 2D/3D")
st.info("""
Carga un archivo Excel con las siguientes hojas:

- nodes
- elements
- loads
- supports
- control

Opcional:
- load_cases

El software permite:
- análisis FEM 2D y 3D,
- visualización estructural,
- cálculo de fuerzas internas,
- evaluación axial OK/FAIL,
- exportación de resultados.
""")
st.caption("Lectura desde Excel · Solver matricial · Esfuerzos axiales · OK/FAIL · Visualización")

uploaded_file = st.sidebar.file_uploader("Cargar archivo Excel", type=["xlsx"])
run_all = st.sidebar.checkbox("Ejecutar todos los casos", value=True)
show_forces = st.sidebar.checkbox("Mostrar fuerzas en la gráfica", value=True)

if uploaded_file is None:
    st.info("Carga un archivo Excel con las hojas nodes, elements, loads, supports, control y opcionalmente load_cases.")
    st.stop()

with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
    tmp.write(uploaded_file.getbuffer())
    temp_path = tmp.name

try:
    data = read_excel_input(temp_path)
except Exception as exc:
    st.error(f"Error leyendo el archivo: {exc}")
    st.stop()

st.sidebar.success(f"Modelo cargado: {data['dim']}D")
st.sidebar.write(f"Nodos: {len(data['nodes'])}")
st.sidebar.write(f"Elementos: {len(data['elements'])}")
st.sidebar.write(f"Casos: {len(data['load_cases'])}")

case_names = list(data["load_cases"].keys())
selected_case = st.sidebar.selectbox("Caso de carga", case_names)

all_results = {}
try:
    if run_all:
        for case_name, case_loads in data["load_cases"].items():
            data_case = data.copy()
            data_case["loads"] = case_loads
            all_results[case_name] = run_fem_analysis(data_case)
    else:
        data_case = data.copy()
        data_case["loads"] = data["load_cases"][selected_case]
        all_results[selected_case] = run_fem_analysis(data_case)
except Exception as exc:
    st.error(f"Error durante el análisis FEM: {exc}")
    st.stop()

if selected_case not in all_results:
    selected_case = list(all_results.keys())[0]

resultados = all_results[selected_case]
data_case = data.copy()
data_case["loads"] = data["load_cases"][selected_case]

warnings = resultados.get("warnings", [])
if warnings:
    with st.expander("Advertencias del solver", expanded=True):
        for warning in warnings:
            st.warning(warning)

max_disp, nodo, max_force, elem_force, max_stress, elem_stress, fails = obtener_resumen_caso(resultados, data["dim"], data_case)

c1, c2, c3, c4 = st.columns(4)
c1.metric("U máx (m)", f"{max_disp:.3e}", f"Nodo {nodo}")
c2.metric("F máx (N)", f"{max_force:.2f}", f"Elemento {elem_force}")
c3.metric("σ máx (MPa)", f"{max_stress/1e6:.3f}", f"Elemento {elem_stress}")
c4.metric("Elementos FAIL", str(fails))

left, right = st.columns([1.15, 1])

with left:
    st.subheader(f"Visualización - Caso {selected_case}")
    fig = plot_structure(data_case, resultados, selected_case, show_forces=show_forces)
    st.pyplot(fig, use_container_width=True)

with right:
    st.subheader("Resumen comparativo")
    st.dataframe(resumen_casos_dataframe(all_results, data), use_container_width=True)

st.subheader("Tablas del caso seleccionado")
tab1, tab2, tab3, tab4 = st.tabs(["Desplazamientos", "Reacciones", "Fuerzas", "Esfuerzos OK/FAIL"])

with tab1:
    st.dataframe(displacements_dataframe(resultados, data["dim"]), use_container_width=True)
with tab2:
    st.dataframe(reactions_dataframe(resultados), use_container_width=True)
with tab3:
    st.dataframe(forces_dataframe(resultados), use_container_width=True)
with tab4:
    st.dataframe(stress_dataframe(data_case, resultados), use_container_width=True)

st.subheader("Exportar resultados")
export_dir = Path(tempfile.mkdtemp())

if len(all_results) > 1:
    output_path = export_dir / "resultados_casos.xlsx"
    export_all_cases_to_excel(all_results, str(output_path))
    label = "Descargar resultados de todos los casos"
else:
    output_path = export_dir / f"resultados_{selected_case}.xlsx"
    export_results_to_excel(resultados, str(output_path))
    label = "Descargar resultados del caso"

with open(output_path, "rb") as file:
    st.download_button(
        label=label,
        data=file,
        file_name=output_path.name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
