import os
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset
import matplotlib.gridspec as gridspec
from matplotlib.ticker import MultipleLocator
from Modules.DXT_darshan_trace_grapher.colormap import create_custom_cmap

def create_plots(df, title_prefix, max_size, output_path):
    df_zoom = df

    x1 = df['Process_IO']
    y1 = df['Temporal_Order']
    z1 = df['Offset(bytes)'] / 1024 / 1024
    c1 = df['Request_Size(bytes)'] / 1024
    s1 = np.clip(df['Request_Size(bytes)'] / 1024, 10, 200)
    
    x3 = df_zoom['Start_Time(s)']
    x2 = df_zoom['Temporal_Order']
    y2 = df_zoom['Offset(bytes)'] / 1024 / 1024
    c2 = df_zoom['Request_Size(bytes)'] / 1024
    s2 = np.clip(df_zoom['Request_Size(bytes)'] / 1024, 10, 200)

    cmap = create_custom_cmap()

    fig = plt.figure(figsize=(20, 25), dpi=600)
    gs = gridspec.GridSpec(2, 2)

    font_size = 20
    plt.rc('font', family='arial', size=font_size)
    plt.rc('xtick', labelsize=font_size)
    plt.rc('ytick', labelsize=font_size)

    ax1 = plt.subplot(gs[0, 1])
    plt.grid(True, which="both", ls="--", alpha=0.3)
    ax1.set_ylabel('Offset (MiB)', color="black", fontsize=font_size)
    ax1.set_xlabel('Operation Order', color="black", fontsize=font_size)
    ax1.xaxis.labelpad = 20
    ax1.yaxis.labelpad = 2
    ax1.tick_params(axis='x', colors='black', labelsize=font_size, rotation=45)
    ax1.tick_params(axis='y', colors='black', labelsize=font_size, rotation=15)
    plt.yticks(rotation=45)
    pd2 = ax1.scatter(x2, y2, c=c2, marker="d", alpha=0.9, cmap=cmap, s=s2, vmin=0, vmax=max_size / 1024)
    ax1.set_title(f'{title_prefix} - Zoomed spatial pattern for 1/4 processes')

    # Calcular límites automáticos para el eje y del gráfico de inserción
    y2_min, y2_max = y2.min(), y2.max()
    y_margin = (y2_max - y2_min) * 0.05
    axins2 = inset_axes(ax1, width="40%", height="40%", loc=4)
    axins2.set_xlim(x2.min(), x2.min() + (x2.max() - x2.min()) * 0.1)
    axins2.set_ylim(y2_min - y_margin, y2_max + y_margin)
    mark_inset(ax1, axins2, loc1=2, loc2=4, fc="none", lw=2, ec='r')
    axins2.scatter(x2, y2, c=c2, marker='d', alpha=0.9, cmap=cmap, s=s2, vmin=0, vmax=max_size / 1024)
    axins2.set_xlabel('Zoomed Operation Order')
    axins2.set_ylabel('Zoomed Offset (MiB)')

    cbar = plt.colorbar(pd2, ax=ax1, fraction=0.08, pad=0.02, label='Read Request Size (KiB)')

    ax2 = plt.subplot(gs[0, 0], projection='3d', facecolor='white')
    ax2.view_init(elev=15., azim=-25)
    ax2.scatter(x1, y1, z1, c=c1, marker='d', alpha=0.9, cmap=cmap, s=s1, vmin=0, vmax=max_size / 1024)
    ax2.set_title(f'{title_prefix} - Temporal pattern for 4 processes')
    ax2.set_ylabel('Temporal Order', color="black", fontsize=font_size)
    ax2.set_xlabel('Process IO', color="black", fontsize=font_size)
    ax2.set_zlabel('Offset (MiB)', color="black", fontsize=font_size)
    ax2.xaxis.labelpad = 20
    ax2.yaxis.labelpad = 40
    ax2.zaxis.labelpad = 40

    ax2.xaxis.pane.set_edgecolor('black')
    ax2.yaxis.pane.set_edgecolor('black')
    ax2.zaxis.pane.set_edgecolor('black')
    ax2.xaxis.pane.fill = True
    ax2.xaxis.pane.set_alpha(0.5)
    ax2.yaxis.pane.fill = True
    ax2.yaxis.pane.set_alpha(0.5)
    ax2.zaxis.pane.fill = True
    ax2.zaxis.pane.set_alpha(0.5)

    ax2.yaxis._axinfo['tick']['inward_factor'] = 0
    ax2.yaxis._axinfo['tick']['outward_factor'] = 0.5
    ax2.zaxis._axinfo['tick']['inward_factor'] = 0
    ax2.zaxis._axinfo['tick']['outward_factor'] = 0.5

    ax2.yaxis.set_major_locator(MultipleLocator(100))
    ax2.zaxis.set_major_locator(MultipleLocator(250))

    ax3 = plt.subplot(gs[1, :])
    ax3.tick_params(axis='x', colors='black', labelsize=font_size)
    ax3.tick_params(axis='y', colors='black', labelsize=font_size)
    plt.grid(True, which="both", ls="--", alpha=0.3)
    ax3.set_xlabel('Start Time(s)', color="black", fontsize=font_size)
    ax3.set_ylabel('File Offset(MiB)', color="black", fontsize=font_size)
    ax3.xaxis.labelpad = 20
    ax3.yaxis.labelpad = 20
    ax3.tick_params(axis='y', colors='black', labelsize=font_size)
    pd1 = ax3.scatter(x3, y2, c=c2, marker='d', alpha=0.9, cmap=cmap, s=s2, vmin=0, vmax=max_size / 1024)
    ax3.set_title(f'{title_prefix} - Zoomed spatial pattern for 1/4 processes (Start Time)')

    # Calcular límites automáticos para el eje y del gráfico de inserción
    y2_min, y2_max = y2.min(), y2.max()
    y_margin = (y2_max - y2_min) * 0.05
    axins1 = inset_axes(ax3, width="20%", height="20%", loc=2)
    axins1.set_xlim(x3.min(), x3.min() + (x3.max() - x3.min()) * 0.1)
    axins1.set_ylim(y2_min - y_margin, y2_max + y_margin)
    mark_inset(ax3, axins1, loc1=2, loc2=4, fc="none", lw=2, ec='r')
    axins1.scatter(x3, y2, c=c2, marker='d', alpha=0.9, cmap=cmap, s=s2, vmin=0, vmax=max_size / 1024)
    axins1.set_xlabel('Zoomed Start Time(s)')
    axins1.set_ylabel('Zoomed Offset (MiB)')

    cbar = plt.colorbar(pd1, ax=ax3, fraction=0.08, pad=0.01, label='Read Request Size (KiB)')

    estadisticas = df_zoom['Request_Size(bytes)'].describe()

    # Guardar los gráficos
    output_file = output_path / f"{title_prefix}_plots.png"
    plt.savefig(output_file)
    
    plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
    plt.show()

    print(f"Estadísticas General para {title_prefix}:")
    print(estadisticas)
    print(f"Graphs saved to {output_file}")
    
