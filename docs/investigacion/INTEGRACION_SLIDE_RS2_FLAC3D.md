# Integración de Slide2, Phase2/RS2 y FLAC3D en RockMassPy

Investigación y propuesta del 14-nov-2026. No incluye código. La pidió Miqueas a través de la sesión Asistente,
después de la sesión 4 del Módulo 9 de GEOMINA. Para hacerla usé solo la web, documentos públicos y el código del
repositorio. No leí ninguna carpeta de clientes.

Antes de programar cualquier punto de este documento, hay que pasar por *brainstorming* y tener un diseño aprobado
por Miqueas, como en las fases anteriores.

**Marcas:** [V1] = lo leí en el documento original; [V2] = sale de un resumen automático de la página oficial o de
una fuente secundaria seria; [NV] = no está verificado (es de memoria o de un extracto del buscador). Ninguna cifra
[NV] sirve como oráculo de prueba.

---

## 1. Resumen en diez líneas

1. **No se replican los solucionadores.** Ni el FEM de RS2, ni el FDM explícito de FLAC3D, ni la SSR. La idea base de
   la sesión Asistente se mantiene.
2. **Esto sería la Fase 8, no la 5.** Las fases 5 (mina sintética), 6 (publicación) y 7 (curvas continuas e
   incertidumbre) ya existen.
3. **Hay que tocar el diseño aprobado.** El §3 del diseño pone como «no objetivo» los elementos finitos o diferencias
   finitas, las deformaciones y los esfuerzos in situ tipo Unwedge, con la marca (C). Las piezas 8B y 8C de abajo
   necesitan que Miqueas cambie esa línea.
4. **Slide2 ya está casi cubierto por la Fase 3.** Falta leer sus resultados y pasarlos por los criterios de la 3D,
   que ya reciben un FS por análisis.
5. **Con RS2 (antes Phase2) se gana más por las soluciones analíticas que por leer sus archivos.** Son Kirsch y la
   convergencia-confinamiento con Mohr-Coulomb y Hoek-Brown, junto con el perfil longitudinal y las curvas de los
   sostenimientos. Todas se validan **hoy** con el manual público de verificación de RS2 y el de RocSupport, sin
   licencias.
6. **FLAC3D solo corre Python dentro del programa.** Su módulo `itasca` no se instala con pip. Lo que conviene es un
   guion corto que el usuario corre dentro de FLAC3D y que escribe el formato largo que lee RockMassPy.
7. **Rocscience publica clientes oficiales en PyPI con licencia MIT:** `RS2Scripting` (11.30.0, 12-ago-2026) y
   `Slide2Scripting` (1.0.2, 10-nov-2026). Necesitan el programa instalado y con licencia. No deben entrar como
   dependencia, solo como ejemplos opcionales.
8. **El lector debe ser genérico, con columnas mapeables, y no atarse a cada formato.** Los formatos de exportación
   cambian con la versión y no hay muestras públicas de todos. Los preajustes por programa y versión se agregan
   cuando haya una muestra real.
9. **Modelo sustituto del FS:** se puede armar con la infraestructura de la Fase 4 (numpy y scipy, validación
   agrupada, incertidumbre de la Fase 7), sin agregar dependencias. Tiene que declarar cuándo está fuera de su dominio.
10. **Orden que recomiendo:** 8B analíticas → 8A lectores y comparación → 8C elementos de contorno → 8D sustituto. La
    8B y la 8C se validan ya; la 8A y la 8D necesitan exportaciones (pueden ser del curso).

---

## 2. Lo que ya existe y se reutiliza

| Pieza actual | Dónde está | Qué aporta a la Fase 8 |
|---|---|---|
| Hoek-Brown (`hb_params`, `hb_sigma1`, `hb_mohr_coulomb`, `hb_sigma3max`, `em_hoek2002`, Hoek-Diederichs) | `include/rockmasspy/hoek_brown.hpp` | Resistencia y módulo del macizo para la convergencia-confinamiento y el *strength factor* |
| Equilibrio límite 2D, búsquedas, Sarma, ky, Newmark (Fase 3C/3D) | `limit_equilibrium.py`, `slip_search.hpp`, `sarma.hpp`, `newmark.hpp` | Ya cubre lo que calcula Slide2. Sirve para comparar el FS que exporta Slide con el que calcula RockMassPy sobre la misma sección |
| `LeAnalysisResult` y `assess_criteria` | `limit_equilibrium.py:500`, `criteria.py:232` | Los criterios aceptan `blocks` y `le`, con las reglas `slope_fs_static`, `slope_fs_pseudostatic`, `slope_pof` y `berm_reliability`. Un FS importado puede entrar como un tercer tipo de objeto (p. ej. `ext`) con las mismas reglas |
| Perfiles de criterios versionados y tabla propia `Criterios` | `profiles/*.json`, `load_criteria_table` | Read y Stacey 2009, NDEP, DMIRS y Ryan-Pryor ya están; los criterios subterráneos (convergencia, *strength factor*) irían en la tabla propia |
| Catálogo de sostenimiento (`Bolt`, `Shotcrete`, `SupportType`) | `support.py` | Base de la 8B. Hoy guarda geometría (longitud, espaciamiento, espesor) pero **no la capacidad ni la rigidez**, que las curvas del sostenimiento necesitan. Hay que agregar campos opcionales |
| Monte Carlo y LHS (`probabilistic.py`, `uncertainty.py`) | Fase 3B y Fase 7 | Propagar la incertidumbre a la convergencia y obtener la PoF con un sustituto |
| Validación agrupada y estados como `not_calibrated` | `predictive/validation.py`, `predictive/correlations.py` | Validar el sustituto por escenario o sección, no por fila (es el antiobjetivo del §3), y negarse fuera del dominio |
| Lectura de CSV con formato numérico dinámico y Excel | `csv_io.py`, `excel_io.py`, `table_io.py` | El lector del formato largo y el mapeo de columnas |
| Informe Word/HTML y CLI con códigos 0/1/2 | `report/`, `cli.py` | Una sección nueva en el informe y uno o dos subcomandos |

**Conclusión:** la 8A es sobre todo Python (lectura, esquema, criterios, informe). La 8B y la 8C van al núcleo C++,
como Hoek-Brown y el equilibrio límite. La 8D vive en `predictive/`.

---

## 3. Qué entrega cada programa y cómo leerlo

Regla: **nunca descifrar binarios** (`.slmd`, `.fez`, `.f3sav`, archivos de resultados). Solo se usa lo que el
fabricante documenta como exportación de texto o como API.

### 3.1 Slide2

