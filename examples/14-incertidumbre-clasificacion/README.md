# Ejemplo 14 · Incertidumbre en las clasificaciones

Todo es sintético: 6 tramos (`ZZSENT-1` a `ZZSENT-6`), una tabla RMR89 para las galerías y una tabla Q para los
cruceros. La librería informa la incertidumbre, no la juzga: ninguna regla de atención cambia.

```bash
pip install "rockmasspy[io]"
python main.py salida/
```

## Qué hace

1. `escribir_entradas.py` arma `entradas.xlsx` con las hojas `Tramos` y `Distribuciones` (una variable aleatoria por
   fila: `normal` o `uniforme`, truncada entre `minimo` y `maximo`).
2. `rm.classify_tramos(..., distributions=...)` clasifica cada tramo y agrega la probabilidad de cada clase de su
   tabla (LHS, 2000 muestras, semilla 1). La clase determinística no cambia.
3. `rm.classification_uncertainty("RMR89", ...)` propaga la incertidumbre de la resistencia y del RQD de un tramo con
   las curvas discretas de Bieniawski y con las continuas (Kundu et al. 2020), y compara media, p05, p95 y la
   probabilidad de cada clase.

## Qué mirar

- **Probabilidad de la clase más probable.** Un tramo con 60 % no es «clase III»: es 60 % clase III y 40 % la vecina.
- **Cerca de un borde** la clasificación avisa `near the boundary between classes ...` (RMR y GSI a 3 puntos o
  menos; Q dentro de un factor 1.25). Son valores provisionales por confirmar.
- **Las curvas continuas** (`RMR89-continuous`) no redondean ni saltan entre clases de puntaje; son un ajuste a las
  gráficas de Bieniawski (1989), por confirmar contra el artículo.
- **Las distribuciones las eliges tú.** La librería solo propaga lo que le das.
- Si una muestra cae fuera del dominio del cálculo (RQD mayor que 100, Jn igual a 0) hay un error que nombra la
  variable; acota su mínimo y su máximo.

Por línea de comandos: `rockmass classify entradas.xlsx --tables galeria.json -o resultados.csv --distributions entradas.xlsx`.
