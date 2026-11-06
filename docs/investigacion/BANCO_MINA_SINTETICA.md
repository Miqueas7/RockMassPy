# Banco de pruebas del módulo predictivo con la mina sintética

Fase 5, tarea 5 (plan M8). Este documento mide la auditoría y los niveles 1, 2 y 3 del módulo predictivo, con
`recommend`, contra la verdad de `synthetic_mine` (`python/rockmasspy/predictive/mine.py`). **Todas las cifras son
de minas sintéticas con mecanismo conocido; ninguna sale de una mina real.** La mina sintética es un banco de
pruebas: no entrena ningún modelo que se entregue ni da coeficientes por defecto.

- Script: [`scripts/banco_mina_sintetica.py`](scripts/banco_mina_sintetica.py).
- Resultados:
  - [`banco_mina_sintetica.csv`](banco_mina_sintetica.csv): **desde la revisión final, la corrida del §11** (13
    escenarios, 2412 filas, 153 columnas; el nivel 3 en tres variantes: `antes_*`, `sz_*` y las de siempre). La del
    §10 (151 columnas) es `git show 07c3a6c:docs/investigacion/banco_mina_sintetica.csv`; la de los §2 a §9 (2124
    filas, 100 columnas), `git show c575d12:docs/investigacion/banco_mina_sintetica.csv`.
  - [`banco_mina_sintetica_sin_minimo_l3.csv`](banco_mina_sintetica_sin_minimo_l3.csv): sensibilidad del §6, con el
    mínimo de eventos por parámetro del nivel 3 bajado a 1 dentro del proceso (la librería no cambia).
- **Los §1 a §9 son la corrida de la Fase 5 (c575d12); el §10 es la de la 5B (07c3a6c) y el §11, la de la revisión
  final (8830a9f).**
- Versión: rama `fase-5` en **fa0a8f5** (la verdad ya corregida: cada tipo contrafactual usa sus propias horas sin
  sostener). Una vista previa anterior, con la verdad vieja, se descartó.
- Comandos, desde la raíz del repo:
  - `.venv\Scripts\python.exe -I docs/investigacion/scripts/banco_mina_sintetica.py --reps 50 --reps-large 20 --n-boot 500`
  - `... --reps 50 --n-boot 500 --min-events-l3 1 --no-defects --scenarios ngi_site,small_mine,base,worse_site,better_site,conservative_practice --out docs/investigacion/banco_mina_sintetica_sin_minimo_l3.csv`
- **Tiempo:** la corrida principal tomó **240 s de reloj** con 28 procesos en la PC (≈ 6300 s de CPU: de 207 s en
  `small_mine` a 1012 s en `large_mine`; un trabajo de `large_mine` toma ≈ 50 s y uno de 600 tramos, 8–15 s). La
  sensibilidad tomó 121 s. Con este costo no hizo falta recortar `large_mine` a 5 semillas: quedó en 20.

## 1. Cómo se corrió

- **Escenarios:** los 11 de `SCENARIOS`. 50 semillas por escenario (20 en `large_mine`), con semillas fijas
  derivadas de `--seed 20261105`. Además, una corrida con `defects=True` por escenario, con la semilla de la réplica
  0: el History es el mismo que el limpio salvo los defectos. Las tablas de los §3 a §6 son de las corridas limpias.
- **Auditoría:** `audit_history` sobre la corrida con defectos. Un defecto inyectado cuenta como detectado si hay un
  hallazgo del mismo tipo en el mismo `id_tramo`. La celda vacía no tiene hallazgo propio: cuenta cualquier hallazgo
  en su tramo. Falso hallazgo: uno que no corresponde a ningún defecto inyectado.
- **Nivel 1:** `fit_site_correlation` con `group_by="litologia"`, para `rmr_from_q` y `gsi_from_rmr`, en toda la mina
  y por litología. La recta verdadera es la OLS sobre los valores **verdaderos** de los mismos tramos (para toda la
  mina coincide con `MineTruth.rmr_lnq_slope`; el script lo verifica). Métricas: estado, si el IC 95 % bootstrap de
  la pendiente cubre la pendiente verdadera, sesgo de la pendiente y cobertura del intervalo de predicción al 95 %
  (fracción de tramos con el valor verdadero dentro del intervalo, dado el x registrado).
- **Nivel 2:** `audit_practice`. Estado, convergencia, veredictos de ln Q y ln De, si sale algún «practice
  incoherent», si la práctica es más predecible que la carta (`beyond_chart`), kappa de la concordancia y tamaño
  medio del conjunto conforme. Los tramos «fuera del conjunto» se comparan con los desvíos verdaderos de la práctica
  (`practice_deviation ≠ 0`): precisión y sensibilidad.
- **Nivel 3 y recomendación:**
  - `fit_performance` con la mina de la semilla; `recommend` se aplica a **una segunda mina del mismo escenario**
    (otra semilla). Las labores y las zonas son nuevas para el ajuste: es más exigente que una labor nueva en una
    zona conocida.
  - Umbrales de P aceptable 0.05 y 0.10; horizontes 365 y 1095 días (3 años caben en la exposición de entrenamiento
    de todas las minas, que van de 4 a 10 años).
  - **Demasiado liviano:** el tipo elegido tiene la P verdadera (`truth.p_fail`, marginal sobre la fragilidad de
    una labor nueva y condicional al efecto de su zona) sobre el umbral.
  - **Óptimo de verdad:** el tipo más liviano con P verdadera ≤ umbral. Si ningún tipo cumple, el tramo no tiene
    óptimo («sin óptimo»). **Sobrecosto:** Σ costo elegido / Σ costo óptimo − 1, con `relative_cost` de
    `SUPPORT_TYPES` (I 1.0, II 1.6, III 2.4, IV 3.5, V 6.0), sobre los tramos con óptimo. Es neto: un tipo demasiado
    liviano baja el costo.
  - **Referencias:** la carta Q con el Q registrado (`read_q_chart` con De = luz/ESR, la misma lectura que usa el
    generador) y lo que instaló la mina. Se miden en todos los tramos y, la carta, también en los mismos tramos donde
    el modelo eligió.
- `n_boot` = 500 en todos los bootstraps. Los mínimos de la librería no se tocan en la corrida principal.

## 2. Auditoría de ingesta

Corrida con defectos, una por escenario (11 minas, 10201 tramos):

| Defecto | Detectados / inyectados |
|---|---|
| Q que no cuadra con sus componentes | 183/184 (99.5 %) |
| Progresivas que se solapan | 184/184 |
| Inspección antes de la instalación | 216/216 |
| Tipo de sostenimiento que no existe | 120/120 |
| Celda vacía | 20/281 (7 %) |
| Falsos hallazgos | 0 (y 0 en las 520 corridas limpias) |

- El Q que se escapó es de un tramo con Q muy bajo: `Q_ABS_TOL` = 0.005 es mayor que |Q − Q/3| cuando Q < 0.0075.
  **Corregido** en la revisión I3 de la 5B (commit 3933087): la regla `Q_MAX_RATIO` = 2 atrapa el ×3 (y el ×1/3)
  aunque el Q sea bajo.
