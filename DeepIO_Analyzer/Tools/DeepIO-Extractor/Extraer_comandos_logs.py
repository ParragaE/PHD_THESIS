import os
import re
import pandas as pd

def extraer_comandos_de_logs(directorio_base):
    # Definimos el patrón para capturar la línea completa del ejecutable
    # Busca la línea que empieza por "# exe: "
    patron = re.compile(r"# exe: (.*)")
    datos_extraidos = []

    # Recorremos recursivamente todos los archivos en la carpeta indicada
    for root, dirs, files in os.walk(directorio_base):
        for file in files:
            # Filtramos si el archivo es un log de texto (puedes ajustar esta condición)
            if file.endswith("_perf.txt"):
                ruta_completa = os.path.join(root, file)
                
                with open(ruta_completa, 'r', encoding='utf-8', errors='ignore') as f:
                    for linea in f:
                        match = patron.search(linea)
                        if match:
                            comando = match.group(1).strip()
                            datos_extraidos.append({
                                'archivo': file,
                                'comando': comando
                            })
                            # Al encontrar el comando, saltamos al siguiente archivo
                            break
    
    return pd.DataFrame(datos_extraidos)

# --- EJECUCIÓN ---
# Reemplaza 'ruta/a/tus/archivos' por la carpeta que contiene los logs
df_resultados = extraer_comandos_de_logs('.')

# Mostrar el resultado
pd.set_option('display.max_colwidth', None)
display(df_resultados)

# Opcional: Guardar en un archivo CSV para análisis posterior
# df_resultados.to_csv("lista_comandos_dlio.csv", index=False)