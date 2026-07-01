import os
import numpy as np
from pathlib import Path

import pandas as pd

import matplotlib.ticker as ticker
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.colors as colors
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import matplotlib.gridspec as gridspec
from matplotlib.ticker import MultipleLocator
from matplotlib.colors import LinearSegmentedColormap
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset, zoomed_inset_axes

from Modules.DXT_darshan_trace_grapher.utils import convert_to_optimal_unit, prepare_ost_data, prepare_table_data, save_histogram_data

def create_custom_cmap(dir_bench):
    """Create a custom colormap for visualization."""
    #color_list = [(0, 'red'), (0.1, 'yellow'), (0.2, 'greenyellow'), (0.4, 'aqua'),  (0.6, 'blue'), (0.8, 'purple'), (1, 'green')]
    color_list_deepgalaxy = [(0, 'red'), (0.2, 'greenyellow'), (0.4, 'aqua'),  (0.6, 'blue'), (0.8, 'purple'), (1, 'green')]
    # Colores para DeepGalaxy (cmap)
    color_list_deepgalaxyw = [
        (0, 'red'),
        (0.1, 'darkorange'),
        (0.2, 'magenta'),
        (0.3, 'yellow'),
        (0.4, 'greenyellow'),
        (0.5, 'aqua'),
        (0.6, 'deepskyblue'),
        (0.7, 'blue'),
        (0.8, 'darkviolet'),
        (0.9, 'purple'),
        (1, 'green')
    ]
    
    # Colores para HDF5 (cmap1)
    color_list_hdf5 = [
        (0, 'brown'),
        (0.1, 'darkred'),
        (0.2, 'pink'),
        (0.3, 'magenta'),
        (0.4, 'darkorange'),
        (0.5, 'orange'),
        (0.6, 'lightblue'),
        (0.7, 'cyan'),
        (0.8, 'darkcyan'),
        (0.9, 'limegreen'),
        (1, 'olive')
    ]
    
    # Colores para NPZ (cmap3)
    color_list_npz = [
        (0, 'darkorange'),
        (0.1, 'yellowgreen'),
        (0.2, 'greenyellow'),
        (0.3, 'green'),
        (0.4, 'limegreen'),
        (0.5, 'darkgreen'),
        (0.6, 'lightseagreen'),
        (0.7, 'aqua'),
        (0.8, 'skyblue'),
        (0.9, 'navy'),
        (1, 'blue')
    ]
    
    # Colores para TFRecord (nuevo cmap para tfrecord)
    # Lista de colores mejorada para una transición de amarillo a azul
    color_list_tfrecord = [
        (0, 'yellow'),         
        (0.1, 'gold'), 
        (0.2, 'darkgoldenrod'),         
        (0.3, 'orangered'),       
        (0.4, 'darkred'),   
        (0.5, 'red'),          
        (0.6, 'tomato'),       
        (0.7, 'darkblue'),     
        (0.8, 'indigo'),    
        (0.9, 'darkmagenta'),  
        (1, 'purple')  
    ]


    # Colores basados en tonos oscuros para histogramas (cmap2)
    color_list_black_based = [
        (0, 'gray'),
        (0.1, 'dimgray'),
        (0.2, 'darkslategray'),
        (0.3, 'darkolivegreen'),
        (0.4, 'darkblue'),
        (0.5, 'darkred'),
        (0.6, 'darkmagenta'),
        (0.7, 'midnightblue'),
        (0.8, 'saddlebrown'),
        (0.9, 'darkgreen'),
        (1, 'black')
    ]
    
    # Colores basados en una transición de gris a negro para histogramas
    color_list_gray_to_black = [
        (0, 'lightgray'),      # Gris claro
        (0.1, 'gainsboro'),    # Muy cercano al blanco, pero ligeramente más oscuro
        (0.2, 'silver'),       # Gris plata
        (0.3, 'darkgray'),     # Gris oscuro
        (0.4, 'gray'),         # Gris estándar
        (0.5, 'dimgray'),      # Gris tenue
        (0.6, 'slategray'),    # Gris pizarra
        (0.7, 'darkslategray'),# Gris pizarra oscuro
        (0.8, '#36454F'),     # Carbón, un gris casi negro
        (0.9, 'black'),        # Negro
        (1, 'black')           # Negro (para asegurar el fin de la escala)
    ]

    cmap2 = LinearSegmentedColormap.from_list('cool_custom_histogram', color_list_gray_to_black)
    # Crear colormaps a partir de las listas de colores
    if dir_bench == "DeepGalaxy":
        cmap = LinearSegmentedColormap.from_list('cool_custom_deepgalaxy', color_list_deepgalaxy)
        return cmap, cmap2
    elif dir_bench == "HDF5":
        cmap = LinearSegmentedColormap.from_list('cool_custom_hdf5', color_list_hdf5)
        return cmap, cmap2
    elif dir_bench == "NPZ":    
        cmap = LinearSegmentedColormap.from_list('cool_custom_npz', color_list_npz)
        return cmap, cmap2
    elif dir_bench == "TFRecord_256kts":
        cmap = LinearSegmentedColormap.from_list('cool_custom_tfrecord', color_list_tfrecord)
        return cmap, cmap2
    elif dir_bench == "TFRecord_1mts":
        cmap = LinearSegmentedColormap.from_list('cool_custom_tfrecord', color_list_tfrecord)
        return cmap, cmap2


