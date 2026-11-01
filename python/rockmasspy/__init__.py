"""RockMassPy: rock mass classifications, Hoek-Brown strength and mining geomechanics."""

from ._rockmasspy_core import *  # noqa: F401,F403

__version__ = "0.1.0"
from .q_tables import Q_TABLES, SRF_CATEGORIES, q_lookup  # noqa: E402,F401
from .issues import TableIssue  # noqa: E402,F401
from .intact_rock import (  # noqa: E402,F401
    MI_ALIASES_ES, MI_SOURCE, MI_TABLE, MR_SOURCE, MR_TABLE, MiEntry, MrEntry, mi_lookup, mr_lookup,
)
from .support import Bolt, Shotcrete, SupportCatalog, SupportType  # noqa: E402,F401
