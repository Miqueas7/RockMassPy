# Verificación de fórmulas y tablas [NV] contra la fuente original — RockMassPy

Fecha: 31-oct-2026. Solo se usaron fuentes públicas y el scratchpad; ningún dato de clientes.

**Marcas**
- **[V1]**: lo vi en la fuente original (el PDF del autor o del organismo), con página.
- **[V1-a]**: lo vi en una publicación posterior **de los mismos autores** que reproduce su propia fórmula o tabla (el original está cerrado). Para el código sirve como V1, pero hay que citar las dos.
- **[V2]**: fuente secundaria seria (Hoek, Osinergmin, un artículo que reproduce la tabla).
- **[NV]**: no verificado.

Las páginas se dan como «impresa / física del PDF» cuando difieren.

---

## Tabla resumen

| # | Ítem | Estado | Fuente vista | Página | Qué falta |
|---|---|---|---|---|---|
| 1a | RMR14: tablas de puntaje (condición, agua, alterabilidad, F0) | **[V2]** | Osinergmin (2017), Guía de criterios geomecánicos, Anexo de RMR14 y cap. 3 | 27–28 y 205–209 (impresas) | El original de Celada et al. (2014, WTC) no está en línea. Resistencia y n.º de juntas/m son **curvas sin ecuación** |
| 1b | RMR14: Fe (TBM), Fs (ICE), ICE | **[V2]** | Osinergmin (2017) | 205–207 | Original. Ojo: la tabla RMR→RMR_TBM y la fórmula de Fe no coinciden del todo (ver detalle) |
| 1c | Correlación RMR14 = 1.1·RMR89 + 2 | **[V2]** | Osinergmin (2017), ec. 11 | 28 y 209 | Original (WTC 2014) |
| 2a | Q 2025: luz máxima sin soporte 2·ESR·Q^0.4 | **[V2]** | Hoek, *Practical Rock Engineering*, cap. 3, ec. 4 (la atribuye a **Barton et al. 1980**, no a 1974) | 18 | **No aparece en el manual NGI 2015 ni 2025** [V1 de la ausencia]. Original: Barton et al. (1980), de pago |
| 2b | Q: longitud de perno L = 2 + 0.15·B/ESR | **[V2]** | Hoek, cap. 3, ec. 3 (Barton et al. 1980) | 18 | No está en NGI 2015/2025: el manual da la longitud **solo como eje gráfico** (ESR = 1) [V1] |
| 2c | Q: presión de soporte | **[V2]** Grimstad-Barton (1993): P_roof = 2·√Jn·Q^(−1/3)/(3·Jr). **[NV]** la de 1974, P = (2/Jr)·Q^(−1/3) | Hoek, cap. 3, ec. 5 | 19 | **El manual NGI 2015/2025 no trae ninguna presión de soporte** [V1 de la ausencia]. Barton et al. (1974) y Grimstad-Barton (1993) son de pago |
| 2d | Q 2025: ESR, 5 categorías de SRF, Jr = 4, ábaco (E700, RRS A/B/C), muros | **[V1]** | NGI (abril 2025), *Using the Q-system* | 15, 22, 25, 29, 31–32, 34–35, 38 (impresas) | Nada |
| 2e | Q 2015 (y actualización 2022) para comparar | **[V1]** | NGI (mayo 2015; rev. junio 2022), copia del propio ngi.no en el Internet Archive | 19, 26, 33–36 | Nada |
| 3 | DS 024-2016-EM, Anexos 39 A, 39 B y 39 D | **[V1]** | El Peruano (DS 034-2023-EM, art. 2 y 4) + anexos publicados por MINEM en gob.pe + compilación MINEM 2026 | Anexos: PDF físico 67–68 y 72–73; compilación 275, 276, 279–280 | Nada. **Son índices de contenido, no traen fórmulas ni valores** |
| 4a | Mathews: forma logit z = a + b1·lnS + b2·lnN | **[V1]** | Mawdesley, Trueman y Whiten (2001), ec. 3–5 | 5 (física) | **Mawdesley (2001) no publica los coeficientes numéricos** |
| 4b | Mathews: coeficientes 3.146, −1.173, 0.8409 | **[V1] con reserva** | Mortazavi y Osserbay, preprint Research Square (2021, CC BY) | 10–11 y 16 (impresas) | Versión publicada (GGE 2022, de pago). **El preprint es incoherente**: con sus propios coeficientes las ecuaciones de frontera no dan lo que dice (ver detalle) |
| 4c | Factores de Potvin (1988): A, B, C | **[V2]** A (gráfico lineal) y C = 8 − 6·cos α; **[NV]** B como ecuación y C para deslizamiento | Osinergmin (2017), figs. 7-5 a 7-7 | 59–61 | La tesis de Potvin es **acceso abierto en UBC**, pero UBC bloquea descargas automáticas: bájala tú en el navegador |
| 5a | SMR: F1, F2, F3, F4 discretos (Romana 1985) | **[V1-a]** | Tomás, Romana y Serón (2017), *Boletín SEMSIG* 190 (Romana es coautor), tablas 1–3 | 26–27 | Romana (1985) original |
| 5b | SMR: funciones continuas de Tomás et al. (2007) | **[V1-a]** | Tomás, Romana y Serón (2017), ec. 4–7 | 28 | Tomás et al. (2007) original: en RUA está en **acceso restringido** |
| 6 | Barton-Bandis, escala (Barton y Bandis 1982), φr = (φb − 20) + 20·r/R | **[V2]** | Hoek, *Practical Rock Engineering*, cap. 4, ec. 4–8 | 5–6 y 12 | Barton y Choubey (1977) y Barton y Bandis (1982) son de pago. Barton (2013, JRMGE) es **acceso abierto**, pero ScienceDirect bloqueó la descarga automática |
| 7 | Q-slope: fórmula, O-factor, Jwice, SRFslope, β = 20·log10(Qslope) + 65° | **[V1-a]** | Bar y Barton (2018), *Periodica Polytechnica Civil Eng.* 62(4), acceso abierto | 894–896 | Bar y Barton (2017, RMRE) está cerrado |
| 8 | Read y Stacey (2009): FoS/PoF | **[V2]** solo la columna estática y el PoF; **[NV]** la columna dinámica | Moffitt (2023), SSIM, tabla 1 (reproduce la tabla 9.9 de Wesseloo y Read 2009) | 3 | El libro (CSIRO Publishing) es de pago. No encontré una reproducción abierta y legible de la columna pseudoestática |
| 9 | RMR = 22·ln(De) + 25 | **[NV]** | — | — | No encontré el origen. Hipótesis algebraica abajo (no es la misma ecuación) |
| 10a | Hoek-Brown 2018: D solo en la zona dañada | **[V1]** | Hoek y Brown (2019), JRMGE, versión *in press* (acceso abierto) | 8–9 (de 19) | Nada |
| 10b | Laubscher (1990): ajustes del MRMR | **[V1]** | Laubscher (1990), J. SAIMM 90(10), acceso abierto | 264–266 | Algunas celdas de la tabla VII no se leen |
| 10c | Laubscher (1994): ábaco MRMR vs radio hidráulico | **[V1]** (es gráfico, **sin ecuación**) | Laubscher (1994), J. SAIMM 94(10) | 282 | La frontera hay que digitalizarla |

---

## PDFs nuevos en `pdfs\`