def matplotlib_to_plotly(cmap, pl_entries=255):
    """
    Convert a matplotlib colormap to a plotly colormap.
    
    Parameters:
    - cmap: matplotlib colormap
    - pl_entries: number of discrete points to sample the colormap
    
    Returns:
    - Plotly colormap as a list
    """
    h = 1.0/(pl_entries-1)
    pl_colorscale = []

    for k in range(pl_entries):
        C = cmap(k*h)[:3]  # Get RGB values
        pl_colorscale.append([k*h, f'rgb({int(C[0]*255)}, {int(C[1]*255)}, {int(C[2]*255)})'])

    return pl_colorscale

        
def conver_value(max_size):
    if max_size >= 1e6:
        return f'{max_size / 1e6:.0f}'
    elif max_size >= 1e3:
        return f'{max_size / 1e3:.0f}'
    else:
        return f'{max_size:.0f}'


def calculate_bins(data):
    """Calculate number of bins using the Freedman-Diaconis rule."""
    q25, q75 = np.percentile(data, [25, 75])
    bin_width = 2 * (q75 - q25) * len(data) ** (-1/3)
    bins = int((data.max() - data.min()) / bin_width)
    return bins if bins > 0 else 10  # Fallback to 10 if the calculated bins is less than or equal to 0

# Function to check if the data contains decimals
def has_decimals(data):
    return not np.all(np.equal(np.mod(data, 1), 0))

# Detect the type of variable and convert if needed
def detect_and_convert(column_name, data):
    if 'bytes' in column_name.lower():
        # If the column represents data in bytes, convert it to optimal units
        converted_data, unit = convert_to_optimal_unit(data)
        return converted_data, unit
    elif 'time' in column_name.lower():
        # If the column represents time, assume it's in seconds and return as-is
        return data, 's'
    else:
        # For other cases (like Process_IO or Temporal_Order), return as-is
        return data, ''
   
# Crea grafico en 3D para el patron temporal-Espacial
def plot_scatter_3ds(ang, df, cmap, xlabel, x_title, ylabel, y_title, zlabel, z_title, cbar_label, cbar_title, graph_title, output_path, dir_bench, save_path=None, max_size=None, valor_transfer=None):
    """
    Create and save a 3D scatter plot.
    
    Parameters:
    - df: DataFrame containing the data
    - cmap: Colormap for coloring the scatter plot
    - xlabel, ylabel, zlabel: Column names for the x, y, and z axes
    - x_title, y_title, z_title: Titles for the axes
    - cbar_label: Column name for the color bar
    - cbar_title: Title for the color bar
    - graph_title: Title for the graph
    - output_path: Directory to save the plot
    - save_path: Filename to save the plot
    - max_size: Maximum value for scaling the marker sizes and color bar
    """
    
    fs_type = df['File_System'].unique()[0].upper()
    fig = plt.figure(figsize=(25, 20), dpi=150)
    ax = fig.add_subplot(111, projection='3d', facecolor='white')
    fig.suptitle(f'{graph_title} File System: {fs_type}', color="black", fontsize=30, verticalalignment='top', y=0.82, x=0.6, fontweight='bold')

    #ax.view_init(elev=15, azim=-30)
    ax.view_init(elev=15, azim=ang)
    x = df[xlabel]
    y = df[ylabel]
    z_values, z_unit = convert_to_optimal_unit(df[zlabel])
    c_values, c_unit = convert_to_optimal_unit(df[cbar_label])

    if dir_bench == "DeepGalaxy":
        ncp=10
    elif dir_bench == "DLIOv1":
        ncp=50
         # Si no se proporciona max_size, toma el valor máximo de la columna
        max_size = conver_value(max_size)
        
    if max_size is None:
        max_size = np.max(c_values)
       
    # Escala los puntos según max_size
    if valor_transfer == "256KB":
        s_values = c_values
        c_values = c_values/1024

    else:
        s_values = np.clip(df[cbar_label] / 1024, ncp, 200) * 1.2
    
    # Crear el gráfico de dispersión 3D con los valores máximo para la barra de colores
    scatter = ax.scatter(x, y, z_values, c=c_values, cmap=cmap, s=s_values, alpha=0.7, vmin=0, vmax=max_size)
    ax.tick_params(axis='x', labelrotation=0, direction='inout', pad=5, left=True, length=10, width=10)

    max_y_value = df[ylabel].max()

    def format_func(value, _):
        if max_y_value >= 1e6:
            return f'{value / 1e6:.1f}'
        elif max_y_value >= 1e3:
            return f'{value / 1e3:.1f}'
        else:
            return f'{value:.0f}'

    if max_y_value >= 1e6:
        unit_stick = "(x1M)"
    elif max_y_value >= 1e3:
        unit_stick = "(x1K)"
    else:
        unit_stick = ""

    # Barra de colores con el valor máximo ajustado
    #cbar = plt.colorbar(scatter, ax=ax, fraction=0.025, pad=0.0001, shrink=0.6)
    cbar = plt.colorbar(scatter, ax=ax, fraction=0.025, pad=0.075, shrink=0.6)
    cbar.ax.tick_params(labelsize=30)
    cbar.set_label(f'{cbar_title} ({c_unit})', fontsize=35, fontweight='bold', labelpad=30)
    
    ax.get_yaxis().set_major_formatter(ticker.FuncFormatter(format_func))
    
    ax.set_xlabel(x_title, fontsize=30, labelpad=30, fontweight='bold')
    ax.set_ylabel(f'{y_title} {unit_stick}', fontsize=30, labelpad=30, fontweight='bold')
    ax.set_zlabel(f'{z_title} ({z_unit})', fontsize=30, labelpad=33, fontweight='bold')

    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    # Ajustar el layout eliminando espacios
    #plt.subplots_adjust(left=0, right=0.1, top=0.1, bottom=0)

    #plt.tight_layout(pad=0)

    if save_path:
        plt.savefig(save_path, dpi=600, bbox_inches='tight', pad_inches=0)
    plt.show()

