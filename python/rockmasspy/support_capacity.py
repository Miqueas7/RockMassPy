"""Capacidades del sostenimiento para la curva de reacción (SCC) y la tabla de presiones de Hoek.

La tabla es la Figura 8 de Hoek (2007), Practical Rock Engineering, capítulo «Tunnels in weak rock», p. 10 del
capítulo (p. 246 del PDF del libro completo), transcrita literal como dato citado. Hoek da la presión máxima de
soporte pimax (MPa) de cada elemento: perno o cable pimax = c/s², cercha pimax = c·D^-e/s y revestimiento
pimax = c·D^-e (D = diámetro del túnel en m, s = espaciamiento en m). La εsm solo se conoce, publicada en
RocSupport (RST pp. 33 y 38), para el perno de 34 mm (0.2 %) y el shotcrete de 50 mm a 28 días (0.1 %).
"""

import math
import re
from dataclasses import dataclass
from pathlib import Path

from . import _rockmasspy_core as _rm
from .csv_io import _CsvSource
from .excel_io import _num, _open, _text, _where
from .support import SupportCatalog

_P = "PRE Fig. 8, p. 246 del PDF (p. 10 del capítulo), curva "


@dataclass(frozen=True)
class HoekSupportItem:
    name: str
    kind: str  # "bolt" c/s² | "set" c·D^-e/s | "lining" c·D^-e
    coefficient: float
    exponent: float | None  # e de D^-e; None en los pernos
    eps_sm: float | None  # fracción (0.002 = 0.2 %); None donde Hoek no la publica en lo leído
    source_page: str


def _sets(name, rows, kind="set"):
    return [HoekSupportItem(f"{name} {label}", kind, c, e, None, f"{_P}{n}") for n, label, c, e in rows]


HOEK_SUPPORT_TABLE: tuple[HoekSupportItem, ...] = tuple(
    _sets("Wide flange rib", [(1, "flange 30 mm, depth 305 mm, 97 kg/m", 19.9, 1.23),
                              (2, "flange 20 mm, depth 203 mm, 67 kg/m", 13.2, 1.3),
                              (3, "flange 15 mm, depth 150 mm, 32 kg/m", 7.0, 1.4)])
    + _sets("I section rib", [(4, "flange 20 mm, depth 254 mm, 82 kg/m", 17.6, 1.29),
                              (5, "flange 15 mm, depth 203 mm, 52 kg/m", 11.1, 1.33)])
    + _sets("TH section rib", [(6, "flange 17 mm, depth 138 mm, 38 kg/m", 15.5, 1.24),
                               (7, "flange 12 mm, depth 108 mm, 21 kg/m", 8.8, 1.27)])
    + _sets("3 bar lattice girder", [(8, "flange 22 mm, depth 190 mm, 19 kg/m (14 mm, 130 mm, 18 kg/m)", 8.6, 1.03)])
    + _sets("4 bar lattice girder", [(9, "flange 22 mm, depth 280 mm, 29 kg/m (14 mm, 200 mm, 26 kg/m)", 18.3, 1.02)])
    + [HoekSupportItem(n, "bolt", c, None, eps, f"{_P}{k}") for k, n, c, eps in [
        (10, "34 mm rockbolt", 0.354, 0.002), (11, "25 mm rockbolt", 0.267, None),
        (12, "19 mm rockbolt", 0.184, None), (13, "17 mm rockbolt", 0.10, None),
        (14, "SS39 Split set", 0.05, None), (15, "EXX Swellex", 0.11, None),
        (16, "20mm rebar", 0.17, None), (17, "22mm fibreglass", 0.26, None),
        (18, "Plain cable", 0.15, None), (19, "Birdcage cable", 0.30, None)]]
    + _sets("Concrete or shotcrete lining", [
        (20, "1m 28 days 35 MPa", 57.8, 0.92), (21, "300 mm 28 days 35 MPa", 19.1, 0.92),
        (22, "150 mm 28 days 35 MPa", 10.6, 0.97), (23, "100 mm 28 days 35 MPa", 7.3, 0.98),
        (24, "50 mm 28 days 35 MPa", 3.8, 0.99), (25, "50 mm 3 days 11 MPa", 1.1, 0.97),
        (26, "50 mm 0.5 days 6 MPa", 0.6, 1.0)], kind="lining")
)
# la εsm del shotcrete de 50 mm a 28 días (RST p. 38) no sale de la Fig. 8: se agrega aquí
HOEK_SUPPORT_TABLE = tuple(
    HoekSupportItem(i.name, i.kind, i.coefficient, i.exponent, 0.001, i.source_page)
    if i.name == "Concrete or shotcrete lining 50 mm 28 days 35 MPa" else i
    for i in HOEK_SUPPORT_TABLE)
_BY_NAME = {i.name: i for i in HOEK_SUPPORT_TABLE}


def _need(name, value):
    if value is None:
        raise ValueError(f"{name} is required for this Hoek support item")
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and > 0")
    return value


