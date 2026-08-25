import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

def create_custom_cmap2():
    color_list = [(0, 'red'), (0.2, 'aqua'), (0.4, 'magenta'),  (0.6, 'blue'), (0.8, 'purple'), (1, 'green')]
    return LinearSegmentedColormap.from_list('cool_custom', color_list)
    
def create_custom_cmap():
    """Create a custom colormap for visualization."""
    #color_list = [(0, 'green'), (0.5, 'red'), (1, 'blue')]
    #color_list = [(0, 'red'), (0.5, 'blue'), (1, 'green')]
    #color_list = [(0, 'red'), (0.2, 'greenyellow'), (0.4, 'aqua'),  (0.6, 'blue'), (0.8, 'purple'), (1, 'green')]
    color_list1 = [(0, 'red'), (0.1, 'yellow'), (0.2, 'greenyellow'), (0.4, 'aqua'),  (0.6, 'blue'), (0.8, 'purple'), (1, 'green')]

    cmap = LinearSegmentedColormap.from_list('cool_custom1', color_list1)
        
    return cmap
def create_custom_cmap2():
    """Create a custom colormap for visualization."""
    #color_list = [(0, 'green'), (0.5, 'red'), (1, 'blue')]
    #color_list = [(0, 'red'), (0.5, 'blue'), (1, 'green')]
    #color_list = [(0, 'red'), (0.2, 'greenyellow'), (0.4, 'aqua'),  (0.6, 'blue'), (0.8, 'purple'), (1, 'green')]
    color_list2 = [
    (0, 'orange'),
    (0.1, 'magenta'),
    (0.2, 'cyan'),
    (0.4, 'darkorange'),
    (0.6, 'pink'),
    (0.8, 'darkred'),
    (1, 'limegreen'),
    (1.2, 'navy'),
    (1.4, 'brown'),
    (1.6, 'olive')
]
    
    cmap2 = LinearSegmentedColormap.from_list('cool_custom2', color_list2)
    
    return cmap2
    

def create_custom_cmap():
    """Create a custom colormap for visualization."""
    #color_list = [(0, 'green'), (0.5, 'red'), (1, 'blue')]
    #color_list = [(0, 'red'), (0.5, 'blue'), (1, 'green')]
    #color_list = [(0, 'red'), (0.2, 'greenyellow'), (0.4, 'aqua'),  (0.6, 'blue'), (0.8, 'purple'), (1, 'green')]
    color_list3 = [(0, 'aqua'), (0.2, 'navy'), (0.4, 'darkorange'),  (0.6, 'greenyellow'), (0.8, 'green'), (1, 'limegreen')]
    color_list = [(0, 'red'), (0.1, 'yellow'), (0.2, 'greenyellow'), (0.4, 'aqua'),  (0.6, 'blue'), (0.8, 'purple'), (1, 'green')]
    color_list1 = [
    (0, 'orange'),
    (0.1, 'magenta'),
    (0.2, 'cyan'),
    (0.3, 'darkcyan'),
    (0.4, 'darkorange'),
    (0.5, 'pink'),
    (0.6, 'darkred'),
    (0.7, 'limegreen'),
    (0.8, 'navy'),
    (0.9, 'brown'),
    (1, 'olive')
    ]

    color_list_black_based = [
        (0, 'gray'),
        (0.1, 'dimgray'),  # Gris oscuro
        (0.2, 'darkslategray'),  # Gris pizarra oscuro
        (0.3, 'darkolivegreen'),  # Verde oliva oscuro
        (0.4, 'darkblue'),  # Azul oscuro
        (0.5, 'darkred'),  # Rojo oscuro
        (0.6, 'darkmagenta'),  # Magenta oscuro
        (0.7, 'midnightblue'),  # Azul medianoche
        (0.8, 'saddlebrown'),  # Marrón silla oscuro
        (0.9, 'darkgreen'),  # Verde oscuro
        (1, 'black')  # Volviendo al negro
    ]

    cmap = LinearSegmentedColormap.from_list('cool_custom', color_list) # DeepGalaxy
    cmap1 = LinearSegmentedColormap.from_list('cool_custom1', color_list1) # HDF5
    cmap2 = LinearSegmentedColormap.from_list('cool_custom2', color_list_black_based) # Histrograma
    cmap3 = LinearSegmentedColormap.from_list('cool_custom3', color_list3) # NPZ
    return cmap, cmap1, cmap2 cmap3
