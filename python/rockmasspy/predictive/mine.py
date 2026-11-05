"""Mina sintética realista, calibrada con la literatura (Fase 5, tareas 2 a 4; plan M1–M7).

Banco de pruebas de los niveles 0 a 3: nunca entrena un modelo que se entregue, no da priors ni coeficientes por
defecto y nunca reemplaza el histórico de una mina. Cada número sale de
`docs/investigacion/CALIBRACION_MINA_SINTETICA.md` (la clave A1…D9 va en el comentario); lo que no tiene fuente
dice «supuesto de diseño». Solo códigos (Z1, L001, T0001, G01) y litologías genéricas: ningún nombre real.

Mecanismo, de la geología al registro (a diferencia de `synthetic_history`, nada sale de una recta):
- Macizo verdadero (M2): calidad latente u por tramo = calidad media de la litología de la zona + efecto de zona
  + efecto de labor + AR(1) en la progresiva (ρ = exp(−Δ/alcance)) + pepita − caída en las zonas de falla
  (Poisson por metro). De u salen los componentes verdaderos (RQD, Jn, Jr, Ja, Jw, SRF, espaciamiento, condición
  de juntas, UCS y agua) con pesos distintos (A2.2: RQD y SRF siguen a u; Jn casi no) y valores modales (A2.1).
  Q, RMR89 y GSI se calculan con el núcleo, como lo haría el geólogo: la recta RMR–ln Q **emerge** y la verdad la
  informa.
- Mapeo (M3): cada labor la mapea un geólogo G01… con sesgo propio y ruido por mapeo en cada componente (B4). Lo
  registrado (componentes, Q con 4 cifras, RMR89 básico y GSI) se recalcula desde los componentes registrados,
  así que `audit_history` no levanta hallazgos. `HistoryTramo` no tiene columna de evaluador: el geólogo va solo en
  la verdad.
- Práctica (M4): la tabla de la mina por rangos de GSI registrado y tipo de labor (C6.1), con pendiente y piso
  opcionales (C6.3), desvíos de un tipo (más liviano o más pesado), un cambio de tabla en una fecha (C6.6) y horas
  sin sostener (C6.5). Con `practice_mode="q_chart"` la mina instala lo que pide la carta Q con el Q registrado.
- Falla (M5–M6): tasa constante por día, log λ = log λ0(tipo de labor) + κ_def·max(0, d) − κ_sob·max(0, −d)
  + efecto de zona + ln(multiplicador)·[horas sin sostener del tipo > autosoporte], por la fragilidad gamma de la
  labor (media 1, varianza θ). d = rango que pide la carta Q con Q_verdadero·exp(−δ) − rango del tipo. Las horas de
  los cinco tipos salen del mismo número aleatorio (cada tipo con su mediana), así que la P contrafactual usa las
  horas que habría tenido ese tipo; el multiplicador es daño persistente (toda la vida del tramo). Con fragilidad
  gamma la P de falla en H de una labor nueva de la misma zona es cerrada: 1 − (1 + θλH)^(−1/θ).
- Defectos (M7, `defects=True`): se inyectan con un generador aparte, así que el resto del History es idéntico al
  de `defects=False` con la misma semilla.
"""

from __future__ import annotations

import dataclasses
import datetime
import math
from dataclasses import dataclass
from functools import cached_property

import numpy as np
from scipy.special import ndtr

from .. import _rockmasspy_core as rm
from ..history import History, HistoryTramo, Inspection
from ..q_support import read_q_chart
from .synthetic import _CATEGORY_TO_TYPE, _LABOR_TYPES, LITHOLOGIES, SUPPORT_TYPES, _positive_int

_START = datetime.date(2019, 1, 1)
_TYPE_CODES = tuple(s.codigo_tipo for s in SUPPORT_TYPES)  # I…V, del más liviano al más pesado
_RANK = {c: k + 1 for k, c in enumerate(_TYPE_CODES)}
_LABOR_TYPE_NAMES = tuple(_LABOR_TYPES)  # Galería, Rampa, Tajeo
_MIN_TRAMOS_PER_LABOR = 4
_MAX_ADVANCE_DAYS = 6  # días entre mapeos de tramos seguidos: 2 a 6
_END_MARGIN_DAYS = 30  # el último tramo de una labor se mapea al menos 30 días antes del fin del histórico