def hoek_psm(name: str, *, diameter_m: float | None = None, spacing_m: float | None = None) -> float:
    """Presión máxima pimax (MPa) de un ítem de HOEK_SUPPORT_TABLE."""
    try:
        it = _BY_NAME[name]
    except KeyError:
        raise ValueError("unknown Hoek support item; see HOEK_SUPPORT_TABLE") from None
    if it.kind == "bolt":
        return it.coefficient / _need("spacing_m", spacing_m) ** 2
    p = it.coefficient * _need("diameter_m", diameter_m) ** -it.exponent
    return p / _need("spacing_m", spacing_m) if it.kind == "set" else p


@dataclass(frozen=True)
class SupportCapacity:
    code: str
    kind: str
    psm_mpa: float | None = None
    eps_sm: float | None = None
    stiffness_mpa: float | None = None
    hoek_item: str | None = None
    thickness_m: float | None = None
    e_mpa: float | None = None
    nu: float | None = None
    sigma_c_mpa: float | None = None
    sigma_t_mpa: float | None = None
    tensile_capacity_mn: float | None = None
    bond_strength_mn_m: float | None = None
    spacing_m: float | None = None

    def to_element(self, diameter_m: float):
        """SupportElement de la SCC; psm y εsm dados mandan, y lo que falta sale del ítem de Hoek."""
        item = None if self.hoek_item is None else _BY_NAME.get(self.hoek_item)
        psm = self.psm_mpa
        if psm is None:
            if self.hoek_item is None:
                raise ValueError("psm_mpa or hoek_item is required")
            psm = hoek_psm(self.hoek_item, diameter_m=diameter_m, spacing_m=self.spacing_m)
        eps = self.eps_sm if self.eps_sm is not None else (None if item is None else item.eps_sm)
        if eps is not None and self.stiffness_mpa is None:
            return _rm.support_from_eps(self.code, psm, eps)
        if self.stiffness_mpa is None:
            raise ValueError("eps_sm or stiffness_mpa is required")
        return _rm.SupportElement(self.code, psm, self.stiffness_mpa)


_ALIAS = {
    "codigo": "code", "code": "code", "tipo": "kind", "kind": "kind",
    "psm_mpa": "psm_mpa", "maximum support pressure": "psm_mpa",
    "eps_sm": "eps_sm", "maximum average strain": "eps_sm",
    "espesor_m": "thickness_m", "thickness": "thickness_m",
    "e_mpa": "e_mpa", "young's modulus": "e_mpa", "nu": "nu", "poisson's ratio": "nu",
    "sigma_c_mpa": "sigma_c_mpa", "compressive strength": "sigma_c_mpa",
    "sigma_t_mpa": "sigma_t_mpa", "tensile strength": "sigma_t_mpa",
    "capacidad_traccion_mn": "tensile_capacity_mn", "tensile capacity": "tensile_capacity_mn",
    "adherencia_mn_m": "bond_strength_mn_m", "bond strength": "bond_strength_mn_m",
    "espaciamiento_m": "spacing_m", "out-of-plane spacing": "spacing_m", "item_hoek": "hoek_item",
}
_TEXT = {"code", "kind", "hoek_item"}


def _canon(h) -> str:
    """Encabezado sin mayúsculas, espacios dobles ni unidades entre paréntesis."""
    return re.sub(r"\s+", " ", re.sub(r"\(.*?\)", "", _text(h) if h is not None else "")).strip().lower()


def load_support_capacity(path, *, sheet: str = "Capacidad_sostenimiento",
                          catalog: SupportCatalog | None = None) -> dict[str, SupportCapacity]:
    """Lee la hoja de capacidades (Excel o CSV); los errores ubican hoja y fila, nunca repiten el valor."""
    p = Path(path)
    src = _CsvSource({sheet: p}) if p.suffix.lower() == ".csv" else _open(p)
    try:
        if sheet not in src.sheetnames:
            raise ValueError(src.missing(sheet))
        dec = src.decimal_comma(sheet)
        rows = iter(src.rows(sheet))
        header = [_ALIAS.get(_canon(h)) for h in next(rows, ())]
        for need in ("code", "kind"):
            if need not in header:
                raise ValueError(f"sheet '{sheet}': missing column '{need}'")
        out: dict[str, SupportCapacity] = {}
        for n, raw in enumerate(rows, start=2):
            vals = {}
            for field, v in zip(header, raw):
                if field is None or v is None or (isinstance(v, str) and not v.strip()):
                    continue
                if field in _TEXT:
                    vals[field] = _text(v)
                    continue
                try:
                    vals[field] = _num(v, sheet, n, field, dec)
                except ValueError:  # _num cita la celda; aquí no se repite el valor
                    raise ValueError(f"{_where(sheet, n, field)}: expected a number") from None
            if not vals:
                continue
            for need in ("code", "kind"):
                if need not in vals:
                    raise ValueError(f"{_where(sheet, n, need)}: required value is empty")
            code = vals["code"]
            if catalog is not None and code not in catalog:
                raise ValueError(f"sheet '{sheet}', row {n}: support code is not in the catalog")
            if code in out:
                raise ValueError(f"sheet '{sheet}', row {n}: duplicate support code")
            if vals.get("hoek_item") is not None and vals["hoek_item"] not in _BY_NAME:
                raise ValueError(f"{_where(sheet, n, 'item_hoek')}: unknown Hoek support item")
            out[code] = SupportCapacity(**vals)
        return out
    finally:
        if hasattr(src, "wb"):
            src.wb.close()