- **La celda vacía no se informa.** `audit_history` no tiene un hallazgo de dato faltante: los 20 detectados son
  celdas que dejaron un recálculo imposible y salen por otra vía. La fila simplemente sale de los niveles que la
  necesitan; solo se ve en los conteos de preparación. **Desde la 5B (tarea 8)** `audit_history` tiene el hallazgo
  `missing_values`, uno por columna con conteos y sin `id_tramo`. En la corrida del §10 el script lo contaba como
  falso hallazgo (130 «falsos» en las gemelas con defectos); desde la revisión final se cuenta aparte (§11).
- Los defectos no se excluyen de los ajustes (la auditoría avisa, no bloquea): con los Q multiplicados por 3 o por
  1/3, la pendiente RMR–ln Q del nivel 1 se movió de 0 a −0.12 puntos. Los estados de los tres niveles no cambiaron en
  ninguna de las 11 gemelas.

## 3. Resumen por escenario

Corridas limpias. Mediana [mínimo–máximo] entre semillas; los conteos son de semillas.

| Escenario | Semillas | Tramos | Fallas (filas del nivel 3) | Nivel 1 RMR–ln Q: «site» / IC cubre | Nivel 2: converge / «incoherent» / supera la carta | Nivel 3: site / partial / not_calibrated |
|---|---:|---|---|---|---|---|
| `base` | 50 | 587 [549–656] | 51 [24–88] | 50/50 / 50/50 | 50/50 / 0/50 / 49/50 | 5 / 11 / 34 |
| `ngi_site` | 50 | 604 [553–672] | 51 [34–79] | 50/50 / 49/50 | 50/50 / 0/50 / 0/50 | 0 / 12 / 38 |
| `worse_site` | 50 | 604 [553–651] | 134 [80–197] | 50/50 / 49/50 | 50/50 / 0/50 / 44/50 | 7 / 43 / 0 |
| `better_site` | 50 | 592 [545–666] | 11 [5–26] | 50/50 / 50/50 | 50/50 / 2/50 / 45/50 | 0 / 0 / 50 |
| `shifted_correlation` | 50 | 609 [555–638] | 63 [30–127] | 50/50 / 49/50 | 50/50 / 2/50 / 50/50 | 14 / 17 / 19 |
| `conservative_practice` | 50 | 600 [558–646] | 12 [4–22] | 50/50 / 50/50 | 48/50 / 0/50 / 48/50 | 0 / 0 / 50 |
| `incoherent_practice` | 50 | 594 [546–637] | 63 [40–105] | 50/50 / 50/50 | 50/50 / 0/50 / 45/50 | 19 / 12 / 19 |
| `mine_practice` | 50 | 600 [539–672] | 55 [27–108] | 50/50 / 50/50 | 50/50 / 1/50 / 47/50 | 7 / 14 / 29 |
| `noisy_mapping` | 50 | 604 [538–656] | 56 [31–87] | 50/50 / 50/50 | 50/50 / 0/50 / 50/50 | 3 / 13 / 34 |
| `small_mine` | 50 | 80 [67–100] | 5 [0–13] | 35/50 / 50/50 | 50/50 / 0/50 / 14/50 | 0 / 0 / 50 |
| `large_mine` | 20 | 4807 [4686–4912] | 508 [371–662] | 20/20 / 20/20 | 14/20 / 0/20 / 20/20 | 19 / 1 / 0 |

### Recomendación, H = 365 días

«Elige» es sobre todos los tramos de la mina de prueba; «demasiado liviano» y «la carta en los mismos tramos», sobre
los elegidos (conteos sumados entre semillas). El sobrecosto va en mediana [rango] entre las semillas que eligieron.

| Escenario | Umbral | Elige | Demasiado liviano (modelo) | Sobrecosto del modelo frente al óptimo | Carta en los mismos tramos: liviana | Carta en todos: liviana / sobrecosto | Instalado: liviano / sobrecosto | Sin óptimo |
|---|---:|---|---|---|---|---|---|---|
| `base` | 0.05 | 2.2 % | 2.6 % (17/665) | +164 % [102–196] | 32.2 % | 53.9 % / −28 % | 39.6 % / +7 % | 18.9 % |
| `base` | 0.10 | 3.5 % | 2.4 % (25/1049) | +126 % [70–475] | 19.5 % | 29.7 % / −9 % | 21.9 % / +28 % | 5.2 % |
| `ngi_site` | 0.05 | 0 | sin elecciones | | | 11.3 % / +2 % | igual a la carta | 0 |
| `ngi_site` | 0.10 | 0 | sin elecciones | | | 0.8 % / +43 % | igual a la carta | 0 |
| `worse_site` | 0.05 | 0.5 % | **6.9 %** (11/159) | +155 % [71–189] | 73.6 % | 86.2 % / −30 % | 73.8 % / +10 % | 66.7 % |
| `worse_site` | 0.10 | 2.5 % | **23.4 %** (175/747) | +119 % [37–172] | 55.7 % | 72.1 % / −15 % | 60.3 % / +24 % | 53.1 % |
| `better_site` | 0.05 | 0 | sin elecciones | | | 6.4 % / +5 % | 9.7 % / +20 % | 0.3 % |
| `better_site` | 0.10 | 0 | sin elecciones | | | 1.5 % / +13 % | 2.6 % / +30 % | 0.1 % |
| `shifted_correlation` | 0.05 | 8.3 % | 2.1 % (53/2477) | +128 % [66–250] | 18.4 % | 47.8 % / −23 % | 46.9 % / −13 % | 18.3 % |
| `shifted_correlation` | 0.10 | 12.5 % | 3.4 % (126/3741) | +79 % [25–175] | 11.0 % | 24.3 % / 0 % | 29.3 % / +4 % | 5.1 % |
| `conservative_practice` | 0.05 | 0 | sin elecciones | | | 24.4 % / +2 % | 9.5 % / +92 % | 4.7 % |
| `conservative_practice` | 0.10 | 0 | sin elecciones | | | 10.2 % / +24 % | 4.0 % / +133 % | 2.1 % |
| `incoherent_practice` | 0.05 | 12.0 % | 2.2 % (80/3630) | +180 % [80–500] | 25.5 % | 52.7 % / −27 % | 42.3 % / +8 % | 17.7 % |
| `incoherent_practice` | 0.10 | 18.3 % | 1.1 % (59/5569) | +145 % [64–358] | 15.2 % | 28.0 % / −5 % | 24.4 % / +30 % | 5.3 % |
| `mine_practice` | 0.05 | 2.2 % | 3.1 % (20/650) | +107 % [89–113] | 25.5 % | 56.3 % / −29 % | 43.4 % / 0 % | 19.7 % |
| `mine_practice` | 0.10 | 2.9 % | 3.7 % (32/876) | +66 % [50–107] | 16.4 % | 31.8 % / −8 % | 24.8 % / +19 % | 6.2 % |
| `noisy_mapping` | 0.05 | 2.8 % | 2.3 % (19/832) | +151 % [114–306] | 20.7 % | 52.8 % / −26 % | 40.0 % / +12 % | 18.7 % |
| `noisy_mapping` | 0.10 | 3.8 % | 1.3 % (15/1150) | +102 % [73–187] | 14.8 % | 29.6 % / −6 % | 22.7 % / +36 % | 6.0 % |
| `small_mine` | 0.05 | 0 | sin elecciones | | | 57.5 % / −33 % | 43.7 % / +4 % | 21.3 % |
| `small_mine` | 0.10 | 0 | sin elecciones | | | 31.0 % / −10 % | 24.4 % / +25 % | 5.8 % |
| `large_mine` | 0.05 | 46.9 % | 3.3 % (1484/44985) | +114 % [48–199] | 28.8 % | 53.1 % / −27 % | 38.6 % / +10 % | 17.4 % |
| `large_mine` | 0.10 | 60.7 % | **5.0 %** (2923/58165) | +59 % [16–104] | 16.5 % | 28.1 % / −6 % | 21.1 % / +32 % | 4.9 % |

