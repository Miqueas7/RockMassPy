# Casos de validación y geotecnia de tajo abierto para una librería de geomecánica minera

Investigación hecha el 31-oct-2026, solo con web y documentos públicos. No se leyó ninguna carpeta local de clientes.

## 0. Cómo leer este informe

**Marcas de verificación**

- **[V1]**: lo leí en el documento original (o en la copia que publica el propio autor o editor). Cuando dice «[V1 + recalculado]», además reproduje el número en local con las ecuaciones publicadas (scripts en `scratchpad/geomecanica/chk/`, no son código de la librería).
- **[V2]**: lo vi en una fuente secundaria seria, o en los metadatos de Crossref (DOI, volumen, páginas).
- **[NV]**: no está verificado. Puede ser un dato de memoria, un extracto del buscador o una fuente que no pude abrir. No lo uses como oráculo de prueba hasta confirmarlo.

**Tolerancias que sugiero para las pruebas automáticas**

| Tipo de resultado | Tolerancia |
|---|---|
| Fórmula cerrada (mb, s, a, Q, RMR, A/B de cuña) | Media unidad del último dígito publicado (p. ej. 1.2601 → ±0.00005; 0.36 → ±0.005) |
| c′/φ′ equivalentes de Hoek-Brown | φ′ ±0.05°; c′ ±0.005 MPa (el original redondea c′ a 2 decimales) |
| FoS de equilibrio límite frente a la solución de referencia (ACADS, Fredlund y Krahn) | ±2 % (dispersión propia de la encuesta ACADS); frente al valor del mismo método publicado, ±0.5 % |
| Valores leídos de ábaco (Hoek 1974, ábacos de cuñas) | ±3 % |
| Monte Carlo (media del FoS, PoF) | Media ±0.02; PoF ±1.5 puntos porcentuales con ≥5 000 iteraciones y semilla fija |

**Licencias y uso de los oráculos.** Los manuales de verificación de Rocscience, NGI y CSIRO tienen copyright. Puedes usar los números (entradas y resultados) como oráculo de prueba citando la fuente, pero no copies figuras ni texto dentro del repositorio. Las geometrías que en el original solo vienen dibujadas en una figura tienen que redibujarse a mano, con la coordenada citada.

---

## A) Casos de validación

### A.1 Hoek-Brown generalizado (2002) y parámetros derivados

