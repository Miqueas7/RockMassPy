# Simulación de los mínimos de datos del módulo predictivo

Fase 4C, tarea 13 (plan R6 y R11). Este documento confirma o corrige con simulación los mínimos de datos de cada
nivel (`MIN_*` de `python/rockmasspy/history.py`). **Todas las cifras son de la simulación, con históricos
sintéticos de mecanismo conocido; ninguna sale de una mina.** Cada mínimo propuesto es una **decisión de diseño
respaldada por simulación**, no un número publicado (`MODELOS_SOSTENIMIENTO.md` §2.3, §3.3 y §7.4).

- Script: [`scripts/simulacion_minimos.py`](scripts/simulacion_minimos.py) (semilla y réplicas por argumento).
- Resultados de los niveles 1 y 2: [`simulacion_minimos_niveles_1_2.csv`](simulacion_minimos_niveles_1_2.csv)
  (formato largo: una métrica por fila, con su IC 95 %).
- Versión de la librería: rama `fase-4bc` en a96deaf (validación con labor y zona fuera, cero pliegues fallidos,
  ≤ 1 % de réplicas descartadas y la temporal como no inferioridad).
- Comando de los niveles 1 y 2: `simulacion_minimos.py --levels 1,2 --seed 20261105 --reps 50 --reps-l1 200
  --n-boot 500`. Tiempo: unos 9 min en la laptop.

**Estado:** los niveles 1 y 2 están corridos con la versión final. El nivel 3 está **pendiente**: su modelo pasa a
una tasa de falla constante (Poisson con offset ln t, P(falla en H) = 1 − exp(−λH)) y el generador pasa a sortear
tiempos de falla. Se corre cuando ese cambio esté en `fase-4bc`.

## 1. Diseño de la simulación

### 1.1 Principio común

- Los históricos salen de `synthetic_history` (`predictive/synthetic.py`), que tiene efectos aleatorios por labor y
  por zona. Por eso la validación agrupada y el bootstrap por labor tienen sentido.
- **La mina «recién alcanza» la celda.** Se sortea un pozo grande de labores y se agregan labores enteras, en orden
  aleatorio, hasta que se cumple la condición de la celda (por ejemplo, 10 tramos del tipo más escaso). Así las
  labores quedan desbalanceadas, como en una mina real, y el conteo de la celda es el que mide la preparación de
  `audit_history`.
- **Sin el corte del mínimo vigente.** Dentro del proceso del script, los mínimos de la librería bajan a 1
  (`correlations.MIN_*` y `performance.MIN_EVENTS_PER_PARAMETER_LEVEL3`). Así se ve qué hace la regla de validación
  por sí sola con 15 pares o con 5 eventos por parámetro, aunque hoy el mínimo lo impediría. La librería no se toca.
- `n_boot` = 500 en todos los bootstraps. Las tasas llevan el IC 95 % de Wilson. Las tasas que juntan eventos de
  una misma réplica (cobertura del conjunto conforme o de P(falla)) llevan un IC por bootstrap de réplicas, porque
  esos eventos no son independientes.

### 1.2 Nivel 1 (correlaciones propias)

- Par `rmr_from_q` para toda la mina (`group_by=None`). Verdad del generador: RMR = 9·ln Q + 44, con efecto de
  labor (desviación 3) y ruido (desviación 4).
- Celdas: 15, 30 y 60 pares × 3, 5 y 8 labores. Los pares se reparten por turnos entre las labores. 200 réplicas
  por celda.
- Métricas:
  - cobertura del IC 95 % bootstrap por labor de la pendiente frente a la verdadera (9);
  - tasa de estado «site»: IC dentro de ±25 % de la pendiente OLS, signo de la global y ≤ 10 % de réplicas
    descartadas;
  - error absoluto medio (EAM) de la pendiente OLS y de la bayesiana;
  - ancho relativo del IC.
- El *prior* bayesiano es la global del núcleo para RMR89 (`RmrFromQ_Huang2026`, pendiente ≈ 6.7). **No coincide
  con la verdad** (9) a propósito: así se ve si un *prior* desviado daña con pocos datos.

