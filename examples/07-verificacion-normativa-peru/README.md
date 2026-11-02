# Verificación normativa (Perú, DS 024-2016-EM)

Datos inventados (no son de ninguna mina). Necesitas los extras: `pip install "rockmasspy[io,viz,report]"`. Corre con
`python verificar.py <carpeta>`; solo imprime conteos por estado, códigos de salida y nombres de archivo, nunca el
contenido de las entradas.

Qué hace, en orden:

1. Escribe dos tablas por labor (`galeria.json` con RMR y luz, `rampa.json` con Q), `Tramos.csv` con 8 tramos,
   `Superficies.csv` con 3 caras de tajeo y los cinco CSV de diseño. Cada hoja tiene al menos una fila que no cumple.
2. Llama a `verify` con el perfil `PE-DS024-2016` y `as_of="2026-11-02"`, y escribe `verificacion.html` y, si está
   `python-docx`, `verificacion.docx`.
3. Corre `rockmass verify` con `main([...])` sobre los mismos archivos y escribe `verificacion_cli.html`.

Los dos caminos salen con código 2: hay ítems que no cumplen o piden atención.

## Qué revisa cada hoja de diseño

| Hoja | Qué revisa |
|---|---|
| `Estaciones_refugio` | Anexo 19: RMR mayor que 60 (o sostenimiento declarado), distancia al frente no mayor a 500 m, área no menor a 1.5 m² por persona. |
| `Refugios_peatonales` | Arts. 214 i) y 216: espaciamiento máximo de 50 m en galerías y otras labores; en rampas, 50 m en tangente larga y 30 m en tangente corta o curva. |
| `Resumen_QC` | Art. 214 b): por mes y tipo de sostenimiento, ensayos de control de calidad de no menos del 1 % de lo instalado. |
| `Factores_seguridad` | Guía de Osinergmin, Tabla 5-1 (excavaciones subterráneas): 1.1 a corto plazo, 1.3 a mediano, mayor que 1.5 a largo. |
| `Autosoporte` | Guía de Osinergmin, 8.4: con 20 h o menos se aplica el art. 213. El tiempo lo declaras tú, la librería no lo calcula. |

Los tramos, las tablas y las caras alimentan el art. 214 g) (luz dentro del rango de la tabla, sin revisar la altura),
el art. 33 (contenido de las tablas) y el punto 4.1 del Anexo 39 B (cálculo empírico).

## Cómo leer el resultado

- Un ítem de la **guía** pide atención, nunca sale «no cumple»; solo la **ley** (el reglamento) puede no cumplirse.
- **«No verificable por la librería» no es un incumplimiento.** Es lo procedural (estudio firmado, publicación en la
  labor, servicios de la estación de refugio): lo revisa el ingeniero.
- **«No revisado»** quiere decir que no diste datos para ese requisito.
- La librería nunca dice «aprobado»: un «cumple» solo confirma el límite numérico que pudo revisar.
- Los identificadores de fila (`id_refugio`, `id_via`, `id_analisis`, `id_tramo`) no salen en la consola ni en el informe.
