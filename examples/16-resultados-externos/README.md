# Ejemplo 16: resultados de Slide2, RS2 y FLAC3D

Todo es sintético (ids `ZZSENT`). `python main.py [carpeta]` escribe cuatro archivos de entrada (FS por método y
sección tipo Slide2, SRF y strength factor por etapa tipo RS2, una tabla RocData con un D incoherente y un monitoreo
de convergencia), los lee con `load_external` y corre `assess_criteria` (READ-STACEY-2009, `ssr_policy="warn"`),
`compare_methods`, `compare_monitoring` contra un `analyze_tunnel` y `check_rocdata`. Imprime solo conteos.

## Qué exportar

- **Slide2:** *Export Raw Data* por método (o la tabla copiada a Excel), con método, id de sección, escala y consecuencia.
- **RS2:** SRF crítico y, por etapa, strength factor, desplazamientos, sigma 1 y sigma 3 (*Export Value at All Nodes*
  o *Plot in Excel*); fuerzas de pernos y revestimiento.
- **FLAC3D:** `flac3d_exportar.py`. Ajusta las variables del inicio (modelo, etapa, ruta de salida, unidades) y
  ejecútalo dentro de FLAC3D. FLAC3D usa tracción positiva; el guion lo invierte a compresión positiva.

No se leen archivos binarios (`.slmd`, `.fez`, `.f3sav`). No hay guiones de Rocscience porque necesitan licencia y no
se pueden probar aquí; consulta los manuales de `Slide2Scripting` y `RS2Scripting`.
