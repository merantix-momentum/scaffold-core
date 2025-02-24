.. _plotting:

Plotting
========

The plotting subpackage provides a set of functions to create plots that follow the Merantix Momentum style guide.
The style is based on the [default Matplotlib style](https://github.com/matplotlib/matplotlib/blob/main/lib/matplotlib/mpl-data/stylelib/classic.mplstyle).

Download the fonts from Google Fonts::

    !wget 'https://github.com/google/fonts/raw/main/ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf'
    !wget 'https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf'

Add the fonts to the font manager::

    from matplotlib import font_manager as fm, pyplot as plt
    font_files = fm.findSystemFonts('.')
    for font_file in font_files:
        fm.fontManager.addfont(font_file)

Alternatively, install the fonts to the system after downloading (e.g., adding them to Font Book on macOS) and add them to the font manager (otherwise they are not in the font cache)::

    from matplotlib import font_manager as fm, pyplot as plt
    font_files = fm.findSystemFonts()
    for font_file in font_files:
        fm.fontManager.addfont(font_file)

Examples
--------

Example Usage 1::

    import matplotlib.pyplot as plt

    style = MXM_STYLE.LIGHT
    with get_mpl_context(style) as ctx:
      plt.figure(figsize=(10,5))
      N = 10
      plt.bar((range(N)), (range(1, N+1, 1)), label='series 1', color=get_color_cycle(style=style))
      plt.title("Amazing title")
      plt.xlabel('Awesome Label')
      plt.ylabel('Awesome Label')

      plt.legend()

Example Usage 2::

    import matplotlib.pyplot as plt

    style = MXM_STYLE.DARK
    with get_mpl_context(style) as ctx:
      plt.figure(figsize=(10,5))
      N = 20
      for c in get_color_cycle(style=style):
          plt.plot(np.random.random(N), label=f'series {c}', color=c)
      plt.title("Amazing title")
      plt.xlabel('Awesome Label')
      plt.ylabel('Awesome Label')

    plt.legend()

Example Usage 3::

    import seaborn as sns
    import numpy as np

    # demo data set
    N = 10
    data = {
        'idx': range(N),
        'x': np.random.random(N),
        'y': np.random.random(N),
        'size': np.random.random(N)
    }
    with get_mpl_context():
      sns.scatterplot(data=data, x="x", y="y",
                      size="size", hue='idx', legend=False,
                      sizes=(100, 500)).set(title='Awesome Title')

Applying the rc params to all plots::

    import matplotlib.pyplot as plt

    style = MXM_STYLE.LIGHT
    rc = get_rc_params(style)
    plt.rcParams.update(rc)
