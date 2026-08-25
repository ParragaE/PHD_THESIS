import re

def process_lustre_line(line, current_file, nodos_dict, fs_type, regex_pattern_lustre):
    """
    Procesa una línea de datos de Lustre y la devuelve como un diccionario estructurado.

    Args:
        line (str): La línea de datos de Lustre que se va a procesar.
        current_file (str): El nombre del archivo actual.
        nodos_dict (dict): Un diccionario que mapea nodos a valores específicos.
        fs_type (str): El tipo de sistema de archivos.
        regex_pattern_lustre (re.Pattern): El patrón de expresión regular para coincidir con los datos de Lustre.

    Returns:
        dict or None: Un diccionario que representa la línea procesada si se encuentra una coincidencia con el patrón,
                      de lo contrario, devuelve None.
    """
    match = regex_pattern_lustre.search(line)
    if match:
        #ost_values_str = match.group(8)
        #ost_values = [int(ost) for ost in re.findall(r'\d+', ost_values_str)]
        return {
            'File_name': current_file,
            'Nodes': nodos_dict.get(match.group(1), 'Desconocido'),
            'Process_IO': int(match.group(1)),
            'File_System': fs_type,
            'Operation_Type': match.group(2),
            'Temporal_Order': int(match.group(3)),
            'Offset(bytes)': int(match.group(4)),
            'Request_Size(bytes)': int(match.group(5)),
            'Start_Time(s)': float(match.group(6)),
            'End_Time(s)': float(match.group(7)),
            #'OST': ost_values
            'OST': match.group(8) # Añade valor de 'OST'
        }