### Recomendación, H = 1095 días (solo donde el modelo eligió)

| Escenario | Umbral | Elige | Demasiado liviano (modelo) | Sobrecosto del modelo | Carta en los mismos tramos: liviana | Sin óptimo |
|---|---:|---|---|---|---|---|
| `base` | 0.05 / 0.10 | 0.7 % / 1.6 % | 1.9 % (4/214) / 1.9 % (9/480) | +132 % / +212 % | 56.1 % / 37.1 % | 44.9 % / 27.8 % |
| `worse_site` | 0.10 | 0.1 % | 2.3 % (1/43) | +121 % | 97.7 % | 73.9 % |
| `shifted_correlation` | 0.05 / 0.10 | 1.5 % / 5.5 % | 4.9 % (22/445) / 1.5 % (24/1641) | +138 % / +135 % | 85.6 % / 30.7 % | 44.7 % / 27.6 % |
| `incoherent_practice` | 0.05 / 0.10 | 3.7 % / 8.9 % | 3.3 % (37/1127) / 2.2 % (59/2716) | +159 % / +171 % | 72.3 % / 34.2 % | 43.7 % / 26.7 % |
| `mine_practice` | 0.05 / 0.10 | 0.5 % / 1.6 % | **8.0 %** (13/162) / 4.7 % (22/470) | +147 % / +135 % | 66.7 % / 43.6 % | 48.5 % / 29.8 % |
| `noisy_mapping` | 0.05 / 0.10 | 0.9 % / 2.1 % | **9.9 %** (28/282) / 1.3 % (8/631) | +132 % / +219 % | 78.0 % / 26.8 % | 44.5 % / 28.5 % |
| `large_mine` | 0.05 / 0.10 | 11.8 % / 36.2 % | 4.8 % (543/11319) / 2.4 % (821/34677) | +146 % / +157 % | 76.4 % / 37.1 % | 43.9 % / 26.6 % |

Con H = 1095 días la combinación umbral–horizonte es inalcanzable en buena parte de los tramos («sin óptimo»
27–74 %, 64 % en `ngi_site` con 0.05): la carta y lo instalado salen «demasiado livianos» en 47–100 % por pura
exposición, no por elegir mal. El resto de las columnas está en el CSV.

## 4. Lo que funciona

1. **La auditoría es exacta en lo que revisa:** 99.5–100 % de los defectos con hallazgo propio y 0 falsos en 531
   minas (corrida c575d12; los `missing_values` de la 5B no son falsos y van aparte, §11).
2. **El nivel 1 recupera la recta de la mina.** «site» en 50/50 en los escenarios de ≈ 600 tramos y en 35/50 en
   `small_mine` (80 tramos). El IC de la pendiente cubre la verdadera en 49–50 de 50, el intervalo de predicción
   cubre 93.9–95.7 % de los RMR verdaderos (medianas) (nominal 95 %) y el sesgo de la pendiente es despreciable. Sigue a la mina
   cuando la recta cambia: `better_site` 7.5 (verdad 7.6) y `shifted_correlation` 7.2 (verdad 7.2). Por litología,
   80–100 % de los dominios llegan a «site» (14 % en `small_mine`) y el IC cubre en 94–100 %.
3. **El nivel 2 no inventa incoherencias.** «practice incoherent» salió en 5 de 520 minas (1 %), todas con ln De, y
   en `ngi_site`, donde la práctica es la carta, dice correctamente que no supera a la carta (0/50).
4. **`ngi_site` y `small_mine` se portan como se esperaba.** `ngi_site` nunca llega a «site» (38 not_calibrated,
   12 partial) ni recomienda; sin el mínimo de eventos (§6) queda 50/50 en «partial»: la validación no le encuentra
   nada que ganarle a la carta. `small_mine` nunca recomienda (50/50 not_calibrated: 2 zonas y ≈ 5 fallas).
5. **Donde el modelo elige, es mucho más seguro que la carta en los mismos tramos.** Con H = 365, demasiado liviano
   1–5 % frente a 11–74 % de la carta en esos mismos tramos.

## 5. Lo que falla

1. **«Demasiado liviano» sobre ~5 %** (P verdadera sobre el umbral en el tipo elegido):
   - `worse_site`, H = 365: **23.4 %** con 0.10 (175/747) y **6.9 %** con 0.05 (11/159). Está concentrado: con
     0.10 eligen 5 de los 7 modelos «site», y uno solo pone 142 de 317 elecciones (45 %) sobre el umbral; otro, 30 de
     232 (13 %).
   - `noisy_mapping`, H = 1095 con 0.05: **9.9 %** (28/282), casi todo de una mina (28/215).
   - `mine_practice`, H = 1095 con 0.05: **8.0 %** (13/162), de una mina (13/61).
   - `large_mine`, H = 365 con 0.10: **5.0 %** (2923/58165), repartido en las 19 minas «site» (de 0.5 % a 17 % por
     mina). Es el caso más representativo: mucho dato, modelo «site» y aun así 1 de cada 20 elecciones liviana.
   - Sin el mínimo de eventos del nivel 3, `base` sube a 10.5 % (0.05) y 6.2 % (0.10): el mínimo sí protege (§6).
2. **Causa: el modelo es aditivo y plano en la calidad; la verdad castiga el déficit.** En la verdad la tasa sube
   κ_def por cada tipo que falta frente a lo que pide la carta con el Q verdadero (corrido δ), o sea que el efecto
   del sostenimiento depende del macizo. El modelo de la librería suma β_q·ln Q + β_rank·rango y no tiene esa
   interacción. En el diagnóstico de la peor mina de `large_mine`, la P del modelo para el tipo elegido queda en
   ≈ 0.025–0.03 en todos los estratos, mientras la verdadera va de 0.02 (tipo ≥ requerido) a 0.11–0.49 (tipo 1 a 3
   escalones bajo lo requerido); el 91 % de sus elecciones livianas (487 de 536) son tipos bajo lo que pide la carta verdadera
   (por ejemplo, tipo I donde la verdad pide III: 75 de 101 livianos). En `worse_site` la pendiente de ln Q sale
   −0.26 (chata) y elige IV o V en roca que pide V con P verdadera ≈ 0.12–0.21. El efecto de zona de la mina de
   prueba no explica el patrón: los livianos se reparten en todas las zonas.
3. **Elige poco y muy caro.** Con los mínimos vigentes, en las minas de ≈ 600 tramos elige en 0–18 % de los tramos
   (0 % en 5 escenarios). Cuando elige, el sobrecosto frente al óptimo de verdad es +59 a +219 % (mediana) y
   +48 a +496 % frente a la carta en los mismos tramos. Es la misma cara del punto 2: en roca buena pide de más y en
   roca mala no pide lo suficiente.
