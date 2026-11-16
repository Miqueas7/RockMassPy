# Fórmulas de la Fase 8C: elementos de contorno 2D y strength factor

Investigación y verificación para la Fase 8C (método de elementos de contorno en 2D, deformación plana, medio infinito,
elástico, isótropo y con campo de esfuerzos in situ, al estilo de Examine2D). Fecha: 14-nov-2026. Solo documentos públicos;
no se tocó ninguna carpeta de clientes.

**Marcas.** [V1] leída en el original o en la copia del autor o del editor (aquí, siempre leída sobre la imagen de la
página, no sobre el texto extraído). [V2] fuente secundaria seria. [NV] no verificada; no entra. «Deducida» = álgebra
mía a partir de ecuaciones marcadas; la comprueba el prototipo. «Prototipo» = cálculo propio en Python local (§7).

**Licencias y código ajeno.** No se copió ni se leyó código de nadie. Las notas de Martel (Univ. de Hawái) traen el
listado de `twoddm.m` sin licencia: leí solo las páginas de texto y diagramas (19-1 a 19-7) y **no** el listado
(19-8 en adelante). El prototipo se escribió desde las ecuaciones transcritas aquí.

## 0. Fuentes

| Clave | Documento | Dónde |
|---|---|---|
| YAN | Yan, X. (2004), A special crack tip displacement discontinuity element, *Mech. Res. Commun.* 31, 651-659. Reproduce la solución de Crouch (1976) y de Crouch y Starfield (1983). Copia en el sitio del laboratorio MSV de la NTOU (no es del autor ni del editor) | msvlab.ntou.edu.tw/cite/MRC-Yan-2004.pdf |
| JH | Jo, H. y Hurt, R. (2013), Testing and review of various displacement discontinuity elements for LEFM crack problems, cap. 42 de *Effective and Sustainable Hydraulic Fracturing*, InTech (ecuaciones en p. 834), CC BY 3.0 (copia del editor), doi 10.5772/56445 | cdn.intechopen.com/pdfs/44675/... |
| MAR | Martel, S. (2003), *GG711c Lec. 19: Boundary element code TWODD*, apuntes de la Univ. de Hawái, «modified from Crouch and Starfield (1983)» | soest.hawaii.edu/martel/Courses/GG703/GG711c_Lec_19.pdf |
| RSF | Rocscience, *Strength Factor* (Phase2 Theory), 4 pp. Enlazado desde la ayuda de RS2 | static.rocscience.cloud/assets/verification-and-theory/RS2/RS2_Strength_Factor_Theory.pdf |
| RSH | Ayuda en línea de RS2 y de EX3, página *Strength factor* | rocscience.com/help/rs2/.../strength-factor ; rocscience.com/help/ex3/documentation/interpret/strength-factor |
| UBC | Eberhardt, E., *EOSC 433 Lab Practical: Boundary Element Stress Analysis* (con Examine2D), Univ. de British Columbia, 9 pp., y su hoja de respuestas (2 pp., en blanco) | eoas.ubc.ca/courses/eosc433/lecture-material/Lab8-BoundaryElementExercise.pdf |
| LING | Ling, C. B. (1948), *J. Appl. Phys.* 19, 77-82, reproducido en Lim, M. y Yu, S. (2017), *Stress concentration for two nearly touching circular holes*, arXiv 1705.10400v1, §3.3, ecs. 3.15-3.24 (pp. 7-9) | arxiv.org/pdf/1705.10400 |
| RS2-S | Rocscience (2021), *RS2 Stress Analysis Verification Manual*, problema 1 | `docs/investigacion/pdfs/Rocscience_RS2_Stress_Verification_2021.pdf` |
| EX3 | Rocscience, *Examine3D Verification Examples 1-7* | static.rocscience.cloud/assets/verification-and-theory/EX3/Verification-Example-N.pdf |
| 8B | `FORMULAS_FASE8B.md` §1 (Kirsch) y §2 (Inglis, de CC02) | este repositorio |
| HB02 | Hoek, Carranza-Torres y Corkum (2002), ec. 7 | `docs/investigacion/pdfs/hb2002.pdf` |

**Lo que no pude abrir:** Crouch (1976) *IJNME* 10, 301-343 (Wiley, de pago); el libro de Crouch y Starfield (1983),
*Boundary Element Methods in Solid Mechanics* (no hay copia pública); Ling (1948) original (de pago); el manual y la
ayuda de Examine2D (es software antiguo; no encontré su página de teoría); el instructivo con números del laboratorio UBC
(la hoja de respuestas está en blanco). Por eso las ecuaciones de Crouch quedan en [V2]: dos fuentes secundarias
independientes concuerdan (YAN y JH) y el prototipo las valida contra Kirsch, Inglis y Ling.

