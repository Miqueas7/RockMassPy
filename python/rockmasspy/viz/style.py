"""Estilo, colores y textos es/en de los gráficos. Sin importar matplotlib al cargar el módulo."""

from __future__ import annotations

from dataclasses import dataclass

from ..table_io import _optional
from ..vallejo_lines import VALLEJO_LINES_SOURCE

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
    "hb_envelope_title": {"es": "Envolvente de Hoek-Brown", "en": "Hoek-Brown envelope"},
    "sigma1_axis": {"es": "σ1 (MPa)", "en": "σ1 (MPa)"},
    "sigma3_axis": {"es": "σ3 (MPa)", "en": "σ3 (MPa)"},
    "tau_axis": {"es": "τ (MPa)", "en": "τ (MPa)"},
    "sigma_n_axis": {"es": "σn (MPa)", "en": "σn (MPa)"},
    "hb_curve": {"es": "Hoek-Brown", "en": "Hoek-Brown"},
    "mc_line": {"es": "Mohr-Coulomb (ajuste)", "en": "Mohr-Coulomb (fit)"},
    "lab_tests": {"es": "Ensayos de laboratorio", "en": "Lab tests"},
    "gsi_label": {"es": "GSI", "en": "GSI"},
    "no_support": {"es": "sin sostenimiento", "en": "no support"},
    "gsi_struct_LF": {"es": "levemente fracturada", "en": "slightly fractured"},
    "gsi_struct_F": {"es": "fracturada", "en": "fractured"},
    "gsi_struct_MF": {"es": "muy fracturada", "en": "very fractured"},
    "gsi_struct_IF": {"es": "intensamente fracturada", "en": "intensely fractured"},
    "gsi_struct_T": {"es": "triturada", "en": "crushed"},
    # Hoek-Marinos: sus códigos no chocan con los de Vallejo dentro de un mismo eje (cond P = «pobre» en ambas)
    "gsi_struct_IM": {"es": "intacta o masiva", "en": "intact or massive"},
    "gsi_struct_B": {"es": "en bloques", "en": "blocky"},
    "gsi_struct_VB": {"es": "muy fracturada en bloques", "en": "very blocky"},
    "gsi_struct_BD": {"es": "bloques perturbados, con planos débiles", "en": "disturbed blocks with weak seams"},
    "gsi_struct_D": {"es": "desintegrada", "en": "disintegrated"},
    "gsi_struct_LS": {"es": "laminada o cizallada", "en": "laminated or sheared"},
    "gsi_cond_VG": {"es": "muy buena", "en": "very good"},
    "gsi_cond_G": {"es": "buena", "en": "good"},
    "gsi_cond_F": {"es": "regular", "en": "fair"},
    "gsi_cond_VP": {"es": "muy pobre", "en": "very poor"},
    "gsi_cond_MB": {"es": "muy buena", "en": "very good"},
    "gsi_cond_B": {"es": "buena", "en": "good"},
    "gsi_cond_R": {"es": "regular", "en": "fair"},
    "gsi_cond_P": {"es": "pobre", "en": "poor"},
    "gsi_cond_MP": {"es": "muy pobre", "en": "very poor"},
    "bolt": {"es": "Perno", "en": "Bolt"},
    "shotcrete": {"es": "shotcrete", "en": "shotcrete"},
    "with_fiber": {"es": "con fibra", "en": "with fibre"},
    "without_fiber": {"es": "sin fibra", "en": "without fibre"},
    "mesh": {"es": "malla", "en": "mesh"},
    "arch": {"es": "cimbra", "en": "steel arch"},
    "span": {"es": "Luz", "en": "Span"},
    "author": {"es": "Autor", "en": "Author"},
    "date": {"es": "Fecha", "en": "Date"},
    "support_legend": {"es": "Tipos de sostenimiento", "en": "Support types"},
    "structure_axis": {"es": "Estructura", "en": "Structure"},
    "condition_axis": {"es": "Condición de la superficie", "en": "Surface condition"},
    "range_axis": {"es": "Valor", "en": "Value"},
    "correlation_title": {"es": "Correlaciones entre sistemas", "en": "Correlations between systems"},
    "scatter_points": {"es": "Datos del sitio", "en": "Site data"},
    "global_scatter_note": {
        "es": "las correlaciones globales tienen mucha dispersión; calibra una correlación propia del sitio",
        "en": "global correlations have high scatter; calibrate a site correlation",
    },
    "class_hist_title": {"es": "Valores por clase", "en": "Values per class"},
    "count_axis": {"es": "Cantidad", "en": "Count"},
    "outside_classes": {"es": "Fuera de toda clase", "en": "Outside every class"},
    "lines_source": {
        "es": "líneas RMR′ digitalizadas de Osinergmin (2017), Anexo A.17 (cartilla de Vallejo, 2011)",
        "en": "RMR′ lines " + VALLEJO_LINES_SOURCE,  # la fuente en inglés vive una sola vez, en vallejo_lines
    },
    "boundary_rule": {"es": "un valor en el límite toma la clase peor", "en": "a value on a boundary takes the worse class"},
    "site": {"es": "sitio", "en": "site"},
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
        if not self.support_colors:
            raise ValueError("support_colors must not be empty")


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
    if n_types > len(colors):  # repetir colores confundiría dos tipos distintos
        raise ValueError(f"{n_types} support types but only {len(colors)} colours; "
                         f"pass Style(support_colors=(...)) with at least {n_types} colours")
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