def plot_scatter_3d(ang, df, cmap, xlabel, x_title, ylabel, y_title, zlabel, z_title, cbar_label, cbar_title, graph_title, output_path, dir_bench, save_path=None, max_size=None, valor_transfer=None):
    """
    Create and save a 3D scatter plot.
    
    Parameters:
    - df: DataFrame containing the data
    - cmap: Colormap for coloring the scatter plot
    - xlabel, ylabel, zlabel: Column names for the x, y, and z axes
    - x_title, y_title, z_title: Titles for the axes
    - cbar_label: Column name for the color bar
    - cbar_title: Title for the color bar
    - graph_title: Title for the graph
    - output_path: Directory to save the plot
    - save_path: Filename to save the plot
    - max_size: Maximum value for scaling the marker sizes and color bar
    """
    
    fs_type = df['File_System'].unique()[0].upper()
    fig = plt.figure(figsize=(25, 20), dpi=150)
    ax = fig.add_subplot(111, projection='3d', facecolor='white')
    #fig.suptitle(f'{graph_title} File System: {fs_type}', color="black", fontsize=30, verticalalignment='top', y=0.82, x=0.6, fontweight='bold')
    fig.suptitle(f'{graph_title} File System: {fs_type}', color="black", fontsize=30, verticalalignment='top', y=0.84, x=0.6, fontweight='bold')
    ax.view_init(elev=20, azim=ang)
    x = df[xlabel]
    y = df[ylabel]
    z_values, z_unit = convert_to_optimal_unit(df[zlabel])
    c_values, c_unit = convert_to_optimal_unit(df[cbar_label])

    if dir_bench == "DeepGalaxy":
        ncp=10
    elif dir_bench == "DLIOv1":
        ncp=50
         # Si no se proporciona max_size, toma el valor máximo de la columna
        max_size = conver_value(max_size)
        
    if max_size is None:
        max_size = np.max(c_values)
       
    # Escala los puntos según max_size
    if valor_transfer == "256KB":
        s_values = c_values
        c_values = c_values/1024

    else:
        s_values = np.clip(df[cbar_label] / 1024, ncp, 200) * 1.2
    
    # Crear el gráfico de dispersión 3D con los valores máximo para la barra de colores
    scatter = ax.scatter(x, y, z_values, c=c_values, cmap=cmap, s=s_values, alpha=0.7, vmin=0, vmax=max_size)
    ax.tick_params(axis='x', labelrotation=0, direction='inout', pad=5, left=True, length=10, width=10)

     # Colorbar setup
    cbar = plt.colorbar(scatter, ax=ax, fraction=0.025, pad=0.075, shrink=0.6)
    cbar.ax.tick_params(labelsize=30)
    cbar.set_label(f'{cbar_title} ({c_unit})', fontsize=35, fontweight='bold', labelpad=30)
   

    # Calculate max values beforehand
    max_y_value = df[ylabel].max()
    max_x_value = df[xlabel].max()

    def format_func(value, _):
        if value >= 1e6:
            return f'{value / 1e6:.1f}'
        elif value >= 1e3:
            return f'{value / 1e3:.1f}'
        else:
            return f'{value:.0f}'

    def format_stick(value):
        if value >= 1e6:
            return "(x1M)"
        elif value >= 1e3:
            return "(x1K)"
        else:
            return ""

    # Axis formatting
    if xlabel == "Process_IO":
        ax.get_yaxis().set_major_formatter(ticker.FuncFormatter(format_func))
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
        ax.set_xlabel(x_title, fontsize=30, labelpad=30, fontweight='bold')
        unit_label = format_stick(max_y_value)
        ax.set_ylabel(f'{y_title} {unit_label}', fontsize=30, labelpad=30, fontweight='bold')
    elif xlabel == "Temporal_Order":
        ax.get_xaxis().set_major_formatter(ticker.FuncFormatter(format_func))
        ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
        unit_label = format_stick(max_x_value)
        ax.set_xlabel(f'{x_title} {unit_label}', fontsize=30, labelpad=30, fontweight='bold')
        ax.set_ylabel(y_title, fontsize=30, labelpad=30, fontweight='bold')

    
    ax.set_zlabel(f'{z_title} ({z_unit})', fontsize=30, labelpad=33, fontweight='bold')

    
    # Ajustar el layout eliminando espacios
    #plt.subplots_adjust(left=0, right=0.1, top=0.1, bottom=0)

    #plt.tight_layout(pad=0)

    if save_path:
        plt.savefig(save_path, dpi=600, bbox_inches='tight', pad_inches=0)
    plt.show()