4. **El tamaño de los escenarios no alcanza el mínimo del nivel 3.** El plan dimensionó ≈ 600 tramos con 5–10 % de
   fallas (D7.5), pero con 6 parámetros el mínimo pide 60 eventos y la mediana es 51: `base` queda not_calibrated en
   34/50. `better_site` y `conservative_practice` (11–12 fallas) nunca llegan.
5. **El nivel 2 no detecta la práctica incoherente** tal como se definió en el escenario. En `incoherent_practice`
   (GSI visual con DE 10, 40 % de desvíos, cambio de tabla) los signos siguen correctos, así que el veredicto es
   «coherent» en 50/50 y «beyond_chart» en 45/50. Las señales están, pero el módulo no las convierte en veredicto:
   conjunto conforme de 3.24 tipos (2.57 en `base`), kappa recomendado–instalado 0.93 (0.97 en `base`) y
   sensibilidad a los desvíos de 15 % (27 % en `base`).
6. **«Fuera del conjunto» no es un detector de desvíos.** Marca ≈ 10 % de los tramos por construcción (nivel 90 %).
   Contra los desvíos verdaderos, la precisión es 30–67 % y la sensibilidad 15–55 %. En `ngi_site`, sin desvíos,
   marca 2933 tramos (precisión 0): son la parte de la carta que el logit en ln Q y ln De no reproduce.
7. **El ajuste ordinal no converge en minas grandes:** 6 de 20 en `large_mine` y 2 de 50 en `conservative_practice`.
   Esas minas quedan con «not estimable» y sin conjuntos conformes (ver §8, error 1).
8. **El nivel 1 GSI–RMR se sesga con mapeo ruidoso.** En `noisy_mapping` el IC de la pendiente cubre en 28/50
   (sesgo +0.05 [0.01–0.10]): el GSI y el RMR registrados comparten los mismos componentes mal mapeados (condición y
   RQD), así que el error no es independiente entre x e y. El RMR–ln Q no se afecta (50/50).

## 6. Sensibilidad: sin el mínimo de eventos del nivel 3

Mismas semillas, mínimo de eventos por parámetro bajado a 1 dentro del proceso; H = 365.

| Escenario | site / partial / not_calibrated | Elige (0.05 / 0.10) | Demasiado liviano (0.05 / 0.10) |
|---|---|---|---|
| `ngi_site` | 0 / 50 / 0 | 0 / 0 | sin elecciones |
| `small_mine` | 0 / 0 / 50 (2 zonas < 3) | 0 / 0 | sin elecciones |
| `base` | 12 / 38 / 0 | 5.2 % / 8.0 % | **10.5 %** (162/1543) / **6.2 %** (148/2382) |
| `worse_site` | 7 / 43 / 0 | igual a la principal (ya pasaba el mínimo) | 6.9 % / 23.4 % |
| `better_site` | 0 / 49 / 1 | 0 / 0 | sin elecciones |
| `conservative_practice` | 1 / 47 / 2 | 0 / 0 | sin elecciones |

La regla de validación sola deja pasar 7 modelos «site» más en `base`, y esos eligen peor: el mínimo vigente de 10
eventos por parámetro sí está protegiendo. Confirma la lectura de `SIMULACION_MINIMOS.md` §5 con otro generador.

**Ojo al repetirla después de la 5B:** `--min-events-l3` cambia `history.MIN_EVENTS_PER_PARAMETER_LEVEL3` y también
`performance.MIN_EVENTS_PER_PARAMETER_LEVEL3`, y este último es el corte de la compuerta (d) (fallas por tipo de
labor). Con `--min-events-l3 1` la sensibilidad también apaga la compuerta (d): no mide solo el mínimo de eventos.
Esta tabla es de c575d12, cuando la compuerta (d) no existía, así que no la afecta.

## 7. Recomendaciones

Para el módulo:

1. **Modelo de desempeño (lo más urgente):** agregar el déficit frente a la carta, d = rango instalado − rango que
   pide la carta NGI con el Q registrado, como variable (o la interacción ln Q × rango), con su cota de signo. Volver
   a correr este banco: la meta es bajar «demasiado liviano» bajo 5 % en `large_mine` y `worse_site`, y el
   sobrecosto. Ojo: el déficit es justo el mecanismo del generador (M5, supuesto de diseño); para no medir el modelo
   con su propia receta, el banco debería tener también un escenario con otro mecanismo (por ejemplo, un umbral de
   calidad o un efecto del sostenimiento que se satura).
2. **Una compuerta de calibración por estrato de calidad:** antes de elegir, observados/esperados fuera de pliegue en
   el tercio peor de ln Q. Con el modelo actual detectaría el caso de `worse_site`.
3. **Compuerta de consistencia con la carta:** no elegir un tipo más liviano que el que pide la carta NGI con el Q
   registrado si el entrenamiento casi no tiene tramos de ese tipo en ese rango de Q. Hoy elige tipo I en roca que la
   verdad clasifica para III.
4. **Nivel 2:** un indicador de práctica ruidosa (tamaño del conjunto conforme o kappa de la concordancia frente a
   una referencia) además de los signos, y documentar que «fuera del conjunto» marca ≈ 1 − nivel de los tramos por
   construcción y no equivale a un desvío.
5. **Ajuste ordinal:** escalar la tolerancia con n (error 1 del §8).
6. **Auditoría:** un hallazgo de dato faltante (por columna, contado, no por fila) y una tolerancia de Q relativa
   para Q muy bajos.
7. **Nivel 1, GSI–RMR:** avisar que GSI y RMR comparten componentes (condición de juntas y RQD) y que el IC de la
   pendiente es optimista con mapeo ruidoso.

Para los mínimos y los escenarios:

8. Mantener `MIN_EVENTS_PER_PARAMETER_LEVEL3` = 10 (§6) y `MIN_ZONES_LEVEL3` = 3 (`small_mine` queda fuera por las
   zonas).
9. Redimensionar `base` para que llegue al mínimo (≈ 800 tramos con la misma prevalencia, o +2 puntos de
   prevalencia): hoy es un escenario «not_calibrated» en 2/3 de las semillas, no el caso típico que se quería medir.
10. Documentar que con H largo (3 años) y umbral 5 % la mayoría de los tramos no tiene ningún tipo que cumpla: la
    librería debería decir «ningún tipo cumple» y no forzar una elección, como hace hoy.

## 8. Errores del paquete encontrados

No se corrigió nada (este banco no toca `python/` ni `tests/`):

1. **`stats.ordinal_logit_fit` no converge con n grande.** Usa `trust-exact` con `gtol` = 1e-9 absoluto sobre la
   log-verosimilitud sumada (no promediada). Con ≈ 4800 tramos, el optimizador termina con «A bad approximation
   caused failure to predict improvement» aunque los coeficientes son moderados (ln Q ≈ −1.5). El mensaje atribuye
   el fallo a una separación que no existe. Efecto: `audit_practice` sale con covarianza NaN, veredictos «not
   estimable» y sin conjuntos conformes en 6 de 20 minas grandes. Arreglo probable: optimizar la log-verosimilitud
   media o una tolerancia relativa.
