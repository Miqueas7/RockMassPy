# Ejemplo 13 · La mina sintética: el módulo predictivo medido contra la verdad

La mina sintética de la Fase 5 (`rockmasspy.predictive.synthetic_mine`) por la auditoría de ingesta y los niveles
1, 2 y 3, con la recomendación medida contra la **P verdadera de falla** que guarda el generador
(`MineTruth.p_fail`). Es lo que hace el banco de pruebas (`docs/investigacion/BANCO_MINA_SINTETICA.md` en el
repositorio) con una sola mina.

```bash
pip install "rockmasspy[io,ml]"
python mina_sintetica.py salida/
```

Tarda unos 6 s.

## Qué es sintético

Todo. `synthetic_mine("base", seed=30)` arma una mina **calibrada con la literatura**
(`docs/investigacion/CALIBRACION_MINA_SINTETICA.md`): 5 zonas, 40 labores y unos 800 tramos con códigos inventados
(`Z1`, `L001`, `T0001`) y litologías genéricas. El macizo verdadero sale de la geología (calidad por litología,
autocorrelación a lo largo de la labor, zonas de falla); los componentes, de esa calidad; Q, RMR89 y GSI se calculan
con la librería, así que la recta RMR–ln Q **emerge** y no se fija. Cada labor la mapea un geólogo que se equivoca;
la mina sostiene con su propia tabla por GSI, con desvíos y horas sin sostener; la falla tiene un mecanismo físico
simple con un sitio algo peor que NGI (δ = 0.5). La verdad (`MineTruth`) guarda los valores verdaderos y la P de
falla de cada tipo en cada tramo.

## Qué hace

1. Guarda la mina como `mina_base.xlsx` con las hojas de la plantilla (`rm.save_history_xlsx`), la vuelve a leer con
   `rm.load_history` y la audita con `rm.audit_history`.
2. **Nivel 1:** `fit_site_correlation(h, "rmr_from_q")` y compara la pendiente de la mina con la verdadera
   (`MineTruth.rmr_lnq_slope`, la OLS sobre los valores verdaderos).
3. **Nivel 2:** `audit_practice`: veredictos de signo y la consistencia de la práctica (Fase 5B).
4. **Nivel 3:** `fit_performance`: estado, forma (aditiva o con interacción), σ̂_z entre zonas y su cota superior χ²,
   avisos y bloqueos.
5. **Recomendación** con `recommend` (umbral de ejemplo 0.10 a 365 días, el del banco; lo fija el ingeniero) sobre
   una **segunda mina** del mismo escenario (semilla 1030): zonas y labores que el ajuste no vio, más exigente que una
   labor nueva en una zona conocida.
6. **Contra la verdad**, con `MineTruth.p_fail` de la segunda mina (P marginal de una labor nueva en la misma zona):
   - **demasiado liviano:** el tipo elegido tiene la P verdadera sobre el umbral;
   - **sobrecosto:** Σ costo elegido / Σ costo del óptimo de verdad − 1 (el óptimo es el tipo más liviano con P
     verdadera ≤ umbral; costo relativo I 1.0, II 1.6, III 2.4, IV 3.5, V 6.0), en los tramos que tienen óptimo. Es
     neto: un tipo demasiado liviano baja el costo;
   - lo mismo para la **carta Q** sola (con el Q registrado y De = luz/ESR) en los mismos tramos donde el modelo
     eligió y en todos, y para **lo que instaló la mina**. La equivalencia categoría de la carta → tipo
     (`CARTA_A_TIPO`) es la del generador; en tu mina la defines tú.

## Salida esperada

```text
mina base: 824 tramos, 80 fallas, 0 hallazgos de auditoría
nivel 1, RMR–ln Q de la mina: pendiente 6.13 (IC 5.47; 6.77), site; verdad 6.13
nivel 2: ready, ln Q coherent, ln De not significant, consistencia 0.586 (consistent)
nivel 3: site, forma additive, σ_z 0.35 (cota 0.83), bloqueos: ninguno
  aviso: only 5 zones: the between-zone SD (sigma_z) is poorly known; recommend uses its one-sided upper bound, 2.37 times the estimate at level 0.9
recomendación en 840 tramos nuevos (umbral 0.1, 365 días):
   539  no support type meets the threshold
   168  chosen
    88  the types that meet the threshold are not eligible
    45  input outside the training domain (extrapolation)
contra la verdad (50 tramos sin ningún tipo bajo el umbral):
  modelo              168 tramos, demasiado liviano 0.0 %, sobrecosto 177.3 %
  carta_en_elegidos   168 tramos, demasiado liviano 29.2 %, sobrecosto -18.6 %
  carta               840 tramos, demasiado liviano 34.4 %, sobrecosto -10.3 %
  instalado           840 tramos, demasiado liviano 20.0 %, sobrecosto 33.5 %
```

Cómo leerla:

- El modelo elige en el 20 % de los tramos nuevos y **ninguna elección queda demasiado liviana**, pero cuesta casi
  el triple que el óptimo de verdad: con 5 zonas la cota de σ_z es 2.4 veces σ̂_z y la seguridad se compra con
  sostenimiento. En el resto dice por qué no elige.
- La carta Q sola queda corta en un tercio de los tramos: este sitio es peor que NGI (δ = 0.5) y el nivel 3 lo
  aprende. Lo instalado por la mina queda corto en el 20 % y aun así sobrecuesta, porque su tabla lee el GSI
  registrado y tiene desvíos.
- **La semilla 30 se eligió porque es una de las minas `base` en que el modelo elige.** En el banco (50 minas
  `base`, umbral 0.10 y 365 días) el nivel 3 queda `site` en 13 y elige en 4 (0.3 % de los tramos, ninguno
  demasiado liviano); con `SEMILLA = 13` queda `partial` y no elige nada. Es lo esperable con ≈ 800 tramos y 5
  zonas: el módulo prefiere no recomendar a recomendar mal.

## Límites

- **Es un banco de pruebas.** La mina sintética nunca entrena un modelo que se entregue, no da *priors* ni
  coeficientes por defecto y nunca reemplaza el histórico de una mina. Lo que mide es cómo se porta el módulo con
  datos que se parecen a los de una mina, contra una verdad conocida.
- Los parámetros del generador salen de la literatura, pero varios son supuestos de diseño (tasas de falla, error
  entre geólogos, proporción por clase de una mina de vetas, zonas de falla por km): están marcados [S] en la
  calibración y quedan por confirmar.
- El mecanismo de falla es uno solo (déficit frente a la carta Q, `chart_deficit`); el banco también mide uno
  alternativo (`saturating`) para no ajustar el módulo a la receta del generador.
- Una mina y un umbral no son una estadística: las tasas por escenario y por mina están en el banco.

La librería recomienda, el ingeniero decide.
