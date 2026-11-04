# Ejemplo 10 · Equilibrio límite y Newmark

Dos secciones inventadas: el talud de un tajo con dos estratos y un botadero sobre una capa débil. La geometría, los
materiales y el registro de aceleraciones son sintéticos; el registro es un seno amortiguado que genera el propio
script. Nada de este ejemplo viene de una mina ni de un sismo real.

```bash
pip install "rockmasspy[io,viz,report]"
python equilibrio.py salida/
```

Escribe las cinco hojas como CSV (`Geometria.csv`, `Estratos.csv`, `Materiales_LE.csv`, `Analisis_LE.csv` y
`Sismos.csv`), las evalúa con `rm.assess_le` y guarda `equilibrio_resultados.csv` (una fila por método). Con
matplotlib dibuja la sección de cada análisis (`seccion_le_1.png`, `seccion_le_2.png`) y el Newmark del botadero
(`newmark_2.png`). Escribe el informe `equilibrio.html` (y `equilibrio.docx` si tienes python-docx) y corre
`rockmass le` con los mismos CSV. **La CLI termina con 0**: ningún FS llega a 1 y no hay avisos. Como hay dos
análisis, la CLI escribe el avance (`analysis 1 of 2...`) en stderr.

Tarda unos 12 s, casi todo en la búsqueda circular con Hoek-Brown. Con Hoek-Brown, una búsqueda circular de 20×20×11
tarda unos 10 a 15 s; con kh, ky por vueltas puede repetirla hasta 5 veces.

## Las dos secciones

| Análisis | Sección | Estratos | Búsqueda y métodos | Sismo |
|---|---|---|---|---|
| 1 | tajo de 80 m a 45°, la cara mira a la derecha | 15 m de suelo residual (Mohr-Coulomb, c 50 kPa, φ 32°, γ 21) sobre roca (Hoek-Brown: σci 8 MPa, GSI 30, mi 10, D 0, γ 25) | circular, malla de centros x 70–170, y 100–200; Bishop y GLE; 25 tajadas | no |
| 2 | botadero de 30 m a 1.5H:1V | desmonte (c 5, φ 38, γ 19), 1.5 m de arcilla (c 12, φ 21, γ 18) y fundación (c 50, φ 35, γ 22); línea piezométrica de 27 m atrás a 20 m en el pie | de bloque sobre la línea `arcilla` (en medio de la capa); Spencer y GLE | kh 0.1, ky y Newmark con el registro `S1` |

## Los números que da

| | Análisis 1 (tajo) | Análisis 2 (botadero) |
|---|---|---|
| FS del primer método | Bishop **1.485** | Spencer **1.108** (con kh 0.1) |
| FS del segundo método | GLE **1.480** (λ 0.886) | GLE **1.106** (λ 0.927) |
| FS estático (`fs_estatico`, sobre la crítica estática) | el mismo (kh 0) | Spencer **1.315**, GLE **1.305** |
| ky | no se pide | **0.156** |
| Newmark | no se pide | **4.6 cm** (gobierna el registro tal como está, no el invertido) |
| Superficies evaluadas / descartadas | 6515 / 1353 | 4545 / 1845 |

`le_counts` da 2 análisis, 2 con FS, 0 con FS ≤ 1, 1 circular, 1 de bloque, 1 con Newmark, 0 avisos y 5 notas. Las
notas no piden atención:
- en el tajo, Bishop dice que en una tajada la fuerza normal efectiva sale negativa. Es una nota, no un aviso: el FS
  converge y GLE, que no la tiene, da casi lo mismo;
- en el botadero, cómo se buscó ky (por vueltas, abajo), que ky salió en otra superficie (la crítica estática, que
  es la de menor ky) y no en la crítica con kh 0.1 que se dibuja, que el FS estático se calcula sobre la crítica
  estática y que en Newmark gobierna el sentido original del registro. Por eso la figura dice «ky = 0.156 (otra superficie)».

En `equilibrio_resultados.csv`, ky y Newmark van solo en la fila del primer método (Spencer), que es el que los calcula.
`fs_estatico` es el FS del talud sin sismo: cada método sobre la crítica estática (la búsqueda con kh = 0), no sobre la
crítica con kh 0.1. Sobre esa otra superficie el FS sin kh sería 1.343, y el talud parecería más seguro de lo que es.

El círculo crítico del tajo (centro 162.10, 143.15 y radio 123.13) corta el suelo residual arriba y entra en la roca.
No pasa por el pie: sale por la cara en (137.5, 22.5), 2.5 m sobre el pie, y su punto más bajo (cota 20.02 en
x 162.1) cae fuera de la masa, delante del pie. La superficie crítica del botadero baja por el desmonte a unos 45° desde la cresta, corre
por la arcilla y sale al pie.

## Qué calcula cada método

Todos cortan la masa en tajadas verticales y buscan el FS que equilibra cada tajada. Se diferencian en qué ecuaciones
cumplen y qué suponen sobre las fuerzas entre tajadas:

- **Ordinario (Fellenius):** ignora las fuerzas entre tajadas. Solo equilibra momentos y suele quedar por debajo de
  los demás. Con `ru`, resta u·l como Fredlund y Krahn.
- **Bishop simplificado:** fuerzas entre tajadas horizontales; equilibra momentos respecto del centro del círculo y la
  fuerza vertical de cada tajada. Es un método circular: con una polilínea toma un centro aproximado y lo deja en nota.
- **Janbu simplificado y corregido:** equilibra fuerzas, no momentos. El corregido multiplica por f0, que depende de
  qué tan profunda es la superficie respecto de su cuerda.
- **Spencer:** fuerzas entre tajadas con una inclinación constante (λ); cumple fuerzas y momentos.
- **Morgenstern-Price/GLE:** como Spencer, pero la inclinación varía a lo largo de la masa con una función (medio seno
  por defecto, o constante, que es Spencer). Cumple fuerzas y momentos.

