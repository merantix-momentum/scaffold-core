import matplotlib.pyplot as plt
import pytest

from scaffold.plotting import add_logo, get_color_cycle, get_mpl_context, MXM_STYLE

ALL_STYLE_VARIANTS = [
    (MXM_STYLE.LIGHT, 0),
    (MXM_STYLE.LIGHT, 1),
    (MXM_STYLE.DARK, 0),
    (MXM_STYLE.DARK, 1),
    (MXM_STYLE.DARK, 2),
]


@pytest.mark.parametrize("style,variant", ALL_STYLE_VARIANTS)
def test_smoke(style, variant):
    """Test if all dependencies for plotting are installed and a simple plot can be created."""
    with get_mpl_context(style, variant):
        fig, ax = plt.subplots(figsize=(10, 5))
        N = 10
        ax.bar(range(N), range(1, N + 1), label="series 1", color=get_color_cycle(style=style))
        ax.set_title("Amazing title")
        ax.set_xlabel("Awesome Label")
        ax.set_ylabel("Awesome Label")
        ax.legend()
    plt.close(fig)


@pytest.mark.parametrize("style,variant", ALL_STYLE_VARIANTS)
def test_add_logo(style, variant):
    """Test that add_logo adds an artist to the figure."""
    with get_mpl_context(style, variant):
        fig, ax = plt.subplots()
        ax.bar([0, 1], [1, 2])
        num_artists_before = len(fig.get_children())
        add_logo(fig, style=style, variant=variant)
        assert len(fig.get_children()) > num_artists_before
    plt.close(fig)
