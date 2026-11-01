"""Tablas de mi (Hoek, tabla 3) y de la razón de módulo MR (tabla 8) de la roca intacta.

Datos puros, sin E/S. Claves en inglés, singular y minúsculas; MI_ALIASES_ES mapea el nombre en español.
Fuentes, ambas [V2] (verificación secundaria, transcritas de la imagen del capítulo):
  mi: Hoek, Practical Rock Engineering, cap. 11, tabla 3 (según Marinos y Hoek 2000).
  MR: Hoek, Practical Rock Engineering, cap. 11, tabla 8 (Hoek y Diederichs 2006, según Deere 1968).
Un valor entre paréntesis en la fuente es estimado (estimate=True). Un MR escrito como valor único
tiene lo == hi; "1000+" (tiza) se guarda como 1000 (límite inferior, sin tope en la fuente).
Los rótulos de clase, grupo y textura están escritos con palabras propias.
"""

import difflib
import unicodedata
from dataclasses import dataclass

MI_SOURCE = "Hoek, Practical Rock Engineering, ch. 11, Table 3 (after Marinos & Hoek 2000)"
MR_SOURCE = "Hoek, Practical Rock Engineering, ch. 11, Table 8 (Hoek & Diederichs 2006, after Deere 1968)"


@dataclass(frozen=True)
class MiEntry:
    mi: float
    plus_minus: float | None
    estimate: bool
    rock_class: str
    group: str
    texture: str


@dataclass(frozen=True)
class MrEntry:
    lo: float
    hi: float
    estimate: bool


# nombre: (mi, ±, estimado, clase, grupo, textura)
_MI = {
    "conglomerate": (21, 3, True, "sedimentary clastic", "", "coarse"),
    "breccia": (19, 5, True, "sedimentary clastic", "", "coarse"),
    "sandstone": (17, 4, False, "sedimentary clastic", "", "medium"),
    "siltstone": (7, 2, False, "sedimentary clastic", "", "fine"),
    "greywacke": (18, 3, True, "sedimentary clastic", "", "fine"),
    "claystone": (4, 2, False, "sedimentary clastic", "", "very fine"),
    "shale": (6, 2, True, "sedimentary clastic", "", "very fine"),
    "marl": (7, 2, True, "sedimentary clastic", "", "very fine"),
    "crystalline limestone": (12, 3, True, "sedimentary non-clastic", "carbonate", "coarse"),
    "sparitic limestone": (10, 2, True, "sedimentary non-clastic", "carbonate", "medium"),
    "micritic limestone": (9, 2, True, "sedimentary non-clastic", "carbonate", "fine"),
    "dolomite": (9, 3, True, "sedimentary non-clastic", "carbonate", "very fine"),
    "gypsum": (8, 2, False, "sedimentary non-clastic", "evaporite", "medium"),
    "anhydrite": (12, 2, False, "sedimentary non-clastic", "evaporite", "fine"),
    "chalk": (7, 2, False, "sedimentary non-clastic", "organic", "very fine"),
    "marble": (9, 3, False, "metamorphic non-foliated", "", "coarse"),
    "hornfels": (19, 4, True, "metamorphic non-foliated", "", "medium"),
    "metasandstone": (19, 3, True, "metamorphic non-foliated", "", "medium"),
    "quartzite": (20, 3, False, "metamorphic non-foliated", "", "fine"),
    "migmatite": (29, 3, True, "metamorphic slightly foliated", "", "coarse"),
    "amphibolite": (26, 6, False, "metamorphic slightly foliated", "", "medium"),
    "gneiss": (28, 5, False, "metamorphic foliated", "", "coarse"),
    "schist": (12, 3, False, "metamorphic foliated", "", "medium"),
    "phyllite": (7, 3, True, "metamorphic foliated", "", "fine"),
    "slate": (7, 4, False, "metamorphic foliated", "", "very fine"),
    "granite": (32, 3, False, "igneous plutonic", "light", "coarse"),
    "diorite": (25, 5, False, "igneous plutonic", "light", "coarse"),
    "granodiorite": (29, 3, True, "igneous plutonic", "light", "coarse"),
    "gabbro": (27, 3, False, "igneous plutonic", "dark", "coarse"),
    "dolerite": (16, 5, True, "igneous plutonic", "dark", "medium"),
    "norite": (20, 5, False, "igneous plutonic", "dark", "coarse"),
    "porphyry": (20, 5, True, "igneous hypabyssal", "", "coarse"),
    "diabase": (15, 5, True, "igneous hypabyssal", "", "fine"),
    "peridotite": (25, 5, True, "igneous hypabyssal", "", "very fine"),
    "rhyolite": (25, 5, True, "igneous volcanic", "lava", "medium"),
    "dacite": (25, 3, True, "igneous volcanic", "lava", "fine"),
    "andesite": (25, 5, False, "igneous volcanic", "lava", "medium"),
    "basalt": (25, 5, True, "igneous volcanic", "lava", "fine"),
    "obsidian": (19, 3, True, "igneous volcanic", "lava", "very fine"),
    "agglomerate": (19, 3, True, "igneous volcanic", "pyroclastic", "coarse"),
    "volcanic breccia": (19, 3, True, "igneous volcanic", "pyroclastic", "medium"),
    "tuff": (13, 5, True, "igneous volcanic", "pyroclastic", "fine"),
}

