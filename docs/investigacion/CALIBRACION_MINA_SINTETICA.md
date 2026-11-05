# Calibración de la mina sintética del módulo predictivo

Fecha: 5-nov-2026. Fuentes: solo web pública y bases públicas; no se abrió ninguna carpeta de clientes ni de
OneDrive. Construye encima de [DATOS_PUBLICOS.md](DATOS_PUBLICOS.md), [MODELOS_SOSTENIMIENTO.md](MODELOS_SOSTENIMIENTO.md)
y [SIMULACION_MINIMOS.md](SIMULACION_MINIMOS.md); lo que ya está ahí no se repite.

**Para qué sirve.** El generador (`python/rockmasspy/predictive/synthetic.py`) es un banco de pruebas de punta a punta
de los niveles 1, 2 y 3. Nunca entrena un modelo que se entregue. Este documento le da a cada parámetro un valor o un
rango con su fuente, para que el banco se parezca a una mina real y no a números inventados.

**Marcas.** **[V1]** leí el texto o calculé el agregado yo mismo sobre la base descargada · **[V2]** solo DOI y
metadatos, o el dato me llega citado por otro · **[NV]** no verificado · **[S]** sin fuente: supuesto de diseño,
con su razonamiento.

**Agregados propios.** Los números marcados «calc.» salen de
[scripts/calibracion_agregados.py](scripts/calibracion_agregados.py) y
[scripts/compendio_desprendimientos.py](scripts/compendio_desprendimientos.py), corridos con
`.venv\Scripts\python.exe -I` sobre las copias de `datos_publicos/` (fuera de git). Solo imprimen medias,
desviaciones, cuantiles, proporciones, pendientes y residuos; nunca filas.

| Base (carpeta en `datos_publicos/`) | Licencia | Uso aquí |
|---|---|---|
| ROCKMass/9/5876 de TC304 (`_sin_licencia_solo_consulta/rockmass_9_5876/`) | ninguna: solo agregados internos | A1, A2, B5 |
| Khimti-2, sobreexcavación en Nepal (`_sin_licencia_solo_consulta/khimti2_overbreak/`) | MIT sin archivo ni fuente: solo agregados internos | A2, A3, D9 |
| Squeezing de Mombilia et al. 2025 (`squeezing_grc_mombilia/`) | CC BY 4.0 (ver nota) | A1, B5 |
| GSI–RMR de Shirdel 2025 (`gsi_rmr_shirdel_alborz/`) | CC BY 4.0 | B5 |
| Luz crítica UBC de García-Gonzalo et al. 2016 (`critical_span_garcia_gonzalo_2016/`) | CC BY 4.0 | A1, D8 |
| HWStability (`hwstability_papaioanou_suorineni/`) | CC BY 4.0 | D8, D9 |
| Adoko et al. 2021, tabla 11 (`adoko_2021_ghana_stopes/`, PDF) | CC BY 4.0 | D8 |

Nota de licencia: el `Dataset GRC.xlsx` de Mombilia tiene el **mismo sha256 en la v1 (CC BY 4.0) y en la v2
(CC BY-NC 3.0)** de Mendeley (`155fc295…6533`), así que el archivo se puede usar con la licencia de la v1 citando
la v1. Khimti-2 se bajó con el mismo régimen que ROCKMass (solo agregados internos, nunca al repo ni al paquete);
si prefieres no usarlo, se borra la carpeta y se pierden los valores de A2, A3 y D9 que dicen «Khimti».

---

## A. Macizo y geología

