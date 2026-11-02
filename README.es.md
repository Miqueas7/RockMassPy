# RockMassPy

Librería open source de ingeniería de macizo rocoso para minería: clasificaciones (RQD, RMR, Q, GSI, MRMR, Q-slope, SMR),
resistencia de Hoek-Brown, tablas personalizables por labor, gráficos, recomendación de sostenimiento, perfiles
normativos por país, tajo abierto y predicción de sostenimiento con datos históricos. Núcleo en C++20 con API en Python.

**Estado:** fases 1A (núcleo de cálculo) y 1B (tablas por labor) terminadas en las ramas `fase-1a` y `fase-1b`; aún sin versión publicada.
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
clases = [(80, "I", "I"), (60, "II", "I"), (40, "III", "II"), (20, "IV", "II"), (0, "V", "II")]
table = rm.RangeTable("RMR", "RMR89", [rm.RangeClass(lo, lo + 20, rotulo, tipo) for lo, rotulo, tipo in clases])
labor = rm.LaborTable("galería", cat, table, span_m=(3, 4))
print(labor.validate())             # []
c = labor.classify(53)
print(c.label, c.support.code)      # III II
print(labor.classify(40).label)     # IV
```

Un valor justo en el límite de dos clases (RMR 40) toma la clase peor. La librería recomienda, el ingeniero decide.
Ver `examples/02-tabla-por-labor/`.

`RatingTable` (puntajes propios por parámetro, RMR89 por defecto) ya está disponible en Python y se guarda con la tabla por labor
(`LaborTable.rating`) en JSON, YAML, Excel y CSV (`save_csv_dir` / `load_csv_dir`).

El CSV es una carpeta con un archivo por hoja (UTF-8 con BOM). `save_csv_dir(t, ruta)` escribe en el formato numérico del
computador (en Windows el que usa Excel, en otros sistemas la configuración regional), así un colega en España o EE. UU.
lo abre bien en su Excel; pasa `separator=` (`","` o `";"`) y/o `decimal=` (`"."` o `","`) para forzar uno. `load_csv_dir` lee los dos, reconoce los nombres de archivo sin importar mayúsculas (`TABLA.CSV`
es `Tabla`) y acepta también la fecha como `d/m/aaaa` (día primero).

## Gráficos

Necesitan el extra opcional `pip install "rockmasspy[viz]"` (matplotlib 3.8 o superior). Sin él, `import rockmasspy`
sigue funcionando y cualquier llamada a `rockmasspy.viz` lanza un `ImportError` que nombra el extra. Las figuras son
`Figure` de matplotlib sin estado global (no se abren ventanas).

```python
import rockmasspy.viz as viz

estilo = viz.Style(lang="es", size="cartilla", brand="Mi empresa")   # lang "es" (por defecto) o "en"; size "cartilla", "A4" o "A3"
fig = viz.plot_cartilla(labor, style=estilo)                        # `labor` viene del bloque anterior
ruta = viz.save_figure(fig, "figs/cartilla.png")                    # crea la carpeta; png, svg o pdf
print(ruta.name)                                                    # cartilla.png
p = rm.hb_params(45, 10, 0)                                         # HbParams no guarda GSI, mi ni D...
env = viz.plot_hb_envelopes(50.0, p, sigma3max_mpa=1.35, gsi=45, mi=10, d=0)  # ...así que pásalos para el pie
```

El mismo módulo dibuja la carta GSI cuantificada, las envolventes Hoek-Brown, la dispersión Q–RMR y los histogramas por
clase; cada figura dice su fuente en el pie. La librería recomienda, el ingeniero decide. Ver `examples/03-cartillas/`.

## Tramos, lote, informe y CLI

Necesita los extras `pip install "rockmasspy[io,viz,report]"` (el informe HTML solo pide el paquete base; el Word pide
`[report]` y las figuras `[viz]`). `load_tramos` lee una hoja `Tramos` (Excel o CSV) y acepta un `column_map` de tus
nombres de columna a los de la plantilla. La clasificación nunca se detiene por una fila: un tramo sin tabla para su
labor o su luz, o sin el valor del método, queda sin clasificar (`label=None`) con un aviso, y el resumen lo cuenta
aparte. Ni la librería ni la CLI imprimen filas de tramos.

```python
from pathlib import Path

import rockmasspy as rm
import rockmasspy.report as rp

