# Ejemplo 12 · Histórico de la mina: auditoría y correlaciones propias (parte 1)

Primer paso del modelo predictivo de sostenimiento (Fase 4A): leer el histórico geomecánico con la plantilla,
auditarlo y ajustar las correlaciones propias del sitio (nivel 1). Los niveles 2 (auditoría de la práctica) y 3
(desempeño y recomendación) llegan en la parte 2.

```bash
pip install "rockmasspy[io,ml,viz,report]"
python historico.py salida/
```

## Qué es sintético

Todo. El histórico lo arma `rockmasspy.predictive.synthetic_history` (semilla 12): 4 zonas, 20 labores y unos 250
tramos con códigos inventados (`Z1`, `L001`, `T0001`) y litologías genéricas. Tiene un **mecanismo conocido**:
RMR = 9 ln Q + 44 y GSI = RMR − 5, más un efecto aleatorio por labor y por zona y el ruido de cada tramo. Por eso el
ejemplo puede comprobar que el ajuste **recupera** la pendiente verdadera dentro de su intervalo. Ningún número viene
de una mina, y nada de lo que el generador produce se entrega como modelo entrenado.

## Qué hace

1. Guarda el histórico como `historico.xlsx`, con las hojas de la plantilla (`Tramos`, `Tipos_sostenimiento` y
   `Desempeno`), y lo vuelve a leer con `rm.load_history`, igual que se leería el de una mina.
2. Lo audita con `rm.audit_history`: Q y RMR89 recalculados, registros no independientes, coherencia entre hojas y
   la preparación de cada nivel contra su mínimo. Los mínimos (30 pares de 5 labores en el nivel 1, por ejemplo)
   son una **decisión de diseño**, no un valor publicado, y así salen en el informe.
3. Ajusta los tres pares (`rmr_from_q`, `gsi_from_rmr` y `gsi_from_q_prime`) por litología y para toda la mina con
   `fit_site_correlation`: OLS con intervalo de predicción, bootstrap por labor y el bayesiano con la correlación
   global como *prior*. Cada ajuste queda «sitio», «inestable» o «no calibrada al sitio». Con esta semilla, el
   dominio D3 tiene solo 3 labores y queda «no calibrada al sitio».
4. Escribe el informe `historico.html` (y `historico.docx` si tienes python-docx): datos, auditoría de ingesta,
   preparación por nivel, nivel 1 con sus figuras y limitaciones.
5. Corre `rockmass history historico.xlsx --correlations --output resultados/`, que escribe:
   - `history_findings.csv`: un hallazgo por fila, con su `id_tramo` y su fila;
   - `site_correlations.csv`: un ajuste por fila, con su dominio (aquí sí va la litología), n, labores, estado,
     a, b, sus IC y el *prior*;
   - `site_correlations.json`: las correlaciones en el formato `correlations` de las tablas por labor, para
     pegarlas en la tuya.

   La CLI sale con código 2: no hay hallazgos, pero D3 no queda «sitio». Tarda unos 5 s.

## Los históricos reales: privacidad

El histórico de una mina es un dato del cliente. Con uno real:

- **Se corre en local**, en la carpeta protegida de la mina, nunca en el repositorio ni en una carpeta
  sincronizada con terceros.
- La CLI y el informe muestran **conteos y códigos**, nunca la labor, la zona, las coordenadas ni la litología: los
  dominios salen como D1, D2… y el nombre del archivo de entrada no aparece en el informe. El `id_tramo` solo va en
  la tabla de hallazgos.
- Los archivos de `resultados/` sí traen el `id_tramo`, la fila y el dominio, porque la mina los necesita para
  corregir su histórico. Por eso **se quedan en la carpeta protegida**, como el histórico.
- El JSON de correlaciones lleva solo etiquetas, conteos y coeficientes; aun así, es de la mina.

La librería recomienda, el ingeniero decide.