# Componentes de Q: (valores del peor al mejor macizo, probabilidades). Pocos valores por parámetro, como en A2.1
# (el geólogo usa 2–3 por dominio); las proporciones son un supuesto de diseño de una mina de vetas, no las de A2.1
# (un túnel en roca mala: Jn = 12 en 92 %, SRF ≥ 2.5 en 95 %).
_JN = ((15.0, 12.0, 9.0, 6.0, 4.0), (0.05, 0.25, 0.45, 0.20, 0.05))
_JR = ((1.0, 1.5, 2.0, 3.0), (0.30, 0.55, 0.12, 0.03))  # A2.1: 1.5 en 57 %, 1 en 30 %
_JA = ((6.0, 4.0, 2.0, 1.0), (0.10, 0.65, 0.17, 0.08))  # A2.1: 4 en 70 %
_SRF = ((10.0, 5.0, 2.5, 1.0), (0.05, 0.20, 0.35, 0.40))
# Agua: Jw y la condición del RMR89 salen del mismo cuantil, así que siempre cuadran
# (A2.1: Jw 1 en 68 %, 0.66 en 28 %)
_JW = ((0.5, 0.66, 1.0), (0.04, 0.28, 0.68))
_WATER = (("Goteo", "Mojado", "Húmedo", "Seco"), (0.04, 0.28, 0.30, 0.38))
# Pesos de u en el cuantil de cada componente (A2.2: RQD–SRF −0.71, Jn casi independiente; A2.4: ρ ≈ 0.5 entre
# RQD, espaciamiento y condición; agua y resistencia ρ ≈ 0.2). Jr y Ja siguen a la condición de juntas.
_W_RQD, _W_SPACING, _W_JCOND, _W_SRF, _W_JN, _W_WATER, _W_UCS = 0.85, 0.70, 0.60, 0.80, 0.15, 0.35, 0.20
_W_JR_JA = 0.70  # peso de la condición de juntas en Jr y Ja
# Autosoporte de Bieniawski 1989 (D8.5): RMR89 → log10 horas (I 20 años, II 1 año, III 1 semana, IV 10 h, V 30 min)
_STANDUP_RMR = (10.0, 30.0, 50.0, 70.0, 90.0)
_STANDUP_LOG10_H = (math.log10(0.5), 1.0, math.log10(168.0), math.log10(8760.0), math.log10(175200.0))
# Sobreexcavación en galería (D9.1, Khimti-2): ln(%) = 1.67 − 0.41·ln Q, DE residual 0.64
_OVERBREAK = (1.67, -0.41, 0.64)
_FAILURE_TYPES = (("Desprendimiento", 0.70), ("Caída de bloque", 0.20), ("Deformación", 0.10))  # supuesto de diseño
_DEFECT_KINDS = ("empty_cell", "q_mismatch", "overlapping_chainage", "inspection_before_installation",
                 "unknown_support")
_EMPTY_COLUMNS = ("rqd_pct", "jn", "jr", "ja", "jw", "srf", "ucs_mpa", "espaciamiento_m", "puntaje_condicion_juntas",
                  "agua", "q_valor", "rmr_valor", "gsi_valor")
_UNKNOWN_TYPE = "VI"
# Nombres de roca genéricos que acepta `lithologies`: así nadie mete sin querer el nombre de una veta o de una mina
GENERIC_LITHOLOGIES = (*LITHOLOGIES, "granito", "granodiorita", "tonalita", "monzonita", "dacita", "riolita",
                       "basalto", "toba", "arenisca", "lutita", "lodolita", "conglomerado", "dolomita", "mármol",
                       "skarn", "cuarcita", "pizarra", "filita", "esquisto", "gneis")
_Q_COLUMNS = ("q_valor", "rqd_pct", "jn", "jr", "ja", "jw", "srf")