| Archivo | Qué es | De dónde |
|---|---|---|
| `q2015.pdf` | NGI, *Using the Q-system*, mayo 2015 | Copia del propio ngi.no guardada en el Internet Archive (web.archive.org, 21-ene-2022) |
| `q2015u2022.pdf` | La misma, con la actualización de junio de 2022 (ábaco revisado en 2019) | Internet Archive, ngi.no (15-jun-2022) |
| `tomas2006.pdf` | Tomás et al. (2006), *Rev. Soc. Geol. España* 19(1–2), funciones continuas del SMR | RUA, Universidad de Alicante, acceso abierto (hdl 10045/2695) |
| `smr_revision2017.pdf` | Tomás, Romana y Serón (2017), «Revisión del estado actual de la clasificación SMR», *Boletín SEMSIG* 190 | RUA, acceso abierto (hdl 10045/70953) |
| `riquelme2016.pdf` | Riquelme, Tomás y Abellán (2016), preprint IJRMMS | RUA, acceso abierto (hdl 10045/52313) |
| `bb2018.pdf` | Bar y Barton (2018), «Rock Slope Design using Q-slope and Geophysical Survey Data» | pp.bme.hu, acceso abierto |
| `laub_v090n10p257.pdf` | Laubscher (1990), J. SAIMM 90(10) 257–273 | saimm.co.za, archivo abierto |
| `laub_v094n10p279.pdf` | Laubscher (1994), J. SAIMM 94(10) 279–293 | saimm.co.za |
| `ds034_2023.html` | DS 034-2023-EM, texto de El Peruano | busquedas.elperuano.pe (dispositivo 2249422-2) |

Los intentos bloqueados quedaron renombrados como `*.BLOQUEADO.html` (páginas de bloqueo, no PDFs): Potvin (UBC), Tomás 2007 (RUA restringido) y Barton 2013 (ScienceDirect). También hay versiones de texto con marca de página (`*.p.txt`). No se ejecutó nada de los PDFs.

---

## 1. RMR14 (Celada, Tardáguila, Varona, Rodríguez y Bieniawski, 2014)

**Original**: «Innovating tunnel design by an improved experience-based RMR system», *World Tunnel Congress 2014*, Foz do Iguaçu. La biblioteca de ITA-AITES lo lista a 0 € pero «no longer in stock», sin descarga. No hay copia abierta del autor. **Todo lo de abajo es [V2] desde Osinergmin (2017)**, que lo transcribe.

Fuente: Osinergmin (2017), *Guía de criterios geomecánicos para diseño, construcción, supervisión y cierre de labores subterráneas*, pp. 27–28 (cap. 3) y 205–209 (anexo «Cálculo del RMR14»).

### 1.1 Parámetros básicos (RMR14b, máximo 100)

1. **Resistencia de la roca intacta** (0–15): **curva** puntuación vs σc (0–250 MPa). Sin ecuación en Osinergmin.
2. **Número de discontinuidades por metro** (0–40): **curva** (40 a 0 juntas/m → 40 a 0 puntos aprox.; llega a 0 cerca de 50/m). Sin ecuación.
3. **Condición de discontinuidades** (0–20), tabla (p. 208):

| Subparámetro | | | | |
|---|---|---|---|---|
| Continuidad | < 1 m: **5** | 1–3 m: **4** | 3–10 m: **2** | > 10 m: **0** |
| Rugosidad | Muy rugoso: **5** | Rugoso: **3** | Liso: **1** | Espejo de falla: **0** |
| Relleno | Duro < 5 mm: **5** | Duro > 5 mm: **2** | Blando < 5 mm: **2** | Blando > 5 mm: **0** |
| Alteración | Inalterada: **5** | Moderadamente alterada: **3** | Altamente alterada: **1** | Descompuesta: **0** |

4. **Agua** (0–15): Seco **15**, Húmedo **10**, Mojado **7**, Goteando **4**, Flujo **0**.
5. **Alterabilidad por Id2 (slake durability)** (0–10): **> 85 % → 10**; 60–85 % → 8; 30–60 % → 4; < 30 % → 0.
   - **Errata en Osinergmin**: las tablas 3-7 (p. 27) y la de p. 205 dicen «< 85» para 10 puntos; la del anexo (p. 208) dice «> 85». Lo correcto es > 85.

### 1.2 Ajustes

```
RMR14 = (RMR14b + F0) · Fe · Fs                                  (Osinergmin ec. 10)

F0 (igual que RMR89 en túneles):
  rumbo ⊥ eje, avance a favor del buzamiento: 45–90° → 0 ; 20–45° → −2
  rumbo ⊥ eje, avance en contra:              45–90° → −5 ; 20–45° → −10
  rumbo ∥ eje:                                 45–90° → −12 ; 20–45° → −5
  buzamiento 0–20°, cualquier rumbo:           −5

Fe (excavación con tuneladora; con voladura Fe = 1):
  RMR < 40:  Fe = 1 + 2·(RMR/100)²
  RMR > 40:  Fe = 1.32 − √(RMR − 40) / 25

ICE (Bieniawski y Celada 2011):
  K0 ≤ 1:  ICE = 3704·σci·e^((RMR−100)/24) / ((3 − K0)·H) · f
  K0 ≥ 1:  ICE = 3704·σci·e^((RMR−100)/24) / ((3·K0 − 1)·H) · f
  f: túnel circular 6 m → 1.3 ; circular 10 m → 1.0 ; convencional 14 m → 0.75 ; caverna 25×60 m → 0.55

Fs (plastificación del frente):
  ICE < 15        → Fs = 1.3
  15 < ICE < 70   → Fs = 1.3 − 0.6·(ICE/100)²
  ICE > 70        → Fs = 1.0
```
Clases ICE: > 130 completamente elástico; 70–130 elástico con plastificación incipiente; 40–69 moderadamente plastificado; 15–39 intensamente plastificado; < 15 totalmente plastificado.

Lo que noté al revisar:
- La fórmula de Fs con ICE aparece limpia en la p. 207 (la versión con el símbolo dañado «GCI» era de otra extracción). Osinergmin dice que «la gráfica puede ser representada» por esas fórmulas: **no queda claro si las fórmulas son de Celada o un ajuste de Osinergmin**. En ICE = 15 la fórmula da 1.287 y no 1.3 (pequeño salto).
- Tabla 5 de Osinergmin (p. 206): RMR 20/40/60/80 → RMR_TBM 21/53/70/85, cociente 1.05/1.32/1.16/1.06. La fórmula de Fe da 1.08 en RMR = 20 y 1.14 en RMR = 60. **No coinciden exactamente**: hay que ver cuál usa el original.
- No hay ajuste por voladura en la fórmula de RMR14: para voladura convencional Fe = 1 (Fe solo se aplica con tuneladora).

### 1.3 Correlación

```
RMR14 = 1.1·RMR89 + 2          (Osinergmin ec. 11, p. 28; repetida en p. 209)
```
El resumen oficial de ITA-AITES confirma que el artículo de 2014 trae una correlación RMR89–RMR14 (2298 casos), pero no la muestra. «RMR14 ≈ RMR89 + 10» sigue [NV].

**Vía legal**: pedirlo a Geocontrol (Madrid) o a los autores; préstamo interbibliotecario de las actas WTC 2014; el libro de Celada y Bieniawski (2019), *Ground Characterization and Structural Analyses for Tunnel Design*, CRC Press. Para las curvas continuas de resistencia y juntas/m, Kundu et al. (2020, IJRMMS 129) y su código QuickRMR.

---

## 2. Sistema Q: manual NGI 2025 frente a 2015