Path("tramos.csv").write_text("id_tramo,Labor,luz_m,RMR\nT01,galería,3.5,53\n", encoding="utf-8")   # una hoja de una fila
tramos = rm.load_tramos("tramos.csv", column_map={"RMR": "rmr_valor", "Labor": "tipo_labor"})   # CSV: la hoja es el nombre del archivo
resultados = rm.classify_tramos(tramos, [labor])                   # `labor` viene de la sección de tablas
resumen = rm.summarize(resultados)
rm.save_results(resultados, "resultados.csv")                      # o .xlsx (pide [io])
informe = rp.build_memoria(resultados, [labor], title="Memoria de cálculo", lang="es")
rp.write_html(informe, "informe.html")                             # rp.write_docx(informe, "informe.docx") pide [report]
print(resumen.total, resumen.classified)                           # 1 1
```

Todo informe dice lo que es: «La librería recomienda, el ingeniero decide. Este documento no reemplaza el estudio
geomecánico firmado.» en la portada y en el pie de cada página, más la edición y la marca de verificación de cada
método y la versión de RockMassPy. `rp.build_anexo39b` da la estructura del Anexo 39 B del DS 024.

El mismo flujo desde la línea de comandos (código de salida 0 bien, 1 error de entrada o de uso, 2 terminó pero hay
algo que revisar):

```bash
rockmass check galeria.json
rockmass cartilla galeria.json -o cartilla.png
rockmass classify tramos.xlsx --tables galeria.json -o resultados.csv
rockmass report tramos.xlsx --tables galeria.json -o informe.docx --template anexo39b --labor galería
```

Ver `examples/04-informe/`.

## Carta de sostenimiento Q (referencia)

Digitalizada de la carta de sostenimiento del sistema Q de NGI (2025, Fig. 4-1; edición 2015, Fig. 7), con la tabla de ESR,
la dimensión equivalente De = luz / ESR y tres fórmulas clásicas marcadas **Secondary**. Es una referencia junto a tus tablas
propias, nunca un reemplazo. El ESR es una decisión de seguridad: `esr_category` es obligatorio y las categorías con rango (A, B) piden también `esr`.

```python
from rockmasspy.q_support import recommend_q_support

r = recommend_q_support(4.5, 15.0, esr_category="C")      # cámara pública de Hoek: Q 4.5, luz 15 m
print(r.roof.category)                                    # 3
print(f"{r.roof.de_m:.3f}")                               # 9.375
print(r.roof.no_empirical_data)                           # False
w = recommend_q_support(0.4, 4.5, esr_category="C", edition="Q-NGI-2015", wall_height_m=4.5)
print(w.wall_q)                                           # 1.0
```

Hoek publica la categoría 4 para esta cámara, leída en una carta anterior (1993); las cartas digitalizadas 2025 y 2015 dan 3.
La longitud de perno de la carta (columnas `q_carta_longitud_*`) está dada para ESR = 1; con otro ESR, compárala con la fórmula de Barton et al. (1980) y con tu criterio.
Los puntos en las zonas a trazos de la carta (sin datos empíricos) siguen sus líneas y llevan `no_empirical_data` y un aviso.
En el lote, `rm.add_q_chart_reference(resultados, {"*": "C"})` agrega la lectura del techo con el Q propio del tramo, y el
informe suma la sección 5.1; `viz.plot_q_chart` dibuja la carta con los tramos (sin rótulos). Desde la línea de comandos:

```bash
rockmass qsupport --q 4.5 --span 15 --esr-category C --chart punto.png      # código 2 con un aviso o categoría 7 o mayor
rockmass classify tramos.xlsx --tables galeria.json --esr "*=C" -o resultados.csv
```

Ver `examples/05-sostenimiento-q/`.

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
| Q-NGI-2025-chart / Q-NGI-2015-chart | Regiones de la carta de sostenimiento Q, digitalizadas por RockMassPy (error máximo medido 0.017 / 0.008 década, con los empalmes) | Primary |
| Q-Barton1980 | Fórmulas de luz máxima sin sostén y longitud de perno (Hoek, según Barton et al. 1980) | Secondary |
| Q-GrimstadBarton1993 | Presión de sostenimiento del techo (Hoek, según Grimstad y Barton 1993); la unidad aún está por confirmar | Secondary |
| GSI-2013 | GSI cuantificado (Hoek, Carter y Diederichs) | Primary |
| HB-2002 / HB-2018 | Parámetros del criterio de Hoek-Brown (`hb_params`) y Mohr-Coulomb equivalente (`hb_mohr_coulomb`); 2018 por defecto | Primary |
| HB-2002 | Módulo del macizo Em (`em_hoek2002`) | Secondary |
| HD-2006 | Módulo del macizo (Hoek y Diederichs) | Primary |
| Correlaciones (nombre del enum, p. ej. `RmrFromQ_Bieniawski1976`) | Correlaciones globales, sin encadenar | Primary o Secondary, ver `rm.correlate(...).info` |

Fuera de la fase 1A: Fe de tuneladora, Q 1974, ecuación 3 del GSI, tablas de mi/MR.

## Notas de Python

Algunos nombres de C++ son palabras reservadas de Python, así que llevan un guion bajo al final:

- `Infilling.None_` (sin relleno), como en `JointCondition89(..., rm.Infilling.None_, ...)`.
- `CorrelationResult.from_` y `CustomCorrelation.from_` (el argumento `from_` de su constructor).

Los resultados se imprimen de forma legible (`QResult(q=4.5, ...)`) y el paquete trae stubs de tipos (`py.typed`).

Licencia: MIT.
