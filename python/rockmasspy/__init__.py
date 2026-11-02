"""RockMassPy: rock mass classifications, Hoek-Brown strength and mining geomechanics."""

from ._rockmasspy_core import *  # noqa: F401,F403

__version__ = "0.1.0"


def _install_reprs():
    """Da a cada estructura del núcleo un __repr__ armado con sus propiedades públicas."""
    import enum
    from . import _rockmasspy_core as core

    def show(value):
        if isinstance(value, core.MethodInfo):  # anidado: solo el identificador
            return f"MethodInfo(method_id={value.method_id!r}, ...)"
        return repr(value)

    def make(names):
        def __repr__(self):
            body = ", ".join(f"{n}={show(getattr(self, n))}" for n in names)
            return f"{type(self).__name__}({body})"
        return __repr__

    for cls in vars(core).values():
        if not isinstance(cls, type) or issubclass(cls, enum.Enum):
            continue
        names = [n for n, v in vars(cls).items() if not n.startswith("_") and isinstance(v, property)]
        if names:
            cls.__repr__ = make(names)


_install_reprs()
del _install_reprs
from .q_tables import Q_TABLES, SRF_CATEGORIES, q_lookup  # noqa: E402,F401
from .issues import TableIssue  # noqa: E402,F401
from .intact_rock import (  # noqa: E402,F401
    MI_ALIASES_ES, MI_SOURCE, MI_TABLE, MR_SOURCE, MR_TABLE, MiEntry, MrEntry, mi_lookup, mr_lookup,
)
from .support import Bolt, Shotcrete, SupportCatalog, SupportType  # noqa: E402,F401
from .range_table import EDITION_BOUNDARIES, RANGE_METHODS, RangeClass, RangeTable  # noqa: E402,F401
from .gsi_charts import GSI_CHARTS, GsiChart, normalize_cell  # noqa: E402,F401
from .cell_table import CellClass, CellTable  # noqa: E402,F401
from .vallejo_lines import (  # noqa: E402,F401
    Q_PRIME_LINES, RMR_PRIME_LINES, VALLEJO_LINES_SOURCE, ChartLine, q_prime_range, rmr_prime_range,
)
from .chart_regions import Region, locate  # noqa: E402,F401
from .q_chart_data import ESR_TABLES, Q_CHART_FRAME, Q_CHARTS, QChartCategory, QChartData  # noqa: E402,F401
from .q_support import QChartReading, QSupportResult, read_q_chart, recommend_q_support  # noqa: E402,F401
from .stability_graphs import STABILITY_GRAPHS, GraphReading, StabilityGraph, read_stability_graph  # noqa: E402,F401
from .mathews import FACTOR_B_INFO, JOINT_ORIENTATION_CURVES, MathewsResult, factor_b, mathews_stability  # noqa: E402,F401
from .rating_table import CategoricalParam, NumericParam, RatingBin, RatingResult, RatingTable  # noqa: E402,F401
from .labor_table import Classification, LaborTable, select_table  # noqa: E402,F401
from .table_io import SCHEMA, SCHEMA_VERSION, from_dict, load_json, load_yaml, save_json, save_yaml, to_dict  # noqa: E402,F401
from .excel_io import load_excel, load_support_catalog_excel, save_excel  # noqa: E402,F401
from .csv_io import load_csv_dir, load_support_catalog_csv, save_csv_dir  # noqa: E402,F401
from .tramos import TRAMO_COLUMNS, Tramo, load_tramos  # noqa: E402,F401
from .batch import (BatchSummary, EsrSpec, TramoResult, add_q_chart_reference, classify_tramos,  # noqa: E402,F401
                    q_chart_crosstab, save_results, summarize)  # noqa: E402,F401
from .stope_surfaces import (SURFACE_COLUMNS, StopeSurface, StopeSurfaceResult, assess_stope_surfaces,  # noqa: E402,F401
                             load_stope_surfaces, save_stope_results, stope_zone_counts)
from .table_files import load_table  # noqa: E402,F401
