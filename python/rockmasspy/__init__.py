"""RockMassPy: rock mass classifications, Hoek-Brown strength and mining geomechanics."""

from ._rockmasspy_core import *  # noqa: F401,F403

__version__ = "0.1.1"


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
from .history import (FINDING_KINDS, FINDING_RESULT_COLUMNS, HISTORY_TRAMO_COLUMNS, INSPECTION_COLUMNS,  # noqa: E402,F401
                      History, HistoryAudit, HistoryFinding, HistoryTramo, Inspection, Level1Rows, LevelReadiness,
                      SupportTypeDef, TramoOutcome, audit_history, check_group_by, history_audit_counts, labor_key,
                      level1_rows, level2_rows, level3_parameters, level3_rows, load_history, save_history_findings, save_history_xlsx, tramo_outcomes)
from .batch import (BatchSummary, EsrSpec, TramoDistributionRow, TramoResult, add_q_chart_reference,  # noqa: E402,F401
                    classify_tramos, load_tramo_distributions, q_chart_crosstab, save_results, summarize)  # noqa: E402,F401
from .stope_surfaces import (SURFACE_COLUMNS, StopeSurface, StopeSurfaceResult, assess_stope_surfaces,  # noqa: E402,F401
                             load_stope_surfaces, save_stope_results, stope_zone_counts)
from .table_files import load_table  # noqa: E402,F401
from .slopes import (FACE_COLUMNS, JOINT_COLUMNS, FamilyStats, JointRecord, SlopeFace, SlopeResult, SmrCase,  # noqa: E402,F401
                     assess_slopes, load_families, load_slope_faces, save_slope_results, slope_counts)
from .normative import (COMPARISONS, FORCES, RULES, VERIFICATIONS, NormativeProfile, NormItem,  # noqa: E402,F401
                        available_profiles, get_profile, load_profile)
from .design_inputs import (DESIGN_SHEETS, DesignInputs, PedestrianRefugeSpacing, QcMonth,  # noqa: E402,F401
                            RefugeStation, SafetyFactor, StandupTime, load_design_inputs)
from .verify import STATUSES, Finding, VerificationResult  # noqa: E402,F401  (la función `verify` taparía el módulo: se usa desde rockmasspy.verify)
from . import q_slope_tables  # noqa: E402,F401
from . import probabilistic  # noqa: E402,F401
from .uncertainty import Summary, UncertaintyResult, classification_uncertainty  # noqa: E402,F401
from .blocks import (BLOCK_COLUMNS, DISTRIBUTION_COLUMNS, BermResult, BlockResult, BlockRow,  # noqa: E402,F401
                     DistributionRow, assess_blocks, block_attention, block_counts, load_blocks, load_distributions,
                     save_block_results)
from .limit_equilibrium import (ANALYSIS_COLUMNS, GEOMETRY_COLUMNS, LAYER_COLUMNS, LE_SHEETS,  # noqa: E402,F401
                                MATERIAL_COLUMNS, RECORD_COLUMNS, Accelerogram, AnalysisRow, GeometryRow, LayerRow,
                                LeAnalysisResult, LeInputs, MaterialRow, RecordRow, assess_le, le_attention, le_counts,
                                le_warning_counts, load_le_inputs, read_accelerogram, save_le_results)
from .normative import CONSEQUENCES, RANGE_POLICIES, SCALES  # noqa: E402,F401
from .criteria import (CRITERIA_COLUMNS, CRITERIA_RESULT_COLUMNS, CRITERIA_STATUSES, CriterionCheck,  # noqa: E402,F401
                       assess_criteria, criteria_attention, criteria_counts, load_criteria_table,
                       save_criteria_results)