**Convención de signos.** Las ecuaciones de Crouch y Starfield usan **tracción positiva**. La API de RockMassPy usa
**compresión positiva** (como Examine2D y RS2). Regla única: el núcleo trabaja en tracción positiva y en la frontera de la
API se cambia el signo de todo esfuerzo: `σ_núcleo = −σ_API`. Los desplazamientos no cambian de signo. Unidades: MPa y m;
los desplazamientos salen en m si `E` está en MPa y los esfuerzos en MPa.

---

## 1. Método de desplazamiento discontinuo (DDM), elemento constante

### 1.1 Definición del desplazamiento discontinuo [V2, YAN p. 652, ec. 1 y Fig. 1]

Segmento `|x| < a`, `y = 0`, en un sólido infinito; lado positivo `y = 0+`, lado negativo `y = 0−`:

```
Dx = ux(x, 0−) − ux(x, 0+)
Dy = uy(x, 0−) − uy(x, 0+)
```

En el sistema local del elemento, `Dx` es la componente tangencial `Ds` y `Dy` la normal `Dn`.

### 1.2 Desplazamientos y esfuerzos de un elemento [V2, YAN p. 652, ecs. 2-3; igual en JH p. 834, ecs. 1-5]

`G` es el módulo de corte y `ν` el coeficiente de Poisson (deformación plana). Tracción positiva:

```
ux  = Dx[2(1−ν) f,y − y f,xx] + Dy[−(1−2ν) f,x − y f,xy]
uy  = Dx[(1−2ν) f,x − y f,xy] + Dy[2(1−ν) f,y − y f,yy]

σxx = 2G Dx[2 f,xy + y f,xyy] + 2G Dy[f,yy + y f,yyy]
σyy = 2G Dx[−y f,xyy]         + 2G Dy[f,yy − y f,yyy]
σxy = 2G Dx[f,yy + y f,yyy]   + 2G Dy[−y f,xyy]
```

JH escribe lo mismo con una segunda función `g` para la parte de `Dy`; con `D` constante, `g = (Dy/Dx)·f`.

### 1.3 La función f y sus derivadas [V2, YAN p. 653, ecs. 4-5]

```
f(x,y) = −1/(4π(1−ν)) · { y[arctan(y/(x−a)) − arctan(y/(x+a))]
                          − (x−a) ln√((x−a)²+y²) + (x+a) ln√((x+a)²+y²) }

f,x   =  1/(4π(1−ν)) · [ln√((x−a)²+y²) − ln√((x+a)²+y²)]
f,y   = −1/(4π(1−ν)) · [arctan(y/(x−a)) − arctan(y/(x+a))]
f,xy  =  1/(4π(1−ν)) · [y/((x−a)²+y²) − y/((x+a)²+y²)]
f,xx  = −f,yy = 1/(4π(1−ν)) · [(x−a)/((x−a)²+y²) − (x+a)/((x+a)²+y²)]
f,xyy = −f,xxx = 1/(4π(1−ν)) · [((x−a)²−y²)/((x−a)²+y²)² − ((x+a)²−y²)/((x+a)²+y²)²]
f,yyy = −f,xxy = 2y/(4π(1−ν)) · [(x−a)/((x−a)²+y²)² − (x+a)/((x+a)²+y²)²]
```

Comprobaciones del prototipo:
- Las derivadas de la ec. 5 coinciden con las diferencias finitas de la ec. 4 (error relativo máximo 3.8×10⁻⁸ en cuatro
  puntos, incluidos puntos a 0.05 del elemento).
- **Rama del arctan.** Hay que escribir `arctan(y/(x∓a))` como `atan2(y, x∓a)`. Con `atan2`, al cruzar el elemento
  (`|x| < a`) `f,y` salta de `−1/(4(1−ν))` (en `y = 0+`) a `+1/(4(1−ν))` (en `y = 0−`), y el desplazamiento salta en
  `−Dx` y `−Dy` (ec. 1): el prototipo da `ux = −0.5` arriba y `+0.5` abajo por `Ds = 1`. Con el `arctan` principal no
  hay salto y los desplazamientos sobre el elemento salen mal. Los esfuerzos no usan `f,y` y no se ven afectados.
- La `f` cerrada de YAN difiere de la integral de JH (ec. 6, `f = −1/(4π(1−ν))∫ln r dξ`) en la constante
  `2a/(4π(1−ν))`; no importa porque solo se usan derivadas (comprobado numéricamente).

**Autoinfluencia (deducida).** En el centro del propio elemento (`x = 0`, `y = 0`): `f,xy = 0`, los términos `y·(…)` se
anulan y `f,yy = 1/(2π(1−ν)a)`. Por eso `σyy = G·Dn/(π(1−ν)a)` y `σxy = G·Ds/(π(1−ν)a)`. Es la diagonal de la matriz.
Se evalúa con las mismas fórmulas en `y = 0`: no hay singularidad en el centro, solo en los extremos `x = ±a`.

### 1.4 Elemento inclinado [deducida; organización según V2, MAR pp. 19-5 a 19-7]

