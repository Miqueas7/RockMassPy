# Simulación de los mínimos de datos del módulo predictivo

Fase 4C, tarea 13 (plan R6 y R11). Este documento confirma o corrige con simulación los mínimos de datos de cada
nivel (`MIN_*` de `python/rockmasspy/history.py`). **Todas las cifras son de la simulación, con históricos
sintéticos de mecanismo conocido; ninguna sale de una mina.** Cada mínimo propuesto es una **decisión de diseño
respaldada por simulación**, no un número publicado (`MODELOS_SOSTENIMIENTO.md` §2.3, §3.3 y §7.4).

- Script: [`scripts/simulacion_minimos.py`](scripts/simulacion_minimos.py).
- Resultados: [`simulacion_minimos.csv`](simulacion_minimos.csv), en formato largo: una métrica por fila, con
  éxitos, n e IC 95 %.
- Comando: `simulacion_minimos.py --seed 20261105 --reps 50 --reps-l1 200 --n-boot 500`. Tomó 16 min en la laptop.
- Versión de la librería: `fase-4bc` en d52d0e6.
  - Nivel 3 con tasa de falla constante (Poisson con offset ln t) y generador con tiempos de falla exponenciales.
  - Validación: labor y zona fuera, cero pliegues fallidos, ≤ 1 % de réplicas descartadas y temporal como no
    inferioridad.
  - `recommend` no elige si el tramo extrapola, si el IC de β_rank toca el 0 o si hay cotas activas en la calidad
    o la luz.

## 1. Diseño de la simulación

### 1.1 Principio común

- Los históricos salen de `synthetic_history` (`predictive/synthetic.py`), que tiene efectos aleatorios por labor y
  por zona. Así la validación agrupada y el bootstrap por labor tienen sentido.
- **La mina «recién alcanza» la celda.** Se sortea un pozo de 4 zonas y labores de ~12 tramos. Después se agregan
  labores enteras, en orden aleatorio, hasta cumplir la condición de la celda: por ejemplo, 10 tramos del tipo más
  escaso, o 60 eventos de la clase menor. Las labores quedan desbalanceadas, como en una mina real, y el conteo de
  la celda es el mismo que mide `audit_history`.
- **Sin el corte del mínimo vigente.** Dentro del proceso del script, los mínimos bajan a 1
  (`correlations.MIN_*` y `history.MIN_EVENTS_PER_PARAMETER_LEVEL3`). Así se mide qué hace la regla de validación
  por sí sola con 15 pares o con 5 eventos por parámetro. La librería no se modifica.
  `MIN_TRAMOS_PER_TYPE_LEVEL2` no se toca: también es una regla de `recommend`.
- `n_boot` = 500 en todos los bootstraps.
- IC 95 %:
  - las tasas por réplica llevan el de Wilson;
  - las que juntan eventos de una misma réplica (tramos nuevos, pares tramo × tipo) llevan uno por bootstrap de
    réplicas, porque esos eventos no son independientes.

### 1.2 Nivel 1 (correlaciones propias)

- Par `rmr_from_q` para toda la mina. Verdad: RMR = 9·ln Q + 44, con efecto de labor (desviación 3) y ruido
  (desviación 4).
- Celdas: 15, 30 y 60 pares × 3, 5 y 8 labores, con los pares repartidos por turnos. 200 réplicas por celda.
- Métricas:
  - cobertura del IC 95 % bootstrap por labor de la pendiente;
  - tasa «site»: IC dentro de ±25 % de la pendiente OLS, signo de la global y ≤ 10 % de réplicas descartadas;
  - error absoluto medio (EAM) de la pendiente OLS y de la bayesiana;
  - ancho relativo del IC.
- El *prior* es la global del núcleo para RMR89 (`RmrFromQ_Huang2026`, pendiente ≈ 6.7). **No coincide** con la
  verdad, que es 9, a propósito: así se ve si un *prior* desviado daña.

