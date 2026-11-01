"""Estilo, colores y textos es/en de los gráficos. Sin importar matplotlib al cargar el módulo."""

from __future__ import annotations

from dataclasses import dataclass

from ..table_io import _optional

# Del sostenimiento más liviano al más pesado: verde, amarillo, naranja, rojo, morado.
# Elección: el tono sigue ese orden y la luminosidad relativa (WCAG) baja de forma estricta,
# con al menos 0.04 entre vecinos, de 0.85 (verde pálido) a 0.02 (morado oscuro). Así el orden
# sobrevive al imprimir en blanco y negro. No se simuló daltonismo con una herramienta externa.
DEFAULT_SUPPORT_COLORS: tuple[str, ...] = (
    "#E5F5B0",  # verde pálido
    "#FFE680",  # amarillo
    "#FDC456",  # ámbar
    "#FB9A3C",  # naranja claro
    "#F26A2E",  # naranja
    "#E03A2C",  # rojo
    "#BC1A40",  # rojo carmín
    "#862280",  # morado
    "#3F0F4F",  # morado oscuro
)

# (ancho, alto) en cm: la cartilla es vertical; A4 y A3 son horizontales.
SIZES_CM = {"cartilla": (21.0, 29.7), "A4": (29.7, 21.0), "A3": (42.0, 29.7)}

# Cada gráfico agrega aquí sus textos: TEXTS[clave][idioma].
TEXTS: dict[str, dict[str, str]] = {
    "undefined": {"es": "sin definir", "en": "undefined"},
    "engineer_decides": {
        "es": "la librería recomienda, el ingeniero decide",
        "en": "the library recommends, the engineer decides",
    },
    "gsi_quant_title": {"es": "Carta GSI cuantificada", "en": "Quantified GSI chart"},
    "jcond89_axis": {"es": "Condición de juntas (JCond89)", "en": "Joint condition (JCond89)"},
    "rqd_axis": {"es": "RQD (%)", "en": "RQD (%)"},
    "gsi_label": {"es": "GSI", "en": "GSI"},
}


@dataclass(frozen=True)
class Style:
    lang: str = "es"
    size: str = "A4"
    brand: str = ""
    dpi: int = 200
    support_colors: tuple[str, ...] = DEFAULT_SUPPORT_COLORS
    font_size: float = 9.0

    def __post_init__(self):
        if self.lang not in ("es", "en"):
            raise ValueError(f"lang must be one of 'es', 'en', got {self.lang!r}")
        if self.size not in SIZES_CM:
            raise ValueError(f"size must be one of 'cartilla', 'A4', 'A3', got {self.size!r}")
        if not 50 <= self.dpi <= 1200:
            raise ValueError(f"dpi must be in [50, 1200], got {self.dpi!r}")


def _mpl():
    """matplotlib, o el ImportError que nombra el extra [viz]."""
    return _optional("matplotlib", "viz")


def text(key: str, lang: str) -> str:
    try:
        return TEXTS[key][lang]
    except KeyError:
        raise KeyError(f"no text for key={key!r}, lang={lang!r}") from None


def support_color(order: int, n_types: int, style: Style) -> str:
    """Color del tipo `order` (1..n_types): el 1 es el primero de la paleta, el último es el final."""
    if not 1 <= order <= n_types:
        raise ValueError(f"order must be in 1..{n_types}, got {order!r}")
    colors = style.support_colors
    if n_types == 1:
        return colors[0]
    return colors[round((order - 1) * (len(colors) - 1) / (n_types - 1))]


def new_figure(style: Style):
    """Figura sin pyplot (sin estado global ni ventanas), con la marca abajo a la derecha."""
    _mpl()
    from matplotlib.figure import Figure

    w, h = SIZES_CM[style.size]
    fig = Figure(figsize=(w / 2.54, h / 2.54), dpi=style.dpi)
    if style.brand:
        fig.text(0.99, 0.01, style.brand, ha="right", va="bottom", fontsize=style.font_size - 1)
    return fig


def footer(fig, source: str, style: Style) -> None:
    """Fuente o edición abajo a la izquierda; todo gráfico la llama."""
    _mpl()
    fig.text(0.01, 0.01, source, ha="left", va="bottom", fontsize=style.font_size - 2)