Elemento `j` del nodo `P1 = (x1, y1)` al nodo `P2 = (x2, y2)`: centro `(xc, yc)` = punto medio, semilongitud
`a = |P2 − P1|/2` y ángulo `β = atan2(y2 − y1, x2 − x1)`. Vectores unitarios: tangente `s = (cos β, sin β)` y normal
`n = (−sin β, cos β)` (a la izquierda del sentido de recorrido; es el eje `ȳ` local, el «lado positivo»).

1. Coordenadas locales del punto de cálculo `(x, y)`:
   `x̄ = (x − xc)cos β + (y − yc)sin β`,   `ȳ = −(x − xc)sin β + (y − yc)cos β`.
2. Esfuerzos `σ̄` y desplazamientos `ū` locales con §1.2-1.3 (`a` del elemento, `Dx → Ds`, `Dy → Dn`).
3. Rotación a globales:
   ```
   σxx = σ̄xx cos²β − 2σ̄xy sinβ cosβ + σ̄yy sin²β
   σyy = σ̄xx sin²β + 2σ̄xy sinβ cosβ + σ̄yy cos²β
   σxy = (σ̄xx − σ̄yy) sinβ cosβ + σ̄xy (cos²β − sin²β)
   ux  = ūx cosβ − ūy sinβ,     uy = ūx sinβ + ūy cosβ
   ```
4. Tracción sobre el elemento `i` (ángulo `βi`): `t = σ·n_i`; componentes `t_s = t·s_i` y `t_n = t·n_i`.
   MAR (p. 19-7) arma lo mismo como `σns = a_nx a_sx σxx + a_nx a_sy σxy + a_ny a_sx σyx + a_ny a_sy σyy`.

### 1.5 Sistema para contornos libres de tracciones con esfuerzo in situ [V2, MAR pp. 19-1 y 19-3; armado deducido]

Superposición (MAR, pasos D y J): campo total = in situ `σ⁰` (uniforme) + campo inducido por los DD. La condición de
borde libre `t_total = 0` en el centro de cada elemento da **tracción inducida = − tracción del campo in situ**:

```
Σ_j [ A_ss(i,j) Ds_j + A_sn(i,j) Dn_j ] = −t⁰_s(i)
Σ_j [ A_ns(i,j) Ds_j + A_nn(i,j) Dn_j ] = −t⁰_n(i)        i = 1..n
```

`A_ss(i,j)` es la tracción tangencial en el centro de `i` por `Ds_j = 1`, y así las demás. Matriz `2n × 2n`, densa y no
simétrica; `t⁰ = σ⁰·n_i`. Las incógnitas `Ds`, `Dn` tienen unidades de longitud.

**Núcleo de la matriz (hallazgo del prototipo, no está en las fuentes leídas).** Para cada contorno cerrado, un `D`
**constante en ejes globales** (`Dx_g`, `Dy_g` iguales en todos sus elementos) no produce esfuerzo en ningún punto: es una
traslación rígida del interior (cada vértice recibe dos extremos de dislocación que se anulan). La matriz tiene entonces
un **núcleo exacto de dimensión 2 por contorno**. Medido: dos valores singulares ≈ 10⁻¹⁶·σ_máx con 64, 128 y 256
elementos, y `‖A·v_traslación‖ ≈ 10⁻¹⁵`. El modo de rotación rígida es casi nulo (`≈ 1.9×10⁻³` con 64 elementos y
`1.2×10⁻⁴` con 256). `np.linalg.solve` falló por «matriz singular» en un caso (círculo, 256 elementos, K = 1).
**Remedio probado:** añadir por contorno `Σ_j L_j·Dx_g,j = 0` y `Σ_j L_j·Dy_g,j = 0` (con `L_j = 2a_j`,
`Dx_g = Ds cosβ − Dn sinβ` y `Dy_g = Ds sinβ + Dn cosβ`) como sistema orlado `[[A, Cᵀ], [C, 0]]`, que es cuadrado y
regular. Mínimos cuadrados sobre `[A; C]` da lo mismo. Ni esfuerzos ni desplazamientos fuera de la excavación cambian
(el modo solo mueve el interior).

### 1.6 Sentido de recorrido, normales y lado del material [deducida; comprobada]

- **Examine2D pide las excavaciones en sentido antihorario** (UBC p. 2: «Enter Excavation CCW») [V2].
- Recorrido antihorario: la normal izquierda `n` apunta **hacia dentro** de la excavación y el material queda en el lado
  negativo, `ȳ = 0−`.
- **Los esfuerzos no dependen del sentido**: recorrer en horario o en antihorario cambia los esfuerzos en 2.8×10⁻¹⁴ MPa,
  porque la tracción es continua a través de un DD. La convención solo importa para los desplazamientos.
- **Desplazamiento del borde**: hay que evaluarlo en el lado del material (`ȳ → 0−` si el recorrido es antihorario).
  Así el prototipo reproduce el `ur` de Kirsch (§7.1).