# Crea gráfico en 2D para el patron espacial 
def plot_scatter_2d(df, cmap, xlabel, x_title, zlabel, z_title, cbar_label, cbar_title, 
                    graph_title, output_path, dir_bench, save_path2d=None, max_size=None, valor_transfer=None):
    """
    Create and save a 2D scatter plot.
    
    Parameters:
    - df: DataFrame containing the data
    - cmap: Colormap for coloring the scatter plot
    - xlabel: Column name for the x-axis
    - x_title: Title for the x-axis
    - zlabel: Column name for the y-axis
    - z_title: Title for the y-axis
    - cbar_label: Column name for the color bar
    - cbar_title: Title for the color bar
    - graph_title: Title for the graph
    - output_path: Directory to save the plot
    - save_path2d: Filename to save the plot
    - max_size: Maximum value for scaling the marker sizes
    """
    fs_type = df['File_System'].unique()[0].upper()
    #fig, ax = plt.subplots(figsize=(20, 15))
    fig, ax = plt.subplots(figsize=(25, 20), dpi=150)
    fig.suptitle(f'{graph_title} File System: {fs_type}', color="black", fontsize=30, verticalalignment='top', y=0.95, fontweight='bold')
    
    x = df[xlabel]
    y, y_unit = convert_to_optimal_unit(df[zlabel])
    c_values, c_unit = convert_to_optimal_unit(df[cbar_label])
    #c = df[cbar_label] / 1024
    #s = np.clip(df[cbar_label] / 1024, 10, 200)
    
    # Si no se proporciona max_size, toma el valor máximo de la columna

    if dir_bench == "DeepGalaxy":
        ncp=10
    elif dir_bench == "DLIOv1":
        ncp=50
        max_size = conver_value(max_size)

    if max_size is None:
        max_size = np.max(c_values)
   
    # Escala los puntos según max_size
    if valor_transfer == "256KB":
        s_values = c_values
        c_values = c_values/1024

    else:
        s_values = np.clip(df[cbar_label] / 1024, ncp, 200) * 1.2

    # Crear el gráfico de dispersión 2D con los valores máximo para la barra de colores
    scatter = ax.scatter(x, y, c=c_values, cmap=cmap, s=s_values, alpha=0.7, vmin=0, vmax=max_size)  

    cbar = plt.colorbar(scatter, fraction=0.05, pad=0, shrink=1)
    cbar.set_label(f'{cbar_title} ({c_unit})', fontsize=35, fontweight='bold', labelpad=10)
    
    ax.set_xlabel(x_title, fontsize=30, labelpad=25, fontweight='bold')
    ax.set_ylabel(f'{z_title} ({y_unit})', fontsize=35, labelpad=15, fontweight='bold')
    ax.tick_params(axis='both', which='major', labelsize=35)

    max_process_num = df[xlabel].max()
    step = 1 if max_process_num <= 10 else max_process_num // 10
    
    ax.set_xticks(np.arange(0, max_process_num + 1, step=step))
    cbar.ax.tick_params(labelsize=35)
    
    ax.minorticks_on()
    ax.grid(which="major", linewidth=1, linestyle='-', color='gray')
    ax.grid(which="minor", linewidth=0.2, linestyle='--', color='lightgray')

    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=False))
    ax.tick_params(axis='y', which='both', length=10, width=2, labelsize=35)  

    if save_path2d:
        plt.savefig(save_path2d, dpi=600, bbox_inches='tight', pad_inches=0)
    plt.show()


