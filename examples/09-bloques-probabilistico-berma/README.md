# Ejemplo 09 · Bloques, probabilidad de falla y banco-berma

Cinco bloques de un tajo inventado, con datos sintéticos tomados de casos publicados y pasados a kN. Nada de este
ejemplo viene de una mina.

```bash
pip install "rockmasspy[io,viz,report]"
python bloques.py salida/
```

Escribe `Familias.csv`, `Taludes.csv`, `Bloques.csv` y `Distribuciones.csv`; evalúa los taludes (3A) y los bloques (3B)
con semilla 9; guarda `bloques_resultados.csv`, el histograma y la curva de PoF del planar (`fs_hist_1.png`,
`fs_cdf_1.png`), el informe `bloques.html` (y `bloques.docx` si hay python-docx) y corre `rockmass slope --blocks`.
Termina con código 0; la CLI termina con **2** (algo pide atención, ver más abajo).

## Qué calcula cada bloque

| Bloque | Modelo | Caso publicado | Resultado |
|---|---|---|---|
| B1 | planar (Hoek y Bray) con grieta de tracción crítica al 90 % de agua, sismo 0.08 y retroanálisis | Sau Mau Ping, RocPlane problema 1 | FS 1.065; PoF cercana a 7 % |
| B2 | cuña por resolución vectorial, dos planos, agua por junta y carga externa | CU-2, SWedge problema 6 (Priest 1993) | FS 1.497, un solo valor |
| B3 | volteo de Goodman y Bray, 16 bloques, cable en el pie de 2013 kN | VO-1, ejemplo 1b | FS 0.9999 (cuenta como 1.0) |
| B4 | banco-berma: banco de 12 m, berma de 12 m, cara de 65 grados con distribución | Ryan y Pryor (2000), fig. 3.8 | Ritchie 6.9 m; confiabilidad cercana a 95 % |
| B5 | planar con un plano de 60 grados bajo una cara de 50 | inventado | el bloque no se forma |

Solo B1 (las cinco variables de Sau Mau Ping) y B4 (el ángulo de la cara) tienen distribuciones. Los demás se
evalúan una sola vez.

## Lo que hay que leer dos veces

- **La PoF depende de las distribuciones que tú eliges.** Con las del ejemplo sale cerca de 7 % (Hoek publica 6.4 %
  con su corrida). Si cambias la desviación de φ de 5 a 3 grados, la PoF baja a cerca de 5 %: la librería no sabe cuánto varía
  tu macizo, solo propaga lo que le das. Las variables se truncan en los límites de la hoja.
- **La semilla fija la corrida.** Con la misma semilla, el mismo número de muestras y las mismas hojas, la PoF sale
  idéntica en cualquier máquina. Cambiar la semilla mueve la PoF menos de un punto (de 6.6 a 7.4 % con las semillas 1, 2, 3, 9 y 10); si se
  mueve más, faltan muestras.
- **El FS igual a 1 cuenta como falla** (con holgura de 1e-9). Por eso B3, que da 0.9999, pide atención.
- **La PoF es condicional a que el bloque se forme**; las muestras que no forman bloque se cuentan aparte (`n` y
  `n_valid`). Una muestra con despegue cuenta como falla.
- **La librería no dice «aceptable».** Un FS bajo 1 es mecánica: el equilibrio no se cumple. Un FS de 1.065 o una PoF
  de 7 % solo se leen contra un criterio (Read y Stacey, DS 024, el de tu mina), y los criterios llegan con la 3D.
  Además, el análisis es 2D por metro de talud: un bloque 3D tiene más resistencia en sus extremos. Por eso la PoF, la
  confiabilidad de berma y la comparación con Ritchie se informan y no cambian el código de salida; solo lo hacen un
  FS bajo 1 y los avisos.

## Cómo se lee la curva y el retroanálisis

- **Histograma del FS** (`fs_hist_1.png`): las barras con FS < 1 van rayadas y su suma es la PoF. El borde 1.0 es
  un borde de barra, no hay barras mezcladas.
- **Curva de PoF** (`fs_cdf_1.png`): la curva acumulada corta FS = 1 a la altura de la PoF.
- **Retroanálisis** (B1, `retroanalisis = si`): para φ de 10 a 50 grados cada 5, la cohesión que da FS = 1. En B1, la
  curva c–φ llega a c = 0 con φ cercano a 50 grados (`phi_c0_grados` en el archivo de resultados): si el talud estuviera
  justo en equilibrio y sin cohesión, esa sería la fricción. Cualquier par (c, φ) sobre la curva da FS = 1.
- **Confiabilidad de berma** (B4): el porcentaje de bermas con ancho final mayor que el requerido (aquí el de Ritchie,
  0.2 H + 4.5 m). El ancho sale de la cara muestreada y del ángulo interrampa de diseño. Un ancho igual al requerido
  no cumple.

## Privacidad

`id_bloque` e `id_talud` salen solo en las tablas del informe y en `bloques_resultados.csv`, nunca en la CLI ni en las
figuras (que llevan el número de orden). Las columnas ajenas (`codigo_mina`, `zona_nivel`, `observaciones`, `este_m`,
`norte_m`) no se leen. Los nombres de `familia` salen en avisos de la CLI: no les pongas códigos de labor ni de mina.
