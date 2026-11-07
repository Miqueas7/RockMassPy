# Datos públicos para el módulo predictivo de RockMassPy

Fecha de búsqueda: 31-oct-2026. Solo datos públicos; no se tocó ninguna carpeta de clientes.

**Leyenda.** Verificación: **[V1]** abrí el dataset o su página de descarga · **[V2]** solo lo cita un artículo · **[NV]** no se pudo comprobar.
Tipo de dato (tu lista): T1 macizo + sostenimiento + desempeño por tramo · T2 estabilidad de tajeos / luces críticas · T3 pares de clasificaciones · T4 túneles TBM/P&V con clase y sostenimiento · T5 taludes de tajo.
Nivel del módulo: **N1** correlaciones · **N2** auditoría de práctica · **N3** desempeño/falla.
"Redistribuible": la licencia permite copiarlo dentro del repo o del paquete. Sin licencia declarada = **no** se redistribuye (solo uso interno de consulta, citando la fuente).

## Tabla resumen

| # | Dataset | Tipo | Nivel | Registros | Licencia | Descarga sin registro | Verif. | Copia local |
|---|---|---|---|---|---|---|---|---|
| 1 | Adoko et al. 2021, tajeos de Ghana (Tabla 11 del artículo) | T2 | N2, N3 | 225 | CC BY 4.0 | Sí (PDF) | [V1] | `adoko_2021_ghana_stopes/` |
| 2 | HWStability (Papaioanou y Suorineni 2016), Mendeley | T2 | N3, N2 | 226 | CC BY 4.0 (la declara quien lo subió) | Sí | [V1] | `hwstability_papaioanou_suorineni/` |
| 3 | Luz crítica UBC, anexo de García-Gonzalo et al. 2016 (MDPI Materials) | T2 | N3, N2 | 399 | CC BY 4.0 | Sí | [V1] | `critical_span_garcia_gonzalo_2016/` |
| 4 | Squeezing de túneles, Mombilia et al. 2025 (Data in Brief + Mendeley) | T1 parcial + T3 | N1, N3 | 135 túneles + 5 280 GRC calculadas | v1 CC BY 4.0 / v2 CC BY-NC 3.0 | Sí | [V1] | `squeezing_grc_mombilia/` |
| 5 | GSI–RMR_adj Alborz central (Shirdel 2025), Zenodo y Mendeley | T3 | N1 | 134 | CC BY 4.0 | Sí | [V1] | `gsi_rmr_shirdel_alborz/` |
| 6 | IOMSSI, taludes de tajo abierto (Ferentinou y Fakir 2018), Mendeley | T5 | N3 | 142 taludes, 42 minas | CC0 1.0 | Sí | [V1] | `iomssi_open_pit_ferentinou/` |
| 7 | Mathews de Dahongshan (Li et al. 2025, Frontiers), figshare | T2 | N3 | 216 (108 tajeos × 2 perfiles) | CC BY 4.0 | Sí | [V1] | `mathews_dahongshan_li_2025/` |
| 8 | ROCKMass/9/5876 (TC304, Ching et al. 2021) | T3 | N1 | 5 876 | **Sin licencia** | Sí, enlace directo | [V1] | no descargado |
| 9 | Base Mathews extendida (GitHub HuangBuddy) | T2 | N3 | 426 | **Sin licencia** | Sí | [V1] | solo consulta, fuera de `datos_publicos` |
| 10 | Sobreexcavación Khimti-2, Nepal (GitHub zexxr) | T1 parcial | N3 | 1 577 | MIT declarada pero sin archivo LICENSE ni fuente | Sí | [V1] | no descargado |
| 11 | Squeezing de 117 casos (GitHub zexxr) | T1 parcial | N3 | 117 | MIT (repo); datos tomados de la literatura | Sí | [V1] | solo consulta |
| 12 | Colapsos de túneles (TU Dortmund, Spyridis et al. 2023) | T1 (falla) | N3 | ~770 líneas | Solo acuerdo de depósito: **no redistribuible** | Sí | [V1] | solo consulta |
| 13 | Estallido de roca, 306 casos (Liu 2026), figshare | complementario | N3 | 306 | CC BY 4.0 | Sí | [V1] | `rockburst_306_liu/` |
| 14 | MWD de 15 túneles noruegos (Hansen 2024), Zenodo | T4 parcial | N1 | 4 CSV (~1,8 MB) | CC BY 4.0 | Sí | [V1] | no descargado (solo trae tipo de roca) |
| 15 | Pilares en roca dura (GitHub WangMeng0734) | complementario | N3 | n/d | **Sin licencia** | Sí | [V1] | no |
| 16 | Dryad CC0: orientaciones de juntas (Chen y Yin 2018) y PLS (Wen et al. 2019) | marginal | N1 | 397 / 193 | CC0 | Sí | [V1] | `dryad_*` (poco valor) |