# Crea gráfico en 2D para el patron espacial con histograma o temporal con histograma
def plot_scttr_hst_2d(df, cmap, cmap2, xlabel, x_title, zlabel, z_title, cbar_label, cbar_title, 
                      graph_title, output_path, dir_bench, save_path2d=None, max_size=None, valor_transfer=None):
    """
    Create and save a 2D scatter plot with histograms.
    
    Parameters:
    - df: DataFrame containing the data
    - cmap: Colormap for coloring the scatter plot
    - xlabel: Column name for the x-axis
    - x_title: Title for the x-axis
    - zlabel: Column name for the y-axis
    - z_title: Title for the y-axis
    - cbar_label: Column name for the color bar
    - cbar_title: Title for the color bar
    - graph_title: Title for the graph
    - output_path: Directory to save the plot
    - save_path2d: Filename to save the plot
    - max_size: Maximum value for scaling the marker sizes
    """
    fs_type = df['File_System'].unique()[0].upper()
    
    fig = plt.figure(figsize=(25, 20), dpi=150)
    gs = fig.add_gridspec(2, 3, width_ratios=(4, 1.5, 0.15), height_ratios=(1.5, 4),
                          left=0.1, right=0.85, bottom=0.1, top=0.9,
                          wspace=0.05, hspace=0.05)  # Adjust wspace for better spacing between colorbars
    
    ax = fig.add_subplot(gs[1, 0])
    ax_histx = fig.add_subplot(gs[0, 0], sharex=ax)
    ax_histy = fig.add_subplot(gs[1, 1], sharey=ax)


    # Convert or use variables for x, y, and color bar based on their names
    x, x_unit = detect_and_convert(xlabel, df[xlabel])
    y, y_unit = detect_and_convert(zlabel, df[zlabel])
    c_values, c_unit = detect_and_convert(cbar_label, df[cbar_label])
    # Set the font sizes
    main_fontsize = 25  # Font size for the main plot
    hist_fontsize = main_fontsize * 0.9  # Font size for the histograms (10% smaller)
    
    # Scale marker sizes based on the color bar variable (Request_Size(bytes) in this case)
    # Si no se proporciona max_size, toma el valor máximo de la columna

    if dir_bench == "DeepGalaxy":
        ncp=10
    elif dir_bench == "DLIOv1":
        ncp=50
        max_size = conver_value(max_size)

    if max_size is None:
        max_size = np.max(c_values)
    
    # Escala los puntos según max_size
    if valor_transfer == "256KB":
        s_values = c_values
        c_values = c_values/1024

    else:
        s_values = np.clip(df[cbar_label] / 1024, ncp, 200) * 1.2

    # Plot scatter plot
    scatter = ax.scatter(x, y, c=c_values, cmap=cmap, s=s_values, alpha=0.7, vmin=0, vmax=max_size)
    #print("A",max(x))
    #print("B",max(y))
    # Adjust colorbar size to match the scatter plot
    cbar = plt.colorbar(scatter, cax=fig.add_subplot(gs[1, 2]), fraction=0.1, pad=0.01)
    cbar.set_label(f'{cbar_title} ({c_unit})', fontsize=main_fontsize, fontweight='bold', labelpad=10)
    if df[xlabel].equals(df['Process_IO']):
        bins_x = np.histogram_bin_edges(x, bins=63)
        bins_y = np.histogram_bin_edges(y, bins=100)
    elif df[xlabel].equals(df['Start_Time(s)']):
        bins_x = np.histogram_bin_edges(x, bins=90, range=(0, 90))  # For time
        bins_y = np.histogram_bin_edges(y, bins=63)
    # Add histograms to the plot
    #bins_x = np.histogram_bin_edges(x, bins='auto')  # Automatically determine the bins for x
    #bins_x = np.histogram_bin_edges(x, bins=63)
    
    # Calculate histograms
    hist_x, bin_edges_x = np.histogram(x, bins=bins_x)
    
    #bins_y = np.histogram_bin_edges(y, bins='auto')  # Automatically determine the bins for y
    hist_y, bin_edges_y = np.histogram(y, bins=bins_y)
    # Calculate bin size for x and y
    bin_size_x = bins_x[1] - bins_x[0]  # Size of each bin in the x axis
    bin_size_y = bins_y[1] - bins_y[0]  # Size of each bin in the y axis
    
    bin_centers_x = 0.5 * (bin_edges_x[:-1] + bin_edges_x[1:])
    bin_centers_y = 0.5 * (bin_edges_y[:-1] + bin_edges_y[1:])
    
   # print("x",x)
    #print("y",y)
    #print("hist_x",hist_x)
    #print("bin_edges_x",bin_edges_x)
   #print("bin_centers_x",bin_centers_x)
    
    #print("bins_y",bins_y)
    #print("bins_y",bins_y)    
    #print("hist_y",hist_y) 
    #print("bin_edges_y",bin_edges_y)
    #print("bin_centers_y",bin_centers_y)
     
    #save_histogram_data(x, y, hist_x, bin_edges_x, bins_y, hist_y, bin_edges_y, save_path2d)

    # Normalize histogram values for color assignment
    hist_freq = np.concatenate([hist_x, hist_y])
    norm = mcolors.Normalize(vmin=np.min(hist_freq), vmax=np.max(hist_freq))
    
    # Assign colors to histograms
    colors_x = cmap2(norm(hist_x))
    colors_y = cmap2(norm(hist_y))

    # Plot the histograms on the marginal axes
    #ax_histx.hist(x, bins=bins_x, color='gray', alpha=0.7)
    #ax_histy.hist(y, bins=bins_y, orientation='horizontal', color='gray', alpha=0.7)

    ax_histx.bar(bin_centers_x, hist_x, width=np.diff(bin_edges_x), color=colors_x, align='center', alpha=0.7)
    ax_histy.barh(bin_centers_y, hist_y, height=np.diff(bin_edges_y), color=colors_y, align='center', alpha=0.7)
    
    # Configure the labels, ticks, and axes representation (integer or decimal)
    if has_decimals(x):
        ax.xaxis.set_major_locator(ticker.AutoLocator())  # Allow decimals
    else:
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))  # Force integer representation

    if has_decimals(y):
        ax.yaxis.set_major_locator(ticker.AutoLocator())  # Allow decimals
        #ax.yaxis.set_major_locator(ticker.MultipleLocator())  # Allow decimals
    else:
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))  # Force integer representation

    # Set labels
    ax.set_xlabel(f'{x_title} {f"({x_unit})" if x_unit else ""}', fontsize=main_fontsize, labelpad=25, fontweight='bold')
    ax.set_ylabel(f'{z_title} {f"({y_unit})" if y_unit else ""}', fontsize=main_fontsize, labelpad=25, fontweight='bold')
 
    ax.tick_params(axis='both', which='major', labelsize=main_fontsize)

    # Set titles for the histograms including bin size
    ax_histx.set_ylabel(f'Count of {x_title}\n(Bin size: {bin_size_x:.2f})', fontsize=hist_fontsize, labelpad=25, fontweight='bold')
    ax_histy.set_xlabel(f'Count of {z_title}\n(Bin size: {bin_size_y:.2f})', fontsize=hist_fontsize, fontweight='bold')

    # Ensure the limits of the histograms match the scatter plot
    ax_histx.set_xlim(ax.get_xlim())
    ax_histy.set_ylim(ax.get_ylim())
    
   
    # Set integer ticks for histograms
    ax_histx.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))  # Force integer ticks on the Y-axis
    ax_histy.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))  # Force integer ticks on the X-axis

    # Apply the transformation to the Y-axis of the top histogram (divide by 1000)
    ax_histx.get_yaxis().set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x / 1000:.1f}k'))
    ax_histy.get_xaxis().set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x / 1000:.1f}k'))

    # Reduce the number of ticks on the histogram axes
    ax_histx.yaxis.set_major_locator(ticker.MaxNLocator(nbins=4))  # Set max 4 ticks on y-axis of the histogram
    ax_histy.xaxis.set_major_locator(ticker.MaxNLocator(nbins=4))  # Set max 4 ticks on x-axis of the side histogram
 
    # Rotate the labels on the X-axis of the side histogram to 45 degrees
    for label in ax_histy.get_xticklabels():
        label.set_rotation(45)
        
    # Rotate the labels on the X-axis of the side histogram to 45 degrees
    for label in ax_histx.get_yticklabels():
        label.set_rotation(0)

    # Hide tick labels on the histogram axes
    ax_histx.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)
    ax_histy.tick_params(axis='y', which='both', left=False, right=False, labelleft=False)
    
    # Activar la rejilla para el gráfico principal y los histogramas
    ax.grid(True)        # Activa la rejilla en el gráfico principal
    ax_histx.grid(True)  # Activa la rejilla en el histograma superior
    ax_histy.grid(True)  # Activa la rejilla en el histograma lateral

    # Add a title to the figure
    fig.suptitle(graph_title, fontsize=main_fontsize +10, fontweight='bold')

    # Save the figure if a save path is provided
    if save_path2d:
        plt.savefig(save_path2d, dpi=600, bbox_inches='tight', pad_inches=0)
    plt.show()

