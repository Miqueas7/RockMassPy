"""Generador de históricos sintéticos con mecanismo conocido (Fase 4A, tarea 4; plan R4).

Arma un `History` con la estructura de la plantilla y parámetros verdaderos conocidos para los tres niveles, con
efectos aleatorios por labor y por zona (la validación agrupada tiene que tener sentido). Sirve para probar que el
pipeline recupera los parámetros y para la simulación de los mínimos (R11); nunca entrena un modelo que se entregue.
Solo códigos (Z1, L001, T0001) y litologías genéricas: ningún nombre real.

Mecanismo (u = calidad latente del macizo = efecto de zona + efecto de labor + ruido del tramo):
- RQD, Jn, Jr, Ja, Jw y SRF salen de u con valores válidos de las tablas NGI; `q_valor` = `rm.q_value` (NGI 2025)
  con 4 cifras significativas, y todo el mecanismo usa ese Q registrado.
- Nivel 1: RMR89 = a·ln Q + b + efecto de labor + ruido; GSI = c·RMR + d + ruido (así Q′ también se relaciona con
  el GSI, a través del RMR). Los componentes del RMR quedan vacíos: la auditoría no lo recalcula.
- Nivel 2: latente s = k·(γ_q·ln Q + γ_de·ln De) + efecto de labor + ruido logístico; rango = 1 + #(cortes < s),
  con k = 1 − 2·incoherencia (0 coherente, 0.5 la práctica ignora el macizo, 1 la invierte).
- Nivel 3: tasa de falla constante. El tiempo hasta la falla es Exponencial(λ), con log λ (por día) = β0
  + β_q·ln Q + β_de·ln De + β_rank·rango + efecto de zona + efecto de labor; la censura es la última inspección
  (un plazo uniforme en `exposure_days`). Con `site_effect=False`, log λ = β0_cat + β_cat·categoría de
  `read_q_chart(Q, De)`, sin efectos de zona ni de labor: la tasa depende solo de la categoría y el modelo del sitio
  no agrega nada sobre la línea base de nivel 0 (pruebas de 4B y 4C).
  Las inspecciones van cada ~4 meses; si el tramo falla, la falla se registra en su fecha real (día entero, al
  menos 1) y ya no hay inspecciones después. Así la exposición de `tramo_outcomes` (hasta la primera falla o la
  última inspección) es exactamente la del modelo verdadero, y los tramos fallados tienen exposiciones más cortas,
  como en una mina real.
"""

from __future__ import annotations

import datetime
import math
from dataclasses import dataclass

import numpy as np
from scipy.special import ndtr

from .. import _rockmasspy_core as rm
from ..history import HISTORY_TRAMO_COLUMNS, INSPECTION_COLUMNS, History, HistoryTramo, Inspection, SupportTypeDef
from ..q_support import read_q_chart
from ..support import Bolt, Shotcrete, SupportType

# Valores válidos de las tablas NGI 2025, del peor al mejor macizo
_JN = (15.0, 12.0, 9.0, 6.0, 4.0, 3.0, 2.0)
_JR = (0.5, 1.0, 1.5, 2.0, 3.0)
_JA = (8.0, 6.0, 4.0, 3.0, 2.0, 1.0, 0.75)
_JW = (0.5, 0.66, 1.0)
_SRF = (5.0, 2.5, 1.0)

LITHOLOGIES = ("andesita", "caliza", "diorita", "brecha")  # genéricas: nunca nombres de minas
# tipo de labor: (luz mínima y máxima en m, vida útil, ESR de NGI para aberturas mineras temporales/permanentes).
# Solo 3 tipos: cada tipo extra suma un parámetro al nivel 3 (audit_history) y subiría el mínimo de eventos.
# Las luces dan ln De de 0 a 2.12: más de 1.5 unidades, para que el signo de ln De sea identificable.
_LABOR_TYPES = {"Galería": (2.5, 4.5, "Permanente", 1.6), "Rampa": (4.0, 5.5, "Permanente", 1.6),
                "Tajeo": (3.0, 25.0, "Temporal", 3.0)}
