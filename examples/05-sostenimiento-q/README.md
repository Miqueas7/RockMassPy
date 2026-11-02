# Sostenimiento con la carta Q

Datos inventados (no son de ninguna mina) y el caso público de Hoek. Necesitas los extras:
`pip install "rockmasspy[io,viz,report]"`. Corre con `python sostenimiento.py <carpeta>`; reutiliza las tablas del
ejemplo 02 y solo imprime el resumen, nunca filas de tramos.

Qué hace, en orden:

1. Cámara de Hoek (Q 4.5, luz 15 m, categoría ESR C): la carta digitalizada da la **categoría 3**. Hoek publica 4
   porque lo leyó en una carta anterior (1993); la diferencia se anota en el CHANGELOG, no se fuerza.
2. Paredes de Q 0.4 (luz 4.5 m, altura 4.5 m) en las dos ediciones: Q de pared 1.0 en 2015 y 0.4 en 2025.
3. Escribe 8 tramos sintéticos con `q_valor`, los clasifica con tus tablas, agrega la referencia de la carta con
   `{"*": "C"}` y guarda `resultados.csv` y `resultados.xlsx`.
4. Guarda `carta.png` (la carta con los tramos, sin rótulos) y `memoria.html` con la sección 5.1.
5. Corre la CLI (`qsupport` y `classify --esr`) con `main([...])`; ambas terminan con código 0.

La referencia de la carta no cambia la clasificación de tus tablas. La librería recomienda, el ingeniero decide.
