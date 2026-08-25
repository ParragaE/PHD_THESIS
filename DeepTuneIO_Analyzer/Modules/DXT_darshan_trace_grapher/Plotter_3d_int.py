import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

def plot_scatter_3d_int(df, cmap, xlabel, x_title, ylabel, y_title, zlabel, z_title, cbar_label, cbar_title, graph_title, save_path=None, max_size=None, valor_transfer=None):
    """
    Create and save an interactive 3D scatter plot using Plotly.
    
    Parameters:
    - df: DataFrame containing the data
    - cmap: Colormap for coloring the scatter plot
    - xlabel, ylabel, zlabel: Column names for the x, y, and z axes
    - x_title, y_title, z_title: Titles for the axes
    - cbar_label: Column name for the color bar
    - cbar_title: Title for the color bar
    - graph_title: Title for the graph
    - save_path: Filename to save the plot
    - max_size: Maximum value for scaling the marker sizes
    - valor_transfer: Transfer value for scaling
    """
    
    fs_type = df['File_System'].unique()[0].upper()
    x = df[xlabel]
    y = df[ylabel]
    z_values, z_unit = convert_to_optimal_unit(df[zlabel])
    c_values, c_unit = convert_to_optimal_unit(df[cbar_label])
    
    if max_size is None:
        max_size = np.max(c_values)

    # Escala los tamaños de los puntos
    if valor_transfer == "256KB":
        s_values = c_values
        c_values = c_values / 1024
    else:
        s_values = np.clip(df[cbar_label] / 1024, 10, 200) * 1.2
    
    # Crear gráfico 3D
    fig = go.Figure(data=[go.Scatter3d(
        x=x,
        y=y,
        z=z_values,
        mode='markers',
        marker=dict(
            size=s_values,
            color=c_values,
            colorscale=cmap,
            colorbar=dict(title=cbar_title + f' ({c_unit})', tickfont=dict(size=14)),
            opacity=0.7,
            showscale=True
        )
    )])

    # Configurar títulos y ejes
    fig.update_layout(
        title=f'{graph_title} - File System: {fs_type}',
        scene=dict(
            xaxis_title=x_title,
            yaxis_title=y_title + f" ({'(x1K)' if max(y) >= 1e3 else ''})",
            zaxis_title=f'{z_title} ({z_unit})',
        ),
        width=1200,
        height=800,
        margin=dict(l=0, r=0, b=0, t=30),
    )

    # Guardar o mostrar el gráfico
    if save_path:
        fig.write_html(save_path)
    fig.show()
