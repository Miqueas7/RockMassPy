# Ejemplo 11 · Criterios de aceptación y Sarma

Tres taludes inventados, cada uno frente a su criterio: el banco y el talud global de un tajo (Read y Stacey, Ryan y
Pryor y el art. 264 del DS 024), un botadero sobre una ladera con arcilla, resuelto por Sarma (frente a una tabla de
criterios propia), y un pad de lixiviación sobre una geomembrana (frente a NDEP). La geometría, los materiales, las
familias, el registro de aceleraciones (un seno amortiguado) y la tabla de criterios del botadero son sintéticos y
los genera el propio script. Nada de este ejemplo viene de una mina ni de un sismo real.

```bash
pip install "rockmasspy[io,viz,report]"
python criterios.py salida/
```

Escribe las hojas como CSV (`Familias`, `Taludes`, `Bloques`, `Distribuciones`, `Geometria`, `Estratos`,
`Materiales_LE`, `Analisis_LE`, `Sismos` y `Criterios`), evalúa los bloques (`rm.assess_blocks`, 5000 muestras con
hipercubo latino y semilla 11) y los tres análisis de equilibrio límite (`rm.assess_le`), y compara cada parte con su
criterio (`rm.assess_criteria`). Guarda `bloques_resultados.csv`, `equilibrio_resultados.csv` y
`criterios_resultados.csv` (un chequeo por fila, de los cuatro perfiles y del art. 264). Con matplotlib dibuja la
sección de cada análisis (`seccion_le_2.png` muestra las tres cuñas de Sarma) y el Newmark del pad (`newmark_3.png`).
Escribe tres informes: `criterios_tajo.html` (el completo, frente a Read y Stacey y con el art. 264; también
`criterios_tajo.docx` si tienes python-docx), `criterios_botadero.html` (tabla propia) y `criterios_pad.html` (NDEP).
Al final corre las dos CLI. Tarda unos 10 s.

## Qué es un criterio de aceptación

Un FS de 1.26 no es bueno ni malo por sí mismo. Se lee contra un **criterio de aceptación**: el FS mínimo (o la
probabilidad de falla máxima, o la confiabilidad mínima de la berma) que una guía, una norma o el propio proyecto pide
para ese tipo de talud. Cada criterio depende de la **escala** (banco, interrampa, global, pad, botadero) y de la
**consecuencia** de una falla (baja, media, alta…). Por eso cada fila de `Bloques` y de `Analisis_LE` lleva sus
columnas `escala` y `consecuencia`.

La librería compara y dice, por cada chequeo, **«cumple», «no cumple» o «no verificable»**, siempre con el criterio,
su fuente, su fuerza y su marca. **Nunca dice «aprobado»**: aprobar un talud es una decisión del ingeniero, que ve lo
que la librería no ve (la calidad de los datos, el monitoreo, la historia del sitio, lo que pide la autoridad). Un
«no cumple» pide atención (código 2 en la CLI). Un «no verificable» es una nota con su razón: falta la escala, el
perfil no tiene criterio para esa escala, no hubo análisis probabilístico… Nunca se cuenta como «cumple».

## Ley o guía, y las marcas V1, V2 y de usuario

- **Fuerza.** Una **ley** obliga (el DS 024-2016-EM en el Perú). Una **guía** recomienda: Read y Stacey (2009), NDEP
  (2021), WA DMIRS (2019) y Ryan y Pryor (2000) son guías. El informe y el archivo de resultados dicen cuál es cuál.
- **Marca.** Dice qué tan verificado está el valor:
  - **V1:** se leyó en la fuente original (NDEP, el DS 024);
  - **V2:** sale de una fuente secundaria que reproduce la original. La tabla 9.9 de Read y Stacey se leyó en Moffitt
    (2023), porque el libro es de pago. El informe lo advierte;
  - **user:** la tabla propia del usuario (`Criterios`), que la librería vuelve un perfil en memoria con fuerza «guía».
    Aquí es el criterio del botadero: FS estático ≥ 1.3 y seudoestático ≥ 1.0, con la fuente «criterio de diseño del
    proyecto, sintético».

## La política de rangos