### 1.3 Nivel 2 (auditoría de la práctica)

- Celdas: 5, 10 y 20 tramos del tipo instalado más escaso (los 5 tipos presentes) × práctica coherente o con
  incoherencia 0.5. Con 0.5 la práctica ignora el macizo: los coeficientes verdaderos de ln Q y ln De son 0.
  50 réplicas por celda.
- Métricas:
  - veredicto «coherent» para ln Q, para ln De y para los dos;
  - falso «incoherent», que es cualquier «practice incoherent…»;
  - cobertura del conjunto conforme al 90 % en **labores nuevas**, sobre un histórico aparte de 2 zonas y
    20 labores;
  - tamaño medio del conjunto.

### 1.4 Nivel 3 (desempeño y recomendación)

- **Parámetros:** 6 (ln Q, ln De, rango, profundidad y 2 indicadores de tipo de labor). Por eso 5, 10 y 20 eventos
  por parámetro son 30, 60 y 120 eventos de la clase menor.
- **Con efecto real** (`site_effect=True`):
  - Prevalencias de 10 % y 25 %, con `fail_beta0` calibrado por bisección (−7.37 y −6.09; la prevalencia
    observada quedó en 9.7–10.7 % y 26–27.5 %).
  - Para cada réplica, 100 tramos nuevos de labores y zonas nuevas. Sus efectos de zona y de labor se sortean
    aparte con la desviación verdadera (0.4 y 0.5).
  - Umbral fijo de 10 % y horizonte fijo H = 365 días.
  - P verdadera **condicional**: 1 − exp(−λ·H), con los efectos de zona y de labor del tramo. P **marginal**: el
    promedio de la condicional sobre esos efectos, que es lo que un modelo sin efectos aleatorios puede estimar.
  - **Demasiado liviana:** el tipo elegido tiene la P verdadera condicional por encima del umbral. Se informa
    también con la P marginal.
  - **Sin compuertas:** se elige el tipo más liviano cuyo límite superior cumple el umbral, sin calibración, sin
    β_rank, sin cotas, sin extrapolación y sin historia. Sirve para ver qué aportan las compuertas.
- **Nulo de frontera** (`site_effect=False`, la tasa depende solo de la categoría NGI):
  - El modelo del sitio se arma en el script con las variables del sitio **más la categoría**, libre de signo.
    Se usan `exponential_hazard_map_fit`, `validate` y la devianza de Poisson, con el ficticio de tasa constante y
    la línea base de la categoría sola, tal como en `performance.py`. Así el modelo anida a la línea base.
  - Recomendación falsa: la validación recomienda y el ajuste final converge. Se mide también la versión con β_rank
    identificado y sin cotas en calidad o luz.
  - Como referencia, la tasa de «site» de `fit_performance` en el mismo nulo («mal especificado»).

## 2. Resultados del nivel 1

200 réplicas por celda; IC 95 % de Wilson.

| Pares | Labores | Cobertura del IC 95 % de la pendiente | «site» | EAM OLS | EAM bayes | Ancho rel. del IC |
|---:|---:|---|---:|---:|---:|---:|
| 15 | 3 | 0.830 [0.772, 0.876] | 0.760 | 0.58 | 0.58 | 0.30 |
| 15 | 5 | 0.885 [0.833, 0.922] | 0.805 | 0.60 | 0.57 | 0.29 |
| 15 | 8 | 0.880 [0.828, 0.918] | 0.860 | 0.58 | 0.56 | 0.30 |
| 30 | 3 | 0.845 [0.788, 0.889] | 0.945 | 0.44 | 0.43 | 0.19 |
| 30 | 5 | 0.860 [0.805, 0.901] | 0.990 | 0.41 | 0.40 | 0.18 |
| 30 | 8 | 0.890 [0.839, 0.926] | 1.000 | 0.38 | 0.37 | 0.19 |
| 60 | 3 | 0.800 [0.739, 0.850] | 0.990 | 0.37 | 0.37 | 0.12 |
| 60 | 5 | 0.840 [0.783, 0.884] | 1.000 | 0.33 | 0.33 | 0.14 |
| 60 | 8 | 0.920 [0.874, 0.950] | 1.000 | 0.29 | 0.29 | 0.14 |

