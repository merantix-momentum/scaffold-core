import matplotlib.pyplot as plt

from scaffold.plotting import get_color_cycle, get_mpl_context, MXM_STYLE


def test_smoke():
    """Test if all dependencies for plotting are installed and a simple plot can be created."""
    style = MXM_STYLE.LIGHT
    with get_mpl_context(style):
        plt.figure(figsize=(10, 5))
        N = 10
        plt.bar((range(N)), (range(1, N + 1, 1)), label="series 1", color=get_color_cycle(style=style))
        plt.title("Amazing title")
        plt.xlabel("Awesome Label")
        plt.ylabel("Awesome Label")

        plt.legend()
