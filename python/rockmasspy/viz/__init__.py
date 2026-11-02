"""Gráficos de RockMassPy. Requiere matplotlib (pip install rockmasspy[viz]); se importa solo al llamar."""

from .save import save_figure  # noqa: F401
from .classes import plot_class_histogram  # noqa: F401
from .correlation import plot_correlation  # noqa: F401
from .cartilla import plot_cartilla  # noqa: F401
from .envelopes import plot_hb_envelopes  # noqa: F401
from .gsi_quant import plot_gsi_quantified  # noqa: F401
from .style import DEFAULT_SUPPORT_COLORS, SIZES_CM, TEXTS, Style, footer, new_figure, support_color, text  # noqa: F401
from .maps import plot_labor_profile, plot_plan_map  # noqa: F401
from .q_chart import plot_q_chart  # noqa: F401
from .stability_graph import plot_stability_graph  # noqa: F401
from .stereonet import plot_stereonet  # noqa: F401
