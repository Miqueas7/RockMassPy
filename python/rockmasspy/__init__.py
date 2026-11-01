"""RockMassPy: rock mass classifications, Hoek-Brown strength and mining geomechanics."""

from ._rockmasspy_core import *  # noqa: F401,F403

__version__ = "0.1.0"
from .q_tables import Q_TABLES, SRF_CATEGORIES, q_lookup  # noqa: E402,F401
from .issues import TableIssue  # noqa: E402,F401
from .intact_rock import (  # noqa: E402,F401
    MI_ALIASES_ES, MI_SOURCE, MI_TABLE, MR_SOURCE, MR_TABLE, MiEntry, MrEntry, mi_lookup, mr_lookup,
)
from .support import Bolt, Shotcrete, SupportCatalog, SupportType  # noqa: E402,F401
from .range_table import EDITION_BOUNDARIES, RANGE_METHODS, RangeClass, RangeTable  # noqa: E402,F401
from .gsi_charts import GSI_CHARTS, GsiChart, normalize_cell  # noqa: E402,F401
from .cell_table import CellClass, CellTable  # noqa: E402,F401
from .rating_table import CategoricalParam, NumericParam, RatingBin, RatingResult, RatingTable  # noqa: E402,F401
from .labor_table import Classification, LaborTable, select_table  # noqa: E402,F401
from .table_io import SCHEMA, SCHEMA_VERSION, from_dict, load_json, load_yaml, save_json, save_yaml, to_dict  # noqa: E402,F401
from .excel_io import load_excel, load_support_catalog_excel, save_excel  # noqa: E402,F401