| # | Parámetro | Valor o rango propuesto | Fuente | Marca | Comentario |
|---|---|---|---|---|---|
| A1.1 | RMR89 en una base mundial | media 55.6, DE 18.4, p5–p95 = 24–84 (n = 3262) | ROCKMass, calc. | [V1] | Sesgo a obra civil y roca buena. Clases: V 3.8 %, IV 18.6 %, III 34.2 %, II 35.1 %, I 8.2 % |
| A1.2 | log10 Q en una base mundial | media 0.45, DE 1.03, p5–p95 = −1.5 a 2.0 (n = 1957) | ROCKMass, calc. | [V1] | Clases NGI: muy mala 21 %, mala 18 %, regular 18 %, buena 22 %, extremadamente mala 8.5 % |
| A1.3 | GSI en una base mundial | media 47, DE 16, p5–p95 = 20–75 (n = 882) | ROCKMass, calc. | [V1] | 40–60: 51 %; 20–40: 24 % |
| A1.4 | Macizo débil (túneles con squeezing) | RMR media 31 (DE 17); GSI 29 (DE 16); log10 Q −0.71 (DE 0.95) | Mombilia et al. 2025, calc. | [V1] | Cota inferior: el escenario «sitio peor» |
| A1.5 | Macizo de galerías de minas de corte y relleno | RMR76 media 63, DE 13, p5–p95 = 40–80; luz mediana 9.5 m | luz crítica UBC, calc. | [V1] | 6 minas canadienses; RMR76 ≈ RMR89 − 5 según Osinergmin (2017) [V2] |
| A1.6 | **Mina andina de vetas (propuesta)** | RMR89 ~ Normal(45, 11) truncada a 15–80 → III ≈ 55 %, IV ≈ 30 %, II ≈ 12 %, V ≈ 3 % | [S], anclado en A1.1, A1.4 y la práctica peruana | [S] | Las tesis peruanas citan cajas IIIB–IVA (RMR 25–50) y vetas mejores (IIIA–IIIB); no encontré ninguna con la proporción por clase tabulada (§«Lo que falta», ítem 3). La DE dentro de una mina (11–13) es menor que la mundial (18): UBC, 6 minas, da 13 |
| A1.7 | DE dentro de una mina (no mundial) | RMR: 10–13; log10 Q: 0.5–0.8 | UBC calc. (13.3); Khimti calc. (log10 Q 0.49 en 1 túnel); Mombilia (0.95 en 135 túneles distintos) | [V1] | El generador hoy usa u con DE total ≈ 1.0 y deriva Q de u: verificar que salga log10 Q con DE ≈ 0.6–0.8 |
| A2.1 | Valores modales de los componentes de Q | Jn = 12 en 92 % de los tramos; Ja = 4 en 70 %; Jr = 1.5 en 57 % y 1 en 30 %; Jw = 1 en 68 % y 0.66 en 28 %; SRF ∈ {2.5, 5, 7.5, 10} en 95 % | Khimti-2, calc. (1577 rondas de un túnel en roca mala) | [V1] | **Realismo clave:** el geólogo usa pocos valores por parámetro. El generador sortea Jn, Jr y Ja con cuantiles uniformes de la tabla: conviene concentrarlos en 2–3 valores por dominio |
| A2.2 | Correlación entre componentes de Q (Spearman) | RQD–SRF −0.71; Jr–Jw −0.42; RQD–Ja −0.32; RQD–Jw +0.30; Ja–SRF +0.21; Jn casi independiente (|ρ| < 0.16) | Khimti-2, calc. | [V1] | ln Q depende sobre todo de RQD (+0.85) y SRF (−0.87). Hoy el generador tiene 0.6·u común en todos (ρ ≈ 0.3 entre pares): subir el peso de u en RQD y SRF y bajarlo en Jn |
| A2.3 | RMR89 contra RQD | RMR = 0.445·RQD + 28.7; DE residual 10.5; r = 0.78 (n = 693) | ROCKMass, calc. | [V1] | Para generar los parciales del RMR a partir de la misma u |
| A2.4 | Componentes del RMR89 (parciales) | sin base pública con los 5 parciales y su correlación | — | [S] | Shirdel trae parciales, pero su RQD sale del espaciamiento (Spearman RQD–espaciamiento = +1.00, calc.) y todo está seco: no sirve. Propuesta: parciales desde u con ρ ≈ 0.5 entre RQD, espaciamiento y condición de juntas; agua y resistencia más independientes (ρ ≈ 0.2) |
| A3.1 | Variograma a lo largo de una labor (log10 Q) | exponencial, alcance práctico ≈ 110 m (ajuste hasta 150 m), con una segunda estructura de ≈ 400 m; pepita 4–20 % de la meseta | Khimti-2, calc. (1388 progresivas, 1.7 m de separación) | [V1] | La pepita baja está inflada a la baja: el mismo mapeo se repite en rondas seguidas. Con mapeo independiente por tramo, esperar 15–30 % |
| A3.2 | Variograma de RQD a lo largo de la labor | exponencial, alcance ≈ 180 m (corto) y ≈ 600 m (largo); pepita 5–9 % | Khimti-2, calc. | [V1] | Igual reserva que A3.1 |
| A3.3 | Variograma del RMR a lo largo de un túnel de TBM | exponencial; alcance 30 m (meseta 360, pepita 25) y 18 m (meseta 75, pepita 20) en dos formaciones | Exadaktylos et al. 2008 | [V2] | Pepita 7–27 % de la meseta. Número leído en un resumen indexado, no en el artículo |
| A3.4 | Variograma 3D del RMR en una mina de cobre (sondajes) | exponencial con pepita, isótropo para RQD; distancias del orden de cientos de metros; los valores numéricos no están tabulados (solo figura) | Egaña y Ortiz 2013 | [V1] | Confirma el modelo «exponencial + pepita» y la simulación de los parciales (no del RMR) |
| A3.5 | **Propuesta para el generador** | AR(1) por progresiva dentro de cada labor con longitud de correlación 30–100 m (ρ entre tramos de 5 m ≈ 0.85–0.95) + pepita del 15–25 % de la varianza del tramo; efecto de zona como estructura larga (300–600 m) | A3.1–A3.3 | [V1]+[S] | Hoy la parte iid del tramo es ≈ 60 % de la varianza de u (0.8² frente a 0.4² + 0.5²): demasiada pepita y nada de continuidad. Con AR(1) la validación agrupada por labor se vuelve exigente, que es lo que hay que probar |
| A3.6 | Zonas de falla o cizalla | 1–5 por km de labor; ancho lognormal con mediana 10–20 m (p25–p75 ≈ 7–33 m); caída de 15–25 puntos de RMR (Q ÷ 10–30) | proxy: tramos contiguos con Q < 0.1 en Khimti-2 (5.1 por km, mediana 19 m, calc.) | [V1] proxy + [S] | No encontré una estadística publicada de zonas de falla por km en túneles. El proxy viene de un túnel muy malo (39 % de la longitud con Q < 0.1): para una mina de vetas usar el extremo bajo (1–2 por km) |

