# RockMassPy

Librería open source de ingeniería de macizo rocoso para minería: clasificaciones (RQD, RMR, Q, GSI, MRMR, Q-slope, SMR),
resistencia de Hoek-Brown, tablas personalizables por labor, gráficos, recomendación de sostenimiento, perfiles
normativos por país, análisis de taludes en roca (cinemática, estereografía, bloques y equilibrio límite), incertidumbre en las clasificaciones y predicción de sostenimiento con datos históricos. Núcleo en C++20 con API en Python.

**Documentación: <https://miqueas.dev/rockmasspy>** (guía, métodos, casos resueltos y referencia de la API, en
español e inglés). Los cambios de cada versión están en [CHANGELOG.md](https://github.com/Miqueas7/RockMassPy/blob/main/CHANGELOG.md) (en inglés).

**Estado:** versión 0.2.0 (fases 1 a 5: núcleo y tablas por labor, sostenimiento y perfil de Perú, tajo abierto, módulo predictivo, mina sintética y banco de pruebas; fase 7: incertidumbre en las clasificaciones).
La librería recomienda, el ingeniero decide.

## Instalación

```bash
pip install rockmasspy
```

Hay ruedas ya compiladas para Python 3.10 a 3.14 en Linux (x86_64), Windows y macOS (Apple Silicon), así que no hace
falta compilador ni CMake. La instalación base no trae dependencias de Python: el cálculo vive en el núcleo compilado.

Los extras opcionales agregan lo que no es cálculo puro:

| Extra | Agrega | Para |
|---|---|---|
| `io` | `pyyaml`, `openpyxl` | Tablas en YAML y Excel; tramos, caras de tajeo, taludes y la plantilla del histórico en Excel |
| `viz` | `matplotlib` | Carta Q, gráficos de estabilidad, estereogramas, cartillas, perfiles y mapas |
| `report` | `python-docx` | Informe Word (el informe HTML no necesita nada extra) |
| `ml` | `numpy`, `scipy` | Módulo predictivo |

```bash
pip install "rockmasspy[io,viz,report,ml]"
```

En otras plataformas (Linux ARM, Mac con Intel) `pip` compila el núcleo C++ desde la distribución de código fuente, y
para eso hace falta un compilador de C++20.

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

## Incertidumbre y bordes de clase

`classification_uncertainty` muestrea las entradas de RMR89, Q, GSI o Hoek-Brown (Monte Carlo o LHS, con semilla) y
entrega media, desviación, p05, p50, p95, mínimo y máximo de cada salida, más la probabilidad de cada clase y de cada
sostenimiento de la tabla de la labor. Informa y nada más: no cambia ninguna regla de atención ni el código de salida.
Las distribuciones las eliges tú; la librería solo propaga lo que le das. Una muestra que el núcleo rechaza es un
error que nombra la variable.

```python
import rockmasspy as rm
from rockmasspy import probabilistic as pb

base = rm.Rmr89Input()
base.functions = rm.RmrFunctions.Continuous            # curvas de Kundu et al. (2020) en lugar de los puntajes de la tabla
base.ucs_mpa, base.rqd_pct, base.spacing_m = 90.0, 70.0, 0.3
base.joint_condition_rating, base.water = 20.0, rm.Water.Dry

table = rm.LaborTable("gallery", rm.SupportCatalog([rm.SupportType("I", 1), rm.SupportType("II", 2)]),
                      rm.RangeTable("RMR", "RMR89", [rm.RangeClass(0, 68, "fair", "II"), rm.RangeClass(68, 100, "good", "I")]))
u = rm.classification_uncertainty("RMR89", base, {"ucs_mpa": pb.normal(90, 15, 50, 130), "rqd_pct": pb.uniform(55, 85)},
                                  table=table, n=2000, seed=1)
print(round(u.outputs["rmr"].mean, 1), u.class_probabilities)   # 67.4 {'fair': 0.5995, 'good': 0.4005}
```

`RmrFunctions.Continuous` usa funciones continuas ajustadas a las gráficas de Bieniawski (1989) (Kundu et al., 2020;
método `RMR89-continuous`), así que un cambio pequeño de UCS, RQD o espaciamiento mueve el puntaje sin saltos. La
clasificación con una tabla por rangos avisa `near the boundary between classes {a} and {b}` cuando el valor está a
3 puntos o menos del borde (RMR, GSI) o dentro de un factor 1.25 (Q); estos dos márgenes son provisionales. En el lote,
una hoja `Distribuciones` por `id_tramo` agrega `clase_probable`, `prob_clase_probable`, `prob_clase`,
`probabilidades` y `n_validas` a los resultados (`rockmass classify ... --distributions ARCHIVO`, también en `report`).
Ver `examples/14-incertidumbre-clasificacion/`.

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

## Estabilidad de tajeos (Mathews) y MRMR

Número de estabilidad modificado de Mathews según Potvin (1988): N' = Q' x A x B x C, con el radio hidráulico de cada
cara del tajeo (`hydraulic_radius`, `hydraulic_radius_rect`) y las zonas estable, transición y hundimiento del
gráfico de Potvin, digitalizado por RockMassPy. No hay curva logit: Mawdesley no publica los coeficientes. El factor C
sigue la ecuación del propio Potvin (8 - 6 cos a); el 8 - 7 cos de Mathews et al. (1980) es del método original. El
MRMR es el de Laubscher (1990) y sus zonas se leen en el diagrama de 1994. Todo es **Primary**; un punto fuera del
marco se lee del lado desfavorable, con aviso.

```python
import rockmasspy as rm

# N' = Q' * A * B * C de un techo sintético (Q' 12, HR 2.5 m), leído en el gráfico de Potvin
r = rm.mathews_stability(12.0, 2.5, ucs_mpa=120, sigma1_mpa=30, dip_difference_deg=60,
                         failure_mode="gravity", surface_inclination_deg=0)
print(f"{r.factor_a:.3f} {r.factor_b:.1f} {r.factor_c:.1f}")      # 0.325 0.8 2.0
print(f"{r.n_prime:.2f}")                                         # 6.24
print(r.reading.zone_label)                                       # stable

# MRMR (Laubscher 1990) de un caso sintético, ubicado en el diagrama de 1994 con HR = 30 m
i = rm.Mrmr90Input()
i.irs_mpa, i.rqd_pct, i.spacings_m, i.joint_condition = 100, 75, [0.5, 1.0, 3.0], 10.8
m = rm.mrmr90(i)
print(m.mrmr_class)                                               # 3B
print(rm.read_stability_graph("Laubscher1994-stability", 30.0, m.mrmr).zone_label)    # caving
```

Las caras salen de una hoja `Superficies` (xlsx) o de un CSV (`rm.SURFACE_COLUMNS`): `rm.load_stope_surfaces`,
`rm.assess_stope_surfaces`, `rm.save_stope_results`, `viz.plot_stability_graph` y `report.build_stope_report`. Una cara
con geometría imposible detiene la corrida y nombra su fila. Por la línea de comandos:

```bash
rockmass mathews Superficies.csv --chart mathews.png -o resultados.csv   # sale con 2 si hay una cara en transición, hundida o con aviso
rockmass mrmr --irs 100 --rqd 75 --spacing 0.5 1.0 3.0 --jc 10.8 --hr 30 --chart laubscher.png
```

Ve `examples/06-tajeos-mathews-mrmr/`.

## Verificación normativa (Perú, DS 024-2016-EM)

`rockmass verify` y `verify(...)` comparan tus datos (tablas por labor, tramos, caras de tajeo y un juego de hojas de
diseño) con los requisitos de un **perfil normativo**: un archivo JSON en `python/rockmasspy/profiles/`. El primero es
`PE-DS024-2016`: el reglamento de seguridad minera del Perú (DS 024-2016-EM, con el DS 023-2017-EM y el DS
034-2023-EM) y la guía de criterios geomecánicos de Osinergmin (2017). Cada requisito lleva su instrumento, artículo,
página, URL y fuerza: **ley** (el reglamento) o **guía** (una recomendación, que nunca sale «no cumple»). Un texto
que no regía en la fecha de `--as-of` sale como no verificable y dice desde cuándo rige el texto cargado.

Seis estados: cumple, no cumple, atención, nota, **no revisado** (no diste datos para él) y **no verificable por la
librería** (es de procedimiento, o no hay regla). Lee esto dos veces:

- **«No verificable por la librería» no es un incumplimiento.** Significa que la librería no puede juzgarlo (un
  estudio firmado, la publicación en la labor, la inspección trimestral); lo revisa el ingeniero.
- **La librería nunca dice «aprobado».** Un «cumple» solo significa que los números declarados cumplen el límite
  numérico que pudo revisar; el estudio firmado y el criterio del ingeniero siguen en pie.
- Código de salida 0 si nada falla, 1 si hay un error de entrada, 2 si algo no cumple o pide atención. Las notas, los
  ítems no revisados y los no verificables no cambian el código.

```python
import rockmasspy as rm
from rockmasspy.design_inputs import DesignInputs, RefugeStation
from rockmasspy.verify import verify

# una estación de refugio inventada: RMR 55 sin sostenimiento declarado, a 400 m del frente, 30 m2 para 20 personas
st = RefugeStation("E1", "roca", rmr=55, distancia_frente_m=400, area_m2=30, aforo=20)
v = verify(rm.get_profile("PE-DS024-2016"), as_of="2026-11-02", design=DesignInputs(refuge_stations=(st,)))
print("PE-DS024-2016" in rm.available_profiles())        # True
print(v.counts())                                       # {'complies': 2, 'does_not_comply': 1, 'attention': 0, 'note': 0, 'not_checked': 12, 'not_verifiable': 9}
print(v.exit_code)                                      # 2
```

Las hojas de diseño son `Estaciones_refugio`, `Refugios_peatonales`, `Resumen_QC`, `Factores_seguridad` y `Autosoporte`
(un libro xlsx, o un CSV por hoja con ese nombre; todas son opcionales). Los identificadores de fila nunca llegan a la
consola ni al informe. Por la línea de comandos:

```bash
rockmass verify --profile PE-DS024-2016 --as-of 2026-11-02 --tables galeria.json --tramos Tramos.csv \
  --surfaces Superficies.csv --design Estaciones_refugio.csv Resumen_QC.csv --report verificacion.html
```

Ve `examples/07-verificacion-normativa-peru/`.

## Cinemática de taludes, SMR y Q-slope

Para la cara de un talud de tajo abierto y sus familias de discontinuidades, `rockmass slope` y `assess_slopes(...)`
devuelven:
- la estadística de **Fisher** de cada familia (orientación media, kappa, alfa95) y la densidad de polos;
- las **pruebas cinemáticas de Markland**: deslizamiento planar, por cuña (zonas primaria y secundaria), volteo
  flexural y volteo directo (el volteo oblicuo se cuenta aparte), cada una con su conteo y su porcentaje;
- el **SMR** (Romana, discreto; Tomás, continuo) por familia, por cuña y por plano sin familia, con el caso que
  gobierna y su clase;
- el **Q-slope** de Bar y Barton y el ángulo beta, comparado con el buzamiento de la cara.

Lee esto dos veces:

- **Los porcentajes son factibilidad, no probabilidad.** Son la parte de los polos (planar, flexural) o de las
  intersecciones (cuña, volteo directo) que cae en la zona crítica. No son una probabilidad de falla.
- **El límite lateral** (30 grados por defecto, `--lateral-limit`) deja el deslizamiento planar y los dos volteos
  para las discontinuidades que rumbean cerca de la cara. La cuña no lleva límite lateral. También se informa el
  planar sin límites; el código de salida usa el que tiene límites.
- **Una cara más empinada que beta** (`face_steeper_than_beta`) quiere decir que la cara es más empinada que el
  ángulo que Q-slope permite sin refuerzo ni soporte: pide atención. Una cara igual a beta también se señala.
- La figura de cuña cuenta las intersecciones primarias más las secundarias. El SMR continuo (`smr_caso_continuo`)
  tiene su propio caso que gobierna, aparte del discreto.
- Los nombres de `familia` llegan a la consola dentro de los avisos: no pongas en ellos códigos de labor ni de mina.
  `id_talud` e `id_tramo` van solo al archivo de resultados y a las tablas del informe, nunca a la consola ni a las
  figuras.

```python
import rockmasspy as rm

# un caso planar inventado (Tomás et al. 2006, p. 93): cara 22/180, junta 21/209, RMR básico 60, voladura normal
a = rm.smr_angles(rm.SmrMode.Planar, 209, 21, rm.PlaneOrientation(180, 22))
print(f"{a.a_deg:.0f} {a.b_deg:.0f} {a.c_deg:.0f}")           # 29 21 -1
d = rm.smr(60, rm.SmrMode.Planar, rm.SmrFunctions.Discrete, rm.SlopeExcavation.NormalBlastingOrMechanical, a)
c = rm.smr(60, rm.SmrMode.Planar, rm.SmrFunctions.Continuous, rm.SlopeExcavation.NormalBlastingOrMechanical, a)
print(f"{d.smr:.0f} {d.smr_class} {c.smr:.1f} {c.smr_class}")  # 52 3 55.7 3
# Q-slope 0.6 (Bar y Barton 2018, Tabla 12): el ángulo más empinado sin refuerzo
print(f"{rm.q_slope_beta(0.6):.2f}")                          # 60.56
```

Las caras salen de una hoja `Taludes` y los planos de una hoja `Familias` (xlsx, o CSV): `rm.load_slope_faces`,
`rm.load_families`, `rm.assess_slopes`, `rm.slope_counts`, `rm.save_slope_results` (26 columnas) y
`report.build_slope_report`. `report.slope_modes` y `report.slope_figure` son los ayudantes que usa la línea de
comandos para los estereogramas. Por la línea de comandos (código 2 si algo pide atención):

```bash
rockmass slope --faces Taludes.csv --families Familias.csv --report taludes.html --charts fig -o resultados.csv
```

Ve `examples/08-taludes-cinematica-smr-qslope/`.

## Bloques en roca, probabilidad de falla y diseño banco–berma

Sobre la cinemática, `assess_blocks(...)` y `rockmass slope --blocks` corren **bloques de equilibrio límite** por cada
fila de una hoja `Bloques`, cada una ligada a una cara de talud por `id_talud`:
- **planar** (Hoek y Bray), con grieta de tracción, agua, sismo horizontal, perno o fuerza externa, y retroanálisis
  opcional (los pares c–φ que dan FS = 1);
- **cuña** por resolución vectorial (dos planos, un plano o despegue), con presión de agua por junta, sismo y fuerza
  externa;
- **volteo** de bloques regulares (Goodman y Bray 1976), con fuerza de soporte opcional en el pie;
- **berma** (Ritchie modificado, 0.2 H + 4.5 m): ángulo interrampa, ancho frente al requerido y, con una distribución,
  la confiabilidad de la berma.

Un bloque con filas en `Distribuciones` para sus variables recibe además una **probabilidad de falla** (Monte Carlo o
hipercubo latino, variables normales truncadas, exponenciales o uniformes, semilla fija), con el FS medio, la
desviación y el índice de confiabilidad.

Lee esto dos veces:

- **La PoF depende de las distribuciones que tú eliges.** La librería propaga lo que le das; no sabe cuánto varía tu
  macizo. Con la misma semilla, el mismo número de muestras y las mismas hojas, la PoF sale igual en cualquier máquina.
- **El FS igual a 1 cuenta como falla** (con holgura de 1e-9), una muestra con despegue cuenta como falla y la PoF es
  condicional a que el bloque se forme (se informan `n` y `n_valid`).
- **La librería nunca dice «aceptable».** Solo un FS menor que 1 y los avisos cambian el código de salida. La PoF, la
  confiabilidad de la berma y la comparación con Ritchie se informan y no se juzgan (solo los juzga un criterio de
  aceptación que tú eliges, más abajo), y el análisis es 2D, por metro de talud.
- **Privacidad:** `id_bloque` e `id_talud` salen solo en las tablas del informe y en el archivo de resultados, nunca
  en la consola, las figuras ni un mensaje de error. No pongas códigos de labor ni de mina en los nombres de `familia`:
  llegan a los avisos.

```python
import rockmasspy as rm
from rockmasspy.probabilistic import Distribution, run_probabilistic

# Sau Mau Ping (problema 1 de verificación de RocPlane, en kN): H 60 m, cara 50, plano 35, c 100 kPa, φ 35, kh 0.08
i = rm.PlanarInput()
i.height_m, i.face_dip_deg, i.plane_dip_deg = 60, 50, 35
i.unit_weight, i.water_unit_weight, i.cohesion, i.friction_deg, i.kh = 27, 10, 100, 35, 0.08
i.water_fill = 1.0                                    # saturado, sin grieta de tracción
print(f"{rm.planar_fs(i).factor_of_safety:.3f}")      # 0.818
crack = rm.critical_tension_crack(60, 50, 35)         # grieta crítica del talud seco, llena al 90 %
print(f"{crack.depth_m:.4f} {crack.distance_m:.4f}")  # 14.0092 15.3358
i.tension_crack_distance_m, i.water_fill = crack.distance_m, 0.9
print(f"{rm.planar_fs(i).factor_of_safety:.3f}")      # 1.065
variables = {"friction_deg": Distribution("normal", 15, 70, 35, 5),
             "cohesion": Distribution("normal", 0, 250, 100, 20),
             "tension_crack_distance_m": Distribution("normal", 0, 35.34, 15.3, 4),
             "water_fill": Distribution("exponential", 0, 1, 0.5),
             "kh": Distribution("exponential", 0, 0.16, 0.08)}
r = run_probabilistic("planar", i, variables, n=5000, sampling="lhs", seed=9)
print(f"{r.pof * 100:.1f} {r.n_valid}/{r.n}")         # 7.4 5000/5000
print(f"{rm.ritchie_berm_width(12).width_m:.1f}")     # 6.9
```

Los bloques salen de una hoja `Bloques` (`rm.load_blocks`, una fila por análisis, columna `modelo` = `planar`, `cuña`,
`volteo` o `berma`) y las variables aleatorias de una hoja `Distribuciones` (`rm.load_distributions`: `id_bloque`,
`variable`, `distribucion` = `normal`, `exponencial` o `uniforme`, `media`, `desviacion`, `minimo`, `maximo`), ambas en
xlsx o CSV. Cada bloque toma la cara y la orientación media (Fisher) de las familias de su talud, así que `Taludes` no
gana columnas. `rm.block_counts` da los conteos y `rm.save_block_results` escribe el archivo de resultados de 25
columnas; `report.build_slope_report(..., blocks=...)` agrega las tablas de bloques y `report.block_figure` dibuja el
histograma del FS y la curva de PoF. Desde la línea de comandos (0 si todo está bien, 1 si hay un error de entrada, 2 si
algo pide atención):

```bash
rockmass slope --faces Taludes.csv --families Familias.csv --blocks Bloques.csv --distributions Distribuciones.csv \
    --iterations 5000 --sampling lhs --seed 9 --blocks-output bloques_resultados.csv --report taludes.html --charts fig
```

Opciones: `--blocks` (pide `--faces` y `--families`), `--sheet-blocks`, `--distributions`, `--sheet-distributions`,
`--iterations` (por defecto 5000), `--sampling lhs|monte-carlo` (por defecto `lhs`), `--seed` (por defecto 1) y
`--blocks-output RES.csv|.xlsx`. Todas, salvo la propia `--blocks`, necesitan `--blocks`.

Mira `examples/09-bloques-probabilistico-berma/`.

## Equilibrio límite y Newmark

`assess_le(...)` y `rockmass le` calculan el **factor de seguridad de una sección 2D por tajadas verticales**: un
talud de tajo, un pad o un botadero, con estratos, línea piezométrica y coeficiente sísmico pseudoestático. Por cada
fila de una hoja `Analisis_LE`:
- los métodos: Ordinario (Fellenius), Bishop simplificado, Janbu simplificado y corregido, Spencer y
  Morgenstern-Price/GLE (función entre tajadas de medio seno o constante);
- la superficie de falla: **búsqueda circular** (malla de centros con radios y afinado local), **búsqueda de bloque**
  sobre una capa débil o una polilínea dada;
- la resistencia en la base de cada tajada: Mohr-Coulomb o **Hoek-Brown no lineal** (envolvente de Balmer, con GSI y
  mi o con mb, s y a);
- agua por `ru` o por línea piezométrica (con el agua encharcada sobre el terreno), grieta de tracción con agua y `kh`;
- el **coeficiente de fluencia ky** (el kh que lleva el FS a 1) y el **desplazamiento de Newmark de bloque rígido**
  para un registro de aceleraciones.

Lee esto dos veces:

- **Con sismo, usa Spencer o GLE.** Bishop no equilibra fuerzas horizontales, así que un kh alto lo separa de los
  métodos rigurosos (ACADS 1(d) en Slide2, kh 0.15: Bishop 1.016, Spencer 0.991).
- **La librería nunca dice «aceptable».** Solo un FS igual o menor que 1 (con holgura de 1e-9) y los avisos cambian el
  código de salida; el FS, ky y el desplazamiento de Newmark se informan y no se juzgan; mira Criterios de aceptación y
  Sarma.
- **Privacidad:** `id_seccion`, `id_analisis`, `material`, `registro` y los nombres de línea salen solo en las tablas
  del informe (los dos ids también en el archivo de resultados), nunca en la consola, las figuras ni un mensaje.

```python
import rockmasspy as rm

# Fredlund y Krahn (1977), problema 21 de verificación de Slide2, en psf, pcf y ft: c 600, φ 20, γ 120, seco
s = rm.LeSection()
s.surface = [rm.Point2(x, y) for x, y in [(0, 60), (60, 60), (140, 20), (180, 20)]]
m = rm.LeMaterial()
m.unit_weight, m.cohesion, m.friction_deg = 120, 600, 20
estrato = rm.LeLayer()
estrato.bottom, estrato.material = [], 0              # un solo estrato: sin línea de base
s.layers, s.materials = [estrato], [m]
f = rm.SlipSurface()
f.circle = rm.Circle(120, 90, 80)                     # xc, yc, R
bishop = rm.le_factor_of_safety(s, f, rm.LeMethod.Bishop)
spencer = rm.le_factor_of_safety(s, f, rm.LeMethod.Spencer)
print(f"{bishop.factor_of_safety:.3f}")               # 2.076
print(f"{spencer.factor_of_safety:.3f}")              # 2.072
print(spencer.info.method_id)                         # Spencer
```

Las hojas son `Geometria` (una fila por vértice: `id_seccion`, `linea`, `x_m`, `y_m`; la línea `superficie` es
obligatoria y `piezometrica` opcional), `Estratos` (`orden` 1 arriba, `material`, `linea_base`), `Materiales_LE`
(`mohr_coulomb` o `hoek_brown`), `Analisis_LE` (`metodos` separados por `;`, el primero busca; `superficie` =
`circular`, `bloque` o `dada`; `kh`, `registro`) y `Sismos` (`registro`, `t_s`, `a_g` en g, paso constante), en un
xlsx o en un CSV por hoja. `rm.le_counts` da los conteos, `rm.save_le_results` escribe una fila por método (con
`kh` y `fs_estatico`, el FS estático de cada método sobre la crítica estática),
`report.build_slope_report(..., le=...)` agrega las tablas de equilibrio límite y `report.le_figure` /
`report.newmark_figure` dibujan la sección y el registro de Newmark. Desde la línea de comandos (0 si todo está bien, 1
si hay un error de entrada, 2 si algo pide atención):

```bash
rockmass le --geometry Geometria.csv --layers Estratos.csv --materials Materiales_LE.csv --analyses Analisis_LE.csv \
    --records Sismos.csv --output equilibrio_resultados.csv --report taludes.html --charts fig
```

Opciones: `--workbook LIBRO.xlsx` (en lugar de los CSV), `--records`, `-o/--output RES.csv|.xlsx`,
`--report OUT.docx|.html`, `--charts DIR`, `--title`, `--author`, `--lang es|en` y `--no-figures`. Con más de un
análisis, `rockmass le` imprime `analysis <k> of <n>...` en stderr.

Tiempos: con Hoek-Brown, una búsqueda circular de 20×20×11 tarda unos 10 a 15 s; con kh, ky por vueltas puede
repetirla hasta 5 veces.

Mira `examples/10-equilibrio-limite-newmark/`.

## Criterios de aceptación y Sarma

`assess_criteria(...)` y `rockmass slope|le --criteria` comparan cada bloque (3B) y cada análisis de equilibrio límite
(3C) con un **criterio de aceptación** que tú eliges, y dicen por chequeo **«cumple», «no cumple» o «no verificable»**,
siempre con el criterio, su fuente, su fuerza (ley o guía) y su marca. Los criterios son perfiles de datos versionados:
- `READ-STACEY-2009`: Read y Stacey (2009), tabla 9.9, FS estático mínimo y PoF máxima por escala (banco, interrampa,
  global) y consecuencia; marca V2 (leída en Moffitt 2023, que la reproduce), sin la columna dinámica;
- `NDEP-2021`: pads de lixiviación de Nevada, FS estático 1.30, seudoestático 1.05 y, bajo 1.05, un análisis de
  deformación;
- `DMIRS-WA-2019`: Australia Occidental, FS por consecuencia;
- `RYAN-PRYOR-2000`: confiabilidad de berma de 50 a 90 %;
- tu tabla propia (hoja `Criterios`: `escala`, `consecuencia`, `fs_estatico_min`, `fs_seudoestatico_min`,
  `pof_max_pct`, `confiabilidad_berma_min_pct`, `fuente`), que `rm.load_criteria_table` lee como guía con la marca
  `user`.

Cada fila de `Bloques` y de `Analisis_LE` lleva `escala` (`banco`, `interrampa`, `global`, `pad`, `botadero`) y
`consecuencia`; `Analisis_LE` lleva además `periodo_retorno_anios`. El perfil `PE-DS024-2016` verifica el **art. 264**
del DS 024 (análisis seudoestático de la pendiente general del tajo con período de retorno de 100 años; no fija FS).

**Sarma con tajadas no verticales** (`superficie = sarma`, la base en `linea_superficie` y un ángulo de interfaz por
vértice interior en `sarma_angulos`, u `opt` para buscarlos) divide la masa en cuñas rígidas con interfaces inclinadas
y entrega el FS y la aceleración crítica Kc. Es el método para botaderos que deslizan sobre una base débil inclinada.
Reproduce el problema 4 del manual de verificación de Sarma de Slide (1.1970 frente a 1.198) y, con una sola cuña, el
bloque planar de Hoek. No acepta Hoek-Brown, agua encharcada ni grieta de tracción.

Lee esto dos veces:

- **La librería nunca dice «aprobado».** Un «no cumple» pide atención (código 2); un «no verificable» es una nota con
  su razón (sin escala, sin criterio para esa escala, sin análisis probabilístico). Nunca cuenta como «cumple».
- **Rangos:** cuando un criterio es un rango (PoF de 25 a 50 % en un banco), la política por defecto es el extremo
  conservador (el alto para un FS mínimo, el bajo para una PoF máxima); `range_policy=` o `--range-policy upper|lower`
  la cambian, y el valor usado se informa. Un valor igual al límite lo cumple.
- **Privacidad:** los ids salen solo en las tablas del informe y en los archivos de resultados, nunca en la consola
  ni en un mensaje.

```python
import csv
import tempfile
from pathlib import Path

import rockmasspy as rm
from rockmasspy.criteria import criteria_assignments

# Verificación de Sarma de Slide, problema 4 (Hoek 1987): pila de desmonte seca sobre piso cizallado, kN y m
ground = [(-50, -2.97), (0, 0), (111.4, 76.5), (229.545, 13.6815), (250, 14.9)]
floor = [(-50, -2.97), (0, 0), (250, 14.9)]
base = [(0, 0), (108, 6.4), (130, 73.06)]             # dos cuñas, un vértice interior
s = rm.LeSection()
s.surface = [rm.Point2(x, y) for x, y in ground]
top, bottom = rm.LeLayer(), rm.LeLayer()
top.bottom, top.material = [rm.Point2(x, y) for x, y in floor], 0
bottom.bottom, bottom.material = [], 1
pile, sheared = rm.LeMaterial(), rm.LeMaterial()
pile.unit_weight, pile.cohesion, pile.friction_deg = 15.7, 100, 42
sheared.unit_weight, sheared.cohesion, sheared.friction_deg = 15.7, 10, 6
s.layers, s.materials = [top, bottom], [pile, sheared]
i = rm.SarmaInput()
i.base, i.interface_angles_deg = [rm.Point2(x, y) for x, y in base], [116.5]  # desde +x, antihorario
r = rm.sarma_fs(s, i)
print(f"{r.factor_of_safety:.3f} {r.critical_acceleration:.4f}")  # 1.197 0.0540

# La misma sección desde hojas, juzgada (solo para ilustrar) como un pad frente a NDEP (2021)
d = Path(tempfile.mkdtemp())
def sheet(name, cols, rows):
    with open(d / f"{name}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, cols, restval="")
        w.writeheader()
        w.writerows(rows)
    return d / f"{name}.csv"
src = {"Geometria": sheet("Geometria", rm.GEOMETRY_COLUMNS, [
           dict(id_seccion="S", linea=n, x_m=x, y_m=y)
           for n, pts in (("superficie", ground), ("piso", floor), ("falla", base)) for x, y in pts]),
       "Estratos": sheet("Estratos", rm.LAYER_COLUMNS, [dict(id_seccion="S", orden=1, material="pila", linea_base="piso"),
                                                       dict(id_seccion="S", orden=2, material="piso")]),
       "Materiales_LE": sheet("Materiales_LE", rm.MATERIAL_COLUMNS, [
           dict(material="pila", modelo="mohr_coulomb", peso_unitario_kn_m3=15.7, cohesion_kpa=100, friccion_grados=42),
           dict(material="piso", modelo="mohr_coulomb", peso_unitario_kn_m3=15.7, cohesion_kpa=10, friccion_grados=6)]),
       "Analisis_LE": sheet("Analisis_LE", rm.ANALYSIS_COLUMNS, [
           dict(id_analisis="A", id_seccion="S", superficie="sarma", linea_superficie="falla", sarma_angulos="116.5",
                base_modelo_m=-10, escala="pad", consecuencia="media")])}
le = rm.assess_le(src)
checks = rm.assess_criteria(rm.get_profile("NDEP-2021"), le=le, assignments=criteria_assignments(le=le))
print(f"{le[0].sarma.factor_of_safety:.3f}")          # 1.197
print(rm.criteria_counts(checks))                     # {'checks': 3, 'meets': 0, 'fails': 1, 'not_verifiable': 2}
print([(c.item_id, c.status) for c in checks][0])     # ('NDEP-6-estatico', 'fails')
print(checks[1].reason)                               # no pseudo-static analysis
```

`rm.save_criteria_results` escribe un chequeo por fila (hoja `Criterios_resultados`) y
`report.build_slope_report(..., criteria=..., criteria_profile=..., profile_checks=...)` arma el informe de taludes
completo: resumen ejecutivo, alcance y criterios, cinemática, bloques, equilibrio límite y Sarma, verificación de
criterios, normativa (art. 264), avisos y métodos. Desde la consola:

```bash
rockmass le --geometry Geometria.csv --layers Estratos.csv --materials Materiales_LE.csv --analyses Analisis_LE.csv \
    --records Sismos.csv --criteria READ-STACEY-2009 --profile PE-DS024-2016 --criteria-output criterios.csv
rockmass slope --faces Taludes.csv --families Familias.csv --blocks Bloques.csv --criteria Criterios.csv
```

Opciones: `--criteria ID|CRITERIOS.csv|.xlsx`, `--criteria-output RES.csv|.xlsx`, `--range-policy
conservative|upper|lower` (las dos piden `--criteria`) y, en `rockmass le`, `--profile PE-DS024-2016`. El resumen
imprime `meets: a, fails: b, not verifiable: c` y los «no cumple» agrupados por regla, sin ids.

Mira `examples/11-criterios-sarma/`.

## Histórico de la mina: auditoría de ingesta y correlaciones propias

Las correlaciones necesitan el extra `pip install "rockmasspy[ml]"` (numpy y scipy). Leer y auditar el histórico solo
pide el paquete base (el Excel pide `[io]`). `rm.load_history` lee la plantilla del histórico
(`plantillas/Plantilla_historico_geomecanico.xlsx`: hojas `Tramos`, `Tipos_sostenimiento` y `Desempeno`), y
`rm.audit_history` recalcula el Q y el RMR89 básico, marca los registros no independientes y las incoherencias
entre hojas, y cuenta cuánto le falta a cada nivel predictivo para su mínimo (decisión de diseño, no un valor
publicado).

```python
import rockmasspy as rm
from rockmasspy.predictive import fit_site_correlation, save_site_correlations

h = rm.load_history("historico.xlsx")
audit = rm.audit_history(h)
fit = fit_site_correlation(h, "rmr_from_q", group_by="litologia")
print(fit.mine.status, fit.mine.a, fit.mine.b)       # "site", "unstable" o "not_calibrated"
save_site_correlations(fit, "resultados/")           # CSV con todos los ajustes, JSON solo con los «site»
```

El nivel 1 ajusta `rmr_from_q`, `gsi_from_rmr` y `gsi_from_q_prime` por dominio y para toda la mina:
- OLS con intervalo de predicción;
- Deming, solo si das el cociente de varianzas de error;
- bootstrap que remuestrea labores enteras;
- un bayesiano conjugado centrado en la correlación global publicada: con pocos datos se queda cerca de ella.

`to_custom_correlation()` convierte un ajuste en una `CustomCorrelation` para tus tablas por labor. Desde la
terminal:

```bash
rockmass history historico.xlsx --correlations --output resultados/ --report historico.docx
```

La CLI y el informe muestran conteos y códigos (los dominios salen como D1, D2…). Nunca muestran la labor, la zona,
las coordenadas ni la litología, ni tampoco el nombre del archivo de entrada. Los archivos de resultados sí traen el
`id_tramo` y el dominio: guárdalos en la carpeta protegida de la mina, junto con el histórico. Mira
`examples/12-historico-prediccion/`.

### Auditoría de la práctica (nivel 2) y modelo de falla con recomendación (nivel 3)

```python
from rockmasspy.predictive import audit_practice, fit_performance, recommend, save_model

practica = audit_practice(h)                  # logit ordinal del tipo instalado: describe, nunca recomienda
modelo = fit_performance(h)                   # "site", "partial" o "not_calibrated"
recs = recommend(modelo, tramos_nuevos, threshold=0.10, exposure_days=365, practice=practica)
save_model(modelo, "modelo.json")             # coeficientes, rangos y conteos; nunca filas ni ids
```

- **Nivel 2:**
  - Ajusta un logit acumulado del tipo de sostenimiento instalado sobre ln Q, ln De (luz/ESR), vida útil y tipo de
    labor.
  - Dice si la práctica es coherente con la calidad del macizo y con la luz, y si es más predecible que la carta Q
    NGI.
  - Marca los tramos cuyo tipo instalado queda fuera de su conjunto conforme al 90 % (≈ 10 % por construcción: no
    es un detector de desvíos).
  - Mide la consistencia de la práctica con 1 − tanh(w/4), con w el ancho medio de las bandas internas del logit;
    sobre 0.66 dice `practice poorly consistent`.
- **Nivel 3:**
  - Modela la tasa de falla con un riesgo constante y una fragilidad gamma por labor; la exposición entra como
    *offset*.
  - Tiene restricciones de signo: peor macizo o más luz nunca bajan el riesgo, y más sostenimiento nunca lo sube.
  - Usa una covarianza robusta agrupada por zona.
  - La P(falla en H días) de una labor nueva es 1 − (1 + θλH)^(−1/θ).
- **Validación:**
  - Particiones: por labor, dejando una zona fuera, y temporal.
  - Referencias: un ficticio de tasa constante y la línea base de la categoría NGI, con bootstrap por labor.
  - El modelo queda `site` solo si las particiones por labor y por zona superan a las dos referencias (IC 95 % de la
    mejora de la devianza de Poisson sobre cero y sin pliegues fallidos), y la temporal no sale peor.
- **Forma:** aditiva en la calidad y el rango del sostenimiento, o con la interacción (calidad − máx)·(rango − máx)
  con cota ≥ 0 (el riesgo sigue monótono en las dos). La interacción entra solo con 10 eventos por parámetro
  contándola y si baja la devianza de Poisson fuera de pliegue (pliegues por labor, de otra semilla que la
  validación); si queda en su cota en el ajuste final, vuelve la aditiva.
- **Recomendación:**
  - Elige el tipo más liviano elegible cuyo límite superior, 1 − exp(−λ_sup·H·Z_q), queda bajo el umbral.
  - λ_sup suma el cuantil de la fragilidad con θ superior y una **zona nueva**: σ_z² = C·Var(η en la media) con la
    covarianza agrupada por zona, tomada en su cota superior unilateral χ², σ̂_z·sqrt((C − 1)/χ²₁₋ᵤ(C − 1)) con
    u = 0.5 + level/2 (`PerformanceModel.zone_sd_upper`; ×1.80 con 8 zonas y ×2.37 con 5, con level 0.9). Con
    menos de 10 zonas, `fit_performance` avisa.
  - El umbral y el horizonte los fija el ingeniero: no hay valores por defecto.
  - No se elige nada si el modelo no es `site`, si el tramo extrapola, si el efecto del sostenimiento no está
    identificado o si queda activa una restricción de signo en la calidad o en la luz. Tampoco con las compuertas
    (decisiones de diseño): (a) el tramo está en el tercio peor de la calidad y ahí el observado/esperado fuera de
    pliegue pasa de 1.2 o tiene menos de 10 fallas; (b) un tipo con menos de 10 tramos de entrenamiento en la clase
    de Q del tramo (Barton et al. 1974; clases de RMR de Bieniawski 1989 con `quality="rmr"`) no es elegible;
    (d) el tipo de labor del tramo tuvo menos de 10 fallas en el entrenamiento. (c) Si ningún tipo queda bajo el
    umbral lo dice (`no support type meets the threshold`), y también si los que cumplen no son elegibles. Las
    opciones se muestran igual, con el motivo.

```bash
rockmass history historico.xlsx --practice --performance --model-output modelo.json --output resultados/ \
    --threshold 0.10 --exposure-days 365 --report historico.docx
rockmass recommend tramos_nuevos.xlsx --model modelo.json --threshold 0.10 --exposure-days 365 \
    --practice-from historico.xlsx --output recomendaciones.csv
```

`recommend` imprime cada tramo por su posición. El `recomendaciones.csv` trae el `id_tramo` y dos columnas vacías,
`decision_ingeniero` y `motivo`, donde el ingeniero anota lo que decidió. Los mínimos de datos por nivel se
comprobaron por simulación (`docs/investigacion/SIMULACION_MINIMOS.md` en el repositorio). La librería recomienda; el
ingeniero decide.

## Mina sintética y banco de pruebas

`synthetic_mine` arma una **mina sintética calibrada con la literatura** para probar el módulo predictivo de punta a
punta contra una verdad conocida. Es un banco de pruebas: nunca entrena un modelo que se entregue, no da *priors* ni
coeficientes por defecto y nunca reemplaza el histórico de una mina.

```python
from rockmasspy.predictive import SCENARIOS, synthetic_mine

h, verdad = synthetic_mine("base", seed=0)        # History (Tramos, Tipos_sostenimiento, Desempeno) y MineTruth
h_mal, verdad_mal = synthetic_mine("base", seed=0, defects=True)  # la misma mina con defectos de datos inyectados
verdad.rmr_lnq_slope                              # la recta RMR–ln Q de la mina (emerge; no se fija)
verdad.p_fail("T0001", "III", 365)                # P verdadera de falla en 365 días con el tipo III, labor nueva
```

- **Mecanismo:** el macizo verdadero sale de la geología (calidad por litología y zona, un AR(1) a lo largo de cada
  labor más pepita, zonas de falla de Poisson); los parámetros de juntas salen de esa calidad y Q, RMR89 y GSI se
  calculan con la librería, así que la relación RMR–ln Q y su dispersión emergen. Cada labor la mapea un geólogo
  con sesgo y ruido; la mina sostiene con su propia tabla por GSI, con desvíos, un cambio de tabla y horas sin
  sostener; la falla es una tasa constante con fragilidad gamma que sube con el déficit frente a la carta Q leída
  con Q·exp(−δ) (δ = 0.5 en `base`, un sitio algo peor que NGI). `failure_mechanism="saturating"` es un mecanismo
  alternativo, sin carta ni déficit, para no ajustar el módulo a una sola receta.
- **Verdad:** `MineTruth.tramos` guarda los valores verdaderos, el geólogo, el tipo de la tabla y el instalado, la
  fragilidad y, por tramo, la tasa verdadera de cada tipo (con las horas sin sostener que habría tenido ese tipo);
  `p_fail(id, tipo, H)` es cerrada, marginal sobre la fragilidad de una labor nueva en la misma zona
  (`conditional=True` para la labor del tramo). `verdad.defects` lista los defectos inyectados.
- **Escenarios** (`SCENARIOS`): `base` (≈ 800 tramos, 5 zonas), `ngi_site` (el sitio es igual a la carta NGI),
  `worse_site`, `better_site`, `shifted_correlation`, `conservative_practice`, `incoherent_practice`,
  `mine_practice`, `noisy_mapping`, `small_mine` (≈ 80 tramos), `large_mine` (≈ 4800 tramos, 8 zonas),
  `saturating_large` y `saturating_worse` (el mecanismo alternativo). Un `MineScenario` se arma o se cambia con
  `dataclasses.replace`.

**Resultados del banco** (`docs/investigacion/BANCO_MINA_SINTETICA.md` en el repositorio; 50 semillas por escenario,
20 en los grandes; la recomendación se aplica a una segunda mina del mismo escenario, con zonas y labores que el
ajuste no vio; umbral 0.10, H = 365 días):

| Escenario | Elige | Demasiado liviano, agrupado | Por mina, p90 / máx | Sobrecosto frente al óptimo de verdad (mediana) |
|---|---:|---:|---:|---:|
| `large_mine` | 30.8 % | 0.7 % | 0.5 % / 4.6 % | +261 % |
| `saturating_large` | 41.8 % | 0.5 % | 1.3 % / 2.6 % | +146 % |
| `shifted_correlation` | 1.8 % | 1.1 % | 1.9 % / 3.2 % | +220 % |
| `incoherent_practice` | 1.9 % | 0.2 % | 0.1 % / 0.3 % | +431 % |
| `base` | 0.3 % | 0.0 % | 0.0 % / 0.0 % | +201 % |
| `worse_site`, `ngi_site`, `better_site`, `conservative_practice`, `small_mine` | 0 | — | — | — |

Antes de las correcciones de la 5B, `large_mine` elegía en el 60.7 % con 5.0 % demasiado liviano y `worse_site`
llegaba a 23.4 %. Ahora el p90 por mina queda en 3.7 % o menos en todas las celdas con ln Q. La seguridad se compró
con sostenimiento y con menos elecciones: con pocas zonas σ_z se conoce mal y su cota lo cubre con más
sostenimiento, no con más información. Donde el modelo elige, es mucho más seguro que la carta Q sola en los mismos
tramos.

**Cambios del módulo que pidió el banco (Fase 5B):**

- Nivel 2: el indicador de consistencia de arriba (corte 0.66); el logit ordinal converge con n grande (criterio
  del gradiente medio).
- Auditoría: `missing_values`, un hallazgo por columna con celdas vacías (solo conteos, sin `id_tramo`); la regla
  de Q es |Q registrado − Q recalculado| > máx(0.005, 1 % de Q) o una razón mayor que 2 (`Q_MAX_RATIO`), y un Q
  registrado ≤ 0 siempre es hallazgo.
- Nivel 1: `gsi_from_rmr` avisa que GSI y RMR comparten la condición de juntas y el RQD (errores de mapeo
  correlacionados).
- Nivel 3: la forma con interacción, la cota χ² de σ_z, las compuertas (a)–(d) y el aviso con menos de 10 zonas
  (arriba). El JSON del modelo pasa al **esquema 4** (`zone_sd`, `poor_rock`, `class_counts`,
  `labor_type_failures`); uno de esquema anterior se rechaza y pide reajustar con
  `rockmass history --performance --model-output`.

Ver `examples/13-mina-sintetica/`: una mina por la auditoría y los niveles 1 a 3, medida contra su verdad.

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
| Mathews-Potvin1988 | Número de estabilidad modificado N' (factores A, B, C), radio hidráulico y gráfico de estabilidad, digitalizado por RockMassPy (error máximo medido 0.014 celda; ajuste del factor A 0.019, C por deslizamiento 0.044, curvas de B 0.007) | Primary |
| MRMR-Laubscher1990 / Laubscher1994-stability | MRMR (Laubscher 1990) y su diagrama de hundimiento (1994, error máximo medido 0.009 celda) | Primary |
| SMR-Romana1985 / SMR-Tomas2007 | SMR de Romana (discreto) y de Tomás (continuo, revisión 2017) para rotura planar y vuelco | PrimaryLaterAuthors |
| SMR-Romana1985-wedge | SMR discreto en cuña (adaptación de Anbalagan 1992, según la describe Tomás) | Secondary |
| Q-slope-BarBarton2017 | Q-slope y el ángulo beta (Bar y Barton 2017, 2018) | PrimaryLaterAuthors |
| Kinematic-PlanarSliding / -WedgeSliding / -FlexuralToppling-Goodman1980 / -DirectToppling-HudsonHarrison1997 | Pruebas cinemáticas de Markland (criterios de la documentación de Dips) | Secondary |
| Fisher1953-set-statistics | Estadística de Fisher de una familia de discontinuidades (según Tauxe et al.) | Secondary |
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

## Cómo citar

Si RockMassPy te sirve en tu trabajo, cítalo. GitHub muestra el botón «Cite this repository», armado desde
[CITATION.cff](https://github.com/Miqueas7/RockMassPy/blob/main/CITATION.cff):

> Quintanilla Ventura, M. (2026). *RockMassPy: rock mass classifications, Hoek-Brown strength and mining
> geomechanics* (versión 0.2.0) [Software]. https://github.com/Miqueas7/RockMassPy

Cada resultado registra además el método y la edición que sigue (`result.info`); cita también esa fuente original.

Licencia: MIT.