Fuentes [V1]:
- NGI (abril 2025), *Using the Q-system. Rock mass classification and support design*, Oslo. `pdfs\q2025.pdf`. Registro de cambios: `pdfs\qchange.pdf`.
- NGI (mayo 2015), mismo título, `pdfs\q2015.pdf`; y la reedición de junio 2022 «Revised rock support chart from 2019, page 34» (`pdfs\q2015u2022.pdf`). Fuera del prefacio y el ábaco, su texto es idéntico al de 2015.

### 2.1 Lo que el manual **no** trae (verificado en 2015 y 2025)
Revisé el texto completo de las dos ediciones: **ninguna** trae la luz máxima sin soporte, la fórmula de longitud de perno ni ninguna presión de soporte. Solo aparecen «swelling pressure» y «squeezing rock pressure» como descripciones de SRF.

### 2.2 Fórmulas clásicas [V2]
Hoek, *Practical Rock Engineering*, cap. 3 «Rock mass classification» (rocscience.com), pp. 18–19:
```
L = 2 + 0.15·B/ESR                          (ec. 3; Barton et al. 1980)
Luz máxima sin soporte = 2·ESR·Q^0.4         (ec. 4; Barton et al. 1980)
P_roof = 2·√Jn · Q^(−1/3) / (3·Jr)          (ec. 5; Grimstad y Barton 1993)
```
- Hoek las atribuye a **Barton, Løset, Lien y Lunde (1980)**, «Application of the Q-system in design decisions…», *Subsurface Space* (Rockstore 80), Pergamon, y no a Barton et al. (1974). Cita esa fuente.
- **P = (2/Jr)·Q^(−1/3)** (la de 1974 para tres o más familias): **[NV]**. No la vi en ninguna fuente de esta sesión.
- La longitud de perno del ábaco **no sigue** L = 2 + 0.15·De. Leída en el eje derecho (ESR = 1): 1.5 m en De ≈ 2, 3 m en De ≈ 10, 5 m en De ≈ 20, 11 m en De ≈ 50, 20 m en De ≈ 100 (lectura aproximada de la figura). La fórmula da 2.3, 3.5, 5, 9.5 y 17. Son dos reglas distintas: hay que documentar cuál se usa.

### 2.3 Jr (2025, Tabla 3-3, p. 15 impresa / 19 física)
| | Descripción (a: contacto roca-roca; b: contacto antes de 10 cm de corte) | Jr |
|---|---|---|
| A | Discontinuous joints / rough, stepped | **4** |
| B | Rough or irregular, undulating / smooth, stepped | 3 |
| C | Smooth, undulating / slickensided, stepped | 2 |
| D | Slickensided, undulating | 1.5 |
| E | Rough, irregular, planar | 1.5 |
| F | Smooth, planar | 1 |
| G | Slickensided, planar | 0.5 |
| H | (c: sin contacto) zona con arcilla que impide el contacto | 1 |

Notas: +1 si el espaciado medio de la familia es > 3 m; Jr = 0.5 para juntas planas con estrías orientadas en la dirección de deslizamiento. 2025, §3.4.3: Jr + 1 si en la labor quedan expuestas pocas juntas de la familia (por ejemplo 1.5 + 1 = 2.5).
**Comparación con 2015** (Tabla 3, p. 19): Jr = 4 ya existía («A Discontinuous joints 4»). En 2025 se agregan los descriptores escalonados (*stepped*) a A, B y C y los valores en la figura 3-2; eso es lo que el registro de cambios llama «added parameter values for stepped surface roughness (Jr = 4)».

### 2.4 SRF: 5 categorías (2025, Tabla 3-6, p. 22 / 26)
| Cat. | Caso | SRF |
|---|---|---|
| a) Zonas débiles que cortan la excavación | A: muchas zonas débiles con arcilla o roca químicamente desintegrada, cualquier profundidad (para squeezing ver 6M y 6N) | 10 |
| | B: muchas zonas de corte en roca competente sin arcilla, roca suelta | 7.5 |
| | C: zona débil única, profundidad ≤ 50 m | 5 |
| | D: juntas abiertas sueltas, muy fracturado, «sugar cube» | 5 |
| | E: zona débil única, profundidad > 50 m | 2.5 |
| | Nota i: reducir 25–50 % si la zona influye pero no corta la excavación | |
| b) Roca competente, esfuerzos bajos o favorables | F: esfuerzos bajos, cerca de superficie, juntas abiertas | 2.5 |
| | G: esfuerzos medios, condición favorable | 1 |
| | Nota ii: si la profundidad de la clave es menor que la luz, subir SRF de 2.5 a 5 | |
| c) Roca competente masiva, problemas de esfuerzos | H: esfuerzo alto, estructura muy cerrada | 0.5–2 (2–5*) |
| | J: lajamiento moderado después de > 1 h | 5–50 |
| | K: lajamiento o estallido a los pocos minutos | 50–200 |
| | L: estallido fuerte y deformación dinámica inmediata | 200–400 |
| d) Squeezing | M: moderado | 5–10 |
| | N: fuerte | 10–20 |
| e) Swelling | O: moderado | 5–10 |
| | P: fuerte | 10–15 |

Tabla 3-7 (p. 25 / 29), solo para la categoría c), «no aplicar sin criterio», datos de roca masiva con RQD/Jn > 20:

| | σc/σ1 | σθ/σc | SRF |
|---|---|---|---|
| H | 10–5 | 0.3–0.4 | 0.5–2 (2–5*) |
| J | 5–3 | 0.5–0.65 | 5–50 |
| K | 3–2 | 0.65–1 | 50–200 |
| L | < 2 | > 1 | 200–400 |

\* Campo virgen muy anisótropo: si 5 ≤ σ1/σ3 ≤ 10, usar 0.75·σc; si σ1/σ3 > 10, usar 0.5·σc.

**Comparación con 2015** (Tabla 6, p. 26): 4 categorías (a–d). La b) de 2015 juntaba F, G, H, J, K y L con sus cocientes en la tabla principal: F «> 200 / < 0.01 → 2.5» y G «200–10 / 0.01–0.3 → 1». En 2025 F y G pasan a b) **sin cocientes**. El squeezing de 2015 tenía σθ/σc (M: 1–5 → 5–10; N: > 5 → 10–20); en 2025 se quitó por falta de datos. 2015 decía «mild» en M y O; 2025 dice «moderate». Valores iguales.
**Errata que hay en las dos ediciones**: el texto de §3.7.1 (2025) remite a «M o N en Tabla 3-6 c)» y «O o P en Tabla 3-6 d)», cuando en 2025 son d) y e). En 2015, la nota de A decía «6L y 6M» en vez de «6M y 6N». Ese texto no sirve para programar las categorías: hay que usar la tabla.

### 2.5 ESR (2025, Tabla 4-1, p. 29 / 33)
| | Tipo de excavación | ESR |
|---|---|---|
| A | Labores mineras temporales | 3–5 |
| B | Piques verticales*: i) circulares / ii) rectangulares o cuadrados | 2.5 / 2.0 |
| C | Labores mineras permanentes, túneles de agua (sin tuberías forzadas de alta presión), túneles piloto, galerías de avance de grandes aberturas | 1.6 |
| D | Túneles viales y ferroviarios menores, chimeneas de equilibrio, accesos, alcantarillado | 1.3 |
| E | Casas de fuerza, almacenes, plantas de tratamiento, túneles viales y ferroviarios mayores, defensa civil, portales, intersecciones | 1.0 |
| F | Centrales nucleares subterráneas, estaciones, instalaciones públicas y deportivas, fábricas | 0.8 |
| G | Cavernas muy importantes con vida ≥ 100 años o sin acceso para mantenimiento | 0.5 |