Lectura:

- **El IC bootstrap por labor es optimista:** cubre 80–85 % con 3 labores, 84–89 % con 5 y 88–92 % con 8, frente
  al 95 % nominal. Lo que lo mejora son las labores, no los pares: con 3 labores, 60 pares cubren peor que 15. Es
  el sesgo conocido del bootstrap de percentiles con pocos grupos.
- La regla «site» no es la que limita desde 30 pares: pasa en 94.5–100 %. Con 15 pares falla en 14–24 % de las
  réplicas, por IC anchos.
- El EAM de la pendiente baja 30 % de 15 a 30 pares y solo 15 % más de 30 a 60.
- El bayesiano empata con la OLS o gana un poco con 15 pares (0.56–0.58), aunque su *prior* está desviado en
  2.3 puntos de pendiente. La fuerza por defecto (desviación de 50 % de la pendiente global) no daña.

## 3. Resultados del nivel 2

50 réplicas por celda. «Tramos» es el total medio y «lab. mín.» son las labores medias del tipo con menos labores.

**Práctica coherente**

| Por tipo | Tramos | Lab. mín. | «coherent» ln Q | «coherent» ln De (= los dos) | Falso «incoherent» | Cobertura conforme 90 % | Tamaño del conjunto |
|---:|---:|---:|---:|---|---:|---|---:|
| 5 | 59 | 2.8 | 0.96 | 0.36 [0.24, 0.50] | 0/50 | 0.933 [0.918, 0.946] | 3.5 |
| 10 | 101 | 5.1 | 0.98 | 0.56 [0.42, 0.69] | 0/50 | 0.901 [0.886, 0.916] | 3.1 |
| 20 | 160 | 9.1 | 1.00 | 0.80 [0.67, 0.89] | 0/50 | 0.910 [0.900, 0.920] | 3.0 |

**Incoherencia 0.5 (la práctica ignora el macizo)**

| Por tipo | Tramos | Lab. mín. | Falso «incoherent» | Cobertura conforme 90 % | Tamaño del conjunto |
|---:|---:|---:|---|---|---:|
| 5 | 77 | 3.4 | 0.08 [0.03, 0.19] (4/50) | 0.929 [0.913, 0.943] | 4.3 |
| 10 | 127 | 6.3 | 0.02 [0.004, 0.105] (1/50) | 0.923 [0.913, 0.933] | 4.2 |
| 20 | 242 | 12.0 | 0.02 [0.004, 0.105] (1/50) | 0.920 [0.909, 0.931] | 4.2 |

Lectura:

- El signo de ln Q sale casi siempre (96–100 %). **El de ln De es el que pide datos:** 36 % con 5 por tipo, 56 %
  con 10 y 80 % con 20. Cuando no se detecta, el veredicto es «not significant», nunca «coherent».
- **El conjunto conforme cumple su 90 % en labores nuevas en todas las celdas** (0.90–0.93): no es lo que limita.
  Cuando la práctica ignora el macizo, el conjunto se agranda a 4.2–4.3 de 5 tipos y deja de informar, que es lo
  correcto.
- El falso «incoherent» es 8 % con 5 por tipo y 2 % con 10 y con 20. Junto en las tres celdas da 6/150 = 4 %
  [1.8 %, 8.5 %], cerca del 5 % esperado si los IC de Wald fueran exactos.

## 4. Resultados del nivel 3

50 réplicas por celda. «Elige» y «demasiado liviana» se cuentan sobre los 100 tramos nuevos de cada réplica
(5000 por celda). Entre corchetes va el IC por bootstrap de réplicas y entre paréntesis los conteos.

