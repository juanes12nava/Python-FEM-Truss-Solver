from fem_excel_writer import export_results_to_excel
from fem_excel_reader import read_excel_input
from fem_solver import run_fem_analysis


def main():

    file_path = "input_fem_template.xlsx"

    data = read_excel_input(file_path)

    all_results = {}

    print("\n====================================")
    print(" ANALISIS FEM POR CASOS DE CARGA")
    print("====================================")

    for case_name, case_loads in data["load_cases"].items():

        print(f"\n--- Ejecutando caso: {case_name} ---")

        data_case = data.copy()
        data_case["loads"] = case_loads

        resultados = run_fem_analysis(data_case)

        all_results[case_name] = resultados

        print("\nDesplazamientos:")
        print(resultados["U"])

        print("\nReacciones:")
        print(resultados["R"])

        print("\nFuerzas internas:")
        print(resultados["forces"])

    # Exporta por ahora el último caso ejecutado
    export_results_to_excel(resultados)

    print("\n====================================")
    print(" ANALISIS FINALIZADO")
    print("====================================")


if __name__ == "__main__":
    main()