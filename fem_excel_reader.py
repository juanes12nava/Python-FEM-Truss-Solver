import pandas as pd


def read_excel_input(file_path):

    # =========================
    # LEER HOJAS PRINCIPALES
    # =========================
    nodes_df = pd.read_excel(file_path, sheet_name="nodes")
    elements_df = pd.read_excel(file_path, sheet_name="elements")
    loads_df = pd.read_excel(file_path, sheet_name="loads")
    supports_df = pd.read_excel(file_path, sheet_name="supports")
    control_df = pd.read_excel(file_path, sheet_name="control")

    # =========================
    # PARAMETROS DE CONTROL
    # =========================
    dim = int(control_df.iloc[0]["dim"])

    # Parámetros opcionales para el chequeo OK/FAIL.
    # Se aceptan desde la hoja control si existen.
    Fy = control_df.iloc[0].get("Fy", 250e6)
    FS = control_df.iloc[0].get("FS", 1.5)
    sigma_allowable = control_df.iloc[0].get("sigma_allowable", None)

    if pd.isna(Fy):
        Fy = 250e6
    if pd.isna(FS):
        FS = 1.5
    if pd.isna(sigma_allowable):
        sigma_allowable = None

    # =========================
    # NODES
    # =========================
    nodes = {}

    for _, row in nodes_df.iterrows():
        nid = int(row["id"])
        x = row["x"]
        y = row["y"]
        z = row.get("z", 0)

        if pd.isna(x) or pd.isna(y):
            raise ValueError(f"El nodo {nid} tiene coordenadas x o y vacías.")

        if dim == 2:
            nodes[nid] = (x, y)
        else:
            if pd.isna(z):
                z = 0
            nodes[nid] = (x, y, z)

    # =========================
    # ELEMENTS
    # =========================
    elements = []

    for _, row in elements_df.iterrows():
        eid = int(row["id"])
        ni = int(row["ni"])
        nj = int(row["nj"])
        A = row["A"]
        E = row["E"]

        if ni not in nodes:
            raise ValueError(f"El elemento {eid} usa el nodo inicial {ni}, pero ese nodo no existe.")

        if nj not in nodes:
            raise ValueError(f"El elemento {eid} usa el nodo final {nj}, pero ese nodo no existe.")

        if pd.isna(A) or A <= 0:
            raise ValueError(f"El elemento {eid} tiene un área A inválida.")

        if pd.isna(E) or E <= 0:
            raise ValueError(f"El elemento {eid} tiene un módulo E inválido.")

        elements.append({
            "id": eid,
            "ni": ni,
            "nj": nj,
            "A": A,
            "E": E
        })

    # =========================
    # LOADS BASE
    # =========================
    loads = {}

    for _, row in loads_df.iterrows():
        node = int(row["node"])

        if node not in nodes:
            raise ValueError(f"La carga está aplicada en el nodo {node}, pero ese nodo no existe.")

        Fx = row.get("Fx", 0)
        Fy = row.get("Fy", 0)
        Fz = row.get("Fz", 0)

        if pd.isna(Fx):
            Fx = 0
        if pd.isna(Fy):
            Fy = 0
        if pd.isna(Fz):
            Fz = 0

        if dim == 2:
            loads[node] = (Fx, Fy)
        else:
            loads[node] = (Fx, Fy, Fz)

    # =========================
    # SUPPORTS
    # =========================
    supports = {}

    for _, row in supports_df.iterrows():
        node = int(row["node"])

        if node not in nodes:
            raise ValueError(f"El apoyo está definido en el nodo {node}, pero ese nodo no existe.")

        rx = row.get("rx", 0)
        ry = row.get("ry", 0)
        rz = row.get("rz", 0)

        if pd.isna(rx):
            rx = 0
        if pd.isna(ry):
            ry = 0
        if pd.isna(rz):
            rz = 0

        if dim == 2:
            supports[node] = (int(rx), int(ry))
        else:
            supports[node] = (int(rx), int(ry), int(rz))

    # =========================
    # LOAD CASES
    # =========================
    load_cases = {}

    try:
        load_cases_df = pd.read_excel(file_path, sheet_name="load_cases")

        for case_name, group in load_cases_df.groupby("case"):
            case_loads = {}

            for _, row in group.iterrows():
                node = int(row["node"])

                if node not in nodes:
                    raise ValueError(
                        f"En el caso {case_name}, la carga está aplicada en el nodo {node}, "
                        f"pero ese nodo no existe."
                    )

                Fx = row.get("Fx", 0)
                Fy = row.get("Fy", 0)
                Fz = row.get("Fz", 0)

                if pd.isna(Fx):
                    Fx = 0
                if pd.isna(Fy):
                    Fy = 0
                if pd.isna(Fz):
                    Fz = 0

                if dim == 2:
                    case_loads[node] = (Fx, Fy)
                else:
                    case_loads[node] = (Fx, Fy, Fz)

            load_cases[str(case_name)] = case_loads

    except ValueError:
        load_cases = {"BASE": loads}

    # =========================
    # RETURN DATA
    # =========================
    return {
        "nodes": nodes,
        "elements": elements,
        "loads": loads,
        "load_cases": load_cases,
        "supports": supports,
        "dim": dim
    }