Lo que **no** sirve o no se encontró está al final (Kaggle, Hugging Face, portales de gobierno, Q-slope, TBM con sostenimiento).

---

## 1. Ya conocidos: confirmación

### 1.1 Adoko et al. 2021, 225 casos — confirmado, con una precisión
- **Referencia:** Adoko, Saadaari, Mireku-Gyimah e Imashev, "A Feasibility Study on The Implementation of Neural Network Classifiers for Open Stope Design", *Geotechnical and Geological Engineering* 40(2):677–696 (en línea 6-jul-2021). DOI 10.1007/s10706-021-01915-8. [V1]
- **Licencia:** CC BY 4.0 (la de Crossref y la del texto del artículo). Ojo: la copia del repositorio de Nazarbayev University dice CC BY-NC-SA 3.0 US; manda la del editor, que es CC BY 4.0.
- **Dónde están los datos:** no hay archivo aparte. La declaración de datos dice "Appendix 1", que es la **Tabla 11** dentro del mismo PDF. Conté 225 filas: 102 estables, 85 inestables y 38 hundidos (*caved*), igual que el texto.
- **Columnas (Tabla 11):** Mine, Level, Orebody, Stope, Surface, Height, Span, Length, HR, Q', A, B, C, N', Status. Las minas son 3 de Ghana; una figura como "B", sin nombre.
- **Nivel:** N3 (clasificador estable/inestable/hundido) y N2 (comparar contra el gráfico de estabilidad). Revisado por pares.
- **Pendiente:** extraer la Tabla 11 a CSV con `pdftotext -layout` (copia del PDF en `datos_publicos/adoko_2021_ghana_stopes/`).

### 1.2 "Wang 2002, 292 casos en anexo" — no confirmado tal cual
- Los **292 casos** son de la base de **luces críticas de UBC** ampliada en el 2000 (Wang et al. 2000), no de una base Mathews. Lo dice Ouchi y Pakalnis (2004), cuya Tabla 2 se titula "Case history data sources (Wang et al. 2002)": es una tabla **de fuentes**, no de casos. [V2]
- No encontré un anexo público con los 292 casos. **Lo que sí está libre** es la base de luces críticas de UBC con **399 casos** en el anexo de García-Gonzalo et al. 2016 (ver §2.3, CC BY 4.0). Es mejor que buscar el Wang.

### 1.3 ROCKMass/9/5876 (TC304, Ching et al.) — **no** es "por contacto"
- **Referencia:** Ching, Phoon, Ho y Weng, "Quasi-site-specific prediction for deformation modulus of rock mass", *Canadian Geotechnical Journal* (2021). DOI 10.1139/cgj-2020-0168. Revisado por pares.
- **Enlace:** índice 304dB en `http://140.112.12.21/issmge/tc304.htm` → pestaña Database (`database_20100.htm`). El archivo se baja directo, sin registro: `http://140.112.12.21/issmge/Database/RM_9.xlsx` (HTTP 200, 280 836 bytes, xlsx, modificado el 14-sep-2020). Definición de las variables: `Database/DEF/Def_ROCKMass_9_5876.htm`. [V1]
- **Contenido declarado:** 9 parámetros: RQD, RMR, Q, GSI, Em, Eem, Edm, Ei, σci. 5 876 casos de 225 estudios en 67 países o regiones (17 % ígneas, 37 % sedimentarias, 26 % metamórficas, 20 % sin clase). Contacto: J. Ching.
- **Licencia:** **ninguna.** La página solo dice "we encourage the use of them". **No se redistribuye.** Por eso no lo bajé; sirve para calibrar correlaciones en uso interno, citando la fuente.
- **Nivel:** N1 (RMR–Q–GSI–Em). Es la base de correlaciones más grande que encontré.
- En la misma página están **ROCK/9/4069** (roca intacta, `Database/ROCK_9_4069_TC304/ROCK_9_4069_TC304.xlsx`, HTTP 200, 217 713 bytes) y **ROCK/10/4025** (roca intacta). Tampoco tienen licencia.

