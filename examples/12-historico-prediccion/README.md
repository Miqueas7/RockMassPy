# Ejemplo 12 · Histórico de la mina: del dato a la recomendación

El modelo predictivo de sostenimiento en dos partes:

- **Parte 1** (`historico.py`, Fase 4A): leer el histórico geomecánico con la plantilla, auditarlo y ajustar las
  correlaciones propias del sitio (nivel 1).
- **Parte 2** (`prediccion.py`, Fase 4B y 4C): auditar la práctica de sostenimiento (nivel 2), ajustar y validar el
  modelo de desempeño (nivel 3), guardarlo en JSON, recomendar para tramos nuevos con el umbral del ingeniero y
  escribir el informe completo con la lista TRIPOD+AI.

```bash
pip install "rockmasspy[io,ml,viz,report]"
python historico.py salida/
python prediccion.py salida2/
```

## Parte 1

### Qué es sintético

Todo. El histórico lo arma `rockmasspy.predictive.synthetic_history` (semilla 12): 4 zonas, 20 labores y unos 250
tramos con códigos inventados (`Z1`, `L001`, `T0001`) y litologías genéricas. Tiene un **mecanismo conocido**:
RMR = 9 ln Q + 44 y GSI = RMR − 5, más un efecto aleatorio por labor y por zona y el ruido de cada tramo. Por eso el
ejemplo puede comprobar que el ajuste **recupera** la pendiente verdadera dentro de su intervalo. Ningún número viene
de una mina, y nada de lo que el generador produce se entrega como modelo entrenado.

### Qué hace

1. Guarda el histórico como `historico.xlsx`, con las hojas de la plantilla (`Tramos`, `Tipos_sostenimiento` y
   `Desempeno`), y lo vuelve a leer con `rm.load_history`, igual que se leería el de una mina.
2. Lo audita con `rm.audit_history`: Q y RMR89 recalculados, registros no independientes, coherencia entre hojas y
   la preparación de cada nivel contra su mínimo. Los mínimos (30 pares de 5 labores en el nivel 1, por ejemplo)
   son una **decisión de diseño**, no un valor publicado, y así salen en el informe.
3. Ajusta los tres pares (`rmr_from_q`, `gsi_from_rmr` y `gsi_from_q_prime`) por litología y para toda la mina con
   `fit_site_correlation`: OLS con intervalo de predicción, bootstrap por labor y el bayesiano con la correlación
   global como *prior*. Cada ajuste queda «sitio», «inestable» o «no calibrada al sitio». Con esta semilla, el
   dominio D3 tiene solo 3 labores y queda «no calibrada al sitio».
4. Escribe el informe `historico.html` (y `historico.docx` si tienes python-docx): datos, auditoría de ingesta,
   preparación por nivel, nivel 1 con sus figuras y limitaciones.
5. Escribe los resultados en `resultados/` con `rm.save_history_findings` y `save_site_correlations`:
   - `history_findings.csv`: un hallazgo por fila, con su `id_tramo` y su fila;
   - `site_correlations.csv`: un ajuste por fila, con su dominio (aquí sí va la litología), n, labores, estado,
     a, b, sus IC y el *prior*;
   - `site_correlations.json`: solo las correlaciones con estado «sitio», en el formato `correlations` de las
     tablas por labor, para pegarlas en la tuya. Las «inestables» y las «no calibradas al sitio» se quedan en el CSV.

   Lo mismo se hace desde la terminal con `rockmass history historico.xlsx --correlations --output resultados/`,
   que sale con código 2 porque D3 no queda «sitio». El ejemplo tarda unos 3 s.

## Parte 2

### Qué es sintético

Otra vez todo. `synthetic_history` (semilla 0) arma un histórico más grande: 8 zonas, 96 labores y unos 1400 tramos,
con un **efecto real del sitio** sobre la falla (peor macizo, más luz y más exposición fallan más; más sostenimiento
falla menos) y una práctica coherente (peor macizo o más luz, sostenimiento más pesado). Con ese tamaño, el nivel 3
queda «propio del sitio»: con 250 tramos, como en la parte 1, no alcanza. Los tramos nuevos salen de otra semilla y
llevan ids inventados (`N001`…).