| Vía | Qué entrega | Marca |
|---|---|---|
| *Export Raw Data* (menú Data) | Texto (`.txt`) o portapapeles, **por cada método elegido**: centro o eje, radio (solo circulares), intersecciones con el talud y FS de **cada** superficie. Si un FS falla, escribe un código negativo (−101, −102, −103…) | [V2] |
| *Query Slice Data* | Datos por dovela de una superficie (copiar a Excel) | [V2] |
| Probabilístico: *Export Statistics Data*, gráficos a Excel | Muestras y estadísticos del FS | [V2] |
| `Slide2Scripting` (PyPI, MIT, 1.0.2 del 10-nov-2026; pide Python ≥ 3.11 y Slide2 ≥ 9.045) | Abrir, modificar, calcular y leer resultados en tablas (`Slide2Interpreter`, `InterpretData`, `InterpretQuery`, `StatisticsData`, `ProbabilisticStatistics`). Si no se usa la última versión de Slide2, la librería se fija a la versión que le corresponde | [V2] |

**Cómo cambia con la versión.** Antes de Slide2 9.045 no hay API. Solo están las exportaciones de la interfaz, y
Slide 6 (2010) no tiene ni esa API ni el cliente de PyPI [NV]. La librería tiene cuatro días en PyPI: puede cambiar.

**Qué falta en RockMassPy:** solo el lector y la comparación. El cálculo ya existe en la Fase 3.

### 3.2 Phase2 / RS2

Phase2 cambió de nombre a RS2 en la versión 9 (alrededor de 2015) [NV en el año]. Los archivos son `.fez` en las dos.

| Vía | Qué entrega | Marca |
|---|---|---|
| *Export Value at All Nodes* (File › Export) | CSV con el valor del contorno activo en cada nodo de la malla (una magnitud por exportación: *strength factor*, σ1, desplazamiento total…) | [V2] |
| *Plot in Excel* y *Copy Data* | Los datos de un gráfico (línea de consulta, historia) a Excel o al portapapeles | [V2] |
| *Export Query to Excel* | Solo después de un análisis probabilístico | [V2] |
| `RS2Scripting` (PyPI, MIT, 11.30.0 del 12-ago-2026; pide RS2 ≥ 11.023 y la librería con la **misma versión** que RS2; Python > 3.7, la más probada es la 3.11.4) | `InterpreterModel`: `GetMeshResults`, `GetHistoryQueryResults`, `GetAllTimeQueryPointResults`, `GetAllTimeQueryLinesResults`, `GetMaterialQueryResults`, `GetBoltResults`, `GetLinerResults`, `GetJointResults`, `GetCompositeResults`, `GetStructuralResults` (por etapa), `getCriticalSRF`, `SetActiveStage`, `SetResultType` | [V2] |

**Qué conviene leer de RS2:** el SRF crítico (el FS de la SSR), los puntos y líneas de consulta (*strength factor*,
desplazamientos, σ1 y σ3) por etapa, y las fuerzas en pernos y revestimiento. Con eso RockMassPy puede comparar
escenarios contra criterios y contra la convergencia analítica de la 8B.

### 3.3 FLAC3D

| Vía | Qué entrega | Marca |
|---|---|---|
| Python **integrado** (módulo `itasca`) | `it.zone.list()`, `z.stress()`, `z.strain()`, `z.pos()`, `z.group()`; `it.gridpoint.list()`, `gp.disp()`, `gp.pos()`; por arreglos: `itasca.zonearray` y `itasca.gridpointarray` (`pos()`, `disp()`, `gridpoints()`) devuelven arreglos de numpy | [V2] |
| `zone export` | Archivo de **malla** `.f3grid` en ASCII (por omisión) o binario. Trae zonas, nodos y grupos, **sin resultados** | [V2] |
| Historias y tablas (`history export`, `table`) | Series por paso o por etapa | [NV] (la página de Itasca devolvió 403) |
| Paquete `itasca` de PyPI (J. Furtney, BSD, 2020.7.12) | Conexión por *socket* y lectura de binarios FISH. **No es oficial** y lleva seis años sin cambios | [V2] |

**Cómo cambia con la versión.** La API de arreglos cambia entre versiones: la 9.6 trae `zone field`, que las
anteriores no tienen [V2]. El Python integrado está desde FLAC3D 6 o 7 [NV].

**Qué conviene hacer:** un guion de unas 40 líneas, escrito por nosotros y publicado en `examples/`, que corre
**dentro** de FLAC3D. Usa `zonearray` y `gridpointarray` y escribe el formato largo de la §4.1: desplazamiento por
nodo y por etapa, esfuerzos y estado por zona, y grupos. RockMassPy no importa `itasca`.

---

## 4. Propuesta por pieza

### 8A · Esquema común, lectores, comparación de escenarios contra criterios e informe

**Qué es.** Un formato largo único, y lectores que llevan a él lo que exportan Slide2, RS2 y FLAC3D, o cualquier
CSV con las columnas mapeadas. Encima van la comparación de escenarios, los criterios y una sección del informe.

#### 4.1 Esquema largo propuesto (borrador para el diseño)

Una fila por objeto, magnitud, etapa y escenario:

| Columna | Ejemplo | Nota |
|---|---|---|
| `programa`, `version` | `RS2`, `11.024` | Se registra siempre (principio de «la edición») |
| `modelo`, `escenario`, `etapa` | `S1`, `kh0.10`, `3` | El escenario es la unidad de comparación |
| `objeto`, `id` | `seccion`, `punto`, `linea`, `nodo`, `zona`, `perno`, `revestimiento` | |
| `x`, `y`, `z`, `distancia` | | Las coordenadas son opcionales; `distancia` sirve para las líneas de consulta |
| `magnitud` | `fs`, `srf`, `strength_factor`, `u_total`, `ux`, `sigma1`, `sigma3`, `estado_plastico`, `fuerza_axial` | Lista cerrada y en inglés en la API |
| `metodo` | `bishop`, `spencer`, `gle`, `ssr` | Sobre todo para los FS |
| `valor`, `unidad` | | Las unidades se convierten al entrar, como hoy |
| `archivo`, `hash` | | Trazabilidad sin copiar el binario |

Los preajustes (*presets*) por programa traducen las columnas reales de cada exportación. Solo se escriben cuando
hay una **muestra real** de esa versión, y la muestra no entra al repositorio (§7). Sin un preajuste, el usuario
mapea las columnas como hoy en las tablas.

#### 4.2 Dónde encaja

- **Criterios:** se agrega un tipo de objeto `ext` a `assess_criteria` y a `criteria_assignments`, con las mismas
  reglas `slope_fs_*` y `slope_pof`.
  - **Aviso obligatorio:** un SRF de SSR (RS2 o FLAC) no es el mismo número que un FS de equilibrio límite. Read y
    Stacey (2009) escriben sus umbrales para FS sin distinguir el método [NV en el texto exacto]. El chequeo debe
    llevar el método en la nota, y el perfil puede decidir si acepta `ssr`.
- **Comparación:** con la misma sección, comparar el FS de Slide contra el de `limit_equilibrium.py`. La diferencia
  esperable entre programas, según la encuesta ACADS, ronda el 2 %, que ya es la tolerancia de las pruebas.
- **Subterráneo:** convergencia y *strength factor* por etapa contra la tabla propia `Criterios`. No hay un perfil
  internacional único para estos valores.
- **Informe y CLI:** una sección «Resultados de modelos externos» y un subcomando (nombre por decidir; p. ej.
  `rockmass ext`).