- En la API, normalizar cada polígono a antihorario (área con signo > 0) y avisar si hay polígonos que se cruzan.

### 1.7 Puntos del campo [V2, MAR pasos H-J]

`σ(x, y) = σ⁰ + Σ_j [S_s,j(x,y) Ds_j + S_n,j(x,y) Dn_j]`, y `u(x, y) = Σ_j [...]` (desplazamiento **inducido** por la
excavación, cero antes de excavar, como en 8B §1.1).
- Dentro de una excavación el esfuerzo total sale ≈ 0, porque el interior de un contorno libre de tracciones queda sin
  esfuerzos (prototipo: 0.28 MPa sobre p = 30 MPa con 128 elementos). Esos puntos se enmascaran con una prueba de punto
  en polígono.
- **Deformación plana** [elasticidad estándar; deducida]: `σzz = σz⁰ + ν(Δσxx + Δσyy)`, donde `Δ` es lo inducido.
  Examine2D pide `σz` del campo por separado (UBC p. 3, «out of plane stress, Sigma Z») [V2].
- **Campo in situ como lo pide Examine2D** (σ1, σ3 y ángulo α de σ1 medido desde +x en sentido antihorario; UBC pp. 3-4)
  [V2 para la entrada; tensor deducido], en compresión positiva:
  `σxx⁰ = (σ1+σ3)/2 + (σ1−σ3)/2·cos2α`, `σyy⁰ = (σ1+σ3)/2 − (σ1−σ3)/2·cos2α`, `τxy⁰ = (σ1−σ3)/2·sin2α`.

### 1.8 Esfuerzo tangencial en el borde: no usar el valor en el punto medio [hallazgo del prototipo; remedio deducido]

En el centro de un elemento, el `σtt` que dan las fórmulas es el **promedio de los dos lados** del contorno: el material
(Kirsch) y el interior (≈ 0). Con Kirsch, el error es **51-53 %**, con cualquier número de elementos. La tracción
(`σnn`, `σnt`) sí es continua y sale bien: `|σnn|/p ≈ 10⁻¹⁴`. Dos remedios probados:

1. **Hooke en el borde (recomendado).** En el lado del material, `εtt = ∂u_t/∂s` por diferencia central entre los
   centros vecinos del mismo contorno (`u` evaluado en `ȳ → 0−`). En deformación plana, con `σnn_total = 0`:
   ```
   σtt_total = σ⁰tt + [2G/(1−ν)]·εtt − [ν/(1−ν)]·σ⁰nn          (tracción positiva)
   ```
   (`Δσtt = E/(1−ν²)·εtt + ν/(1−ν)·Δσnn`, con `Δσnn = −σ⁰nn`.)
2. **Doble del punto medio**: `σtt_material = 2·σtt(centro)`, válido porque el interior queda en cero. Es la mitad de
   preciso que el remedio 1 (§7.1).

En esquinas vivas (rectángulos, bóvedas con hastiales rectos) el esfuerzo elástico exacto es singular. El valor del
borde junto a una esquina depende de la malla y **no sirve como valor esperado** de una prueba.

### 1.9 Puntos cerca del borde [hallazgo del prototipo; remedio deducido]

Con elementos constantes, el campo es singular en los extremos de cada elemento. Cerca del borde, el error depende de
`d/L` (distancia al borde sobre longitud del elemento) y **no baja al refinar**: es 76-78 % con `d = 0.1L`, 26 % con
`0.25L`, 7-8 % con `0.5L` y 0.9-1.6 % con `1L`. Con `d ≥ 2L` queda en el error del campo lejano (tabla en §7.2).
Algunos textos hablan de una regla de «no evaluar a menos de un elemento del borde», pero no la leí en Crouch y
Starfield [NV].

**Remedio probado**: si `d < c·L` (con `L` el largo del elemento más cercano):
1. pie `F` del punto sobre el elemento más cercano `i` y punto `Q = F + c·L·n_material`;
2. tensor del borde en `F`: `σnn = σnt = 0` y `σtt` de §1.8 (remedio 1), interpolado linealmente a lo largo del contorno
   entre los centros de `i` y de su vecino;
3. `σ(P) = σ_borde + (d/(cL))·(σ(Q) − σ_borde)`.

Con `c = 1`, el error máximo para toda distancia es ≤ 2.0 % con 64 elementos, ≤ 1.13 % con 128 y ≤ 0.86 % con 256.
Con `c = 2` y 256 elementos el error baja a ≤ 0.49 %.

---

## 2. Algoritmo paso a paso (núcleo en tracción positiva)

1. **Entrada API** (compresión +): polígonos cerrados de las excavaciones, `E`, `ν`, campo `σ1`, `σ3`, `α`, `σz` (o
   `σxx⁰`, `σyy⁰`, `τxy⁰`), puntos de cálculo y criterio de resistencia.