### 1.4 "Zenodo GSI–RMR, 134 casos" — confirmado, está en dos sitios
- **Zenodo:** "Field Dataset for GSI-RMR_adj Correlation in Central Alborz Rock Masses", B. Shirdel, 21-oct-2025, DOI 10.5281/zenodo.17397696, **CC BY 4.0**. [V1]
- **Mendeley (los mismos archivos):** DOI 10.17632/8z54mc65j3.1, CC BY 4.0, asociado a un manuscrito enviado a *Rock Mech. Rock Eng.* **Calidad:** todavía no revisado por pares; el registro de Zenodo enlaza a un arXiv (2401.12345) que no verifiqué.
- **Archivos descargados** (`gsi_rmr_shirdel_alborz/`):
  - `Data Base-14040720-REV02.xlsx`: 1 hoja, 136 filas × 50 columnas. Proyecto (2 minas de bauxita y 1 de caliza en Irán), Zone/Station, Elevation, Geological Unit (Shemshak 80, Elika 28, Lar 26), Lithology, RQD %, Joint Spacing (cm), Persistence, Fill Width, Roughness, Fill Strength, Weathering y Groundwater (todo DRY) como texto. Además, los puntajes parciales del RMR y del cuadro cuantificado del GSI (2013), el RMR y el GSI.
  - `Book2.xlsx`: 140 filas × 6 columnas (RMRa, GSI 2013 final, GSI_model, Delta, |Delta|, Delta²).
  - `ELIKA.xlsx`, `LAR.xlsx` (29 filas × 50 columnas), `SHEMSHAK.xlsx`: las mismas columnas, separadas por formación. `RMR to GSI.xlsx` (3,2 MB): 1 hoja de cálculo.
- **Nivel:** N1. Ojo: tiene poca variedad (todo seco y casi todo con meteorización "Slight").

---

## 2. Hallazgos nuevos, por tipo

### 2.1 HWStability, Papaioanou y Suorineni 2016 (T2) — de los mejores
- **Enlace:** https://data.mendeley.com/datasets/999nngmxb4 (v1, 2-mar-2021). Lo subieron S. Bozkurt Keser y G. Erdoğan Erten para su artículo de predicción. **CC BY 4.0.** [V1]
- **Origen:** la base de Papaioanou y Suorineni (2016), "Development of a generalised dilution-based stability graph for open stope design", *Mining Technology*, DOI 10.1080/14749009.2015.1131940. Ese artículo es de pago y la base la redistribuyó un tercero: **cita a los dos** y toma la CC BY con esa reserva.
- **Estructura** (`raw data.xlsx`, hoja "Manuscript"): 226 casos de 6 minas australianas (los nombres de las minas son públicos). Las 81 columnas declaradas son en la práctica 14 útiles: No., Mine Name, Stope #, Stope Surface (HW 76, SW 69, FW 41, Crown 40), Strike Length L (m), Exposed Height H (m), Ore Width (m), HR (m), **ELOS actual (m)**, N', Depth of excavation, **Dilution %**, clase de dilución (<5 % 122 · 5–10 % 57 · 10–15 % 24 · 15–20 % 10 · >20 % 13) y **stable/unstable** (122/104).
- **Nivel:** N3. Es el único con **sobreexcavación medida (ELOS)** por cara de tajeo; también sirve para N2. Revisado por pares (el artículo original).

### 2.2 Mathews de Dahongshan, Li, Qiao y Yang 2025 (T2)
- **Enlace:** figshare 10.3389/feart.2025.1610234.s001 (archivo `Table 1_….xlsx`, 22 kB). Artículo: *Frontiers in Earth Science*, DOI 10.3389/feart.2025.1610234. **CC BY 4.0.** [V1]
- **Estructura:** 216 filas × 6 columnas: No., Stope, N, HR, **Average Collapse Height (m)** y Note (sección este u oeste; perfil según buzamiento o según rumbo). Son 108 tajeos de una mina china de cobre, a 800–1 000 m de profundidad.
- **Nivel:** N3 (altura de colapso medida con escaneo, es decir, desempeño continuo y no binario). Revisado por pares.