# Crea gráfico en 2D para el patron espacial haciendo zoom en un punto especifico
def plot_zoomed_spatial_pattern(df_zoom, cmap, ylabel, y_title, zlabel, z_title, cbar_label, cbar_title, npi, npt, pn, save_path2dzoom, dir_bench, max_size=None, valor_transfer=None):
    fs_type = df_zoom['File_System'].unique()[0].upper()
    fig, ax = plt.subplots(figsize=(25, 20), dpi=150)
    plt.grid(True, which="both", ls="--", alpha=0.3)
    
    fig.suptitle(f'Spatial Pattern Zoom for Process {npi} of {npt} (Process Number: {pn}) \n File System: {fs_type}', color="black", fontsize=30, verticalalignment='top', y=0.95, fontweight='bold')

    # Titulo de la gráfica
    #ax.set_title(f'Spatial Pattern Zoom for Process {npi} of {npt} (Process Number: {pn}) \n File System: {fs_type}')   
    
    x = df_zoom[ylabel]
    y, y_unit = convert_to_optimal_unit(df_zoom[zlabel])
    c_values, c_unit = convert_to_optimal_unit(df_zoom[cbar_label])
    
    # Si no se proporciona max_size, toma el valor máximo de la columna

    if dir_bench == "DeepGalaxy":
        ncp=10
        axins = zoomed_inset_axes(ax, zoom=2, loc=1, borderpad=3) # configura la posición del recuadro del zoom
        mark_inset(ax, axins, loc1=2, loc2=4, fc="none", ec='0.5')

    elif dir_bench == "DLIOv1":
        ncp=50
        axins = zoomed_inset_axes(ax, zoom=2, loc=2, borderpad=3) # configura la posición del recuadro del zoom
        mark_inset(ax, axins, loc1=1, loc2=3, fc="none", ec='0.5')
        max_size = conver_value(max_size)

    if max_size is None:
        max_size = np.max(c_values)

    
    # Escala los puntos según max_size
    if valor_transfer == "256KB":
        s_values = c_values
        c_values = c_values/1024

    else:
        s_values = np.clip(df_zoom[cbar_label] / 1024, ncp, 200) * 1.2
        
    # Crear el gráfico de dispersión 2D con los valores máximo para la barra de colores
    pd2 = ax.scatter(x, y, c=c_values, marker="d", alpha=0.7, cmap=cmap, s=s_values, vmin=0, vmax=max_size)
    
    ax.set_ylabel(f'{z_title} ({y_unit})', color="black", fontsize=35)
    ax.set_xlabel(y_title, color="black", fontsize=35)
    ax.tick_params(axis='x', colors='black', labelsize=35, rotation=45)
    ax.tick_params(axis='y', colors='black', labelsize=35, rotation=15)
    plt.yticks(rotation=45)
    
    vmax = max_size if max_size else c.max()

    # Calcular cuartiles
    x_q1, x_q3 = np.percentile(x, [25, 75])
    y_q1, y_q3 = np.percentile(y, [25, 75])

    # Calcular el rango intercuartil (IQR)
    x_iqr = x_q3 - x_q1
    y_iqr = y_q3 - y_q1

    # Definir los límites del zoom basados en los cuartiles
    #x_min_zoom = max(x_q1 - 0.3 * x_iqr, x.min())
    #x_max_zoom = min(x_q3 + 0.3 * x_iqr, x.max())
    #y_min_zoom = max(y_q1 - 0.3 * y_iqr, y.min())
    #y_max_zoom = min(y_q3 + 0.3 * y_iqr, y.max())

    # Seleccionar una porción del área de la gráfica principal
    zoom_fraction_x = 0.1  # Fracción del eje x que será mostrada en el zoom
    zoom_fraction_y = 0.1  # Fracción del eje y que será mostrada en el zoom

    x_center = np.median(x)  # Centro en x alrededor del cual se hará el zoom
    y_center = np.median(y)  # Centro en y alrededor del cual se hará el zoom

    x_min_zoom = max(x_center - zoom_fraction_x * (x.max() - x.min()) / 2, x.min())
    x_max_zoom = min(x_center + zoom_fraction_x * (x.max() - x.min()) / 2, x.max())
    y_min_zoom = max(y_center - zoom_fraction_y * (y.max() - y.min()) / 2, y.min())
    y_max_zoom = min(y_center + zoom_fraction_y * (y.max() - y.min()) / 2, y.max())

    
    axins.set_xlim(x_min_zoom, x_max_zoom) # Determina el área del zoom en el eje x
    axins.set_ylim(y_min_zoom, y_max_zoom) # Determina el área del zoom en el eje y
    
    axins.yaxis.get_major_locator().set_params(nbins=3)
    axins.xaxis.get_major_locator().set_params(nbins=3)
    axins.tick_params(labelleft=True, labelbottom=True)

    
    axins.scatter(x, y, c=c_values, marker='d', alpha=0.9, cmap=cmap, s=s_values, vmin=0, vmax=vmax)

    cbar = plt.colorbar(pd2, ax=ax, fraction=0.08, pad=0.02, label=f'{cbar_title} ({c_unit})')
    
    if save_path2dzoom:
        plt.savefig(save_path2dzoom, dpi=600, bbox_inches='tight', pad_inches=0)
    
    plt.show()



