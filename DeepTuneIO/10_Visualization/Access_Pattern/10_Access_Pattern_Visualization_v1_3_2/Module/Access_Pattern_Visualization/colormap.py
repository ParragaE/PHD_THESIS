from __future__ import annotations

from matplotlib.colors import LinearSegmentedColormap


_COLOR_MAPS = {
    "deepgalaxy": [
        (0.0, "red"), (0.2, "greenyellow"), (0.4, "aqua"),
        (0.6, "blue"), (0.8, "purple"), (1.0, "green"),
    ],
    "hdf5": [
        (0.0, "brown"), (0.2, "magenta"), (0.4, "darkorange"),
        (0.6, "lightblue"), (0.8, "darkcyan"), (1.0, "olive"),
    ],
    "npz": [
        (0.0, "darkorange"), (0.2, "greenyellow"), (0.4, "limegreen"),
        (0.6, "lightseagreen"), (0.8, "skyblue"), (1.0, "blue"),
    ],
    "tfrecord": [
        (0.0, "yellow"), (0.2, "darkgoldenrod"), (0.4, "darkred"),
        (0.6, "tomato"), (0.8, "indigo"), (1.0, "purple"),
    ],
    "default": [
        (0.0, "navy"), (0.5, "cyan"), (1.0, "yellow"),
    ],
}


def create_request_size_cmap(application: str, file_format: str):
    fmt = str(file_format or "").lower().lstrip(".")
    if fmt == "h5":
        fmt = "hdf5"
    if fmt == "tfrecords":
        fmt = "tfrecord"

    # Keep the original DeepGalaxy palette for historical continuity.
    key = "deepgalaxy" if str(application).lower() == "deepgalaxy" else fmt
    colors = _COLOR_MAPS.get(key, _COLOR_MAPS["default"])
    return LinearSegmentedColormap.from_list(
        f"deeptuneio_access_{key}", colors
    )
