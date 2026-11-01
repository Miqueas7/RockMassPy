# Cartillas y gráficos

Datos inventados (no son de ninguna mina). Necesitas el extra de gráficos: `pip install "rockmasspy[viz]"` (requiere
matplotlib 3.8 o superior). Corre con `python graficos.py <carpeta>`; reutiliza el catálogo y las tablas del ejemplo 02.
La semilla es fija, así que las figuras salen siempre iguales.

| Archivo | Qué muestra |
|---|---|
| `cartilla_celdas.png` y `.pdf` | Cartilla de celdas de Vallejo (tajeo) con las líneas RMR′ digitalizadas y su fuente en el pie |
| `cartilla_rango.png` | Cartilla de rangos RMR89 (galería) con la leyenda del catálogo |
| `gsi_cuantificada.svg` | Carta GSI cuantificada (JCond89 contra RQD) con 5 puntos |
| `envolventes.png` | Envolventes Hoek-Brown (HB-2018) σ1–σ3 y τ–σn, con su ajuste Mohr-Coulomb y 4 ensayos dentro del rango de σ3 |
| `correlacion.png` | Dispersión Q–RMR89 con la correlación global `RmrFromQ_Huang2026` |
| `histograma.png` | Conteo de RMR89 por clase de la tabla, con el color del sostenimiento |
| `tabla_csv/` | La tabla del tajeo con `rating` guardada en CSV (`;` y BOM UTF-8) y leída de vuelta |

`main` devuelve `{"files": [...], "csv_roundtrip_ok": True}`. Todo es sintético: ninguna cifra sirve para diseñar.

La librería recomienda, el ingeniero decide.