\* Según el uso; puede ser menor. Usar ESR = 1.0 cuando Q ≤ 0.1 en B, C y D. «En la mayoría de casos se usa E (ESR = 1)». De = luz o altura [m] / ESR.
**Comparación con 2015** (Tabla 7, p. 33): mismos valores, escritos como «ca. 3–5», «ca. 2.5», «ca. 2.0». La regla de Q ≤ 0.1 ya estaba.

### 2.6 Ábaco de sostenimiento (2025, Fig. 4-1, pp. 31–32 / 35–36)
Categorías 2025:
1. Sin sostenimiento o pernos puntuales
2. Pernos puntuales
3. Pernos sistemáticos + shotcrete con fibra 5–6 cm, **B + Sfr**
4. Shotcrete con fibra y pernos, 6–9 cm, **Sfr (E700) + B**
5. Shotcrete con fibra y pernos, 9–12 cm, **Sfr (E700) + B**
6. Shotcrete con fibra y pernos, 12–15 cm + RRS y pernos, **Sfr (E1000) + B + RRS-A**
7. \* Shotcrete con fibra > 15 cm + RRS y pernos, **Sfr (E1000) + B + RRS-B**
8. \* Shotcrete con fibra > 25 cm + doble capa de RRS y pernos, **Sfr (E1000) + B + RRS-C**
9. \* Evaluación especial

\* En las categorías 7–9 la recomendación es indicativa: hacen falta evaluaciones de geología e ingeniería de rocas (cap. 4.7).

RRS (espaciado según Q):

| Tipo | Luz 5 m | Luz 10 m | Luz 20 m |
|---|---|---|---|
| RRS-A | — | Si30/6 Ø16–Ø20 | D40/6+4 Ø16–20 |
| RRS-B | Si35/6 Ø16–20 | D45/6+4 Ø16–20 | D55/6+4 Ø20 |
| RRS-C | D40/6+4 Ø16–20 | D55/6+4 Ø20 | Evaluación especial |

(Si30/6 = una capa de 6 barras, 30 cm de shotcrete; D = doble capa; Ø16 = barra de 16 mm.) Espaciado c/c de RRS en el ábaco: 1.0, 1.7, 2.3, 2.9 y 4.0 m. Líneas de energía: E = 700 J (dos tramos) y E = 1000 J (dos tramos). Tabla 4-3 (p. 38 / 42): E700 ≥ 700 J y E1000 ≥ 1000 J (ensayo de panel, NB Publ. 7, 2022). Antes de la RRS se aplica una capa de 12–15 cm de Sfr (p. 35 / 39). En 7–9, considerar anclaje adicional de la RRS o solera de concreto.

**Comparación con 2015/2022** (Fig. 7, pp. 34–35):
- Cat. 4: **Sfr (E500)** + B → 2025: E700. Cat. 5: E700 en las dos.
- Cat. 6: **Sfr (E700)** + RRS I + B → 2025: E1000 + RRS-A.
- Cat. 7: E1000 + RRS II + B (igual, salvo el nombre).
- Cat. 8: **«Cast concrete lining, CCA or Sfr (E1000) + RRS III + B»** → 2025 quita el revestimiento de concreto y queda Sfr > 25 cm + RRS-C.
- RRS I/II/III → RRS-A/B/C. Las barras extra de doble capa cambian: 2015 I (luz 20 m) **D40/6+2** → 2025 A **D40/6+4**; 2015 II (luz 10 m) **D45/6+2** → 2025 B **D45/6+4**. El resto es igual.
- Líneas de energía 2015: E = 500, 700, 700 y 1000 J. 2025: 700, 700, 1000 y 1000 J.
- Rótulos de clase A: 2015 «Very good / Extremely good / Exceptionally good»; 2025 solo «Very good».
- El ábaco no tiene ecuaciones oficiales: hay que digitalizarlo (sigue siendo [NV] como polígonos).

### 2.7 Paredes (2025, Tabla 4-2, p. 34 / 38)
| Calidad | Q | Ajuste |
|---|---|---|
| Buena | Q > 10 | Q × 5 |
| Mala a regular | 1 < Q < 10 | Q × 2.5 (con esfuerzos altos, Q real) |
| Mala | Q < 1 | Q real |
| Altura de pared > luz | cualquier Q | Q real en todo el perfil |

En paredes, De usa la altura de pared. **2015** (Tabla 8, p. 36): el límite era 0.1 < Q < 10 y Q < 0.1, sin la fila de «altura > luz».

---

## 3. DS 024-2016-EM: Anexos 39 A, 39 B y 39 D

**Base legal [V1]**
- **DS 034-2023-EM** (El Peruano, 30-dic-2023, dispositivo 2249422-2), `pdfs\ds034_2023.html`:
  - **Art. 2** modifica el **art. 33** del Reglamento. Los estudios geomecánicos globales (labores subterráneas y superficiales) deben comprender lo indicado en el **Anexo 39 A** y basarse en ensayos de laboratorio de mecánica de rocas **acreditados**. Antes de toda labor subterránea se debe contar con una **evaluación geomecánica local** según el **Anexo 39 B**, actualizada cuando se amerite. Se deben publicar en cada labor las tablas y planos geomecánicos con la calidad de roca, las recomendaciones de sostenimiento y dimensionamiento, el estándar y el PETS. Los estudios hidrogeológicos y de sismicidad inducida siguen los **Anexos 39 C y 39 D**. Los estudios de estabilidad de taludes se exigen durante la operación y hasta el final del cierre.
  - **Art. 4** incorpora los Anexos 39, 39 A, 39 B, 39 C, 39 D, 40, 41, 42 y 43.
  - **Art. 5** ordena publicar los anexos en gob.pe/minem el mismo día. El texto de los anexos **no está en El Peruano**: el oficial es la publicación de MINEM.
