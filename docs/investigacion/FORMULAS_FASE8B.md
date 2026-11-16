# Fórmulas de la Fase 8B: excavaciones subterráneas

Investigación y verificación de fórmulas para la Fase 8B (soluciones analíticas de excavaciones subterráneas).
Fecha: 14-nov-2026. Solo documentos públicos; no se tocó ninguna carpeta de clientes.

**Marcas.** [V1] leída en el original o en la copia que publica el autor o el editor (en este informe, siempre leída
sobre la imagen de la página, no sobre el texto extraído). [V2] fuente secundaria seria; entra como «secundaria».
[NV] no verificada; no entra.

**Convención común.** Compresión positiva. Desplazamiento radial `u` positivo hacia el interior del túnel (convergencia).
Unidades: MPa, m, MN. Deformación plana. «Recalculado» = lo calculé en Python local con la fórmula transcrita y lo
comparé con el número publicado.

**Fuentes leídas (todas públicas):**

| Clave | Documento | Dónde |
|---|---|---|
| RS2-S | Rocscience (2021), *RS2 Stress Analysis Verification Manual*, 193 pp. | `docs/investigacion/pdfs/Rocscience_RS2_Stress_Verification_2021.pdf` (página PDF = página impresa) |
| RSV | Rocscience, *RocSupport Verification Manual* v4.0 | `docs/investigacion/pdfs/Rocscience_RocSupport_Verification_v4.pdf` |
| RST | Rocscience, *RocSupport Tutorial Manual* (versión de la serie 3; página impresa = página PDF − 4) | rocscience.com/downloads/rocsupport/RocSupport%20Tutorial.pdf |
| PRE | Hoek, E. (2007), *Practical Rock Engineering*, cap. «Tunnels in weak rock» (pp. 1-21 del capítulo = pp. 237-257 del PDF completo) | rocscience.com/assets/resources/learning/hoek/Practical-Rock-Engineering-Full-Text.pdf |
| KL08 | Hoek, Carranza-Torres, Diederichs y Corkum (2008), *Integration of geotechnical and structural design in tunnelling*, 56th Minnesota Geotech. Conf., copia del autor (página impresa = PDF − 1) | d.umn.edu/~carranza/KL08 |
| CC02 | Fairhurst y Carranza-Torres (2002), *Closing the circle*, 50th Minnesota Geotech. Conf., copia del autor | d.umn.edu/~carranza/CC02 |
| OR09 | Oreste, P. (2009), The convergence-confinement method: roles and limits..., *Am. J. Applied Sci.* 6(4), 757-771 (acceso abierto del editor) | thescipub.com/pdf/ajassp.2009.757.771.pdf |
| UBC | Eberhardt, E. (2014), *Topic 7 – Ground Reaction Curves*, apuntes de curso UBC EOSC 547 (reproduce un ejemplo de Harrison y Hudson 2000) | eoas.ubc.ca/courses/eosc547/lecture-material/Topic7-GroundReactionCurves.pdf |
| HELP | Ayuda en línea de RocSupport (páginas *Support behaviour* y *Longitudinal deformation profile*) | rocscience.com/help/rocsupport/... |

**Lo que no pude abrir** (no hay copia pública del autor ni del editor; solo copias en Scribd, que no cuentan):
Carranza-Torres y Fairhurst (2000) *TUST* 15(2); Carranza-Torres y Fairhurst (1999) *IJRMMS* 36; Carranza-Torres (2004)
*IJRMMS* 41(S1); Carranza-Torres (2009) *RMRE* 42; Carranza-Torres y Diederichs (2009) *TUST* 24; Vlachopoulos y
Diederichs (2009) *RMRE* 42; Hoek y Marinos (2000) *T&T International*; Hoek y Brown (1980); Brady y Brown; Panet (1995);
Hoek, Kaiser y Bawden (1995). Donde un método depende de ellos, uso la copia del autor que los reproduce (KL08, CC02) o
lo marco [NV].

---

## 1. Kirsch: hueco circular en medio elástico

### 1.1 Ecuaciones [V1, RS2-S p. 8; también CC02 p. 26, Fig. 1b]

Hueco de radio `a`, esfuerzo `p1` horizontal (eje x) y `p2` vertical, `θ` medido desde el eje x, `G = E/(2(1+ν))`:

```
σr  = (p1+p2)/2·(1 − a²/r²) + (p1−p2)/2·(1 − 4a²/r² + 3a⁴/r⁴)·cos2θ
σθ  = (p1+p2)/2·(1 + a²/r²) − (p1−p2)/2·(1 + 3a⁴/r⁴)·cos2θ
τrθ = −(p1−p2)/2·(1 + 2a²/r² − 3a⁴/r⁴)·sin2θ
ur  = (p1+p2)/(4G)·a²/r + (p1−p2)/(4G)·(a²/r)·[4(1−ν) − a²/r²]·cos2θ
```

`ur` es el desplazamiento inducido por la excavación (cero antes de excavar), positivo hacia el centro.
Borde (r = a): `σθ = (p1+p2) − 2(p1−p2)cos2θ`; hastial (θ = 0) `3p2 − p1`; corona (θ = 90°) `3p1 − p2`.
CC02 escribe lo mismo con σ1 vertical y σ3 horizontal.

### 1.2 Validez
Elástico lineal, isótropo, medio infinito, deformación plana, esfuerzos principales alineados con los ejes, sin presión interna.

### 1.3 Caso de prueba [V1, RS2-S problema 1, pp. 7-11]
Entradas: a = 1 m, p1 = p2 = 30 MPa, E = 10 000 MPa, ν = 0.2. La página publica solo gráficas (Figs. 1.3-1.5) y el
error de RS2 (Tabla 1.2), no una tabla de valores analíticos.

Recálculo: borde σθ = 60.0 MPa, σr = 0, ur = 3.60 mm; en r = 5 m, σr = 28.8 y σθ = 31.2 MPa, ur = 0.72 mm.
Coincide con las gráficas (eje de desplazamiento hasta 0.004 m, σθ máximo de 60). Prueba con K ≠ 1 (p1 = 10, p2 = 20):
hastial 50, corona 10 = 3p2 − p1 y 3p1 − p2. **Listo para implementar.**

---

## 2. Elipse: esfuerzo de borde

### 2.1 Ecuación [V1, CC02 p. 26, Fig. 1c, «adaptado de Inglis (1913)»]

Semieje horizontal `a`, vertical `b`, σ1 vertical, σ3 horizontal, `θ` desde el eje x:

```
σθ_borde(θ) = (σ1+σ3) − [(a−b)(σ1+σ3) + (a+b)(σ1−σ3)]·(a·sin²θ − b·cos²θ)/(a²·sin²θ + b²·cos²θ)
```

**Aclaración (14-nov, FORMULAS_FASE8C §7.3):** la fórmula vale con θ = ángulo **excéntrico (paramétrico)** del
punto, `x = a cos θ`, `y = b sin θ`, no con el ángulo polar. Con el polar el error llega a 24-51 % en ángulos
intermedios. La librería recibe el ángulo polar φ y lo convierte: θ = atan2(a·sin φ, b·cos φ).