2. **`audit_history` y Q muy bajos:** la tolerancia absoluta `Q_ABS_TOL` = 0.005 esconde un Q registrado 3 veces
   mayor (o menor) cuando Q < 0.0075 (1 de 184 en el banco). **Corregido** (3933087): `Q_MAX_RATIO` = 2 lo atrapa.
3. Hueco, no error: no hay hallazgo de celda vacía (7 % de detección, solo indirecta). **Corregido** en la 5B:
   `missing_values` por columna.

## 9. Limitaciones

- El generador es una simplificación, aunque calibrada (`CALIBRACION_MINA_SINTETICA.md`): tasa constante, fragilidad
  gamma, déficit frente a la carta como mecanismo y una sola práctica por escenario. El punto 1 del §7 viene de que el
  modelo de la librería no tiene la forma del generador; con otro mecanismo verdadero el resultado podría ser otro.
- La mina de prueba trae zonas nuevas: es más exigente que aplicar el modelo a una labor nueva en una zona conocida.
- Las tasas «demasiado liviano» con pocas elecciones (decenas a cientos, de 2 a 7 minas «site») dependen de una o dos
  minas; sirven para ver dónde falla, no para fijar un número.
- El costo es el `relative_cost` sintético de `SUPPORT_TYPES`, no el de una mina; el sobrecosto es solo comparativo.

## 10. Antes y después de la 5B

Fase 5B, tarea 7 (6-nov). Mismas semillas, `--reps 50 --reps-large 20 --n-boot 500` y mínimos de la librería que
la corrida c575d12; commit **59e7560** de `fase-5`. Tomó 1014 s de reloj con 28 procesos. Cambios medidos:

- **Mina:** `base` pasa a ≈ 800 tramos (8 labores por zona); los demás escenarios de la Fase 5 no cambian (las
  minas son idénticas a las de c575d12). Dos escenarios nuevos con el **mecanismo alternativo**
  (`failure_mechanism="saturating"`: sin carta ni déficit, −0.6·ln Q + 0.8·ln De y un efecto del sostenimiento
  que se satura, 4·(1 − exp(−(rango − 1)/2.5))): `saturating_large` (como `large_mine`, ≈ 13 % de fallas, 20
  semillas) y `saturating_worse` (geología de `worse_site`, ≈ 20 %).
- **Nivel 3** (`performance.py`):
  1. forma: aditiva o interacción (calidad − máx)·(rango − máx) con cota ≥ 0; la interacción entra solo si la clase
     menor alcanza 10 eventos por parámetro contándola y si baja la devianza de Poisson fuera de pliegue
     (partición por labor);
  2. **zona nueva en la cota superior:** η_sup = η + q·sqrt(se² + σ_z²), σ_z² = C·Var(η en la media) con la
     covarianza agrupada por zona;
  3. compuertas de `recommend` (valores por confirmar): (a) O/E fuera de pliegue en el tercio peor de la calidad,
     falla si pasa de 1.2 o si hay menos de 10 fallas; (b) un tipo no es elegible en una clase de Q de Barton et al.
     1974 con menos de 10 tramos de ese tipo; (c) «ningún tipo cumple» explícito; (d) no elige en un tipo de labor
     con menos de 10 fallas en el entrenamiento.
- **Tres variantes con la misma mina, en el mismo proceso:** «antes» = aditiva, sin zona ni compuertas a, b y d
  (reproduce c575d12 **exactamente** en los 10 escenarios que no cambiaron de tamaño); «sin zona» = 5B con
  `zone_sd` = 0; «después» = 5B tal como se entrega.

### Recomendación, H = 365 días

Elige % / demasiado liviano % (conteo sumado) / sobrecosto mediano frente al óptimo de verdad.

| Escenario | Umbral | Antes | Sin zona | Después |
|---|---:|---|---|---|
| `base` (≈ 800) | 0.05 | 5.0 % / 6.1 % (124/2020) / +127 % | 2.0 % / 7.5 % (59/787) / +115 % | 0.8 % / 3.4 % (11/321) / +144 % |
| `base` (≈ 800) | 0.10 | 9.2 % / 4.9 % (180/3710) / +91 % | 6.3 % / 3.6 % (91/2517) / +91 % | 3.1 % / 2.2 % (28/1254) / +156 % |
| `worse_site` | 0.05 | 0.5 % / 6.9 % (11/159) / +155 % | 0.1 % / 2.9 % (1/34) / +184 % | 0 / sin elecciones |
| `worse_site` | 0.10 | 2.5 % / **23.4 %** (175/747) / +119 % | 1.3 % / 11.0 % (42/383) / +109 % | 0.6 % / **5.3 %** (10/189) / +126 % |
| `shifted_correlation` | 0.05 | 8.3 % / 2.1 % (53/2477) / +128 % | 2.7 % / 5.4 % (44/821) / +110 % | 1.7 % / 6.4 % (33/517) / +149 % |
| `shifted_correlation` | 0.10 | 12.5 % / 3.4 % (126/3741) / +79 % | 6.1 % / 4.2 % (77/1816) / +90 % | 4.1 % / 2.3 % (29/1237) / +134 % |
| `incoherent_practice` | 0.05 | 12.0 % / 2.2 % (80/3630) / +180 % | 5.5 % / 1.9 % (32/1672) / +218 % | 3.0 % / 1.9 % (17/898) / +285 % |
| `incoherent_practice` | 0.10 | 18.3 % / 1.1 % (59/5569) / +145 % | 11.3 % / 0.6 % (19/3426) / +162 % | 7.3 % / 0.1 % (2/2214) / +249 % |
| `mine_practice` | 0.05 | 2.2 % / 3.1 % (20/650) / +107 % | 1.1 % / 1.5 % (5/329) / +115 % | 0.5 % / 0.7 % (1/144) / +148 % |
| `mine_practice` | 0.10 | 2.9 % / 3.7 % (32/876) / +66 % | 2.6 % / 1.0 % (8/795) / +112 % | 2.2 % / 0.1 % (1/677) / +135 % |
| `noisy_mapping` | 0.05 | 2.8 % / 2.3 % (19/832) / +151 % | 1.4 % / 2.1 % (9/436) / +160 % | 0.9 % / 1.1 % (3/275) / +229 % |
| `noisy_mapping` | 0.10 | 3.8 % / 1.3 % (15/1150) / +102 % | 2.7 % / 1.4 % (11/806) / +103 % | 1.7 % / 0.2 % (1/526) / +187 % |
| `large_mine` | 0.05 | 46.9 % / 3.3 % (1484/44985) / +114 % | 45.6 % / 3.2 % (1420/43707) / +116 % | 26.5 % / 1.1 % (283/25435) / +260 % |
| `large_mine` | 0.10 | 60.7 % / **5.0 %** (2923/58165) / +59 % | 60.0 % / 4.8 % (2740/57538) / +57 % | 50.8 % / **1.3 %** (646/48735) / +133 % |
| `saturating_large` | 0.05 | 49.3 % / 3.3 % (1558/47138) / +80 % | 48.5 % / 3.2 % (1504/46448) / +80 % | 39.0 % / 1.3 % (467/37349) / +114 % |
| `saturating_large` | 0.10 | 63.5 % / 4.0 % (2440/60739) / +65 % | 62.1 % / 4.0 % (2394/59435) / +67 % | 53.7 % / 1.5 % (772/51356) / +97 % |
| `saturating_worse` | 0.05 | 2.6 % / 4.6 % (36/776) / +97 % | 1.5 % / 5.3 % (24/450) / +81 % | 0.9 % / 3.4 % (9/267) / +132 % |
| `saturating_worse` | 0.10 | 4.8 % / 4.9 % (71/1439) / +84 % | 3.6 % / 4.2 % (46/1095) / +95 % | 2.7 % / 2.6 % (21/805) / +123 % |