### 4.1 Con efecto real: potencia, coberturas y elección

| Prevalencia | Eventos/parám. | Tramos | Labores | «site» | Cob. IC 95 % ln Q / ln De / rango | Cob. IC 90 % P marginal | Cob. IC 90 % P condicional |
|---:|---:|---:|---:|---|---|---|---|
| 10 % | 5 | 313 | 26 | 0.02 (1/50) | 0.94 / 0.98 / 0.96 | 0.862 [0.825, 0.900] | 0.690 |
| 10 % | 10 | 660 | 55 | 0.10 (5/50) | 0.92 / 0.96 / 0.90 | 0.838 [0.798, 0.879] | 0.567 |
| 10 % | 20 | 1293 | 108 | 0.50 (25/50) | 0.92 / 0.92 / 0.94 | 0.797 [0.744, 0.841] | 0.464 |
| 25 % | 5 | 127 | 11 | 0.00 (0/50) | 0.94 / 1.00 / 0.90 | 0.862 [0.817, 0.897] | 0.723 |
| 25 % | 10 | 232 | 19 | 0.04 (2/50) | 0.82 / 0.94 / 0.90 | 0.790 [0.749, 0.835] | 0.542 |
| 25 % | 20 | 472 | 39 | 0.22 (11/50) | 0.84 / 0.94 / 0.86 | 0.777 [0.735, 0.817] | 0.451 |

| Prevalencia | Eventos/parám. | Elige | No elige | Demasiado liviana (P condicional) | Ídem (P marginal) | Sin compuertas (P condicional) |
|---:|---:|---|---|---|---|---|
| 10 % | 5 | 0.011 (55/5000) | 0.989 | 0.000 (0/55) | 0.018 (1/55) | 0.079 [0.050, 0.114] (244/3076) |
| 10 % | 10 | 0.073 (363/5000) | 0.927 | **0.072** [0.007, 0.187] (26/363) | 0.036 (13/363) | 0.112 [0.077, 0.149] (433/3881) |
| 10 % | 20 | 0.397 (1985/5000) | 0.603 | **0.105** [0.065, 0.148] (208/1985) | 0.067 (133/1985) | 0.100 [0.073, 0.130] (397/3973) |
| 25 % | 5 | 0.000 (0/5000) | 1.000 | sin elecciones | sin elecciones | 0.158 [0.084, 0.238] (153/966) |
| 25 % | 10 | 0.011 (57/5000) | 0.989 | **0.281** [0.250, 0.320] (16/57) | 0.228 (13/57) | 0.113 [0.071, 0.157] (162/1433) |
| 25 % | 20 | 0.091 (457/5000) | 0.909 | **0.206** [0.104, 0.297] (94/457) | 0.074 (34/457) | 0.140 [0.098, 0.183] (272/1945) |

Motivos de no elegir en los modelos «site»:

- «β_rank no identificado» y «cota activa en calidad o luz»: 0 % en todas las celdas.
- «El tramo extrapola»: 2–13 %.
- «Ningún tipo elegible cumple el umbral» (incluye los tipos sin historia suficiente): 14–60 %.

El resto de los «no elige» viene de modelos que no son «site».

### 4.2 Nulo de frontera

| Prevalencia | Eventos/parám. | Tramos | Labores | Recomendación falsa | Ídem con β_rank identificado | «site» del modelo de la librería (mal especificado) |
|---:|---:|---:|---:|---|---|---|
| 10 % | 5 | 272 | 22 | 0/50 [0, 0.071] | 0/50 | 0/50 |
| 10 % | 10 | 555 | 46 | 0/50 [0, 0.071] | 0/50 | 0/50 |
| 10 % | 20 | 1104 | 92 | 0/50 [0, 0.071] | 0/50 | 0/50 |
| 25 % | 5 | 120 | 10 | 0/50 [0, 0.071] | 0/50 | 0/50 |
| 25 % | 10 | 214 | 18 | 0/50 [0, 0.071] | 0/50 | 0/50 |
| 25 % | 20 | 447 | 37 | 0/50 [0, 0.071] | 0/50 | 0/50 |

