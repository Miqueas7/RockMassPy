# RockMassPy

Librería open source de ingeniería de macizo rocoso para minería: clasificaciones (RQD, RMR, Q, GSI, MRMR, Q-slope, SMR),
resistencia de Hoek-Brown, tablas personalizables por labor, gráficos, recomendación de sostenimiento, perfiles
normativos por país, tajo abierto y predicción de sostenimiento con datos históricos. Núcleo en C++20 con API en Python.

**Estado:** fase 1A (núcleo de cálculo) terminada en la rama `fase-1a`; aún sin versión publicada.
La librería recomienda, el ingeniero decide.

## Instalación (desde el código)

Necesitas Python >= 3.10 y un compilador C++20.

```bash
pip install .
```

## Ejemplo mínimo

```python
import rockmasspy as rm

q = rm.q_value(rm.QInput(65, 9, 1.5, 2, 1, 1))          # rqd, Jn, Jr, Ja, Jw, SRF
print(q.q, q.info.method_id)                             # 5.4167 Q-NGI-2025

gsi = rm.gsi_from_jcond89_rqd(18, 65).gsi                # 59.5
p = rm.hb_params(gsi, 25, 0)                             # mi = 25, D = 0, HB-2018
scm = rm.hb_global_strength(90.0, p)
s3 = rm.hb_sigma3max(scm, 0.027, 400, rm.HbApplication.Tunnel)   # MN/m3, profundidad en m
mc = rm.hb_mohr_coulomb(90.0, p, s3)
print(mc.phi_deg, mc.cohesion_mpa)                       # 52.75 2.633
```

El recorrido completo con datos sintéticos está en `examples/01-tramo-sintetico/`.

## Tablas de sostenimiento por labor

Cada tipo de labor (galería, tajeo...) tiene su propia tabla: un catálogo de sostenimientos más clases RMR/Q/GSI o celdas de la cartilla GSI.
Las tablas validan (avisan, nunca bloquean), clasifican y van y vienen por JSON, YAML y Excel. YAML y Excel necesitan el extra opcional: `pip install "rockmasspy[io]"`.

```python
import rockmasspy as rm

cat = rm.SupportCatalog([rm.SupportType("I", 1), rm.SupportType("II", 2, bolt=rm.Bolt("split-set", 1.8, 1.5))])
table = rm.RangeTable("RMR", "RMR89", [rm.RangeClass(50, 100, "buena", "I"), rm.RangeClass(0, 50, "mala", "II")])
labor = rm.LaborTable("galería", cat, table, span_m=(3, 4))
print(labor.validate())             # []
print(labor.classify(53).support)   # SupportType(code='I', ...)
```

La librería recomienda, el ingeniero decide. Ver `examples/02-tabla-por-labor/`.

## Métodos

Cada resultado lleva `info.method_id` y una marca de verificación: **Primary** (verificada en la fuente original, o en
una reproducción fiel de sus ecuaciones por un autor citado), **PrimaryLaterAuthors** (verificada en una publicación
posterior de los mismos autores) o **Secondary** (solo fuente secundaria). **UserDefined** significa calibrada por el usuario con datos del sitio.

| method_id | Método | Verificación |
|---|---|---|
| RQD-Deere | RQD por testigo | Secondary |
| RQD-PH1976 | RQD por frecuencia de discontinuidades (Priest y Hudson) | Primary |
| RQD-P1982 | RQD desde Jv (Palmström 1982) | Primary |
| RQD-P2005 | RQD desde Jv (Palmström 2005) | Secondary |
| RMR76 | Bieniawski 1976 | Secondary |
| RMR89 | Bieniawski 1989 | Secondary |
| RMR14 | Celada et al. 2014 | Secondary |
| Q-NGI-2015 / Q-NGI-2025 | Sistema Q, ediciones NGI (2025 por defecto) | Primary |
| GSI-2013 | GSI cuantificado (Hoek, Carter y Diederichs) | Primary |
| HB-2002 / HB-2018 | Parámetros del criterio de Hoek-Brown (`hb_params`) y Mohr-Coulomb equivalente (`hb_mohr_coulomb`); 2018 por defecto | Primary |
| HB-2002 | Módulo del macizo Em (`em_hoek2002`) | Secondary |
| HD-2006 | Módulo del macizo (Hoek y Diederichs) | Primary |
| Correlaciones (nombre del enum, p. ej. `RmrFromQ_Bieniawski1976`) | Correlaciones globales, sin encadenar | Primary o Secondary, ver `rm.correlate(...).info` |

Fuera de la fase 1A: Fe de tuneladora, Q 1974, ecuación 3 del GSI, tablas de mi/MR, presión de soporte y luz máxima.

## Notas de Python

Algunos nombres de C++ son palabras reservadas de Python, así que llevan un guion bajo al final:

- `Infilling.None_` (sin relleno), como en `JointCondition89(..., rm.Infilling.None_, ...)`.
- `CorrelationResult.from_` y `CustomCorrelation.from_` (el argumento `from_` de su constructor).

Los resultados se imprimen de forma legible (`QResult(q=4.5, ...)`) y el paquete trae stubs de tipos (`py.typed`).

Licencia: MIT.
