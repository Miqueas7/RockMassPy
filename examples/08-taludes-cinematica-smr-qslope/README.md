# Taludes: cinemática de Markland, SMR y Q-slope

Datos inventados (no son de ninguna mina). Necesitas los extras: `pip install "rockmasspy[io,viz,report]"`. Corre con
`python taludes.py <carpeta>`; solo imprime conteos, el código de salida de la CLI y nombres de archivo, nunca el
contenido de las entradas.

Qué hace, en orden:

1. Escribe con `random.Random(8)` dos tramos en `Familias.csv`. `T01` tiene tres familias de 25 polos cada una,
   alrededor de 45/180, 75/0 y 60/270 (dispersión de unos 8°). `T02` tiene tres familias suaves que buzan hacia dentro
   del macizo, alrededor de 25/0, 30/45 y 28/315. Escribe también `Taludes.csv` con tres caras: `TL1` 60/180 y `TL2`
   70/090 sobre `T01`, y `TL3` 45/180 sobre `T02`, con fricción, RMR básico, método de excavación y los parámetros de
   Q-slope (las dos primeras).
2. Llama a `assess_slopes`, guarda `resultados.csv` (26 columnas), dibuja un estereograma por modo crítico de la
   primera cara (si hay matplotlib) y escribe `taludes.html` y, si está `python-docx`, `taludes.docx`.
3. Corre `rockmass slope` con `main([...])` sobre los mismos archivos.

El código de salida es 2: dos caras piden atención.

## Qué debe salir

| Cara | Planar | Cuña (primaria + secundaria) | Volteo flexural | Volteo directo (oblicuo) | SMR discreto | SMR continuo | Q-slope y β |
|---|---|---|---|---|---|---|---|
| TL1 60/180 | 25 de 75 polos | 597 + 173 de 1875 | 25 de 75 | 17 (130) de 1875 | 4.0, clase V | 4.5, clase V | 0.54, β = 59.7°: **cara más empinada que β** |
| TL2 70/090 | 0 | 0 | 24 | 389 (95) | 50.0, clase III | 50.1, clase III | 11.3, β = 86.1° |
| TL3 45/180 | 0 | 0 | 0 | 0 (0) | 90.0, clase I | 89.7, clase I | sin Q-slope |

En total: 225 planos, 5625 intersecciones, 0 avisos y 0 notas. `TL3` es la cara sin nada crítico.

## Cómo leerlo

- **Los modos.**
  - *Planar*: un plano que aflora en la cara y buza más que la fricción, dentro del límite lateral.
  - *Cuña*: la línea de intersección de dos planos de familias distintas. En la zona **primaria** desliza por la línea
    (su inmersión supera la fricción y aflora en la cara). En la **secundaria** desliza sobre un solo plano.
  - *Volteo flexural*: planos que buzan hacia dentro del macizo, casi paralelos a la cara, con deslizamiento entre
    capas.
  - *Volteo directo*: intersecciones que buzan hacia dentro del macizo y son lo bastante empinadas. El **oblicuo**
    (fuera del límite lateral) se cuenta aparte.
- **Los porcentajes son factibilidad, no probabilidad.** Un «25 de 75 polos» dice que 25 polos caen en la zona crítica.
  No es una probabilidad de falla ni un factor de seguridad (eso es de las fases siguientes).
- **El límite lateral** (`limite_lateral_grados` de la hoja `Taludes`, 30° en las tres caras; si la celda va vacía
  se usa `--lateral-limit`, 30° por defecto) deja planar, flexural y volteo directo solo para las discontinuidades
  cuya dirección de buzamiento está a ±L de la de la cara. Un plano casi perpendicular a la cara no la libera. La
  cuña no usa límite lateral. Un límite menor deja menos polos críticos.
- **SMR discreto y continuo.** Las clases de Romana saltan por tramos; las funciones continuas de Tomás dan un valor
  suave. En este ejemplo quedan cerca: en `resultados.csv`, `TL1` da 4.0 y 4.5, `TL2` 50.0 y 50.1 y `TL3` 90.0 y
  89.7, y ninguna clase cambia. Pueden
  caer a lados distintos de un límite de clase: la hoja trae las dos lecturas y cada una con su propio caso que
  gobierna (`smr_caso` y `smr_caso_continuo`). Un valor justo en el límite toma la clase menos favorable.
- **Una cara más empinada que β.** β = 20·log10(Q-slope) + 65° es el ángulo más empinado que no pide refuerzo ni
  soporte. `TL1` tiene Q-slope 0.54 (β = 59.7°) y su cara buza 60°: la cara es más empinada que β, y la librería lo
  marca como atención aunque la cinemática no existiera. Con la cara exactamente igual a β también pide atención.

## Privacidad

Los nombres de `familia` salen en los avisos de la consola: no pongas en ellos códigos de labor ni de mina. Las
columnas ajenas (`codigo_mina`, `zona_nivel`, `observaciones`, coordenadas) no se leen. `id_talud` e `id_tramo` van
al archivo de resultados y a las tablas del informe, nunca a la consola ni a las figuras: las figuras se titulan con
el número de orden del talud.

La librería recomienda, el ingeniero decide.