### 1.3 Nivel 2 (auditoría de la práctica)

- Celdas: 5, 10 y 20 tramos del tipo instalado más escaso (los 5 tipos presentes) × práctica coherente
  (`practice_incoherence=0`) o incoherente al 0.5. Con 0.5 la práctica ignora el macizo: los coeficientes
  verdaderos de ln Q y ln De son 0. 50 réplicas por celda.
- Métricas:
  - con práctica coherente, la tasa de veredicto «coherent» para ln Q, para ln De y para los dos;
  - en los dos escenarios, la tasa de falso «incoherent», que es cualquier veredicto «practice incoherent…»;
  - la cobertura del conjunto conforme al 90 % en **labores nuevas**, sobre un histórico aparte de 2 zonas y
    20 labores con la misma verdad;
  - el tamaño medio del conjunto.

### 1.4 Nivel 3 (desempeño y recomendación), pendiente

El diseño está armado en el script y se adapta al modelo nuevo antes de correrlo:

- **Con efecto real** (`site_effect=True`):
  - Celdas: 5, 10 y 20 eventos de la clase menor por parámetro × prevalencias de 10 % y 25 %. La prevalencia se
    ajusta con `fail_beta0`, calibrado por bisección en un pozo grande.
  - Métricas: la tasa de «site» (potencia); la cobertura de los IC de los coeficientes; la cobertura del intervalo
    al 90 % de P(falla) contra la P verdadera del mecanismo, marginal sobre los efectos de labor y zona porque el
    tramo nuevo es de una labor y una zona nuevas; y la **tasa de recomendación demasiado liviana**, que es el tipo
    elegido con P verdadera sobre el umbral.
  - Umbral fijo de 10 % y exposición fija de 365 días, en 100 tramos nuevos por réplica.
  - Se informa también la misma tasa **sin la compuerta de calibración**, para ver de qué protege la regla.
- **Nulo de frontera** (`site_effect=False`, la P depende solo de la categoría NGI):
  - El modelo del sitio se arma en el script con las variables del sitio **más la categoría**, con `validate`
    y `compare_models` tal como los usa `performance.py`. Así anida a la línea base (categoría + exposición) y la
    regla se mide en su tamaño real.
  - Métrica: la tasa de recomendación falsa. La meta es quedar cerca o por debajo de 5 %.
  - Como referencia, también la tasa de «site» del modelo de la librería en el mismo nulo («nulo mal especificado»).
    Ahí el plan advierte que sale ≈ 0 por mala especificación.

Un hallazgo de la corrida corta con el modelo logístico anterior, ya descartado, que conviene vigilar con el modelo
nuevo: la cobertura del intervalo de P(falla) **bajaba al crecer la muestra** (≈ 0.9 con pocos eventos, 0.65–0.78
con 20 por parámetro, 3 réplicas). Es la firma de un sesgo que no se achica: el intervalo de Laplace ignora la
incertidumbre del efecto de zona, y con 4 zonas la media de sus efectos no se cancela. En esa misma corrida la
compuerta de calibración evitó todas las elecciones demasiado livianas (0 de 206), contra 0 % a 32 % por celda sin compuerta.
Son solo 3 réplicas: es un indicio, no un resultado.

## 2. Resultados del nivel 1

200 réplicas por celda. Entre corchetes, el IC 95 % de Wilson.