# nombre: (lo, hi, estimado)
_MR = {
    "conglomerate": (300, 400, False), "breccia": (230, 350, False), "sandstone": (200, 350, False),
    "siltstone": (350, 400, False), "greywacke": (350, 350, False), "claystone": (200, 300, False),
    "shale": (150, 250, False), "marl": (150, 200, False),
    "crystalline limestone": (400, 600, False), "sparitic limestone": (600, 800, False),
    "micritic limestone": (800, 1000, False), "dolomite": (350, 500, False),
    "gypsum": (350, 350, True), "anhydrite": (350, 350, True), "chalk": (1000, 1000, False),
    "marble": (700, 1000, False), "hornfels": (400, 700, False), "metasandstone": (200, 300, False),
    "quartzite": (300, 450, False), "migmatite": (350, 400, False), "amphibolite": (400, 500, False),
    "gneiss": (300, 750, False), "schist": (250, 1100, False), "phyllite": (300, 800, False),
    "slate": (400, 600, False), "granite": (300, 550, False), "diorite": (300, 350, False),
    "granodiorite": (400, 450, False), "gabbro": (400, 500, False), "dolerite": (300, 400, False),
    "norite": (350, 400, False), "porphyry": (400, 400, True), "diabase": (300, 350, False),
    "peridotite": (250, 300, False), "rhyolite": (300, 500, False), "andesite": (300, 500, False),
    "dacite": (350, 450, False), "basalt": (250, 450, False), "agglomerate": (400, 600, False),
    "volcanic breccia": (500, 500, True), "tuff": (200, 400, False),
}

MI_TABLE = {k: MiEntry(float(v[0]), float(v[1]), *v[2:]) for k, v in _MI.items()}
MR_TABLE = {k: MrEntry(float(v[0]), float(v[1]), v[2]) for k, v in _MR.items()}

_ES = {
    "conglomerate": "conglomerado", "breccia": "brecha", "sandstone": "arenisca", "siltstone": "limolita",
    "greywacke": "grauvaca", "claystone": "arcillolita", "shale": "lutita", "marl": "marga",
    "crystalline limestone": "caliza cristalina", "sparitic limestone": "caliza esparítica",
    "micritic limestone": "caliza micrítica", "dolomite": "dolomita", "gypsum": "yeso",
    "anhydrite": "anhidrita", "chalk": "tiza", "marble": "mármol", "hornfels": "corneana",
    "metasandstone": "metarenisca", "quartzite": "cuarcita", "migmatite": "migmatita",
    "amphibolite": "anfibolita", "gneiss": "gneis", "schist": "esquisto", "phyllite": "filita",
    "slate": "pizarra", "granite": "granito", "diorite": "diorita", "granodiorite": "granodiorita",
    "gabbro": "gabro", "dolerite": "dolerita", "norite": "norita", "porphyry": "pórfido",
    "diabase": "diabasa", "peridotite": "peridotita", "rhyolite": "riolita", "dacite": "dacita",
    "andesite": "andesita", "basalt": "basalto", "obsidian": "obsidiana", "agglomerate": "aglomerado",
    "volcanic breccia": "brecha volcánica", "tuff": "toba",
}


def _strip(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


MI_ALIASES_ES = {}
for _en, _es in _ES.items():
    MI_ALIASES_ES[_es] = _en
    MI_ALIASES_ES[_strip(_es)] = _en


def _lookup(table: dict, rock: str):
    key = rock.strip().lower()
    key = MI_ALIASES_ES.get(key, key)
    if key in table:
        return table[key]
    near = difflib.get_close_matches(key, list(table) + list(MI_ALIASES_ES), n=5)
    raise KeyError(f"unknown rock {rock!r}; similar: {near}")


def mi_lookup(rock: str) -> MiEntry:
    return _lookup(MI_TABLE, rock)


def mr_lookup(rock: str) -> MrEntry:
    return _lookup(MR_TABLE, rock)