### 2.3 Luz crítica de UBC, anexo de García-Gonzalo et al. 2016 (T2)
- **Artículo:** "Hard-Rock Stability Analysis for Span Design in Entry-Type Excavations with Learning Classifiers", *Materials* 9(7):531, DOI 10.3390/ma9070531. **CC BY 4.0.** [V1]
- **Archivo:** `materials-09-00531-s001.xlsx` (se bajó con `europepmc.org/…/PMC5456900/supplementaryFiles`).
- **Estructura:** 399 filas × 4 columnas: Number, RMR (%), Span (m) (tipo mixto: hay que limpiarlo) y Stability (1 estable 240 · 2 potencialmente inestable 103 · 3 inestable 56).
- **Nivel:** N3 y N2, para la luz crítica de Lang y Pakalnis. Es la base de UBC (Lang 1994 más ampliaciones). No trae sostenimiento.
- **Relacionados sin datos tabulados:** la tesis de Lang (1994, UBC, 172 casos de Detour Lake), en `circle.ubc.ca/handle/2429/5578`, con licencia no comercial [V2]. También Ouchi, Pakalnis y Brady (NIOSH 2004 y ARMA 08-376 de 2008), con más de 450 puntos en roca débil (RMR76 < 50) **separados por tipo de sostenimiento**. Están en dominio público, pero los datos vienen **solo en gráficos** [V1]: `stacks.cdc.gov/view/cdc/221136` y `/226973`.

### 2.4 Base Mathews extendida (T2) — sin licencia
- **Enlace:** https://github.com/HuangBuddy/Enhancing-Open-Stope-Stability-Prediction (`Dataset.csv`, 38 kB) y otro repo del mismo autor con 466 filas (HR, N, Stability). **Sin licencia** (GitHub: none). [V1]
- **Estructura:** 426 filas × 12 columnas: Q, Jn, Ja, A, B, C, HR, N, Stability (0/1: 285/141), Location y Source. Hay 92 fuentes; las principales son el informe BART P447 de Trueman et al. (1997, 198 casos), datos de BHP/Coffey (71), Mathews et al. 1980 (17), Itasca (14) y la tesis de Nickson (10). Es, en la práctica, la base "Extended Mathews" de Mawdesley y Trueman.
- **Nivel:** N3. **Uso:** solo consulta interna; la copia está en `papers/_sin_licencia_solo_consulta/`, fuera de `datos_publicos`. La base original (Mawdesley et al. 2001, *Mining Technology*) no es pública [V2].

### 2.5 Squeezing de túneles, Mombilia et al. 2025 (T1 parcial + T3)
- **Artículo:** "Analytical dataset to determine squeezing potential of deep tunnels", *Data in Brief* 61:111808, DOI 10.1016/j.dib.2025.111808 (PMC12269506). **Datos:** Mendeley DOI 10.17632/w3yhkp6zxn. [V1]
- **Licencia:** la **v1 es CC BY 4.0**, pero la **v2 (la vigente) es CC BY-NC 3.0**. El archivo que bajé es el de la v2, así que para uso comercial cita la v1 o verifica que el archivo sea idéntico.
- **Estructura** (`Dataset GRC.xlsx`, 4 hojas):
  - `Data Strain Literature`: 135 túneles × 22 columnas útiles: Name of Tunnel, References, Location, Rock Type, **Q, RMR, mi, GSI** (unos 123 no nulos), γ, radio a, H, UCS, Qc, σcm, po, **deformación del túnel ε (%)**, Erm, Ei, σcm/po y **Category** (sin squeezing 64 · menor 14 · severo 26 · muy severo 18 · extremo 13). Las fuentes son Dwivedi 2013 (62), Singh 2006 (26), Sharma 2019 (18), Dehkordi 2011 (10), Mhanna 2024 (9), Hoek 2001 (7) y Barla 1999 (3).
  - `GRC Calculation`: 5 280 filas sintéticas (GSI, H, a, pi/po, Rp, ur, ε, σcm/po).
  - `pi_po` y `Linear Regression`: tablas auxiliares.
- **Nivel:** N1 (unos 120 tríos Q–RMR–GSI de túneles reales) y N3 (convergencia y clase de squeezing). No trae el sostenimiento instalado. Revisado por pares (*Data in Brief*).
- **Parecido:** el GitHub `zexxr/Tunnel-Squeezing-Classification` (MIT) trae 117 casos con D, H, Q, K, ε y clase (1:33, 2:24, 3:60), compilados de la literatura sin fuente precisa. Se solapa con Dwivedi. [V1]