- **DS 023-2017-EM** no creó estos anexos. En la compilación de MINEM, el art. 33 solo lleva la nota «modificado por D.S. N° 034-2023-EM art. 2».
- Textos revisados: anexos de MINEM (`dl\5631689-anexos-ds-024-2016-em.pdf`, PDF físico pp. 67–68 y 72–73) y compilación oficial de MINEM «Reglamento… y modificatorias», edición 2026 (`dl\5631689-rsso-reglamento-2026.pdf`, pp. 275, 276 y 279–280; art. 33 en p. 55). Entre ambos solo cambian la maquetación y erratas («2.44.» por «2.4.4.», «(Método (Brasilero)»).

**Importante para la librería**: los tres anexos son **índices de contenido**, no traen fórmulas, tablas de valores ni factores de seguridad. Sirven como plantilla del informe.

### Anexo N° 39 A — Estructura del estudio geomecánico global
1. Introducción: 1.1 Objetivo y alcances; 1.2 Información técnica revisada; 1.3 Criterios de diseño (descripción general).
2. Investigaciones de campo y laboratorio: 2.1 Mapeo geomecánico de labores subterráneas; 2.2 Logueo de perforaciones diamantinas; 2.3 Recopilación del modelo 3D de tajeos; 2.4 Ensayos de laboratorio de mecánica de rocas: 2.4.1 Propiedades físicas; 2.4.2 Compresión simple (uniaxial); 2.4.3 Carga puntual (point load); 2.4.4 Compresión triaxial; 2.4.5 Tracción (método brasileño); 2.4.6 Propiedades elásticas.
3. Caracterización geomecánica del macizo rocoso: 3.1 Geología (3.1.1 regional; 3.1.2 local); 3.2 Hidrogeología; 3.3 Geoestructuras (3.3.1 fallas; 3.3.2 discontinuidades); 3.4 Caracterización geomecánica: 3.4.1 Propiedades físicas y mecánicas de la roca intacta; 3.4.2 Índice RQD; **3.4.3 Sistema de clasificación RMR**; 3.4.4 Sectores de diseño; 3.4.5 Parámetros de diseño de resistencia de roca intacta del macizo (laboratorio).
4. Diseño de excavaciones para los métodos de minado (subterránea): 4.1 Metodología; 4.2 Alternativas de método; 4.3 Diseño de aberturas; 4.4 Pilares costilla y pilares puente; 4.5 Resistencia del relleno; 4.6 Modelo numérico de esfuerzos (software) y secuencia de minado.
5. Diseño de sostenimiento de labores mineras (subterránea).
6. Instrumentación y monitoreo.
7. Conclusiones y recomendaciones.
8. Anexos.

### Anexo N° 39 B — Estructura de la evaluación geomecánica local (minería subterránea)
1. Introducción
2. Caracterización geomecánica del macizo rocoso
3. Condiciones geomecánicas actuales de la labor
4. Evaluación de estabilidad: 4.1 Cálculo empírico; 4.2 Análisis cinemático de cuñas; 4.3 Modelamiento numérico (4.3.1 Recomendación de excavación o explotación; 4.3.2 Recomendación de reforzamiento o sostenimiento)
5. Conclusiones y recomendaciones
6. Anexos

Además: «Se deberá presentar una memoria resumen con los parámetros de entrada del software geomecánico utilizado y una copia electrónica de los archivos». Esto vuelve requisito exportar los parámetros de entrada.

### Anexo N° 39 D — Estructura del estudio de sismicidad inducida (minería subterránea)
1. Introducción: 1.1 Objetivos (general y específicos); 1.2 Alcances.
2. Antecedentes y condiciones de sismicidad actual: 2.1 Unidad minera (ubicación); 2.2 Zonas o minas con sismicidad inducida: 2.2.1 Ubicación; 2.2.2 Ensayos de laboratorio de mecánica de rocas; 2.2.3 Mediciones de esfuerzos in situ; 2.2.4 Planos topográficos de detalle; 2.2.5 Planos estructurales; 2.2.6 Información geológica y geotécnica; 2.2.7 Caracterización geomecánica, calidades zonificadas; 2.2.8 Diseño de mina explotado y labores de avance de la zona de eventos; 2.2.9 Diseño de mina actual y futuro (secuencia y dimensiones de cavidades).
3. Sistema de alertas: 3.1 Monitoreo microsísmico (introducción; planos de ubicación y cobertura; equipos y software).
4. Análisis de peligro y riesgo sísmico: 4.1 Introducción; 4.2 Parámetros: 4.2.1 Poisson y Gauss; 4.2.2 Tasa de producción de eventos y disparos; **4.2.3 Gutenberg-Richter, parámetro «b»**; 4.2.4 Distancia entre eventos; 4.2.5 Radios de ruptura; 4.2.6 Probabilidad de ocurrencia; 4.2.7 Periodo de retorno; 4.2.8 Distribución temporal; 4.2.9 Conclusiones.
5. Voladura y sismicidad inducida: 5.1 Subterránea y 5.2 Superficial (introducción, metodología del monitoreo de vibraciones, equipos, procesamiento, conclusiones; anexos: plano de ubicación, registros, fotos).
6. Plan de acción y medidas de control: medidas tácticas, estratégicas, cronograma.
7. Conclusiones y recomendaciones. 8. Anexos (data microsísmica procesada, planos, figuras 3D de eventos, panel fotográfico). Bibliografía. Apéndice: glosario (conceptos teóricos, parámetros sísmicos).

---

## 4. Gráfico de estabilidad de Mathews

### 4.1 Mawdesley, Trueman y Whiten (2001), *Mining Technology* 110(1) 27–39 [V1, p. 5 física]
```
z = a + b1·X1 + b2·X2 + … + bk·Xk                (ec. 3)
f(z) = 1 / (1 + e^(−z))                          (ec. 4)
z = a + b1·ln S + b2·ln N                         (ec. 5)
```
Usaron un logit de **tres niveles** (estable, falla, falla mayor). El artículo **no publica a, b1 ni b2**. Da un valor logit de corte de 0.865 (con 48 % de probabilidad de estable y falla, y 4 % de falla mayor sobre la línea). Los coeficientes estarían en la tesis de Mawdesley (2002, Univ. of Queensland) [NV].

### 4.2 Mortazavi y Osserbay, preprint Research Square rs-191163 (2021, CC BY) [V1 con reserva]
```
N = Q′ × A × B × C                                     (ec. 1, p. 3)
Z = 3.146 − 1.173·ln S + 0.8409·ln N                    (ec. 6, p. 10)
Z = ln(p / (1 − p))                                    (ec. 7)
N = exp((Z − α − β1·ln S) / β2)                         (ec. 8)
Estable–falla:        Z = ln(0.89/0.11) = 2.09  → reportan N = e^(−1.1 + 1.62·ln S)    (ec. 17–18, p. 16)
Falla–falla mayor:    Z = ln(0.78/0.22) = 1.27  → reportan N = e^(−2.14 + 1.62·ln S)   (ec. 19–20)
```
**Incoherencia interna del preprint.** Con α = 3.146, β1 = −1.173 y β2 = 0.8409, la ec. 8 da para Z = 2.09:
N = exp((2.09 − 3.146 + 1.173·ln S)/0.8409) = **e^(−1.256 + 1.395·ln S)**, no e^(−1.1 + 1.62·ln S). Además, el texto de la ec. 18 escribe «2.09 − 3.146 − 1.17 ln S» y divide entre 0.84. **No programes estas fronteras** hasta ver la versión publicada (Geotech. Geol. Eng. 40(5) 2409–2424, 2022, de pago) o recalcularlas con los datos.
Las ecuaciones de frontera de Mortazavi son líneas rectas en ln N–ln S, igual que en Mawdesley.

### 4.3 Factores A, B y C
- **A (esfuerzo)** [V2, Osinergmin fig. 7-5, p. 59]: A = 0.1 si σc/σi ≤ 2; A = 1.0 si σc/σi ≥ 10; lineal entre los dos. La recta que pasa por (2, 0.1) y (10, 1.0) es **A = 0.1125·(σc/σi) − 0.125**. Eso es aritmética sobre esa descripción, no una ecuación vista en Potvin. Mortazavi (p. 4) confirma 0.1 para σc/σi < 2 en Potvin.
- **B (orientación)** [V2, Osinergmin fig. 7-6, p. 60]: es una **familia de curvas** según la diferencia de rumbo (0°, 30°, 45°, 60°, 90°) y la diferencia de buzamiento. Valores leídos de la curva de 0°: 0.3 en 0°, 0.2 entre 10° y 30°, 0.8 en 60°, 1.0 en 90°. No hay ecuación publicada: hay que digitalizarla [NV].
- **C (gravedad)** [V2]: Osinergmin (fig. 7-7, p. 61) rotula **C = 8 − 6·cos(buzamiento de la cara)**, para caída por gravedad y lajamiento. Los rótulos coinciden con la fórmula: 2.8 en 30°, 3.4 en 40°, 4.1 en 50°, 5.0 en 60°, 5.9 en 70°, 7.0 en 80°; 2 en techo horizontal y 8 en pared vertical.
  - Mortazavi (ec. 2, p. 3) atribuye a Mathews et al. (1981) **C = 8 − 7·cos(dip)**. Esa fórmula da 1 en techos y contradice el «2 en techos horizontales» del mismo método. **Discrepancia sin resolver** [NV].
  - El C de Potvin para **deslizamiento** (en función del buzamiento de la junta crítica) no lo vi en ninguna fuente [NV].

**Vía legal**: Potvin (1988), tesis PhD UBC, **acceso abierto** en UBC Open Collections, ítem 1.0081130 (handle 2429/29264). UBC bloquea los clientes automáticos: descárgala tú en el navegador. La versión publicada de Mortazavi y la de Suorineni (2010) se piden por biblioteca o al autor (los dos tienen ResearchGate). La tesis de Mawdesley (2002), en UQ eSpace o a pedido.

---

## 5. SMR (Romana 1985; Tomás et al. 2007)

Fuente: Tomás, R., Romana, M. y Serón, J. B. (2017). «Revisión del estado actual de la clasificación geomecánica Slope Mass Rating (SMR)». *Boletín de la SEMSIG*, 190, 23–42 (RUA hdl 10045/70953). Romana, autor del SMR, es coautor, y Tomás es el autor de las funciones continuas: **[V1-a]**. Tomás et al. (2007) está en RUA, pero en acceso restringido. Tomás et al. (2006) (`tomas2006.pdf`) es el antecedente en español.

### 5.1 Fórmula y factores discretos (Romana 1985; tabla 1 en p. 26)
```
SMR = RMRb + (F1 × F2 × F3) + F4                 (ec. 1)
```
| Rotura | | Muy favorable | Favorable | Normal | Desfavorable | Muy desfavorable |
|---|---|---|---|---|---|---|
| P | A = \|αj − αs\| | > 30° | 30–20° | 20–10° | 10–5° | < 5° |
| T | A = \|αj − αs − 180°\| | (mismos rangos) | | | | |
| P/T | **F1** | 0.15 | 0.40 | 0.70 | 0.85 | 1.00 |
| P | B = βj | < 20° | 20–30° | 30–35° | 35–45° | > 45° |
| P | **F2** | 0.15 | 0.40 | 0.70 | 0.85 | 1.00 |
| T | **F2** | 1.00 en todas | | | | |
| P | C = βj − βs | > 10° | 10–0° | 0° | 0–(−10°) | < (−10°) |
| T | C = βj + βs | < 110° | 110–120° | > 120° | — | — |
| P/T | **F3** | 0 | −6 | −25 | −50 | −60 |

P = rotura plana; T = vuelco; α = dirección de buzamiento; β = buzamiento; j = discontinuidad; s = talud. Para cuña se usa la línea de intersección (αi, βi), según el uso habitual: **la tabla de 2017 no muestra la fila de cuña** [NV para cuña desde esta fuente].
En vuelco no hay clases «desfavorable» ni «muy desfavorable» de F3 (p. 26).

**F4** (tabla 2): talud natural +15; precorte +10; voladura suave +8; voladura normal o excavación mecánica 0; voladura deficiente −8.
**Clases** (tabla 3): I 81–100 muy buena, completamente estable, sin roturas, P(rotura) 0; II 61–80 buena, estable, algunos bloques, 0.2; III 41–60 normal, parcialmente estable, plana en algunas juntas o cuñas, 0.4; IV 21–40 mala, inestable, plana o grandes cuñas, 0.6; V 0–20 muy mala, completamente inestable, grandes planos o circular, 0.9.

### 5.2 Funciones continuas
Romana (1993):
```
F1 = (1 − sen|A|)²        (ec. 2)
F2 = tan² B               (ec. 3)
```
Tomás et al. (2007) (ec. 4–7, p. 28):
```
F1 = 16/25 − (3/500)·atan( (1/10)·(|A| − 17) )
F2 = 9/16 + (1/195)·atan( (17/100)·B − 5 )          (rotura plana y cuña)
F3 = −30 + (1/3)·atan(C)                             (rotura plana y cuña)
F3 = −13 − (1/7)·atan(C − 120)                       (vuelco)
```
**Unidades: atan devuelve GRADOS** (A, B y C también en grados). Lo comprobé con los límites de la tabla. F1(0) = 0.64 + 59.5·0.006 = 0.997, F2(0) = 0.159, F2(90) = 0.996, F3 plana(−30) = −59.4, F3 vuelco(130) = −25.0. Con radianes no se reproducen. Diferencia máxima frente a las discretas: < 7 puntos (p. 27).

**Vía legal**: pedir a R. Tomás (roberto.tomas@ua.es) el postprint de 2007; Romana (1985) se consigue en las actas del ISRM en Zacatecas por biblioteca.

---

## 6. Barton-Bandis

Fuente [V2]: Hoek, E., *Practical Rock Engineering*, cap. 4 «Shear strength of discontinuities» (versión 2023 de rocscience.com, `pdfs\pre23_4.pdf`), pp. 5–6 y 12.
```
τ = σn · tan( φb + JRC·log10(JCS/σn) )            (ec. 4; Barton 1973, 1976)
τ = σn · tan( φr + JRC·log10(JCS/σn) )            (ec. 5; Barton y Choubey 1977, 130 ensayos)
φr = (φb − 20°) + 20°·(r/R)                        (ec. 6)
   r: rebote Schmidt en la junta húmeda y meteorizada; R: en superficie seca, sana y aserrada
JRCn = JRC0 · (Ln/L0)^(−0.02·JRC0)                 (ec. 7; Barton y Bandis 1982)
JCSn = JCS0 · (Ln/L0)^(−0.03·JRC0)                 (ec. 8; Barton y Bandis 1982)
   JRC0, JCS0, L0: escala de laboratorio (100 mm); JRCn, JCSn, Ln: tamaño de bloque in situ
```
Límites de uso (p. 12): la ec. 6 [sic, se refiere a la ecuación de resistencia] no vale para σn = 0 y pierde sentido práctico si φr + JRC·log10(JCS/σn) > 70°; el límite superior es σn = JCS.
Las ec. 5 y 6 forman parte del criterio Barton-Bandis (Barton y Bandis 1990).

**Vía legal**: Barton, N. (2013). «Shear strength criteria for rock, rock joints, rockfill and rock masses: Problems and some solutions». *JRMGE*, 5(4), 249–261, doi:10.1016/j.jrmge.2013.05.008. **Es acceso abierto (CC BY-NC-ND)**, pero ScienceDirect devolvió 403 al cliente automático: descárgalo en el navegador y queda [V1-a]. Barton y Choubey (1977) y Barton y Bandis (1982) se piden por biblioteca (Springer y OnePetro/ARMA).

---

## 7. Q-slope

Fuente [V1-a]: Bar, N. y Barton, N. (2018). «Rock Slope Design using Q-slope and Geophysical Survey Data». *Periodica Polytechnica Civil Engineering*, 62(4), 893–900, doi:10.3311/PPci.12287 (acceso abierto). Son los mismos autores del método. Bar y Barton (2017, RMRE 50: 3307–3322) está cerrado.

```
Qslope = (RQD/Jn) · (Jr/Ja)_0 · (Jwice / SRFslope)        (ec. 1, p. 894)
τ ≈ σn · tan⁻¹(Jr/Ja)                                      (ec. 2)
β = 20·log10(Qslope) + 65°                                  (ec. 3, p. 896)
   Qslope = 10 → 85°;  1 → 65°;  0.1 → 45°;  0.01 → 25°
Qc = (σc/100)·Q ;  Vp ≈ 3.5 + log Qc ;  Qc ≈ 10^(Vp − 3.5) ;  Qslope ≈ (Qc)_0 · Jwice/SRFslope   (ec. 4–7)
```
β es el ángulo más empinado que no requiere refuerzo ni soporte. Viene de más de 450 casos de 5 m a más de 250 m de altura.

- RQD, Jn, Jr y Ja: iguales al sistema Q (tablas 1–4). RQD ≤ 10 se toma como 10; basta con intervalos de RQD de 5.
- **Cuñas**: (Jr/Ja)_0 = (Jr/Ja)_1 × O_A × (Jr/Ja)_2 × O_B. El texto pone como ejemplo «(Jr/Ja)1 × 0.7» y «(Jr/Ja)2 × 0.9».
- **O-factor** (tabla 5, p. 895):

| Descripción | Set A | Set B |
|---|---|---|
| Very favourably oriented | 2.0 | 1.5 |
| Quite favorable | 1.0 | 1.0 |
| Unfavorable | 0.75 | 0.9 |
| Very unfavorable | 0.50 | 0.8 |
| Causing failure if unsupported | 0.25 | 0.5 |

  Set A se aplica a la familia más desfavorable; Set B, a la secundaria (cuñas).
- **Jwice** (tabla 6):

| | Desierto | Húmedo | Tormentas tropicales | Cuña de hielo |
|---|---|---|---|---|
| Estructura estable, roca competente | 1.0 | 0.7 | 0.5 | 0.9 |
| Estable, roca incompetente | 0.7 | 0.6 | 0.3 | 0.5 |
| Inestable, roca competente | 0.8 | 0.5 | 0.1 | 0.3 |
| Inestable, roca incompetente | 0.5 | 0.3 | 0.05 | 0.2 |

  Con drenaje: Jwice × 1.5. Con refuerzo: × 1.3. Con los dos: × 1.5 × 1.3.
- **SRFslope = máx(SRFa, SRFb, SRFc)** (p. 895).
  - SRFa (tabla 7): A aflojamiento leve por cercanía a la superficie, voladura o excavación, 2.5; B bloques sueltos, grietas de tracción, cizalla en juntas, susceptible a meteorización, voladura severa, 5; C como B pero muy susceptible a meteorización, 10; D erosión avanzada por agua o hielo, 15; E talud residual con transporte importante de material, 20.
  - SRFb (tabla 8; σc/σ1 → SRFb): F rango moderado 50–200 → 2.5–1; G alto 10–50 → 5–2.5; H falla localizada de roca intacta 5–10 → 10–5; J aplastamiento o fluencia plástica 2.5–5 → 15–10; K flujo plástico de material ablandado 1–2.5 → 20–15.
  - SRFc (tabla 9; favorable / desfavorable / muy desfavorable / causa falla sin soporte): L discontinuidad mayor con poca o ninguna arcilla 1 / 2 / 4 / 8; M con RQD100 = 0 por arcilla y roca triturada 2 / 4 / 8 / 16; N con RQD300 = 0 4 / 8 / 12 / 24 (RQD100 y RQD300: muestreo perpendicular de 1 y 3 m).
- Ja (tabla 4, igual que Q): A 0.75; B 1.0; C 2.0; D 3.0; E 4.0; F 4.0; G 6.0; H 8.0; J 8–12; M «6, 8 u 8–12»; N 5.0; OPR «10, 13 o 13–20». Jr (tabla 3) igual que Q, y agrega **J = 1.0** («arena, grava o zona triturada que impide el contacto»).
- Otros autores ajustan la constante 65° por probabilidad de falla (70.5 y 73.5): [NV], no está en esta fuente. Bar y Barton remiten a las isolíneas de PoF de la fig. 2 de su ref. [5].

---

## 8. Read y Stacey (2009): criterios de aceptación

El libro (*Guidelines for Open Pit Slope Design*, CSIRO Publishing, 2009) es de pago. La tabla es la **9.9** del capítulo 9 (Wesseloo y Read, «Acceptance criteria»).

Reproducción [V2]: Moffitt, K. (2023). SSIM 2023, ACG, tabla 1, p. 3 (`dl\moffitt.pdf`), «Typical FoS and PoS requirements for open pit slope design (Table 9.9, Wesseloo & Read 2009)»:

| Escala | Consecuencia de falla | FoS estático mínimo | PoF máximo |
|---|---|---|---|
| Banco | Baja–alta | 1.1 | 25–50 % |
| Interrampa | Baja | 1.15–1.20 | 25 % |
| | Media | 1.20 | 20 % |
| | Alta | 1.20–1.30 | 10 % |
| Global | Baja | 1.20–1.30 | 15–20 % |
| | Media | 1.30 | 5–10 % |
| | Alta | 1.30–1.50 | 5 % |

**Columna dinámica o pseudoestática: [NV].** Moffitt no la reproduce. Una lámina de SRK (Hormazábal 2018) la trae según el buscador (valores entre 1.0 y 1.1), pero el dominio no resolvió y no la pude abrir. No uses valores dinámicos sin ver el libro.

**Vía legal**: CSIRO Publishing (libro o capítulo 9 suelto); bibliotecas de facultades de minas (UNI, PUCP, UNSCH vía préstamo interbibliotecario); o pedirle la tabla a los autores (Wesseloo, ACG). Hay un trabajo de 2020 que propone actualizar los criterios para taludes en operación («Design acceptance criteria for operating open-pit slopes: an update»), que conviene revisar.

---

## 9. «RMR = 22·ln(De) + 25»

**[NV]: no encontré el origen.** No aparece en Bieniawski (1989) según las fuentes revisadas: el ábaco de autosoporte es gráfico y no tiene ecuación. Tampoco está en NGI 2015/2025, en Hoek ni en Osinergmin. Búsquedas web con la forma directa y la inversa («ESR·exp((RMR − 25)/22)») no dieron nada.

**Hipótesis (aritmética mía, no es una fuente).** Si se combinan la luz máxima sin soporte De = 2·Q^0.4 (Barton et al. 1980, vía Hoek) y la correlación RMR = 9·ln Q + 44 (Bieniawski 1976):
ln Q = 2.5·ln(De/2) → **RMR = 22.5·ln(De) + 28.4**.
El coeficiente (22.5 ≈ 22) se parece, pero la constante no (28.4 frente a 25). Puede ser una variante redondeada o tomada de otra correlación RMR–Q. **No la programes como oráculo.** Si se incluye, que sea marcada «de procedencia desconocida», o mejor reemplazada por la combinación explícita de dos fórmulas citadas.
Siguiente paso: pedir a Miqueas una tesis peruana concreta que la use (la de Ancalla, UNSAAC, §2.3.8.1) y revisar a qué referencia la atribuye. Candidata a revisar: Lowson y Bieniawski (2013), RETC (SME, de pago).

---

## 10. Hoek-Brown 2018 y Laubscher

### 10.1 Hoek y Brown (2019), «The Hoek–Brown failure criterion and GSI – 2018 edition», JRMGE 11(3) 445–463 [V1]
Archivo: `dl\hb2018.pdf`, versión *Article in press* (pp. 1–19; las páginas citadas son de esa versión, no de la paginación final).
```
mb = mi·exp((GSI − 100)/(28 − 14D))          (ec. 4)
s  = exp((GSI − 100)/(9 − 3D))               (ec. 5)
a  = 1/2 + (1/6)·(e^(−GSI/15) − e^(−20/3))   (ec. 6)
```
Sobre D (sección 8 y tabla 2, pp. 6–9):
- «A common error is to assume that the disturbance factor D should be applied to the entire rock mass in which the excavation is conducted. This will result in an extremely conservative and inappropriate design» (p. 8).
- Encabezado de la tabla 2: «**The disturbance factor D should never be applied to the entire rock mass surrounding an excavation**».
- Tabla 2 (p. 9):
  - Voladura controlada excelente, rozadora o TBM: **D = 0**.
  - Excavación mecánica o manual en roca de mala calidad: D = 0; con squeezing y levantamiento de piso sin solera temporal: **D = 0.5 sin solera**. En el túnel de ejemplo, D = 0.5 **solo en una zona de unos 2 m** alrededor de la mitad inferior de un túnel de 12 m de luz (p. 8).
  - Voladura muy mala en túnel de roca dura: **D = 1.0 en la superficie con disminución lineal a D = 0 a ±2 m**. En el texto: «D = 1.0, with a linear decrease to zero, has been assigned to the first 3 m» en un túnel de 8 m de luz (p. 8).
  - Taludes civiles con voladura a pequeña escala: **D = 0.5** con precorte o recorte; **D = 1.0** con voladura de producción. En el ejemplo de la presa, D = 0.5 en 1–2 m detrás de la cara y D = 1.0 en 2–3 m en la cara voladura masiva (p. 8).
  - Roca débil excavada con ripper o bulldozer, daño por alivio de esfuerzos: **D = 0.7**. Taludes de tajo muy grandes: **D = 1.0** por voladura de producción. Una relación de D transicional que incluya la relajación de esfuerzos puede derivarse del *disturbance rating* de Rose et al. (2018).
  - Tajo abierto (p. 8): bancos de 18 m con D = 1.0 en la roca inmediata, «graded downward, to a final value of D = 0, as the distance behind the face increases to about **30 % of the slope height**». Los taludes interrampa y finales también sufren daño por relajación, que puede superar al de la voladura.
  - Los taludes civiles pueden usar el D de minería a cielo abierto, pero con un FS global mayor por su vida más larga.
- Módulo (ec. 9–10): Erm = Ei·(0.02 + (1 − D/2)/(1 + e^((60 + 15D − GSI)/11))) y Erm = 10^5·(1 − D/2)/(1 + e^((75 + 25D − GSI)/11)); la fig. 13 muestra las curvas para D = 0, 0.5 y 1.
- Implicación para la librería: D debe ser un **campo por zona** (por ejemplo, función de la distancia a la cara), no un escalar global. Rose et al. (2018), *Slope Stability 2018*, sería la fuente para el D transicional en tajo [NV, no revisado].

### 10.2 Laubscher (1990), J. SAIMM 90(10) 257–273 [V1] (`laub_v090n10p257.pdf`)
- **Meteorización** (tabla VI, p. 264), ajuste en % según el tiempo de exposición (½, 1, 2, 3, 4+ años):

| Grado | ½ a | 1 a | 2 a | 3 a | 4+ a |
|---|---|---|---|---|---|
| Fresca | 100 | 100 | 100 | 100 | 100 |
| Leve | 88 | 90 | 92 | 94 | 96 |
| Moderada | 82 | 84 | 86 | 88 | 90 |
| Alta | 70 | 72 | 74 | 76 | 78 |
| Completa | 54 | 56 | 58 | 60 | 62 |
| Suelo residual | 30 | 32 | 34 | 36 | 38 |

- **Orientación de juntas** (tabla VII, p. 265): n.º de juntas que definen el bloque vs n.º de caras inclinadas desde la vertical, con columnas de 70, 75, 80, 85 y 90 %.
  - Fila 3 juntas: 3 (70 %), 2 (80 %), y en 90 % un símbolo **ilegible** («•»).
  - Fila 4: 4, 3, 2.
  - Fila 5: 5, 4, 3, 2, 1.
  - Fila 6: 6, 5, 4, 3, «2,1».
  - **Las celdas de las filas 3 y 4 no se leen bien** (no está claro en qué columna van). Revísalas en el PDF antes de programar.
  - Zonas de corte respecto al avance: 0–15° = 76 %, 15–45° = 84 %, 45–75° = 92 %. Avance contra el buzamiento: × 90 % (ejemplo: 70 % × 90 % = 63 %).
- **Buzamiento de la intersección en la base del bloque** (tabla VIII): por rangos de puntaje de condición (0–5 … 30–40) y buzamiento, ajustes de 70 a 90 %.
- **Esfuerzos inducidos**: hasta 120 % (compresión que cierra juntas) y hasta 60 % (diferencias de esfuerzo); «the total adjustment is from 60 to 120 per cent» (p. 266).
- **Voladura** (p. 266): perforación (boring) 100; voladura de paredes lisas 97; voladura convencional buena 94; voladura deficiente 80.
- **Resumen de ajustes** (p. 266): meteorización 30–100; orientación 63–100; esfuerzos inducidos 60–120; voladura 80–100 %.
  - El «ajuste total no menor de ~50 %» **no aparece en este artículo** [NV]. Viene de trabajos posteriores (Laubscher 1993/1994, Jakubec y Laubscher 2000).
- RMS = ((A − B)/80) × C × 80/100, con A = puntaje total, B = puntaje de IRS y C = IRS (MPa). DRMS = RMS × ajustes (meteorización, orientación, voladura). Ejemplo del autor: 85 % × 75 % × 90 % = 57 %, con DRMS = 50 × 0.57 = 29 MPa.

### 10.3 Laubscher (1994), J. SAIMM 94(10) 279–293 [V1] (`laub_v094n10p279.pdf`)
Fig. 1 (p. 282): «A stability diagram for various mines worldwide», MRMR (0–100) vs radio hidráulico = área/perímetro (0–80 m). Tiene zonas **estable**, **transicional** y **hundimiento (caving)** separadas por dos curvas, **sin ecuación**. Para usarlo hay que digitalizar las dos curvas, citar la figura y declarar el error de digitalización.

---

## Qué falta y cómo conseguirlo por vía legal

| Falta | Vía |
|---|---|
| Celada et al. (2014), RMR14 original | Geocontrol o los autores; actas WTC 2014 por préstamo interbibliotecario; libro de Celada y Bieniawski (2019, CRC) |
| Barton et al. (1974, *Rock Mechanics* 6) y Barton et al. (1980, Rockstore 80): L, luz máxima y P de 1974 | Biblioteca (Springer, Pergamon); pedir a NGI o a N. Barton (nickbarton.com) |
| Grimstad y Barton (1993), P_roof | Norwegian Concrete Association (actas de Fagernes), biblioteca |
| Potvin (1988), factores A, B, C | **Abierto** en UBC Open Collections (ítem 1.0081130): bajarlo en el navegador |
| Mortazavi y Osserbay (2022), versión publicada | Biblioteca o ResearchGate del autor; o recalcular las fronteras con su base de datos |
| Mawdesley (2002), coeficientes logit | UQ eSpace o pedirlos al autor |
| Tomás et al. (2007) postprint | Pedirlo a R. Tomás (RUA lo tiene restringido) |
| Romana (1985) | Actas ISRM en Zacatecas, biblioteca |
| Barton (2013), JRMGE | **Abierto**: bajarlo en el navegador desde ScienceDirect |
| Bar y Barton (2017), RMRE | Biblioteca o ResearchGate de N. Bar |
| Read y Stacey (2009), tabla 9.9 con la columna dinámica | CSIRO Publishing; biblioteca de minas |
| RMR = 22·ln(De) + 25 | Revisar la bibliografía de la tesis que la usa (Ancalla, UNSAAC) |