`ngi_site`, `better_site`, `conservative_practice` y `small_mine` siguen **sin ninguna elección** en las tres
variantes y los dos horizontes (estados idénticos a c575d12: `ngi_site` 38 not_calibrated y 12 partial, los otros
tres 50/50 not_calibrated). La columna c575d12 no se repite: «antes» es igual, salvo `base`, que cambió de tamaño
(en c575d12, con ≈ 600 tramos: 2.2 % / 2.6 % / +164 % y 3.5 % / 2.4 % / +126 %).

Con H = 1095 días (el resto en el CSV): `large_mine` 0.10 pasa de 2.4 % (821/34677) a 1.3 % (155/12371), con
0.05 de 4.8 % a 2.7 %; `saturating_large` de 2.5 % a 1.1 %; `noisy_mapping` 0.05 de 9.9 % (28/282) a 0 % (0/10) y
`mine_practice` 0.05 de 8.0 % a sin elecciones. Quedan sobre 5 %: `base` 0.10 con 6.2 % (8/128) y
`saturating_worse` 0.10 con 6.9 % (10/145), con muy pocas elecciones.

### Qué quedó en el modelo y por qué

- **La forma casi no importa.** La interacción entró en 7/20 minas de `large_mine`, 11/20 de `saturating_large`,
  18/50 de `worse_site`, 20/50 de `saturating_worse` y 1–7 de 50 en los demás. «Sin zona» (forma elegida y
  compuertas, sin la zona nueva) deja `large_mine` en 4.8 % y `saturating_large` en 4.0 %: casi lo mismo que antes.
- **El déficit frente a la carta se probó y se descartó.** En un prototipo sin validación ni mínimos, el
  déficit/sobrante con el Q registrado subió «demasiado liviano» en `large_mine` (4.8 % → 7.8 % con 0.10) y no bajó
  en `worse_site`. Además la librería no tiene la equivalencia entre los tipos de una mina y las categorías de la
  carta, así que el déficit necesitaría un dato que hoy no se pide.
- **La causa principal era la zona nueva**, no la forma: la mina de prueba trae zonas que el ajuste no vio (DE 0.4
  en log λ) y el modelo no tiene efecto de zona en la media. σ_z estimado: mediana 0.42 [0.21–0.62] en
  `large_mine` y 0.41 en `saturating_large` (verdad 0.40); 0.42–0.49 en las minas de 600–800 tramos (por exceso,
  como se buscaba). Es lo que baja `large_mine` de 5.0 % a 1.3 %.
- **`worse_site` era una sola mina:** con 8 fallas en rampa, el efecto de rampa salió −0.34 (verdad 0) y la mina de
  prueba tiene 215 tramos de rampa: 70 de sus 79 livianos tras la zona nueva. La compuerta (d) la saca; el 5.3 %
  que queda son 10 de 189, 9 de ellos de otra mina.
- Lo que el modelo sigue sin ver: el × 4 de las horas sin sostener sobre el autosoporte (C6.5), que en el
  diagnóstico explica casi todos los livianos que quedan. ln(horas) como variable bajó «demasiado liviano» de 4.8 %
  a 4.0 % en el prototipo, pero al recomendar pide las horas previstas de cada tipo: queda pendiente.

### Compuertas

| Compuerta | Valor | Tramos sin elección por ella (después, H = 365, 0.10) |
|---|---|---|
| (a) O/E en el tercio peor de la calidad | > 1.2, o < 10 fallas | 273 `incoherent_practice`, 350 `noisy_mapping`, 259 `saturating_worse`; ninguna en las minas grandes. Falló en 0 de 20 `large_mine` (O/E 0.96 [0.79–1.05]) y en 47–50 de 50 en las minas de pocas fallas, que de todos modos no están calibradas |
| (b) soporte por clase de Q | < 10 tramos del tipo en la clase | cuenta dentro de «no elegible»: 2333 en `large_mine`, 4294 en `saturating_large`, 76–866 en las otras |
| (c) ningún tipo cumple | todas las cotas sobre el umbral | 38990 en `large_mine`, 29561 en `saturating_large`, 479–5569 en las otras |
| (d) tipo de labor con pocas fallas | < 10 fallas | 1210 `base`, 1262 `shifted_correlation`, 1173 `incoherent_practice`, 215 `worse_site`, 0 en las grandes |

Las cuatro son decisiones de diseño con el valor por confirmar.

### Contra la meta

| Meta | Resultado |
|---|---|
| «Demasiado liviano» < 5 % en `large_mine` | **Cumple** con H = 365 (1.1 % y 1.3 %) y con H = 1095 (2.7 % y 1.3 %) |
| … en `worse_site` | **Casi:** 5.3 % (10/189) con 0.10; con 0.05 ya no elige |
| … en `shifted_correlation` (agregado en la revisión final) | **No cumple** con 0.05 y H = 365: 6.4 % (33/517), peor que antes (2.1 %, 53/2477); con 0.10 cumple (2.3 %) |
| … en el mecanismo alternativo | **Cumple:** `saturating_large` 1.3 % / 1.5 %, `saturating_worse` 3.4 % / 2.6 % (H = 365); con H = 1095 `saturating_worse` 0.10 queda en 6.9 % (10/145) |
| `ngi_site`, `small_mine`, `better_site` sin recomendar | **Cumple:** 0 elecciones en todas las variantes |
| Sin subir el sobrecosto | **No cumple.** El sobrecosto mediano sube en todos los escenarios: `large_mine` +59 % → +133 % (0.10) y +114 % → +260 % (0.05); `saturating_large` +65 % → +97 %; `worse_site` +119 % → +126 %. También baja la fracción de tramos con elección (`large_mine` 60.7 % → 50.8 %) |

La seguridad se compró con sostenimiento: el modelo no es más fino, es más prudente donde no sabe (zonas nuevas,
tipos de labor y clases de Q con poca historia). Bajar el sobrecosto pide que la media mejore (efecto de zona o
de nivel cuando la zona es conocida, las horas sin sostener) y no más compuertas.

## 11. Después de la revisión final

Revisión final de la 5B (6-nov). Mismas semillas y configuración que el §10 (`--reps 50 --reps-large 20 --n-boot
500`, mínimos de la librería sin tocar), commit **8830a9f** de `fase-5`. Tomó 1074 s de reloj con 28 procesos.
«Antes» es la corrida del §10 (07c3a6c) y «después», esta. Cambios medidos:

- **σ_z en su cota superior (I1).** σ̂_z = C·Var(η en la media) es una sola estimación con C − 1 grados de libertad:
  en `large_mine` va de 0.21 a 0.62 (verdad 0.40, 8 zonas) y la mina de σ̂_z = 0.21 ponía 297 de sus 3670
  elecciones sobre el umbral (8.1 %, H = 365, 0.10). `recommend` usa ahora σ̂_z·sqrt((C − 1)/χ²_{1−u}(C − 1)) con
  u = 0.5 + level/2, el mismo cuantil que la cota de η: ×1.80 con 8 zonas y ×2.37 con 5 (level 0.9).
  `fit_performance` avisa con menos de 10 zonas.