## B. Mapeo

| # | Parámetro | Valor o rango propuesto | Fuente | Marca | Comentario |
|---|---|---|---|---|---|
| B4.1 | DE del GSI entre evaluadores (visual, con la carta) | 8–10 puntos (COV 0.14–0.35); un caso con 16.6 | Pozo 2022: 40 ingenieros de Perú, España y Chile evaluando los mismos 4 macizos | [V1] | **El dato más cercano a una mina peruana.** Con fórmulas cuantitativas (RQD, Jcond) baja a 3–4.3 puntos (COV 0.06–0.15) |
| B4.2 | DE del GSI de un geólogo experimentado (proyecto con presupuesto) | ≈ 2.5 (GSI 25 ± 5 al 90 %); mayor en proyectos «de bajo presupuesto» | Hoek 1998 | [V1] | Cota inferior; Hoek sugiere un COV ≈ 0.10 |
| B4.3 | DE del RMR entre geólogos | 4–6 puntos | [S] | [S] | No encontré un estudio con varios geólogos en el mismo tramo y la DE del RMR. Razonamiento: el RMR suma 5 parciales con saltos de 2–5 puntos, y en la comparación noruega de RMR, Q y RMi el RMR resultó el menos sensible a cambiar un parámetro [NV, resumen en buscador]. Escenario malo: 8 |
| B4.4 | DE de log10 Q entre geólogos | 0.2–0.3 (un factor de 1.6–2 en Q) | [S] | [S] | Hay un estudio con 14 geólogos mapeando los mismos frentes en realidad virtual (Skretting et al., s. f.), pero no pude abrirlo (§«Lo que falta», ítem 1). Hansen et al. (2024) [V1] muestran que los errores de clase Q caen en clases vecinas |
| B4.5 | Variación del RQD entre observadores | alta; usar DE 10–15 puntos | Pells et al. 2017 | [V2] | El artículo documenta diferencias grandes en el mismo testigo; no tengo el número exacto |
| B4.6 | Sesgo sistemático por geólogo | efecto aleatorio con DE 2–4 puntos de RMR (o 0.1 en log10 Q), constante en el tiempo | [S], acotado por B5.4 | [S] | ROCKMass da DE 8.3 entre estudios, pero eso junta sitio, método y observador: es una cota superior. Para probar el nivel 1 con «geólogo» como grupo |
| B5.1 | RMR = a·ln Q + b (mundial) | a = 6.67 ± 0.13, b = 49.3; DE residual 10.4; R² 0.70 (n = 1101) | ROCKMass, calc. | [V1] | Por litología: ígneas 5.65 / 54.2 (DE 11.7); sedimentarias 6.32 / 43.9 (8.7); metamórficas 6.59 / 51.0 (9.0) |
| B5.2 | La misma, macizo débil | a = 6.94 ± 0.32, b = 42.2; DE residual 7.7; R² 0.80 (n = 122) | Mombilia, calc. | [V1] | — |
| B5.3 | La misma, clásicas | Bieniawski 1976: 9 ln Q + 44; Barton 1995: 15 ln Q + 50; Huang et al. 2026: 6.70 ln Q + 46.3 (448 pares) | [INVESTIGACION_BIBLIOGRAFICA.md](INVESTIGACION_BIBLIOGRAFICA.md) §8 | [V2] | El generador usa 9 ln Q + 44: queda en el borde alto de la pendiente. Dejar 9/44 como «sitio Bieniawski» y usar 6.7/46–49 por defecto |
| B5.4 | **Efecto de sitio en la correlación** | DE del sesgo por estudio 8.3 (RMR–Q) y 8.8 (RMR–GSI); DE residual dentro del estudio, mediana 7.2; pendiente por estudio: mediana 7.2, p5–p95 = 2.8–8.9 (17 estudios) | ROCKMass, calc. (estudios con ≥ 10 pares) | [V1] | **Lo que más le sirve al nivel 1:** es el tamaño real del «por qué cada mina necesita su correlación». En el generador: `rmr_b` de la mina ~ 46 ± 8 y `rmr_a` ~ 6.7 ± 1.5 por escenario; `sd_rmr` ≈ 7 dentro de la mina |
| B5.5 | GSI = c·RMR89 + d | c = 0.78, d = 6.4; DE residual 11.1 (n = 343); GSI − RMR: media −3.5, DE 11.7 | ROCKMass, calc. | [V1] | Coherente con «GSI = RMR89 − 5» de Hoek, con mucha dispersión |
| B5.6 | La misma, macizo débil | c = 0.82, d = 4.05; DE 7.9 | Mombilia, calc. | [V1] | — |
| B5.7 | GSI = e·ln Q + f | e = 5.5–5.9, f = 39–44; DE 9.4–11.0 | ROCKMass y Mombilia, calc. | [V1] | Hoek et al. (1995) usan 9 ln Q′ + 44 [V2] |
| B5.8 | GSI–RMR de un solo sitio con GSI cuantificado | GSI = 1.74·RMR − 9.5; DE 0.9; GSI − RMR = +19 ± 4 | Shirdel 2025, calc. | [V1] | No sirve como calibración: el GSI sale de una fórmula sobre los mismos parámetros (R² 0.99), el rango de RMR es estrecho y la base no tiene revisión por pares. Muestra lo que pasa si el GSI se calcula en vez de mapearse |