Read y Stacey dan algunos criterios como un rango: la PoF máxima de un banco va de 25 a 50 %; el FS mínimo global con
consecuencia alta, de 1.30 a 1.50. El ingeniero elige dentro del rango; la librería necesita un número. La **política
por defecto es la conservadora**: el extremo alto para un mínimo (FS) y el bajo para un máximo (PoF). `upper` y `lower`
la cambian (en la API, `range_policy=`; en la CLI, `--range-policy`). El valor usado sale en el resultado
(`rango_usado`, por ejemplo `lower of 25-50`).

El límite cumple: un FS igual al mínimo cumple «≥» y una PoF igual al máximo cumple «≤». La comparación es exacta en
decimales, así que el resultado no depende del ruido de coma flotante.

## Qué es Sarma y cuándo usarlo en botaderos

Sarma (1979), en la forma de Hoek (1987), corta la masa en **cuñas rígidas con interfaces inclinadas**, no en tajadas
verticales. Equilibra las fuerzas de cada cuña con la resistencia reducida por F en la base y en las interfaces, y
entrega el FS y la **aceleración crítica Kc** (el kh que lleva el FS a 1). Las interfaces se cortan por dentro de la
masa, así que el mecanismo puede romperse internamente, como pasa cuando un botadero se desliza sobre una base débil
inclinada: una cuña de atrás empuja a las de adelante a lo largo de la arcilla. Un círculo no sigue esa base, y las
tajadas verticales no representan el corte interno. Con `sarma_angulos = opt`, la librería busca los ángulos de las
interfaces que dan el menor FS.

Se verificó con el problema 4 del manual de verificación de Sarma de Slide (una pila de desmonte sobre un piso
cizallado): 1.1970 frente a 1.198 publicado. Con una sola cuña da exactamente el bloque planar de Hoek. No acepta
Hoek-Brown, agua encharcada ni grieta de tracción (no hay caso publicado para verificarlo); para Hoek-Brown usa GLE.

## Qué pide el art. 264 del DS 024

El art. 264 del DS 024-2016-EM pide analizar la **pendiente general del tajo en condición seudoestática**, con sismo y
lluvia de **período de retorno de 100 años**. No fija un FS mínimo. El ítem `PE-264` del perfil `PE-DS024-2016` dice
«cumple» si hay al menos un análisis con `escala = global`, kh > 0 y `periodo_retorno_anios` ≥ 100. El kh lo da el
usuario: la librería no lo calcula a partir de la sismicidad. Sin período de retorno, el chequeo es «no verificable».

## Las tres partes y sus números

**(a) Tajo.** Un banco de 15 m con la cara a 70° y un plano de 40° que aflora en ella:
- El bloque planar (escala banco) tiene **FS 1.120** y **PoF 28.2 %**. La PoF sale de c (25 ± 12 kPa) y φ (32 ± 5°)
  aleatorios.
- La berma de 10 m tiene **94.5 %** de confiabilidad, con la cara del banco de 70 ± 5°.
- El talud global de 150 m a unos 45°, en un solo material (c 200 kPa, φ 36°, γ 26), se resolvió con búsqueda
  circular por Spencer y Bishop. Da **FS estático 1.424** y **FS 1.229 con kh 0.1**; ky es 0.251.

**(b) Botadero.** 40 m a 37° sobre una ladera de 8° cubierta por 2 m de arcilla (c 12, φ 18):
- Sarma con tres cuñas sobre la arcilla da **FS estático 1.258**, **FS 1.059 con kh 0.07** y **Kc 0.0956**.
- Los ángulos óptimos de las interfaces son 70.8° y 81.5°.

**(c) Pad.** 30 m a 2H:1V sobre una geomembrana (interfaz c 0, φ 20°):
- La búsqueda de bloque sobre la geomembrana da **FS estático 1.516** y **FS 1.040 con kh 0.16**.
- ky es 0.178. Con el registro sintético (pico de 0.3 g), el Newmark es de **2.7 cm**.