- **Forma (M2, M3):** se elige con pliegues por labor de otra semilla que la validación, y si la interacción queda
  en su cota en el ajuste final vuelve la aditiva. La interacción quedó en 7/20 `large_mine` (igual), 0/20
  `saturating_large` (antes 11/20), 1/50 `saturating_worse` (antes 20/50), 16/50 `worse_site` (antes 18/50) y
  0–8 de 50 en los demás: con el mecanismo que se satura casi deja de entrar. Los estados del
  nivel 3 no cambiaron en ningún escenario.
- **Auditoría (M5 del banco):** `missing_values` va aparte. En las gemelas con defectos: 0 falsos y 130 hallazgos
  `missing_values` (uno por columna con celdas vacías); 0 hallazgos en las corridas limpias. Los defectos con
  hallazgo propio salen 100 % (Q que no cuadra 288/288, con la regla `Q_MAX_RATIO` de 3933087).
- **Nivel 2:** la consistencia nueva (1 − tanh(w/4), corte 0.66) marca «poorly consistent» en 50/50
  `incoherent_practice` (mediana 0.705), en 21/50 `shifted_correlation` (0.656) y en 0–2 de 50 en los demás
  (`ngi_site` 0.008, `mine_practice` 0.358).

### Cómo se eligió la cota de σ_z

Experimento aparte, con las mismas minas del banco (escenarios que eligen, nivel 3 con ln Q y, en `worse_site`,
`large_mine` y `saturating_worse`, también con RMR; H = 30, 365 y 1095 días; umbrales 0.01, 0.05 y 0.10). Para cada
variante se midió «demasiado liviano» por mina (p90 y máximo entre las minas que eligen) y la fracción de tramos con
elección:

| Variante | Peor p90 por mina, ln Q | Peor máximo, ln Q | Peor p90, RMR | `large_mine` H = 365, 0.10: elige / sobrecosto |
|---|---:|---:|---:|---|
| σ̂_z (la del §10) | 24.5 % | 24.5 % | 94 % | 50.8 % / +133 % |
| Momentos (DerSimonian–Laird) con O/E por zona fuera de pliegue | 24.6 % | 33.3 % | 91 % | 52.7 % / +124 % |
| Piso 0.3 | 15.3 % | 18.2 % | 96 % | 50.7 % / +133 % |
| χ² al 90 % | 5.8 % | 9.7 % | 56 % | 37.8 % / +223 % |
| Cota Q-profile al 90 % de los momentos | 9.4 % | 11.1 % | 56 % | 38.8 % / +211 % |
| **χ² al cuantil de η (95 % unilateral con level 0.9)** | **3.7 %** | 7.3 % (H 30) | 7.6 % | **30.8 % / +261 %** |

Las peores celdas son de pocas elecciones (decenas a cientos en 2 a 6 minas; los 56–96 % de RMR son celdas de
9–110 elecciones con umbral 0.01). Con RMR la χ² baja `worse_site` (H 30, 0.05) de p90 17.3 % a 0.8 %.

- La estimación por momentos sola sale más baja que σ̂_z y no ayuda; el piso casi no actúa (σ̂_z rara vez baja de
  0.3) y su valor solo lo respaldaría el generador (DE 0.4), igual que un prior: se descartaron.
- La Q-profile se parece a la χ² al 90 % y pide guardar los O/E por zona en el JSON; la χ² sale de lo que ya se
  guarda (`zone_sd` y las zonas del ajuste).
- Quedó la χ² al mismo cuantil que η: es la única que deja el p90 por mina bajo ~5 % en todas las celdas con ln Q.

### Recomendación, H = 365 días

Elige % de los tramos / demasiado liviano agrupado (conteo) / **por mina: p90 y máximo** entre las minas que eligen /
sobrecosto mediano frente al óptimo de verdad.

| Escenario | Umbral | Antes (§10) | Después |
|---|---:|---|---|
| `base` | 0.05 | 0.8 % / 3.4 % (11/321) / p90 5.2 %, máx 7.4 % (6 minas) / +144 % | 0.0 % / 0.0 % (0/2) / p90 0.0 %, máx 0.0 % (1 minas) / +195 % |
| `base` | 0.1 | 3.1 % / 2.2 % (28/1254) / p90 4.5 %, máx 5.0 % (8 minas) / +156 % | 0.3 % / 0.0 % (0/103) / p90 0.0 %, máx 0.0 % (4 minas) / +201 % |
| `worse_site` | 0.1 | 0.6 % / 5.3 % (10/189) / p90 6.5 %, máx 9.8 % (5 minas) / +126 % | 0 / sin elecciones |
| `shifted_correlation` | 0.05 | 1.7 % / 6.4 % (33/517) / p90 11.9 %, máx 17.2 % (5 minas) / +149 % | 0.3 % / 1.3 % (1/76) / p90 2.0 %, máx 2.4 % (3 minas) / +226 % |
| `shifted_correlation` | 0.1 | 4.1 % / 2.3 % (29/1237) / p90 3.6 %, máx 10.0 % (8 minas) / +134 % | 1.8 % / 1.1 % (6/527) / p90 1.9 %, máx 3.2 % (5 minas) / +220 % |
| `incoherent_practice` | 0.05 | 3.0 % / 1.9 % (17/898) / p90 1.4 %, máx 6.9 % (14 minas) / +285 % | 0.8 % / 4.1 % (10/245) / p90 3.7 %, máx 4.6 % (3 minas) / +445 % |
| `incoherent_practice` | 0.1 | 7.3 % / 0.1 % (2/2214) / p90 0.1 %, máx 1.0 % (17 minas) / +249 % | 1.9 % / 0.2 % (1/582) / p90 0.1 %, máx 0.3 % (9 minas) / +431 % |
| `mine_practice` | 0.05 | 0.5 % / 0.7 % (1/144) / p90 0.9 %, máx 1.1 % (3 minas) / +148 % | 0.1 % / 0.0 % (0/25) / p90 0.0 %, máx 0.0 % (2 minas) / +232 % |
| `mine_practice` | 0.1 | 2.2 % / 0.1 % (1/677) / p90 0.2 %, máx 0.3 % (4 minas) / +135 % | 1.2 % / 0.0 % (0/348) / p90 0.0 %, máx 0.0 % (2 minas) / +182 % |
| `noisy_mapping` | 0.05 | 0.9 % / 1.1 % (3/275) / p90 1.6 %, máx 1.8 % (2 minas) / +229 % | 0.2 % / 1.6 % (1/64) / p90 1.6 %, máx 1.6 % (1 minas) / +167 % |
| `noisy_mapping` | 0.1 | 1.7 % / 0.2 % (1/526) / p90 0.3 %, máx 0.4 % (3 minas) / +187 % | 0.7 % / 0.0 % (0/220) / p90 0.0 %, máx 0.0 % (2 minas) / +347 % |
| `large_mine` | 0.05 | 26.5 % / 1.1 % (283/25435) / p90 1.9 %, máx 4.4 % (19 minas) / +260 % | 9.5 % / 0.5 % (48/9115) / p90 0.8 %, máx 1.3 % (14 minas) / +334 % |
| `large_mine` | 0.1 | 50.8 % / 1.3 % (646/48735) / p90 2.1 %, máx 8.1 % (19 minas) / +133 % | 30.8 % / 0.7 % (204/29520) / p90 0.5 %, máx 4.6 % (19 minas) / +261 % |
| `saturating_large` | 0.05 | 39.0 % / 1.3 % (467/37349) / p90 2.7 %, máx 3.9 % (18 minas) / +114 % | 26.3 % / 0.6 % (142/25199) / p90 1.4 %, máx 2.2 % (18 minas) / +187 % |
| `saturating_large` | 0.1 | 53.7 % / 1.5 % (772/51356) / p90 3.5 %, máx 4.8 % (18 minas) / +97 % | 41.8 % / 0.5 % (218/40009) / p90 1.3 %, máx 2.6 % (18 minas) / +146 % |
| `saturating_worse` | 0.05 | 0.9 % / 3.4 % (9/267) / p90 5.5 %, máx 6.7 % (7 minas) / +132 % | 0.3 % / 0.0 % (0/82) / p90 0.0 %, máx 0.0 % (5 minas) / +200 % |
| `saturating_worse` | 0.1 | 2.7 % / 2.6 % (21/805) / p90 6.0 %, máx 7.5 % (9 minas) / +123 % | 1.1 % / 0.6 % (2/343) / p90 0.8 %, máx 1.6 % (6 minas) / +184 % |