def plot_zoomed_spatial_pattern_start_time(df_zoom, cmap, tlabel, t_title, zlabel, z_title, cbar_label, cbar_title, npi, npt, pn, save_path2dzmtime, dir_bench, max_size=None, valor_transfer=None):
    fs_type = df_zoom['File_System'].unique()[0].upper()
    fig, ax = plt.subplots(figsize=(25, 20), dpi=150)
    plt.grid(True, which="both", ls="--", alpha=0.3)   
    fig.suptitle(f'Temporal Pattern Zoom for Process {npi} of {npt} (Process Number: {pn}) \n File System: {fs_type}', color="black", fontsize=30, verticalalignment='top', y=0.95, fontweight='bold')
    
    x = df_zoom[tlabel]
    #print(x)
    y, y_unit = convert_to_optimal_unit(df_zoom[zlabel])
    c_values, c_unit = convert_to_optimal_unit(df_zoom[cbar_label])


    if dir_bench == "DeepGalaxy":
        ncp=10
        axins = zoomed_inset_axes(ax, zoom=2, loc=1, borderpad=3) # configura la posición del recuadro del zoom
        mark_inset(ax, axins, loc1=2, loc2=4, fc="none", ec='0.5')

    elif dir_bench == "DLIOv1":
        ncp=50
        axins = zoomed_inset_axes(ax, zoom=2, loc=2, borderpad=3) # configura la posición del recuadro del zoom
        mark_inset(ax, axins, loc1=1, loc2=3, fc="none", ec='0.5')
        # Si no se proporciona max_size, toma el valor máximo de la columna
        max_size = conver_value(max_size)

    if max_size is None:
        max_size = np.max(c_values)
  
    # Escala los puntos según max_size
    if valor_transfer == "256KB":
        s_values = c_values
        c_values = c_values/1024

    else:
        s_values = np.clip(df_zoom[cbar_label] / 1024, ncp, 200) * 1.2
        
    vmax = max_size if max_size else c.max()    
    pd2 = ax.scatter(x, y, c=c_values, marker="d", alpha=0.7, cmap=cmap, s=s_values, vmin=0, vmax=vmax)
    
    ax.set_ylabel(f'{z_title} ({y_unit})', color="black", fontsize=35)
    ax.set_xlabel(t_title, color="black", fontsize=35)
    ax.tick_params(axis='x', colors='black', labelsize=35, rotation=45)
    ax.tick_params(axis='y', colors='black', labelsize=35, rotation=15)
    plt.yticks(rotation=45)
    


    # Calcular cuartiles
    x_q1, x_q3 = np.percentile(x, [25, 75])
    y_q1, y_q3 = np.percentile(y, [25, 75])

    # Calcular el rango intercuartil (IQR)
    x_iqr = x_q3 - x_q1
    y_iqr = y_q3 - y_q1

    # Adaptar los límites del zoom basados en los cuartiles
    #x_min_zoom = max(x_q1 - 0.5 * x_iqr, x.min())
    #x_max_zoom = min(x_q3 + 0.5 * x_iqr, x.max())
    #y_min_zoom = max(y_q1 - 0.5 * y_iqr, y.min())
    #y_max_zoom = min(y_q3 + 0.5 * y_iqr, y.max())
    
    # Seleccionar una porción del área de la gráfica principal
    zoom_fraction_x = 0.1  # Fracción del eje x que será mostrada en el zoom
    zoom_fraction_y = 0.1  # Fracción del eje y que será mostrada en el zoom

    x_center = np.median(x)  # Centro en x alrededor del cual se hará el zoom
    y_center = np.median(y)  # Centro en y alrededor del cual se hará el zoom

    x_min_zoom = max(x_center - zoom_fraction_x * (x.max() - x.min()) / 2, x.min())
    x_max_zoom = min(x_center + zoom_fraction_x * (x.max() - x.min()) / 2, x.max())
    y_min_zoom = max(y_center - zoom_fraction_y * (y.max() - y.min()) / 2, y.min())
    y_max_zoom = min(y_center + zoom_fraction_y * (y.max() - y.min()) / 2, y.max())


    #axins = zoomed_inset_axes(ax, zoom=7, loc=1, borderpad=3)
    axins.set_xlim(x_min_zoom, x_max_zoom)
    axins.set_ylim(y_min_zoom, y_max_zoom)
    
    axins.yaxis.get_major_locator().set_params(nbins=3)
    axins.xaxis.get_major_locator().set_params(nbins=3)
    axins.tick_params(labelleft=True, labelbottom=True)

    axins.scatter(x, y, c=c_values, marker='d', alpha=0.7, cmap=cmap, s=s_values, vmin=0, vmax=vmax)

    cbar = plt.colorbar(pd2, ax=ax, fraction=0.08, pad=0.02, label=f'{cbar_title} ({c_unit})')
    
    if save_path2dzmtime:
        plt.savefig(save_path2dzmtime, dpi=600, bbox_inches='tight', pad_inches=0)
    
    plt.show()
    
 

