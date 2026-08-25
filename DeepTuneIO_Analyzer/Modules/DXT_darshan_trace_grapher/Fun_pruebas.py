

def plot_scatter_3dfunciona(df, cmap, xlabel, x_title, ylabel, y_title, zlabel, z_title, 
                    cbar_label, cbar_title, graph_title, output_path, 
                    save_path=None, max_size=None):
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
    - max_size: Maximum value for scaling the marker sizes
    """
    fs_type = df['File_System'].unique()[0].upper()
    fig = plt.figure(figsize=(25, 20), dpi=250)
    ax = fig.add_subplot(111, projection='3d', facecolor='white')
    fig.suptitle(f'{graph_title} File System: {fs_type}', color="black", fontsize=30, verticalalignment='top', y=0.82, x=0.5, fontweight='bold')

    #ax.view_init(elev=10, azim=-25) # configuracion inicial
    ax.view_init(elev=15, azim=-30)
   # fig.subplots_adjust(left=0.1, right=0.2, top=0.2, bottom=0.1)

    z_values, z_unit = convert_to_optimal_unit(df[zlabel])
    c_values, c_unit = convert_to_optimal_unit(df[cbar_label])
    #print(c_values)
    # Convert cbar_label from bytes to KiB
    #c_values = df[cbar_label] / 1024
    # Control the size of the points by adjusting the range or applying a scale factor
    s_values = np.clip(df[cbar_label] / 1024, 50, 200)* 1.2 # Increase the size by multiplying by 1.5
    
    # Create the scatter plot
    #scatter = ax.scatter(df[xlabel], df[ylabel], z_values, c=c_values, cmap=cmap, s=s_values, vmin=0, vmax=max_size / 1024)
    scatter = ax.scatter(df[xlabel], df[ylabel], z_values, c=c_values, cmap=cmap, s=s_values, alpha=0.7, vmin=0, vmax=np.max(c_values))

    # Obtener el valor máximo de la variable 'ylabel'
    max_y_value = df[ylabel].max()
    # Configurar el formateador dinámico dependiendo del valor máximo
    def format_func(value, _):
        if max_y_value >= 1e6:
            return f'{value / 1e6:.2f}M'  # Mostrar en millones si es mayor que 1 millón
        elif max_y_value >= 1e3:
            return f'{value / 1e3:.0f}K'  # Mostrar en miles si es mayor que 1 mil
        else:
            return f'{value:.0f}'  # Mostrar el valor completo si es menor que mil

    # Determinar la unidad para la etiqueta del eje Y
    if max_y_value >= 1e6:
        unit_stick = "(x1M)"
    elif max_y_value >= 1e3:
        unit_stick = "(x1K)"
    else:
        unit_stick = ""

    cbar = plt.colorbar(scatter, ax=ax, fraction=0.025, pad=0.06, shrink=0.6)
    cbar.ax.tick_params(labelsize=30)
    cbar.set_label(f'{cbar_title} ({c_unit})', fontsize=35, fontweight='bold', labelpad=30)
    #ax.get_yaxis().set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x / 1000:.0f}k'))
    
    
    # Aplicar el formateador dinámico al eje Y
    ax.get_yaxis().set_major_formatter(ticker.FuncFormatter(format_func))
        
    ax.set_xlabel(x_title, fontsize=30, labelpad=30, fontweight='bold')
    ax.set_ylabel(f'{y_title} {unit_stick}', fontsize=30, labelpad=30, fontweight='bold')
    ax.set_zlabel(f'{z_title} ({z_unit})', fontsize=30, labelpad=33, fontweight='bold')
    
    # Asigna las ubicaciones (ticks) en el eje X de manera fija
    #locs = ax.get_xticks()
    #ax.set_xticks(locs)  # Configura los ticks en el eje X
    #ax.set_xticklabels([f'{int(loc):,}' for loc in locs], rotation=15, ha='right')
    
    #ax.tick_params(axis='both', which='major', labelsize=30, direction='inout', pad=10)
    #ax.tick_params(axis='y', labelrotation=25, labelsize=30, direction='inout')
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))

    plt.tight_layout(pad=1) # Reduce el pad para que ajuste mejor

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight', pad_inches=0)
    plt.show()
 


def plot_scttr_hst_2d1(df, cmap, xlabel, x_title, zlabel, z_title, cbar_label, cbar_title, 
                    graph_title, output_path, save_path2d=None, max_size=None):
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
    #fs_type = df['File_System'].unique()[0]
    #fig, ax = plt.subplots(figsize=(20, 15))
    #fig.suptitle(f'{graph_title} File System: {fs_type}', color="black", fontsize=35, verticalalignment='top', y=0.95, fontweight='bold')
    
    fig = plt.figure(figsize=(20, 16))
    # Add a gridspec with two rows and two columns and a ratio of 1 to 4 between
    # the size of the marginal Axes and the main Axes in both directions.
    # Also adjust the subplot parameters for a square plot.
    gs = fig.add_gridspec(2, 2,  width_ratios=(4, 1), height_ratios=(1, 4),
                          left=0.1, right=0.9, bottom=0.1, top=0.5,
                          wspace=0, hspace=0)
    # Create the Axes.
    ax = fig.add_subplot(gs[1, 0])
    ax_histx = fig.add_subplot(gs[0, 0], sharex=ax)
    ax_histy = fig.add_subplot(gs[1, 1], sharey=ax)
    
    x = df[xlabel]
    y, y_unit = convert_to_optimal_unit(df[zlabel])
    c, c_unit = convert_to_optimal_unit(df[cbar_label])
    c = df[cbar_label] / 1024
    s = np.clip(df[cbar_label] / 1024, 10, 200)

    scatter = ax.scatter(x, y, c=c, cmap=cmap, s=s, vmin=0, vmax=max_size / 1024)    
    cbar = plt.colorbar(scatter, fraction=0.05, pad=0.01)
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

    # construccion del histograma
    # now determine nice limits by hand:
    binwidth = 0.25
    xymax = max(np.max(np.abs(x)), np.max(np.abs(y)))
    lim = (int(xymax/binwidth) + 1) * binwidth
    Colors = {'Red','Black','Blue'}
    #bins = np.arange(lim, lim + binwidth, binwidth)
    bins =  10
    histtype = "bar"
    ax_histx.hist(x, bins=bins, histtype= histtype, color='Red', stacked=True)
    ax_histy.hist(y, bins=bins, orientation='horizontal', histtype= histtype, color='yellow', stacked=True)

    # Para los histogramas la seleccion del color puede depender del tamaño de la operacion, es decir, buscar la manera de que para cada proceso calcule los valores unicos de las operaciones y estos sean 
    # relacionados con la barra de colores. Construir las barras del histograma a partir del tamaño de la operaciones
    if save_path2d:
        plt.savefig(save_path2d, dpi=300, bbox_inches='tight', pad_inches=0)
    plt.show()


def plot_scttr_hst_2d2(df, cmap, xlabel, x_title, zlabel, z_title, cbar_label, cbar_title, 
                      graph_title, output_path, save_path2d=None, max_size=None):
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
    
    fig = plt.figure(figsize=(20, 16))
    gs = fig.add_gridspec(2, 2, width_ratios=(4, 1), height_ratios=(1, 4),
                          left=0.1, right=0.9, bottom=0.1, top=0.9,
                          wspace=0, hspace=0)  # Set wspace and hspace to 0 to remove spaces
    
    ax = fig.add_subplot(gs[1, 0])
    ax_histx = fig.add_subplot(gs[0, 0], sharex=ax)
    ax_histy = fig.add_subplot(gs[1, 1], sharey=ax)

    x = df[xlabel]
    y, y_unit = convert_to_optimal_unit(df[zlabel])
    c, c_unit = convert_to_optimal_unit(df[cbar_label])
    c = df[cbar_label] / 1024
    s = np.clip(df[cbar_label] / 1024, 10, 200)

    scatter = ax.scatter(x, y, c=c, cmap=cmap, s=s, vmin=0, vmax=max_size / 1024)
    cbar = plt.colorbar(scatter, ax=ax_histy, fraction=0.1, pad=0.01, aspect=40)
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

    # Automatically calculate bins using the Freedman-Diaconis rule
    def calculate_bins(data):
        q25, q75 = np.percentile(data, [25, 75])
        bin_width = 2 * (q75 - q25) * len(data) ** (-1/3)
        bins = int((data.max() - data.min()) / bin_width)
        return bins if bins > 0 else 10  # Fallback to 10 if the calculated bins is less than or equal to 0

    bins_x = calculate_bins(x)
    bins_y = calculate_bins(y)
    
    # Calculate histogram and assign colors to each bin
    hist_x, bin_edges_x = np.histogram(x, bins=bins_x)
    bin_centers_x = 0.5 * (bin_edges_x[:-1] + bin_edges_x[1:])
    
    colors_x = []
    for i in range(len(bin_centers_x)):
        mask = (x >= bin_edges_x[i]) & (x < bin_edges_x[i + 1])
        if np.any(mask):
            avg_color = np.mean(c[mask])
            colors_x.append(cmap(avg_color / (max_size / 1024)))
        else:
            colors_x.append(cmap(0))

    ax_histx.bar(bin_centers_x, hist_x, width=np.diff(bin_edges_x), color=colors_x, align='center', alpha=0.7)
    
    # Repeat the same for the y histogram
    hist_y, bin_edges_y = np.histogram(y, bins=bins_y)
    bin_centers_y = 0.5 * (bin_edges_y[:-1] + bin_edges_y[1:])
    
    colors_y = []
    for i in range(len(bin_centers_y)):
        mask = (y >= bin_edges_y[i]) & (y < bin_edges_y[i + 1])
        if np.any(mask):
            avg_color = np.mean(c[mask])
            colors_y.append(cmap(avg_color / (max_size / 1024)))
        else:
            colors_y.append(cmap(0))

    ax_histy.barh(bin_centers_y, hist_y, height=np.diff(bin_edges_y), color=colors_y, align='center', alpha=0.7)
    
    # Adjusting histogram limits and adding ticks
    ax_histx.set_xlim(ax.get_xlim())
    ax_histy.set_ylim(ax.get_ylim())
    
    ax_histx.tick_params(axis='y', which='both', left=True, right=False, labelleft=True)
    ax_histy.tick_params(axis='x', which='both', bottom=True, top=False, labelbottom=True)
    ax_histx.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)
    ax_histy.tick_params(axis='y', which='both', left=False, right=False, labelleft=False)

    # Titles and final adjustments
    fig.suptitle(graph_title, fontsize=35, fontweight='bold')
    ax_histx.set_title(f'Frequency \nof {x_title}', fontsize=20, fontweight='bold')
    ax_histy.set_title(f'Frequency \nof {z_title}', fontsize=20, fontweight='bold', rotation=0)

    if save_path2d:
        plt.savefig(save_path2d, dpi=300, bbox_inches='tight', pad_inches=0)
    plt.show()



def plot_scttr_hst_2d3(df, cmap, xlabel, x_title, zlabel, z_title, cbar_label, cbar_title, 
                      graph_title, output_path, save_path2d=None, max_size=None):
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
    
    fig = plt.figure(figsize=(22, 16))
    gs = fig.add_gridspec(2, 3, width_ratios=(4, 1, 0.1), height_ratios=(1, 4),
                          left=0.1, right=0.9, bottom=0.1, top=0.9,
                          wspace=0, hspace=0)  # Set wspace and hspace to 0 to remove spaces
    
    ax = fig.add_subplot(gs[1, 0])
    ax_histx = fig.add_subplot(gs[0, 0], sharex=ax)
    ax_histy = fig.add_subplot(gs[1, 1], sharey=ax)

    x = df[xlabel]
    y, y_unit = convert_to_optimal_unit(df[zlabel])
    c, c_unit = convert_to_optimal_unit(df[cbar_label])
    c = df[cbar_label] / 1024  # Convert to MiB
    s = np.clip(df[cbar_label] / 1024, 10, 200)  # Marker sizes

    scatter = ax.scatter(x, y, c=c, cmap=cmap, s=s, vmin=0, vmax=max_size / 1024)
    
    # Adjust colorbar size to match the main plot
    cbar = plt.colorbar(scatter, cax=fig.add_subplot(gs[1, 2]), fraction=0.1, pad=0.01)
    cbar.set_label(f'{cbar_title} ({c_unit})', fontsize=25, fontweight='bold', labelpad=10)
    
    # Second colorbar for the histogram using ScalarMappable
    norm = mcolors.Normalize(vmin=0, vmax=max_size / 1024)
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar_hist = plt.colorbar(sm, cax=fig.add_subplot(gs[0, 2]))
    cbar_hist.set_label(f'Histogram Scale ({c_unit})', fontsize=25, fontweight='bold', labelpad=10)

    ax.set_xlabel(x_title, fontsize=30, labelpad=25, fontweight='bold')
    ax.set_ylabel(f'{z_title} ({y_unit})', fontsize=30, labelpad=25, fontweight='bold')
    ax.tick_params(axis='both', which='major', labelsize=20)

    max_process_num = df[xlabel].max()
    step = 1 if max_process_num <= 10 else max_process_num // 10

    ax.set_xticks(np.arange(0, max_process_num + 1, step=step))
    cbar.ax.tick_params(labelsize=20)
    cbar_hist.ax.tick_params(labelsize=20)

    ax.minorticks_on()
    ax.grid(which="major", linewidth=1, linestyle='-', color='gray')
    ax.grid(which="minor", linewidth=0.2, linestyle='--', color='lightgray')

    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=False))
    ax.tick_params(axis='y', which='both', length=10, width=2, labelsize=20)  

    # Automatically calculate bins using the Freedman-Diaconis rule
    def calculate_bins(data):
        """Calculate number of bins using the Freedman-Diaconis rule."""
        q25, q75 = np.percentile(data, [25, 75])
        bin_width = 2 * (q75 - q25) * len(data) ** (-1/3)
        bins = int((data.max() - data.min()) / bin_width)
        return bins if bins > 0 else 10  # Fallback to 10 if the calculated bins is less than or equal to 0

    bins_x = calculate_bins(x)
    bins_y = calculate_bins(y)
    
    # Calculate histogram and assign colors to each bin
    hist_x, bin_edges_x = np.histogram(x, bins=bins_x)
    bin_centers_x = 0.5 * (bin_edges_x[:-1] + bin_edges_x[1:])
    
    colors_x = []
    for i in range(len(bin_centers_x)):
        mask = (x >= bin_edges_x[i]) & (x < bin_edges_x[i + 1])
        if np.any(mask):
            avg_color = np.mean(c[mask])
            colors_x.append(cmap(avg_color / (max_size / 1024)))
        else:
            colors_x.append(cmap(0))

    ax_histx.bar(bin_centers_x, hist_x, width=np.diff(bin_edges_x), color=colors_x, align='center', alpha=0.7)
    
    # Repeat the same for the y histogram
    hist_y, bin_edges_y = np.histogram(y, bins=bins_y)
    bin_centers_y = 0.5 * (bin_edges_y[:-1] + bin_edges_y[1:])
    
    colors_y = []
    for i in range(len(bin_centers_y)):
        mask = (y >= bin_edges_y[i]) & (y < bin_edges_y[i + 1])
        if np.any(mask):
            avg_color = np.mean(c[mask])
            colors_y.append(cmap(avg_color / (max_size / 1024)))
        else:
            colors_y.append(cmap(0))

    ax_histy.barh(bin_centers_y, hist_y, height=np.diff(bin_edges_y), color=colors_y, align='center', alpha=0.7)
    
    # Adjusting histogram limits and adding ticks
    ax_histx.set_xlim(ax.get_xlim())
    ax_histy.set_ylim(ax.get_ylim())
    
    ax_histx.tick_params(axis='y', which='both', left=True, right=False, labelleft=True)
    ax_histy.tick_params(axis='x', which='both', bottom=True, top=False, labelbottom=True)
    ax_histx.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)
    ax_histy.tick_params(axis='y', which='both', left=False, right=False, labelleft=False)

    # Titles and final adjustments
    fig.suptitle(graph_title, fontsize=35, fontweight='bold')
    ax_histx.set_title(f'Frequency \nof {x_title}', fontsize=20, fontweight='bold', pad=20)
    ax_histy.set_title(f'Frequency \nof {z_title}', fontsize=20, fontweight='bold', rotation=-90, pad=40)

    if save_path2d:
        plt.savefig(save_path2d, dpi=300, bbox_inches='tight', pad_inches=0)
    plt.show()




def plot_scttr_hst_2d5(df, cmap, cmap2, xlabel, x_title, zlabel, z_title, cbar_label, cbar_title, 
                      graph_title, output_path, save_path2d=None, max_size=None):
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
    
    fig = plt.figure(figsize=(22, 16))
    gs = fig.add_gridspec(2, 3, width_ratios=(4, 1, 0.15), height_ratios=(1, 4),
                          left=0.1, right=0.85, bottom=0.1, top=0.9,
                          wspace=0, hspace=0)  # Increased wspace for better spacing between colorbars
    
    ax = fig.add_subplot(gs[1, 0])
    ax_histx = fig.add_subplot(gs[0, 0], sharex=ax)
    ax_histy = fig.add_subplot(gs[1, 1], sharey=ax)
    
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

    # Convert or use variables for x, y, and color bar based on their names
    x, x_unit = detect_and_convert(xlabel, df[xlabel])
    y, y_unit = detect_and_convert(zlabel, df[zlabel])
    c, c_unit = detect_and_convert(cbar_label, df[cbar_label])
    
    #c = df[cbar_label] / 1024  # Convert to MiB
    # Scale marker sizes based on the color bar variable (Request_Size(bytes) in this case)
    s = np.clip(df[cbar_label] / 1024, 10, 200)  # Marker sizes based on cbar_label

    # Plot scatter plot
    scatter = ax.scatter(x, y, c=c, cmap=cmap, s=s, vmin=0, vmax=max_size / 1024)

   # Adjust colorbar size to match the main plot
    cbar = plt.colorbar(scatter, cax=fig.add_subplot(gs[1, 2]), fraction=0.1, pad=0.01)
    cbar.set_label(f'{cbar_title} ({c_unit})', fontsize=25, fontweight='bold', labelpad=10)

   # Verificar si los valores de los ejes tienen decimales
    def has_decimals(arr):
        return not np.all(np.equal(np.mod(arr, 1), 0))
    
    x_limits = ax.get_xlim()
    y_limits = ax.get_ylim()

    # Configurar el eje X para enteros si no hay decimales
    if not has_decimals(np.linspace(x_limits[0], x_limits[1], num=10)):
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    else:
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=False))

    # Configurar el eje Y para enteros si no hay decimales
    if not has_decimals(np.linspace(y_limits[0], y_limits[1], num=10)):
        ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    else:
        ax.yaxis.set_major_locator(plt.MaxNLocator(integer=False))
        
    # Calculate histogram and assign colors to each bin
    bins_x = calculate_bins(x)
    hist_x, bin_edges_x = np.histogram(x, bins=bins_x)
    
    bins_y = calculate_bins(y)
    hist_y, bin_edges_y = np.histogram(y, bins=bins_y)
    
    # Calculate bin size
    bin_size_x = (x.max() - x.min()) / bins_x
    bin_size_y = (y.max() - y.min()) / bins_y

    bin_centers_x = 0.5 * (bin_edges_x[:-1] + bin_edges_x[1:])
    bin_centers_y = 0.5 * (bin_edges_y[:-1] + bin_edges_y[1:])
    
    hist_freq = np.concatenate([hist_x, hist_y])

    # Create a colorbar based on the frequency of bins
    norm = mcolors.Normalize(vmin=np.min(hist_freq), vmax=np.max(hist_freq))
    sm = cm.ScalarMappable(cmap=cmap2, norm=norm)
    
    sm.set_array([])
    
    #cbar_hist = plt.colorbar(sm, cax=fig.add_subplot(gs[0, 2]))
    #cbar_hist.set_label(f'Histogram Scale ({c_unit})', fontsize=25, fontweight='bold', labelpad=10)

    # Adjust the colorbar to represent the bin frequencies
    #cbar_hist = plt.colorbar(sm, cax=fig.add_subplot(gs[0, 2]), fraction=0.1, pad=0.01)
    #cbar_hist.set_label(f'Frequency \nof operations', fontsize=25, fontweight='bold', labelpad=10)
    #cbar_hist.ax.tick_params(labelsize=20)

    # Assign colors to histograms based on frequency
    colors_x = cmap2(norm(hist_x))
    colors_y = cmap2(norm(hist_y))

    ax_histx.bar(bin_centers_x, hist_x, width=np.diff(bin_edges_x), color=colors_x, align='center', alpha=0.7)
    ax_histy.barh(bin_centers_y, hist_y, height=np.diff(bin_edges_y), color=colors_y, align='center', alpha=0.7)
    
    # Plot adjustments
    ax.set_xlabel(x_title, fontsize=30, labelpad=25, fontweight='bold')
    ax.set_ylabel(f'{z_title} ({y_unit})', fontsize=30, labelpad=25, fontweight='bold')
    ax.tick_params(axis='both', which='major', labelsize=20)

    max_process_num = df[xlabel].max()
    step = 1 if max_process_num <= 10 else max_process_num // 10

    ax.set_xticks(np.arange(0, max_process_num + 1, step=step))
    
    #cbar.ax.tick_params(labelsize=20)
    #cbar_hist.ax.tick_params(labelsize=20)

    ax.minorticks_on()
    ax.grid(which="major", linewidth=1, linestyle='-', color='gray')
    ax.grid(which="minor", linewidth=0.2, linestyle='--', color='lightgray')

    #ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    #ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.tick_params(axis='y', which='both', length=10, width=2, labelsize=20)  
    
    # Adjusting histogram limits and adding ticks
    ax_histx.set_xlim(ax.get_xlim())
    ax_histy.set_ylim(ax.get_ylim())
    
    ax_histx.tick_params(axis='y', which='both', left=True, right=False, labelleft=True)
    ax_histy.tick_params(axis='x', which='both', bottom=True, top=False, labelbottom=True)
    ax_histx.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)
    ax_histy.tick_params(axis='y', which='both', left=False, right=False, labelleft=False)

    # Titles and final adjustments
    fig.suptitle(graph_title, fontsize=35, fontweight='bold')
    # Adjust axis labels to include bin size
    ax_histx.set_ylabel(f'I/O Operations \nper {x_title}\n(Bin size: {bin_size_x:.2f})', 
                        fontsize=20, labelpad=25, fontweight='bold')
    
    ax_histy.set_xlabel(f'I/O Access \nAcross {z_title} \n(Bin size: {bin_size_y:.2f})', 
                        fontsize=20, fontweight='bold')

    if save_path2d:
        plt.savefig(save_path2d, dpi=300, bbox_inches='tight', pad_inches=0)
    plt.show()




def plot_scttr_hst_2d3(df, cmap, cmap2, x_column, x_title, y_column, y_title, color_column, color_title, 
                      graph_title, output_path, save_path2d=None, max_size=None, **kwargs):
    """
    Create and save a 2D scatter plot with histograms.
    
    Parameters:
    - df: DataFrame containing the data
    - cmap: Colormap for coloring the scatter plot
    - x_column: Column name for the x-axis
    - x_title: Title for the x-axis
    - y_column: Column name for the y-axis
    - y_title: Title for the y-axis
    - color_column: Column name for the color bar
    - color_title: Title for the color bar
    - graph_title: Title for the graph
    - output_path: Directory to save the plot
    - save_path2d: Filename to save the plot
    - max_size: Maximum value for scaling the marker sizes
    - kwargs: Additional optional arguments for customization
    """
    
    fig = plt.figure(figsize=(22, 16))
    gs = fig.add_gridspec(2, 3, width_ratios=(4, 1, 0.15), height_ratios=(1, 4),
                          left=0.1, right=0.85, bottom=0.1, top=0.9, wspace=0, hspace=0)

    ax = fig.add_subplot(gs[1, 0])
    ax_histx = fig.add_subplot(gs[0, 0], sharex=ax)
    ax_histy = fig.add_subplot(gs[1, 1], sharey=ax)

    # Convert units
    x = df[x_column]
    y, y_unit = convert_to_optimal_unit(df[y_column])
    c, c_unit = convert_to_optimal_unit(df[color_column])
    
    # Marker sizes
    s = np.clip(df[color_column] / 1024, 10, 200)  # Marker sizes in MiB
    
    # Create scatter plot
    scatter = ax.scatter(x, y, c=c, cmap=cmap, s=s, vmin=0, vmax=max_size / 1024)
    
    # Create colorbar
    cbar = plt.colorbar(scatter, cax=fig.add_subplot(gs[1, 2]), fraction=0.1, pad=0.01)
    cbar.set_label(f'{color_title} ({c_unit})', fontsize=25, fontweight='bold', labelpad=10)

    # Calculate and plot histograms
    bins_x = calculate_bins(x)
    hist_x, bin_edges_x = np.histogram(x, bins=bins_x)
    
    bins_y = calculate_bins(y)
    hist_y, bin_edges_y = np.histogram(y, bins=bins_y)

    bin_centers_x = 0.5 * (bin_edges_x[:-1] + bin_edges_x[1:])
    bin_centers_y = 0.5 * (bin_edges_y[:-1] + bin_edges_y[1:])
    
    # Normalize histogram values for color assignment
    hist_freq = np.concatenate([hist_x, hist_y])
    norm = mcolors.Normalize(vmin=np.min(hist_freq), vmax=np.max(hist_freq))
    
    # Assign colors to histograms
    colors_x = cmap2(norm(hist_x))
    colors_y = cmap2(norm(hist_y))

    ax_histx.bar(bin_centers_x, hist_x, width=np.diff(bin_edges_x), color=colors_x, align='center', alpha=0.7)
    ax_histy.barh(bin_centers_y, hist_y, height=np.diff(bin_edges_y), color=colors_y, align='center', alpha=0.7)

    # Set axis labels and title
    ax.set_xlabel(x_title, fontsize=30, labelpad=25, fontweight='bold')
    ax.set_ylabel(f'{y_title} ({y_unit})', fontsize=30, labelpad=25, fontweight='bold')

    # Customize ticks and grid
    ax.tick_params(axis='both', which='major', labelsize=20)
    ax.minorticks_on()
    ax.grid(which="major", linewidth=1, linestyle='-', color='gray')
    ax.grid(which="minor", linewidth=0.2, linestyle='--', color='lightgray')

    # Final adjustments
    fig.suptitle(graph_title, fontsize=35, fontweight='bold')
    
    # Save plot if save_path2d is provided
    if save_path2d:
        plt.savefig(save_path2d, dpi=300, bbox_inches='tight', pad_inches=0)
    plt.show()


def plot_scttr_hst_2d4(df, cmap, xlabel, x_title, zlabel, z_title, cbar_label, cbar_title, 
                      graph_title, output_path, save_path2d=None, max_size=None):
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
    
    fig = plt.figure(figsize=(22, 16))
    gs = fig.add_gridspec(2, 2, width_ratios=(4, 1), height_ratios=(1, 4),
                          left=0.1, right=0.85, bottom=0.1, top=0.9,
                          wspace=0, hspace=0)  # Set wspace to 0 to remove space between central plot and histograms
    
    ax = fig.add_subplot(gs[1, 0])
    ax_histx = fig.add_subplot(gs[0, 0], sharex=ax)
    ax_histy = fig.add_subplot(gs[1, 1], sharey=ax)

    x = df[xlabel]
    y, y_unit = convert_to_optimal_unit(df[zlabel])
    c, c_unit = convert_to_optimal_unit(df[cbar_label])
    c = df[cbar_label] / 1024  # Convert to MiB
    s = np.clip(df[cbar_label] / 1024, 10, 200)  # Marker sizes

    scatter = ax.scatter(x, y, c=c, cmap=cmap, s=s, vmin=0, vmax=max_size / 1024)
    # Adjust colorbar size to match the main plot
    cbar = plt.colorbar(scatter, fraction=0.1, pad=0.01, orientation="horizontal", location='bottom', aspect=40)
    cbar.set_label(f'{cbar_title} ({c_unit})', fontsize=25, fontweight='bold', labelpad=10)
    
    # Calculate histogram and assign colors to each bin
    bins_x = calculate_bins(x)
    hist_x, bin_edges_x = np.histogram(x, bins=bins_x)
    
    bins_y = calculate_bins(y)
    hist_y, bin_edges_y = np.histogram(y, bins=bins_y)

    bin_centers_x = 0.5 * (bin_edges_x[:-1] + bin_edges_x[1:])
    bin_centers_y = 0.5 * (bin_edges_y[:-1] + bin_edges_y[1:])
    
    hist_freq = np.concatenate([hist_x, hist_y])
    
    # Create a colorbar based on the frequency of bins
    norm = mcolors.Normalize(vmin=np.min(hist_freq), vmax=np.max(hist_freq))
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    
    # Adjust the colorbar to represent the bin frequencies
    cbar = plt.colorbar(sm, fraction=0.1, pad=0.01)
    cbar.set_label(f'Offset operation frequency', fontsize=25, fontweight='bold', labelpad=10)
    cbar.ax.tick_params(labelsize=20)

    # Assign colors to histograms based on frequency
    colors_x = cmap(norm(hist_x))
    colors_y = cmap(norm(hist_y))

    ax_histx.bar(bin_centers_x, hist_x, width=np.diff(bin_edges_x), color=colors_x, align='center', alpha=0.7)
    ax_histy.barh(bin_centers_y, hist_y, height=np.diff(bin_edges_y), color=colors_y, align='center', alpha=0.7)
    
    # Plot adjustments
    ax.set_xlabel(x_title, fontsize=30, labelpad=25, fontweight='bold')
    ax.set_ylabel(f'{z_title} ({y_unit})', fontsize=30, labelpad=25, fontweight='bold')
    ax.tick_params(axis='both', which='major', labelsize=20)

    max_process_num = df[xlabel].max()
    step = 1 if max_process_num <= 10 else max_process_num // 10

    ax.set_xticks(np.arange(0, max_process_num + 1, step=step))
    
    ax.minorticks_on()
    ax.grid(which="major", linewidth=1, linestyle='-', color='gray')
    ax.grid(which="minor", linewidth=0.2, linestyle='--', color='lightgray')

    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=False))
    ax.tick_params(axis='y', which='both', length=10, width=2, labelsize=20)  

    ax_histx.set_xlim(ax.get_xlim())
    ax_histy.set_ylim(ax.get_ylim())
    
    ax_histx.tick_params(axis='y', which='both', left=True, right=False, labelleft=True)
    ax_histy.tick_params(axis='x', which='both', bottom=True, top=False, labelbottom=True)
    ax_histx.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)
    ax_histy.tick_params(axis='y', which='both', left=False, right=False, labelleft=False)

    # Titles and final adjustments
    fig.suptitle(graph_title, fontsize=35, fontweight='bold')
    ax_histx.set_title(f'Frequency \nof {x_title}', fontsize=20, fontweight='bold', pad=20)
    #ax_histy.set_title(f'Frequency of {z_title}', fontsize=20, fontweight='bold', rotation=-90, pad=40)

    if save_path2d:
        plt.savefig(save_path2d, dpi=300, bbox_inches='tight', pad_inches=0)
    plt.show()



def plot_zoomed_spatial_pattern1(df_zoom, ylabel, y_title, zlabel, z_title, cbar_label, cbar_title, npi, npt, np, save_path2dzoom, max_size=None):
    x = df_zoom[ylabel]
    y, y_unit = convert_to_optimal_unit(df_zoom[zlabel])
    c, c_unit = convert_to_optimal_unit(df_zoom[cbar_label])
    s = np.clip(df_zoom[cbar_label] / 1024, 10, 200)

    cmap = create_custom_cmap()
    fig, ax = plt.subplots(figsize=(10, 8), dpi=600)
    
    plt.grid(True, which="both", ls="--", alpha=0.3)
    ax.set_ylabel(f'{z_title} ({y_unit})', color="black", fontsize=25)
    ax.set_xlabel(y_title, color="black", fontsize=25)
    ax.tick_params(axis='x', colors='black', labelsize=25, rotation=45)
    ax.tick_params(axis='y', colors='black', labelsize=25, rotation=15)
    plt.yticks(rotation=45)
    #vmax=max_size/1024
    vmax=max_size

    pd2 = ax.scatter(x, y, c=c, marker="d", alpha=0.9, cmap=cmap, s=s, vmin=0, vmax=vmax)
    ax.set_title(f'Zoomed Spatial Pattern for {npi}/{npt} Processes (np)')

    y_min, y_max = y.min(), y.max()
    y_margin = (y_max - y_min) * 0.05
    #axins = inset_axes(ax, width="40%", height="40%", loc=4)
    axins = zoomed_inset_axes(ax, zoom=7, loc=1, borderpad=3) # configura la posición del recuadro del zoom
    #axins.set_xlim(x.min(), x.min() + (x.max() - x.min()) * 0.1)
    axins.set_xlim(x.max()/1.8, x.max()/1.7 ) # determina el area del zoom en el eje x
    #axins.set_xlim(7000, 8000 )
    #axins.set_ylim(y_min - y_margin, y_max + y_margin)
    axins.set_ylim(y_min, y_max/50 ) # determina el area del zoom en el eje y
    #axins.set_ylim(0.015, 0.025 )
    # fix the number of ticks on the inset Axes
    axins.yaxis.get_major_locator().set_params(nbins=3)
    axins.xaxis.get_major_locator().set_params(nbins=3)
    #axins.tick_params(labelleft=False, labelbottom=False)
    axins.tick_params(labelleft=True, labelbottom=True)
    #mark_inset(ax, axins, loc1=2, loc2=4, fc="none", lw=2, ec='r')
    mark_inset(ax, axins, loc1=2, loc2=4, fc="none", ec='0.5')
    axins.scatter(x, y, c=c, marker='d', alpha=0.9, cmap=cmap, s=s, vmin=0, vmax=vmax)
    #axins.set_xlabel(f'Zoomed \n{y_title}')
    #axins.set_ylabel(f'Zoomed \n{z_title} ({y_unit})')

    cbar = plt.colorbar(pd2, ax=ax, fraction=0.08, pad=0.02, label=f'{cbar_title} ({c_unit})')
    if save_path2dzoom:
        plt.savefig(save_path2dzoom, dpi=300, bbox_inches='tight', pad_inches=0)
    plt.show()

def plot_zoomed_spatial_patternt(df_zoom, ylabel, y_title, zlabel, z_title, cbar_label, cbar_title, npi, npt, pn, save_path2dzoom, max_size=None):

    x = df_zoom[ylabel]
    y, y_unit = convert_to_optimal_unit(df_zoom[zlabel])
    c, c_unit = convert_to_optimal_unit(df_zoom[cbar_label])
    s = np.clip(df_zoom[cbar_label] / 1024, 10, 200)

    cmap = create_custom_cmap()
    fig, ax = plt.subplots(figsize=(10, 8), dpi=600)
    
    plt.grid(True, which="both", ls="--", alpha=0.3)
    ax.set_ylabel(f'{z_title} ({y_unit})', color="black", fontsize=20)
    ax.set_xlabel(y_title, color="black", fontsize=20)
    ax.tick_params(axis='x', colors='black', labelsize=20, rotation=45)
    ax.tick_params(axis='y', colors='black', labelsize=20, rotation=15)
    plt.yticks(rotation=45)
    
    vmax = max_size if max_size else c.max()

    pd2 = ax.scatter(x, y, c=c, marker="d", alpha=0.9, cmap=cmap, s=s, vmin=0, vmax=vmax)
    ax.set_title(f'Spatial Pattern Zoom for Process {npi} of {npt} (Process Number: {pn})')

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


    axins = zoomed_inset_axes(ax, zoom=2, loc=1, borderpad=3) # configura la posición del recuadro del zoom
    axins.set_xlim(x_min_zoom, x_max_zoom) # Determina el área del zoom en el eje x
    axins.set_ylim(y_min_zoom, y_max_zoom) # Determina el área del zoom en el eje y
    
    axins.yaxis.get_major_locator().set_params(nbins=3)
    axins.xaxis.get_major_locator().set_params(nbins=3)
    axins.tick_params(labelleft=True, labelbottom=True)

    mark_inset(ax, axins, loc1=2, loc2=4, fc="none", ec='0.5')
    axins.scatter(x, y, c=c, marker='d', alpha=0.9, cmap=cmap, s=s, vmin=0, vmax=vmax)

    cbar = plt.colorbar(pd2, ax=ax, fraction=0.08, pad=0.02, label=f'{cbar_title} ({c_unit})')
    
    if save_path2dzoom:
        plt.savefig(save_path2dzoom, dpi=300, bbox_inches='tight', pad_inches=0)
    
    plt.show()