2. Validar: polígonos simples sin cruces; orientarlos en antihorario; `E > 0` y `0 ≤ ν < 0.5`.
3. Discretizar cada lado en elementos de largo `L ≤ L_obj`. En curvas, `L ≤ 0.04·ρ` (ρ = radio de curvatura) para un
   error de borde menor de 1 % (§7). Refinar junto a las esquinas.
4. Convertir el in situ a tracción positiva: `σ⁰_núcleo = −σ⁰_API`.
5. Armar `A` (`2n × 2n`) con §1.3-1.4 en los centros; `b = −t⁰` (§1.5).
6. Agregar las 2 restricciones de traslación por contorno y resolver el sistema orlado (LU denso; con Eigen,
   `PartialPivLU` sobre la matriz orlada). Costo `O(n³)`: con 2000 elementos son 4000 incógnitas y basta una
   factorización densa.
7. Borde: `σtt` por Hooke (§1.8), `σnn = σnt = 0` y desplazamiento en el lado del material.
8. Campo: §1.7 con el remedio de §1.9 si `d < L`, máscara dentro de las excavaciones y `σzz` de deformación plana.
9. Principales `σ1`, `σ3` (y `σz`) → strength factor (§3).
10. Salida en compresión positiva: `σ_API = −σ_núcleo`.

---

## 3. Strength factor

### 3.1 Definición de Rocscience [V1, RSH y RSF]

«The strength factor is calculated by dividing the rock strength (based on your failure criteria) by the induced
stress» (RSH, RS2 y EX3). En un material elástico puede bajar de 1, porque se permite el sobreesfuerzo. **Tracción**:
«Sigma 3 is less than the calculated negative stress (Tension) cutoff for the failure criterion in use» (RSH).

### 3.2 Ecuaciones de RS2 (Phase2 Theory) [V1, RSF p. 1 (Mohr-Coulomb) y p. 3 (Hoek-Brown); compresión positiva]

```
I1 = σxx + σyy + σzz
J2 = (1/6)[(σxx−σyy)² + (σyy−σzz)² + (σzz−σxx)²] + τxy² + τyz² + τzx²
J3 = (σxx−I1/3)(σyy−I1/3)(σzz−I1/3) + 2τxyτyzτzx − (σxx−I1/3)τyz² − (σyy−I1/3)τzx² − (σzz−I1/3)τxy²
Θ  = (1/3)·arcsin[ −3√3·J3 / (2·J2^(3/2)) ],    −π/6 < Θ < π/6
S  = √J2

Mohr-Coulomb (c, φ):
  S_max = [ (I1/3) sinφ + c cosφ ] / [ cosΘ + sinΘ sinφ/√3 ]

Hoek-Brown (m, s, σc; a = 0.5):
  S_max = { √[ (1 + tanΘ/√3)²(mσc/8)² + (mσc·I1/12 + sσc²/4) ] − (mσc/8)(1 + tanΘ/√3) } / cosΘ

strength factor = S_max / S
```

La página 4 da Drucker-Prager (`S_max = k + q·I1/3`), que no hace falta aquí. **Comprobado** (prototipo, `sf.py`): sobre
la envolvente de Mohr-Coulomb (`σ1 = σ3·Nφ + 2c√Nφ`) y de Hoek-Brown con `a = 0.5` (`σ1 = σ3 + σc√(mσ3/σc + s)`), el
SF da 1.000000 con `σ3` = 0, 5 y 20 y con `σ2` = `σ3`, `σ1` o el promedio. Escala `√J2` a `I1` y `Θ` fijos, así que
`σz` entra por `I1`. Es el SF «3D» que menciona RSH.

### 3.3 Definición 2D (la que la UBC describe para Examine2D) [V2, UBC p. 5, paso 10]

«In two dimensions, the strength factor is calculated by dividing the rock strength in terms of the maximum internal
shear (σ1−σ3)/2 at failure for a given confining pressure (σ1+σ3)/2 at a point, by the maximum induced internal shear at
that point.» Es decir, con `σm = (σ1+σ3)/2` y `τ = (σ1−σ3)/2`:
- Mohr-Coulomb [deducida]: `SF = (c cosφ + σm sinφ)/τ`.
- Hoek-Brown generalizado [deducida]: `SF = τf/τ`, donde `τf` resuelve `2τf = σci·(mb(σm−τf)/σci + s)^a` (raíz única;
  se resuelve por bisección).

Las dos definiciones coinciden sobre la envolvente (SF = 1) y difieren fuera de ella. Ejemplo con `σ1 = 40`, `σ3 = 10` y
`σz = 10`: Mohr-Coulomb (c = 5, φ = 30°) da 1.122 en 2D y 1.146 en RS2; Hoek-Brown (m = 10, s = 1, σc = 100) da 2.075
en 2D y 2.457 en RS2. **La fórmula exacta que usa Examine2D no la leí en un documento de Rocscience** [NV]: la de 3.3
viene de unos apuntes de curso.

### 3.4 Tracción [V1 RSH para la regla; V1 HB02 ec. 7]