def create_and_save_table(table_data, file_name, output_path, table_title, fname_generated):
    """
    Create and save a table as an image file.
    
    Parameters:
    - table_data: Data for the table
    - file_name: Base filename for saving the table
    - output_path: Directory to save the table
    - table_title: Title for the table
    - fname_generated: Generated filename for the table
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle(table_title, color="black", fontsize=25, verticalalignment='bottom', y=0.75, fontweight='bold')

    ax.axis('tight')
    ax.axis('off')
    
    max_columns = max(len(row) for row in table_data)
    colWidths = [0.8] * max_columns

    table = ax.table(cellText=table_data, colWidths=colWidths, cellLoc='center', loc='center', bbox=[-0.3, 0, 1.5, 0.8])
    table.auto_set_font_size(False)
    table.set_fontsize(20)
    table.scale(3, 6)
    
    save_table = fname_generated
    plt.savefig(os.path.join(output_path, f'1_Characterization table_{save_table}'), dpi=300, bbox_inches='tight', pad_inches=0)
    plt.show()
    return save_table

def tabla_data_patron(df, file_name, output_path, macc, app_name):
    """
    Prepare data for the table based on the file system type.
    
    Parameters:
    - df: DataFrame containing the data
    - file_name: Base filename for the table
    - output_path: Directory to save the table
    
    Returns:
    - table_data: Data prepared for the table
    - table_title: Title for the table
    """
    fs_type = df['File_System'].unique()[0].upper()
    num_unique_osts = prepare_ost_data(df) if fs_type == 'LUSTRE' else None
    table_data, table_title = prepare_table_data(df, num_unique_osts, macc, app_name)
    
    return table_data, table_title