@dataclass(frozen=True)
class MineScenario:
    """Parámetros de una mina sintética. Cada campo con su clave de la calibración o «supuesto de diseño»."""

    name: str = "base"
    # tamaño: ≈ 600 tramos, lo que pide el nivel 3 con 5–10 % de fallas (D7.5)
    n_zones: int = 5
    labors_per_zone: int = 6
    tramos_per_labor: int = 20  # media (Poisson, al menos 4)
    years: int = 5
    # A1: (litología genérica, UCS mediana en MPa, calidad media en unidades de u); supuesto de diseño
    # nombres solo de GENERIC_LITHOLOGIES (nunca el de una veta, un cuerpo o una mina)
    lithologies: tuple[tuple[str, float, float], ...] = (
        ("andesita", 80.0, 0.2), ("caliza", 60.0, 0.0), ("diorita", 100.0, 0.4), ("brecha", 35.0, -0.5))
    quality_shift: float = 0.0  # corre toda la mina (sitio peor o mejor)
    # A3.5: varianza de u = zona + labor + AR(1) + pepita (≈ 1); pepita ≈ 20 % de la varianza del tramo
    sd_zone_quality: float = 0.35
    sd_labor_quality: float = 0.35
    sd_path_quality: float = 0.75
    correlation_length_m: float = 60.0  # A3.5: 30–100 m
    sd_nugget_quality: float = 0.40
    # A3.6: zonas de falla (extremo bajo para una mina de vetas)
    fault_rate_per_km: float = 1.5
    fault_width_median_m: float = 15.0
    fault_width_sd_log: float = 1.0  # p25–p75 ≈ 7–33 m
    fault_quality_drop: float = 1.6  # ≈ 15–25 puntos de RMR
    # A2: componentes del RMR89 desde u (calibrado para RMR ~ N(45, 11), A1.6)
    rqd_mean: float = 48.0
    rqd_sd: float = 25.0
    spacing_median_m: float = 0.18
    spacing_sd_log: float = 0.7
    jcond_mean: float = 11.0
    jcond_sd: float = 5.0
    jcond_shift: float = 0.0  # corre el RMR (y el GSI) sin tocar el Q: correlación del sitio corrida
    sd_log_ucs: float = 0.30
    # B4: mapeo
    n_geologists: int = 4
    sd_geologist_bias: float = 0.18  # B4.6: ≈ 2–4 puntos de RMR; supuesto de diseño
    sd_mapping_z: float = 0.20  # cuantil de Jn, Jr, Ja, SRF y agua; supuesto de diseño (B4.4: log10 Q 0.2–0.3)
    sd_mapping_rqd: float = 6.0  # B4.5 da 10–15, pero con 10 el GSI cuantificado pasa la DE 3–4.3 de B4.1
    sd_mapping_jcond: float = 1.5  # supuesto de diseño (B4.3: RMR 4–6 entre geólogos)
    sd_mapping_log_spacing: float = 0.25  # supuesto de diseño
    sd_mapping_log_ucs: float = 0.25  # supuesto de diseño
    sd_gsi_visual: float = 0.0  # B4.1: 8–10 si el GSI se lee en la carta; 0 = GSI cuantificado (Hoek 2013)
    # C6: práctica
    practice_mode: str = "gsi_table"  # o "q_chart": la mina instala lo que pide la carta con el Q registrado
    practice_gsi_cuts: tuple[float, ...] = (28.0, 38.0, 48.0, 58.0)  # GSI: V | IV | III | II | I; supuesto (C6.1)
    practice_temporary_gsi_bonus: float = 5.0  # las labores temporales leen la tabla con GSI + 5; supuesto
    practice_slope: float = 1.0  # C6.3: 0.5–0.7 en la práctica tipo mina (Peck y Lee)
    practice_min_rank: int = 1  # C6.3: piso (2 = nunca menos que el tipo II)
    practice_type_shift: int = 0  # +1: todo un tipo más pesado (práctica conservadora)
    p_lighter: float = 0.08  # C6.4: desvíos por falta de material; supuesto de diseño
    p_heavier: float = 0.08  # C6.4: desvíos por precaución; supuesto de diseño
    table_change_date: str | None = None  # C6.6: desde esa fecha la tabla se lee con GSI + el bono
    table_change_gsi_bonus: float = 6.0
    unsupported_hours_heavy: float = 12.0  # C6.5: mediana de 1 turno en roca IV–V (tipos IV y V)
    unsupported_hours_light: float = 72.0  # C6.5: 1–7 días en roca II–III
    sd_log_unsupported: float = 0.6  # supuesto de diseño
    # D: falla (tasa por día)
    site_shift_delta: float = 0.5  # δ: el sitio lee la carta con Q·exp(−δ); 0 = igual a NGI; supuesto de diseño
    log_lambda0: tuple[float, float, float] = (-9.8, -9.8, -8.4)  # Galería, Rampa, Tajeo; calibrado con D7.5
    kappa_deficit: float = 0.8  # por tipo que falta; D7.5 (× ≈ 10 con déficit) y D8.4
    kappa_deficit_rock_v: float | None = None  # D8.4: en roca V (RMR89 verdadero < 21); None = kappa_deficit
    kappa_surplus: float = 0.3  # por tipo que sobra: rendimiento decreciente; supuesto de diseño
    sd_zone_failure: float = 0.4
    frailty_variance: float = 0.3  # θ de la fragilidad gamma por labor (≈ DE 0.5 en log)
    # C6.5: × 3–5 si las horas sin sostener pasan el autosoporte (D8.5). Decisión de diseño: daño persistente, el
    # multiplicador dura toda la vida del tramo (la exposición se cuenta desde la instalación)
    unsupported_multiplier: float = 4.0
    # D9: inspecciones y vida útil
    inspection_active_days: int = 30  # D9.5: mensual en labores activas
    active_period_days: int = 180  # supuesto de diseño
    inspection_inactive_days: int = 120  # D9.5: trimestral a semestral en inactivas
    life_permanent_years: tuple[float, float] = (3.0, 15.0)  # D9.4
    life_temporary_days: tuple[int, int] = (60, 365)  # D9.4: tajeo 2–12 meses
    failure_volume_exponent: float = 0.75  # D9.3: Pareto acumulado 0.5–1.0
    failure_volume_min_m3: float = 0.01
    # M7: tasas de defectos por tramo (solo con defects=True); supuesto de diseño
    defect_empty_rate: float = 0.03
    defect_q_mismatch_rate: float = 0.02
    defect_overlap_rate: float = 0.02
    defect_inspection_before_rate: float = 0.02
    defect_unknown_support_rate: float = 0.01

    def __post_init__(self):
        for name in ("lithologies", "practice_gsi_cuts", "log_lambda0", "life_permanent_years",
                     "life_temporary_days"):  # una lista también entra
            object.__setattr__(self, name, tuple(getattr(self, name)))
        object.__setattr__(self, "lithologies", tuple(tuple(x) for x in self.lithologies))
        for name in ("n_zones", "labors_per_zone", "tramos_per_labor", "years", "n_geologists",
                     "inspection_active_days", "active_period_days", "inspection_inactive_days"):
            _positive_int(name, getattr(self, name))
        for name in ("practice_type_shift", "practice_min_rank"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, (int, np.integer)):
                raise ValueError(f"{name} must be an integer")
        m = self.tramos_per_labor  # una labor casi nunca pasa media + 4 DE de Poisson; avance máximo 6 días
        if _MAX_ADVANCE_DAYS * (m + 4 * math.sqrt(m) + 4) + 2 * _END_MARGIN_DAYS > 365.25 * self.years:
            raise ValueError("the expected advance of a labor does not fit in the years of the history; "
                             "raise years or lower tramos_per_labor")
        if any(getattr(self, n) < 0 for n in self.__dataclass_fields__ if n.startswith("sd_")):
            raise ValueError("standard deviations must be >= 0")
        if not self.lithologies or any(len(x) != 3 or not _real(x[1]) or not x[1] > 0 or not _real(x[2])
                                       for x in self.lithologies):
            raise ValueError("lithologies must be (name, ucs_mpa > 0, mean quality) triples of numbers")
        if any(x[0] not in GENERIC_LITHOLOGIES for x in self.lithologies):
            raise ValueError(f"lithology names must be generic rock names from GENERIC_LITHOLOGIES: "
                             f"{', '.join(GENERIC_LITHOLOGIES)}")
        if self.kappa_deficit_rock_v is not None and self.kappa_deficit_rock_v < 0:
            raise ValueError("kappa_deficit_rock_v must be >= 0")
        cuts = self.practice_gsi_cuts
        if len(cuts) != len(SUPPORT_TYPES) - 1 or any(b <= a for a, b in zip(cuts, cuts[1:])):
            raise ValueError(f"practice_gsi_cuts must be {len(SUPPORT_TYPES) - 1} strictly increasing values")
        if self.practice_mode not in ("gsi_table", "q_chart"):
            raise ValueError("practice_mode must be 'gsi_table' or 'q_chart'")
        if not 1 <= self.practice_min_rank <= len(SUPPORT_TYPES):
            raise ValueError("practice_min_rank must be between 1 and 5")
        if len(self.log_lambda0) != len(_LABOR_TYPES):
            raise ValueError(f"log_lambda0 needs one value per labor type {_LABOR_TYPE_NAMES}")
        rates = ("p_lighter", "p_heavier", *(n for n in self.__dataclass_fields__ if n.startswith("defect_")))
        if any(not 0.0 <= getattr(self, n) <= 1.0 for n in rates) or self.p_lighter + self.p_heavier > 1.0:
            raise ValueError("probabilities and defect rates must be between 0 and 1")
        positive = ("correlation_length_m", "fault_width_median_m", "spacing_median_m", "unsupported_hours_heavy",
                    "unsupported_hours_light", "unsupported_multiplier", "failure_volume_exponent",
                    "failure_volume_min_m3", "practice_slope")
        if any(not getattr(self, n) > 0 for n in positive):
            raise ValueError(f"{', '.join(positive)} must be > 0")
        if self.fault_rate_per_km < 0 or self.frailty_variance < 0 or self.kappa_deficit < 0 \
                or self.kappa_surplus < 0:
            raise ValueError("fault_rate_per_km, frailty_variance and the kappas must be >= 0")
        (lo, hi), (dlo, dhi) = self.life_permanent_years, self.life_temporary_days
        if not (0 < lo <= hi and 1 <= dlo <= dhi):
            raise ValueError("life ranges must be (low, high) with 0 < low <= high")
        if self.table_change_date is not None:
            datetime.date.fromisoformat(self.table_change_date)  # ValueError si no es ISO


