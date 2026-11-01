# Tabla de sostenimiento por labor

Datos inventados (no son de ninguna mina). Corre con `python tabla.py` después de instalar la librería con el extra
de lectura y escritura: `pip install "rockmasspy[io]"` (YAML y Excel lo necesitan).

Arma un catálogo de 5 tipos de sostenimiento (I a V, del más liviano al más pesado), una tabla RMR89 para galerías
(luz de 3 a 4 m) y una tabla de celdas GSI para tajeos (luz de 4 a 8 m, las 18 celdas de la cartilla, sin saltos
hacia un sostenimiento más liviano). Valida ambas, clasifica y guarda cada tabla en JSON, YAML y Excel, y la lee de nuevo.

| Resultado | Valor |
|---|---|
| Galería, RMR 53, luz 3.5 m (base `RMR89`) | sostenimiento III |
| Tajeo, celda MF/R, luz 6 m (base `GSI-Vallejo-Osinergmin2017`) | sostenimiento III |
| Avisos de validación, galería | 0 |
| Avisos de validación, tajeo | 0 |
| `roundtrip_ok` | True |

La librería recomienda, el ingeniero decide.