Extremos de los ejes (deducidos de la misma fórmula; con p = σ1, K = σ3/σ1, q = W/H = a/b):
- extremo del eje horizontal (hastial, θ = 0): `σ = σ1(1 + 2a/b) − σ3 = p(1 − K + 2q)`;
- extremo del eje vertical (corona, θ = 90°): `σ = σ3(1 + 2b/a) − σ1 = p(K − 1 + 2K/q)`.

Son las expresiones que suelen citarse de Hoek y Brown (1980) y Brady y Brown, cuyo original no leí: la forma de los
extremos queda [V1] por deducción directa de CC02, no por lectura de esos libros.

### 2.2 Validez
Elástico, medio infinito, ejes de la elipse alineados con los esfuerzos principales. Solo el borde (no da el campo).

### 2.3 Casos de prueba
No encontré un número publicado para una elipse. Pruebas de consistencia que da la propia fuente:
- a = b se reduce a Kirsch: σ1 = 20, σ3 = 10 → hastial 50, corona 10. Recalculado: igual.
- «Hueco armónico» (CC02, nota de la Fig. 1c): si b/a = σ1/σ3, σθ = σ1 + σ3 constante. Recalculado con a = 1, b = 2,
  σ1 = 20, σ3 = 10: 30.0 en θ = 0, 0.3, 0.9 y π/2.
- a = 2, b = 1, σ1 = 20, K = 0.5: hastial 90.0 = p(1 − K + 2q); corona 0.0 = p(K − 1 + 2K/q).

**Listo para implementar (borde).** El campo completo alrededor de la elipse queda fuera (va a la 8C con elementos de contorno).

---

## 3. GRC de Mohr-Coulomb

### 3.1 Qué fórmula usa cada fuente

| Fuente | Rp | Desplazamiento en la pared | Dilatancia |
|---|---|---|---|
| Salençon (1969) según RS2-S, problema 2 [V1 de la transcripción, NV del original] | sí | sí, en cualquier r (elástico y plástico) | sí, con Kψ |
| Duncan Fama (1993) según Hoek, PRE ec. 4-7 [V1 de la transcripción] | sí | sí, solo en la pared | **no** (ψ = 0, «zero plastic volume change») |
| RocSupport «Duncan-Fama» (RSV problema 5) | sí | sí | sí: la curva de RSV Fig. 5-1 coincide con la fórmula de Salençon con Kψ (ver 3.5) |
| Carranza-Torres (2003) *RMRE* 36 (adimensional) | — | — | [NV], no leído |
| Vrakas y Anagnostou (2014), grandes deformaciones | — | — | [NV], solo citado en RSV |

Rp de Salençon y de Duncan Fama es la **misma** expresión. Con ψ = 0 el desplazamiento de Salençon en r = a es
**idéntico** al de Hoek ec. 7 (comprobado numéricamente: 0.066998 m en ambos para el caso Soria con ψ = 0).

### 3.2 Ecuaciones

Comunes [V1, PRE pp. 3-4, ec. 1-6, pp. 239-240 del PDF; RS2-S p. 14]:

```
k   = (1 + sinφ)/(1 − sinφ)              (RS2-S lo llama Kp)
σcm = 2c·cosφ/(1 − sinφ)                 (RS2-S lo llama q = 2c·tan(45 + φ/2), es lo mismo)
pcr = (2p0 − σcm)/(1 + k)                 presión crítica; si pi ≥ pcr todo es elástico
rp  = R·[ 2(p0(k−1) + σcm) / ((1+k)((k−1)pi + σcm)) ]^(1/(k−1))
```

Elástico (pi ≥ pcr) [V1, PRE ec. 5]: `u = R(1+ν)(p0 − pi)/Em`.

Plástico sin dilatancia [V1, PRE ec. 7, p. 4]:
```
u = R(1+ν)/E · [ 2(1−ν)(p0 − pcr)(rp/R)² − (1−2ν)(p0 − pi) ]
```

Plástico con dilatancia, en cualquier radio a ≤ r ≤ R0 [V1, RS2-S p. 15; `Kps = (1+sinψ)/(1−sinψ)`, `a` = radio del
túnel, `R0` = rp, `Pi` = presión interna, `q` = σcm]:
```
u(r) = r/(2G)·[ (2ν−1)(P0 + q/(Kp−1))
              + (1−ν)(Kp²−1)/(Kp+Kps) · (Pi + q/(Kp−1)) · (R0/a)^(Kp−1) · (R0/r)^(Kps+1)
              + ( (1−ν)(Kp·Kps+1)/(Kp+Kps) − ν ) · (Pi + q/(Kp−1)) · (r/a)^(Kp−1) ]
```
En la pared se usa r = a. Esfuerzos [V1, RS2-S p. 14]: zona plástica
`σr = −q/(Kp−1) + (Pi + q/(Kp−1))(r/a)^(Kp−1)`, `σθ = −q/(Kp−1) + Kp(Pi + q/(Kp−1))(r/a)^(Kp−1)`;
zona elástica `σr,θ = P0 ∓ (P0 − σre)(R0/r)²`, `σre = (2P0 − q)/(Kp+1)`; elástica `u = R0²/(2G)·(P0 − σre)/r`.

### 3.3 Validez
Túnel circular, esfuerzo hidrostático (K = 1), elástico-perfectamente plástico, plasticidad no asociada lineal,
pequeñas deformaciones (RSV problema 5 muestra hasta 15 % de error frente al FEM con ψ grande y convergencias grandes),
deformación plana, sin efecto del frente. La dilatancia no cambia rp.

### 3.4 Casos de prueba y recálculo

| Caso | Entradas | Publicado | Recalculado | ¿Coincide? |
|---|---|---|---|---|
| RSV problema 5, Tabla p. 8 [V1] | R = 1, E = 10 000, ν = 0.2, φ = 30°, c = 3.45, p0 = 30 | rp D-F = 1.74 m | 1.735 | sí |
| idem | c = 3.45, p0 = 20 | 1.47 | 1.474 | sí |
| idem | c = 5, p0 = 30 | 1.49 | 1.494 | sí |
| idem | c = 5, p0 = 20 | 1.29 | 1.286 | sí |
| RSV Fig. 5-1, p. 9 (lectura de gráfica) | c = 3.45, p0 = 30, ψ = 0 y 30° | u ≈ 8.2 y ≈ 19 mm | 8.24 y 19.09 mm (Salençon con Kψ) | sí (dentro de la lectura) |
| RSV Fig. 5-2 (lectura) | c = 3.45, p0 = 20, ψ = 0 y 30° | u ≈ 4.0 y ≈ 6.8 mm | 3.98 y 6.80 mm | sí |
| RS2-S problema 2, Figs. 2.4 y 2.7 (lectura) | a = 1, P0 = 30, E = 10 000, ν = 0.2, c = 3.45, φ = 30°, ψ = 0 y 30° | escalas hasta 0.009 y 0.025 m | 8.24 y 19.09 mm | compatible |
| PRE Fig. 4, p. 5 (hoja de cálculo de Hoek) [V1] | σci = 10, mi = 10, GSI = 25, ν = 0.3, ro = 3, po = 2, pi = 0 (ajuste lineal de HB con 8 puntos, fórmulas de celda en la misma figura) | mb 0.69, a 0.525, k 2.44, φ 24.72°, c 0.22, σcm 0.69, E 749.9, pcr 0.96, rp 6.43 m, ui 0.0306 m (30.5957 mm), ui/ro 0.0102 | mb 0.687, a 0.525, k 2.437, φ 24.72°, c 0.222, σcm 0.694, E 749.9, pcr 0.962, rp 6.433, ui 0.03060 | sí |
| RST Ejemplo 1, pp. 22-35 [V1] | R = 6, p0 = 1.62, E = 352.817, σcm = 0.46927, φ = 25.6394°, ν = 0.3 (por defecto, p. 22) | rp 13.77 m (13.8), convergencia 2.03 % | rp 13.78 m, u/R 2.030 % | sí |