### 2.6 Sobreexcavación Khimti-2, Nepal (T1 parcial) — muy útil, pero sin licencia válida
- **Enlace:** https://github.com/zexxr/-Tunnel-Overbreak-Prediction (`khimti 2 Overbreak.xlsx`, 175 kB). [V1]
- **Estructura** (según su `dataset_info.txt`): 1 577 filas × 14 columnas: Chainage, Pull (m), Drill Hole length (m), **RQD, Jn, Jr, Ja, Jw, SRF, Q**, **Overbreak %**, Specific Charge (kg/m³) y H (m).
- **Licencia:** el README dice MIT, pero no hay archivo LICENSE (GitHub: none) y no dice de dónde salen los datos (parecen datos de obra de una central hidroeléctrica). **No se redistribuye.** No lo bajé.
- **Nivel:** N3, con macizo (Q completo) y desempeño (sobreexcavación) **por ronda o tramo**. Es lo más cercano a tu tipo 1, pero sin sostenimiento.

### 2.7 Taludes de tajo abierto, IOMSSI (Ferentinou y Fakir 2018) (T5)
- **Enlace:** https://data.mendeley.com/datasets/73r6xcghmj (v1, 17-oct-2018). **CC0 1.0.** [V1]
- **Estructura** (`Appendix.docx`, 1 tabla): 142 taludes de 42 minas × 22 columnas: Mine, Pit-wall, **P1–P18** (parámetros codificados de 0 a 1, en el esquema de matriz de interacción) y **status** (0: 80 · 0,3: 36 · 1: 25; por lo que parece, estable / inestable / falla) más la referencia. Antes de usarlo hay que leer el artículo del IOMSSI para saber qué es cada P y qué significa cada valor del status.
- **Nivel:** N3 para un clasificador de taludes. Los datos están **codificados**, no son RMR ni Q-slope crudos. Revisado por pares.
- **Otros de taludes, sin datos públicos:**
  - Zare Naghadehi et al. 2013 (MSII, citado por Ayache et al. 2023, *REM*, CC BY) [V2].
  - Mahmoodzadeh et al. 2024 (*JRMGE*, CC BY-NC-ND, 344 taludes de Irán): el artículo no tiene declaración de datos [V1].
  - Trinidad y Momayez 2026, *Geotechnics* 6(1):15, CC BY, con un **tajo peruano** (FS con H, ángulo, γ, c y φ): MDPI bloqueó la consulta y no pude ver si trae anexo [NV].
  - NIOSH, Sbai et al. 2022, *Development of a Comprehensive Slope Failure Evaluation Database*: dominio público, pero es una propuesta y no trae datos; menciona 221 casos históricos (106 fallas y 115 estables) [V1, sin datos].

### 2.8 Pares RMR–Q (T3), aparte de los ya dichos
- Rehman et al. 2018, *Applied Sciences* 8(5):782, CC BY: 462 tramos de 2 túneles. MDPI bloqueó la consulta y no pude ver si hay anexo [NV].
- *Scientific Reports* 2025, PMC12084632 (CC BY): RMR–Q en roca fallada, 106 estaciones. Datos "on reasonable request", solo estadísticas [V1].
- Ranasooriya y Nikraz 2009 (*Australian Geomechanics*, Curtin) [V2].
- Seti Khola, Nepal (934 observaciones): "datos aún no disponibles" [V2].

### 2.9 TBM y túneles con clase de macizo (T4) — nada que sirva limpio
- MWD de 15 túneles noruegos (Hansen, Zenodo 10.5281/zenodo.10358374, CC BY 4.0): 4 CSV (raw, full, train, test) con **etiquetas de tipo de roca**, no de Q ni de sostenimiento [V1].
- Yinsong (China), `github.com/ChenZuyuIWHR/YS-IWHR`: ciclos de la TBM con 199 variables del sensor y tramos de colapso. **Sin licencia** y sin clase de macizo [V1]. El "shared big dataset for intelligent TBM" de Li et al. (2023, *Underground Space*) se entrega con solicitud [V2].
- Queens Water Tunnel (Yagiz, 151 casos) y Pahang-Selangor (Malasia, 180 tramos de macizo con datos de la TBM): solo citados [V2].
- "TBM Tunnel Collapse Ontology" (Zenodo 22079738): es una ontología, no trae datos.

