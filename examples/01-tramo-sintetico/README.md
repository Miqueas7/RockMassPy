# Tramo sintético

Datos inventados (no son de ninguna mina). Corre con `python tramo.py` después de instalar la librería.

Entradas: UCS = σci = 90 MPa, RQD 65, espaciado 0.25 m, JCond89 = 18, húmedo, orientación regular, túnel;
Q con Jn 9, Jr 1.5, Ja 2, Jw 1, SRF 1; mi = 25, D = 0, HB-2018, profundidad 400 m, γ = 0.027 MN/m³.
El GSI sale de `gsi_from_jcond89_rqd` (GSI cuantificado, no una correlación).

| Resultado | Valor | method_id |
|---|---|---|
| RMR89 (7 + 13 + 10 + 18 + 10 − 5) | 53 | RMR89 |
| Q | 5.4167 | Q-NGI-2025 |
| GSI | 59.5 | GSI-2013 |
| φ' | 52.75° | HB-2018 |
| c' | 2.633 MPa | HB-2018 |
| Erm simplificado | 19 637.7 MPa | HD-2006 |

La librería calcula y avisa; no recomienda sostenimiento. La librería recomienda, el ingeniero decide.
