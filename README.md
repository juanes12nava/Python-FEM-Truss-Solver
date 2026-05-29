# FEM Solver - Armaduras 2D/3D

Aplicación FEM en Python para análisis de armaduras 2D y 3D.

## Ejecutar en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Estructura

- `app.py`: interfaz Streamlit.
- `fem_solver.py`: núcleo matricial FEM.
- `fem_excel_reader.py`: lectura de Excel.
- `fem_excel_writer.py`: exportación de resultados.
- `fem_postprocess.py`: esfuerzos, resúmenes, críticos y preparación de deformada.
- `fem_plotter.py`: gráficas 2D/3D.
- `fem_tables.py`: tablas para visualización.
- `run_from_excel.py`: ejecución por consola.

## Hojas esperadas en Excel

- `nodes`
- `elements`
- `loads`
- `supports`
- `control`
- `load_cases` opcional