### Recomendación, H = 1095 días

| Escenario | Umbral | Antes (§10) | Después |
|---|---:|---|---|
| `base` | 0.05 | 0.0 % / 0.0 % (0/6) / p90 0.0 %, máx 0.0 % (1 minas) / +81 % | 0 / sin elecciones |
| `base` | 0.1 | 0.3 % / 6.2 % (8/128) / p90 12.4 %, máx 14.6 % (3 minas) / +125 % | 0 / sin elecciones |
| `shifted_correlation` | 0.1 | 0.6 % / 2.6 % (5/193) / p90 5.5 %, máx 7.0 % (5 minas) / +190 % | 0.0 % / 0.0 % (0/1) / p90 0.0 %, máx 0.0 % (1 minas) / +500 % |
| `incoherent_practice` | 0.05 | 0.2 % / 0.0 % (0/46) / p90 0.0 %, máx 0.0 % (4 minas) / +350 % | 0.2 % / 2.0 % (1/50) / p90 2.0 %, máx 2.0 % (1 minas) / +147 % |
| `incoherent_practice` | 0.1 | 1.6 % / 1.9 % (9/481) / p90 0.0 %, máx 5.1 % (12 minas) / +287 % | 0.5 % / 2.8 % (4/144) / p90 2.3 %, máx 2.8 % (3 minas) / +500 % |
| `mine_practice` | 0.1 | 0.1 % / 0.0 % (0/26) / p90 0.0 %, máx 0.0 % (2 minas) / +150 % | 0 / sin elecciones |
| `noisy_mapping` | 0.05 | 0.0 % / 0.0 % (0/10) / p90 0.0 %, máx 0.0 % (1 minas) / +109 % | 0 / sin elecciones |
| `noisy_mapping` | 0.1 | 0.5 % / 0.7 % (1/151) / p90 0.9 %, máx 1.0 % (2 minas) / +252 % | 0.0 % / 0.0 % (0/13) / p90 0.0 %, máx 0.0 % (1 minas) / +162 % |
| `large_mine` | 0.05 | 1.6 % / 2.7 % (41/1514) / p90 15.3 %, máx 18.2 % (6 minas) / +108 % | 0.3 % / 0.7 % (2/300) / p90 0.7 %, máx 0.7 % (1 minas) / +133 % |
| `large_mine` | 0.1 | 12.9 % / 1.3 % (155/12371) / p90 1.8 %, máx 4.4 % (19 minas) / +310 % | 4.1 % / 0.6 % (24/3941) / p90 1.7 %, máx 2.0 % (8 minas) / +283 % |
| `saturating_large` | 0.05 | 15.1 % / 0.7 % (105/14434) / p90 1.3 %, máx 1.7 % (18 minas) / +156 % | 7.9 % / 0.5 % (36/7552) / p90 0.7 %, máx 1.1 % (11 minas) / +168 % |
| `saturating_large` | 0.1 | 30.3 % / 1.1 % (316/29002) / p90 2.3 %, máx 3.4 % (18 minas) / +130 % | 19.2 % / 0.4 % (82/18406) / p90 0.8 %, máx 1.3 % (17 minas) / +193 % |
| `saturating_worse` | 0.05 | 0.2 % / 0.0 % (0/58) / p90 0.0 %, máx 0.0 % (3 minas) / +119 % | 0.0 % / 0.0 % (0/15) / p90 0.0 %, máx 0.0 % (1 minas) / +83 % |
| `saturating_worse` | 0.1 | 0.5 % / 6.9 % (10/145) / p90 9.4 %, máx 9.6 % (5 minas) / +106 % | 0.2 % / 0.0 % (0/63) / p90 0.0 %, máx 0.0 % (1 minas) / +93 % |

`ngi_site`, `better_site`, `conservative_practice` y `small_mine` siguen sin ninguna elección.

### Contra la meta

| Meta | Antes (§10) | Después |
|---|---|---|
| Por mina, p90 de «demasiado liviano» ≤ ~5 % | No: 11.9 % `shifted_correlation` (0.05), 6.5 % `worse_site`, 6.0 % `saturating_worse`, 15.3 % `large_mine` H 1095 | **Cumple** en todas las celdas: el peor p90 es 3.7 % (`incoherent_practice`, 0.05, H 365) |
| Máximo por mina | 17.2 % | 4.6 % (la mina de `large_mine` con σ̂_z = 0.21: 154/3354, antes 297/3670) |
| Agrupado < 5 % | No en `worse_site` (5.3 %), `shifted_correlation` 0.05 (6.4 %), `base` y `saturating_worse` con H 1095 (6.2 % y 6.9 %) | **Cumple** en todas: el mayor es 4.1 % (`incoherent_practice`, 0.05, H 365, 10/245) |
| Sin subir el sobrecosto ni bajar la elección | — | **No cumple.** `large_mine` (0.10, H 365) elige en el 30.8 % de los tramos (antes 50.8 %) con sobrecosto +261 % (antes +133 %); `saturating_large` 41.8 % (53.7 %) y +146 % (+97 %); `worse_site` ya no elige; en las minas de 600–800 tramos la elección cae a 0–2 % |

**El costo:** la seguridad se compró otra vez con sostenimiento y con menos elecciones. Con 5 zonas la cota es
2.4 veces σ̂_z, así que las minas de ≈ 600 tramos casi no eligen: en ese tamaño el módulo dice «ningún tipo cumple»
en vez de arriesgar.

**Límite de fondo:** con pocas zonas σ_z no se conoce. La cota lo cubre con más sostenimiento, no con más
información, y una mina cuyas zonas de entrenamiento salieron muy parecidas entre sí todavía puede quedar corta (la
de σ̂_z = 0.21 baja de 8.1 % a 4.6 %, no a cero). La salida de fondo es más zonas en el histórico o un efecto de zona
en la media cuando la zona del tramo nuevo es conocida.