**Propuesta para el nivel 1:** `rmr_a` 6.7, `rmr_b` 46, `sd_rmr` 7, `sd_labor_rmr` 3; `gsi_c` 0.8, `gsi_d` 5, `sd_gsi` 8.
Más el ruido de observador de B4 encima de la «verdad», si se quiere probar la regresión con errores en ambas
variables (Deming).

## C. Práctica

| # | Parámetro | Valor o rango propuesto | Fuente | Marca | Comentario |
|---|---|---|---|---|---|
| C6.1 | Cómo se elige el sostenimiento en el Perú | tabla GSI propia de cada mina (estructura × condición, 5 × 5, con color y sostenimiento por sección), derivada de Vallejo (2002); el RMR y el Q se usan como verificación | Osinergmin 2017 §3.2.3.8; [INVESTIGACION_BIBLIOGRAFICA.md](INVESTIGACION_BIBLIOGRAFICA.md) §9.3 | [V1]/[V2] | La práctica del generador debería leer **GSI** (con su ruido de B4.1, DE 8–10), no ln Q. Así el nivel 2 ve la incoherencia que viene del mapeo visual |
| C6.2 | Uso del Q y de la carta en minas de roca dura | ≈ 75 % de las minas (más de 60 planes de control de terreno de Australia y Canadá) usan el Q para el diseño preliminar; Unwedge 55 %; modelos numéricos 20 % | Potvin y Hadjigeorgiou 2015 | [V1] | — |
| C6.3 | Desvío de lo instalado frente a la carta | «a menudo se aparta de forma significativa»; en minas australianas el Q **subestima** el sostenimiento en roca buena y muy buena y lo **sobrestima** en roca mala a extremadamente mala (59 casos de 15 minas) | Potvin y Hadjigeorgiou 2015, citando a Peck y Lee 2007 | [V1] (Peck y Lee [V2]) | En el generador: `practice_beta_lnq` más plano que la carta (la mina instala un mínimo en roca buena y ahorra en roca mala). Propuesta: cortar la pendiente de la práctica al 50–70 % de la que implica la carta, con un piso (nunca menos que el tipo II) |
| C6.4 | Dispersión de la práctica alrededor de su propia regla | ruido logístico con escala 1 (≈ 60–70 % de los tramos en la clase modal de su celda) + efecto de labor DE 0.5 | [S] | [S] | No encontré ninguna auditoría peruana que cuantifique «instalado contra tabla». Es el valor actual del generador; el razonamiento es que el desvío viene del cambio de tabla, del equipo disponible y del criterio del supervisor, no de un sesgo fijo |
| C6.5 | Tiempo sin sostener | mediana 1 turno en roca IV–V (regla de Osinergmin: si el autosoporte leído es ≤ 20 h, «labor avanzada, labor sostenida»); 1–7 días en roca II–III | DS 024-2016-EM art. 213; Osinergmin 2017 §8.4 | [V1]/[V2] la regla; [S] la distribución | Ligarlo al autosoporte de D8.5: si el retraso supera el autosoporte de la clase y la luz, la tasa de falla del tramo sube (por ejemplo × 3–5 durante ese lapso) [S] |
| C6.6 | Cambio de tablas en el tiempo | revisión anual del plan de control de terreno (Australia, en algunas jurisdicciones); en el Perú la actualización mensual del estudio (2016) pasó a «cuando se amerite» (2023) | Potvin y Hadjigeorgiou 2015; DS 024-2016-EM y DS 034-2023-EM | [V1] | Escenario: un cambio de tabla en el año 3 que aliviana un tipo en roca III (como el paso de pernos de 22 a 19 mm de Salcedo, 2023 [V2]); el nivel 2 debería ver un quiebre temporal |
| C6.7 | Control de calidad obligatorio | mensual, ≥ 1 % por cada tipo de sostenimiento | DS 024-2016-EM art. 214 b (texto 2023) | [V1] | Fija la frecuencia mínima de «inspección» que una mina registra |

## D. Desempeño

