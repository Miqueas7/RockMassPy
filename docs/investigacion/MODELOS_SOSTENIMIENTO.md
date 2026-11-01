# Modelos para predecir sostenimiento y calibrar tablas propias de cada mina

Investigación bibliográfica para el módulo de calibración de una librería open source de geomecánica minera (Python con núcleo C++). Fecha: 31-oct-2026. Fuentes: solo web pública; no se leyó ninguna carpeta local ni dato de cliente.

## Cómo leer las marcas de verificación

- **[V1]**: leí el texto completo o el resumen en la página de la editorial, en arXiv o en el repositorio oficial.
- **[V2]**: verifiqué el DOI y los metadatos (autores, revista, volumen, páginas) en Crossref a través de OpenAlex, que indexa los DOI de Crossref. La API directa de Crossref devolvió error 429 (límite de consultas), así que todas las comprobaciones de DOI se hicieron con OpenAlex resolviendo el DOI exacto. Cuando también leí el resumen indexado, lo indico como "[V2 + resumen]".
- **[NV]**: no verificado. Lo cito porque es un clásico o porque lo encontré en un buscador sin poder abrir la fuente. No uses estas referencias sin revisarlas antes.

Ningún DOI de este informe es inventado. Los textos sin DOI aparecen sin DOI. Hubo un caso en que el DOI que recordaba estaba mal (Santos et al., 2021, termina en `-y` y no en `-0`), y lo corregí con la verificación. Por eso conviene comprobar cada DOI antes de citarlo.

---

## 0. Respuesta corta

Con el histórico de una mina (evaluaciones RMR/Q/GSI más el sostenimiento instalado y si falló) **no conviene entrenar un solo clasificador "macizo → tipo de sostenimiento"**. Ese modelo aprende la *práctica pasada* de la mina, incluidos sus errores y su conservadurismo, y no aprende qué sostenimiento *funciona*. La literatura y la estadística aplicada apuntan a separar tres problemas:

1. **Correlaciones propias** (RMR–Q, RMR–GSI, Q–GSI): regresión con intervalos de predicción, bootstrap y, si hay pocos datos, un modelo bayesiano jerárquico que combine una base de datos global con los datos de la mina (Ching et al., 2020).
2. **Modelo de práctica** (qué sostenimiento se instala normalmente): regresión logística ordinal. Sirve para auditar la consistencia del histórico, no para recomendar.
3. **Modelo de desempeño** (probabilidad de falla según el macizo, la luz, el tipo de labor y el sostenimiento): regresión logística, de preferencia bayesiana, con curvas de isoprobabilidad al estilo Mathews/Mawdesley (Mawdesley et al., 2001). La recomendación es *el sostenimiento más liviano cuya probabilidad de falla queda bajo el umbral que fija el ingeniero*.

La validación tiene que ser **agrupada por labor y por zona, además de temporal**, nunca aleatoria por registro. La gran mayoría de los artículos con exactitudes del 90 al 100 % usan particiones aleatorias de tramos vecinos, y esos números no se pueden comparar con el desempeño en una zona nueva.

---

## 1. Estado del arte 2010–2026

### 1.1 Tabla resumen