| Pares | Labores | Cobertura IC 95 % de la pendiente | Tasa «site» | EAM OLS | EAM bayes | Ancho rel. del IC |
|---:|---:|---|---:|---:|---:|---:|
| 15 | 3 | 0.815 [0.755, 0.863] | 0.775 | 0.57 | 0.58 | 0.28 |
| 15 | 5 | 0.895 [0.845, 0.930] | 0.790 | 0.62 | 0.58 | 0.30 |
| 15 | 8 | 0.890 [0.839, 0.926] | 0.850 | 0.59 | 0.59 | 0.31 |
| 30 | 3 | 0.820 [0.761, 0.867] | 0.950 | 0.44 | 0.42 | 0.19 |
| 30 | 5 | 0.895 [0.845, 0.930] | 0.990 | 0.39 | 0.38 | 0.18 |
| 30 | 8 | 0.880 [0.828, 0.918] | 1.000 | 0.39 | 0.39 | 0.20 |
| 60 | 3 | 0.840 [0.783, 0.884] | 0.995 | 0.35 | 0.34 | 0.12 |
| 60 | 5 | 0.870 [0.816, 0.910] | 1.000 | 0.34 | 0.34 | 0.14 |
| 60 | 8 | 0.890 [0.839, 0.926] | 1.000 | 0.31 | 0.31 | 0.14 |

Lectura:

- **El IC bootstrap por labor es optimista en todas las celdas:** cubre 82–84 % con 3 labores y 87–90 % con 5 u
  8, frente al 95 % nominal. No mejora con más pares: es el sesgo conocido del bootstrap de percentiles con pocos
  grupos. Con 3 labores es claramente peor (los IC de 3 y de 5 labores casi no se tocan).
- La regla «site» no es la que limita desde 30 pares: pasa en 95–100 % de las réplicas. Con 15 pares falla en
  15–22 % de las réplicas, por IC anchos.
- El EAM de la pendiente baja 32 % de 15 a 30 pares y solo 15 % más de 30 a 60.
- El bayesiano empata con la OLS incluso con 15 pares, aunque su *prior* está desviado en 2.3 puntos de pendiente.
  La fuerza por defecto (desviación de 50 % de la pendiente global) es débil frente a los datos: no daña, pero
  tampoco ayuda con pocos datos.

## 3. Resultados del nivel 2

50 réplicas por celda. «Tramos» y «labores mín.» son medias por réplica: el total de tramos y las labores del tipo
con menos labores.

**Práctica coherente**

| Tramos por tipo | Tramos | Labores mín. por tipo | «coherent» ln Q | «coherent» ln De | Los dos | Cobertura conforme 90 % (labores nuevas) | Tamaño del conjunto |
|---:|---:|---:|---:|---:|---:|---|---:|
| 5 | 56 | 2.7 | 0.92 | 0.22 [0.13, 0.35] | 0.22 | 0.929 [0.910, 0.946] | 3.6 |
| 10 | 95 | 5.0 | 0.96 | 0.60 [0.46, 0.72] | 0.60 | 0.928 [0.918, 0.938] | 3.2 |
| 20 | 163 | 9.2 | 1.00 | 0.78 [0.65, 0.87] | 0.78 | 0.911 [0.902, 0.920] | 2.9 |

Con práctica coherente, el falso «incoherent» fue 2 de 50 con 5 por tipo y 0 de 50 con 10 y con 20.

**Incoherencia 0.5 (la práctica ignora el macizo)**

| Tramos por tipo | Tramos | Labores mín. por tipo | Falso «incoherent» | Cobertura conforme 90 % (labores nuevas) | Tamaño del conjunto |
|---:|---:|---:|---|---|---:|
| 5 | 77 | 3.5 | 0.04 [0.011, 0.135] | 0.921 [0.902, 0.939] | 4.3 |
| 10 | 129 | 6.2 | 0.12 [0.056, 0.238] | 0.924 [0.912, 0.935] | 4.3 |
| 20 | 255 | 12.2 | 0.02 [0.004, 0.105] | 0.921 [0.911, 0.931] | 4.2 |

Lectura:

- El signo de ln Q se detecta casi siempre (92–100 %). **El de ln De es el que necesita datos:** 22 % con 5 por
  tipo, 60 % con 10 y 78 % con 20. Cuando no se detecta, el veredicto es «not significant», nunca «coherent»: la
  falta de datos no se disfraza.