### 2.10 Fallas y colapsos de túneles (T1, falla)
- **Enlace:** TU Dortmund Eldorado, "Database of tunnel collapses and failures", Spyridis, Mitroulis y Proske 2023. DOI 10.17877/DE290R-23148. Archivo de 101 kB. [V1]
- **Columnas:** Year, Country, Location, Project name, Failure type (FIR, OSF, FAC…), Incidents/causes, Length, Diameter, Depth, Construction/Operation, Excavation method, Construction typology, Ground condition, Rock/Soil, Consequences, Fatalities, Losses (USD) y Source.
- **Licencia:** solo el acuerdo de depósito con la universidad, sin licencia para terceros: **no se redistribuye.** No trae clase de macizo; sirve como contexto para N3.

### 2.11 Complementarios (estallido de roca y pilares)
- **Estallido de roca:**
  - Liu 2026, figshare 10.6084/m9.figshare.33346203, **CC BY 4.0**, descargado: 306 filas × 11 columnas (procedimiento constructivo, distancia al frente, posición en la sección, litología siempre gneis, sobrecarga, **profundidad del cráter**, intensidad leve 271 / moderada 32 / intensa 3, tipo y control estructural).
  - Mendeley `t9m76twr72` (CC BY 4.0, 91 casos microsísmicos, PDF) y `hj6vktg6jw` (CC BY 4.0, 69 casos someros, DOCX). [V1]
- **Pilares:**
  - `github.com/WangMeng0734/Pillar-stability-prediction-dataset` (`data.xlsx`, sin licencia) [V1].
  - Lunder y Pakalnis (178 casos, tesis de UBC, no comercial) [V2].
  - NIOSH, Esterhuizen et al., pilares de caliza (dominio público; datos en figuras o tablas resumidas) [V1].

---

## 3. Descartados
- **Kaggle:** lo que aparece es **sintético** o de otro rubro: `dradmanesv/slope-stability-dataset` (Monte Carlo), `ziya07/slope-stability-analysis-dataset` (10 000 casos generados), `ziya07/tunnel-risk-dataset` (simulado) y `colabsss/rock-stability-dataset` (pinturas rupestres). No hay nada de macizos reales. [V1]
- **Hugging Face:** nada de macizo rocoso ni de estallido; las búsquedas de "tunnel" devuelven tráfico e imágenes. [V1]
- **Portales de gobierno:**
  - BGS, National Geotechnical Properties Database: la licencia no está definida y parte es confidencial; es sobre todo de suelos [V2].
  - MSHA, Accidents (`arlweb.msha.gov/OpenGovernmentData/DataSets/`): obra del gobierno de EE. UU.; las caídas de roca solo vienen como narrativa, sin macizo [V2].
  - INGEMMET (GEOCATMIN): inventario de movimientos en masa, sin clasificación de macizo ni sostenimiento; no hallé su licencia [V2].
  - Sernageomin, Geoscience Australia y USGS: no encontré bases de macizo con sostenimiento [NV].
- **Q-slope:** la base de Bar y Barton (más de 500 casos) no es pública; solo publicaron gráficos [V2].
- **Dryad CC0** (descargados, poco valor): orientaciones de juntas (397 filas: dip y dip direction) y ensayos de PLS (hojas con 193 y 119 filas). No traen RMR, Q ni GSI.

## 4. Huecos sin datos públicos
1. **Tipo 1 completo:** macizo **+ sostenimiento instalado + desempeño** por tramo. No hay ninguna base pública con licencia. Lo más cercano es Khimti-2 (Q + sobreexcavación, sin sostenimiento ni licencia) y el squeezing de Mombilia (Q/RMR/GSI + convergencia, sin sostenimiento).
2. **Tipo 4:** túneles de TBM o de perforación y voladura con **clase de macizo y tipo de sostenimiento**. Las bases chinas e iraníes existen, pero se dan con solicitud o vienen sin licencia. Lo de NIOSH sobre luz contra sostenimiento (Ouchi y Pakalnis) solo está en gráficos.
3. **Q-slope y taludes de tajo con RMR/GSI crudos y estado fallado:** solo está IOMSSI, que viene codificado.
4. **Datos de Perú o Chile:** ningún dataset de macizo ni de estabilidad con datos abiertos. Lo único peruano es el tajo de Trinidad y Momayez 2026, sin verificar.

## 5. Copias locales
Carpeta base: `docs/investigacion/datos_publicos/` (fuera de git). Hay una carpeta por dataset y solo están los que tienen licencia CC BY o CC0. No se ejecutó nada de lo descargado; la estructura se leyó con `scripts\estructura.py` (openpyxl en solo lectura y `python -I`).