@dataclass(frozen=True)
class TrueTramo:
    """Verdad de un tramo. `rates`: tasa verdadera por día de cada tipo I…V con fragilidad 1 (labor media)."""

    id_tramo: str
    geologist: str
    q: float
    rmr: float
    gsi: float
    in_fault_zone: bool
    table_type: str  # lo que pide la tabla de la mina con el GSI registrado (sost_recomendado)
    installed_type: str  # el instalado de verdad (aunque un defecto cambie la celda)
    practice_deviation: int  # instalado − tabla, en tipos (−1 más liviano, +1 más pesado)
    required_type: str  # lo que pide la carta Q con Q·exp(−δ) y De
    unsupported_hours: float  # las del tipo instalado (tiempo_sin_sostener_h)
    frailty: float  # fragilidad de la labor (media 1)
    censor_days: int  # censura planeada: fin de la vida útil o del histórico, desde la instalación
    rates: tuple[float, ...]
    unsupported_hours_by_type: tuple[float, ...]  # horas sin sostener con cada tipo I…V (mismo número aleatorio)
    standup_hours: float  # autosoporte de Bieniawski 1989 con el RMR89 verdadero (D8.5)
    zone_failure_effect: float  # efecto de zona en log λ (ya sorteado)
    failure_day: int  # día real de la falla desde la instalación (puede pasar la censura)
    failed: bool  # falló dentro del histórico: failure_day <= censor_days


@dataclass(frozen=True)
class MineTruth:
    scenario: MineScenario
    seed: int
    tramos: tuple[TrueTramo, ...]
    # recta verdadera RMR = a·ln Q + b de toda la mina (OLS sobre los valores verdaderos) y su DE residual
    rmr_lnq_slope: float
    rmr_lnq_intercept: float
    rmr_lnq_residual_sd: float
    defects: tuple[tuple[str, str, str], ...]  # (tipo, id_tramo, detalle)

    @cached_property
    def _by_id(self):
        return {t.id_tramo: t for t in self.tramos}

    def rate(self, tramo_id: str, type_code: str, *, conditional: bool = False) -> float:
        """Tasa verdadera por día con el tipo `type_code` (con las horas sin sostener que tendría ese tipo);
        con `conditional=True`, por la fragilidad de la labor del tramo."""
        t = self._by_id[tramo_id]
        return t.rates[_RANK[type_code] - 1] * (t.frailty if conditional else 1.0)

    def p_fail(self, tramo_id: str, type_code: str, horizon_days: float, *, conditional: bool = False) -> float:
        """P verdadera de falla dentro de `horizon_days` desde la instalación. Por defecto, marginal sobre la
        fragilidad de una labor nueva EN LA MISMA ZONA (gamma, cerrada; condicional al efecto de zona ya sorteado);
        con `conditional=True`, la de la labor del tramo."""
        lam_h = self.rate(tramo_id, type_code, conditional=conditional) * horizon_days
        theta = self.scenario.frailty_variance
        if conditional or theta == 0:
            return -math.expm1(-lam_h)
        return 1.0 - (1.0 + theta * lam_h) ** (-1.0 / theta)


def _real(x):
    return not isinstance(x, bool) and isinstance(x, (int, float, np.integer, np.floating)) and math.isfinite(x)


def _pick(table, z):
    """Valor de la tabla (valores, probabilidades) según el cuantil normal de z (z alto = mejor macizo)."""
    values, probs = table
    return values[min(len(values) - 1, int(np.searchsorted(np.cumsum(probs), ndtr(z), side="right")))]


def _rmr89(ucs, rqd, spacing, jcond, water):
    i = rm.Rmr89Input()
    i.ucs_mpa, i.rqd_pct, i.spacing_m = ucs, rqd, spacing
    i.joint_condition_rating, i.water = jcond, _CORE_WATER[water]
    return rm.rmr89(i).basic


_CORE_WATER = {"Seco": rm.Water.Dry, "Húmedo": rm.Water.Damp, "Mojado": rm.Water.Wet, "Goteo": rm.Water.Dripping}


