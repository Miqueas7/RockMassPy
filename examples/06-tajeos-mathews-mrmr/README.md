# Tajeos con Mathews y MRMR

Datos inventados (no son de ninguna mina). Necesitas los extras: `pip install "rockmasspy[io,viz,report]"`. Corre con
`python tajeos.py <carpeta>`; solo imprime el resumen (zonas, N′, MRMR y archivos), nunca el archivo de caras.

Qué hace, en orden:

1. Escribe `Superficies.csv` con 6 caras de un tajeo inventado: techo, tres paredes (dos por gravedad y una por
   deslizamiento) y dos caras con área y perímetro. Las demás usan ancho y largo.
2. Lee, evalúa con el gráfico de Potvin (1988) y guarda `resultados.csv` y `resultados.xlsx`.
3. Guarda `mathews.png` (gráfico con las caras, sin rótulos en los puntos) y `informe.html`.
4. Calcula el MRMR de Laubscher (1990) del caso de prueba (IRS 100, RQD 75, espaciamientos 0.5, 1 y 3 m) y lo ubica en
   el diagrama de Laubscher (1994) con HR = 30 m: `laubscher.png`.
5. Corre `mathews` y `mrmr` por la CLI con `main([...])`.

Hay una cara en transición y una en hundimiento a propósito: así se ven las tres zonas. El código de salida de
`mathews` es 2 cuando hay caras así (piden atención). La librería recomienda, el ingeniero decide.