Junto: **0 de 300, IC 95 % [0 %, 1.3 %]**. El tamaño real de la regla está muy por debajo del 5 %.

### 4.3 Lectura

1. **La regla de validación es muy conservadora.** No recomienda nunca en el nulo de frontera: 0/300, ≤ 1.3 %. Con
   efecto real, la potencia es baja: con el mínimo vigente (10 eventos por parámetro, 60 de la clase menor) llega a
   «site» en 10 % (prevalencia 10 %) y 4 % (prevalencia 25 %). Recién con 20 por parámetro sube a 50 % y 22 %.
   Exigir que ganen la partición por labor **y** la de zona fuera, contra el ficticio **y** la línea base, con
   0 pliegues fallidos, compra seguridad frente a la recomendación falsa a costa de potencia.
2. **La potencia depende de las labores, no solo de los eventos.** Con los mismos 20 eventos por parámetro, la
   prevalencia de 25 % llega con 39 labores (22 % de «site») y la de 10 % con 108 (50 %). Contar solo la clase
   menor subestima lo que hace falta cuando las fallas son frecuentes.
3. **La métrica que más importa queda alta: la recomendación demasiado liviana va de 7 % a 28 %.** El caso de 28 %
   tiene solo 2 modelos «site». Un tipo elegido con el límite superior del 90 % bajo 10 % tiene, en el tramo real,
   una P verdadera sobre 10 % en 1 de cada 10 elecciones (prevalencia 10 %, 20 por parámetro) y en 1 de cada 5
   (prevalencia 25 %). La causa principal es el **efecto de labor y de zona**, que el modelo no puede conocer en una
   labor nueva: desviación 0.64 en log λ, un factor de ≈ 1.9 en la tasa.
   - El intervalo de P cubre 78–86 % de la P marginal, bajo el 90 % nominal y cada vez peor con más datos: es un
     sesgo que no se achica, porque Laplace ignora la correlación dentro de labor y zona.
   - Cubre solo 45–72 % de la P condicional.
   - Las compuertas reducen **cuántas** veces se elige, no **cuán seguras** son las elecciones: sin compuertas la
     tasa es parecida (8–16 %).
4. Las coberturas de los coeficientes están cerca del 95 %, salvo ln Q con prevalencia 25 % (0.82–0.84). Las cotas
   en calidad o luz no se activaron con efecto real, y β_rank quedó siempre identificado en los modelos «site».

## 5. Mínimos propuestos

Cada uno es una **decisión de diseño respaldada por simulación**. No cambié las constantes de `history.py`: decide
el orquestador.

| Constante | Actual | Propuesto | Justificación |
|---|---:|---:|---|
| `MIN_PAIRS_LEVEL1` | 30 | **30 (se confirma)** | Desde 30 la regla «site» pasa en 94.5–100 % y el EAM ya bajó 30 % frente a 15. Duplicar a 60 gana 15 %. Con 15, 14–24 % de las réplicas quedan inestables. |
| `MIN_LABORS_LEVEL1` | 5 | **5 (se confirma; 8 es mejor)** | Con 3 labores la cobertura del IC cae a 80–85 %. Con 5 es 84–89 % y con 8, 88–92 %. Subir a 8 mejora la cobertura, pero no la lleva al 95 %: el sesgo es del método. |
| `MIN_TRAMOS_PER_TYPE_LEVEL2` | 10 | **10 (se confirma)** | Con 10 se detecta ln Q en 98 % y ln De en 56 %; lo no detectado sale como «not significant». El falso «incoherent» baja de 8 % (con 5) a 2 %. El conjunto conforme ya cubre. |
| `MIN_LABORS_PER_TYPE_LEVEL2` | 5 | **5 (se confirma)** | Una mina que llega a 10 por tipo tiene en promedio 5.1 labores en su tipo más escaso: las dos condiciones van juntas. Con 5 por tipo no pasa de 2.8. |
| `MIN_EVENTS_PER_PARAMETER_LEVEL3` | 10 | **10 (se confirma como piso de «not_calibrated»)** | El mínimo no es lo que protege: la regla de validación no recomienda en el nulo con ningún tamaño (0/300) y casi nunca con 5 por parámetro (≤ 2 %). Subirlo a 20 no baja la tasa demasiado liviana (sigue en 10–21 %); solo pasaría casos «partial» a «not_calibrated». Hay que decir que con 10 por parámetro el modelo llega a «site» en 4–10 % de las minas: para esperarlo en la mitad hacen falta ~20 por parámetro y ~100 labores. |
| `MIN_ZONES_LEVEL3` | 3 | **3 (no se probó)** | Todas las celdas usaron un pozo de 4 zonas. La simulación no lo confirma ni lo corrige. |