def _q(rqd, jn, jr, ja, jw, srf):
    return rm.q_value(rm.QInput(rqd, jn, jr, ja, jw, srf), rm.QEdition.NGI2025).q


def _components(sc, z, ucs_median, shift_z=0.0, rng=None, mapped=False):
    """Componentes desde los cuantiles z (dict). Con `mapped`, el geólogo suma su sesgo `shift_z` y su ruido."""
    def zz(k, sd=0.0):
        return z[k] + shift_z + (rng.normal(0, sd) if mapped and sd > 0 else 0.0)

    sdz = sc.sd_mapping_z
    rqd = sc.rqd_mean + sc.rqd_sd * zz("rqd") + (rng.normal(0, sc.sd_mapping_rqd) if mapped else 0.0)
    spacing = sc.spacing_median_m * math.exp(sc.spacing_sd_log * zz("spacing")
                                             + (rng.normal(0, sc.sd_mapping_log_spacing) if mapped else 0.0))
    jcond = sc.jcond_mean + sc.jcond_shift + sc.jcond_sd * zz("jcond") \
        + (rng.normal(0, sc.sd_mapping_jcond) if mapped else 0.0)
    ucs = ucs_median * math.exp(sc.sd_log_ucs * z["ucs"]
                                + (rng.normal(0, sc.sd_mapping_log_ucs) if mapped else 0.0))
    zw = zz("water", sdz)
    out = dict(rqd=float(np.clip(round(rqd), 0, 100)), jn=_pick(_JN, zz("jn", sdz)), jr=_pick(_JR, zz("jr", sdz)),
               ja=_pick(_JA, zz("ja", sdz)), jw=_pick(_JW, zw), srf=_pick(_SRF, zz("srf", sdz)),
               water=_pick(_WATER, zw),
               spacing=float(np.clip(round(spacing, 2), 0.02, 3.0)), jcond=float(np.clip(round(jcond), 0, 30)),
               ucs=float(max(1.0, round(ucs))))
    if not mapped:  # la verdad sin redondear lo continuo
        out.update(rqd=float(np.clip(rqd, 0, 100)), spacing=float(np.clip(spacing, 0.02, 3.0)),
                   jcond=float(np.clip(jcond, 0, 30)), ucs=float(max(1.0, ucs)))
    return out


def _table_rank(sc, gsi, temporary, date):
    """Tipo (1…5) que pide la tabla de la mina con el GSI registrado (C6.1, C6.3, C6.6)."""
    cuts = sc.practice_gsi_cuts
    center = 0.5 * (cuts[0] + cuts[-1])
    g = center + sc.practice_slope * (gsi - center) + (sc.practice_temporary_gsi_bonus if temporary else 0.0)
    if sc.table_change_date is not None and date.isoformat() >= sc.table_change_date:
        g += sc.table_change_gsi_bonus
    rank = len(SUPPORT_TYPES) - sum(g >= c for c in cuts) + sc.practice_type_shift
    return int(np.clip(max(rank, sc.practice_min_rank), 1, len(SUPPORT_TYPES)))


def _rates(sc, ti, zone_f, rmr_true, required, hours_by_type, standup_h):
    """Tasa verdadera por día de cada tipo I…V con fragilidad 1 (M5), cada uno con sus horas sin sostener."""
    kd = sc.kappa_deficit if sc.kappa_deficit_rock_v is None or rmr_true >= 21 else sc.kappa_deficit_rock_v
    return tuple(math.exp(sc.log_lambda0[ti] + zone_f
                          + (math.log(sc.unsupported_multiplier) if h > standup_h else 0.0)
                          + kd * max(0, required - rk) - sc.kappa_surplus * max(0, rk - required))
                 for rk, h in enumerate(hours_by_type, start=1))


def _chart_rank(q, de):
    return _RANK[_CATEGORY_TO_TYPE.get(read_q_chart(q, de).category, "V")]


def _resolve(scenario):
    if scenario is None:
        return SCENARIOS["base"]
    if isinstance(scenario, str):
        if scenario not in SCENARIOS:
            raise ValueError(f"unknown scenario {scenario!r}; known: {', '.join(SCENARIOS)}")
        return SCENARIOS[scenario]
    if not isinstance(scenario, MineScenario):
        raise TypeError("scenario must be a MineScenario, a name from SCENARIOS or None")
    return scenario