# inicio de cada labor: 2019-01-01 + 0..1460 días; las evaluaciones cubren al menos 4 años (validación temporal)
_START, _START_SPAN_DAYS = datetime.date(2019, 1, 1), 1460
_MIN_TRAMOS_PER_LABOR = 4

SUPPORT_TYPES = tuple(SupportTypeDef(code, order, desc, SupportType(code, order, desc, bolt, shot, mesh, arch, cost),
                                     order + 1)
                      for code, order, desc, bolt, shot, mesh, arch, cost in (
    ("I", 1, "Perno ocasional", Bolt("fricción", 1.8, 1.5), None, None, None, 1.0),
    ("II", 2, "Pernos sistemáticos con malla", Bolt("fricción", 2.1, 1.2), None, "electrosoldada", None, 1.6),
    ("III", 3, "Pernos y shotcrete", Bolt("helicoidal", 2.4, 1.2), Shotcrete(50.0, True), None, None, 2.4),
    ("IV", 4, "Pernos, malla y shotcrete", Bolt("helicoidal", 2.4, 1.0), Shotcrete(75.0, True), "electrosoldada",
     None, 3.5),
    ("V", 5, "Shotcrete, pernos y cimbra", Bolt("helicoidal", 3.0, 1.0), Shotcrete(100.0, True), None,
     "perfil H @1.0 m", 6.0)))
# interceptos de log λ por día (recalibrados para la tasa constante: ~45 % de fallas en los dos modos)
FAIL_BETA0 = -5.3
FAIL_CATEGORY_BETA0 = -7.7
_CATEGORY_TO_TYPE = {1: "I", 2: "I", 3: "II", 4: "III", 5: "IV"}  # 6 o más: V (lo que pediría la carta Q)


@dataclass(frozen=True)
class SyntheticTruth:
    """Parámetros verdaderos del mecanismo; cada efecto aleatorio con su desviación."""

    # calidad latente del macizo
    sd_zone_quality: float = 0.4
    sd_labor_quality: float = 0.5
    sd_tramo_quality: float = 0.8
    # nivel 1 (a y b de Bieniawski 1976: RMR = 9 ln Q + 44; c y d de Hoek: GSI = RMR89 − 5)
    rmr_a: float = 9.0
    rmr_b: float = 44.0
    sd_labor_rmr: float = 3.0
    sd_rmr: float = 4.0
    gsi_c: float = 1.0
    gsi_d: float = -5.0
    sd_gsi: float = 3.0
    # nivel 2: γ_q < 0 y γ_de > 0 (peor macizo o más luz → tipo más pesado); 4 cortes para los tipos I a V
    practice_beta_lnq: float = -1.0
    practice_beta_lnde: float = 1.5
    practice_cuts: tuple[float, ...] = (-2.5, -1.0, 0.5, 2.0)
    sd_labor_practice: float = 0.5
    practice_incoherence: float = 0.0
    # nivel 3, log λ por día: β_q < 0, β_de > 0, β_rank < 0
    fail_beta0: float = FAIL_BETA0  # ~45 % de fallas: la clase menor alcanza el mínimo del nivel 3 con 240 tramos
    fail_beta_lnq: float = -0.5
    fail_beta_lnde: float = 1.0
    fail_beta_rank: float = -0.6
    sd_zone_failure: float = 0.4
    sd_labor_failure: float = 0.5
    site_effect: bool = True
    fail_category_beta0: float = FAIL_CATEGORY_BETA0  # solo con site_effect=False; prevalencia parecida
    fail_category_beta: float = 0.5
    # censura: días desde la instalación hasta la última inspección
    exposure_days: tuple[int, int] = (30, 900)

    def __post_init__(self):
        for name in ("practice_cuts", "exposure_days"):  # una lista también entra, y la verdad sigue hasheable
            object.__setattr__(self, name, tuple(getattr(self, name)))
        cuts = self.practice_cuts
        if len(cuts) != len(SUPPORT_TYPES) - 1 or any(b <= a for a, b in zip(cuts, cuts[1:])):
            raise ValueError(f"practice_cuts must be {len(SUPPORT_TYPES) - 1} strictly increasing values")
        if not 0.0 <= self.practice_incoherence <= 1.0:
            raise ValueError("practice_incoherence must be between 0 and 1")
        if any(getattr(self, n) < 0 for n in self.__dataclass_fields__ if n.startswith("sd_")):
            raise ValueError("standard deviations must be >= 0")
        lo, hi = self.exposure_days
        if not 1 <= lo <= hi:
            raise ValueError("exposure_days must be (low, high) with 1 <= low <= high")