Nota del Ejemplo 1 de RST: los parámetros salen de la calculadora de RocSupport (p. 25) con σci = 7, GSI = 15, mi = 10,
D = 0. Los reproduje con Hoek-Carranza-Corkum (2002): E = 352.817 (fórmula de Erm de 2002), «UCS of rock mass» =
**σcm global** 0.46927 y φ = 25.6394° del ajuste con σ3max = 0.47·σcm·(σcm/p0)^−0.94. Ojo: RocSupport mezcla el σcm global
con el φ del ajuste; el `2c·cosφ/(1−sinφ)` del mismo ajuste daría 0.283, no 0.469. RockMassPy debe reproducir esa mezcla
si quiere coincidir con RocSupport, y decirlo.

### 3.5 Caso de tesis: Soria Medina (2023, UNAM)
Entradas: R = 5 m, p0 = 4.05 MPa, Em = 446 MPa, ν = 0.3, c = 1 MPa, φ = 37°, ψ = 6°. Publicado con RocSupport v5:
Rp = 5.86 m, u = 68.05 mm.

Recálculo: k = 4.0228, σcm = 4.0114 MPa, pcr = 0.8140 MPa, **rp = 5.8573 m**.
- Hoek PRE ec. 7 (sin dilatancia): u = **67.00 mm** (no coincide).
- **Salençon con Kψ (RS2-S p. 15), Kψ = 1.2335: u = 68.049 mm → 68.05 mm. Coincide.**

Conclusión: el «Duncan-Fama» de RocSupport con dilatancia es la fórmula de Salençon de RS2-S p. 15 (lo confirman también
las curvas de RSV Fig. 5-1 y 5-2). La de 67.00 mm solo vale con ψ = 0. **Listo para implementar.**

---

## 4. GRC de Hoek-Brown con a = 0.5

### 4.1 Carranza-Torres y Fairhurst (transformación de Londe) [V1, CC02 pp. 53-55, ec. 5-11]

El artículo de 2000 (*TUST*) no tiene copia pública del autor; CC02 (copia del autor, coautor Carranza-Torres) reproduce
las mismas ecuaciones «presented here without details», citando a Carranza-Torres y Fairhurst (1999).

```
Pi    = pi/(mb·σci) + s/mb²                     So = σo/(mb·σci) + s/mb²
Pi_cr = (1/16)·[1 − √(1 + 16·So)]²
pi_cr = (Pi_cr − s/mb²)·mb·σci
elástico (pi > pi_cr):  u = (σo − pi)·R/(2Grm)
Rpl   = R·exp[ 2(√Pi_cr − √Pi) ]
Kψ    = (1 + sinψ)/(1 − sinψ)

u·2Grm/(R(σo − pi_cr)) = (Kψ−1)/(Kψ+1) + 2/(Kψ+1)·(Rpl/R)^(Kψ+1)
      + (1−2ν)/(4(So − Pi_cr))·[ln(Rpl/R)]²
      − [ (1−2ν)/(Kψ+1)·√Pi_cr/(So − Pi_cr) + (1−ν)/2·(Kψ−1)/(Kψ+1)²·1/(So − Pi_cr) ]
        × [ (Kψ+1)·ln(Rpl/R) − (Rpl/R)^(Kψ+1) + 1 ]
```

Validez: túnel circular, hidrostático, Hoek-Brown con a = 0.5 (no generalizado), perfectamente plástico (sin
ablandamiento), flujo con ψ constante, pequeñas deformaciones.

**Caso de prueba [V1, CC02 pp. 55-58]:** R = 3.82 m, σo = 30 MPa, pi = 5 MPa, σci = 30, mb = 1.7, s = 3.9·10⁻³,
a = 0.5, ψ = 0, Grm = 1 GPa, ν = 0.25. Publicado: So ≈ 0.6, Pi ≈ 0.1, Pi_cr = 0.32, pi_cr = 16 MPa, Rpl/R = 1.64,
Rpl = 6.26 m, u·2G/(R(σo − pi_cr)) = 3.1, u = 0.08 m (los dos últimos leídos por los autores de los ábacos).

Recálculo exacto: So = 0.5896, Pi = 0.0994, Pi_cr = 0.3108, pi_cr = 15.78 MPa, Rpl/R = 1.623 (Rpl = 6.20 m),
f = 3.074, u = 0.0835 m. Con So = 0.6 y Pi = 0.1 redondeados como en el texto: Pi_cr = 0.318 y Rpl/R = 1.641.
**Coincide** dentro del redondeo y de la lectura de ábacos que hacen los propios autores. El test debe usar los valores
exactos (1.623; 3.07; 0.0835) con tolerancia de 2 % contra los publicados, no los publicados como valor exacto.

### 4.2 Hoek y Brown (1982), con resistencia residual [V1, RS2-S p. 22, problema 3]

Solo esfuerzos (no hay desplazamiento en el manual). Pico m, s; residual mr, sr:
```
M   = ½·[ (m/4)² + m·P0/σc + s ]^½ − m/8
N   = 2/(mr·σc)·( mr·σc·P0 + sr·σc² − mr·σc²·M )^½
re  = a·exp[ N − 2/(mr·σc)·( mr·σc·Pi + sr·σc² )^½ ]
σre = P0 − M·σc
elástico:  σr,θ = P0 ∓ (P0 − σre)(re/r)²
plástico:  σr = (mr·σc/4)·[ln(r/a)]² + ln(r/a)·( mr·σc·Pi + sr·σc² )^½ + Pi
           σθ = σr + ( mr·σc·σr + sr·σc² )^½
```
Caso [V1, RS2-S p. 21, Tabla 3.1]: P0 = 30, a = 1, E = 10 000, ν = 0.25, σc = 100, m = 2.515, s = 0.003865, mr = 0.5,
sr = 1·10⁻⁵ (la tabla imprime «1e10⁻⁵»; lo leo como 1×10⁻⁵, que es lo que cuadra con las gráficas).
Recálculo: M = 0.22268, re = 2.168 m, σre = 7.73 MPa, salto de σθ en re de 27.4 (plástico) a 52.3 MPa (elástico);
en r = 5 m σr = 25.8 y σθ = 34.2. Las Figs. 3.2 y 3.3 (p. 24) muestran el salto entre 2.1 y 2.3 m, σr ≈ 8 en el
quiebre y 25.7/34 en r = 5. **Coincide (lectura de gráfica).** Sirve para probar esfuerzos con ablandamiento frágil.