def synthetic_mine(scenario: MineScenario | str | None = None, *, seed: int = 0,
                   defects: bool = False) -> tuple[History, MineTruth]:
    """Mina sintética calibrada con la literatura. Misma semilla → mismo History y misma verdad.

    `scenario`: un `MineScenario`, el nombre de uno de `SCENARIOS` o None (el «base»). Con `defects=True` se
    inyectan los defectos de M7 con un generador aparte: el resto queda igual al de `defects=False`.
    """
    sc = _resolve(scenario)
    rng = np.random.default_rng(seed)
    end = _START + datetime.timedelta(days=round(365.25 * sc.years))
    theta = sc.frailty_variance
    tramos, truth, insp = [], [], []
    labor_of = []  # índice de la primera fila de cada labor (para el defecto de solape)
    for zi in range(sc.n_zones):
        zone = f"Z{zi + 1}"
        lit, ucs_med, lit_q = sc.lithologies[int(rng.integers(len(sc.lithologies)))]
        zone_q, zone_f = rng.normal(0, sc.sd_zone_quality), rng.normal(0, sc.sd_zone_failure)
        for j in range(sc.labors_per_zone):
            labor = f"L{zi * sc.labors_per_zone + j + 1:03d}"
            ti = int(rng.integers(len(_LABOR_TYPE_NAMES)))
            tipo = _LABOR_TYPE_NAMES[ti]
            span_lo, span_hi, vida, esr = _LABOR_TYPES[tipo]
            temporary = vida == "Temporal"
            labor_q = rng.normal(0, sc.sd_labor_quality)
            frailty = float(rng.gamma(1.0 / theta, theta)) if theta > 0 else 1.0
            geologist = f"G{int(rng.integers(sc.n_geologists)) + 1:02d}"
            bias = rng.normal(0, sc.sd_geologist_bias)
            depth = float(rng.integers(100, 800))
            life = int(rng.integers(*sc.life_temporary_days)) if temporary else \
                int(365.25 * rng.uniform(*sc.life_permanent_years))
            n = max(min(_MIN_TRAMOS_PER_LABOR, sc.tramos_per_labor), int(rng.poisson(sc.tramos_per_labor)))
            n = min(n, ((end - _START).days - _END_MARGIN_DAYS) // _MAX_ADVANCE_DAYS)  # la validación lo hace raro
            lengths = rng.integers(3, 9, n)  # metros enteros: tramos contiguos sin solape
            chain = np.concatenate(([0], np.cumsum(lengths)))
            centers = chain[:-1] + lengths / 2.0
            # zonas de falla (A3.6): Poisson por metro, ancho lognormal
            n_f = int(rng.poisson(sc.fault_rate_per_km * chain[-1] / 1000.0))
            f_c = rng.uniform(0, chain[-1], n_f)
            f_w = sc.fault_width_median_m * np.exp(rng.normal(0, sc.fault_width_sd_log, n_f))
            in_fault = (np.abs(centers[:, None] - f_c[None, :]) <= f_w[None, :] / 2).any(axis=1) if n_f else \
                np.zeros(n, dtype=bool)
            # AR(1) en la progresiva (A3.5)
            path = np.empty(n)
            path[0] = rng.normal(0, sc.sd_path_quality)
            for k in range(1, n):
                rho = math.exp(-(centers[k] - centers[k - 1]) / sc.correlation_length_m)
                path[k] = rho * path[k - 1] + math.sqrt(1 - rho * rho) * rng.normal(0, sc.sd_path_quality)
            u = lit_q + sc.quality_shift + zone_q + labor_q + path + rng.normal(0, sc.sd_nugget_quality, n) \
                - sc.fault_quality_drop * in_fault
            advance = rng.integers(2, _MAX_ADVANCE_DAYS + 1, n)  # días entre mapeos de tramos seguidos
            last_start = (end - _START).days - _END_MARGIN_DAYS - int(advance.sum())
            date = _START + datetime.timedelta(days=int(rng.integers(max(1, last_start + 1))))
            labor_of.append(len(tramos))
            prev = None
            for k in range(n):
                e = rng.normal(0, 1, 8)
                zc = _W_JCOND * u[k] + math.sqrt(1 - _W_JCOND ** 2) * e[2]
                z = dict(rqd=_W_RQD * u[k] + math.sqrt(1 - _W_RQD ** 2) * e[0],
                         spacing=_W_SPACING * u[k] + math.sqrt(1 - _W_SPACING ** 2) * e[1], jcond=zc,
                         jr=_W_JR_JA * zc + math.sqrt(1 - _W_JR_JA ** 2) * e[3],
                         ja=_W_JR_JA * zc + math.sqrt(1 - _W_JR_JA ** 2) * e[4],
                         srf=_W_SRF * u[k] + math.sqrt(1 - _W_SRF ** 2) * e[5],
                         jn=_W_JN * u[k] + math.sqrt(1 - _W_JN ** 2) * e[6],
                         water=_W_WATER * u[k] + math.sqrt(1 - _W_WATER ** 2) * e[7],
                         ucs=_W_UCS * u[k] + math.sqrt(1 - _W_UCS ** 2) * rng.normal())
                tc = _components(sc, z, ucs_med)
                q_true = _q(tc["rqd"], tc["jn"], tc["jr"], tc["ja"], tc["jw"], tc["srf"])
                rmr_true = _rmr89(tc["ucs"], tc["rqd"], tc["spacing"], tc["jcond"], tc["water"])
                gsi_true = rm.gsi_from_jcond89_rqd(tc["jcond"], tc["rqd"]).gsi
                c = _components(sc, z, ucs_med, bias, rng, mapped=True)
                comp = (c["rqd"], c["jn"], c["jr"], c["ja"], c["jw"], c["srf"], c["ucs"], c["spacing"], c["jcond"],
                        c["water"])
                if comp == prev:  # la auditoría lo vería como registros no independientes
                    c["rqd"] += 1.0 if c["rqd"] < 100 else -1.0
                prev = (c["rqd"], *comp[1:])
                # 4 cifras: openpyxl guarda 16 y perdería la ida y vuelta exacta; la auditoría tolera 1 %
                q_rec = float(f"{_q(c['rqd'], c['jn'], c['jr'], c['ja'], c['jw'], c['srf']):.4g}")
                rmr_rec = _rmr89(c["ucs"], c["rqd"], c["spacing"], c["jcond"], c["water"])
                gsi_rec = rm.gsi_from_jcond89_rqd(c["jcond"], c["rqd"]).gsi
                if sc.sd_gsi_visual > 0:  # leído en la carta: ruido visual encima (B4.1)
                    gsi_rec += rng.normal(0, sc.sd_gsi_visual)
                gsi_rec = round(float(np.clip(gsi_rec, 0, 100)), 1)
                span = round(float(rng.uniform(span_lo, span_hi)), 1)
                de = span / esr
                # práctica (M4)
                table = _chart_rank(q_rec, de) if sc.practice_mode == "q_chart" else \
                    _table_rank(sc, gsi_rec, temporary, date)
                r = rng.random()
                dev = -1 if r < sc.p_lighter else (1 if r < sc.p_lighter + sc.p_heavier else 0)
                if sc.practice_mode == "q_chart":
                    dev = 0
                installed = int(np.clip(table + dev, 1, len(SUPPORT_TYPES)))
                # un solo número aleatorio para las horas de los cinco tipos: el contrafactual usa las suyas
                z_h = rng.normal(0, sc.sd_log_unsupported)
                hours_by_type = tuple(float(np.clip(round((sc.unsupported_hours_heavy if rk >= 4 else
                                                           sc.unsupported_hours_light) * math.exp(z_h)), 1, 240))
                                      for rk in range(1, len(SUPPORT_TYPES) + 1))
                hours = hours_by_type[installed - 1]
                inst_date = date + datetime.timedelta(days=int(hours // 24))
                # falla (M5)
                required = _chart_rank(q_true * math.exp(-sc.site_shift_delta), de)
                standup_h = 10 ** float(np.interp(rmr_true, _STANDUP_RMR, _STANDUP_LOG10_H))
                rates = _rates(sc, ti, zone_f, rmr_true, required, hours_by_type, standup_h)
                to_end = (end - inst_date).days
                censor = max(1, min(life, to_end))
                abandoned = life < to_end
                fail_day = max(1, math.ceil(rng.exponential(1.0 / (rates[installed - 1] * frailty))))
                failed = fail_day <= censor
                tid = f"T{len(tramos) + 1:04d}"
                tramos.append(dict(
                    id_tramo=tid, zona_nivel=zone, labor_codigo=labor, tipo_labor=tipo,
                    fecha_evaluacion=date.isoformat(), progresiva_inicio_m=float(chain[k]),
                    progresiva_fin_m=float(chain[k + 1]), este_m=None, norte_m=None, cota_m=None, datum=None,
                    profundidad_m=depth, ancho_m=span, alto_m=4.0, luz_m=span, esr=esr, rumbo_labor_grados=None,
                    vida_util=vida, metodo_excavacion="Perforación y voladura", litologia=lit, alteracion=None,
                    ucs_mpa=c["ucs"], metodo_ucs=None, rqd_pct=c["rqd"], jv=None, num_familias=None,
                    espaciamiento_m=c["spacing"], puntaje_condicion_juntas=c["jcond"], agua=c["water"], jn=c["jn"],
                    jr=c["jr"], ja=c["ja"], jw=c["jw"], srf=c["srf"], rmr_valor=rmr_rec, rmr_edicion="RMR89",
                    q_valor=q_rec, q_edicion="Q-NGI-2025", gsi_valor=gsi_rec,
                    gsi_tabla="GSI clásico" if sc.sd_gsi_visual > 0 else "GSI cuantificado",
                    gsi_celda=None, sost_recomendado=_TYPE_CODES[table - 1],
                    sost_instalado=_TYPE_CODES[installed - 1], fecha_instalacion=inst_date.isoformat(),
                    tiempo_sin_sostener_h=hours))
                truth.append(TrueTramo(tid, geologist, q_true, rmr_true, gsi_true, bool(in_fault[k]),
                                       _TYPE_CODES[table - 1], _TYPE_CODES[installed - 1], installed - table,
                                       _TYPE_CODES[required - 1], hours, frailty, censor, rates, hours_by_type,
                                       standup_h, zone_f, fail_day, failed))
                # inspecciones (D9.5): mensuales mientras la labor está activa, luego cada ~4 meses; la falla en su
                # fecha real y nada después, así la exposición de `tramo_outcomes` es la del modelo verdadero
                stop = fail_day if failed else censor
                days = [d for d in range(sc.inspection_active_days, sc.active_period_days + 1,
                                         sc.inspection_active_days) if d < stop]
                days += [d for d in range(sc.active_period_days + sc.inspection_inactive_days, stop,
                                          sc.inspection_inactive_days)]
                days.append(stop)
                last_state = "Falla" if failed else ("Abandonado" if abandoned else "Estable")
                for m, d in enumerate(days):
                    last = m == len(days) - 1
                    volume = None
                    if last and failed:  # D9.3: Pareto con corte inferior, recortado a 1000 m³
                        volume = round(min(1000.0, sc.failure_volume_min_m3 * rng.random()
                                           ** (-1.0 / sc.failure_volume_exponent)), 3)
                    insp.append(dict(
                        id_tramo=tid, fecha_inspeccion=(inst_date + datetime.timedelta(days=d)).isoformat(),
                        estado=last_state if last else "Estable",
                        tipo_falla=_pick(tuple(zip(*_FAILURE_TYPES)), rng.normal()) if last and failed else None,
                        volumen_m3=volume,
                        sobreexcavacion_pct=round(math.exp(_OVERBREAK[0] + _OVERBREAK[1] * math.log(q_true)
                                                           + rng.normal(0, _OVERBREAK[2])), 1) if m == 0 else None,
                        convergencia_mm=None, reparacion_tipo=None))
                date += datetime.timedelta(days=int(advance[k]))
    found = _inject_defects(sc, np.random.default_rng([seed, 1]), tramos, insp, labor_of) if defects else ()
    hist = History(tuple(HistoryTramo(**t, fila=i + 2) for i, t in enumerate(tramos)), SUPPORT_TYPES,
                   tuple(Inspection(**d, fila=i + 2) for i, d in enumerate(insp)))
    lnq = np.log([t.q for t in truth])
    rmr = np.array([t.rmr for t in truth])
    a, b = np.polyfit(lnq, rmr, 1)
    resid = float(np.std(rmr - (a * lnq + b), ddof=2))
    return hist, MineTruth(sc, seed, tuple(truth), float(a), float(b), resid, found)


def _inject_defects(sc, rng, tramos, insp, labor_of):
    """Defectos de M7 sobre los registros (dicts). Devuelve (tipo, id_tramo, detalle) por defecto inyectado."""
    out = []
    first = set(labor_of)
    by_tramo, extra = {}, []
    for i, d in enumerate(insp):
        by_tramo.setdefault(d["id_tramo"], i)
    for i, t in enumerate(tramos):
        tid = t["id_tramo"]
        if rng.random() < sc.defect_empty_rate:
            col = _EMPTY_COLUMNS[int(rng.integers(len(_EMPTY_COLUMNS)))]
            t[col] = None
            out.append(("empty_cell", tid, col))
        # solo con Q y sus seis componentes: si no, la auditoría no puede recalcularlo y el defecto no se ve
        if rng.random() < sc.defect_q_mismatch_rate and all(t[c] is not None for c in _Q_COLUMNS):
            t["q_valor"] = float(f"{t['q_valor'] * (3.0 if rng.random() < 0.5 else 1 / 3):.4g}")
            out.append(("q_mismatch", tid, ""))
        if rng.random() < sc.defect_overlap_rate and i not in first:
            t["progresiva_inicio_m"] -= float(rng.integers(1, 3))  # el tramo anterior mide al menos 3 m
            out.append(("overlapping_chainage", tid, ""))
        if rng.random() < sc.defect_inspection_before_rate:
            before = datetime.date.fromisoformat(t["fecha_instalacion"]) - datetime.timedelta(
                days=int(rng.integers(1, 11)))
            extra.append(dict(insp[by_tramo[tid]], fecha_inspeccion=before.isoformat(), estado="Estable",
                              tipo_falla=None, volumen_m3=None, sobreexcavacion_pct=None))
            out.append(("inspection_before_installation", tid, ""))
        if rng.random() < sc.defect_unknown_support_rate:
            t["sost_instalado"] = _UNKNOWN_TYPE
            out.append(("unknown_support", tid, _UNKNOWN_TYPE))
    insp += extra  # al final: las demás inspecciones conservan su fila
    return tuple(out)


_BASE = MineScenario()
# «Propuesta de escenarios» de la calibración, traducida a los campos de MineScenario (cambian solo lo indicado)
SCENARIOS: dict[str, MineScenario] = {s.name: s for s in (
    _BASE,
    # el nivel 3 no tiene que inventar efecto de sitio: δ = 0, sin efectos aleatorios ni horas sin sostener, la
    # misma tasa base en todas las labores y la práctica = la carta Q. La recta RMR–ln Q no se fija en 9 ln Q + 44
    # (Bieniawski): emerge de los componentes, igual que en la base
    dataclasses.replace(_BASE, name="ngi_site", site_shift_delta=0.0, sd_zone_failure=0.0, frailty_variance=0.0,
                        unsupported_multiplier=1.0, log_lambda0=(-9.0, -9.0, -9.0), practice_mode="q_chart"),
    # roca débil (A1.4: RMR ~ N(32, 15)); zonas de falla 3–5/km; prevalencia 15–25 %; en roca V el sostenimiento
    # ayuda poco (D8.4: β_rank −0.2 frente a −0.5): κ_def 0.3 solo con RMR89 verdadero < 21
    dataclasses.replace(_BASE, name="worse_site", quality_shift=-1.7, sd_path_quality=1.2, fault_rate_per_km=4.0,
                        kappa_deficit_rock_v=0.3, log_lambda0=(-9.0, -9.0, -7.8)),
    # A1.5: RMR ~ N(63, 13); prevalencia 1–3 %
    dataclasses.replace(_BASE, name="better_site", quality_shift=1.9, sd_path_quality=0.9,
                        log_lambda0=(-11.0, -11.0, -9.6)),
    # B5.4: la recta RMR–ln Q de la mina se corre (intercepto +≈ 8, pendiente mayor) sin tocar el Q
    dataclasses.replace(_BASE, name="shifted_correlation", jcond_shift=8.0, jcond_sd=9.0),
    # la mina sostiene de más: todo un tipo más pesado; fallas muy raras (≈ 2 %)
    dataclasses.replace(_BASE, name="conservative_practice", practice_type_shift=1,
                        log_lambda0=(-10.8, -10.8, -9.4)),
    # C6.1 y C6.6: GSI visual con DE 10, desvíos más frecuentes y un cambio de tabla en el año 3
    dataclasses.replace(_BASE, name="incoherent_practice", sd_gsi_visual=10.0, p_lighter=0.2, p_heavier=0.2,
                        table_change_date="2022-01-01"),
    # C6.3 (Peck y Lee): pendiente de la práctica al 60 % y piso en el tipo II
    dataclasses.replace(_BASE, name="mine_practice", practice_slope=0.6, practice_min_rank=2),
    # B4 y la propuesta: ruido de observador ≈ RMR 5.4, log10 Q 0.27, GSI 9 y efecto de geólogo ≈ 2.4 puntos de
    # RMR (B4.6: 2–4). Con el GSI en 9 el RMR y el Q no bajan a 5 y 0.25: no cuadran juntos
    dataclasses.replace(_BASE, name="noisy_mapping", sd_geologist_bias=0.15, sd_mapping_z=0.10, sd_mapping_rqd=16.0,
                        sd_mapping_jcond=3.0, sd_mapping_log_spacing=0.15, sd_mapping_log_ucs=0.15),
    dataclasses.replace(_BASE, name="small_mine", n_zones=2, labors_per_zone=4, tramos_per_labor=10, years=4),
    dataclasses.replace(_BASE, name="large_mine", n_zones=8, labors_per_zone=15, tramos_per_labor=40, years=10),
)}