**Por qué Bishop y Spencer/GLE se separan con kh alto.** Sin sismo, el equilibrio de momentos manda y Bishop queda muy
cerca de los métodos rigurosos (aquí 1.485 contra 1.480). El sismo pseudoestático es una fuerza horizontal en cada
tajada. Bishop no equilibra fuerzas horizontales y supone que entre tajadas no hay corte, así que esa fuerza solo le
llega por el momento. Spencer y GLE sí la equilibran, y el corte entre tajadas que necesitan para hacerlo baja el FS.
Cuanto mayor es kh, mayor es la diferencia. En el caso ACADS 1(d) del manual de verificación de Slide2 (kh 0.15),
Bishop da 1.016 y Spencer 0.991: uno dice que el talud resiste y el otro que falla. Con sismo, el método que manda es
Spencer o GLE; por eso el botadero usa esos dos.

## Búsqueda circular y búsqueda de bloque

- **Circular** (análisis 1): una malla de 20 × 20 intervalos de centros, cada uno con 11 radios entre el que apenas
  toca la superficie y el tangente a la base del modelo (más apretados cerca de la superficie, para no perder los
  círculos someros), y un afinado local desde los cinco mejores. Se queda el círculo de
  menor FS con el primer método de `metodos`; los demás métodos se evalúan sobre ese mismo círculo. Si el centro
  crítico queda en el borde de la malla, sale un aviso: agranda la malla.
- **De bloque** (análisis 2): para superficies que siguen una capa débil. Toma pares de puntos sobre la línea débil
  (`linea_debil`), sigue la línea entre ellos y proyecta desde el punto de atrás un tramo hacia la cresta (entre 45° y
  65° sobre la horizontal) y desde el de adelante otro hacia el pie (entre 25° y 45°); luego afina los vértices. Es lo que hace falta en un botadero o un pad sobre
  arcilla, donde un círculo no puede seguir la capa.

## ky y Newmark

- **ky (coeficiente de fluencia)** es el kh que lleva el FS a 1: la aceleración horizontal, en g, que la masa aguanta
  sin moverse. La superficie crítica estática no siempre es la de menor ky, así que la librería busca por vueltas:
  busca con kh = 0 y calcula su ky, vuelve a buscar con kh = ese ky y recalcula, hasta 4 vueltas o hasta que ky cambie
  menos de 1e-4. Informa el menor ky con su superficie.
- **Newmark de bloque rígido:** mientras la aceleración del registro supera ky, la masa desliza como un bloque sobre
  su superficie; la aceleración relativa (a − ky)·g se integra dos veces hasta que la velocidad relativa vuelve a cero.
  Solo cuenta el deslizamiento hacia la cara. La librería prueba el registro en los dos sentidos y se queda con el
  peor. Aquí el registro (pico de 0.3 g) supera ky = 0.156 en sus primeros ciclos y el botadero se mueve 4.6 cm.
- La curva inferior de `newmark_2.png` es el desplazamiento acumulado: sube a escalones, uno por cada pulso que pasa
  ky.

## Por qué la librería no dice «aceptable»

Un FS bajo 1 es mecánica: el equilibrio no se cumple, y eso sí pide atención (código 2). Un FS de 1.48 en el tajo, un
FS pseudoestático de 1.11 o 4.6 cm de Newmark en el botadero solo se leen contra un criterio (Read y Stacey, la guía
que siga tu operación, el DS 024), y cada criterio depende del tipo de talud, de su consecuencia y de cuánto se conoce
el macizo. Esos criterios entran como datos en la fase 3D. Hasta entonces la librería informa FS, ky y desplazamiento
sin juzgarlos: solo un FS ≤ 1 (con holgura de 1e-9) y los avisos cambian el código de salida.

## Convención de las hojas

- **`Geometria`:** una fila por vértice (`id_seccion`, `linea`, `x_m`, `y_m`), con x creciente. La línea
  `superficie` es obligatoria; `piezometrica` es opcional; las demás son contactos, líneas débiles o superficies dadas.
  La cara puede mirar a la izquierda o a la derecha: el núcleo lo detecta y reflejar la sección no cambia nada.
- **`Estratos`:** `orden` 1 arriba; cada estrato nombra la línea de su base (`linea_base`), salvo el último.
- **`Materiales_LE`:** `mohr_coulomb` con `cohesion_kpa` y `friccion_grados`, o `hoek_brown` con `sigma_ci_mpa` (en
  MPa) y `gsi` + `mi` (+ `d`, vacío = 0) o `mb`, `s` y `a`. Usa `d` solo en la zona dañada por la voladura, nunca en
  todo el macizo: si no, la librería avisa.
- **`Analisis_LE`:** `metodos` separados por `;` (`ordinario`, `bishop`, `janbu`, `janbu_corregido`, `spencer`, `gle`);
  el primero busca. `superficie` es `circular` (con la malla), `bloque` (con `linea_debil`) o `dada` (con
  `linea_superficie`). `kh` y `registro` (un id de `Sismos`) piden ky; `registro`, además, Newmark.
- **`Sismos`:** `registro`, `t_s` desde 0 con paso constante y `a_g` en g.

Unidades: kN, kPa y m.

## Privacidad

`id_seccion`, `id_analisis`, `material`, `registro` y los nombres de línea salen solo en las tablas del informe (los
dos ids también en `equilibrio_resultados.csv`), nunca en la CLI, en las figuras (que llevan el número de orden y
«Estrato 1, 2…») ni en un mensaje. Las columnas ajenas (`codigo_mina`, `zona_nivel`, `observaciones`, `este_m`,
`norte_m`…) no se leen.