**Qué no hace:** no convierte un modelo de Slide en uno de RockMassPy (eso sería leer el `.slmd`) y no dibuja los
contornos de la malla. Una figura de puntos y líneas de consulta sí es posible.

### 8B · Excavaciones subterráneas analíticas (sostenimiento)

**Dónde encaja.** Es una ampliación de la Fase 2, que trata de sostenimiento, y no una fase aparte. Propongo un
archivo nuevo en el núcleo (`include/rockmasspy/excavation.hpp`) y uno en Python que lo use junto con
`support.py`. Contenido:

1. **Kirsch:** esfuerzos alrededor de un hueco circular con K arbitrario, en el contorno y en el campo. Se suma el
   contorno de una elipse (Inglis; Brady y Brown), útil para la concentración de esfuerzos en labores reales.
2. **Curva de reacción del terreno (GRC):**
   - Mohr-Coulomb elástico-perfectamente plástico (Salençon 1969; Duncan Fama 1993);
   - Hoek-Brown (Hoek y Brown 1982 con a = 0.5; Carranza-Torres y Fairhurst 2000; Hoek-Brown generalizado,
     Carranza-Torres 2004);
   - frágil-plástico, opcional (Reed 1986).
3. **Perfil longitudinal (LDP):** Panet (1995) y Vlachopoulos y Diederichs (2009). Este último depende del radio
   plástico y es el que RocSupport usa por omisión [V2].
4. **Curvas características del sostenimiento (SCC):** pernos, shotcrete y cimbras, con su capacidad y su rigidez
   (Hoek y Brown 1980; Carranza-Torres y Fairhurst 2000; Oreste 2003 [NV en las ecuaciones]). Se combinan y se
   obtiene el FS del sostenimiento en el cruce GRC–SCC.
5. **Squeezing:** clase de deformación según Hoek y Marinos (2000), con la deformación en función de σcm/p0. Une el
   GSI y Hoek-Brown que ya existen con la decisión de sostenimiento [V2 en la fórmula, por verificar].
6. Monte Carlo sobre GSI, σci y p0 con `uncertainty.py`: da la probabilidad de que el sostenimiento quede corto.

**Límite que hay que declarar:** túnel circular, esfuerzo hidrostático y deformación plana. Es lo mismo que limita a
RocSupport [V2]. Para labores no circulares o con K ≠ 1, la herramienta es la 8C o RS2.

### 8C · Elementos de contorno 2D elásticos (estilo Examine2D)

**Qué es.** Un método indirecto de elementos de contorno (desplazamiento discontinuo o esfuerzo ficticio, de Crouch
y Starfield 1983) en el núcleo C++. Calcula los esfuerzos elásticos en deformación plana alrededor de una o varias
excavaciones de forma libre, y con ellos el *strength factor*: la resistencia de Hoek-Brown o Mohr-Coulomb entre el
esfuerzo inducido.

**Por qué en C++:** es una matriz densa de N×N (N = elementos del contorno, pocos cientos) y el cálculo en una
grilla de puntos. Encaja con el núcleo actual.

**Usos mineros:** pilares entre tajeos, la interacción entre labores cercanas y las zonas de sobreesfuerzo para
ubicar el sostenimiento.

**Límite:** es elástico, de un solo material y sin etapas. No reemplaza a RS2, como tampoco lo hace Examine2D [V2].

### 8D · Modelo sustituto del FS (o del desplazamiento)

**Qué es.** Un modelo que aprende el FS (o el desplazamiento) a partir de **corridas** de Slide, RS2 o FLAC3D en
función de los parámetros (c, φ, GSI, kh, nivel freático, geometría). Sirve para barridos y para la PoF sin volver
a correr el programa.

**Dónde encaja:** en `predictive/`, con la misma disciplina de la Fase 4.
- **Modelos sin dependencias nuevas:** superficie de respuesta polinomial e interpolación RBF
  (`scipy.interpolate.RBFInterpolator`), dentro del extra `[ml]`.
- **Validación:** agrupada por escenario o sección, nunca por fila al azar.
- **Dominio:** un chequeo de dominio (envolvente convexa o distancia de Mahalanobis) devuelve un estado como
  `out_of_domain`, igual que el `not_calibrated` que ya existe.
- **PoF:** sale de pasar por el sustituto la LHS de la Fase 7.

**Advertencias:**
- No extrapola.
- No reemplaza la corrida final.
- El banco de pruebas debe comparar contra una verdad conocida. Es la lección de la Fase 4: se generan las «corridas»
  con el propio equilibrio límite de la Fase 3, donde el FS verdadero es exacto, antes de usar corridas de otros
  programas.

---

## 5. Validación sin licencias

| Caso | Fuente pública | Sirve para | Marca |
|---|---|---|---|
| Hueco cilíndrico en medio elástico infinito (Kirsch) | RS2 *Stress Verification Manual* (Rocscience 2021), problema 1; Jaeger y Cook (1976) | 8B Kirsch, 8C | [V1] (índice y referencias leídos) |
| Hueco cilíndrico en Mohr-Coulomb | RS2 Stress, problema 2; Salençon (1969); Itasca (1993) | 8B GRC MC | [V1] |
| Hueco cilíndrico en Hoek-Brown | RS2 Stress, problema 3; Hoek y Brown (1982); Itasca (1993) | 8B GRC HB | [V1] |
| Túnel revestido en medio elástico | RS2 Stress, problema 7; Einstein y Schwartz (1979) | 8B SCC del revestimiento | [V1] |
| Túnel revestido en medio plástico | RS2 Stress, problema 11 (Drucker-Prager, campo biaxial) | Referencia; probablemente fuera del alcance analítico | [V1] |
| Esfuerzo a lo largo de un perno inyectado | RS2 Stress, problema 20; Farmer (1975), Hyett et al. (1996) | 8B pernos (opcional) | [V1] |
| Túnel reforzado con pernos | RS2 Stress, problema 21; Carranza-Torres (2002, 2009) | 8B SCC de pernos | [V1] |
| Hueco en medio frágil-plástico MC | RS2 Stress, problema 30; Reed (1986) | 8B frágil-plástico | [V1] |
| Hueco en medio transversalmente isótropo | RS2 Stress, problema 8 | Fuera del alcance (anisotropía) | [V1] |
| GRC de Hoek-Brown con ablandamiento | RocSupport *Verification Manual* v4, problema 4; Lee y Pietruszczak (2008) frente a Carranza-Torres (2004) | 8B HB generalizado | [V1] |
| GRC de Duncan Fama frente a Phase2 | RocSupport, problema 5 | 8B MC | [V1] |
| Grandes deformaciones (Vrakas y Anagnostou 2013, 2014) | RocSupport, problemas 1 a 3 | Fuera del alcance (deformación finita); sirve de advertencia | [V1] |
| Ejemplo resuelto y hoja de cálculo de la GRC con Hoek-Brown | Carranza-Torres y Fairhurst (2000), *TUST* 15(2), 187-213 | 8B | [V2] |
| LDP | Vlachopoulos y Diederichs (2009), *RMRE* 42, 131-146, doi:10.1007/s00603-009-0176-4 | 8B | [V2] |
| Esfuerzos en el contorno de una elipse y de huecos múltiples | Brady y Brown, *Rock Mechanics for Underground Mining* (cap. 7) | 8B y 8C | [NV] (consultar la edición que tenga Miqueas) |
| *Strength factor* con Examine2D | Laboratorio 8 de EOSC 433 (UBC), pilar entre excavaciones | 8C | [V2] |
| FS por equilibrio límite frente a Slide | Manual de verificación de Slide2 (ya usado en la Fase 3) | 8A comparación | [V1] (Fase 3) |