---

## 5. Hoek-Brown generalizado (a ≠ 0.5)

- **Carranza-Torres (2004)** [NV]: según el resumen público y la ayuda de RocSupport, reescribe el criterio con esfuerzos
  transformados y **requiere integración numérica**; Chen y Tonon (2011, *RMRE*) dicen haber dado luego una forma cerrada
  [NV]. No hay copia pública del autor: no se implementa la fórmula.
- **Lee y Pietruszczak (2008)** [NV]: método numérico por anillos con ablandamiento; RSV problema 4 (p. 6-7) lo compara con
  Carranza-Torres (2004). Datos [V1, RSV p. 6]: R = 2 m, E = 5700 MPa, σ0 = 15 MPa, σci = 30/30, mb = 1.7/0.85,
  s = 0.0039/0.0019, a = 0.55/0.6 (pico/residual), ψ = 0, ν = 0.25. Resultado solo en gráfica (Fig. 4-1, p. 7):
  presión crítica ≈ 6.3 MPa a ≈ 4 mm y u ≈ 32 mm con pi ≈ 0.5 MPa (lectura aproximada). Sirve como referencia gruesa
  para una implementación numérica futura, no como valor exacto.
- **Lo que sí se puede hacer ahora [V1]:** el camino de RocSupport en su Ejemplo 1: Hoek-Brown 2002 → σcm global, φ del
  ajuste con σ3max de túneles y Erm de 2002 → GRC de Mohr-Coulomb (sección 3). Recalculado y coincide (3.4).
- **Recomendación:** en la 8B, HB generalizado = «equivalente Mohr-Coulomb» (marcado así en la salida). La solución
  rigurosa (integración numérica tipo Lee-Pietruszczak) queda para una fase posterior, con RSV problema 4 como prueba
  gráfica.

---

## 6. Frágil-plástico de Reed

### 6.1 Ecuaciones [V1, RS2-S p. 176, problema 30; Reed (1986) NV como original]
Pico c, φ; residual c′ con el mismo φ en el ejemplo; `k = (1+sinφ)/(1−sinφ)`, `σc = 2c·cosφ/(1−sinφ)`,
`σ′c = 2c′·cosφ/(1−sinφ)`, `p′ = σ′c/(k−1)`, `p` = presión en r = ro, `r̄` = radio elastoplástico:
```
elástico:  σr = q − (r̄/r)²·[(k−1)q + σc]/(k+1)
           σθ = q + (r̄/r)²·[(k−1)q + σc]/(k+1)     (el manual lo rotula «σc» por errata)
plástico:  σr = (p + p′)(r/ro)^(k−1) − p′
           σθ = k(p + p′)(r/ro)^(k−1) − p′
r̄ se obtiene igualando σr en r̄:  (p + p′)(r̄/ro)^(k−1) − p′ = (2q − σc)/(k+1)
```
El manual no da el desplazamiento (la Fig. 30.4 lo grafica sin fórmula): **desplazamiento de Reed [NV]**.

### 6.2 Caso de prueba y **errata del manual**
La Tabla 30.1 (p. 175) dice ro = 2 m y q = 30 MPa (c pico 30, residual 5 MPa, φ = 30°). Con esos datos **no hay
plastificación**: σθ en la pared = 2q = 60 < σc = 103.9 MPa. Las gráficas (Figs. 30.2 y 30.3, p. 178) empiezan en
r = 4 m y tienden a 100 MPa. Con **ro = 4 m y q = 100 MPa** recalculo: r̄ = 7.77 m, σθ máximo elástico = 176.0 MPa,
σθ plástico en r̄ = 89.4, σθ en la pared = 17.3, σr(14 m) = 76.6 y σθ(14 m) = 123.4. Las gráficas muestran r̄ ≈ 7.8,
pico ≈ 177, ≈ 87 antes del salto, ≈ 19 en la pared, 77 y ≈ 123 en 14 m. **Coincide con ro = 4 m y q = 100 MPa.**
El test se escribe con esos valores y una nota que diga que la tabla del manual tiene errata (regla: una errata nunca es el
valor esperado). Solo esfuerzos: listo para implementar; desplazamiento no.

---

## 7. LDP: perfil longitudinal de desplazamiento

Todas leídas en KL08, Apéndice 1 (pp. 39-46), que según el propio texto es un extracto de Vlachopoulos y Diederichs
(2008); Diederichs es coautor de KL08, así que la copia vale como copia del autor [V1]. El artículo de 2009 en *RMRE* no
lo pude abrir; las ecuaciones de 2009 que se citan en la literatura son las mismas.

`X*` = dt = X/R (X positivo hacia el interior del túnel ya excavado, negativo delante del frente), `u/umax`.

- **Panet (1995)** [V1 por KL08 ec. A1.1, p. 39]: `u/umax = 1/4 + 3/4·[1 − (3/(3 + 4X*))²]` para X* ≥ 0 (elástico).
- **Unlu y Gercek (2003)** [V1 por KL08 ec. A1.2-A1.3, p. 39]: X < 0: `u/umax = u0/umax + Aa(1 − e^(Ba·X*))`;
  X > 0: `u/umax = u0/umax + Ab(1 − (Bb/(Bb + X*))²)`; `u0/umax = 0.22ν + 0.19`, `Aa = −0.22ν − 0.19`,
  `Ba = 0.73ν + 0.81`, `Ab = −0.22ν + 0.81`, `Bb = 0.39ν + 0.65`.
- **Ajuste a Chern et al. (1998)** [V1 por KL08 ec. A1.4, p. 40]: `u/umax = (1 + e^(−X*/1.10))^(−1.7)`.
- **Vlachopoulos y Diederichs** [V1 por KL08 ec. A1.5-A1.7, pp. 44 y 46], `R* = Rp/R` (radio plástico **máximo**, sin
  sostenimiento):
  ```
  u0/umax = (1/3)·e^(−0.15·R*)
  X* ≤ 0:  u/umax = (u0/umax)·e^(X*)
  X* ≥ 0:  u/umax = 1 − (1 − u0/umax)·e^(−3X*/(2R*))
  inversas: X* = ln(u/u0) (u < u0);  X* = −(2/3)·R*·ln[(umax − u)/(umax − u0)] (u > u0)
  ```
Validez: túnel circular, hidrostático, excavación a sección completa; KL08 advierte que Panet y Unlu-Gercek valen solo si
Rp ≤ 2R, y que el paso de excavación cambia el perfil (Fig. A1.7).

Ayuda de RocSupport [V1, HELP]: Vlachopoulos y Diederichs (2009) es el método por defecto; Chern et al. (1998) era el
defecto en la versión 3.007 y anteriores.