| Referencia | Qué predice | Datos (n) | Variables de entrada | Modelos | Métrica reportada | Validación | ¿Datos públicos? | Marca |
|---|---|---|---|---|---|---|---|---|
| Wang, Milne y Pakalnis (2002) | Estabilidad de la luz (estable / potencialmente inestable / inestable), gráfico de luz crítica | 292 casos de 6 minas canadienses | RMR, luz | Red neuronal (Braincel) | Mapa de estabilidad sobre 342 puntos de malla | No detallada en el resumen | **Sí: la base de datos va como anexo** | [V2 + resumen] |
| García-Gonzalo et al. (2016) | Las mismas tres clases del gráfico de luz crítica | Base de casos de corte y relleno de Canadá (la de la línea anterior, ampliada) | RMR, luz | SVM, ELM | "Correlación razonable" con las guías previas | No detallada en el resumen | Base de la literatura | [V2 + resumen] |
| Goh et al. (2017) | Estabilidad de excavaciones con ingreso de personal | Base de luz crítica | RMR, luz | MARS, regresión logística | — | — | Base de la literatura | [V2] |
| Qi et al. (2018) | Estabilidad del hastial colgante (*hangingwall*) del tajeo abierto | 115 casos de la literatura | Parámetros del gráfico de estabilidad (N', RH, etc.) | Random forest | AUC 0,873 en la prueba | Partición aleatoria + 5-fold CV | Literatura | [V1 resumen] |
| Santos, Amaral et al. (2020), REM (Brasil) | Estabilidad de tajeos abiertos | — | — | IA (clasificadores) | — | — | Hay un registro en Figshare | [V2] |
| Santos, Lana y Pereira (2020, 2021), UFOP (Brasil) | Clase RMR | Base de tajos abiertos (n no visible en el resumen) | Subconjunto de variables RMR | Naive Bayes, RF, ANN, SVM | Exactitud media > 0,81 | 30 submuestreos aleatorios (2/3 entrenamiento) | No | [V1 resumen] |
| Adoko et al. (2021) | Estado del tajeo: estable / inestable / hundido | **225 superficies** de 3 minas de Ghana (45 / 38 / 17 %) | N', RH | Red feed-forward (2×110) | Exactitud media 91 %; falla en la clase "hundido" (6 de 38 mal clasificados) | Aleatoria 70/15/15, **sin validación cruzada** | **Sí, anexo (CC BY)** | [V1 texto completo] |
| Korigov, Adoko y Sengani (2022) | Zonas de dilución no planificada | — | Gráfico de dilución | Clasificador ANN | — | — | — | [V2 + resumen] |
| Mortazavi y Osserbay (2022) | Gráfico de Mathews "consolidado" | Base Mathews extendida, solo métodos sin ingreso de personal | N', RH | Regresión logística | Isoprobabilidades | — | Literatura | [V2 + resumen] |
| Hu et al. (2022), mina Chambishi | Clase de macizo (I–V) | **80 casos**, 4 variables | 4 factores | SVM + PSO/GA/GWO | Exactitud de prueba 93,75 % (**15 de 16**) | Aleatoria 64/16 | — | [V2 + resumen] |
| Chang et al. (2022), ISGSR | **Patrón de sostenimiento inicial** (S4b, S4c, S5a, S5b, S5c) | **133 frentes de un solo túnel** (30 / 27 / 20 / 26 / 30) | 13 variables de frente | LR, RF, SVM, AdaBoost, votación | F1 > 90 % en la prueba; AdaBoost exactitud = F1 = 1,00 | Aleatoria 70/30 | No | [V1 texto completo] |
| Liu, Wang et al. (2020) | Clase de macizo (método hidroeléctrico chino) a partir de datos de TBM | 3166 muestras | Estadísticos de la operación de la TBM | AdaBoost-CART | Exactitud 0,865; F1 0,770 | Partición entrenamiento/prueba; SMOTE | No | [V2 + resumen] |
| Hou, Liu y Yang (2022) | Clase de macizo a partir de datos de TBM | 7538 ciclos | Operación de la TBM | Stacking | — | — | No | [V2 + resumen] |
| Brousset et al. (2023), UPC (Perú) | Índice RMR | — | Propiedades del macizo | ANN | "Error de 0,279 %" | No visible en el resumen | No | [V2 + resumen] |
| Huang et al. (2024) | Calidad del macizo en el frente, con datos incompletos | Dataset multifuente de frentes | Imágenes (agua, fracturas, capas débiles) + parámetros | Swin Transformer + red bayesiana TAN | — | — | — | [V2 + resumen] |
| Hansen, Erharter et al. (2024) | **Clase Q (A–E2)** y valor de Q a partir de MWD | ~500 000 taladros, 15 túneles noruegos | Datos de perforación (MWD) | KNN, Extra Trees, votación, CNN | Exactitud balanceada 0,86 (6 clases), 0,90 (3 clases), 0,95 (binaria) | 75/25 + 5-fold, **SMOTE dentro del pipeline**; partición aleatoria, no por túnel | Un dataset de MWD con tipo de roca sí es público | [V1 texto completo] |
| Katuwal, Panthi y Basnet (2024/25) | Clase RMR a partir de datos de TBM (Himalaya) | 6879 ciclos | Operación de la TBM | LR, SVM, DT, RF, KNN, XGBoost, stacking | Exactitud 92 % (RF y stacking) | Aleatoria 80/20 + SMOTE | No | [V1 resumen + texto parcial] |
| Lawal et al. (2025) | **Valor de Q** | 356 mediciones de campo (Great Dyke, Zimbabue) | RQD, Jn, Jr, Ja, Jw, SRF | ANN, RF, GB + explicabilidad | R², diagramas de Taylor | Aleatoria 70/15/15 | No | [V1 resumen + texto parcial] |
| Zvarivadza et al. (2025) | RMR a partir de los parámetros de Q | Mediciones de campo emparejadas | Parámetros de Q | Aprendizaje profundo | "Alta exactitud" | — | — | [V2 + resumen] |
| Liu, Ku y Wu (2025) | Clase RMR con menos parámetros | **Base sintética** para entrenar + 41 casos reales | Parámetros RMR | RF + optimización bayesiana | "100 %" en los 41 casos reales | — | A pedido | [V1 resumen + texto parcial] |
| Liang et al. (2025/26) | Estabilidad de tajeos (base de Mawdesley revisada) | Base de Mawdesley | N', RH, etc. | Stacking (10 algoritmos) + Optuna | Exactitud 0,869 pero **kappa 0,576**, F1 0,786, AUC 0,894 | Partición + 5-fold CV | A pedido | [V1 resumen + texto parcial] |
| Paixao, Rogers y de Jesus (2025) | Gráfico de estabilidad *propio del sitio* con datos desbalanceados | Base de tajeos de una mina | Variables elegidas por importancia por permutación | Modelos probabilísticos + ML, SMOTE | — | — | — | [V2 + resumen] |
| Morgenroth, Perras y Khan (2022) | Fluencia del revestimiento (Cigar Lake) | Estaciones de 1 m de un túnel de 164 m | Geología, congelamiento, clase de sostenimiento, desplazamiento | CNN | — | — | No | [V2] |

Revisiones útiles como marco: Morgenroth, Khan y Perras (2019) [V2 + resumen] y Suorineni (2010) sobre el gráfico de estabilidad [V2 + resumen].

### 1.2 Trampas metodológicas documentadas

1. **Fuga espacial entre tramos vecinos.** Los frentes o ciclos consecutivos de una misma labor son casi copias unos de otros. Si se reparten al azar entre entrenamiento y prueba, el modelo "predice" el vecino que ya vio. Erharter y Marcher (2021) [V2 + resumen] muestran que los pronósticos de datos de TBM "con alta exactitud" suelen ser versiones retrasadas de la misma señal, sin valor predictivo. En Hansen et al. (2024) [V1] el mejor modelo fue KNN, y los autores lo explican porque "condiciones parecidas se agrupan": es una señal de autocorrelación espacial con una partición que no se hizo por túnel. Chang et al. (2022) [V1] obtienen F1 = 1,00 con 133 frentes de un solo túnel. La solución está documentada fuera de la geomecánica: validación cruzada por bloques o grupos (Roberts et al., 2017 [V2 + resumen]; Valavi et al., 2019 [V2]). Ploton et al. (2020) [V2] muestran cómo la validación espacial destruye exactitudes que parecían altas. Kapoor y Narayanan (2023) [V2] dan una taxonomía general de fugas de datos.
2. **Aprender la fórmula.** Predecir RMR a partir de sus propios componentes, o Q a partir de RQD, Jn, Jr, Ja, Jw y SRF, solo vuelve a aprender una suma o un producto que ya es determinista. Así se explican errores como el 0,279 % de Brousset et al. (2023) o el R² alto de Lawal et al. (2025). Entrenar con **datos sintéticos generados con la propia tabla RMR** (Liu, Ku y Wu, 2025) tiene el mismo problema. Para el módulo, eso no aporta nada: la librería ya calcula RMR y Q de forma exacta.
3. **Clases desbalanceadas y métricas engañosas.** Liang et al. (2025) reportan una exactitud de 0,87 pero un kappa de 0,58. Adoko et al. (2021) señalan que la clase minoritaria ("hundido") es la que peor se predice. Hansen et al. (2024) usan un modelo ficticio de base (exactitud 0,43 y exactitud balanceada 0,17) para mostrar cuánto infla la exactitud simple. Lo que se debe reportar es la exactitud balanceada, el F1 macro, el kappa ponderado (Cohen, 1968 [V2]) y la sensibilidad (*recall*) por clase.
4. **SMOTE mal usado.** Aplicarlo antes de partir los datos filtra información sintética hacia la prueba. Hansen et al. (2024) lo aplican correctamente, dentro del pipeline. Además, si el objetivo es una **probabilidad calibrada de falla**, sobremuestrear distorsiona las probabilidades (van den Goorbergh et al., 2022 [V2]). Es preferible no rebalancear y fijar el umbral según el costo.
5. **Conjuntos de prueba diminutos.** Hu et al. (2022) prueban con 16 casos: un solo acierto o error mueve la exactitud en 6 puntos.
6. **Ruido en la etiqueta.** El RMR y el Q tienen variabilidad entre observadores. Hansen et al. (2024) muestran que los errores se concentran en clases vecinas, por casos fronterizos, y que agrupar clases sube la exactitud balanceada de 0,86 a 0,90. Palmström y Broch (2006) [V2] y Elmo y Stead (2020) [V2] discuten el uso incorrecto y la subjetividad de las clasificaciones. Pells et al. (2017) [V2] cuestionan el RQD como variable.
7. **Extrapolación.** Las redes fallan fuera del rango de entrenamiento (Adoko et al., 2021, lo dicen de forma explícita). Hace falta un control del dominio de aplicabilidad.
8. **La práctica pasada como etiqueta.** El sostenimiento instalado depende de la clase de roca que se evaluó. Un modelo entrenado con "lo instalado" reproduce las decisiones del pasado, no las óptimas. Las fallas observadas también dependen del sostenimiento que se eligió (sesgo de selección). Ningún artículo de la tabla trata este problema de forma explícita. Es la razón principal para separar el modelo de práctica del modelo de desempeño (sección 7).

---

## 2. Calibración de correlaciones propias (RMR–Q, RMR–GSI, Q–GSI)

### 2.1 Qué dice la literatura

- Las correlaciones son **propias de cada sitio** y no equivalentes entre sistemas. Goel, Jethwa y Paithankar (1996) [V2] proponen correlacionar índices "reducidos" (RCR y N, con SRF = 1) en lugar de RMR y Q completos. Tzamos y Sofianos (2007) [V2] comparan cuatro sistemas a través de sus índices de fábrica. Ranasooriya y Nikraz (2009) [V2] cuestionan la confiabilidad de la correlación lineal RMR–ln Q. Laderian y Abaspoor (2012) [V2] ajustan más de 800 estaciones en Irán. Park, Go y Oh (2025) [V2 + resumen] encuentran correlaciones débiles y diferentes en zonas de falla. Somodi et al. (2021) [V2 + resumen] muestran que la relación RMR–GSI depende de la litología. Rehman et al. (2018a, 2018b) [V2] revisan la evolución y las limitaciones de ambos sistemas.
- Para el GSI, la cuantificación de Hoek, Carter y Diederichs (2013) [V2, sin DOI, ARMA] y la de Cai et al. (2004) [V2] permiten calcularlo a partir de la condición de juntas y del RQD o el volumen de bloque. Las limitaciones están en Marinos, Marinos y Hoek (2005) [V2] y la versión vigente en Hoek y Brown (2019) [V2].
- **Lo más cercano a lo que buscas**: Ching et al. (2020) [V2 + resumen] compilan **ROCKMass/9/5876**, con 5876 casos de 225 estudios que incluyen RQD, RMR, Q, GSI, Em, etc. Comparan cuatro maneras de construir un modelo de transformación "cuasi propio del sitio" con pocos datos locales: regresión múltiple probabilística, hibridación, **modelo bayesiano jerárquico** y similitud. **El jerárquico bayesiano fue el más eficaz.** La misma escuela tiene el método de Ching y Phoon (2019) [V2] para distribuciones multivariadas propias del sitio.

### 2.2 Métodos estadísticos recomendados

| Objetivo | Método | Por qué | Referencia |
|---|---|---|---|
| **Predecir** Y a partir de una X medida (por ejemplo, RMR a partir de ln Q) | Regresión ordinaria (OLS) de Y sobre X, con **intervalo de predicción** y no solo R² | Para predecir con una X observada con error, la regresión de Y dado X es el estimador correcto. No hay que "corregirla". | Warton et al. (2006) [V2] |
| **Relación estructural** o conversión en los dos sentidos | Regresión de Deming u ortogonal (errores en ambas variables), o eje mayor reducido (RMA) como descripción | El RMR y el Q tienen error de medición. La pendiente OLS se atenúa y no se puede invertir. RMA solo equivale a errores en variables si la razón de varianzas de error coincide con la razón de varianzas observadas. | Warton et al. (2006) [V2]; Carroll et al. (2006) [V2]; Fontanari y Santos (2026) [V2] |
| Razón de varianzas de error | Estimarla con **mapeos repetidos** del mismo tramo por dos geólogos | Sin esa razón, Deming es arbitrario | Carroll et al. (2006) [V2] |
| Incertidumbre de los coeficientes | **Bootstrap por grupos** (remuestrear labores o zonas, no filas) | Respeta la dependencia espacial | Efron y Tibshirani (1994) [V2]; Roberts et al. (2017) [V2] |
| Pocos datos locales | **Bayesiano jerárquico**: global (ROCKMass) → litología o dominio → mina | Contrae hacia la relación global cuando hay pocos datos y se independiza cuando hay muchos | Ching et al. (2020) [V2 + resumen] |
| Promedios de RMR por zona | No promediar sin más; usar geoestadística | El RMR es no lineal, direccional y mezcla poblaciones | Egaña y Ortiz (2013) [V2 + resumen]; Pinheiro et al. (2016) [V2] |

### 2.3 Tamaño mínimo de muestra

La literatura geomecánica **no fija un mínimo** para estas correlaciones. Lo que sí está bien fundamentado viene de los modelos de predicción clínicos, que se pueden transferir porque el problema estadístico es el mismo:

- Riley et al. (2019a) [V2], para respuestas continuas, dan criterios para que la contracción (*shrinkage*) sea ≥ 0,9, el R² optimista sea pequeño y la varianza residual sea precisa. Riley et al. (2020) [V2] lo explican de forma práctica. El tamaño se **calcula**; no se adopta una cifra fija.
- **Propuesta de diseño (heurística mía, no de la literatura):** activar una correlación propia por dominio geotécnico solo con **≥ 30 pares de al menos 5 labores distintas**, y publicarla solo si el ancho del IC 95 % bootstrap de la pendiente es menor que un umbral configurable. Por debajo de eso, el modelo jerárquico se queda con la relación global y la marca como "no calibrada". Conviene confirmar esta regla con simulaciones sobre ROCKMass/9/5876.

---

## 3. Calibración de tablas de sostenimiento o de GSI con casos de falla y no falla

### 3.1 Antecedente directo: el gráfico de Mathews con regresión logística

- **Mawdesley, Trueman y Whiten (2001)** [V2 + resumen] amplían la base de Mathews a más de 400 casos y reemplazan las zonas trazadas a mano por **regresión logística**. Generan **contornos de isoprobabilidad** para cada estado (estable, falla, falla mayor) y así cuantifican el riesgo. Es el patrón que hay que copiar.
- Suorineni (2010) [V2 + resumen]: la confiabilidad del método depende del tamaño, la calidad y la consistencia de la base, y de que los factores se determinen siempre igual.
- Papaioanou y Suorineni (2016) [V2 + resumen]: gráfico de dilución con datos de 6 minas australianas, con **regresión logística y discriminación bayesiana por verosimilitud**.
- Mortazavi y Osserbay (2022) [V2 + resumen]: depuran la base (solo métodos sin ingreso de personal) y aplican regresión logística.
- Vallejos et al. (2024) [V2 + resumen], de la U. de Chile: **más de 600 casos chilenos** de tajeos por subniveles analizados con MineRoc y comparados con las bases de Mawdesley y Clark. Concluyen que las curvas de la literatura tienen un alcance limitado en Chile. Es un argumento directo a favor de calibrar por sitio.
- Paixao, Rogers y de Jesus (2025) [V2 + resumen]: metodología para un **gráfico de estabilidad propio del sitio** con datos desbalanceados, que reduce las variables a dos dimensiones para que siga siendo interpretable.
- Para luces de excavaciones con ingreso de personal (galerías, cruceros): la base de luz crítica de Wang et al. (2002) y los clasificadores de García-Gonzalo et al. (2016) y Goh et al. (2017, con regresión logística) [V2].

### 3.2 Cómo trasladarlo a las tablas Q y RMR

- La carta de sostenimiento Q es un plano (Q; De = luz/ESR) dividido en categorías (Grimstad y Barton, 1993 [NV]; NGI, 2015 [NV]). La **calibración propia** equivale a ajustar, en ese mismo plano, una regresión logística de P(falla | log Q, log De, categoría de sostenimiento). Luego se trazan las isoprobabilidades para cada categoría, exactamente como Mawdesley lo hizo en el plano (N', RH).
- Kim et al. (2019) [V2] estudian el **retrocálculo** de la calidad del macizo a partir del sostenimiento instalado (RMR y Q), lo que sirve para revisar la coherencia del histórico.
- **Actualización bayesiana**: Miranda, Gomes Correia y Ribeiro e Sousa (2009) [V2] actualizan parámetros geomecánicos con datos nuevos y cuantifican la incertidumbre. Feng y Jiménez (2015) [V2] seleccionan y actualizan modelos de forma bayesiana. Contreras, Brown y Ruest (2018) y Contreras y Brown (2019) [V2] hacen análisis bayesiano de datos y retroanálisis de fallas. Li et al. (2024) [V2 + resumen] actualizan el RMR delante del frente de forma secuencial. Mishra et al. (2019) [V2 + resumen] combinan el criterio de expertos con instrumentación en una red bayesiana para el riesgo de colapso de tajeos. En la práctica, esto significa usar como *prior* los coeficientes de la base global (o de Mawdesley) y actualizarlos con los casos de la mina a medida que llegan.
- **Lógica difusa**: Aydın (2004) [V2] y Samimi Namin, Rinne y Rafie (2015, SAIMM) [V2 + resumen] tratan la vaguedad de las entradas del RMR. Sirve para propagar la incertidumbre de la entrada, pero **no calibra contra fallas observadas**. Es mejor como opción secundaria.

### 3.3 Detalles que no se pueden omitir

- **Separación cuasi completa**: con pocas fallas, la regresión logística por máxima verosimilitud diverge. Se usa la corrección de Firth (Firth, 1993 [V2]) o *priors* débilmente informativos (Gelman et al., 2008 [V2]).
- **Eventos por variable**: la referencia clásica es 10 eventos por parámetro (Peduzzi et al., 1996 [V2]). Es insuficiente como regla única (van Smeden et al., 2019 [V2]). Lo que se usa son los criterios de Riley et al. (2019b) [V2]. Ejemplo de cálculo: con 5 % de fallas y 3 parámetros, 10 eventos por parámetro equivalen a 30 fallas, es decir, alrededor de 600 casos.
- **Exposición**: una labor que estuvo abierta 3 meses no equivale a una que estuvo abierta 3 años. Si existe la fecha, conviene incluir el tiempo de exposición (como desplazamiento o *offset*, o como modelo de supervivencia).
- **Monotonía**: a peor macizo o mayor luz, la probabilidad de falla no puede bajar. Con más sostenimiento, no puede subir. Esto se impone con coeficientes de signo restringido o con restricciones monótonas en el *boosting*. Es una propuesta de diseño, no está tomada de un artículo.

---

## 4. Explicabilidad e incertidumbre para el ingeniero

1. **Primero un modelo interpretable, no una caja negra explicada después.** Rudin (2019) [V2] argumenta que en decisiones de alto riesgo hay que usar modelos interpretables cuando rinden igual. En geomecánica, un logístico ordinal o binario con pocas variables, o un ábaco de isoprobabilidad, suele rendir igual que un *boosting* con menos de 1000 casos (Hansen et al., 2024, encontraron que KNN superaba a modelos más complejos; Adoko et al., 2021, y Liang et al., 2025, no muestran ventajas grandes del *stacking* en kappa).
2. **Probabilidades calibradas.** Hay que reportar la curva de calibración, el error de Brier y la pendiente y el intercepto de calibración (Van Calster et al., 2019 [V2]; Niculescu-Mizil y Caruana, 2005 [V2]). Un árbol o una red no calibrados entregan "probabilidades" que no lo son.
3. **Conjuntos de predicción con cobertura garantizada.** La predicción conforme (Angelopoulos y Bates, 2023 [V2]) devuelve, por ejemplo, {clase III, clase IV} con 90 % de cobertura. **Advertencia:** la garantía supone intercambiabilidad. Con datos espaciales, la calibración se tiene que hacer con zonas que no se usaron en el entrenamiento.
4. **Intervalos**: posterior bayesiana para los modelos jerárquicos o logísticos, y bootstrap por grupos para los demás.
5. **Razones**: los coeficientes y las razones de probabilidades (*odds ratios*) en los modelos lineales; TreeSHAP para los de árboles (Lundberg et al., 2020 [V2]; Lundberg y Lee, 2017 [NV, NeurIPS, sin DOI]). Lawal et al. (2025) usan explicabilidad para Q.
6. **Ordinalidad**: las clases de sostenimiento están ordenadas. Conviene usar un logit acumulado (Bürkner y Vuorre, 2019 [V2]) o la descomposición de Frank y Hall (2001) [V2], y evaluar con kappa ponderado cuadrático. Confundir la clase III con la IV no es tan grave como confundir la I con la V.
7. **La decisión queda en manos del ingeniero**: la salida muestra la probabilidad de falla de *cada* opción de sostenimiento, el umbral que eligió el usuario, la opción más liviana que lo cumple, la alerta de extrapolación y un campo donde se registra la decisión final y su motivo. Esa decisión, junto con el desempeño posterior, alimenta la actualización bayesiana. Como guía de reporte, TRIPOD+AI (Collins et al., 2024 [V2]) es la lista de verificación más completa disponible para modelos de predicción con ML. Viene de la medicina, pero se aplica sin cambios de fondo. Steyerberg y Vergouwe (2014) [V2] proponen 7 pasos de desarrollo y un "ABCD" de validación.

---

## 5. Datasets públicos para pruebas

| Dataset | Contenido | n | Acceso | Uso en la librería | Marca |
|---|---|---|---|---|---|
| Adoko et al. (2021), anexo 1 / tabla 11 | N', RH y estado del tajeo (estable / inestable / hundido), 3 minas de Ghana | 225 | Artículo de acceso abierto, CC BY 4.0 | Prueba de regresión logística e isoprobabilidades estilo Mathews | [V1] |
| Wang, Milne y Pakalnis (2002), anexo | RMR, luz y estabilidad, 6 minas canadienses | 292 | Anexo del artículo (Trans. IMM A, de pago) | Prueba del gráfico de luz crítica | [V2 + resumen] |
| **ROCKMass/9/5876** (ISSMGE TC304, 304dB) | RQD, RMR, Q, GSI, Em, Eem, Edm, Ei, σci; 225 estudios de 67 países | 5876 | Página de bases de datos del TC304 (http://140.112.12.21/issmge/tc304.htm), contacto J. Ching | *Prior* global para las correlaciones RMR–Q–GSI | [V1 página TC304] |
| Shirdel (2025), Zenodo 10.5281/zenodo.17397696 | GSI y RMR ajustado, 3 formaciones, 2 minas (Alborz, Irán) | 134 | CC BY 4.0 | Prueba de la correlación RMR–GSI | [V1 registro]. **Cuidado:** no tiene revisión por pares y su "arXiv relacionado" (2401.12345) parece un marcador de posición |
| Hansen (2024), Zenodo 10.5281/zenodo.10358374 | MWD con etiqueta de tipo de roca, 15 túneles noruegos, con partición entrenamiento/prueba | ~4895 muestras de modelo | CC BY 4.0 | Prueba de **validación por túnel (grupos)**, no de Q | [V1 registro] |
| Chen y Yin (2019), Dryad 10.5061/dryad.7nh05k6 | Zonificación estructural y calidad del macizo | — | Dryad | Prueba de zonificación | [V1 registro] |
| Base extendida de Mathews (Mawdesley) | Más de 400 casos | >400 | Tabulada en la tesis de Mawdesley o en trabajos derivados; Liang et al. (2025) la revisaron | Prueba principal del modelo de desempeño | [NV] sobre su disponibilidad |
| Potvin (1988), tesis UBC (cIRcle, 10.14288/1.0081130) | Casos originales del gráfico de estabilidad modificado | — | cIRcle UBC | Histórico | [V2] |
| *No usar:* Zenodo 10.5281/zenodo.18704885 | RMR **sintético** | — | — | Solo como prueba unitaria de la fórmula | [V1 registro] |

En ninguna búsqueda (Zenodo, Mendeley, anexos) encontré un dataset público con **evaluación geomecánica + sostenimiento instalado + falla/no falla por tramo de labor**. Ese es el vacío que llenaría una mina dispuesta a publicar sus datos anonimizados. Para las pruebas de la librería, la vía realista es un generador sintético *con mecanismo conocido* (para comprobar que el pipeline recupera los parámetros) más las bases de Adoko, de Wang y la de Mathews para el desempeño, y ROCKMass para las correlaciones.

---

## 6. Tesis y trabajos peruanos y latinoamericanos

| Trabajo | Institución | Qué aporta | Límites | Marca |
|---|---|---|---|---|
| Brousset, Pehovaz, Quispe, Raymundo y Moguerza (2023), *Energy Reports* 9 | UPC (Perú) | ANN para clasificar el macizo en minas subterráneas peruanas; error de 0,279 % en el RMR | Con ese nivel de error, parece reaprender la fórmula del RMR a partir de sus componentes. El resumen no informa validación espacial ni datos públicos | [V2 + resumen] |
| "Propuesta de Red Neuronal para Caracterizar el Macizo Rocoso en una Mina Subterránea en el Centro del Perú" (archivo Castro_HK) | UPC, handle 10757/670755 | Entradas: condición de juntas, espaciamiento, RQD, agua, resistencia a compresión simple (RCS); salida: RMR; reporta 99 % | Mismo problema: las entradas son los componentes del RMR. No pude abrir el PDF (error 403); no tengo confirmados el autor, el año ni el asesor | [NV] (solo vi el resumen en un buscador) |
| Belizario-Calsin et al. (2020), IOP Conf. Ser. 758 | UPC (Perú) | Mathews + elementos finitos para tajeos en vetas angostas peruanas | No usa ML ni calibración estadística | [V2 + resumen] |
| Tesis UNSA: reactivación de la U. M. Buena Vista Rey de Reyes (Caravelí) | UNSA | RMR 39–53, GSI 30–50, Q 1,8–9,5; diseño del sostenimiento | Clásica, sin ML | [NV] (resumen en un buscador) |
| Egaña y Ortiz (2013), *J. GeoEngineering* 8(3) | U. de Chile | Simulación geoestadística del RMR y su incertidumbre (Chuquicamata Subterránea); advierte que el RMR es no lineal, direccional y multipoblacional | No predice sostenimiento | [V2 + resumen] |
| Pinheiro, Vallejos, Miranda y Emery (2016), *Eng. Geol.* 205 | U. de Chile / U. Minho | Mapa de la heterogeneidad del RMR por simulación | No predice sostenimiento | [V2] |
| Vallejos et al. (2024), ARMA | U. de Chile | Base chilena de más de 600 casos de tajeos; muestra que las curvas de la literatura no se transfieren tal cual | La base no es pública; es una ponencia de congreso | [V2 + resumen] |
| Santos, Lana y Pereira (2020, 2021) | UFOP (Brasil) | Clase RMR con menos variables (NB, RF, ANN, SVM) | Submuestreo aleatorio y base de tajo abierto | [V1 resumen] |
| Santos, Amaral, Mendonça y Silva (2020), REM 73(3) | Brasil | Estabilidad de tajeos con IA | — | [V2] |
| Pereira, L. C. (2020), tesis doctoral | UFV (Brasil) | 473 sondajes (Vazante); el RF señala al RQD como la variable más influyente; modelo 3D por kriging | Sin métricas de validación formales | [V1 resumen del repositorio] |
| Lins, P. G. C., *Classificação de maciços rochosos: uma abordagem por redes neurais* | USP São Carlos (tesis doctoral) | Expresa Q y RMR como representaciones neuronales locales | Es antigua; el año del DOI (2016) parece ser el de la carga al repositorio | [V2] |
| Paixao, Rogers y de Jesus (2025) | Autores brasileños (U. de Utah) | Gráfico de estabilidad propio del sitio con datos desbalanceados | SMOTE (ver la trampa 4) | [V2 + resumen] |

**Hallazgo negativo:** no encontré tesis de la UNI, la PUCP, la UNMSM ni la PUC Chile que predigan **sostenimiento** con ML usando el histórico de falla/no falla. Los trabajos con ML de la UNI y la PUCP que aparecieron son de voladura. Ojo con la cobertura: los repositorios de la UPC, la PUC Chile y la USP devolvieron error 403 o 400 a la descarga automática, así que esta búsqueda no es exhaustiva.

---

## 7. Recomendación de arquitectura para el módulo

### 7.1 Unidad de dato y controles de ingesta

- **Una fila = un tramo evaluado de una labor**, con `id_labor`, `zona/dominio`, `nivel`, `fecha`, coordenadas (pueden ser locales o desplazadas), tipo de labor, luz, ESR, profundidad, componentes RMR/Q/GSI, sostenimiento instalado (en clase ordinal y en detalle), resultado (falla sí/no, tipo, fecha) y tiempo de exposición.
- **Recalcular** RMR, Q y GSI a partir de sus componentes y marcar las discrepancias con el valor registrado. Es la auditoría más barata y la más útil.
- Detectar **tramos duplicados o casi duplicados** y avisar que esos registros no se pueden tratar como independientes.

### 7.2 Modelos que se ofrecen por defecto, por niveles

| Nivel | Qué hace | Modelo por defecto | Opción secundaria (*challenger*) |
|---|---|---|---|
| 0. Línea base (siempre activa) | Tablas originales: carta Q (NGI, 2015), RMR89, GSI/Hoek–Brown | Determinista | — |
| 1. Correlaciones propias | RMR–Q, RMR–GSI, Q–GSI | OLS con intervalo de predicción + Deming + **bootstrap por grupos**; **jerárquico bayesiano** con *prior* de ROCKMass si hay pocos datos | — |
| 2. Modelo de práctica | Qué sostenimiento instala la mina en cada condición (auditoría de consistencia, **no recomienda**) | **Logit ordinal acumulado** | *Gradient boosting* con restricciones monótonas |
| 3. Modelo de desempeño | P(falla \| macizo, De, tipo de labor, profundidad, sostenimiento, exposición) | **Logística bayesiana** (Firth o *prior* débil), ábaco de isoprobabilidad en el plano (log Q, log De) por categoría de sostenimiento | *Boosting* monótono calibrado, solo si supera al logístico en validación agrupada |
| Recomendación | El sostenimiento más liviano con P(falla) ≤ umbral elegido por el usuario | Regla de decisión explícita, con conjunto conforme e intervalo | — |

No incluir por defecto: redes neuronales profundas, SMOTE, entrenamiento con datos sintéticos de tablas, ni modelos que predigan RMR o Q a partir de sus propios componentes.

### 7.3 Validación obligatoria (sin esto, no hay recomendación)

1. **CV agrupada por labor** y **dejar una zona fuera** (*leave-one-zone-out*), más una **prueba temporal**: entrenar con los años más antiguos y probar con el último. Está prohibida la partición aleatoria por fila; si el usuario la pide, se reporta solo como "optimista".
2. Todo el preprocesamiento (escalado, imputación, selección de variables) va **dentro** del pipeline y se ajusta en cada pliegue.
3. Métricas mínimas: exactitud balanceada, F1 macro, **kappa ponderado cuadrático**, sensibilidad por clase, Brier, curva y pendiente de calibración y, para la falla, AUC y precisión-sensibilidad (PR).
4. **Comparación obligatoria** contra la línea base (nivel 0) y contra un clasificador ficticio. Si el intervalo bootstrap de la mejora incluye cero, la librería **no recomienda** y lo dice.
5. Alerta de **extrapolación**: entradas fuera de la envolvente de los datos de entrenamiento (rango o distancia de Mahalanobis).
6. Reporte en el formato de TRIPOD+AI.

### 7.4 Datos mínimos antes de recomendar (propuesta para confirmar con simulación)

- **Nivel 1**: ≥ 30 pares por dominio y de ≥ 5 labores; por debajo de eso, solo el modelo jerárquico contraído hacia la relación global.
- **Nivel 2**: ≥ 10 registros por clase de sostenimiento en ≥ 5 labores independientes.
- **Nivel 3**: ≥ 10 fallas por parámetro estimado (Peduzzi) y que se cumplan los criterios de Riley (2019b); ≥ 3 zonas para poder hacer *leave-one-zone-out*. Con menos fallas, se reporta la curva global (Mawdesley o la base que corresponda) actualizada de forma bayesiana y se marca como "no calibrada al sitio".

Estos umbrales son decisiones de diseño razonadas, no números publicados. Lo que sí está publicado es el método para calcularlos (Riley et al., 2019a, 2019b, 2020).

### 7.5 Salida que ve el ingeniero

Para cada opción de sostenimiento: P(falla) con su intervalo, el conjunto conforme de clases, las 3 razones principales (coeficientes o SHAP), la alerta de extrapolación, el nivel de calibración ("global", "parcial" o "propio del sitio") y el campo **"decisión del ingeniero"**. Ese campo, junto con el desempeño posterior, actualiza el modelo.

---

## Bibliografía (APA 7)

Adoko, A. C., Kunkyin-Saadaari, F., Mireku-Gyimah, D., & Imashev, A. Zh. (2022). A feasibility study on the implementation of neural network classifiers for open stope design. *Geotechnical and Geological Engineering, 40*(2), 677–696. https://doi.org/10.1007/s10706-021-01915-8 [V1]

Angelopoulos, A. N., & Bates, S. (2023). Conformal prediction: A gentle introduction. *Foundations and Trends in Machine Learning, 16*(4). https://doi.org/10.1561/2200000101 [V2]

Aydın, A. (2004). Fuzzy set approaches to classification of rock masses. *Engineering Geology, 74*(3–4), 227–245. https://doi.org/10.1016/j.enggeo.2004.03.011 [V2]

Barton, N. (2002). Some new Q-value correlations to assist in site characterisation and tunnel design. *International Journal of Rock Mechanics and Mining Sciences, 39*(2), 185–216. https://doi.org/10.1016/S1365-1609(02)00011-4 [V2]

Barton, N., Lien, R., & Lunde, J. (1974). Engineering classification of rock masses for the design of tunnel support. *Rock Mechanics, 6*(4), 189–236. https://doi.org/10.1007/BF01239496 [V2]

Belizario-Calsin, M., Condori-Cardenas, R., Pehovaz-Alvarez, H., Raymundo, C., & Perez, M. (2020). Empirical and numerical finite-element-based model to improve narrow vein mine design in Peruvian mining. *IOP Conference Series: Materials Science and Engineering, 758*(1), 012014. https://doi.org/10.1088/1757-899X/758/1/012014 [V2]

Brousset, J., Pehovaz, H., Quispe, G., Raymundo, C., & Moguerza, J. M. (2023). Rock mass classification method applying neural networks to minimize geomechanical characterization in underground Peruvian mines. *Energy Reports, 9*, 376–386. https://doi.org/10.1016/j.egyr.2023.05.246 [V2]

Bürkner, P.-C., & Vuorre, M. (2019). Ordinal regression models in psychology: A tutorial. *Advances in Methods and Practices in Psychological Science, 2*(1). https://doi.org/10.1177/2515245918823199 [V2]

Cai, M., Kaiser, P. K., Uno, H., Tasaka, Y., & Minami, M. (2004). Estimation of rock mass deformation modulus and strength of jointed hard rock masses using the GSI system. *International Journal of Rock Mechanics and Mining Sciences, 41*(1), 3–19. https://doi.org/10.1016/S1365-1609(03)00025-X [V2]

Carroll, R. J., Ruppert, D., Stefanski, L. A., & Crainiceanu, C. M. (2006). *Measurement error in nonlinear models: A modern perspective* (2.ª ed.). Chapman & Hall/CRC. https://doi.org/10.1201/9781420010138 [V2]

Chang, J., Huang, H., Zhang, D., Yang, T., & Xing, Z. (2022). Machine learning-based prediction of drilling and blasting tunnel initial support patterns. En *Proceedings of the 8th International Symposium for Geotechnical Safety and Risk (ISGSR)* (pp. 565–570). https://doi.org/10.3850/978-981-18-5182-7_00-08-013.xml [V1]

Chawla, N. V., Bowyer, K. W., Hall, L. O., & Kegelmeyer, W. P. (2002). SMOTE: Synthetic minority over-sampling technique. *Journal of Artificial Intelligence Research, 16*, 321–357. https://doi.org/10.1613/jair.953 [V2]

Chen, Q., & Yin, T. (2019). Integration of homogeneous structural region identification and rock mass quality classification. *Royal Society Open Science, 6*(1), 181353. https://doi.org/10.1098/rsos.181353 [V2]

Ching, J., Li, K.-H., Phoon, K.-K., & Weng, M.-C. (2018). Generic transformation models for some intact rock properties. *Canadian Geotechnical Journal, 55*(12), 1702–1741. https://doi.org/10.1139/cgj-2017-0537 [V2]

Ching, J., & Phoon, K.-K. (2019). Constructing site-specific multivariate probability distribution model using Bayesian machine learning. *Journal of Engineering Mechanics, 145*(1). https://doi.org/10.1061/(ASCE)EM.1943-7889.0001537 [V2]

Ching, J., & Phoon, K.-K. (2025). Overview and future prospect of ISSMGE TC304 open-access databases (304dB). *Intelligent Transportation Infrastructure, 4*. https://doi.org/10.1093/iti/liaf004 [V2]

Ching, J., Phoon, K.-K., Ho, Y.-H., & Weng, M.-C. (2021). Quasi-site-specific prediction for deformation modulus of rock mass. *Canadian Geotechnical Journal, 58*(7), 936–951. https://doi.org/10.1139/cgj-2020-0168 [V2 + resumen]

Cohen, J. (1968). Weighted kappa: Nominal scale agreement provision for scaled disagreement or partial credit. *Psychological Bulletin, 70*(4), 213–220. https://doi.org/10.1037/h0026256 [V2]

Collins, G. S., Moons, K. G. M., Dhiman, P., Riley, R. D., Beam, A. L., Van Calster, B., Ghassemi, M., Liu, X., et al. (2024). TRIPOD+AI statement: Updated guidance for reporting clinical prediction models that use regression or machine learning methods. *BMJ, 385*, e078378. https://doi.org/10.1136/bmj-2023-078378 [V2]

Contreras, L.-F., & Brown, E. T. (2019). Slope reliability and back analysis of failure with geotechnical parameters estimated using Bayesian inference. *Journal of Rock Mechanics and Geotechnical Engineering, 11*(3), 628–643. https://doi.org/10.1016/j.jrmge.2018.11.008 [V2]

Contreras, L.-F., Brown, E. T., & Ruest, M. (2018). Bayesian data analysis to quantify the uncertainty of intact rock strength. *Journal of Rock Mechanics and Geotechnical Engineering, 10*(1), 11–31. https://doi.org/10.1016/j.jrmge.2017.07.008 [V2]

Efron, B., & Tibshirani, R. J. (1994). *An introduction to the bootstrap*. Chapman & Hall/CRC. https://doi.org/10.1201/9780429246593 [V2]

Egaña, M., & Ortiz, J. M. (2013). Assessment of RMR and its uncertainty by using geostatistical simulation in a mining project. *Journal of GeoEngineering, 8*(3), 83–90. https://doi.org/10.6310/jog.2013.8(3).2 [V2 + resumen]

Elmo, D., & Stead, D. (2020). Disrupting rock engineering concepts: Is there such a thing as a rock mass digital twin and are machines capable of learning rock mechanics? En *Slope Stability 2020* (pp. 565–576). Australian Centre for Geomechanics. https://doi.org/10.36487/ACG_repo/2025_34 [V2]

Erharter, G. H., & Marcher, T. (2021). On the pointlessness of machine learning based time delayed prediction of TBM operational data. *Automation in Construction, 121*, 103443. https://doi.org/10.1016/j.autcon.2020.103443 [V2 + resumen]

Feng, X., & Jimenez, R. (2015). Estimation of deformation modulus of rock masses based on Bayesian model selection and Bayesian updating approach. *Engineering Geology, 199*, 19–27. https://doi.org/10.1016/j.enggeo.2015.10.002 [V2]

Firth, D. (1993). Bias reduction of maximum likelihood estimates. *Biometrika, 80*(1), 27–38. https://doi.org/10.1093/biomet/80.1.27 [V2]

Fontanari, J. F., & Santos, M. (2026). The same problem by different names: Unifying regression dilution and regression to the mean. *Mathematics, 14*(12), 2052. https://doi.org/10.3390/math14122052 [V2]

Frank, E., & Hall, M. (2001). A simple approach to ordinal classification. En *Machine Learning: ECML 2001* (LNCS 2167). Springer. https://doi.org/10.1007/3-540-44795-4_13 [V2]

García-Gonzalo, E., Fernández-Muñiz, Z., García Nieto, P. J., Bernardo Sánchez, A., & Menéndez Fernández, M. (2016). Hard-rock stability analysis for span design in entry-type excavations with learning classifiers. *Materials, 9*(7), 531. https://doi.org/10.3390/ma9070531 [V2 + resumen]

Gelman, A., Jakulin, A., Pittau, M. G., & Su, Y.-S. (2008). A weakly informative default prior distribution for logistic and other regression models. *The Annals of Applied Statistics, 2*(4), 1360–1383. https://doi.org/10.1214/08-AOAS191 [V2]

Goel, R. K., Jethwa, J. L., & Paithankar, A. G. (1996). Correlation between Barton's Q and Bieniawski's RMR—A new approach. *International Journal of Rock Mechanics and Mining Sciences & Geomechanics Abstracts, 33*(2), 179–181. https://doi.org/10.1016/0148-9062(95)00057-7 [V2]

Goh, A. T. C., Zhang, Y., Zhang, R., Zhang, W., & Xiao, Y. (2017). Evaluating stability of underground entry-type excavations using multivariate adaptive regression splines and logistic regression. *Tunnelling and Underground Space Technology, 70*, 148–154. https://doi.org/10.1016/j.tust.2017.07.013 [V2]

Grimstad, E., & Barton, N. (1993). Updating the Q-system for NMT. En *Proceedings of the International Symposium on Sprayed Concrete* (Fagernes). Norwegian Concrete Association. [NV]

Hansen, T. F., Erharter, G. H., Liu, Z., & Tørresen, J. (2024). A comparative study on machine learning approaches for rock mass classification using drilling data. *Applied Computing and Geosciences, 24*, 100199. https://doi.org/10.1016/j.acags.2024.100199 [V1: texto completo en arXiv:2403.10404]

Hansen, T. F., Liu, Z., & Tørresen, J. (2024). Predicting rock type from MWD tunnel data using a reproducible ML-modelling process. *Tunnelling and Underground Space Technology, 152*, 105843. https://doi.org/10.1016/j.tust.2024.105843 [V2 + resumen]. Dataset: https://doi.org/10.5281/zenodo.10358374 [V1]

He, H., & Garcia, E. A. (2009). Learning from imbalanced data. *IEEE Transactions on Knowledge and Data Engineering, 21*(9), 1263–1284. https://doi.org/10.1109/TKDE.2008.239 [V2]

Hoek, E., & Brown, E. T. (2019). The Hoek–Brown failure criterion and GSI – 2018 edition. *Journal of Rock Mechanics and Geotechnical Engineering, 11*(3), 445–463. https://doi.org/10.1016/j.jrmge.2018.08.001 [V2]

Hoek, E., Carter, T. G., & Diederichs, M. S. (2013). Quantification of the Geological Strength Index chart. En *47th US Rock Mechanics/Geomechanics Symposium* (ARMA 13-672). American Rock Mechanics Association. [V2, sin DOI]

Hou, S., Liu, Y., & Yang, Q. (2022). Real-time prediction of rock mass classification based on TBM operation big data and stacking technique of ensemble learning. *Journal of Rock Mechanics and Geotechnical Engineering, 14*(1), 123–143. https://doi.org/10.1016/j.jrmge.2021.05.004 [V2 + resumen]

Hu, J., Zhou, T., Ma, S., Yang, D., Guo, M., & Huang, P. (2022). Rock mass classification prediction model using heuristic algorithms and support vector machines: A case study of Chambishi copper mine. *Scientific Reports, 12*, 928. https://doi.org/10.1038/s41598-022-05027-y [V2 + resumen]

Huang, H., Wu, C., Zhou, M., Chen, J., Han, T., & Zhang, L. (2024). Rock mass quality prediction on tunnel faces with incomplete multi-source dataset via tree-augmented naive Bayesian network. *International Journal of Mining Science and Technology, 34*(3), 323–337. https://doi.org/10.1016/j.ijmst.2024.03.003 [V2 + resumen]

Kapoor, S., & Narayanan, A. (2023). Leakage and the reproducibility crisis in machine-learning-based science. *Patterns, 4*(9), 100804. https://doi.org/10.1016/j.patter.2023.100804 [V2]

Katuwal, T. B., Panthi, K. K., & Basnet, C. B. (2025). Machine learning approach for rock mass classification with imbalanced database of TBM tunnelling in Himalayan geology. *Rock Mechanics and Rock Engineering, 58*(10), 11293–11318. https://doi.org/10.1007/s00603-024-04212-x [V1 resumen + texto parcial]

Kim, J., Rehman, H., Ali, W., Naji, A. M., & Yoo, H. (2019). Weightage effect during back-calculation of rock-mass quality from the installed tunnel support in rock-mass rating and tunneling quality index system. *Applied Sciences, 9*(10), 2065. https://doi.org/10.3390/app9102065 [V2]

Korigov, S., Adoko, A. C., & Sengani, F. (2022). Unplanned dilution prediction in open stope mining: Developing new design charts using artificial neural network classifier. *Journal of Sustainable Mining, 21*(2), 157–168. https://doi.org/10.46873/2300-3960.1356 [V2 + resumen]

Laderian, A., & Abaspoor, M. A. (2012). The correlation between RMR and Q systems in parts of Iran. *Tunnelling and Underground Space Technology*. https://doi.org/10.1016/j.tust.2011.06.001 [V2]

Lawal, A. I., Zvarivadza, T., Onifade, M., Mulenga, F. K., & Khandelwal, M. (2025). Optimising tunnel support design with machine learning models. *Environmental Earth Sciences, 84*(21). https://doi.org/10.1007/s12665-025-12573-x [V1 resumen + texto parcial]

Li, X., Chen, Z., Tang, L., Chen, C., Li, T., Ling, J., Lu, Y., & Rui, Y. (2024). Predicting rock mass rating ahead of the tunnel face with Bayesian estimation. *Frontiers in Earth Science, 12*. https://doi.org/10.3389/feart.2024.1333117 [V2 + resumen]

Liang, W., Lu, P., Wang, M., & Mitri, H. S. (2026). Hybrid stacking model with Optuna optimization for open stope stability prediction. *Rock Mechanics and Rock Engineering, 59*(4), 4845–4869. https://doi.org/10.1007/s00603-025-05043-0 [V1 resumen + texto parcial]

Lins, P. G. C. (s. f.). *Classificação de maciços rochosos: uma abordagem por redes neurais* [Tesis doctoral, Universidade de São Paulo, Escola de Engenharia de São Carlos]. https://doi.org/10.11606/T.18.2016.tde-08032016-114433 [V2; el año de defensa no está confirmado]

Liu, C.-Y., Ku, C.-Y., & Wu, T.-Y. (2025). Advancing rock mass classification using machine learning approach. *Bulletin of Engineering Geology and the Environment, 84*(12). https://doi.org/10.1007/s10064-025-04585-5 [V1 resumen + texto parcial]

Liu, Q., Wang, X., Huang, X., & Yin, X. (2020). Prediction model of rock mass class using classification and regression tree integrated AdaBoost algorithm based on TBM driving data. *Tunnelling and Underground Space Technology, 106*, 103595. https://doi.org/10.1016/j.tust.2020.103595 [V2 + resumen]

Lundberg, S. M., Erion, G., Chen, H., DeGrave, A., Prutkin, J. M., Nair, B., Katz, R., Himmelfarb, J., Bansal, N., & Lee, S.-I. (2020). From local explanations to global understanding with explainable AI for trees. *Nature Machine Intelligence, 2*, 56–67. https://doi.org/10.1038/s42256-019-0138-9 [V2]

Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. En *Advances in Neural Information Processing Systems 30* (NeurIPS 2017). [NV, sin DOI]

Marinos, V., Marinos, P., & Hoek, E. (2005). The geological strength index: Applications and limitations. *Bulletin of Engineering Geology and the Environment, 64*(1), 55–65. https://doi.org/10.1007/s10064-004-0270-5 [V2]

Mawdesley, C., Trueman, R., & Whiten, W. J. (2001). Extending the Mathews stability graph for open-stope design. *Mining Technology (Trans. IMM A), 110*(1), 27–39. https://doi.org/10.1179/mnt.2001.110.1.27 [V2 + resumen]

Miranda, T., Gomes Correia, A., & Ribeiro e Sousa, L. (2009). Bayesian methodology for updating geomechanical parameters and uncertainty quantification. *International Journal of Rock Mechanics and Mining Sciences, 46*(7), 1144–1153. https://doi.org/10.1016/j.ijrmms.2009.03.008 [V2]

Mishra, R., Kiuru, R., Uotinen, L., Janiszewski, M., & Rinne, M. (2019). Combining expert opinion and instrumentation data using Bayesian networks to carry out stope collapse risk assessment. En *Mining Geomechanical Risk 2019* (pp. 85–96). Australian Centre for Geomechanics. https://doi.org/10.36487/ACG_rep/1905_02_Mishra [V2 + resumen]

Morgenroth, J., Khan, U. T., & Perras, M. A. (2019). An overview of opportunities for machine learning methods in underground rock engineering design. *Geosciences, 9*(12), 504. https://doi.org/10.3390/geosciences9120504 [V2 + resumen]

Morgenroth, J., Perras, M. A., & Khan, U. T. (2022). A convolutional neural network approach for predicting tunnel liner yield at Cigar Lake Mine. *Rock Mechanics and Rock Engineering, 55*(5), 2821–2843. https://doi.org/10.1007/s00603-021-02563-3 [V2]

Mortazavi, A., & Osserbay, B. (2022). The consolidated Mathews stability graph for open stope design. *Geotechnical and Geological Engineering, 40*(5), 2409–2424. https://doi.org/10.1007/s10706-021-02034-0 [V2 + resumen]

NGI. (2015). *Using the Q-system: Rock mass classification and support design* (Handbook). Norwegian Geotechnical Institute. [NV]

Niculescu-Mizil, A., & Caruana, R. (2005). Predicting good probabilities with supervised learning. En *Proceedings of the 22nd International Conference on Machine Learning* (pp. 625–632). https://doi.org/10.1145/1102351.1102430 [V2]

Paixao, L. de A. G., Rogers, W. P., & de Jesus, E. B. (2025). A novel methodology to develop mining stope stability graphs on imbalanced datasets using probabilistic approaches. *Mining, 5*(2), 24. https://doi.org/10.3390/mining5020024 [V2 + resumen]

Palmström, A., & Broch, E. (2006). Use and misuse of rock mass classification systems with particular reference to the Q-system. *Tunnelling and Underground Space Technology, 21*(6), 575–593. https://doi.org/10.1016/j.tust.2005.10.005 [V2]

Papaioanou, A., & Suorineni, F. T. (2016). Development of a generalised dilution-based stability graph for open stope design. *Mining Technology, 125*(2), 121–128. https://doi.org/10.1080/14749009.2015.1131940 [V2 + resumen]

Park, J.-S., Go, Y.-W., & Oh, T.-M. (2025). Evaluating the relationship between RMR and Q-system for improved classification of faulted rocks and weak rocks. *Scientific Reports, 15*, 17121. https://doi.org/10.1038/s41598-025-01985-1 [V2 + resumen]

Peduzzi, P., Concato, J., Kemper, E., Holford, T. R., & Feinstein, A. R. (1996). A simulation study of the number of events per variable in logistic regression analysis. *Journal of Clinical Epidemiology, 49*(12), 1373–1379. https://doi.org/10.1016/S0895-4356(96)00236-3 [V2]

Pells, P. J. N., Bieniawski, Z. T., Hencher, S. R., & Pells, S. E. (2017). Rock quality designation (RQD): Time to rest in peace. *Canadian Geotechnical Journal, 54*(6), 825–834. https://doi.org/10.1139/cgj-2016-0012 [V2]

Pereira, L. C. (2020). *O uso da geoestatística para elaboração de modelos geomecânicos multidimensionais* [Tesis doctoral, Universidade Federal de Viçosa]. https://www.locus.ufv.br/handle/123456789/27865 [V1 resumen del repositorio]

Pinheiro, M., Vallejos, J., Miranda, T., & Emery, X. (2016). Geostatistical simulation to map the spatial heterogeneity of geomechanical parameters: A case study with rock mass rating. *Engineering Geology, 205*, 93–103. https://doi.org/10.1016/j.enggeo.2016.03.003 [V2]

Ploton, P., Mortier, F., Réjou-Méchain, M., Barbier, N., Picard, N., Rossi, V., Dormann, C., Cornu, G., et al. (2020). Spatial validation reveals poor predictive performance of large-scale ecological mapping models. *Nature Communications, 11*, 4540. https://doi.org/10.1038/s41467-020-18321-y [V2]

Potvin, Y. (1988). *Empirical open stope design in Canada* [Tesis doctoral, University of British Columbia]. https://doi.org/10.14288/1.0081130 [V2]

Qi, C., Fourie, A., Du, X., & Tang, X. (2018). Prediction of open stope hangingwall stability using random forests. *Natural Hazards, 92*(2), 1179–1197. https://doi.org/10.1007/s11069-018-3246-7 [V1 resumen]

Ranasooriya, J., & Nikraz, H. (2009). Reliability of the linear correlation of Rock Mass Rating (RMR) and Tunnelling Quality Index (Q). *Australian Geomechanics, 44*(2), 47–54. [V2, sin DOI]

Rehman, H., Ali, W., Naji, A. M., Kim, J., Abdullah, R. A., & Yoo, H. (2018a). Review of rock-mass rating and tunneling quality index systems for tunnel design: Development, refinement, application and limitation. *Applied Sciences, 8*(8), 1250. https://doi.org/10.3390/app8081250 [V2]

Rehman, H., Naji, A. M., Kim, J., & Yoo, H. (2018b). Empirical evaluation of rock mass rating and tunneling quality index system for tunnel support design. *Applied Sciences, 8*(5), 782. https://doi.org/10.3390/app8050782 [V2 + resumen]

Riley, R. D., Ensor, J., Snell, K. I. E., Harrell, F. E., Martin, G. P., Reitsma, J. B., Moons, K. G. M., Collins, G., & van Smeden, M. (2020). Calculating the sample size required for developing a clinical prediction model. *BMJ, 368*, m441. https://doi.org/10.1136/bmj.m441 [V2]

Riley, R. D., Snell, K. I. E., Ensor, J., Burke, D. L., Harrell, F. E., Moons, K. G. M., & Collins, G. S. (2019a). Minimum sample size for developing a multivariable prediction model: Part I – Continuous outcomes. *Statistics in Medicine, 38*(7), 1262–1275. https://doi.org/10.1002/sim.7993 [V2]

Riley, R. D., Snell, K. I. E., Ensor, J., Burke, D. L., Harrell, F. E., Moons, K. G. M., & Collins, G. S. (2019b). Minimum sample size for developing a multivariable prediction model: Part II – Binary and time-to-event outcomes. *Statistics in Medicine, 38*(7), 1276–1296. https://doi.org/10.1002/sim.7992 [V2]

Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S., Elith, J., Guillera-Arroita, G., Hauenstein, S., Lahoz-Monfort, J. J., et al. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography, 40*(8), 913–929. https://doi.org/10.1111/ecog.02881 [V2 + resumen]

Rudin, C. (2019). Stop explaining black box machine learning models for high stakes decisions and use interpretable models instead. *Nature Machine Intelligence, 1*, 206–215. https://doi.org/10.1038/s42256-019-0048-x [V2]

Samimi Namin, F., Rinne, M., & Rafie, M. (2015). Uncertainty determination in rock mass classification when using FRMR software. *Journal of the Southern African Institute of Mining and Metallurgy, 115*(11), 1073–1082. https://doi.org/10.17159/2411-9717/2015/v115n11a12 [V2 + resumen]

Santos, A. E. M., Amaral, T. K. M., Mendonça, G. A., & Silva, D. F. S. (2020). Open stope stability assessment through artificial intelligence. *REM – International Engineering Journal, 73*(3), 395–401. https://doi.org/10.1590/0370-44672020730012 [V2]

Santos, A. E. M., Lana, M. S., & Pereira, T. M. (2021a). Rock mass classification by multivariate statistical techniques and artificial intelligence. *Geotechnical and Geological Engineering, 39*(3), 2409–2430. https://doi.org/10.1007/s10706-020-01635-5 [V1 resumen]

Santos, A. E. M., Lana, M. S., & Pereira, T. M. (2021b). Evaluation of machine learning methods for rock mass classification. *Neural Computing and Applications, 34*(6), 4633–4642. https://doi.org/10.1007/s00521-021-06618-y [V1 resumen]

Shirdel, B. (2025). *Field dataset for GSI–RMR_adj correlation in Central Alborz rock masses* [Conjunto de datos]. Zenodo. https://doi.org/10.5281/zenodo.17397696 [V1 registro]

Somodi, G., Bar, N., Kovács, L., Arrieta, M., Török, Á., & Vásárhelyi, B. (2021). Study of rock mass rating (RMR) and geological strength index (GSI) correlations in granite, siltstone, sandstone and quartzite rock masses. *Applied Sciences, 11*(8), 3351. https://doi.org/10.3390/app11083351 [V2 + resumen]

Steyerberg, E. W., & Vergouwe, Y. (2014). Towards better clinical prediction models: Seven steps for development and an ABCD for validation. *European Heart Journal, 35*(29), 1925–1931. https://doi.org/10.1093/eurheartj/ehu207 [V2]

Suorineni, F. T. (2010). The stability graph after three decades in use: Experiences and the way forward. *International Journal of Mining, Reclamation and Environment, 24*(4), 307–339. https://doi.org/10.1080/17480930.2010.501957 [V2 + resumen]

Tzamos, S., & Sofianos, A. I. (2007). A correlation of four rock mass classification systems through their fabric indices. *International Journal of Rock Mechanics and Mining Sciences, 44*(4), 477–495. https://doi.org/10.1016/j.ijrmms.2006.08.003 [V2]

Valavi, R., Elith, J., Lahoz-Monfort, J. J., & Guillera-Arroita, G. (2019). blockCV: An R package for generating spatially or environmentally separated folds for k-fold cross-validation of species distribution models. *Methods in Ecology and Evolution, 10*(2), 225–232. https://doi.org/10.1111/2041-210X.13107 [V2]

Vallejos, J., Retamal, F., Barberán, A., & Velásquez, J. (2024). Development of Chilean open stope empirical stability database using MineRoc and their comparison with literature. En *58th US Rock Mechanics/Geomechanics Symposium* (ARMA 24-1114). https://doi.org/10.56952/ARMA-2024-1114 [V2 + resumen]

Van Calster, B., McLernon, D. J., van Smeden, M., Wynants, L., & Steyerberg, E. W. (2019). Calibration: The Achilles heel of predictive analytics. *BMC Medicine, 17*, 230. https://doi.org/10.1186/s12916-019-1466-7 [V2]

van den Goorbergh, R., van Smeden, M., Timmerman, D., & Van Calster, B. (2022). The harm of class imbalance corrections for risk prediction models: Illustration and simulation using logistic regression. *Journal of the American Medical Informatics Association, 29*(9), 1525–1534. https://doi.org/10.1093/jamia/ocac093 [V2]

van Smeden, M., Moons, K. G. M., de Groot, J. A. H., Collins, G. S., Altman, D. G., Eijkemans, M. J. C., & Reitsma, J. B. (2019). Sample size for binary logistic prediction models: Beyond events per variable criteria. *Statistical Methods in Medical Research, 28*(8), 2455–2474. https://doi.org/10.1177/0962280218784726 [V2]

Wang, J., Milne, D., & Pakalnis, R. (2002). Application of a neural network in the empirical design of underground excavation spans. *Mining Technology (Trans. IMM A), 111*(1), 73–81. https://doi.org/10.1179/mnt.2002.111.1.73 [V2 + resumen]

Warton, D. I., Wright, I. J., Falster, D. S., & Westoby, M. (2006). Bivariate line-fitting methods for allometry. *Biological Reviews, 81*(2), 259–291. https://doi.org/10.1017/S1464793106007007 [V2]

Zvarivadza, T., Lawal, A. I., Onifade, M., Mulenga, F. K., Kwon, S., & Khandelwal, M. (2025). Deep learning-powered rock mass classification: Predicting RMR from Q-system parameters with high accuracy. *Rock Mechanics Bulletin, 4*(4), 100219. https://doi.org/10.1016/j.rockmb.2025.100219 [V2 + resumen]

---

## Notas de alcance

- Verifiqué en OpenAlex el volumen y las páginas de los trabajos de estadística (Peduzzi, van den Goorbergh, Valavi, van Smeden, Angelopoulos, Ploton, Steyerberg y Niculescu-Mizil). En unos pocos casos completé de memoria los volúmenes o las páginas que faltaban (por ejemplo, el número de *Patterns* o la página de TRIPOD+AI): el DOI y el título sí están verificados.
- Muchos artículos de Springer y Elsevier son de pago: de ellos solo leí el resumen y los fragmentos visibles. Los tamaños de dataset que faltan en la tabla 1.1 ("—") no aparecían en esos textos.
- Esta sesión no leyó ni imprimió datos de clientes ni carpetas de zona. Todo salió de la web pública.