| # | Parámetro | Valor o rango propuesto | Fuente | Marca | Comentario |
|---|---|---|---|---|---|
| D7.1 | Muertes por desprendimiento de rocas, mediana y gran minería del Perú | 152 de 543 (28 %) entre 2007 y 2025; 20–22 por año en 2008–2009, ≈ 5 por año desde 2015; 2024: 8 de 15 | Osinergmin, compendios de accidentes mortales 2024 y 2025-II, tabla 3.3 | [V1] | Primera causa de muerte. No da tasas por km: Osinergmin no publica los km de labor activos |
| D7.2 | Dónde ocurrieron (11 relatos de 2023–2025) | galería, crucero o rampa 36 %; chimenea 18 %; corona 45 %; con sostenimiento mencionado 36 %; desatado 27 %; estructura o falla 18 % | Osinergmin, calc. con palabras clave | [V1] | Muestra chica (n = 11): solo dice que las caídas también pasan **con** sostenimiento instalado. No usar como proporción |
| D7.3 | Proporción de casos «no estables» en bases de casos | galerías y techos de corte y relleno: 14 % inestables y 26 % potencialmente inestables (n = 399); tajeos: 46 % (HWStability) y 52 % (Adoko) | luz crítica UBC, HWStability y Adoko, calc. | [V1] | Son bases sesgadas hacia los casos interesantes; no son tasas |
| D7.4 | Labores de minas que necesitaron rehabilitación | 3 de 30 sitios (10 %) | Peck y Lee 2007, citado por Potvin y Hadjigeorgiou 2015 | [V2] | La única cifra cercana a «proporción de labores que fallan» |
| D7.5 | **Tasa base para el generador** | galería permanente bien sostenida: 0.5–2 % de los tramos de 5 m con falla registrada por año (≈ 1–4 eventos por km por año); roca IV–V o sostenimiento por debajo de la carta: 5–15 % por año | [S], acotado por D7.3 y D7.4 | [S] | Hoy el generador tiene ≈ 45 % de fallas en 30–900 días, pensado para la potencia del nivel 3. Proponer dos modos: «realista» (prevalencia 5–15 % en la vida del histórico) y «estrés» (el actual). La simulación de mínimos tendría que repetirse en modo realista: con 5–10 % de fallas, 10 eventos por parámetro piden ≈ 400–600 tramos |
| D8.1 | Luz crítica sin sostenimiento o con sostenimiento local (UBC) | logit P(inestable) = 2.00 − 0.280·RMR76 + 5.01·ln luz (± 0.85, 0.039, 0.76); AUC 0.94 | luz crítica UBC (n = 399, 56 inestables), calc. | [V1] | Con «potencialmente inestable» como evento: 8.71 − 0.351·RMR + 5.40·ln luz. Para eventos raros, logit ≈ log λ + log T, así que estas pendientes valen como pendientes de log λ |
| D8.2 | Lo mismo en ln Q | β_lnQ ≈ −0.28 × 6.7 ≈ −1.9 por unidad de ln Q; β_ln De ≈ 5 | D8.1 y B5.1 | [V1] derivado | El generador usa −0.5 y 1.0: efectos 4–5 veces más débiles que en la base UBC. Propuesta: β_lnq −1.0 a −2.0 y β_lnde 1.5 a 3 (la base UBC está etiquetada contra la propia curva y exagera la separación) |
| D8.3 | Tajeos (gráfico de estabilidad) | logit P(inestable) = 1.96 − 1.88·ln N′ + 0.90·ln HR (HWStability, AUC 0.89); P(no estable) = −8.28 − 2.09·ln N′ + 7.63·ln HR (Adoko, AUC 0.96); P(hundido) = −16.6 − 4.07·ln N′ + 11.9·ln HR | HWStability y Adoko, calc. | [V1] | Para el tipo de labor «Tajeo». Los coeficientes de Mawdesley et al. (2001) no se pudieron leer (§«Lo que falta», ítem 2) |
| D8.4 | Efecto del tipo de sostenimiento sobre la luz estable (roca débil) | 463 casos con RMR76 25–60 en 4 categorías: A pernos de fricción (n = 47; luz estable máxima de 3 m con RMR76 = 25), B con barras puntuales (176), C con barras sistemáticas (152), D cables, shotcrete, marchavantes o cuadros (88). Las barras de resina **no** corren la curva tanto como se esperaba en roca débil | Ouchi, Pakalnis y Brady 2004 y 2009 | [V1] | En el generador: `fail_beta_rank` −0.3 a −0.6 por paso de tipo, no más; escenario «el sostenimiento casi no ayuda en roca V» con −0.2 |
| D8.5 | Tiempo de autosoporte por clase (RMR89) | I: 20 años con 15 m de luz · II: 1 año con 10 m · III: 1 semana con 5 m · IV: 10 h con 2.5 m · V: 30 min con 1 m | Bieniawski 1989, tabla reproducida por Hoek (Practical Rock Engineering, cap. 3) | [V1] | Otras copias dan 10 años y 6 meses con 8 m para I y II: esas son de la versión de 1976–1979. Sirve para C6.5 |
| D8.6 | Carta Q de Grimstad y Barton | la base original es casi toda de túneles escandinavos; en 1974 tenía solo 2 casos de excavaciones mineras temporales y pocas luces de 4–6 m; la mayoría de las minas siguen con el SRF de 1974 | Potvin y Hadjigeorgiou 2015 | [V1] | La carta no trae probabilidades de falla: no da coeficientes logísticos |
| D9.1 | Sobreexcavación en galería por voladura | mediana 12 % (p5–p95 = 4–38 %); ln(sobreexc. %) = 1.67 − 0.41·ln Q, DE residual 0.64 | Khimti-2, calc. | [V1] | Avance mediano 1.7 m por ronda |
| D9.2 | Sobreexcavación en tajeos (ELOS) | mediana 0.95 m (p5–p95 = 0.1–3.4 m); ln ELOS = 0.87 − 0.54·ln N′, DE 1.05 | HWStability, calc. | [V1] | Lognormal |
| D9.3 | Volumen de las caídas | Pareto (ley de potencia) con exponente acumulado 0.5–1.0 y corte inferior ~0.01 m³; el tamaño típico ligado al bloque de la familia de juntas (espesor 0.3–1 m) | caídas naturales en taludes: exponentes 0.3–1.0 y 0.51–1.27 | [V2] / [S] para minas | No encontré una relación frecuencia–volumen publicada para caídas en labores subterráneas. Si el generador registra «volumen de la caída», usar esto solo como forma |
| D9.4 | Vida útil de la labor | galería y rampa permanentes: 3–15 años; tajeo: 2–12 meses | [S] | [S] | El generador ya distingue permanente o temporal (ESR 1.6 o 3) |
| D9.5 | Frecuencia de inspección | labores activas: mensual (art. 214 b); inactivas: trimestral a semestral | DS 024 art. 214 b; [S] para inactivas | [V1]/[S] | El generador usa ≈ 4 meses: sirve para labores inactivas; en activas pasar a 1 mes |