**Casos de prueba:**
- KL08 p. 9 [V1]: «Rp/Rt ≈ 2 → closure at the face approximately one quarter of the final closure». Recalculado:
  u0/umax = 0.247. Coincide.
- RST Ejemplo 1 (pernos instalados a 3 m del frente, ver sección 9): con el LDP de Chern se reproducen FS = 1.84 y las
  demás salidas; con Vlachopoulos-Diederichs sale FS = 1.92 y con Panet 5.24. Confirma que ese tutorial (serie 3) usaba
  Chern, como dice la ayuda.
- Valores de control (recalculados, para tests de regresión): Panet en X* = 0 / 1 / 2: 0.2500 / 0.8622 / 0.9442;
  V-D con R* = 1: X* = −1 / 0 / 1: 0.1055 / 0.2869 / 0.8409; V-D con R* = 2.5: 0.0843 / 0.2291 / 0.5769;
  Chern: 0.1199 / 0.3078 / 0.5624.

**Listo para implementar** (Panet, Unlu-Gercek, Chern y V-D).

---

## 8. SCC: curvas de los sostenimientos

### 8.1 Modelo de RocSupport (el que se puede verificar entero) [V1]
- Cada sostenimiento es elástico-perfectamente plástico con dos datos: **presión máxima psm** y **deformación media
  máxima εsm** (RST pp. 32-33; HELP *Support behaviour*). Rigidez = psm/εsm (RST p. 36: «the slope of the elastic
  portion... is equal to the Maximum Support Pressure divided by the Maximum Average Strain»). En desplazamiento:
  `p = psm·(u − u_in)/(εsm·R)` hasta `p = psm`.
- `u_in` sale del LDP en la distancia de instalación al frente (RST p. 36).
- **psm** sale de la tabla de Hoek, PRE Fig. 8, p. 10 (p. 246 del PDF) [V1], que RST atribuye a «Hoek, 1999b». Ejemplos:
  perno de 34 mm `0.354/s²`, 25 mm `0.267/s²`, 19 mm `0.184/s²`, 17 mm `0.10/s²`, Split set SS39 `0.05/s²`, Swellex EXX
  `0.11/s²`, barra de 20 mm `0.17/s²`, fibra de vidrio 22 mm `0.26/s²`, cable simple `0.15/s²`, cable *birdcage* `0.30/s²`;
  cerchas: ala ancha 305 mm `19.9·D^−1.23/s`, ... ; shotcrete u hormigón: 1 m/28 d/35 MPa `57.8·D^−0.92`, 300 mm `19.1·D^−0.92`,
  150 mm `10.6·D^−0.97`, 100 mm `7.3·D^−0.98`, 50 mm/28 d `3.8·D^−0.99`, 50 mm/3 d/11 MPa `1.1·D^−0.97`,
  50 mm/0.5 d/6 MPa `0.6·D^−1.0` (D = diámetro en m, s = espaciamiento en m). La tabla completa (19 cerchas/pernos y
  7 revestimientos) se copia literal de esa página.
- **εsm:** solo dos valores publicados en lo que leí: perno de 34 mm = 0.2 %, shotcrete de 50 mm a 28 días = 0.1 %
  (RST pp. 33 y 38). La tabla completa de εsm de Hoek (1999b) **[NV]**.
- Caso [V1, RST pp. 33 y 38]: D = 12 m, shotcrete de 50 mm a 28 días → psm = 0.325 MPa. Recalculado:
  3.8·12^−0.99 = 0.3246. Coincide. Perno de 34 mm a 1 × 1 m → 0.354. Coincide.

Diferencia que hay que respetar: la tabla de Hoek **no** es la fórmula de anillo grueso de Lamé (8.2). Con 300 mm y
35 MPa: D = 4 m, tabla 5.34 frente a Lamé 4.86; D = 10 m, 2.30 frente a 2.04 (entre 10 y 17 % más). Son dos modelos
distintos; no se mezclan en un mismo test.

### 8.2 Revestimiento de shotcrete u hormigón como anillo grueso [V2]
Rigidez [V2, UBC diapositivas 20-22, que reproduce a Harrison y Hudson (2000)]; es la misma forma que se cita de
Hoek y Brown (1980) y de Carranza-Torres y Fairhurst (2000) [NV en esos originales]:
```
k  = Ec/(1+νc) · [a² − (a − tc)²] / [(1 − 2νc)·a² + (a − tc)²]        (MPa)
pr = k·(u − u0)/a
```
Presión máxima del anillo grueso, `pmax = (σcc/2)·[1 − (a − tc)²/a²]` (Lamé: esfuerzo tangencial máximo en la cara interna
= σcc): se usa mucho, pero **no la leí en una fuente** de las listadas → [NV] hasta conseguir CTF 2000 o Hoek y Brown 1980.

Caso [V2, UBC pp. 10-12]: a = 1.85 m, tc = 0.15 m, Ec = 30 GPa, νc = 0.25, p0 = 20 MPa, G = 2 GPa, u0 = 1 mm. Publicado:
k = 2.78 GPa, u(pr = 0) = 9.25 mm, punto de equilibrio u = 5.9 mm, p = 7.3 MPa. Recalculado: k = 2.7775 GPa,
u = 5.869 mm, p = 7.310 MPa. **Coincide.**

### 8.3 Cerchas de acero (bloqueadas o completas) [NV]
La fórmula de Hoek y Brown (1980, p. 254 de la 2.ª ed., según la base de conocimiento de RocSupport: σy = 245 MPa,
E = 207 GPa) y la de Carranza-Torres y Fairhurst (2000) para cerchas con bloques **no las pude leer**. Disponible ahora:
la tabla de psm de PRE Fig. 8 [V1] con el modelo de 8.1, y la capacidad M-N-Q de la sección (sección 11).

### 8.4 Pernos
- **Mecánicos, modelo de RocSupport:** psm = T/s² de la tabla PRE Fig. 8 y εsm del tipo [V1 parcial, ver 8.1].
- **Fórmula de rigidez de Hoek y Brown (1980)** (`1/K = sc·sl/R·[4l/(π·db²·Eb) + Q]`): [NV], no leída.
- **Refuerzo elástico con pernos (Carranza-Torres 2002 según RS2-S problema 21, pp. 137-141)** [V1 de la transcripción,
  **no apta para implementar**]: el manual tiene erratas evidentes: define ρ = a/r pero ρb = rb/a (las fórmulas
  solo cuadran con ρb = a/rb), escribe «βρ²» en el denominador donde va ρb, y «μr» por ur. Probé la transcripción con
  las entradas del problema (a = 1, σ0 = 10, E = 250, ν = 0.3, db = 25 mm, Eb = 116 667, Lb = 1, Nb = 72, D = 1): con
  ninguna de las dos lecturas de ρb hay continuidad del desplazamiento en rb en el caso de anclaje puntual, y en el
  caso inyectado σr en la pared no da 0. Un planteamiento propio de equilibrio da σrb/σ0 = 0.762, frente a 0.903 de
  la fórmula impresa. Hace falta el original (Carranza-Torres 2009, *RMRE* 42:175-228) → **[NV para implementar]**.
