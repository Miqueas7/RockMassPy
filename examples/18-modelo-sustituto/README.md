# Ejemplo 18: modelo sustituto

Todo es sintético. `python main.py [carpeta]` genera 300 corridas de un talud planar en 10 escenarios (cada uno con su
inclinación del plano y su altura), las guarda en `corridas.csv` como si las hubiera exportado Slide2, y luego:
(1) valida el sustituto agrupado por escenario y aleatorio (la validación agrupada sale peor, y es la honesta);
(2) compara la PoF de `poly2` y de `rbf` contra la verdad de `run_probabilistic` (en este banco `poly2` da 1,5 veces
la verdad aunque su validación parece buena); (3) muestra que una extrapolación se rechaza (FS = nan). Imprime solo
números.

El sustituto no extrapola, se valida por escenario y no reemplaza la corrida final en el programa de origen.