| Parte | Criterio | Chequeo | Requerido | Obtenido | Estado |
|---|---|---|---|---|---|
| banco | Read y Stacey | FS estático | ≥ 1.1 | 1.120 | cumple |
| banco | Read y Stacey | PoF | ≤ 25 % (lower of 25-50) | 28.2 % | **no cumple** |
| berma | Ryan y Pryor | confiabilidad | ≥ 90 % (upper of 50-90) | 94.5 % | cumple |
| global | Read y Stacey, global y media | FS estático | ≥ 1.3 | 1.424 | cumple |
| global | DS 024, art. 264 (ley) | análisis seudoestático global, Tr ≥ 100 | sí | kh 0.1, Tr 100 | cumple |
| botadero | Read y Stacey | FS estático | sin criterio para botadero | | no verificable |
| pad | Read y Stacey | FS estático | sin criterio para pad | | no verificable |
| botadero | tabla propia | FS estático | ≥ 1.3 | 1.258 | **no cumple** |
| botadero | tabla propia | FS seudoestático | ≥ 1.0 | 1.059 | cumple |
| pad | NDEP, ítem 6 | FS estático | ≥ 1.3 | 1.516 | cumple |
| pad | NDEP, ítem 6 | FS seudoestático | ≥ 1.05 | 1.040 | **no cumple** |
| pad | NDEP, ítem 7 | deformación si el seudoestático es < 1.05 | Newmark | 2.7 cm | cumple |

En conteos, Read y Stacey dan 5 chequeos (2 cumple, 1 no cumple, 2 no verificables); Ryan y Pryor, 1 cumple; la tabla
propia, 1 cumple y 1 no cumple; NDEP, 2 cumple y 1 no cumple.

Lo que muestra cada fila:
- **Una escala sin criterio.** Read y Stacey no tienen criterio para botaderos ni pads. Por eso el botadero y el pad
  salen «no verificable», con la razón «the profile has no criterion for this scale». No es un «cumple».
- **La política de rangos.** Con `range_policy="upper"`, la PoF del banco se compara con 50 % y pasa a «cumple».
  El ejemplo lo calcula y lo imprime.
- **NDEP, ítems 6 y 7.** El seudoestático del pad (1.040) queda bajo 1.05, así que no cumple el ítem 6. Por eso
  mismo el ítem 7 exige un análisis de deformación. Como el análisis trae Newmark, el ítem 7 se cumple. Los dos
  chequeos son independientes: el Newmark no borra el «no cumple» del ítem 6. El ingeniero decide si 2.7 cm son
  tolerables.
- **Sarma frente a la tabla propia.** El botadero aguanta el sismo según su criterio (1.059 ≥ 1.0), pero no el caso
  estático (1.258 < 1.3).

Ningún FS llega a 1 y los análisis no tienen avisos, así que lo único que pide atención son los «no cumple».

## Las dos CLI

```bash
rockmass le --geometry Geometria.csv --layers Estratos.csv --materials Materiales_LE.csv --analyses Analisis_LE.csv \
    --records Sismos.csv --criteria READ-STACEY-2009 --profile PE-DS024-2016 --criteria-output criterios_le_cli.csv
rockmass slope --faces Taludes.csv --families Familias.csv --blocks Bloques.csv --distributions Distribuciones.csv \
    --iterations 5000 --seed 11 --criteria READ-STACEY-2009
```

- **`rockmass le` termina con 0.** Contra Read y Stacey imprime `meets: 1, fails: 0, not verifiable: 2` (el global
  cumple; el botadero y el pad no tienen criterio) y `PE-264: meets [law]`. No hay ningún «no cumple» ni ningún aviso.
- **`rockmass slope` termina con 2.** Imprime `meets: 1, fails: 1, not verifiable: 0` y `fails by rule: slope_pof (1)`.
  La cara del banco también pide atención por la cinemática de la 3A: el plano permite deslizamiento planar y el SMR
  sale de clase V. Con `--range-policy upper`, la PoF cumpliría, pero el código seguiría siendo 2 por la cinemática.
  La berma no aparece porque Read y Stacey no tienen regla de berma; en la API se evalúa con `RYAN-PRYOR-2000`.

Cada CLI recibe un solo perfil de criterios. Para evaluar cada parte con el suyo, como hace el script, se usa la API:
`rm.assess_criteria(perfil, blocks=..., le=..., assignments=criteria_assignments(...))`.

## Privacidad

Los ids (`id_bloque`, `id_talud`, `id_analisis`, `id_seccion`), los materiales, el registro y los nombres de línea
salen solo en las tablas de los informes y en los archivos de resultados. Nunca salen en la CLI, en las figuras (que
llevan el número de orden) ni en un mensaje. Las razones de «no verificable» van sin ids ni valores.