- **Pernos inyectados como SCC:** no existe una SCC de pernos inyectados en las fuentes leídas; OR09 (p. 763, ec. 26)
  dice que el refuerzo inyectado no se puede tratar como línea de reacción independiente porque cambia el equilibrio
  del macizo. [V1 como advertencia; no hay fórmula que implementar].

### 8.5 Combinación de sostenimientos
Tres reglas publicadas, distintas entre sí:
1. **RocSupport serie 3** [V1, RST pp. 37-38]: psm se **suma**; εsm se **promedia** («(.200 + .100)/2»). Caso: perno
   de 34 mm + shotcrete de 50 mm a 28 días, D = 12 → psm = 0.354 + 0.325 = 0.679 MPa, εsm = 0.15 %.
2. **RocSupport actual** [V1, HELP *Support behaviour*]: psm se suma; εsm = el **máximo** de los individuales.
3. **Rigidez sumada** [V1, OR09 p. 763, ec. 24-25]: `ktot = Σ ki`; cada sostenimiento carga `pi = ki·(ueq − uin)` y se
   revisa contra su propio pmax.

Recomendación: implementar la regla 3 como la correcta mecánicamente (cada elemento con su rigidez y su límite) y las
reglas 1 y 2 como «modo RocSupport» para comparar, diciendo qué versión se imita.

---

## 9. FS del sostenimiento en el cruce GRC-SCC

**Definición [V1, RST pp. 14-15, Figs. 1-6 y 1-7]:**
- Si el cruce cae en el tramo elástico de la SCC: `FS = psm/peq` (peq = presión del cruce).
- Si la GRC cruza la SCC después del límite elástico: se **prolonga** la recta elástica de la SCC hasta cortar la GRC y
  `FS = psm/p′eq` (< 1).

**Caso completo de convergencia-confinamiento [V1, RST Ejemplo 1, pp. 22-36]:** GRC Duncan-Fama de la sección 3.4
(R = 6, p0 = 1.62, E = 352.817, σcm = 0.46927, φ = 25.6394°, ν = 0.3); perno de 34 mm a 1 × 1 m (psm = 0.354 MPa,
εsm = 0.2 %), instalado a 3 m del frente. Publicado: FS = 1.84, radio plástico 10.01 m (10.0), convergencia 0.99 %.
Recalculado con el LDP de Chern: u_in/umax = 0.4336, peq = 0.1926 MPa, **FS = 1.838, rp = 10.02 m, convergencia
0.989 %. Coincide.** Es el mejor test de integración de la 8B (GRC + LDP + SCC + FS en un solo número).

---

## 10. Squeezing de Hoek y Marinos

### 10.1 Ecuaciones [V1, PRE ec. 8 p. 8 y ec. 9 p. 9 (pp. 244-245 del PDF); Hoek y Marinos (2000) NV como original]
```
ε (%) = 100·ui/ro = (0.2 − 0.25·pi/po) · (σcm/po)^(2.4·pi/po − 2)
rp/ro = (1.25 − 0.625·pi/po) · (σcm/po)^(pi/po − 0.57)
σcm = 2c′·cosφ′/(1 − sinφ′)
```
Con pi = 0: `ε % = 0.2·(σcm/po)^−2` (PRE Fig. 5). ε se define como cierre/diámetro × 100 = ui/ro × 100.
Validez: ajuste estadístico de un Monte Carlo con la GRC de Duncan Fama y Carranza-Torres-Fairhurst (PRE nota 2:
σci 1-30 MPa, mi 5-12, GSI 10-35, p0 2-20 MPa, radio 2-8 m); túnel circular hidrostático; Fig. 7 solo cubre
σcm/po ≤ 0.5 y pi/po ≤ 0.5.

### 10.2 Clases [V1 en la copia de Rocscience: RST Apéndice, Tabla A-1, pp. 74-75, citando a Hoek y Marinos (2000)]

| Clase | ε % | Problema |
|---|---|---|
| A | < 1 | pocos problemas de estabilidad; pernos y shotcrete |
| B | 1 – 2.5 | squeezing menor |
| C | 2.5 – 5 | squeezing severo |
| D | 5 – 10 | squeezing muy severo y problemas de frente |
| E | > 10 | squeezing extremo |

### 10.3 Caso de prueba [V1, PRE p. 13 (p. 249 del PDF)]
Falla con σcm/po = 0.15, túnel de radio 2 m, po = 4 MPa. Publicado: «radius of plastic zone ... approximately 7.4 m»,
«wall deformation approximately 0.18 m», «strain of 9 %», y con 2 % de deformación «pi/po = 0.25 ... pi = 1 MPa».
Recalculado: rp = 7.37 m, ε = 8.89 %, ui = 0.178 m; con pi/po = 0.25, ε = 1.96 %. **Coincide.**

**Listo para implementar.**

---

## 11. Diagrama de capacidad M-N (y Q-N) del revestimiento

### 11.1 Ecuaciones [V1, KL08 Apéndice 2, pp. 47-51; base: Carranza-Torres y Diederichs (2009), NV como original]
Sección rectangular equivalente de ancho b, área A, inercia I, espesor t; σc (compresión, +) y σt (tracción, **negativa**):
```
σmax/FS = N/A + M·t/(2I)          σmin/FS = N/A − M·t/(2I)          (A2.11-A2.12)
Nmax = A·σc/FS    Nmin = A·σt/FS                                     (A2.13-A2.14)
Mmax = ±(σc − σt)/FS · I/t        en  Ncr = A(σc + σt)/(2FS)         (A2.15-A2.16)
Corte:  compresión  N = σc·A/FS − 9Q²·FS/(4σc·A)
        tracción    N = σt·A/FS − 9Q²·FS/(4σt·A)                     (A2.21-A2.22)
        Qcr = ±(A/FS)·√(−4σc·σt/9)                                   (A2.23)
```
La envolvente M-N es el rombo (Nmax, 0) – (Ncr, ±Mmax) – (Nmin, 0); para cada FS se repite con σ/FS.
Sección compuesta cercha + shotcrete [V1, A2.1-A2.10]: `D = E·A/(1−ν²)`, `K = E·I/(1−ν²)`, `Deq = n(Dst + Dsh)`,
`Keq = n(Kst + Ksh)`, `teq = √(12Keq/Deq)`, `Eeq = Deq/(b·teq)`; reparto de M, N y Q (A2.24-A2.29):
`Mst = M·Kst/(n(Kst+Ksh))`, `Msh = M·Ksh/(n(Kst+Ksh))`,
`Nst = N·Dst/(n(Dst+Dsh)) + M(Dsh·Kst − Dst·Ksh)/(n·R·(Dst+Dsh)(Kst+Ksh))`,
`Nsh = N·Dsh/(n(Dst+Dsh)) − M(Dsh·Kst − Dst·Ksh)/(n·R·(Dst+Dsh)(Kst+Ksh))`, `Q` como M.
Erratas tipográficas de KL08: A2.27 se rotula «Nst» y es Nsh; A2.3 escribe «Ehst» por Esh.