Los PDF de RS2 Stress y de RocSupport quedaron en `docs/investigacion/pdfs/`, que está fuera de git. Rocscience
también publica los modelos de verificación (`RS2_Stress-Analysis-Verification.zip`, archivos `.fez`), pero sin
licencia no se pueden abrir y no hacen falta: las entradas están en el manual.

**Lo que se valida ya:** todo lo de la 8B y la 8C. La comparación de la 8A con el equilibrio límite propio también.
**Lo que necesita exportaciones reales:** los preajustes de los lectores de la 8A y la validación de la 8D con
corridas de otros programas.

---

## 6. Librerías abiertas y propiedad intelectual

| Proyecto | Qué es | ¿Duplica? | Marca |
|---|---|---|---|
| `onurkoc/ground-curve` (GitHub, MIT) | GRC en Python, con shotcrete por el método de tasa de flujo | Parcial: no cubre Hoek-Brown generalizado ni el LDP. Solo para comparar | [V2] (sin revisar el código) |
| Arif Yunando, blog «Convergence Confinement Method» (2024) | Notas y código de ejemplo | No es una librería | [NV] |
| BigWham (EPFL) | Elementos de contorno por desplazamiento discontinuo con matrices jerárquicas; API en Python | Está pensada para fracturas hidráulicas y en 3D, no para el *strength factor* minero. Es pesada como dependencia | [V2] (licencia sin revisar) |
| TWODD (MATLAB, cursos de la Univ. de Hawái) y Vinci.js | Desplazamiento discontinuo 2D de Crouch y Starfield | Material de enseñanza. Se puede leer el método, pero se escribe código propio (revisar la licencia antes de mirar el código) | [V2] |
| Bempp-cl, PyBEM2D | BEM general (Laplace, Helmholtz) | No sirve para elasticidad minera | [V2] |
| `RS2Scripting`, `Slide2Scripting` (MIT, Rocscience) | Clientes oficiales | Son complemento, no duplican: solo se usan en ejemplos opcionales | [V2] |
| `itasca` (PyPI, BSD, 2020) | *Socket* y archivos FISH | No es oficial y está detenido. No usarlo | [V2] |

**Propiedad intelectual** (sigue la regla 4 del `CLAUDE.md`):
- Las soluciones analíticas (Kirsch, Salençon, Hoek-Brown, Carranza-Torres) son métodos publicados. Entran como
  ecuaciones citadas.
- El método de elementos de contorno de Crouch y Starfield es un algoritmo de libro. Se escribe desde las ecuaciones,
  sin copiar el código de nadie.
- No se reproduce la lógica interna de Examine2D ni de RocSupport (por ejemplo, sus valores por omisión no
  publicados).
- Los números de los manuales de Rocscience se usan solo como oráculo de prueba citado, sin copiar figuras ni texto,
  como ya se hizo con Slide2 en la Fase 3.
- El guion de FLAC3D llama a la API documentada de Itasca. Es nuestro y no reproduce código de Itasca.

---

## 7. Datos de clientes

- Las exportaciones reales que consiga Miqueas pueden ser de clientes: viven en la carpeta protegida de cada mina, se
  miran **solo** con el lector seguro (`inspeccionar.py`) y nunca entran al repositorio.
- Para escribir un preajuste hace falta conocer **la cabecera y el formato** de la exportación, no sus valores. El
  lector seguro da nombres de columnas, tipos y conteos, y con eso basta.
- **La mejor fuente de muestras son los archivos del Módulo 9 de GEOMINA, si salen de modelos de enseñanza
  sintéticos.** Los datos de docencia no tienen restricción. Miqueas confirma de dónde salieron.
- Las pruebas del repositorio usan archivos sintéticos con el mismo formato, escritos por nosotros.

---

## 8. Esfuerzo y orden recomendado

| Subfase | Contenido | Esfuerzo (sesiones como las de las fases 2 y 3) | ¿Se valida ya? |
|---|---|---|---|
| **8B** | Kirsch, elipse, GRC MC y HB, LDP, SCC, squeezing, Monte Carlo, informe y CLI | 2 a 3 | **Sí** (RS2 Stress 1, 2, 3, 7, 21, 30; RocSupport 4 y 5) |
| **8A** | Esquema largo, mapeo de columnas, tipo `ext` en los criterios, comparación con la Fase 3, informe y CLI; guion de FLAC3D y ejemplos con los clientes de Rocscience | 2 (genérico); preajustes, medio día cada uno cuando haya muestra | La lógica sí; los preajustes no |
| **8C** | Elementos de contorno 2D, *strength factor*, varias excavaciones, figura de contornos | 2 a 3 | **Sí** (Kirsch, elipse, Examine2D/UBC) |
| **8D** | Sustituto (polinomio, RBF), dominio, validación agrupada, PoF con LHS | 1 a 2 | Con un banco propio sí; con corridas externas no |

**Por qué este orden y no el de la sesión Asistente (8A primero):**
- La 8B tiene el mayor valor para la minería subterránea peruana. Se une al sostenimiento, que es el centro del
  proyecto, y se valida hoy sin depender de nadie.
- Si la 8A va primero, sus preajustes quedan esperando muestras.
- Si Miqueas prefiere la 8A primero por el curso, se puede hacer su parte genérica y dejar los preajustes para
  después. No cambia la arquitectura.

---

## 9. Decisiones que necesito de Miqueas

1. **Cambiar el §3 del diseño:** sacar de los «no objetivos» las soluciones analíticas de excavaciones (8B) y el BEM
   elástico (8C), y dejar FEM, FDM y SSR como no objetivo, pero **leíbles** (8A).
2. **Nombre y numeración:** «Fase 8» y el orden 8B → 8A → 8C → 8D, o el orden de la sesión Asistente.
3. **Muestras de exportación:** ¿los archivos del Módulo 9 son sintéticos y se pueden usar como muestra de formato?
   ¿Qué versiones de Slide2, RS2 y FLAC3D se usaron?
4. **SRF frente a FS:** ¿un perfil de criterios acepta el SRF de la SSR como FS, con aviso, o lo deja «no
   verificable»?
5. **Campos nuevos en el catálogo de sostenimiento** (capacidad, rigidez, resistencia del shotcrete, perfil de la
   cimbra): ¿opcionales en la misma hoja o en una hoja aparte?

---