- **El conjunto conforme cumple su 90 % en labores nuevas en todas las celdas** (0.91–0.93), también con 5 por
  tipo. No es lo que limita el mínimo. Cuando la práctica ignora el macizo, el conjunto se agranda solo (4.2–4.3 de
  5 tipos): no informa, y eso es lo correcto.
- El falso «incoherent» junto de las tres celdas con incoherencia 0.5 es 9 de 150 = 6 % [3.2 %, 11.0 %]. Si los
  IC de Wald fueran exactos, lo esperado sería ≈ 5 % (dos variables × 2.5 % por el lado contrario). El 12 % con 10
  por tipo cae dentro del ruido de 50 réplicas, pero sugiere lo mismo que el nivel 1: los IC del ajuste ordinal
  ignoran el efecto de labor y son algo optimistas.

## 4. Mínimos propuestos

Cada uno es una **decisión de diseño respaldada por simulación**. No cambié las constantes de `history.py`: decide
el orquestador.

| Constante | Actual | Propuesto | Justificación |
|---|---:|---:|---|
| `MIN_PAIRS_LEVEL1` | 30 | **30 (se confirma)** | Desde 30 la regla «site» pasa en 95–100 % y el EAM ya bajó 32 % frente a 15. Duplicar a 60 solo gana 15 % más. Con 15 pares, 15–22 % de las réplicas quedan inestables. |
| `MIN_LABORS_LEVEL1` | 5 | **5 (se confirma)** | Con 3 labores la cobertura del IC cae a 82–84 %. Con 5 sube a 87–90 %, y 8 no agrega nada. |
| `MIN_TRAMOS_PER_TYPE_LEVEL2` | 10 | **10 (se confirma)** | Con 10 se detecta ln Q en 96 % y ln De en 60 %. Lo no detectado sale como «not significant», no como un falso «coherent». El conjunto conforme ya cubre. Con 5, ln De solo se detecta en 22 %. |
| `MIN_LABORS_PER_TYPE_LEVEL2` | 5 | **5 (se confirma)** | Una mina que llega a 10 por tipo tiene en promedio 5.0 labores en su tipo más escaso: las dos condiciones van juntas. Con 5 por tipo no pasa de 2.7. |
| `MIN_EVENTS_PER_PARAMETER_LEVEL3` | 10 | pendiente | Se decide con la corrida del nivel 3, con el modelo de tasa constante. |
| `MIN_ZONES_LEVEL3` | 3 | pendiente | Ídem. La partición de zona fuera ya es obligatoria para recomendar. |

Si se quiere un veredicto de ln De más firme, 20 por tipo da 78 %. Lo dejo como opción, no como mínimo: el
veredicto «not significant» ya protege.

## 5. Limitaciones

- **El generador es una simplificación:**
  - efectos aleatorios normales;
  - relaciones lineales en ln Q y ln De;
  - un solo mecanismo de práctica;
  - 3 tipos de labor y 5 tipos de sostenimiento;
  - sin errores de registro.

  Una mina real puede tener efectos de labor más fuertes, dominios mezclados o una práctica que cambió con los años.
- **La prevalencia y el efecto de una mina real pueden ser distintos.** Las tasas de detección dependen del tamaño
  del efecto verdadero (aquí γ_lnDe = 1.5 y la pendiente de RMR = 9). Con un efecto más chico, los mismos mínimos
  detectan menos.
- El *prior* del nivel 1 está desviado de la verdad a propósito, en 2.3 puntos de pendiente. Con una desviación
  mayor o un *prior* más fuerte, el bayesiano con pocos datos podría dañar.
- Las coberturas por debajo del nominal (IC bootstrap del nivel 1 e IC de Wald del nivel 2) son propiedades de los
  métodos, no de los mínimos: no se arreglan subiendo los mínimos. Quedan como riesgo documentado. Las alternativas,
  como un bootstrap-t por labor o errores robustos por grupo, no están implementadas.
- 50 réplicas por celda en el nivel 2 dan IC de ±10–14 puntos en las tasas intermedias. Bastan para ordenar las
  celdas, no para afinar un punto de corte.