---

## Propuesta de escenarios

Cada escenario cambia solo lo que se indica respecto del **base**. Los nombres de los campos son los de
`SyntheticTruth`; los que no existen todavía van en *cursiva* (habría que agregarlos al generador).

| Escenario | Qué prueba | Cambios |
|---|---|---|
| **Base realista** | todo el pipeline con números de la literatura | `rmr_a` 6.7, `rmr_b` 46, `sd_rmr` 7, `sd_labor_rmr` 3; `gsi_c` 0.8, `gsi_d` 5, `sd_gsi` 8; *RMR objetivo* ~ N(45, 11); *AR(1)* de 30–100 m + pepita 20 %; *zonas de falla* 1–2/km de 10–20 m; `fail_beta_lnq` −1.5, `fail_beta_lnde` 2.0, `fail_beta_rank` −0.5; prevalencia de falla 5–15 %; `exposure_days` 30–1800; inspección mensual |
| **Sitio igual a NGI** | que el nivel 3 no invente efecto de sitio | `site_effect=False` (la tasa depende solo de la categoría de la carta Q), `rmr_a` 9, `rmr_b` 44; práctica = carta Q (`practice_incoherence` 0 y pendiente plena) |
| **Sitio peor** (roca débil, squeezing) | extrapolación y la clase V | RMR objetivo ~ N(32, 15) (Mombilia); `rmr_b` 42, `rmr_a` 6.9; zonas de falla 3–5/km; prevalencia 15–25 %; `fail_beta_rank` −0.2 en roca V (D8.4) |
| **Sitio mejor** | pocas fallas, separación casi completa | RMR objetivo ~ N(63, 13) (UBC); prevalencia 1–3 %; prueba Firth y la contracción a la curva global |
| **Correlación del sitio corrida** | nivel 1: detectar que la mina no sigue la ecuación mundial | `rmr_b` = 46 ± 8 (una DE de B5.4) y `rmr_a` de 5 u 8.5 |
| **Práctica conservadora** | nivel 2: la mina sostiene de más | cortes de `practice_cuts` corridos −1 (todo un tipo más pesado); pendiente plena; fallas muy raras (≈ 2 %) |
| **Práctica incoherente** | nivel 2: el modelo de práctica pierde la señal | `practice_incoherence` 0.3–0.5; *la práctica lee el GSI visual con DE 10* (B4.1) en vez de ln Q; *cambio de tabla* en el año 3 (C6.6) |
| **Práctica tipo mina** (Peck y Lee) | nivel 2 frente a la carta | pendiente de la práctica al 50–70 % de la carta (más que la carta en roca buena, menos en roca mala); piso en el tipo II |
| **Mapeo ruidoso** | errores en ambas variables | ruido de observador encima de la verdad: RMR DE 5, log10 Q DE 0.25, GSI DE 9; *efecto de geólogo* DE 3; Jn, Ja y Jr con valores modales (A2.1) |
| **Mina chica** | mínimos de datos | 2 zonas × 4 labores × ~10 tramos (≈ 80 tramos), 4 años |
| **Mina grande** | escala y validación por zona | 8 zonas × 15 labores × ~40 tramos (≈ 4800 tramos), 10 años; zonas de falla presentes |

---

## Lo que falta descargar

Artículos y tesis de pago o bloqueados para la descarga automática. Ordenados por importancia para el generador.