def _pick(values, z):
    """Valor de la tabla según el cuantil normal de z (z alto = mejor macizo)."""
    return values[min(len(values) - 1, int(ndtr(z) * len(values)))]


def _positive_int(name, v):
    if isinstance(v, bool) or not isinstance(v, (int, np.integer)) or v < 1:
        raise ValueError(f"{name} must be a positive integer")


def synthetic_history(*, n_zones: int = 4, labors_per_zone: int = 5, tramos_per_labor: int = 12,
                      truth: SyntheticTruth | None = None, seed: int = 0) -> tuple[History, SyntheticTruth]:
    """Histórico sintético con mecanismo conocido. Misma semilla → mismo History.

    `tramos_per_labor` es la MEDIA: cada labor sortea su tamaño (Poisson, al menos min(4, tramos_per_labor)), así
    que las labores quedan desbalanceadas, como en una mina real, y el total de tramos varía con la semilla.
    """
    for name, v in (("n_zones", n_zones), ("labors_per_zone", labors_per_zone), ("tramos_per_labor", tramos_per_labor)):
        _positive_int(name, v)
    tr = SyntheticTruth() if truth is None else truth
    rng = np.random.default_rng(seed)
    k_practice = 1.0 - 2.0 * tr.practice_incoherence
    types = list(_LABOR_TYPES)
    tramos, inspections = [], []
    for z in range(n_zones):
        zone, zone_q, zone_f = f"Z{z + 1}", rng.normal(0, tr.sd_zone_quality), rng.normal(0, tr.sd_zone_failure)
        for j in range(labors_per_zone):
            labor = f"L{z * labors_per_zone + j + 1:03d}"
            tipo = types[int(rng.integers(len(types)))]
            span_lo, span_hi, vida, esr = _LABOR_TYPES[tipo]
            lit = LITHOLOGIES[int(rng.integers(len(LITHOLOGIES)))]
            labor_q, labor_rmr = rng.normal(0, tr.sd_labor_quality), rng.normal(0, tr.sd_labor_rmr)
            labor_p, labor_f = rng.normal(0, tr.sd_labor_practice), rng.normal(0, tr.sd_labor_failure)
            n_tramos = max(min(_MIN_TRAMOS_PER_LABOR, tramos_per_labor), int(rng.poisson(tramos_per_labor)))
            depth = float(rng.integers(100, 800))
            date = _START + datetime.timedelta(days=int(rng.integers(_START_SPAN_DAYS + 1)))
            chain, prev = 0, None
            for _ in range(n_tramos):
                u = zone_q + labor_q + rng.normal(0, tr.sd_tramo_quality)
                e = rng.normal(0, 0.5, 6)
                rqd = float(np.clip(round(55 + 22 * (0.6 * u + e[0])), 10, 100))
                jn, jr, ja = _pick(_JN, 0.6 * u + e[1]), _pick(_JR, 0.6 * u + e[2]), _pick(_JA, 0.6 * u + e[3])
                jw, srf = _pick(_JW, 0.5 * u + e[4] + 1.0), _pick(_SRF, 0.5 * u + e[5] + 0.8)
                if prev == (rqd, jn, jr, ja, jw, srf):  # la auditoría lo vería como registros no independientes
                    rqd += 1.0 if rqd < 100 else -1.0
                prev = (rqd, jn, jr, ja, jw, srf)
                # 4 cifras: openpyxl guarda 16 y perdería la ida y vuelta exacta; la auditoría tolera 1 %
                q = float(f"{rm.q_value(rm.QInput(rqd, jn, jr, ja, jw, srf), rm.QEdition.NGI2025).q:.4g}")
                lnq = math.log(q)
                rmr = round(float(np.clip(tr.rmr_a * lnq + tr.rmr_b + labor_rmr + rng.normal(0, tr.sd_rmr), 0, 100)), 1)
                gsi = round(float(np.clip(tr.gsi_c * rmr + tr.gsi_d + rng.normal(0, tr.sd_gsi), 0, 100)), 1)
                span = round(float(rng.uniform(span_lo, span_hi)), 1)
                de = span / esr
                lnde = math.log(de)
                s = k_practice * (tr.practice_beta_lnq * lnq + tr.practice_beta_lnde * lnde) + labor_p \
                    + rng.logistic(0, 1)
                rank = 1 + sum(s > c for c in tr.practice_cuts)
                category = read_q_chart(q, de).category
                censor = int(rng.integers(tr.exposure_days[0], tr.exposure_days[1] + 1))
                if tr.site_effect:
                    eta = (tr.fail_beta0 + tr.fail_beta_lnq * lnq + tr.fail_beta_lnde * lnde + tr.fail_beta_rank * rank
                           + zone_f + labor_f)
                else:
                    eta = tr.fail_category_beta0 + tr.fail_category_beta * category
                fail_day = max(1, math.ceil(rng.exponential(math.exp(-eta))))  # media 1/λ
                failed = fail_day <= censor
                exposure = fail_day if failed else censor
                length = int(rng.integers(3, 9))  # metros enteros: tramos contiguos sin solape ni deriva de redondeo
                installed = date + datetime.timedelta(days=int(rng.integers(1, 5)))
                tid = f"T{len(tramos) + 1:04d}"
                tramos.append(HistoryTramo(
                    id_tramo=tid, zona_nivel=zone, labor_codigo=labor, tipo_labor=tipo,
                    fecha_evaluacion=date.isoformat(), progresiva_inicio_m=float(chain),
                    progresiva_fin_m=float(chain + length), este_m=None, norte_m=None, cota_m=None, datum=None,
                    profundidad_m=depth, ancho_m=span, alto_m=4.0, luz_m=span, esr=esr, rumbo_labor_grados=None,
                    vida_util=vida, metodo_excavacion="Perforación y voladura", litologia=lit, alteracion=None,
                    ucs_mpa=None, metodo_ucs=None, rqd_pct=rqd, jv=None, num_familias=None, espaciamiento_m=None,
                    puntaje_condicion_juntas=None, agua=None, jn=jn, jr=jr, ja=ja, jw=jw, srf=srf, rmr_valor=rmr,
                    rmr_edicion="RMR89", q_valor=q, q_edicion="Q-NGI-2025", gsi_valor=gsi, gsi_tabla="GSI clásico",
                    gsi_celda=None, sost_recomendado=_CATEGORY_TO_TYPE.get(category, "V"),
                    sost_instalado=SUPPORT_TYPES[rank - 1].codigo_tipo, fecha_instalacion=installed.isoformat(),
                    tiempo_sin_sostener_h=None, fila=len(tramos) + 2))
                # una inspección cada ~4 meses hasta la censura; si falla, las de antes de la falla y la falla
                n_censor = max(1, math.ceil(censor / 120))
                days = [round(censor * k / n_censor) for k in range(1, n_censor + 1)]
                days = [x for x in days if x < exposure] + [exposure] if failed else days
                n_insp = len(days)
                for k, day in enumerate(days, start=1):
                    last = k == n_insp
                    inspections.append(Inspection(
                        id_tramo=tid, fecha_inspeccion=(installed + datetime.timedelta(days=day)).isoformat(),
                        estado="Falla" if last and failed else "Estable",
                        tipo_falla="Desprendimiento" if last and failed else None, volumen_m3=None,
                        sobreexcavacion_pct=None, convergencia_mm=None, reparacion_tipo=None,
                        fila=len(inspections) + 2))
                chain += length
                date += datetime.timedelta(days=int(rng.integers(5, 21)))
    return History(tuple(tramos), SUPPORT_TYPES, tuple(inspections)), tr