### 9.1 Respuestas de Miqueas (14-nov-2026)

1. **§3 del diseño: sí.** Ya está cambiado en el diseño (§3 y §12).
2. **Orden: sí,** 8B → 8A → 8C → 8D.
3. **Los archivos del Módulo 9 son sintéticos,** pero hay que investigar tesis para conocer los datos reales; las
   tesis son importantes aquí. → §12.
4. **SRF frente a FS: investigarlo.** → §11.
5. **Campos del sostenimiento: en una hoja aparte** del catálogo.

---

## 11. ¿Un SRF de reducción de resistencia vale como FS ante los criterios?

### 11.1 Lo que dice la literatura

| Hallazgo | Fuente | Marca |
|---|---|---|
| **Los criterios están escritos para «FoS» sin restringir el método.** No encontré ninguna fuente que diga que la tabla 9.9 de Read y Stacey (2009), escrita por Wesseloo y Read, vale solo para equilibrio límite. El libro trata el diseño con equilibrio límite y con modelos numéricos. El texto exacto del capítulo no se leyó (es de pago) | Moffitt (2023), que reproduce la tabla 9.9; búsqueda sin resultado contrario | [NV] en el texto del capítulo |
| **Con supuestos equivalentes, la SSR reproduce el FS de equilibrio límite dentro de ~5 %.** Hay que usar el mismo E para todos los materiales, un solo ν, dilatancia 0 y comportamiento elástico-perfectamente plástico. En 27 casos de verificación de Slide y Phase2, el SRF queda casi siempre igual o por debajo del FS de Spencer. Peores casos: con ru, 1.04 frente a 1.12 (−7 %); con nivel freático, 1.18 frente a 1.245 (−5 %); el caso 23 da 1.12 frente a 1.15–1.17 | Hammah, Yacoub, Corkum y Curran (2005), tabla 3 | [V1] |
| **Con rigideces muy distintas entre capas (hasta 1000 veces), el SRF va de −5 % a +11 % del valor de referencia.** La dilatancia (0°, 5°, 17.5°) mueve el FS menos del 5 % | Hammah et al. (2005), tablas 1 y 2 | [V1] |
| **Talud de Hoek-Brown (45°, 10 m):** SSR con HB generalizado 1.15; SSR con MC equivalente 1.15; Bishop 1.153; Spencer 1.152; 3DEC 1.16 | Hammah et al. (2005), reproducido por Itasca | [V2] |
| **En taludes de roca empinados, la SSR con c′/φ′ equivalentes de Mohr-Coulomb estima mal el FS** | Artículo de *Geosciences* (2022) en DOAJ, sin poder abrirlo | [NV] |
| **El equilibrio límite nunca es cota inferior,** así que FLAC3D puede dar un FS mayor o menor. Una diferencia no prueba que FLAC3D sea poco conservador. La SSR de FLAC3D encierra el FS entre dos valores con un error típico del 1 %; el último estado estable está unos 0.005 por debajo | Itasca, *FLAC3D Theory: Factor of Safety* | [V2] |
| **Con flujo no asociado (dilatancia baja y fricción alta), la SSR puede ser numéricamente inestable.** Un material no asociado nunca es más resistente que uno asociado | Tschuchnigg, Schweiger y Sloan (2015), *Géotechnique* 65(4), 249-257; Itasca | [V2] |
| **La SSR entrega una sola superficie** y no ve otras casi igual de críticas. Es sensible al solucionador cuando hay una banda blanda con fricción | Cheng, Lansivaara y Wei (2007), *Computers and Geotechnics* 34(3), 137-150 | [V2] (resumen) |
| **Con mallas finas, la SSR queda unos pocos por ciento sobre el análisis límite** | Dawson, Roth y Drescher (1999), *Géotechnique* 49(6), 835-840 | [V2] |
| **Ningún método es siempre más conservador.** La PoF del equilibrio límite llegó a ser hasta el doble que la numérica en algunos modelos y menor en otros. Las superficies numéricas son más profundas, porque incluyen la redistribución y la falla progresiva. La PoF numérica se obtiene con estimas puntuales (Rosenblueth) o con superficies de respuesta | Chiwaye y Stacey (2010), *J. SAIMM* 110, 571-580 | [V1] |

### 11.2 Recomendación para RockMassPy

**Sí se acepta, con aviso y con reglas.** Excluir el SRF dejaría fuera la práctica más común de los informes de
diseño. Las diferencias publicadas son del mismo orden que las que ya se toleran entre métodos de equilibrio límite
(±2 % en la encuesta ACADS) y que la dispersión de los parámetros. Las reglas:

1. **Cada FS lleva su método** (`bishop`, `spencer`, `gle`, `sarma`, `ssr`…) y el chequeo lo informa: «SRF (SSR),
   no FS de equilibrio límite».
2. **Política por perfil, también sobrescribible por el usuario,** como hoy `range_policy`:
   - `ssr_policy = "warn"` (por omisión): acepta y avisa;
   - `"accept"`: acepta sin avisar;
   - `"not_verifiable"`: el SRF no se evalúa.
   Los cuatro perfiles internacionales actuales arrancan en `"warn"`, porque ninguno restringe el método [NV].
3. **Banda de cercanía al umbral:** si el SRF queda a menos de un 5 % del umbral, el resultado se mantiene, pero pide
   atención (código 2). El 5 % sale de las diferencias de Hammah et al. (2005); es un valor **provisional y por
   confirmar**, igual que el margen del aviso de borde de la Fase 7.
4. **Metadatos de la SSR:** tolerancia de búsqueda, regla de flujo o dilatancia, criterio (HB generalizado o MC
   equivalente), malla y programa con su versión. Si falta alguno, sale un aviso, sin bloquear. Si la SSR usó **MC
   equivalente en un talud empinado de Hoek-Brown**, sale un aviso específico.
5. **Si la misma sección también tiene equilibrio límite** (de RockMassPy o de Slide), el informe muestra las dos
   cifras y avisa cuando difieren más del 10 %. La sección se juzga con la más baja, como ya hace `_lowest` con
   varios métodos.
6. **La PoF numérica** (por estimas puntuales, superficie de respuesta o sustituto 8D) entra por `slope_pof` con su
   método en la nota.
7. **Pseudoestático:** un SRF con kh sigue las mismas reglas que el equilibrio límite.
8. **En subterránea no hay un criterio internacional para el SRF.** Va solo en la tabla propia `Criterios`.

Esto se lleva al *brainstorming* de la 8A. Los valores provisionales son la banda del 5 % y el umbral del 10 % entre
métodos.

---

## 12. Tesis: casos para validar y cómo es la práctica

Se buscó el 14-nov-2026. Se abrieron 26 documentos públicos de repositorios de Perú, Colombia, México y Canadá. Los
PDF y sus textos están solo en el scratchpad de la sesión y no entran al repositorio. Las páginas son las impresas
en cada tesis.

### 12.1 Las fuentes más útiles