- Si `σ3 < −T` (compresión positiva), el punto se marca como **tracción** y no se da un SF numérico (o se da 0, con su
  marca).
- Mohr-Coulomb: `T` es la resistencia a tracción que da el usuario (en el laboratorio UBC, «tensile strength = 0 MPa»).
- Hoek-Brown: `σt = −s·σci/mb` (HB02 ec. 7, la resistencia biaxial). Con `a = 0.5`, el radicando de la fórmula de RS2
  `(mσc·I1/12 + sσc²/4)` es negativo cuando `I1/3 < −sσc/m`: es el mismo corte.

**Recomendación**: por defecto, la definición de RS2 (§3.2, [V1], con la ecuación publicada), con `σz` de deformación
plana. Como opción `modo="examine2d"`, la definición 2D de §3.3 [V2]. Para Hoek-Brown generalizado (`a ≠ 0.5`), RSF no
trae fórmula [NV]. Se puede resolver numéricamente con la misma idea: escalar la parte desviadora a `I1` y `Θ` fijos
hasta tocar la envolvente. Las fórmulas cerradas de 3.2 sirven de oráculo para la prueba con `a = 0.5`.

---

## 4. Casos de validación con valores publicados

| Caso | Fuente | Valores esperados | Estado |
|---|---|---|---|
| Kirsch, hidrostático | RS2-S problema 1 [V1] (solo gráficas; números recalculados en 8B §1.3) | a = 1, p = 30, E = 10 000, ν = 0.2: borde σθ = 60.0 y ur = 3.60 mm; en r = 5: σr = 28.8, σθ = 31.2 y ur = 0.72 mm | prototipo OK (§7.1) |
| Kirsch, K ≠ 1 | 8B §1.1 [V1] | hastial 3p2 − p1 y corona 3p1 − p2; campo completo | prototipo OK |
| Cilindro, hidrostático | EX3 ejemplo 1 [V1] | a = 2.5 m, p = 10 MPa, E = 2000, ν = 0.25; solo gráficas de σr y σθ hasta 15 m (Brady y Brown) | = Kirsch |
| Elipse (borde) | 8B §2.1 (CC02 de Inglis) [V1] | a = 2, b = 1, σ1 = 20 vertical, σ3 = 10: hastial 90.0 y corona 0.0. Con σ3 = 20: 80.0 y 20.0. a = 1, b = 2: 30.0 y 30.0. a = 3, b = 1: 130.0 y −3.33 | prototipo OK (§7.3) |
| Dos huecos iguales, hidrostático | LING vía arXiv 1705.10400 ec. 3.23 [V2] | Esfuerzo tangencial total sobre p, en el punto del pilar (θ = π), para gap/r = 2, 1, 0.5 y 0.25: 2.4108, 2.8875, 3.6561 y 4.9095. En θ = π/2: 1.7905, 1.7313, 1.9264 y 2.5439. En el lado exterior (θ = 0): 2.1577, 2.2548, 2.3594 y 2.4616. Tiende a 2 al separar los huecos (gap/r = 50: 2.0014) | calculado de la serie (400 términos); prototipo OK (§7.4) |
| Laboratorio UBC (Examine2D) | UBC [V2] | Geometría y parámetros completos (dos cavernas con sus vértices; σ1 = 40, σ3 = 20 y σz = 30; E = 30 000 y ν = 0.2; HB m = 5, s = 0.02, σc = 40, a = 0.503; MC con T = 0, φ = 30° y c = 10, 5 y 2; 100 elementos por defecto). **No hay resultados publicados** (la hoja de respuestas está en blanco) | sirve como caso de integración, no como oráculo |

Los valores de Ling salen de la serie publicada, no de la tabla original de Ling, que no leí. Que el DDM converja a
ellos (0.22-0.29 % con 512 elementos por hueco) es una validación cruzada de los dos métodos.

---

## 5. Recomendación: DDM, no FSM

**DDM de elemento constante.** Razones:
1. Sus ecuaciones están transcritas de dos fuentes independientes que concuerdan, y el prototipo las valida contra tres
   soluciones exactas.
2. El mismo núcleo sirve después para fallas y juntas (son DD de verdad) sin cambiar de método.
3. Del método de esfuerzo ficticio (FSM) no encontré una fuente pública con sus coeficientes: queda [NV].

**Número de elementos**:
- Error del método `O(L)`: el error se reduce a la mitad cada vez que se duplica N (§7).
- Campo lejano (r ≥ 1.5R): 64 elementos por contorno ya dan menos de 0.6 %.
- Borde con Hooke (§1.8): `L ≤ 0.04·ρ` para menos de 1 %. En un círculo son 128 elementos; en una elipse 2:1, 256
  (por la curvatura en el hastial); en una 3:1, 512.
- Desplazamiento del borde: 256 elementos en el círculo (0.5-0.65 %).
- Valor por defecto propuesto: 128 elementos por contorno, con refinamiento por curvatura. Examine2D usa 100 elementos
  en total por defecto (UBC) [V2].
