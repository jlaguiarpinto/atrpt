#atrpt/application/shared/aplicar_filtros.py

def aplicar_filtros(df, filtros):

    for coluna, op, valor in filtros:

        if valor is None or valor == "":
            continue

        if coluna not in df.columns:
            continue

        serie = df[coluna]

        if op == ">":
            df = df[serie > valor]

        elif op == "<":
            df = df[serie < valor]

        elif op == "=":
            df = df[serie == valor]

        elif op == ">=":
            df = df[serie >= valor]

        elif op == "<=":
            df = df[serie <= valor]

    return df