Validez: elástico, sección no fisurada, sin interacción M-N plástica (KL08 avisa que son envolventes elásticas).

### 11.2 Caso de prueba [V1, KL08 p. 51, FS = 1] y **errata**
Cercha: A = 4.75·10⁻³ m², I = 2.23·10⁻⁵ m⁴, t = 0.162 m, σc = 500, σt = −500 MPa. Publicado: Nmax 2.38, Mmax 0.14,
Nmin −2.38, Qmax 1.58 MN; con Q = ±1.19 → N = ±1.04. Recalculado: 2.375, 0.1377, −2.375, 1.583; N(1.19) = 1.033.
**Coincide.**

Shotcrete: A = 0.12 m², I = 0.0004 m⁴, t = 0.2 m, σc = 40 MPa; el texto dice **σt = −2.5 MPa**. Publicado: Nmax 4.80,
Mmax 0.09 en N 2.10, Nmin −0.60, Qmax 1.13; con Q = 0.85 → N = 4.46 (compresión) y 2.10 (tracción).
Con σt = −2.5 salen Nmin −0.30, Ncr 2.25, Qcr 0.80 → **no coincide**. Con **σt = −5 MPa** salen Nmin −0.60, Mmax 0.090,
Ncr 2.10, Qcr 1.131 y N(0.85) = 4.461 y 2.109 → **coincide**. La tabla de KL08 se calculó con σt = −5 MPa; el texto tiene
errata. El test usa σt = −5 con esa nota.

La tabla de reparto de KL08 p. 52 **no** sirve de test: el cociente Msteel/Mtotal publicado (0.29 con n = 1/0.6) difiere
4 % del que dan las propiedades de p. 51 (0.279), y no publica el N total. Queda sin usar.

### 11.3 Revestimiento elástico de Einstein y Schwartz [V1, RS2-S p. 41, problema 7]
Revestimiento en medio elástico, campo no hidrostático (K = σxx/σyy), θ desde el eje x:
```
N = (a·σyy/2)·[ (1+K)(1 − a0*) + (1−K)(1 + 2a2*)·cos2θ ]
M = (a²·σyy/4)·(1−K)(1 − 2a2* + 2b2*)·cos2θ
a0* = C*F*(1−ν)/(C* + F* + C*F*(1−ν))      a2* = β·b2*
b2* = C*(1−ν) / (2[C*(1−ν) + 4ν − 6β − 3βC*(1−ν)])
β   = [C*(6 + F*)(1−ν) + 2F*ν] / [3C* + 3F* + 2C*F*(1−ν)]
C*  = E·a(1−νs²)/(Es·A(1−ν²))     F* = E·a³(1−νs²)/(Es·I(1−ν²))
```
(E, ν del macizo; Es, νs del revestimiento; A, I por metro de túnel.) Da los pares (M, N) que se llevan al diagrama.
Caso: σxx = 30, σyy = 15 (K = 2), E = 6000, ν = 0.2, Es = 20 000, νs = 0.2, h = 0.5 m, a = 2.5 m. Publicado solo en
gráfica (Figs. 7.3 y 7.4, p. 42): N de ≈ 14.6 (θ = 0) a ≈ 36.6 MN (θ = 90°), M de ≈ −0.70 a +0.70 MN·m. Recalculado:
C* = 1.5, F* = 450, N = 14.61 / 25.61 / 36.62 MN y M = −0.703 / 0 / +0.703 MN·m en θ = 0/45/90°. **Coincide (lectura de
gráfica).** Listo para implementar.

---

## 12. Tabla resumen

| Método | Fórmula lista | Marca | Caso de prueba | Diferencia del recálculo |
|---|---|---|---|---|
| Kirsch (campo y borde) | sí | V1 (RS2-S p. 8; CC02 p. 26) | RS2-S 1: σθ = 60, ur = 3.6 mm | 0 (gráfica) |
| Elipse (borde y extremos) | sí | V1 (CC02 p. 26) | a = b → Kirsch; hueco armónico = σ1 + σ3 | 0 (consistencia; sin número publicado) |
| GRC MC: pcr, rp | sí | V1 (PRE ec. 4, 6; RS2-S p. 14) | RSV 5: 1.74/1.47/1.49/1.29 m | ≤ 0.005 m |
| GRC MC: u sin dilatancia | sí | V1 (PRE ec. 7) | PRE Fig. 4: 30.6 mm; RST: 2.03 % | 0.00 %; 0.0 % |
| GRC MC: u con dilatancia (Salençon) | sí | V1 (RS2-S p. 15) | Soria: 68.05 mm; RSV Fig. 5-1/5-2 | 68.049 mm (0.00 %); dentro de la lectura |
| GRC HB a = 0.5 (CTF) | sí | V1 (CC02 ec. 5-11) | CC02: Rpl/R 1.64, u 0.08 m | 1.623 exacto (1.641 con el redondeo del texto); 0.0835 m |
| HB 1982 con residual (esfuerzos) | sí | V1 (RS2-S p. 22) | RS2-S 3: re ≈ 2.1-2.2 m | re = 2.168 (gráfica) |
| HB generalizado riguroso | no | NV | RSV 4 (solo gráfica) | — |
| HB generalizado vía MC equivalente | sí | V1 (RST pp. 25, 29) | RST Ej. 1: E 352.817, σcm 0.46927, φ 25.6394° | 0 |
| Reed (esfuerzos) | sí | V1 (RS2-S p. 176) | RS2-S 30 con ro = 4, q = 100 (errata en la tabla) | r̄ 7.77; pico 176 (gráfica) |
| Reed (desplazamiento) | no | NV | — | — |
| LDP Panet, Unlu-Gercek, Chern | sí | V1 (KL08 A1.1-A1.4) | RST Ej. 1 (Chern) → FS 1.84 | 0.1 % |
| LDP Vlachopoulos-Diederichs | sí | V1 (KL08 A1.5-A1.7) | KL08: R* = 2 → ≈ 1/4 en el frente | 0.247 |
| SCC modelo RocSupport (psm, εsm) | sí (con 2 εsm conocidos) | V1 (RST, PRE Fig. 8) | D = 12, 50 mm → 0.325 MPa | 0.3246 |
| Tabla psm de Hoek (PRE Fig. 8) | sí (datos) | V1 | idem | — |
| εsm de toda la tabla de Hoek (1999b) | no | NV | — | — |
| Rigidez de anillo grueso (shotcrete/hormigón) | sí | V2 (UBC / Harrison y Hudson) | k 2.78 GPa; u 5.9 mm; p 7.3 MPa | 2.7775; 5.869; 7.310 |
| pmax de anillo grueso (Lamé) | no | NV | — | — |
| Cerchas (H&B 1980, CTF 2000) | no | NV | — | — |
| Pernos: rigidez H&B 1980 | no | NV | — | — |
| Pernos: refuerzo elástico Carranza-Torres (RS2-S 21) | no | V1 transcripción con erratas | no cierra la verificación | σrb/σ0 0.903 impreso vs 0.762 propio |
| Combinación de sostenimientos | sí (3 reglas) | V1 (RST pp. 37-38; HELP; OR09 ec. 24-25) | 0.354 + 0.325 = 0.679 | 0 |
| FS en el cruce GRC-SCC | sí | V1 (RST pp. 14-15) | RST Ej. 1: FS 1.84, rp 10.0, 0.99 % | 1.838; 10.02; 0.989 % |
| Squeezing Hoek-Marinos | sí | V1 (PRE ec. 8-9; RST Tabla A-1) | PRE p. 13: 7.4 m, 0.18 m, 9 %, 2 % con pi/po 0.25 | 7.37; 0.178; 8.89; 1.96 |
| Capacidad M-N y Q-N | sí | V1 (KL08 A2.11-A2.23) | KL08 p. 51 (σt = −5 por errata) | ≤ 0.005 MN |
| Revestimiento elástico Einstein-Schwartz | sí | V1 (RS2-S p. 41) | RS2-S 7: N 14.6-36.6, M ±0.70 | 14.61-36.62; ±0.703 (gráfica) |