- Opción barata para las pruebas: la extrapolación de Richardson `2·f(2N) − f(N)` elimina el término `O(L)` (por ejemplo,
  RS2-S p1 en el borde: 2·60.25 − 60.50 = 60.00).

**Cerca del borde**: remedio de §1.9 con `c = 1` (o `c = 2` si N ≥ 256). Enmascarar los puntos dentro de las
excavaciones.

---

## 6. Ecuaciones listas y no listas

| Pieza | Marca | Estado |
|---|---|---|
| DD constante: u, σ, f y derivadas (§1.1-1.3) | V2 (dos fuentes) + prototipo | **listo** |
| Rotación, tracciones y armado (§1.4-1.5) | deducida + MAR V2 | **listo** |
| Restricción de traslación (§1.5) | hallazgo del prototipo | **listo** |
| σtt del borde por Hooke (§1.8) | deducida + prototipo | **listo** |
| Remedio cerca del borde (§1.9) | deducida + prototipo | **listo** |
| SF de RS2, MC y HB a = 0.5 (§3.2) | V1 | **listo** |
| SF 2D estilo Examine2D (§3.3) | V2 | listo como opción |
| SF Hoek-Brown generalizado | numérico, sin fuente | listo como cálculo numérico; sin oráculo publicado |
| FSM | NV | no entra |

---

## 7. Resultados del prototipo

Scripts temporales del prototipo, no publicados
(`ddm.py`, `test_kirsch.py`, `near.py`, `remedy.py`, `test_ellipse_holes.py`, `rs2p1.py`, `sf.py`, `nullspace.py`).
Python con numpy; núcleo en tracción positiva; nodos sobre la curva y el punto medio del elemento 0 en θ = 0.

### 7.1 Kirsch (R = 1, σv = 30, σh = K·σv, E = 10 000, ν = 0.2)

Error = máx|σ_DDM − σ_Kirsch| / máx|σθ_Kirsch| sobre los centros de los elementos (borde) o sobre 72 ángulos (campo, peor
entre σr y σθ).

| K | N | borde, punto medio | borde, 2× | borde, Hooke | ur del borde | r = 1.5R | r = 2R |
|---|---|---|---|---|---|---|---|
| 1 | 64 | 52.9 % | 5.77 % | 1.73 % | 2.64 % | 0.568 % | 0.369 % |
| 1 | 128 | 51.4 % | 2.89 % | **0.83 %** | 1.30 % | 0.290 % | 0.189 % |
| 1 | 256 | 50.7 % | 1.45 % | 0.41 % | **0.65 %** | 0.147 % | 0.095 % |
| 0.5 | 64 | 53.2 % | 6.46 % | 1.37 % | 2.08 % | 0.581 % | 0.365 % |
| 0.5 | 128 | 51.6 % | 3.26 % | **0.66 %** | 1.02 % | 0.286 % | 0.177 % |
| 0.5 | 256 | 50.8 % | 1.63 % | 0.33 % | **0.50 %** | 0.142 % | 0.087 % |

- Poner los puntos medios (y no los nodos) sobre la curva, o usar un polígono de igual área, no mejora nada: el error es
  del método, no de la geometría.
- RS2-S problema 1 (K = 1, p = 30), resultados del DDM:
  - con 64, 128 y 256 elementos, el borde da σθ = 61.04, 60.50 y 60.25 (esperado 60.0) y ur = 3.695, 3.647 y 3.623 mm
    (esperado 3.60);
  - en r = 5, con 256 elementos: σr = 28.794 y σθ = 31.206 (esperado 28.8 y 31.2) y ur = 0.7234 mm (esperado 0.72).

### 7.2 Error cerca del borde (K = 0.5), sin remedio

| N | 0.1L | 0.25L | 0.5L | 1L | 2L | 4L |
|---|---|---|---|---|---|---|
| 64 | 77.6 % | 26.2 % | 7.8 % | 1.64 % | 0.79 % | 0.65 % |
| 128 | 76.9 % | 26.3 % | 7.4 % | 1.13 % | 0.44 % | 0.39 % |
| 256 | 75.8 % | 26.2 % | 7.4 % | 0.86 % | 0.23 % | 0.22 % |

Con el remedio de §1.9 y `c = 1`:

| N | borde | 0.1L | 0.25L | 0.5L | 1L | 1.5L |
|---|---|---|---|---|---|---|
| 64 | 1.37 % | 1.48 % | 1.80 % | 2.02 % | 1.64 % | 0.89 % |
| 128 | 0.66 % | 0.72 % | 0.84 % | 0.96 % | 1.13 % | 0.49 % |
| 256 | 0.33 % | 0.37 % | 0.44 % | 0.54 % | 0.86 % | 0.28 % |

Con `c = 2`, los errores máximos son 3.68 %, 1.31 % y 0.49 % con 64, 128 y 256 elementos.

