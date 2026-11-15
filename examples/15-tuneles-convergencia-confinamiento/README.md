# Ejemplo 15 · Túneles: convergencia-confinamiento

Todo es sintético, salvo el RST Ejemplo 1 (RocSupport Tutorial, Rocscience), que es un caso publicado. Los códigos de
sostenimiento son `ZZSENT-PB` y `ZZSENT-SC`.

```bash
python main.py salida/
```

## Qué hace

1. **RST Ejemplo 1:** Hoek-Brown con `a` distinto de 0.5 (equivalente Mohr-Coulomb al estilo RocSupport), un perno de
   34 mm de la tabla de Hoek, LDP de Chern. Debe dar FS 1.84, rp 13.8 m y ε 2.03 %.
2. **Túnel sintético en Mohr-Coulomb con ψ:** el sostenimiento sale de una hoja de capacidades que `main.py` escribe en
   la carpeta de salida; se combinan perno y shotcrete por rigidez y se compara con el perno solo y sin sostenimiento.
3. **Coherencia de Hoek-Brown:** una tabla inventada declara D = 0.5, pero sus `mb` y `s` salen con D = 0;
   `check_hoek_brown` lo avisa y devuelve el D implícito.
4. **Capacidad M-N de un shotcrete** (Carranza-Torres y Diederichs 2009) y los pares (N, M) del revestimiento elástico
   de Einstein y Schwartz (1979) en tres ángulos.

## Qué mirar

- **Sin cruce no hay FS:** si el sostenimiento no alcanza la curva del terreno, el FS es `None` y hay un aviso.
- **Los avisos y las notas** nunca repiten valores de entrada; el equivalente Mohr-Coulomb avisa que mezcla el σcm
  global con el φ del ajuste, como RocSupport.
- La GRC supone túnel circular, K = 1 y pequeñas deformaciones; fuera de eso hay un aviso, no un error.