| # | Fuente (acceso) | Entradas | Salida publicada | Marca |
|---|---|---|---|---|
| HB-1 | Hoek, Carranza-Torres y Corkum (2002), sección 7. [PDF libre (UBC)](https://www.eoas.ubc.ca/courses/eosc433/lecture-material/2002-HoekBrownCriterion.pdf) | σci = 50 MPa, mi = 10, GSI = 45, D = 0, túnel a 100 m de profundidad, σ′3max con la ec. 18 | φ′ = 47.16°, c′ = 0.58 MPa | [V1 + recalculado]: con γ = 0.027 MN/m³ obtengo 47.16° y 0.583 MPa. **El paper no publica γ**, así que el valor 0.027 es una suposición mía (con 0.025 salen 47.71° y 0.561) |
| HB-2 | Igual | Mismo macizo, talud de H = 100 m, D = 1, σ′3max con la ec. 19 | φ′ = 27.61°, c′ = 0.35 MPa | [V1 + recalculado] 27.61° y 0.348 MPa con γ = 0.027 MN/m³ |
| HB-3 | Hoek, *Practical Rock Engineering* (PRE), capítulo «Rock mass properties», tabla 1. [PDF libre (Rocscience)](https://www.rocscience.com/assets/resources/learning/hoek/Practical-Rock-Engineering-Chapter-11-Rock-Mass-Properties.pdf) | Triaxiales: σ3 = 0, 5, 7.5, 15, 20 MPa; σ1 = 38.3, 72.4, 80.5, 115.6, 134.3 MPa | σci = 37.4 MPa, mi = 15.50, r² = 0.997 | [V1 + recalculado] 37.39 / 15.50 / 0.9971 |
| HB-4 | PRE, «Practical examples», brecha Braden (El Teniente) | σci = 51, mi = 16.3, GSI = 75 | mb = 6.675, s = 0.062, a = 0.501 | [V1 + recalculado]. El Em = 15 000 MPa **no** sale de ninguna fórmula: no lo uses |
| HB-5 | PRE, gneis de Río Grande | σci = 110, mi = 28, GSI = 75 | mb = 11.46, s = 0.062, a = 0.501 | [V1 + recalculado] (11.466). Em = 45 000 sale del criterio del autor: no lo uses |
| HB-6 | PRE, esquisto de Nathpa Jhakri | σci = 30, mi = 15, GSI = 65 | mb = 4.3, s = 0.02, a = 0.5 | [V1 + recalculado] |
| HB-7 | PRE, esquisto de Atenas | σci = 5–10, mi = 9.6, GSI = 20 | mb = 0.55, s = 0.0001 | [V1 + recalculado] (s = 1.4·10⁻⁴) |
| ✗ | PRE, filita de Yacambú | σci = 50, mi = 10, GSI = 25 | mb = 0.481 publicado | **No coincide**: la ecuación da 0.687. Lo descarto como prueba |
| HB-8 | Carranza-Torres y Hormazábal (2020), Slope Stability 2020 (Perth). [Preprint libre](https://www.d.umn.edu/~carranza/SLOPE20/%5b2020%5d_CCT_&_EH_%5bSlopes_HB_Rock_Mass-Perth-conference%5d.pdf) | Tabla 1, cinco taludes de 50° con D = 0 y a = 0.5. Caso 3: H = 360 m, γ = 27 kN/m³, GSI = 42, σci = 77.7 MPa, mi = 10 → mb = 1.2601, s = 1.5893·10⁻³ | Los 5 casos dan FS = 2.01 (Bishop circular), xc/H = −0.5758, yc/H = 1.6293, R/H = 1.728. Con s = 0: FS = 1.88 | [V1]. mb y s del caso 3 recalculados. Es la mejor prueba de **similitud**: cinco entradas distintas, mismo FS |

Comentarios:

- Para el módulo de deformación, las fórmulas de Hoek y Diederichs (2006) [V2: Crossref] y la ec. 11 de Hoek (2002) [V1] son cerradas. No encontré un ejemplo publicado con su Erm, así que la prueba tiene que ser de fórmula, con valores calculados por ti y documentados como tales.
- RocLab/RocData: no encontré un manual de verificación público de RocData. Los casos HB-1 y HB-2 reproducen exactamente lo que hace RocLab.
- Para el GSI 2018, Hoek y Brown (2019) es la referencia vigente [V2: Crossref], pero no revisé si tiene ejemplos numéricos.

### A.2 Clasificaciones

| Método | Caso o fuente | Entradas | Salida | Marca |
|---|---|---|---|---|
| **RMR89** | Hoek, PRE, capítulo «Rock mass classification». [PDF libre](https://www.rocscience.com/assets/resources/learning/hoek/Practical-Rock-Engineering-Chapter-3-Rock-Mass-Classification.pdf) | Granito; Is50 = 8 MPa → 12; RQD = 70 % → 13; espaciado de 300 mm → 10; condición desglosada 4+4+3+6+5 = 22; agua «wet» → 7; orientación «Fair» (túnel contra el buzamiento de 60°) → −5 | RMR = 59 | [V1]. Es el único ejemplo RMR89 completo y verificado |
| **Q (1974)** | Mismo capítulo | Cámara de chancado de 15 m a 2 100 m de profundidad; RQD = 90, Jn = 4, Jr = 3, Ja = 1, Jw = 1, SRF = 15 (σc/σ1 = 2) | Q = 4.5; ESR = 1.6 → De = 9.4; categoría 4 (pernos a 2.3 m + 40–50 mm de shotcrete) | [V1]. La variante con RQD = 50 publica Q = 2.9, pero la fórmula da **2.5**: es un error del original, no la uses |
| Q: relaciones | Mismo capítulo, ecs. 3 a 5 | — | Luz máxima sin soporte = 2·ESR·Q^0.4; L = 2 + 0.15·B/ESR; Proof = (2·√Jn / 3Jr)·Q^(−1/3) | [V1] luz máxima; [V2] las otras dos (el texto del PDF sale dañado) |
| **Q 2015 → 2025** | NGI, *Using the Q-system* (abril de 2025) y su registro de cambios. [Manual](https://prod.ngi.no/globalassets/bilder/forskning-og-radgivning/bygg-og-anlegg/q-handbook_2025_english_final.pdf), [registro de cambios](https://www.ngi.no/globalassets/bilder/forskning-og-radgivning/bygg-og-anlegg/change-log-q-handbook-revision-2025_final.pdf) | — | Cambios en 2025: SRF pasa de 4 a **5 categorías**, porque la antigua b) se parte en «masiva, tensión baja o favorable» y «masiva, problemas de tensión»; la relación σc/σ1 sale de la tabla principal de SRF; se añade **Jr = 4** para superficies escalonadas; aparece Q′ (Qbase); las RRS pasan a llamarse A/B/C; E500 → E700 en la clase 4; la elevación de Q para paredes baja su límite de 0.1 a 1; la tabla de ESR se mantiene (A: 3–5, B: 2.5/2.0, C: 1.6, D: 1.3, E: 1.0, F: 0.8, G: 0.5) | [V1]. La librería necesita un parámetro `edicion = 1974 | 2015 | 2025` porque cambia la tabla SRF. No encontré un ejemplo resuelto en el manual de 2025 |
| **GSI cuantificado** | Hoek, Carter y Diederichs (2013), ARMA 13-672. [PDF libre](https://www.rocscience.com/assets/resources/learning/hoek/2013-Quantification-of-the-GSI-Chart.pdf) | — | GSI = 1.5·JCond89 + RQD/2 (ec. 1); GSI = 2·JCond76 + RQD/2 (ec. 2); JCond89 = 35·(Jr/Ja)/(1 + Jr/Ja); RQD = 100·e^(−0.1λ)(0.1λ + 1); RQD = 115 − 3.3·Jv | [V1]. La ec. 3 (GSI en función de Jr/Ja) no salió legible; por sustitución el coeficiente es 52.5 y el paper lo da como 52 [NV]. No hay ejemplo resuelto: haz pruebas de fórmula |
| RQD | Deere; Priest y Hudson (1976); Palmström | — | Fórmulas anteriores | [V1] las fórmulas (tomadas de Hoek et al. 2013). No hay un ejemplo publicado verificado |
| **RMR14** | Celada et al. (2014), WTC Foz do Iguaçu | — | Estructura RMR14 = (RMR14b + F0)·Fe·Fs; RMR14b suma resistencia, discontinuidades por metro, condición, agua y alterabilidad (Id2) | [V2] la estructura (CGE Journal, ITA). La correlación RMR14 ≈ 1.1·RMR89 + 2 es [NV]. **0 casos completos** |
| **MRMR** | Laubscher (1990); Laubscher y Jakubec (2001) | — | IRMR × ajustes (meteorización, orientación, esfuerzos inducidos, voladura) → MRMR; ábaco MRMR–radio hidráulico | [V2] la estructura (ACG 2024, JME). **0 casos completos**: las tablas de ajuste están en libros con copyright |
| **Q-slope** | Bar y Barton (2017), RMRE 50:3307–3322 | — | Q-slope = (RQD/Jn)·(Jr/Ja)₀·(Jwice/SRFslope); β = 20·log10(Q-slope) + 65° | [V2] (Crossref y fuentes secundarias). **0 casos completos verificados**: el artículo está tras muro de pago |
| **SMR** | Romana (1985) por tramos; Tomás, Delgado y Serón (2007), funciones continuas | A = \|αj − αs\| para planar (otra definición para volteo) | F1 = 16/25 − (3/500)·atan((\|A\| − 17)/10); F2 = 9/16 + (1/195)·atan(0.17·βj − 5), y F2 = 1 en volteo; F3 = −30 + (1/3)·atan(βj − βs) en planar, o −13 − (1/7)·atan(βs + βj − 120) en volteo; atan en grados | [V1] en el código de [SMRTool](https://github.com/adririquelme/SMRTool) (GPL-2.0); [V2] el paper (Crossref). **0 ejemplos resueltos publicados verificados.** SMRTool sirve como oráculo ejecutable, pero por la GPL **no copies su código**: solo compara salidas |
| **Mathews** | Mawdesley, Trueman y Whiten (2001); Mortazavi y Osserbay (2021), preprint | N = Q′·A·B·C; S = área/perímetro | Modelo logit: z = a + b1·ln S + b2·ln N. Gráfico consolidado: Z = 3.146 − 1.173·ln S + 0.8409·ln N, con P(estable–falla) = 0.91 | [V1] la forma de Mawdesley 2001; [V1] la ecuación de Mortazavi (preprint, revisar el signo y el orden en la versión publicada). Las fórmulas de A y C de Potvin (1988) son [NV]. **0 casos completos** |

### A.3 Análisis cinemático, falla planar, cuñas y volteo

| # | Fuente (acceso) | Método | Entradas | Salida | Marca |
|---|---|---|---|---|---|
| PL-1 | RocPlane Verification Manual, problema 1 (Hoek, Sau Mau Ping). [PDF](https://static.rocscience.cloud/assets/verification-and-theory/RocPlane/RocPlane-Verification-Manual.pdf) | Planar, sin grieta de tracción | H = 60 m, ψf = 50°, ψp = 35°, γr = 0.027 MN/m³, γw = 0.01 MN/m³, c = 0.10 MPa, φ = 35°, α = 0.08 g, saturado (U = γw·H²/(4·sin ψp)) | FS = 0.8184 | [V1 + recalculado] 0.818425 |
| PL-2 | Igual | Planar con grieta de tracción llena al 90 % | Igual; z = H·(1 − √(cot ψf·tan ψp)) = 14.0092 m; zw = 0.9z | FS = 1.0655 | [V1 + recalculado]. **Ojo**: el manual imprime valores intermedios erróneos (zw = 16.61, U = 4.49, y c = 0.01 en la línea final). Con zw = 12.608 y c = 0.1 se reproduce 1.0655 |
| PL-3 | RocPlane, problema 7 (Kliche) | Planar con grieta y perno | H = 30 m, 50°/35°, grieta a 9 m de la cresta y llena al 51 %, c = 7 t/m², φ = 30°, γ = 2.79 t/m³, α = 0.10 g, fuerza externa de 37 t/m a 90° | FS = 1.222; con un perno activo de 111 t/m a 30° → FS = 1.50 | [V1]. La tabla sale desordenada en el texto: confirma el emparejamiento en el PDF |
| PL-4 | RocPlane, problema 6 (Priest 1993) | Bloque rígido | Ver el PDF | FS = 1.049 | [V1] solo el resultado |
| PL-5 | Slide2 Verification, problema 43 (Baker 2001) | Planar por el pie (Culmann) | c = 30 kPa, φ = 30°, γ = 20 kN/m³; geometría en figura | FS = 1.35 en el plano de 49.5° | [V1] |
| CU-1 | Hoek (1974), *The design of rock slopes and foundations*, fig. 22. [PDF](https://static.rocscience.cloud/assets/resources/learning/hoek/1974-The-Design-of-Rock-Slopes-and-Foundations.pdf) | Cuña seca, sin cohesión (ábacos A y B) | Plano A 40/105, φ = 20°; plano B 70/235, φ = 30° | A = 1.75, B = 0.95, F = 1.18 | [V1]. Recalculado analíticamente: A = 1.763, B = 0.956, F = 1.194 (diferencia por lectura de ábaco; usa ±3 %) |
| CU-2 | SWedge Verification Manual, problema 6 (Priest 1993, ej. 1). [PDF](https://static.rocscience.cloud/assets/verification-and-theory/SWedge/SWedge-Verification-Manual.pdf) | Cuña tetraédrica, deslizamiento por dos planos, agua y carga externa | J1 47/203, J2 52/287, banco 5/225, talud 60/230; V = 45.20 m³; γ = 26 kN/m³; u1 = 5 kPa, u2 = 15 kPa; carga de 180 kN con tendencia/inmersión 168/70; c y φ en la tabla 1.6.2 | FS = 1.4966 (Priest ≈ 1.5) | [V1]. Confirma en el PDF cuál c/φ va con cada junta (la tabla sale desordenada) |
| CU-3 | SWedge, problema 7 (Priest, ej. 2) | Deslizamiento por un plano | Ver el PDF (V = 81.74 m³, γ = 25, u1 = 25 kPa, u2 = 15 kPa) | SWedge da 0.8493; Priest dice «≈ 0.9»; con las fuerzas de Priest sale 0.864 | [V1]. Tolerancia amplia (±5 %) |
| CU-4 a CU-6 | SWedge, problemas 3 a 5 (Kumsar, Aydan y Ulusay 2000, casos 3, 4 y 5) | Cuña estática y sísmica | Ver el PDF | Caso 3: 0.73 (ensayo) frente a 0.712; caso 4: 2.02 estático y 0.99 sísmico (kh = 0.3303); caso 5: FS = 1 con α = 0.32 | [V1] |
| CU-7 y CU-8 | Hoek, Kaiser y Bawden (1995), cap. 5. [Copia académica](https://galaxy.agh.edu.pl/~cala/hoek/Chapter5.pdf); también PRE 2023, cap. 8 | Cuñas laterales de túnel, φ = 30°, c = 0, sin agua: **el FS no depende del tamaño** | J1 70/036, J2 85/144, J3 55/262; eje del túnel 025/15 | Lateral 1, desliza sobre J1/J2: FS = 0.36. Lateral 2, desliza sobre J3: 0.52 (edición 1995) o 0.40 (PRE 2023) | [V1 + recalculado]. Mi cálculo da 0.363 para J1/J2 y tan30/tan55 = 0.404 para J3, que coincide con 2023. **Usa 0.40.** Los pesos de las cuñas (13 / 3.7 / 43 t) dependen de una sección en arco que solo está dibujada: no es una prueba completa |
| VO-1 | RocTopple Verification, problema 1 (Goodman y Bray 1976, ej. 1, 16 bloques). [PDF](https://static.rocscience.cloud/assets/verification-and-theory/RocTopple/RocTopple-Verification-Manual.pdf) y [paper escaneado](https://static.rocscience.cloud/assets/verification-and-theory/RocTopple/Toppling-of-Rock-Slopes-Goodman-Bray-1976.pdf) | Volteo de bloques (equilibrio límite) | φ = 38.15° (1a), 33.02° (1b), 38.66° (1c y 1d); fuerza en el pie de 0.5 o 2 013 kN; γ = 25 kN/m³ | Goodman y Bray: 1a = 1.0, 1b = 1.0, 1c = 1.02, 1d = 1.23 | [V1]. La geometría de los bloques está en la figura del paper escaneado |
| **Cinemática** | Dips y Maptek (teoría) | Markland: planar, cuña, volteo flexural y directo | — | — | [V1] los criterios (ventana de afloramiento o *daylight*, cono de fricción, *slip limit* = talud − φ, límites laterales a elección del usuario). **No encontré ningún ejemplo publicado y abierto con los polos completos y el conteo de casos críticos.** Haz pruebas sintéticas: un polo dentro o fuera de cada zona, y conteos contra un conjunto generado |

### A.4 Equilibrio límite 2D (Bishop, Janbu, Spencer, Morgenstern-Price/GLE, Sarma)

Fuente principal: **Slide2 Slope Stability Verification Manual** (Rocscience, 2022, 361 páginas, 111 ejemplos). [PDF](https://static.rocscience.cloud/assets/verification-and-theory/Slide2/Slide_SlopeStabilityVerification.pdf) e [índice por archivo](https://static.rocscience.cloud/assets/verification-and-theory/Slide2/Slide_SlopeStabilityVerification_Index_by_File.pdf). Todo lo de esta tabla es [V1]. La geometría suele venir en figura con coordenadas legibles. En civil hay muchos más casos (refuerzos, presas); aquí van los útiles para una v1 minera.

| # Slide | Origen | Materiales | FoS publicado (referencia) |
|---|---|---|---|
| 1 | ACADS 1(a), Giam y Donald (1989) | Homogéneo; c = 3 kPa, φ = 19.6°, γ = 20 | Referencia 1.00. Slide: Bishop 0.987, Spencer 0.986, GLE 0.986, Janbu corregido 0.990 |
| 2 | ACADS 1(b) | c = 32, φ = 10, γ = 20; grieta de tracción con agua | Referencia 1.65. Slide: Bishop 1.596, Spencer y GLE 1.592 |
| 3 | ACADS 1(c) | Tres suelos: 0/38, 5.3/23 y 7.2/20; γ = 19.5 | El manual dice referencia «1.65», pero Slide da 1.374–1.405 y la media de la encuesta es 1.381–1.406: **el 1.65 parece una errata**; otras fuentes citan 1.39 [NV] |
| 4 | ACADS 1(d), sísmico | Igual que el 3 | Referencia 1.00 |
| 5 y 6 | ACADS 2(a) y 2(b), presa de enrocado | — | Referencia 1.95 y 2.29 |
| 7 y 8 | ACADS 3(a) y 3(b), capa débil, no circular | 28.5/20 y 0/10; γ = 18.84 | Referencia 1.24–1.27 y 1.34 |
| 9 | ACADS 4, nivel freático y carga | — | Referencia 0.78 |
| 10 | ACADS 5, agua | c = 11, φ = 28, γ = 20 | Referencia 1.53 |
| 14 a 16 | Arai y Tagyo (1985), ejemplos 1 a 3 | — | Bishop 1.451 (Janbu 1.265); 0.417; 1.138 (Janbu 0.995) |
| 18 | Spencer (1969), vía Baker (1980) | ru | Spencer 1.02 |
| 21 | **Fredlund y Krahn (1977)**, unidades imperiales | c = 600 psf, φ = 20°, γ = 120 pcf; círculo xc = 120, yc = 90, R = 80 | Seco: Ordinario 1.928, Bishop 2.080, Spencer 2.073, M-P 2.076. ru = 0.25: 1.607, 1.766, 1.761, 1.764. Nivel freático: 1.693, 1.834, 1.830, 1.832 |
| 22 | Fredlund y Krahn (1977), capa débil | — | La capa débil está en posiciones distintas según el autor: tolerancia amplia |
| 23 y 24 | Low (1989), no drenado | — | Ordinario 1.36 y Bishop 1.14; 1.44 y 1.44 |
| 25 y 26 | Prandtl, capacidad portante | φ = 0, sin peso | FS teórico = 1.0 (qc = (2 + π)·c). Es una **prueba analítica exacta** |
| 28 a 36 | Chowdhury y Xu (1995); El-Ramly et al. (2003); Wolff y Harr (1987); Li y Lumb (1987) | Probabilístico | PoF e índice de confiabilidad publicados (ver el PDF) |

**Sarma.** El [manual Sarma de Slide2](https://static.rocscience.cloud/assets/verification-and-theory/Slide2/Slide_SlopeStabilityVerification_Sarma.pdf) [V1] trae 9 problemas; cuatro sirven para minería:

- Problema 4: pila de desmonte sobre piso cizallado (Coulthard 1979; Hoek 1987). Desmonte c = 100 kPa, φ = 42°, γ = 15.7; piso c = 10 kPa, φ = 6°. Referencia 1.2 seco y 0.48 saturado; Slide da 1.198 y 0.434.
- Problema 5: tajo de carbón con manto de carbón bajo toba (Hoek 1987, 9 cuñas). Referencia 1.17; Slide 1.091.
- Problema 6: enrocado semisumergido. Referencia 1.91; Slide 2.164.
- Problema 3: botadero de Bowen Basin.

Los problemas 5 y 6 discrepan entre 7 % y 13 %: no los uses como prueba estricta. Úsalos para comparar con un rango.

**Probabilístico «a mano».** Hoek, PRE 2023, cap. 9, Sau Mau Ping [V1]. [PDF](https://static.rocscience.cloud/assets/resources/learning/hoek/9.-Factor-of-safety-and-probability-of-failure_2023-06-30-120706_oohd.pdf)

- Datos fijos: H = 60 m, ψf = 50°, ψp = 35°, γr = 2.6 t/m³, γw = 1.0 t/m³.
- Variables aleatorias:
  - φ: normal 35 ± 5°, truncada entre 15° y 70°.
  - c: normal 10 ± 2 t/m², truncada entre 0 y 25.
  - z: normal 14 ± 3 m, truncada entre 0.1 y 24.75 m.
  - b: 15.3 ± 4 m.
  - zw: exponencial truncada, media z/2, entre 0 y z.
  - α: exponencial truncada, media 0.08, entre 0 y 2α.
- Simulación: 5 000 iteraciones con hipercubo latino.
- Resultado: FS medio = 1.34, desviación estándar = 0.23, mínimo 0.61, máximo 2.33, **PoF = 6.4 %**.

Las fórmulas del FS están en PL-1 y PL-2.

**Equilibrio límite con Hoek-Brown.** Ver HB-8 (Carranza-Torres y Hormazábal 2020, FS = 2.01).

### A.5 Caída de rocas

El [RocFall2 Verification Manual (lump mass)](https://static.rocscience.cloud/assets/verification-and-theory/RocFall/RocFall2-Verification-Manual-Lump-Mass.pdf) trae cinco problemas con solución analítica: proyectil, deslizamiento, probabilidad, envolventes e impacto. También compara con CRSP. [V1] el índice y la existencia de las soluciones analíticas; no transcribí los números. Con eso basta para probar una cinemática *lump mass* (parábola, coeficientes de restitución Rn y Rt).

### A.6 Tesis

Encontré tesis peruanas y de la región que usan Dips, RocData, RocPlane, Unwedge, Phase2 y Slide. **No pude abrir ninguna**: los repositorios DSpace (UNI, Continental, CORE) no devuelven el PDF a un cliente automático. Son candidatas [NV]; habría que revisar a mano si publican la entrada completa:

- Cortez y Cotrina (2022), galería de la mina Atahualpa: RMR, Q, GSI, Dips, Phase2 y Unwedge.
- Palacios Quispe (2020), Universidad Continental: RMR14 y Unwedge 3.0.
- Mercado y Obregón (2017), PUCP: Dips, Unwedge, Phase2, GSI y Q.
- Valencia Chiroque (UNI): botaderos con Slide.
- Castro Chunga (UNI, 2025): tajo con alteración hidrotermal, cinemática y equilibrio límite.
- Tesis del tajo Seductora: Dips, RocPlane, RocData y Slide.
- Pozo García, PUCP: GSI escalado para taludes de tajo (acceso restringido).
- Obregon Mitma (2020), McGill: diseño probabilístico de bancos; dio origen a Obregon y Mitri (2019).

Ojo con las tesis como oráculo: casi nunca publican la geometría completa ni el archivo del modelo. En la práctica sirven como comparación de orden de magnitud, no como prueba automática.

### A.7 Conteo de casos con datos completos y resultado publicado

| Método | Casos utilizables | Comentario |
|---|---|---|
| Hoek-Brown (mb, s, a, c′, φ′, ajuste triaxial) | **7** (HB-1 a HB-7) | HB-1 y HB-2 con γ supuesta |
| Equilibrio límite con Hoek-Brown | **6** (5 casos similares + s = 0) | HB-8 |
| RQD, GSI, RMR14, MRMR, Q-slope, SMR, Mathews | **0** ejemplos resueltos verificados | Hay ecuaciones (V1 o V2): las pruebas tienen que ser de fórmula. Para SMR, SMRTool sirve de oráculo |
| RMR89 | **1** | Hoek (RMR = 59) |
| Q (1974/2015) | **1** | Hoek (Q = 4.5); Q 2025 sin ejemplo |
| Falla planar | **5** | PL-1 a PL-5 |
| Cuña de talud | **6** | CU-1 a CU-6 |
| Cuña subterránea (tipo Unwedge) | **2** | Solo el FS de las cuñas laterales |
| Volteo | **4** (+1 de Alejano y Alonso 2005) | Goodman y Bray, ej. 1 |
| Cinemática con estereograma | **0** | Pruebas sintéticas |
| Equilibrio límite circular y no circular (Bishop, Janbu, Spencer, M-P/GLE) | **≈ 20** | Slide 1–10, 14–18, 21, 23–26 |
| Sarma | **9** (4 fiables) | — |
| Probabilístico | **≈ 10** | Hoek Sau Mau Ping + Slide 28–36 |
| Caída de rocas | **5** analíticos | RocFall |

---

## B) Geotecnia de tajo abierto

### B.1 Escalas de diseño y método dominante en cada una

| Escala | Qué controla la estabilidad | Métodos de la práctica | ¿v1 de librería? |
|---|---|---|---|
| **Banco** (cara + berma) | Estructuras a escala de banco: cuñas, planos y volteo | Cinemática de Markland sobre estereograma; cuñas y planos con FS determinístico y probabilístico; análisis de rotura posterior del banco (*backbreak*) con distribuciones de orientación, longitud y espaciado (Call y Savely 1990; Ryan y Pryor 2000 [V1]); cuñas uniformemente distribuidas para elegir el ángulo de cara del banco (BFA) (Langford, Corkum y Curran 2014, DFNE [V1]); Q-slope para el BFA (Bar y Barton 2017 [V2]) | **Sí**: cinemática, cuña y plano analíticos, y Monte Carlo |
| **Berma de seguridad** | Contención de caída de rocas | Ritchie modificado: **ancho mínimo (m) = 0.2·H + 4.5** (Call 1992, reproducido por Ryan y Pryor 2000, ec. 3.1 [V1]; la figura del mismo capítulo dice 4.6 + 0.2H). En pies: 0.2H + 15 [V2]. Confiabilidad de la berma = % de bermas con ancho ≥ el criterio; se diseña al 50–90 % según el caso [V1]. Además, simulación *lump mass* | **Sí** (fórmula y estadística del ancho remanente) |
| **Interrampa** | Estructuras mayores (fallas, contactos), escalonadas, y el macizo | Cinemática de estructuras mayores; cuña y plano grandes; equilibrio límite no circular sobre el macizo + estructura | Sí: equilibrio límite 2D no circular + cuña 3D analítica. **No**: escalonado o DFN |
| **Talud global** | Resistencia del macizo (Hoek-Brown con D), agua, anisotropía | Equilibrio límite 2D (Bishop, Spencer, M-P/GLE) con Hoek-Brown no lineal o c′/φ′ equivalentes (Hoek 2002: D = 1 en tajos grandes [V1]); ábacos adimensionales (Carranza-Torres y Hormazábal 2020 [V1]); análisis por reducción de resistencia (SSR) con FEM o FDM para validar mecanismos | Equilibrio límite 2D: **sí**. SSR, FEM o FDM: **fuera de v1** |
| **Botaderos** | Desmonte granular, base débil, agua, sismo; además, *runout* | Equilibrio límite circular y no circular; dos cuñas o Sarma sobre una base inclinada débil (ver Sarma 4, Hoek 1987 [V1]); sistema de clasificación de estabilidad y peligro del botadero (WSRHC) de Hawley y Cunning (2017) [V2] con criterios propios (§8.3.2; los valores son [NV]); pseudoestático | Sí: equilibrio límite + Sarma + pseudoestático. *Runout*: fuera |
| **Pads de lixiviación** | **Interfaz** geomembrana–suelo (la superficie más débil), presión de solución, sismo | Equilibrio límite **traslacional** de bloque o cuña sobre la interfaz (Janbu, Spencer, GLE no circular); análisis de sensibilidad de la resistencia de interfaz; Newmark si el pseudoestático no cumple. Nevada (NDEP 2021) [V1]: **FS ≥ 1.30 estático y ≥ 1.05 pseudoestático**, con PGA del 10 % en 50 años; se puede reducir la PGA hasta 50 % si se justifica y se acompaña de un análisis de deformaciones | Sí: equilibrio límite no circular + Newmark analítico (bloque rígido). Deformación FEM: fuera |
| **Retroanálisis** | — | FS = 1 → curva c–φ movilizada (Hoek, Sau Mau Ping [V1]); calibración de GSI o D contra fallas observadas | **Sí** (raíz de FS(c, φ) = 1) |

### B.2 Criterios de aceptación

- **Read y Stacey (2009), cap. 9 (Wesseloo y Read): matriz FoS–PoF** por escala y consecuencia [V2 para la estructura]. Los valores típicos que circulan son estos [**NV**: coinciden con el extracto de Obregon y Mitri (2019) que mostró el buscador, pero no los vi en el libro; verifícalos antes de codificarlos]:

  | Escala | Consecuencia | FS mín. estático | FS mín. dinámico | PoF máx. |
  |---|---|---|---|---|
  | Banco | Baja a alta | 1.1 | NA | 25–50 % |
  | Interrampa | Baja | 1.15–1.2 | 1.0 | 25 % |
  | Interrampa | Moderada | 1.2 | 1.0 | 20 % |
  | Interrampa | Alta | 1.2–1.3 | 1.1 | 10 % |
  | Global | Baja | 1.2–1.3 | 1.0 | 15–20 % |
  | Global | Moderada | 1.3 | 1.05 | 5–10 % |
  | Global | Alta | 1.3–1.5 | 1.1 | ≤ 5 % |

- **Críticas y actualización.** Los pares FS–PoF de 2009 no son coherentes estadísticamente (Velarde y Macciotta 2023 [V1]). Por eso se propusieron criterios basados en confiabilidad (RBDAC, Macciotta, Creighton y Martin 2020, CIM Journal [V2]), que agregan el coeficiente de variación del FS (COV_FS). Un ejemplo publicado usa «FS mín. 1.2 y PoF máx. 10 %» para un talud de consecuencia económica según el RBDAC 2020 [V1, Velarde].
- **Implementación sugerida.** Guarda los criterios como **datos versionados**, no como código, con la cita de cada valor. El usuario elige la tabla (Read y Stacey 2009, RBDAC 2020, NDEP, la normativa local). En Perú no encontré la guía del MINEM con valores verificados [NV].

### B.3 Qué entra en la v1 y qué queda fuera

**Entra en la v1 (analítico o equilibrio límite 2D, sin malla):**

1. Clasificaciones: RQD, RMR89, Q (con `edicion`), GSI cuantificado (ecuaciones 2013), SMR (discreto y continuo), Q-slope, Mathews (N′, S, probabilidad logit), MRMR (estructura).
2. Hoek-Brown 2002 y 2018: mb, s, a, σcm, σt, Erm (2002 y Hoek-Diederichs 2006), c′/φ′ equivalentes con σ′3max para túnel y talud, ajuste triaxial.
3. Estereografía: proyección de igual ángulo y de igual área, densidad de polos, sets (Fisher), cinemática de Markland (planar, cuña, volteo flexural y directo).
4. Plano (Hoek y Bray, con grieta, agua, sismo y perno), cuña tetraédrica (Hoek y Bray / Priest, con agua, cohesión, cargas externas y sismo), volteo de bloques (Goodman y Bray).
5. Equilibrio límite 2D: Ordinario, Bishop, Janbu simplificado y corregido, Spencer, Morgenstern-Price/GLE y Sarma, con búsqueda circular (grilla) y no circular (bloque o trayectoria + optimización), Mohr-Coulomb, Hoek-Brown no lineal, ru, nivel freático, grieta de tracción, pseudoestático.
6. Probabilístico: Monte Carlo e hipercubo latino sobre cualquiera de los anteriores, PoF, índice de confiabilidad; sensibilidad.
7. Diseño banco–berma: Ritchie modificado, confiabilidad de la berma y del *backbreak*, ángulo interrampa desde la geometría del banco.
8. Retroanálisis (FS = 1) y Newmark de bloque rígido para pads y botaderos.
9. Caída de rocas *lump mass* 2D (opcional en v1).

**Queda fuera de la v1 (necesita FEM, FDM, DEM o 3D):**

- SSR (Phase2/RS2, FLAC), deformaciones, plasticidad, zonas de plastificación alrededor de excavaciones.
- Cuñas subterráneas con esfuerzos *in situ* (el *clamping* que muestra Unwedge cambia el FS de 0 a 1.23 en el ejemplo de Hoek) y la geometría 3D de excavaciones con arco. La cuña de techo y pared sin esfuerzos puede ser v1.5.
- Equilibrio límite 3D (Slide3), rocas en 3D, DFN y fallas escalonadas (*step-path*), volteo flexural por FEM o DEM, filtraciones por FEM (en v1 basta con línea piezométrica, ru o Hu).
- Respuesta sísmica dinámica, análisis de deformación de pads y botaderos, *runout* de botaderos.

---

## C) Ábacos clásicos: ¿hay ecuaciones o versiones abiertas?

| Ábaco | ¿Hay ecuación publicada? | ¿Versión abierta? | Cómo trazarlo sin copiar la figura |
|---|---|---|---|
| **Carta GSI** (Hoek y Marinos) | Sí, para la versión cuantificada: GSI = 1.5·JCond89 + RQD/2 (o con Jr/Ja) (Hoek et al. 2013 [V1]). Las isolíneas son rectas en ejes JCond89–RQD | No encontré una digitalización con licencia abierta [NV] | Traza la carta cuantificada desde la ecuación. La carta descriptiva es una figura con copyright: reemplázala por tu propia tabla de descriptores con la cita |
| **Soporte del Q** (Grimstad y Barton 1993; NGI 2015/2025) | Parcial: longitud de perno y luz máxima (ver A.2). Los límites de las clases 1 a 9 **no tienen ecuación oficial** [NV] | El ábaco de NGI tiene copyright (NGI es el editor) | Digitaliza tú los vértices de los límites como datos (son hechos), cítalos y documenta el error de digitalización; o pide permiso a NGI. Avisa del cambio de E500 a E700 de 2025 |
| **Mathews / Potvin** | Sí: el modelo logit z = a + b1·ln S + b2·ln N (Mawdesley et al. 2001 [V1]); coeficientes en Mortazavi y Osserbay (2021, preprint [V1]) | El preprint de Research Square suele llevar CC BY 4.0 [NV] | Traza las isolíneas de probabilidad desde la ecuación |
| **Laubscher** (MRMR vs radio hidráulico) | No encontré una ecuación oficial de los límites [NV] | No | Digitalización propia, rotulada como aproximada |
| **Bieniawski** (tiempo de autosoporte vs luz) | No hay ecuación oficial [NV] | No | Digitalización propia; marcar como «indicativo» |
| **Red estereográfica** | Sí: igual ángulo r = R·tan((90° − inmersión)/2); igual área r = R·√2·sin((90° − inmersión)/2) (matemática de dominio público) | **mplstereonet**, licencia MIT [V1]; RockSlope (PyPI, MIT, v0.1.1, joven) [V1] | Implementación propia o mplstereonet como dependencia opcional |
| **Ritchie** | El original de 1963 es un ábaco de cuneta vial; la versión minera es una ecuación: W = 0.2H + 4.5 m [V1] | — | Ecuación |
| **Ábacos de cuña de Hoek y Bray** (A y B) | Sí: fórmulas cerradas de A y B (recalculadas en CU-1) | — | Ecuación |
| **Ábacos HB–Bishop de Carranza-Torres** | Ecuaciones de regresión y un libro Excel del autor (2020 [V1]) | El preprint es del autor, con licencia [NV] | Reproducir las ecuaciones con la cita |

---

## D) Erratas y trampas detectadas en las fuentes (importa para las pruebas)

1. Hoek, PRE «Rock mass classification»: Q con RQD = 50 publicado como 2.9; la fórmula da 2.5.
2. Slide2, problema 3 (ACADS 1c): referencia impresa 1.65; los resultados apuntan a ≈ 1.39.
3. RocPlane, problema 1, caso con grieta: intermedios mal impresos (zw, U, c); el FS final (1.0655) sí es correcto.
4. Hoek, PRE «Rock mass properties», Yacambú: mb = 0.481 no corresponde a mi = 10 y GSI = 25 (da 0.687).
5. Cuña lateral sobre J3 del ejemplo de túnel de Hoek: 0.52 (1995) frente a 0.40 (2023). El cálculo analítico da 0.404.
6. Ritchie modificado: 4.5 m en la ecuación y 4.6 m en la figura del mismo capítulo (Ryan y Pryor 2000).
7. Hoek (2002), ejemplo de c′/φ′: no publica γ. Con 0.027 MN/m³ se reproduce exacto.
8. Sarma de Slide2, problemas 5 y 6: discrepancias de 7 % y 13 % frente a la referencia de Hoek (1987).
9. SMRTool es GPL-2.0: úsalo como oráculo, no como fuente de código.

---

## Bibliografía (APA 7)

- Bar, N., & Barton, N. (2017). The Q-slope method for rock slope engineering. *Rock Mechanics and Rock Engineering, 50*, 3307–3322. https://doi.org/10.1007/s00603-017-1305-0 [V2]
- Barton, N., Lien, R., & Lunde, J. (1974). Engineering classification of rock masses for the design of tunnel support. *Rock Mechanics, 6*, 189–236. https://doi.org/10.1007/BF01239496 [V2]
- Bieniawski, Z. T. (1989). *Engineering rock mass classifications*. Wiley. [V2]
- Bishop, A. W. (1955). The use of the slip circle in the stability analysis of slopes. *Géotechnique, 5*(1), 7–17. https://doi.org/10.1680/geot.1955.5.1.7 [V2]
- Carranza-Torres, C., & Hormazábal, E. (2020). Computational tools for the estimation of factor of safety and location of the critical failure surface for slopes in rock masses that satisfy the Hoek-Brown failure criterion. En *Slope Stability 2020*. Perth, Australia (preprint de los autores). [V1]
- Celada, B., Tardáguila, I., Varona, P., Rodríguez, A., & Bieniawski, Z. T. (2014). Innovating tunnel design by an improved experience-based RMR system. En *World Tunnel Congress 2014*. Foz do Iguaçu: ITA. [V2]
- Fredlund, D. G., & Krahn, J. (1977). Comparison of slope stability methods of analysis. *Canadian Geotechnical Journal, 14*(3), 429–439. https://doi.org/10.1139/t77-045 [V2]
- Giam, P. S. K., & Donald, I. B. (1989). *Example problems for testing soil slope stability programs* (Civil Engineering Research Report No. 8/1989). Monash University. [NV: título y número citados según los manuales de Rocscience]
- Goodman, R. E., & Bray, J. W. (1976). Toppling of rock slopes. En *Rock Engineering for Foundations and Slopes* (pp. 201–234). ASCE. [V1]
- Hawley, M., & Cunning, J. (Eds.). (2017). *Guidelines for mine waste dump and stockpile design*. CSIRO Publishing. https://doi.org/10.1071/9781486303519 [V2]
- Hoek, E. (1974). *The design of rock slopes and foundations* (apuntes). Rocscience, Hoek's Corner. [V1]
- Hoek, E. (2007/2023). *Practical rock engineering* (apuntes en línea; capítulos «Rock mass classification», «Rock mass properties», «Structurally controlled instability in tunnels», «Factor of safety and probability of failure», «A slope stability problem in Hong Kong»). Rocscience. [V1]
- Hoek, E., & Brown, E. T. (2019). The Hoek–Brown failure criterion and GSI – 2018 edition. *Journal of Rock Mechanics and Geotechnical Engineering, 11*(3), 445–463. https://doi.org/10.1016/j.jrmge.2018.08.001 [V2]
- Hoek, E., Carranza-Torres, C., & Corkum, B. (2002). Hoek-Brown failure criterion – 2002 edition. En *Proceedings of NARMS-TAC 2002* (pp. 267–273). Toronto. [V1]
- Hoek, E., Carter, T. G., & Diederichs, M. S. (2013). Quantification of the Geological Strength Index chart (ARMA 13-672). *47th US Rock Mechanics/Geomechanics Symposium*. San Francisco. [V1]
- Hoek, E., & Diederichs, M. S. (2006). Empirical estimation of rock mass modulus. *International Journal of Rock Mechanics and Mining Sciences, 43*(2), 203–215. https://doi.org/10.1016/j.ijrmms.2005.06.005 [V2]
- Hoek, E., Kaiser, P. K., & Bawden, W. F. (1995). *Support of underground excavations in hard rock* (cap. 5). Balkema. [V1: copia académica del capítulo]
- Kumsar, H., Aydan, Ö., & Ulusay, R. (2000). Dynamic and static stability assessment of rock slopes against wedge failures. *Rock Mechanics and Rock Engineering, 33*(1), 31–51. [V2: citado en el manual de SWedge]
- Langford, J. C., Corkum, B., & Curran, J. H. (2014). Preliminary selection of optimum bench face angle using uniformly distributed wedges. En *DFNE 2014*. Vancouver. [V1]
- Laubscher, D. H. (1990). A geomechanics classification system for the rating of rock mass in mine design. *Journal of the South African Institute of Mining and Metallurgy, 90*(10), 257–273. [NV: volumen y páginas]
- Laubscher, D. H., & Jakubec, J. (2001). The MRMR rock mass classification for jointed rock masses. En W. A. Hustrulid & R. L. Bullock (Eds.), *Underground mining methods* (pp. 475–481). SME. [NV: páginas]
- Macciotta, R., Creighton, A., & Martin, C. D. (2020). Design acceptance criteria for operating open-pit slopes: An update. *CIM Journal, 11*(4), 248–265. https://doi.org/10.1080/19236026.2020.1826830 [V2]
- Mawdesley, C., Trueman, R., & Whiten, W. J. (2001). Extending the Mathews stability graph for open-stope design. *Mining Technology, 110*(1), 27–39. https://doi.org/10.1179/mnt.2001.110.1.27 [V2]
- Montoya-Araque, E. A., & Suarez-Burgoa, L. O. (2018). pyBIMstab: Application software for 2D slope stability analysis of block-in-matrix and homogeneous materials. *SoftwareX, 7*, 383–387. https://doi.org/10.1016/j.softx.2018.11.003 [V2]
- Morgenstern, N. R., & Price, V. E. (1965). The analysis of the stability of general slip surfaces. *Géotechnique, 15*(1), 79–93. https://doi.org/10.1680/geot.1965.15.1.79 [V2]
- Mortazavi, A., & Osserbay, B. (2021). *The consolidated Mathews stability graph for open stope design* [Preprint]. Research Square. https://doi.org/10.21203/rs.3.rs-191163/v1 [V1]
- Nevada Division of Environmental Protection, Bureau of Mining Regulation and Reclamation. (2021). *Stability requirements for heap leach pads*. [V1]
- NGI. (2025). *Using the Q-system: Rock mass classification and support design*. Norwegian Geotechnical Institute. [V1]
- Obregon, C., & Mitri, H. (2019). Probabilistic approach for open pit bench slope stability analysis – A mine case study. *International Journal of Mining Science and Technology, 29*(4), 629–640. https://doi.org/10.1016/j.ijmst.2019.06.017 [V2]
- Priest, S. D. (1993). *Discontinuity analysis for rock engineering*. Chapman & Hall. [V2]
- Read, J., & Stacey, P. (Eds.). (2009). *Guidelines for open pit slope design*. CSIRO Publishing. [V2]
- Riquelme, A. J., Tomás, R., & Abellán, A. (2016). Characterization of rock slopes through slope mass rating using 3D point clouds. *International Journal of Rock Mechanics and Mining Sciences, 84*, 165–176. https://doi.org/10.1016/j.ijrmms.2015.12.008 [V2]
- Rocscience. (2022). *Slide2 slope stability verification manual*; *Slide2 verification manual (Sarma)*; *RocPlane verification manual*; *SWedge verification manual*; *RocTopple verification manual*; *RocFall2 verification manual – Lump mass*. Rocscience Inc. [V1]
- Romana, M. (1985). New adjustment ratings for application of Bieniawski classification to slopes. En *Proceedings of the International Symposium on the Role of Rock Mechanics* (pp. 49–53). Zacatecas: ISRM. [NV]
- Ryan, T. M., & Pryor, P. R. (2000). Designing catch benches and interramp slopes. En W. A. Hustrulid, M. K. McCarter & D. J. A. Van Zyl (Eds.), *Slope stability in surface mining* (cap. 3). SME. [V1; páginas NV]
- Sarma, S. K. (1979). Stability analysis of embankments and slopes. *Journal of the Geotechnical Engineering Division (ASCE), 105*(GT12), 1511–1524. [NV]
- Spencer, E. (1967). A method of analysis of the stability of embankments assuming parallel inter-slice forces. *Géotechnique, 17*(1), 11–26. https://doi.org/10.1680/geot.1967.17.1.11 [V2]
- Tomás, R., Delgado, J., & Serón, J. B. (2007). Modification of slope mass rating (SMR) by continuous functions. *International Journal of Rock Mechanics and Mining Sciences, 44*(7), 1062–1069. https://doi.org/10.1016/j.ijrmms.2007.02.004 [V2]
- Velarde, G., & Macciotta, R. (2023). Probabilistic pit slope stability analysis targeting a reliability-based design acceptance criteria: a parametric study. En *SSIM 2023: Third International Slope Stability in Mining Conference*. Australian Centre for Geomechanics. https://papers.acg.uwa.edu.au/d/2335_08_Velarde/08_Velarde.pdf [V1]