### 7.3 Elipse (borde por Hooke; nodos en ángulo paramétrico uniforme)

| a, b, σ1 (vertical), σ3 | N | hastial (exacto) | error | corona (exacto) | error / hastial |
|---|---|---|---|---|---|
| 2, 1, 20, 10 | 128 | 91.98 (90.00) | +2.20 % | 0.10 (0.00) | +0.11 % |
| 2, 1, 20, 10 | 256 | 90.98 | +1.09 % | 0.05 | +0.05 % |
| 2, 1, 20, 10 | 512 | 90.49 | +0.54 % | 0.02 | +0.03 % |
| 2, 1, 20, 20 | 256 | 80.92 (80.00) | +1.15 % | 20.03 (20.00) | +0.03 % |
| 1, 2, 20, 10 | 256 | 29.99 (30.00) | −0.03 % | 30.39 (30.00) | +1.30 % |
| 3, 1, 20, 10 | 256 | 132.44 (130.00) | +1.88 % | −3.28 (−3.33) | +0.04 % |
| 3, 1, 20, 10 | 512 | 131.21 | +0.93 % | −3.31 | +0.02 % |

En todo el borde, el DDM coincide con la fórmula de 8B §2.1 **si θ es el ángulo excéntrico (paramétrico)**,
`x = a cos θ`, `y = b sin θ`. Con θ polar, el error llega a 24-51 %.

### 7.4 Dos huecos iguales (radio 1, campo hidrostático p = 1 en compresión; borde por Hooke)

| gap/r | N por hueco | pilar DDM | Ling | error | máx|err|/máx en todo el borde |
|---|---|---|---|---|---|
| 2 | 128 / 256 / 512 | 2.4324 / 2.4215 / 2.4162 | 2.4108 | +0.89 / +0.44 / +0.22 % | 0.89 / 0.44 / 0.22 % |
| 1 | 128 / 256 / 512 | 2.9145 / 2.9012 / 2.8944 | 2.8875 | +0.94 / +0.47 / +0.24 % | igual |
| 0.5 | 128 / 256 / 512 | 3.6922 / 3.6750 / 3.6658 | 3.6561 | +0.99 / +0.52 / +0.26 % | igual |
| 0.25 | 128 / 256 / 512 | 4.9563 / 4.9361 / 4.9236 | 4.9095 | +0.95 / +0.54 / +0.29 % | igual |

**Elementos para menos de 1 %**:
- campo a 1.5R o más: 64;
- borde con Hooke: 128 en círculos y dos huecos, 256 en una elipse 2:1 y 512 en una 3:1 (regla `L ≤ 0.04ρ`);
- `ur` del borde: 256;
- puntos cerca del borde con remedio: 128 o más.

---

## 8. Lo que queda [NV]

1. Crouch (1976) y Crouch y Starfield (1983) como originales: las ecuaciones entran por YAN y JH (V2).
2. Coeficientes del método de esfuerzo ficticio (FSM).
3. La fórmula exacta del strength factor de Examine2D: solo tengo la descripción de UBC (V2) y la de RS2 (V1).
4. El strength factor de Hoek-Brown generalizado (a ≠ 0.5) en la forma 3D de RS2: no hay ecuación publicada; queda
   como cálculo numérico.
5. La tabla original de Ling (1948): uso la serie reproducida en arXiv 1705.10400.
6. Resultados numéricos del laboratorio UBC (no publicados).
7. La regla de Crouch y Starfield sobre la distancia mínima al borde.
8. El campo gravitacional de Examine2D (in situ que varía con la profundidad): el método es el mismo (`t⁰` evaluado en
   cada elemento), pero no lo probé.

## 9. Erratas y aclaraciones (no usar como valor esperado)

| Fuente | Problema | Qué se usa |
|---|---|---|
| YAN pp. 652-653 | «Scouch (1976)» y «Scouch et al. (1983)» por Crouch | Crouch |
| YAN ecs. 4-5 (y JH) | `arctan(y/(x∓a))` escrito sin rama; con el arctan principal, `f,y` no salta sobre el elemento y los desplazamientos salen mal | `atan2(y, x∓a)` |
| YAN ec. 4 vs JH ec. 6 | la `f` cerrada omite la constante `2a/(4π(1−ν))` de la integral | sin efecto (solo se usan derivadas) |
| arXiv 1705.10400 ec. 3.23 | rotulada `σ¹θθ` (la perturbación), pero su valor es el esfuerzo tangencial **total** (`σ⁰ + σ¹`): tiende a 2 (Kirsch) al separar los huecos y coincide con el DDM | esfuerzo total |
| 8B §2.1 (aclaración, no errata de CC02) | «θ desde el eje x» es ambiguo; la fórmula de Inglis vale con el ángulo excéntrico | θ paramétrico |
| UBC, hoja de respuestas | en blanco: no hay valores esperados | solo geometría y parámetros |
