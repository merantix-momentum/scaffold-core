from contextlib import AbstractContextManager
from enum import Enum
from typing import List

# Primary
BLACK = "#000000"
WHITE = "#FFFFFF"
BLUEBERRY = "#381D59"
OFFWHITE = "#FFFAF4"

# Secondary
LAVENDER = "#ABABF9"
CARIBBEAN = "#11D8C1"
CORAL = "#FF5665"
ELECTRIC = "#9E36FF"

# Tertiary
VANILLA = "#FFFFAE"
ADMIRAL = "#1D0693"
VERMILLION = "#CE3D4A"
PINE = "#007D85"

MXM_THEME = {
    "title_font": "Space Grotesk",
    "text_font": "Inter",
    "primary": [BLACK, WHITE, BLUEBERRY, OFFWHITE],
    "secondary": [LAVENDER, CARIBBEAN, CORAL, ELECTRIC],
    "tertiary": [VANILLA, ADMIRAL, VERMILLION, PINE],
}

# Can be applied using fig.suptitle("title", **TITLE_FONT)
TITLE_FONT = {"fontfamily": MXM_THEME["title_font"]}


class MXM_STYLE(Enum):
    """Plotting style options."""

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
            ELECTRIC,
            CARIBBEAN,
            VERMILLION,
            ADMIRAL,
            PINE,
        ]
    elif style == MXM_STYLE.DARK:
        return [
            VANILLA,
            CARIBBEAN,
            CORAL,
            OFFWHITE,
            LAVENDER,
        ]
    else:
        raise ValueError(f"Invalid style: {style}")


def get_rc_params(style: MXM_STYLE = MXM_STYLE.LIGHT, variant: int = 0) -> dict:
    """Get rc (runtime configuration) parameters for the chosen style.
    Used for customizing the properties and default styles of Matplotlib.

    Some fonts are not available by default in Matplotlib, so you may need to install them, see :ref:`plotting`.

    Args:
        style (MXM_STYLE, optional): The style used for plotting. Defaults to MXM_STYLE.LIGHT.
        variant (int, optional): The variant of the style to use. Defaults to 0.
    Returns:
        dict: Dictionary with rc parameters.
    """
    import matplotlib.pyplot as plt

    if style == MXM_STYLE.LIGHT:
        # white background
        if variant == 0:
            fg = BLACK
            bg = WHITE

        # offwhite background
        elif variant == 1:
            fg = BLACK
            bg = OFFWHITE
        else:
            raise ValueError(f"Invalid variant: {variant}")
    elif style == MXM_STYLE.DARK:
        # blueberry background
        if variant == 0:
            fg = OFFWHITE
            bg = BLUEBERRY

        # black background
        elif variant == 1:
            fg = OFFWHITE
            bg = BLACK

        # admiral background
        elif variant == 2:
            fg = OFFWHITE
            bg = ADMIRAL
        else:
            raise ValueError(f"Invalid variant: {variant}")
    else:
        raise ValueError(f"Invalid style: {style}")

    rc = {
        "axes.grid.axis": "y",
        "font.family": MXM_THEME["text_font"],
        "axes.prop_cycle": plt.cycler(color=get_color_cycle(style)),
        "savefig.transparent": True,
        "axes.spines.left": False,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.spines.bottom": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "figure.facecolor": bg,
        "axes.facecolor": bg,
        "grid.color": fg,
        "text.color": fg,
        "axes.labelcolor": fg,
        "xtick.color": fg,
        "ytick.color": fg,
        "legend.frameon": False,
    }
    return rc


def get_mpl_context(style: MXM_STYLE = MXM_STYLE.LIGHT, variant: int = 0) -> AbstractContextManager[None]:
    """Get Matplotlib context manager for the chosen style.

    Args:
        style (MXM_STYLE, optional): The style used for plotting. Defaults to MXM_STYLE.LIGHT.
        variant (int, optional): The variant of the style to use. Defaults to 0.

    Returns:
        AbstractContextManager[None]: Context manager for Matplotlib.
    """
    import matplotlib.pyplot as plt

    rc = get_rc_params(style, variant)

    return plt.rc_context(rc=rc)