| # | Referencia | DOI o enlace | Qué dato sacaríamos | Importancia |
|---|---|---|---|---|
| 1 | Skretting, E. et al. (s. f., ≈ 2023) [NV]. *Virtual reality based uncertainty assessment of rock mass characterization of tunnel faces* (14 geólogos mapeando los mismos frentes con Q) | sin DOI verificado; ResearchGate 374559810 (403 al bajar) | DE de log10 Q y de cada parámetro entre geólogos, sesgo por persona (B4.4, B4.6) | **Alta** |
| 2 | Mawdesley, C., Trueman, R., & Whiten, W. J. (2001). Extending the Mathews stability graph for open-stope design. *Mining Technology*, 110(1) | 10.1179/mnt.2001.110.1.27 [V2] | coeficientes logísticos de las isoprobabilidades de estable, falla y falla mayor (D8.3) | **Alta** |
| 3 | Tesis peruanas con mapeo por clases en vetas: Oriundo Yaranga (2008, UNSCH); Córdova Rojas (2008, UNI); Ancalla Monge (2019, UNSAAC) | enlaces en [INVESTIGACION_BIBLIOGRAFICA.md](INVESTIGACION_BIBLIOGRAFICA.md) §10 | proporción de metros por clase RMR o GSI en cajas y vetas, DE dentro de la mina (A1.6) | **Alta** |
| 4 | Pinheiro, M., Vallejos, J., Miranda, T., & Emery, X. (2016). *Engineering Geology*, 205, 93–103; y Pinheiro, Emery, Miranda y Vallejos (2016), *Rock Mech. Rock Eng.*, 49(8), 3371–3376 | 10.1016/j.enggeo.2016.03.003; 10.1007/s00603-016-0928-x [V2] | alcances, pepita y anisotropía de los parciales del RMR en una mina (A3) | **Alta** |
| 5 | Pinheiro, M., Emery, X., Miranda, T., Lamas, L., & Espada, M. (2018). Modelling geotechnical heterogeneities using geostatistical simulation and finite differences analysis. *Minerals*, 8(2), 52 | 10.3390/min8020052 (acceso abierto; MDPI bloquea la descarga automática) | variogramas de parámetros del macizo | Media (gratis desde el navegador) |
| 6 | Ouchi, A., Pakalnis, R., & Brady, T. (2008). ARMA 08-376 (luz en roca débil por tipo de sostenimiento), NIOSH stacks 226973 | stacks.cdc.gov/view/cdc/226973 | los 463 casos por categoría A–D (RMR, luz, estado): coeficiente real de `fail_beta_rank` (D8.4). El apéndice de 2004 sale mal por OCR (solo 70 de 135 casos legibles) | **Alta** |
| 7 | Peck, W. A., & Lee, M. F. (2007). Aplicación del Q a minas metálicas australianas (59 casos de 15 minas) | [NV] sin DOI | sostenimiento instalado contra Q (C6.3), rehabilitaciones (D7.4) | Media |
| 8 | Exadaktylos, G. et al. (2008). A spatial estimation model for continuous rock mass characterization from the specific energy of a TBM. *Rock Mech. Rock Eng.* | 10.1007/s00603-007-0160-9 [V2] | confirmar los variogramas del RMR de A3.3 | Media |
| 9 | Pells, P. J., Bieniawski, Z. T., Hencher, S. R., & Pells, S. E. (2017). Rock quality designation (RQD): time to rest in peace. *Canadian Geotechnical Journal*, 54 | 10.1139/cgj-2016-0012 [V2] | DE del RQD entre observadores (B4.5) | Media |
| 10 | Vallejo, C. (2002) y Vallejos Cortez, C. (2011): GSI modificado y su aplicación al control de caída de rocas | sin DOI (congresos peruanos) | regla de la práctica peruana y su desvío (C6.1, C6.4) | Media |
| 11 | Potvin, Y., & Nedin, P. (2003). *Management of rockfall risks in underground metalliferous mines* (ACG/MOSHAB) | [NV] | frecuencia de caídas por mina y su tamaño (D7.5, D9.3) | Media |
| 12 | Lang, B. (1994). Tesis de maestría, UBC (172 casos de luz crítica) | circle.ubc.ca/handle/2429/5578 (no comercial) | casos originales sin la mezcla de minas | Baja |
| 13 | Ranasooriya, J., & Nikraz, H. (2009). Reliability of the linear correlation of RMR and Q. *Australian Geomechanics*, 44(2) | [V2] sin DOI | DE residual de RMR–ln Q en otra base (ya la tenemos de ROCKMass) | Baja |
| 14 | Tesis U. de Chile (2020). *Modelamiento geoestadístico de la clasificación geomecánica de Bieniawski (RMR)* | repositorio.uchile.cl/handle/2250/176858 (el PDF no bajó) | variogramas del RMR en un skarn | Baja |

**Sin fuente (supuestos de diseño, para revisar con Miqueas):** A1.6, A2.4, A3.5 (parte), A3.6, B4.3, B4.4, B4.6,
C6.4, C6.5 (multiplicador), D7.5, D9.3 (en minas), D9.4 y D9.5 (inactivas).

---

## Bibliografía (APA 7)

