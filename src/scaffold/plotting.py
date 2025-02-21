from contextlib import AbstractContextManager
from enum import Enum
from typing import List

MXM_THEME = {
    "title_font": "Space Grotesk",
    "text_font": "Inter",
    "primary": ["#000000", "#FFFFFF", "#381D59", "#FFFAF4"],
    "secondary": ["#ABABF9", "#FF5665", "#11D8C1", "#9E36FF"],
    "tertiary": ["#FF5665", "#9E36FF", "#CE3D4A", "#007D85"],
}


class MXM_STYLE(Enum):
    LIGHT = 1
    DARK = 2


def get_color_cycle(style: MXM_STYLE = MXM_STYLE.LIGHT) -> List[str]:
    """Get color cycle for the chosen style.

    Args:
        style (MXM_STYLE, optional): The style used for plotting. Defaults to MXM_STYLE.LIGHT.

    Returns:
        List[str]: List of colors for the color cycle.
    """
    if style == MXM_STYLE.LIGHT:
        return [
            MXM_THEME["tertiary"][1],
            MXM_THEME["secondary"][1],
            MXM_THEME["tertiary"][2],
            MXM_THEME["secondary"][3],
            MXM_THEME["tertiary"][3],
        ]
    else:
        return [
            MXM_THEME["secondary"][2],
            MXM_THEME["secondary"][1],
            MXM_THEME["tertiary"][0],
            MXM_THEME["primary"][3],
            MXM_THEME["secondary"][0],
        ]


def get_rc_params(style: MXM_STYLE = MXM_STYLE.LIGHT) -> dict:
    """Get rc (runtime configuration) parameters for the chosen style.
    Used for customizing the properties and default styles of Matplotlib.

    Some fonts are not available by default in Matplotlib, so you may need to install them, see :ref:`plotting`.

    Args:
        style (MXM_STYLE, optional): The style used for plotting. Defaults to MXM_STYLE.LIGHT.

    Returns:
        dict: Dictionary with rc parameters.
    """
    import matplotlib.pyplot as plt

    if style == MXM_STYLE.LIGHT:
        fg = MXM_THEME["primary"][0]
        bg = MXM_THEME["primary"][1]
    else:
        fg = MXM_THEME["primary"][3]
        bg = MXM_THEME["primary"][2]
    rc = {
        "axes.grid.axis": "y",
        "font.family": MXM_THEME["text_font"],
        "axes.prop_cycle": plt.cycler(color=get_color_cycle(style)),
        "savefig.transparent": True,
        "axes.spines.left": False,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.spines.bottom": False,
        "figure.facecolor": bg,
        "axes.facecolor": bg,
        "grid.color": fg,
        "text.color": fg,
        "axes.labelcolor": fg,
        "xtick.color": fg,
        "ytick.color": fg,
    }
    return rc


def get_mpl_context(style: MXM_STYLE = MXM_STYLE.LIGHT) -> AbstractContextManager[None]:
    """Get Matplotlib context manager for the chosen style.

    Args:
        style (MXM_STYLE, optional): The style used for plotting. Defaults to MXM_STYLE.LIGHT.

    Returns:
        AbstractContextManager[None]: Context manager for Matplotlib.
    """
    import matplotlib.pyplot as plt

    rc = get_rc_params(style)

    return plt.rc_context(rc=rc)