## 13. Lo que queda [NV]

1. Desplazamiento de Reed (frágil-plástico).
2. Hoek-Brown generalizado riguroso (Carranza-Torres 2004; Lee y Pietruszczak 2008; Chen y Tonon 2011).
3. SCC de cerchas (Hoek y Brown 1980; Carranza-Torres y Fairhurst 2000, cerchas con bloques).
4. Rigidez de pernos mecánicos de Hoek y Brown (1980) y SCC de pernos inyectados.
5. Presión máxima del anillo grueso de shotcrete u hormigón `(σcc/2)[1 − (R − tc)²/R²]` (fórmula conocida, sin fuente leída).
6. Tabla completa de εsm de Hoek (1999b) usada por RocSupport (solo conozco 0.2 % del perno de 34 mm y 0.1 % del shotcrete
   de 50 mm a 28 días).
7. Solución de refuerzo elástico con pernos de Carranza-Torres (RS2-S 21): transcrita, pero con erratas que impiden verificarla.
8. Grandes deformaciones de Vrakas y Anagnostou (RSV 1-3, 5): solo gráficas, no hay fórmula.
9. Ejemplo resuelto y hoja de cálculo de Carranza-Torres y Fairhurst (2000): no hay copia pública; el ejemplo de CC02 lo reemplaza.

## 14. Erratas encontradas en las fuentes (no usar como valor esperado)

| Fuente | Errata | Qué se usa |
|---|---|---|
| RS2-S problema 30, Tabla 30.1 (p. 175) | ro = 2 m y q = 30 MPa no producen plastificación; las gráficas son de ro = 4 m y q = 100 MPa | ro = 4, q = 100 |
| RS2-S problema 30, p. 176 | σθ elástico rotulado «σc» | σθ |
| RS2-S problema 21, pp. 139-141 | ρ = a/r pero ρb = rb/a; «βρ²» por βρb²; «μr» por ur | no se implementa |
| RS2-S problema 3, Tabla 3.1 | sr impreso «1e10⁻⁵» | 1×10⁻⁵ |
| KL08 p. 51 | σtsh = −2.5 MPa en el texto, la tabla se calculó con −5 MPa | −5 MPa |
| KL08 A2.27 y A2.3 | «Nst» por Nsh; «Ehst» por Esh | Nsh; Esh |

## Apéndice: recálculo

Scripts temporales del recálculo, no publicados (`mc.py`, `todo.py`, `hb02.py`, `bolts.py`, `bolts_derive.py`).
Núcleo, para copiar a los tests de la 8B:

```python
from math import sin, cos, radians, sqrt, exp, log

def grc_mc(R, p0, E, nu, c, phi, psi, pi=0.0):
    """Mohr-Coulomb: pcr, rp y u en la pared (Salençon según RS2-S pp. 14-15)."""
    k = (1 + sin(radians(phi))) / (1 - sin(radians(phi)))
    kps = (1 + sin(radians(psi))) / (1 - sin(radians(psi)))
    scm = 2 * c * cos(radians(phi)) / (1 - sin(radians(phi)))
    pcr = (2 * p0 - scm) / (1 + k)
    G = E / (2 * (1 + nu))
    if pi >= pcr:
        return pcr, R, R * (1 + nu) * (p0 - pi) / E
    rp = R * (2 * (p0 * (k - 1) + scm) / ((1 + k) * ((k - 1) * pi + scm))) ** (1 / (k - 1))
    A = pi + scm / (k - 1)
    u = R / (2 * G) * ((2 * nu - 1) * (p0 + scm / (k - 1))
                       + (1 - nu) * (k * k - 1) / (k + kps) * A * (rp / R) ** (k - 1) * (rp / R) ** (kps + 1)
                       + ((1 - nu) * (k * kps + 1) / (k + kps) - nu) * A)
    return pcr, rp, u

assert abs(grc_mc(5, 4.05, 446, 0.3, 1, 37, 6)[2] - 0.06805) < 5e-6      # Soria Medina (2023)
assert abs(grc_mc(1, 30, 1e4, 0.2, 3.45, 30, 0)[1] - 1.74) < 0.01        # RSV problema 5

def grc_hb05(R, s0, pi, sci, mb, s, G, nu, psi):
    """Hoek-Brown a = 0.5 (CC02 ec. 5-11)."""
    Kp = (1 + sin(radians(psi))) / (1 - sin(radians(psi)))
    So = s0 / (mb * sci) + s / mb ** 2; Pi = pi / (mb * sci) + s / mb ** 2
    Pcr = (1 - sqrt(1 + 16 * So)) ** 2 / 16; pcr = (Pcr - s / mb ** 2) * mb * sci
    if pi >= pcr:
        return pcr, R, (s0 - pi) * R / (2 * G)
    x = exp(2 * (sqrt(Pcr) - sqrt(Pi)))
    f = ((Kp - 1) / (Kp + 1) + 2 / (Kp + 1) * x ** (Kp + 1) + (1 - 2 * nu) / (4 * (So - Pcr)) * log(x) ** 2
         - ((1 - 2 * nu) / (Kp + 1) * sqrt(Pcr) / (So - Pcr) + (1 - nu) / 2 * (Kp - 1) / (Kp + 1) ** 2 / (So - Pcr))
         * ((Kp + 1) * log(x) - x ** (Kp + 1) + 1))
    return pcr, R * x, f * R * (s0 - pcr) / (2 * G)

def ldp_vd(xs, rs):
    """Vlachopoulos-Diederichs (KL08 A1.5-A1.7): u/umax con X* = X/R y R* = Rp/R."""
    u0 = exp(-0.15 * rs) / 3
    return u0 * exp(xs) if xs <= 0 else 1 - (1 - u0) * exp(-3 * xs / (2 * rs))

def ldp_chern(xs):
    return (1 + exp(-xs / 1.10)) ** -1.7      # KL08 A1.4
```