| Tesis | Programa | Labor | Qué publica completo | Sirve para | Marca |
|---|---|---|---|---|---|
| Soria Medina (2023), maestría UNAM, *Equivalencias 2D–3D en análisis tenso-deformacionales de túneles* ([PDF](https://ru.dgb.unam.mx/bitstream/20.500.14330/TES01000834385/3/0834385.pdf)) | RocSupport v5, RS2 v9 | Túnel circular | Todas las entradas de Mohr-Coulomb; desplazamiento y radio plástico con K0 = 1 y 0.5 | **8B**: caso limpio | [V1 + recalculado] |
| Rodríguez Paihua (2021), UNSCH ([ficha](http://repositorio.unsch.edu.pe/handle/UNSCH/4683)) | RocSupport, Phase2, RS2 v9.0 | Galería, rampa, tajeo | Tabla 4.1 de Hoek-Brown pico y residual (pp. 75-76); desplazamientos; momento del shotcrete | **8B** (conversión de Hoek-Brown y Erm) y caso de incoherencia | [V1 + recalculado] |
| García Aquino (2024), UNI ([ficha](https://repositorio.uni.edu.pe/handle/20.500.14076/28472)) | Phase2 (2010) | Acceso entre dos cuerpos minados | Triaxiales (tabla 25); Hoek-Brown por litología (tabla 32, p. 69); profundidad, K, σv y σh; SF por etapa | **8C** (semicuantitativo: la geometría solo está en planos) | [V1] |
| Riveros Mendoza (2024), maestría UNAP ([ficha](https://repositorio.unap.edu.pe/handle/20.500.14082/25394)) | RocSupport, Phase2, RocData | Cortada de 4.5 × 4.0 m | Hoek-Brown completo; espesor plástico; FS del sostenimiento | 8B, pero **no se reproduce** (§12.2) | [V1] |
| Fuentes Montesinos (2020), UNAP ([ficha](https://repositorio.unap.edu.pe/handle/20.500.14082/14540)) | Phase2 v8.0 | Túnel somero con cerchas y shotcrete | **Pares (M, N) de los diagramas de capacidad para FS 1, 1.5 y 2** (tabla 31, pp. 103-105) | **8A y 8B**: diagramas de capacidad del revestimiento | [V1] |
| Mercado y Obregón (2017), PUCP ([ficha](https://tesis.pucp.edu.pe/handle/20.500.12404/8712)) | Phase2 v7.0 | Labores de 4-5 m; corte y relleno con pilares | Factor de resistencia por clase RMR, sin y con sostenimiento (tabla 54) | 8D (referencia) y 8C | [V1] |
| Velásquez Ortiz (2021), maestría UNAL ([PDF](https://bffrepositorio.unal.edu.co/server/api/core/bitstreams/8d5100d6-0c21-4df6-8c46-30fd1f79d0fb/content)) | RS2 | Túnel vial | Convergencias diarias medidas (tabla 3-2) y RS2 con K de 1 a 3 | Monitoreo frente al modelo (8A) | [V1] |
| Langford (2013), doctorado Queen's ([ficha](https://qspace.library.queensu.ca/handle/1974/8291)) | Phase2 y convergencia-confinamiento analítico | Túnel de ejemplo; túnel Driskos | Tabla 5-4 con medias y desviaciones (p. 191); convergencias observadas frente al modelo (tabla 8-10) | **8B con incertidumbre, 8D** | [V1] (dos tablas desalineadas en el texto extraído) |
| Burgos Cedeño (2015), magíster U. de Chile ([ficha](https://repositorio.uchile.cl/handle/2250/134934)) | Phase2 con SSR | Galería de 16 m² | 162 casos (250-1000 m, K 1-2, σci 50-150 MPa, tres GSI, pernos) con su SRF | **8D**: el mejor banco para el sustituto | [V2] (el PDF está detrás de un filtro antibots) |
| Huaman Cangalaya (2023), PUCP ([ficha](https://tesis.pucp.edu.pe/handle/20.500.12404/25416)) | Slide frente a Abaqus (SSR) | Talud 2H:1V (caso de Griffiths y Lane) | FS de Spencer, M-P y Janbu frente a la SSR | §11 y 8A | [V1] |
| Rios Barreto (2026), UNI ([ficha](https://repositorio.uni.edu.pe/handle/20.500.14076/29751)) | Phase2 v8.024 | Tajeo de 3.5 × 4.5 m | Hoek-Brown por dominio; **pernos Swellex y shotcrete con los campos del diálogo de Phase2** (tabla 20) | Columnas de la hoja de sostenimiento | [V1] |
| Hancco Carrasco (2026), UNAP; Mango Alvarez (2024), UNSA | Phase2 | Tajeos y pilares de SLS | Triaxiales, GSI y profundidad; SF 1.14-1.58 | 8C (rangos) | [V1] |
| Cruz Ordoñez (2019), UNAP | Phase2 y SAP2000 | Túnel de 3 × 3 m | Presiones de 0.08-0.26 MPa; M, Q y N en la cimbra THN-29 frente a su capacidad | 8B (cimbras) | [V1] |

Revisadas pero de poca utilidad: Cortez y Cotrina (2022) y Valencia Chiroque (2026), porque sus entradas están solo
en figuras; Belizario-Calsin et al. (2020), porque la tabla de parámetros está en imagen.

### 12.2 Casos convertibles en pruebas

1. **Soria Medina (2023), pp. 18-22** [V1 + recalculado].
   - Entradas: R = 5 m; p0 = 4.05 MPa; Em = 446 MPa; ν = 0.3; c = 1 MPa; φ = 37°; ψ = 6°.
   - Resultados publicados: RocSupport da Rp = 5.86 m y u = 68.05 mm; RS2 da 5.84 m y 65.50 mm.
   - La solución cerrada de Mohr-Coulomb da **Rp = 5.857 m** (Kp = 4.023, σcm = 4.011 MPa, pcr = 0.814 MPa).
     Coincide.
   - Falta reproducir el desplazamiento con ψ = 6°.
   - El caso con K0 = 0.5 (bóveda y hastial distintos) sirve solo como referencia: la GRC analítica supone K = 1.
2. **Rodríguez Paihua (2021), tabla 4.1** [V1 + recalculado].
   - Entradas: σci = 135.79 MPa; mi = 32; Ei = 12 400 MPa.
   - Fila pico (GSI 35, D 0): mb = 3.14, s = 0.00073, a = 0.5159, Erm = 1406 MPa. Se reproduce con Hoek-Brown 2002
     y Hoek-Diederichs generalizado.
   - Fila residual (GSI 30): la tesis **declara D = 0.3, pero sus mb = 2.626 y s = 0.000419 salen con D = 0**. Con
     D = 0.3 saldrían mb ≈ 1.69 y Erm ≈ 687 MPa. Es un caso de prueba para el chequeo de coherencia (§12.5).
3. **García Aquino (2024), tabla 32 (p. 69)**: mb y s de las cuatro litologías se reproducen con D = 0. Sirve como
   prueba de conversión. Ojo: γ = 0.042 MN/m³ es una errata de la tesis. Valores [V1]:

   | Litología | σc (MPa) | GSI | mi | mb | s | a | Emr (MPa) | ν |
   |---|---|---|---|---|---|---|---|---|
   | SPP | 45 | 53 | 21.22 | 3.961 | 0.0054 | 0.505 | 11 920 | 0.25 |
   | SPB | 49 | 56 | 22.01 | 4.573 | 0.0075 | 0.504 | 15 093 | 0.25 |
   | Volcánico | 75 | 50 | 26.17 | 4.388 | 0.0039 | 0.506 | 9 340 | 0.23 |
   | Dique | 110 | 53 | 28.98 | 5.409 | 0.0054 | 0.505 | 11 920 | 0.24 |

   Comprobación (14-nov): mb = 21.22·e^((53−100)/28) = 3.9605 y s = e^(−47/9) = 0.00539. Emr sale con Hoek-Diederichs
   simplificado: 100 000/(1 + e^((75 − 53)/11)) = 11 920.
4. **Fuentes Montesinos (2020), tabla 31**: pares (M, N) de la envolvente de capacidad del shotcrete y de la cercha
   H-1.
   - Dos valores son incoherentes dentro de la propia tabla: el M del codo con FS = 2 y la tensión con FS = 1.
   - Antes de usarla hay que confirmar b, t y f′c en el PDF.
   - Una errata nunca es el valor esperado (regla 2).
5. **Langford (2013), tabla 5-4**.
   - Entradas: GSI 60 ± 2, UCS 52 ± 9 MPa, mi 13 ± 3, MR 250, σ0 = 10 MPa, R = 5 m.
   - Es un caso de convergencia-confinamiento con Hoek-Brown y Monte Carlo o PEM, pero los resultados están en
     histogramas: sirve para comparar distribuciones, no un número.
6. **Riveros Mendoza (2024)**: **no se reproduce.** Publica un espesor plástico de 0.93 m. Con Carranza-Torres
   (a = 0.5) se estiman unos 1.67 m y con Mohr-Coulomb equivalente unos 1.75 m. Faltan ν, la presión interna y el
   método que usó. No se usa como prueba.

### 12.3 Rangos típicos de la práctica peruana [V1, de las tesis abiertas]

| Parámetro | Rango observado | Nota |
|---|---|---|
| GSI | 20-45 en tajeos y labores con problemas; 45-60 en accesos y tajeos de SLS | Regla común: GSI = RMR89 − 5, o GSI = RMR en condición húmeda |
| σci | 33-155 MPa (lo más frecuente, 45-135) | A veces sale del martillo Schmidt o de la picota, no del laboratorio |
| mi | 18-32 en intrusivos y volcánicos | Sale de triaxiales ajustados en RocData |
| D | Casi siempre 0; también 0.2, 0.3 y 0.8 | **A veces está implícito y no se declara (≈ 0.7)** |
| K | 0.25-0.48 cuando sale de la medición o de Sheorey; 1.0-1.5 cuando se supone | **Es frecuente que el K del estudio no coincida con el del modelo** |
| Profundidad | 210-800 m; γ ≈ 0.027 MN/m³ | |
| Sostenimiento | Swellex o helicoidal de 2.1 m a 0.9-1.8 m; shotcrete de 50-100 mm con fibra de 40 kg/m³; cimbras 6W20 o THN-29 a 1-1.5 m; cable bolting en tajeos | |
| Criterios usados | SF o FS ≥ 1.1-1.5 en Phase2; FS ≥ 1.4-1.5 en Unwedge; taludes y botaderos 1.3-1.5 estático y 1.0-1.1 pseudoestático (guía del MINEM, 2017) | La guía del MINEM es candidata a perfil [NV] |

### 12.4 Cómo se reporta (insumo para la 8A)

- **Versiones citadas:** Phase2 7.0 a 8.024, RS2 9, RocSupport 3.0 y 5, RocData 3.0 y 4.0, Examine 8.0, FLAC3D 7.00,
  Slide y Slide2. Ninguna tesis usa los clientes de Python.
- **Ninguna tesis publica una exportación** (CSV, Excel, `.fez`). Los resultados son capturas de contornos (*Strength
  Factor*, *Yielded Elements*, *Total Displacement*, σ1) con el máximo o el mínimo citado en el texto.
- **Las tablas de entrada copian el formato de RocData** (σci, GSI, mi, mb, s, a, Erm, ν, γ) y los diálogos de
  sostenimiento de Phase2:
  - pernos: *Bolt Type*, *Tensile Capacity* (MN), *Bond Strength* (MN/m), *Out-of-plane Spacing*;
  - revestimiento: *Liner Type*, *Thickness*, *Young's Modulus*, *Poisson's Ratio*, resistencias a compresión y
    tracción, peso unitario.
- **Diagramas de capacidad** como pares (M, N) por FS, con el formato del *Support Capacity Plot* de RS2.
- **Unidades mezcladas** (MN/m³, kN/m³, t/m³; kg·m, MN·m), coma decimal y erratas en γ.

### 12.5 Lo que esto cambia en la propuesta

1. **La hoja aparte de sostenimiento** (decisión 5) usa los nombres del diálogo de Phase2/RS2 como encabezados
   reconocidos, en inglés y en español. Así una tabla copiada de una tesis o de un informe entra sin remapear.
2. **8B: diagramas de capacidad del revestimiento** (Carranza-Torres y Diederichs 2009, como en RS2). Calcula las
   envolventes (M, N) por FS para el shotcrete y las cimbras y verifica las fuerzas actuantes. Fuentes Montesinos y
   Cruz Ordoñez lo usan; no estaba en la propuesta.
3. **Chequeo de coherencia de Hoek-Brown** (8B o el `verify` de la 2C):
   - recalcular mb, s, a y Erm desde GSI, mi y D, y avisar si no coinciden con lo declarado (Rodríguez Paihua) o si
     el D implícito difiere del declarado (Rios Barreto);
   - avisar si el K del modelo difiere del K del estudio.
   Son errores reales y frecuentes que la librería puede atrapar.
4. **8A:** el lector más útil hoy **no es de exportaciones sino de tablas de entrada y salida** como las de las
   tesis (RocData, diálogo de sostenimiento, valores máximos por etapa). Además normaliza unidades, acepta la coma
   decimal y lee pares (M, N).
5. **8D:** el banco de Burgos Cedeño (162 SRF en una grilla de profundidad, K, σci, GSI y pernos) es el caso ideal
   para probar el sustituto. Hace falta que Miqueas baje el PDF a mano (repositorio de la U. de Chile).
6. **Monitoreo frente al modelo** (Velásquez Ortiz, Langford): cabe en la 8A como «convergencia medida frente a la
   calculada», con la convergencia analítica de la 8B como referencia.

### 12.6 Huecos

- **No hay ninguna tesis con datos completos de Examine2D.** La 8C se valida con Kirsch, la elipse y los manuales de
  Rocscience.
- **No hay casos peruanos del LDP de Vlachopoulos y Diederichs ni de squeezing de Hoek y Marinos.**
- **No hay ninguna comparación directa de Slide con RS2 en un tajo peruano.**
- **Repositorios bloqueados:**
  - U. de Chile y U. Continental tienen un filtro antibots, que no se evadió;
  - core.ac.uk tiene un desafío de Cloudflare;
  - UNI y PUCP devuelven 401 en Quispe Aronés, Bazalar Gamarra (2011, modelos numéricos en túneles), Villalobos
    Suazo, Santos Chauca y Pehovaz;
  - las APIs de UNASAM, UNDAC, UNMSM y UNC no respondieron.
  - Si Miqueas los consigue a mano, se revisan.
- **Sigue sin abrir** la tesis del tajo Seductora.
- **Ruta técnica para DSpace 7:** `/server/api/pid/find?id=<handle>`, luego `/core/items/<uuid>/bundles`, luego
  `/bitstreams/<id>/content`. ALICIA tiene una API VuFind en `/vufind/api/v1/search`.

---

## 13. Fuentes

- Rocscience. (2021). *RS2 Stress Analysis Verification Manual* (193 pp.). [PDF](https://static.rocscience.cloud/assets/verification-and-theory/RS2/RS2-Stress-Verification.pdf). Índice de manuales: [verification manuals](https://www.rocscience.com/help/rs2/verification-theory/verification-manuals). [V1]
- Rocscience. *RocSupport Verification Manual*, versión 4.0. [PDF](https://www.rocscience.com/assets/verification-and-theory/RocSupport/RocSupport-Verification-Manual.pdf). [V1]
- Rocscience. *RS2 Python Reference Manual*: [rocscience.github.io/rs2-scripting](https://rocscience.github.io/rs2-scripting), [InterpreterModel](https://rocscience.github.io/rs2-scripting/generatedAPIDocFiles/rs2.interpreter.InterpreterModel.html); [PyPI RS2Scripting](https://pypi.org/project/RS2Scripting/). [V2]
- Rocscience. *Slide2 Python Reference Manual*: [rocscience.github.io/slide2-scripting](https://rocscience.github.io/slide2-scripting/); [PyPI Slide2Scripting](https://pypi.org/project/Slide2Scripting/); [Export Raw Data](https://www.rocscience.com/help/slide2/documentation/slide-interpret/import-export/export/export-raw-data). [V2]
- Rocscience. RS2 Interpret: [Export Value at All Nodes](https://www.rocscience.com/help/rs2/documentation/rs2-interpret/import-export/export/export-value-at-all-nodes), [Plot in Excel](https://rocscience.com/help/rs2/documentation/rs2-interpret/import-export/export/plot-in-excel), [Export Query to Excel](https://rocscience.com/help/rs2/documentation/rs2-interpret/probabilistic-analysis/export-query-to-excel). [V2]
- Itasca. *Using Python with FLAC3D* y *Array Style Programming with FLAC3D and NumPy*: [docs.itascacg.com](https://docs.itascacg.com/pfc700/common/docproject/source/manual/scripting/python/doc/python_flac3d.py.html); [zone export](https://docs.itascasoftware.com/itasca970/flac3d/zone/doc/manual/zone_manual/zone_commands/cmd_zone.export.html). [V2]
- Carranza-Torres, C. y Fairhurst, C. (2000). Application of the convergence-confinement method of tunnel design to rock masses that satisfy the Hoek-Brown failure criterion. *Tunnelling and Underground Space Technology*, 15(2), 187-213. [V2]
- Carranza-Torres, C. (2004). Elasto-plastic solution of tunnel problems using the generalized form of the Hoek-Brown failure criterion. *IJRMMS*, 41(S1). [NV]
- Vlachopoulos, N. y Diederichs, M. S. (2009). Improved longitudinal displacement profiles for convergence confinement analysis of deep tunnels. *RMRE*, 42, 131-146. https://doi.org/10.1007/s00603-009-0176-4 [V2]
- Hoek, E. y Marinos, P. (2000). Predicting tunnel squeezing problems in weak heterogeneous rock masses. *Tunnels and Tunnelling International*. [NV]
- Crouch, S. L. y Starfield, A. M. (1983). *Boundary Element Methods in Solid Mechanics*. Allen & Unwin. [NV]
- Brady, B. H. G. y Brown, E. T. (2004). *Rock Mechanics for Underground Mining* (3.ª ed.). Springer. [NV]
- Salençon (1969), Hoek y Brown (1982), Einstein y Schwartz (1979), Reed (1986), Farmer (1975), Carranza-Torres (2002), Lee y Pietruszczak (2008), Duncan Fama (1993), Vrakas y Anagnostou (2013, 2014): citados en los manuales de Rocscience. [V1 como cita, NV como original]
- Xu, H. et al. (2023). *Machine learning in the stochastic analysis of slope stability: a state-of-the-art review*, *Modelling* 4(4) ([UTS](https://opus.lib.uts.edu.au/handle/10453/177186)), sobre sustitutos del FS. [V2 en el resumen]
- Hammah, R. E., Yacoub, T. E., Corkum, B. y Curran, J. H. (2005). *A comparison of finite element slope stability analysis with conventional limit-equilibrium investigation*. Artículo de conferencia. [PDF en Rocscience](https://www.rocscience.com/assets/resources/learning/papers/A-Comparison-of-Finite-Element-Slope-Stability-Analysis-with-Conventional-Limit-Equilibrium-Investigation.pdf). [V1 en el contenido; la conferencia no se verificó]
- Chiwaye, H. T. y Stacey, T. R. (2010). A comparison of limit equilibrium and numerical modelling approaches to risk analysis for open pit mining. *J. SAIMM*, 110(10), 571-580. [PDF](https://scielo.org.za/pdf/jsaimm/v110n10/02.pdf) [V1]
- Itasca. *FLAC3D Theory and Background: Factor of Safety*. [docs.itascacg.com](https://docs.itascacg.com/pfc600/flac3d/docproject/source/theory/factorofsafety/computationalmethods.html); talud de Hoek-Brown en [3DEC](https://docs.itascacg.com/pfc700/3dec/block/test3d/Theory_and_Background/Factor_of_Safety/HoekBrownSlope/hoekbrownslope.html). [V2]
- Cheng, Y. M., Lansivaara, T. y Wei, W. B. (2007). *Computers and Geotechnics*, 34(3), 137-150. [V2]
- Dawson, E. M., Roth, W. H. y Drescher, A. (1999). *Géotechnique*, 49(6), 835-840. [V2]
- Tschuchnigg, F., Schweiger, H. F. y Sloan, S. W. (2015). *Géotechnique*, 65(4), 249-257. [V2]
- Macciotta, R., Creighton, A. y Martin, C. D. (2020). Design acceptance criteria for operating open-pit slopes: an update. *CIM Journal*, 11(4), 248-265. doi:10.1080/19236026.2020.1826830 [V2]; candidato a perfil nuevo.
- GitHub: [onurkoc/ground-curve](https://www.github.com/onurkoc/ground-curve); BigWham (GeoEnergyLab-EPFL). [V2]