## 6. Riesgos y propuestas para el orquestador

1. **Recomendación demasiado liviana de 10–21 % con suficiente información** (7 % con pocos «site»). Es el riesgo
   principal. Propuesta, por decidir: que el intervalo de P de un tramo nuevo incluya la variabilidad entre labores
   y entre zonas (intervalo de predicción para una labor nueva, con la varianza del efecto estimada o con un
   inflado conservador). Si no, el ingeniero debe saber que el umbral es para la labor promedio, no para la labor
   que tiene delante.
2. **Potencia baja del nivel 3.** Con el mínimo vigente casi nunca se llega a «site». Si se quiere más potencia sin
   perder tamaño, hay margen: el tamaño real es ≤ 1.3 % frente a la meta de 5 %. Por ejemplo, exigir la zona fuera
   como no inferioridad, como la temporal, en lugar de superioridad. Habría que volver a simular.
3. **IC optimistas por agrupamiento.** Afecta al bootstrap de percentiles del nivel 1 (84–89 % con 5 labores), al
   intervalo de Laplace de P en el nivel 3 (78–86 % de la marginal) y, en menor medida, a ln Q en el nivel 3 con
   prevalencia alta. Son propiedades de los métodos y no se arreglan subiendo mínimos.

## 7. Limitaciones

- **El generador es una simplificación:**
  - efectos aleatorios normales;
  - relaciones lineales en ln Q y ln De;
  - tasa de falla constante en el tiempo (exponencial);
  - un solo mecanismo de práctica;
  - 3 tipos de labor y 5 tipos de sostenimiento;
  - 4 zonas;
  - sin errores de registro.

  Una mina real puede tener efectos de labor más fuertes, dominios mezclados, tasas que cambian con la edad de la
  labor o una práctica que cambió con los años.
- **La prevalencia y el efecto de una mina real pueden ser distintos.** Las tasas de detección dependen del tamaño
  del efecto verdadero:
  - nivel 1: pendiente de RMR = 9;
  - nivel 2: γ_lnDe = 1.5;
  - nivel 3: β_q = −0.5, β_de = 1.0, β_rank = −0.6 y desviación de 0.64 del efecto de labor y zona.

  Con efectos más chicos, los mismos mínimos detectan menos. Con efectos de labor más grandes, la tasa demasiado
  liviana sube.
- El umbral (10 %) y el horizonte (365 días) son fijos. Con otro umbral cambian las tasas de elección y de
  elección demasiado liviana.
- El *prior* del nivel 1 está desviado de la verdad en 2.3 puntos de pendiente. Un *prior* más fuerte o más
  desviado podría dañar con pocos datos.
- 50 réplicas por celda en los niveles 2 y 3 dan IC de ±10–14 puntos en las tasas intermedias, y la tasa
  demasiado liviana con pocos modelos «site» es muy incierta (por ejemplo, 2 modelos en la celda de 25 % y 10 por
  parámetro). Bastan para ordenar las celdas, no para afinar un punto de corte.
