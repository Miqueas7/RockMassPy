# Tramos, lote e informe

Datos inventados (no son de ninguna mina; las coordenadas también). Necesitas los extras:
`pip install "rockmasspy[io,viz,report]"`. Corre con `python informe.py <carpeta>`; reutiliza el catálogo y las tablas
del ejemplo 02 y solo imprime el resumen (conteos y nombres de archivo), nunca filas de tramos.

Qué hace, en orden:

1. Escribe una hoja `Tramos` sintética en Excel y en CSV: 2 labores, 12 tramos con progresivas y coordenadas en datum
   `WGS84 UTM 18S`. Un tramo es de una rampa, que no tiene tabla: queda sin clasificar (`clase=None`) y se cuenta aparte.
2. Clasifica los tramos con las tablas del ejemplo 02 y guarda los resultados en `resultados.xlsx`.
3. Genera la memoria de cálculo y el Anexo 39 B, cada uno en HTML y en Word.
4. Corre la CLI `rockmass` (`classify` y `report`) con `main([...])`. Terminan con código 2 porque hay un tramo sin tabla.

`main` devuelve `{"files": [...], "total": 12, "classified": 11, "unclassified": 1, "exit_codes": {...}}`.
Todo es sintético: ninguna cifra sirve para diseñar.

La librería recomienda, el ingeniero decide.
