.. _plotting:

Plotting
========

The plotting subpackage provides functions to create plots following the Merantix Momentum style guide.

Fonts
-----

Download and install the required fonts from Google Fonts::

    wget 'https://github.com/google/fonts/raw/main/ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf'
    wget 'https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf'

Install them to your system (e.g., Font Book on macOS), then register with matplotlib::

    from matplotlib import font_manager as fm
    for font_file in fm.findSystemFonts():
        fm.fontManager.addfont(font_file)

Styles and Variants
-------------------

Two styles are available via ``MXM_STYLE``:

- ``MXM_STYLE.LIGHT`` — light backgrounds (variant 0: white, variant 1: offwhite)
- ``MXM_STYLE.DARK`` — dark backgrounds (variant 0: blueberry, variant 1: black, variant 2: admiral)

Use ``get_mpl_context(style, variant)`` to apply the theme as a context manager.

Title Font
----------

Matplotlib has no rcParam for title font family, so titles use the body font by default.
Apply the title font explicitly using the ``TITLE_FONT`` dict::

    fig.suptitle("My Title", **plotting.TITLE_FONT)
    ax.set_title("Axes Title", **plotting.TITLE_FONT)

Colors
------

Individual colors can be imported directly::

    from scaffold.plotting import ELECTRIC, CARIBBEAN, CORAL, ADMIRAL, PINE

Or get the full color cycle for a style::

    from scaffold.plotting import get_color_cycle, MXM_STYLE
    colors = get_color_cycle(style=MXM_STYLE.LIGHT)

Example
-------

::

    from scaffold import plotting
    import matplotlib.pyplot as plt
    import numpy as np

    style = plotting.MXM_STYLE.LIGHT
    variant = 0

    with plotting.get_mpl_context(style, variant):
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.suptitle("Example plot", **plotting.TITLE_FONT)

        N = 5
        x = np.arange(N)
        for i in range(3):
            ax.bar(x + i * 0.25, np.random.randint(3, 15, N), width=0.2)

        ax.set_xlabel("Category")
        ax.set_ylabel("Value")
        ax.legend(["A", "B", "C"], loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)

    plt.tight_layout()
    plt.show()

Logo Helper
-----------

Use ``plotting.add_logo()`` to place a logo in the corner of a figure::

    plotting.add_logo(fig, style=style, variant=variant, position="upper right")

Custom logos can be passed via the ``logo_path`` argument (supports any fsspec-compatible path)::

    plotting.add_logo(fig, logo_path="gs://my-bucket/logo.png")

Applying Globally
-----------------

To apply the style to all plots without a context manager::

    import matplotlib.pyplot as plt
    from scaffold.plotting import get_rc_params, MXM_STYLE

    plt.rcParams.update(get_rc_params(MXM_STYLE.LIGHT, variant=0))