- Adoko, A. C., Saadaari, F., Mireku-Gyimah, D., & Imashev, A. (2021). A feasibility study on the implementation of neural network classifiers for open stope design. *Geotechnical and Geological Engineering, 40*(2), 677–696. https://doi.org/10.1007/s10706-021-01915-8 [V1]
- Bieniawski, Z. T. (1989). *Engineering rock mass classifications*. Wiley. Tabla de autosoporte leída en Hoek, E., *Practical rock engineering*, cap. 3 (Rocscience). [V1]
- Ching, J., Phoon, K.-K., Ho, Y.-H., & Weng, M.-C. (2021). Quasi-site-specific prediction for deformation modulus of rock mass. *Canadian Geotechnical Journal*. https://doi.org/10.1139/cgj-2020-0168 [V2]. Base ROCKMass/9/5876: http://140.112.12.21/issmge/Database/RM_9.xlsx [V1]
- Egaña, M., & Ortiz, J. M. (2013). Assessment of RMR and its uncertainty by using geostatistical simulation in a mining project. *Journal of GeoEngineering, 8*(3), 83–90. https://doi.org/10.6310/jog.2013.8(3).2 [V1]
- Exadaktylos, G., Stavropoulou, M., Xiroudakis, G., et al. (2008). A spatial estimation model for continuous rock mass characterization from the specific energy of a TBM. *Rock Mechanics and Rock Engineering*. https://doi.org/10.1007/s00603-007-0160-9 [V2]
- García-Gonzalo, E., Fernández-Muñiz, Z., García Nieto, P. J., Bernardo Sánchez, A., & Menéndez Fernández, M. (2016). Hard-rock stability analysis for span design in entry-type excavations with learning classifiers. *Materials, 9*(7), 531. https://doi.org/10.3390/ma9070531 [V1]
- Hoek, E. (1998). Reliability of Hoek-Brown estimates of rock mass properties and their impact on design. *International Journal of Rock Mechanics and Mining Sciences, 35*(1), 63–68. https://doi.org/10.1016/S0148-9062(97)00314-8 [V1]
- Mombilia et al. (2025). Analytical dataset to determine squeezing potential of deep tunnels. *Data in Brief, 61*, 111808. https://doi.org/10.1016/j.dib.2025.111808 [V1]; datos: https://doi.org/10.17632/w3yhkp6zxn
- Osinergmin (2017). *Guía de criterios geomecánicos para diseño, construcción, supervisión y cierre de labores subterráneas*. [V1, en INVESTIGACION_BIBLIOGRAFICA.md]
- Osinergmin (2024–2025). *Información estadística de seguridad y compendio ilustrativo de accidentes mortales en el ámbito de mediana y gran minería* (ediciones 2023, 2024, 2025-I y 2025-II). [V1]
- Ouchi, A. M., Pakalnis, R., & Brady, T. M. (2004). *Update of span design curve for weak rock masses*. CIM AGM, Edmonton. https://stacks.cdc.gov/view/cdc/221136 [V1]
- Ouchi, A., Pakalnis, R., & Brady, T. (2009). Weak rock mass span design: best practices. En M. Diederichs y G. Grasselli (Eds.), *RockEng09, 3rd CANUS Rock Mechanics Symposium*, Toronto. [V1]
- Papaioanou, A., & Suorineni, F. T. (2016). Development of a generalised dilution-based stability graph for open stope design. *Mining Technology, 125*(2), 121–128. https://doi.org/10.1080/14749009.2015.1131940 [V2]; datos: https://data.mendeley.com/datasets/999nngmxb4 [V1]
- Pells, P. J., Bieniawski, Z. T., Hencher, S. R., & Pells, S. E. (2017). Rock quality designation (RQD): time to rest in peace. *Canadian Geotechnical Journal, 54*. https://doi.org/10.1139/cgj-2016-0012 [V2]
- Potvin, Y., & Hadjigeorgiou, J. (2015). Empirical ground support design of mine drives. En Y. Potvin (Ed.), *Design Methods 2015* (pp. 419–430). Australian Centre for Geomechanics. https://doi.org/10.36487/ACG_rep/1511_25_Potvin [V1]
- Pozo, R. (2022). Comparative analysis of different calculation methods of the Geological Strength Index (GSI) based on qualitative and quantitative approaches. *Rudarsko-geološko-naftni zbornik, 37*(3), 121–138. https://doi.org/10.17794/rgn.2022.3.10 [V1]
- Shirdel, B. (2025). *Field dataset for GSI-RMR_adj correlation in Central Alborz rock masses* [Conjunto de datos]. Zenodo. https://doi.org/10.5281/zenodo.17397696 [V1]
- Wang, J., Milne, D., & Pakalnis, R. (2002). Application of a neural network in the empirical design of underground excavation spans. *Mining Technology, 111*(1). https://doi.org/10.1179/mnt.2002.111.1.73 [V2]
- zexxr (s. f.). *Tunnel overbreak prediction* (datos de Khimti-2) [Repositorio de GitHub]. https://github.com/zexxr/-Tunnel-Overbreak-Prediction [V1, sin licencia válida]
- Caídas naturales (D9.3, solo forma): preprint EGUsphere-2025-6247 y «Comparison of block size distribution in rockfalls» (UPCommons). [V2, solo resumen]