def create_plotsev(df, title_prefix, max_size, output_path):
    df_zoom = df

    x1 = df['Process_IO']
    y1 = df['Temporal_Order']
    z1 = df['Offset(bytes)'] / 1024 / 1024
    c1 = df['Request_Size(bytes)'] / 1024
    s1 = np.clip(df['Request_Size(bytes)'] / 1024, 10, 200)
    
    x3 = df_zoom['Start_Time(s)']
    x2 = df_zoom['Temporal_Order']
    y2 = df_zoom['Offset(bytes)'] / 1024 / 1024
    c2 = df_zoom['Request_Size(bytes)'] / 1024
    s2 = np.clip(df_zoom['Request_Size(bytes)'] / 1024, 10, 200)

    cmap = create_custom_cmap()

    fig = plt.figure(figsize=(20, 25), dpi=600)
    gs = gridspec.GridSpec(2, 2)

    font_size = 20
    plt.rc('font', family='arial', size=font_size)
    plt.rc('xtick', labelsize=font_size)
    plt.rc('ytick', labelsize=font_size)

    ax1 = plt.subplot(gs[0, 1])
    plt.grid(True, which="both", ls="--", alpha=0.3)
    ax1.set_ylabel('Offset (MiB)', color="black", fontsize=font_size)
    ax1.set_xlabel('Operation Order', color="black", fontsize=font_size)
    ax1.xaxis.labelpad = 20
    ax1.yaxis.labelpad = 2
    ax1.tick_params(axis='x', colors='black', labelsize=font_size, rotation=45)
    ax1.tick_params(axis='y', colors='black', labelsize=font_size, rotation=15)
    plt.yticks(rotation=45)
    pd2 = ax1.scatter(x2, y2, c=c2, marker="d", alpha=0.9, cmap=cmap, s=s2, vmin=0, vmax=max_size / 1024)
    ax1.set_title(f'{title_prefix} - Zoomed spatial pattern for 1/4 processes')

    # Personalizar ticks y etiquetas
    ax1.set_xticks([0, 1000, 2000, 3000, 4000])
    ax1.set_xticklabels(['0', '1k', '2k', '3k', '4k'])
    ax1.set_yticks([0, 500, 1000, 1500, 2000])
    ax1.set_yticklabels(['0 MiB', '500 MiB', '1 GiB', '1.5 GiB', '2 GiB'])

    # Calcular límites automáticos para el eje y del gráfico de inserción
    y2_min, y2_max = y2.min(), y2.max()
    y_margin = (y2_max - y2_min) * 0.05
    axins2 = inset_axes(ax1, width="40%", height="40%", loc=4)
    axins2.set_xlim(x2.min(), x2.min() + (x2.max() - x2.min()) * 0.1)
    axins2.set_ylim(y2_min - y_margin, y2_max + y_margin)
    mark_inset(ax1, axins2, loc1=2, loc2=4, fc="none", lw=2, ec='r')
    axins2.scatter(x2, y2, c=c2, marker='d', alpha=0.9, cmap=cmap, s=s2, vmin=0, vmax=max_size / 1024)
    axins2.set_xlabel('Zoomed Operation Order')
    axins2.set_ylabel('Zoomed Offset (MiB)')

    cbar = plt.colorbar(pd2, ax=ax1, fraction=0.08, pad=0.02, label='Read Request Size (KiB)')

    ax2 = plt.subplot(gs[0, 0], projection='3d', facecolor='white')
    ax2.view_init(elev=15., azim=-25)
    ax2.scatter(x1, y1, z1, c=c1, marker='d', alpha=0.9, cmap=cmap, s=s1, vmin=0, vmax=max_size / 1024)
    ax2.set_title(f'{title_prefix} - Temporal pattern for 4 processes')
    ax2.set_ylabel('Temporal Order', color="black", fontsize=font_size)
    ax2.set_xlabel('Process IO', color="black", fontsize=font_size)
    ax2.set_zlabel('Offset (MiB)', color="black", fontsize=font_size)
    ax2.xaxis.labelpad = 20
    ax2.yaxis.labelpad = 40
    ax2.zaxis.labelpad = 40

    ax2.xaxis.pane.set_edgecolor('black')
    ax2.yaxis.pane.set_edgecolor('black')
    ax2.zaxis.pane.set_edgecolor('black')
    ax2.xaxis.pane.fill = True
    ax2.xaxis.pane.set_alpha(0.5)
    ax2.yaxis.pane.fill = True
    ax2.yaxis.pane.set_alpha(0.5)
    ax2.zaxis.pane.fill = True
    ax2.zaxis.pane.set_alpha(0.5)

    ax2.yaxis._axinfo['tick']['inward_factor'] = 0
    ax2.yaxis._axinfo['tick']['outward_factor'] = 0.5
    ax2.zaxis._axinfo['tick']['inward_factor'] = 0
    ax2.zaxis._axinfo['tick']['outward_factor'] = 0.5

    ax2.yaxis.set_major_locator(MultipleLocator(100))
    ax2.zaxis.set_major_locator(MultipleLocator(250))

    # Personalizar ticks y etiquetas del gráfico 3D
    ax2.set_xticks([0, 1, 2, 3])
    ax2.set_xticklabels(['P0', 'P1', 'P2', 'P3'])
    #ax2.set_yticks([0, 1000, 2000, 3000, 4000])
    #ax2.set_yticklabels(['0', '1k', '2k', '3k', '4k'])
    #ax2.set_zticks([0, 500, 1000, 1500, 2000])
    #ax2.set_zticklabels(['0 MiB', '500 MiB', '1 GiB', '1.5 GiB', '2 GiB'])

    ax3 = plt.subplot(gs[1, :])
    ax3.tick_params(axis='x', colors='black', labelsize=font_size)
    ax3.tick_params(axis='y', colors='black', labelsize=font_size)
    plt.grid(True, which="both", ls="--", alpha=0.3)
    ax3.set_xlabel('Start Time(s)', color="black", fontsize=font_size)
    ax3.set_ylabel('File Offset(MiB)', color="black", fontsize=font_size)
    ax3.xaxis.labelpad = 20
    ax3.yaxis.labelpad = 20
    ax3.tick_params(axis='y', colors='black', labelsize=font_size)
    pd1 = ax3.scatter(x3, y2, c=c2, marker='d', alpha=0.9, cmap=cmap, s=s2, vmin=0, vmax=max_size / 1024)
    ax3.set_title(f'{title_prefix} - Zoomed spatial pattern for 1/4 processes (Start Time)')

    # Personalizar ticks y etiquetas del gráfico 2D
    #ax3.set_xticks([0, 2, 4, 6, 8, 10])
    #ax3.set_xticklabels(['0s', '2s', '4s', '6s', '8s', '10s'])
    #ax3.set_yticks([0, 500, 1000, 1500, 2000])
    #ax3.set_yticklabels(['0 MiB', '500 MiB', '1 GiB', '1.5 GiB', '2 GiB'])

    # Calcular límites automáticos para el eje y del gráfico de inserción
    y2_min, y2_max = y2.min(), y2.max()
    y_margin = (y2_max - y2_min) * 0.05
    axins1 = inset_axes(ax3, width="20%", height="20%", loc=2)
    axins1.set_xlim(x3.min(), x3.min() + (x3.max() - x3.min()) * 0.1)
    axins1.set_ylim(y2_min - y_margin, y2_max + y_margin)
    mark_inset(ax3, axins1, loc1=2, loc2=4, fc="none", lw=2, ec='r')
    axins1.scatter(x3, y2, c=c2, marker='d', alpha=0.9, cmap=cmap, s=s2, vmin=0, vmax=max_size / 1024)
    axins1.set_xlabel('Zoomed Start Time(s)')
    axins1.set_ylabel('Zoomed Offset (MiB)')

    cbar = plt.colorbar(pd1, ax=ax3, fraction=0.08, pad=0.01, label='Read Request Size (KiB)')

    estadisticas = df_zoom['Request_Size(bytes)'].describe()

    # Guardar los gráficos
    output_file = output_path / f"{title_prefix}_plots.png"
    plt.savefig(output_file)
    
    plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
    plt.show()

    print(f"Estadísticas General para {title_prefix}:")
    print(estadisticas)
    print(f"Graphs saved to {output_file}")