### Qué hace

1. Guarda y vuelve a leer el histórico (`historico_grande.xlsx`), lo audita y ajusta el nivel 1, como la parte 1.
2. **Nivel 2** con `audit_practice`: un logit acumulado del tipo instalado sobre ln Q, ln De, vida útil y tipo de
   labor, sin restricciones de signo. Dice si la práctica es coherente con el macizo y la luz, si es más predecible
   que la carta Q (kappa ponderado contra el ficticio y la línea base NGI, por partición) y qué tramos tienen un tipo
   instalado fuera de su conjunto conforme al 90 %. **Describe la práctica, no recomienda**: lo que la mina instaló
   no es necesariamente lo que debió instalar.
3. **Nivel 3** con `fit_performance`: P(falla) por tramo con restricciones de signo, validado por labor, por zona
   fuera y por año contra el ficticio y la línea base NGI. Sale «propio del sitio» solo si las particiones por labor
   y por zona superan a las dos referencias (IC 95 % de la mejora del Brier sobre cero) y la temporal no sale peor.
4. Guarda el modelo en `modelo.json` (coeficientes, rangos, métricas y conteos; **nunca filas ni ids**) y lo vuelve
   a leer con `load_model`.
5. Recomienda para 6 tramos nuevos (`tramos_nuevos.xlsx`) con `recommend`: P(falla) con su intervalo al 90 % para
   cada tipo y el más liviano cuyo límite superior queda bajo el umbral. El **umbral de ejemplo es 0.35 a 365 días**
   y lo fija el ingeniero según el costo de una falla en su labor: la librería no trae valor por defecto. Un tramo
   puede quedar sin elección (ningún tipo cumple, o hay extrapolación u otro motivo de bloqueo) y lo dice.
6. Escribe el informe completo `prediccion.html` (y `.docx`): datos, auditoría, preparación, nivel 1, nivel 2,
   nivel 3 con la curva de calibración y las isoprobabilidades por tipo al estilo de Mawdesley et al. (2001), la
   lista TRIPOD+AI (Collins et al. 2024) de lo que cubre y lo que no, y limitaciones. Todos los mínimos y umbrales
   van marcados como **decisión de diseño**.
7. Escribe en `resultados/` el `practice_results.csv` (un tramo por fila, con su conjunto conforme) y el
   `recomendaciones.csv` (un tramo × tipo por fila, con las columnas vacías `decision_ingeniero` y `motivo`, donde
   el ingeniero registra lo que decidió; con el desempeño posterior, alimentan el siguiente ajuste).

Lo mismo desde la terminal:

```bash
rockmass history historico_grande.xlsx --practice --performance --output resultados/ \
    --model-output modelo.json --report prediccion.html
rockmass recommend tramos_nuevos.xlsx --model modelo.json --threshold 0.35 --exposure-days 365 \
    --practice-from historico_grande.xlsx --output resultados/recomendaciones.csv
```

`history` sale con 2 si la práctica es incoherente o no significativa o si el nivel 3 no queda «propio del sitio»;
`recommend`, si algún tramo queda sin elección o con alerta. `recommend` imprime cada tramo por su posición (`tramo
1`, `tramo 2`…): el `id_tramo` va solo en el archivo de salida. La parte 2 tarda unos 10 s.

## Los históricos reales: privacidad

El histórico de una mina es un dato del cliente. Con uno real:

- **Se corre en local**, en la carpeta protegida de la mina, nunca en el repositorio ni en una carpeta
  sincronizada con terceros.
- La CLI y el informe muestran **conteos y códigos**, nunca la labor, la zona, las coordenadas ni la litología: los
  dominios salen como D1, D2… y el nombre del archivo de entrada no aparece en el informe. El `id_tramo` solo va en
  la tabla de hallazgos y en la de tramos fuera del conjunto conforme.
- Los archivos de `resultados/` sí traen el `id_tramo`, la fila y el dominio, porque la mina los necesita para
  corregir su histórico. Por eso **se quedan en la carpeta protegida**, como el histórico.
- El JSON de correlaciones y el del modelo llevan solo etiquetas, conteos y coeficientes; aun así, son de la mina.

La librería recomienda, el ingeniero decide.
