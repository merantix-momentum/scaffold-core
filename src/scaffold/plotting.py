from contextlib import AbstractContextManager
from enum import Enum
from pathlib import Path
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    import matplotlib.pyplot as plt

ASSETS_DIR = Path(__file__).parent / "assets"

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


LOGO_MAP = {
    (MXM_STYLE.LIGHT, 0): ASSETS_DIR / "logo_black.png",
    (MXM_STYLE.LIGHT, 1): ASSETS_DIR / "logo_black.png",
    (MXM_STYLE.DARK, 0): ASSETS_DIR / "logo_offwhite.png",
    (MXM_STYLE.DARK, 1): ASSETS_DIR / "logo_offwhite.png",
    (MXM_STYLE.DARK, 2): ASSETS_DIR / "logo_offwhite.png",
}


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


def add_logo(
    fig: plt.Figure,
    style: MXM_STYLE = MXM_STYLE.LIGHT,
    variant: int = 0,
    logo_path: str | Path | None = None,
    position: str = "upper right",
    size: float = 0.08,
    alpha: float = 0.8,
) -> None:
    """Add a small logo to the corner of a matplotlib figure.

    Args:
        fig: The matplotlib figure to add the logo to.
        style: The style, used to pick an appropriate default logo. Defaults to MXM_STYLE.LIGHT.
        variant: The variant of the style. Used to select a contrasting logo. Defaults to 0.
        logo_path: Path or URI to a custom logo image. If None, uses the default logo for the style/variant.
        position: Corner placement. One of "lower right", "lower left", "upper right", "upper left".
        size: Size of the logo as a fraction of figure height. Defaults to 0.08.
        alpha: Opacity of the logo. Defaults to 0.8.
    """
    import io

    import fsspec
    import matplotlib.image as mpimg
    from matplotlib.offsetbox import AnnotationBbox, OffsetImage

    if logo_path is None:
        logo_path = str(LOGO_MAP[(style, variant)])

    with fsspec.open(str(logo_path), "rb") as f:
        data = f.read()

    img = mpimg.imread(io.BytesIO(data), format=Path(str(logo_path)).suffix.lstrip("."))

    positions = {
        "lower right": (0.95, 0.05),
        "lower left": (0.05, 0.05),
        "upper right": (0.95, 0.95),
        "upper left": (0.05, 0.95),
    }
    xy = positions[position]

    fig_height_px = fig.get_size_inches()[1] * fig.dpi
    logo_height_px = size * fig_height_px
    zoom = logo_height_px / img.shape[0]

    imagebox = OffsetImage(img, zoom=zoom, alpha=alpha)
    ab = AnnotationBbox(imagebox, xy, xycoords="figure fraction", frameon=False)
    fig.add_artist(ab)
