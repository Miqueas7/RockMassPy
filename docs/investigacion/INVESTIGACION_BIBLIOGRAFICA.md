# Investigación bibliográfica: librería Python de geomecánica minera con tablas personalizables

Fecha: 31-oct-2026. Alcance: solo fuentes públicas en la web (no se usaron archivos del equipo ni datos de clientes).

## Convención de verificación

Cada dato lleva una marca para que sepas cuánto confiar en él antes de pasarlo a código:

- **[V1]** verificado en la fuente primaria (leí el texto original o su copia del autor).
- **[V2]** verificado en una fuente secundaria seria (guía oficial, revisión indexada, metadatos Crossref) pero no en el original.
- **[NV]** no verificado en esta sesión: lo cito de conocimiento previo o de una sola fuente débil. **No lo pases a código sin revisar el original.**

Todos los DOI de la bibliografía se comprobaron contra la API de Crossref el 31-oct-2026 salvo los marcados [NV].

---

## Resumen ejecutivo

1. Las fórmulas centrales (Hoek-Brown 2002, módulo de Hoek-Diederichs 2006, GSI cuantificado 2013, RQD de Priest-Hudson y Palmström, RMR89, RMR14, ESR y reglas de pared del Q) se verificaron en texto original o en la guía de Osinergmin.
2. La práctica peruana tiene un origen documentado: **el «GSI modificado» se atribuye a C. Vallejo (2002), «Aplicaciones del Índice G.S.I. para el mapeo geomecánico y la definición del sostenimiento de labores mineras subterráneas», XI Congreso Peruano de Geología**, según la *Guía de criterios geomecánicos* de Osinergmin (2017), que además reproduce la tabla en su Anexo A.17. El trabajo original de Vallejo no está en línea (no lo pude leer).
3. La guía de Osinergmin (2017) **recomienda explícitamente que cada mina construya su propia correlación entre sistemas** a partir de datos crudos y que no se encadenen correlaciones. Eso respalda directamente el diseño de «tablas personalizables» de tu librería.
4. La norma vigente (DS 024-2016-EM modificado por DS 023-2017-EM y DS 034-2023-EM) obliga a publicar en cada labor «las tablas y planos geomecánicos que indiquen la calidad de roca, recomendaciones de sostenimiento y dimensionamiento». Desde el DS 034-2023-EM exige además un **estudio geomecánico global (Anexo 39 A)** y una **evaluación geomecánica local previa a toda labor subterránea (Anexo 39 B)**. No pude leer el contenido de esos anexos.
5. El artículo de Springer 2026 existe y está confirmado: Huang, Zhou, Khandelwal, Zvarivadza, Mpanza y Lawal, *Rock Mechanics and Rock Engineering*, publicado el 17-sep-2026, 448 pares Q–RMR, recalibra **RMR = 6.70 ln Q + 46.31** y concluye que una relación lineal global no basta.
6. El manual del Q de NGI tiene **revisión de abril de 2025** (no solo 2013/2015): cambia SRF a cinco categorías, renombra RRS I/II/III a A/B/C, reemplaza E500 por E700 y eleva a Q = 1 el límite para el ajuste de pared. Tu librería debe versionar el gráfico de sostenimiento por edición.
7. No existe hoy una librería Python mantenida y publicada que reúna RQD + RMR + Q + GSI + Hoek-Brown + Mathews + SMR con tablas configurables por mina. Hay piezas sueltas (QuickRMR, calculadoras web, groundhog para suelos, pyslope, mplstereonet/apsg). Ese es tu hueco.

---

## 1. RQD (Rock Quality Designation)

### Fuentes originales
- Deere, D. U. (1964). Technical description of rock cores for engineering purposes. *Rock Mechanics and Engineering Geology*, 1(1), 17–22. [V2: la cita aparece así en múltiples revisiones; sin DOI]
- Deere, D. U., Hendron, A. J., Patton, F. D. y Cording, E. J. (1967). Design of surface and near-surface construction in rock. *8th U.S. Symposium on Rock Mechanics*, 237–302. [NV]
- Deere, D. U. y Deere, D. W. (1988). The Rock Quality Designation (RQD) index in practice. En *Rock Classification Systems for Engineering Purposes*, ASTM STP 984, 91–101. doi:10.1520/STP48465S [V2 Crossref]. El informe extenso es Deere y Deere (1989), U.S. Army Corps of Engineers, Technical Report GL-89-1 [NV].

### Definición
```
RQD (%) = 100 · Σ(longitud de trozos de testigo sanos ≥ 10 cm) / longitud total de la corrida
```
Testigo de diámetro NX (≈ 54.7 mm) o mayor, sin contar roturas mecánicas de perforación. [V2]

### Estimaciones indirectas (verificadas en Hoek, Carter y Diederichs 2013, que las reproduce) [V1]
- Priest y Hudson (1976), con λ = discontinuidades por metro y umbral de 0.1 m:
  ```
  RQD = 100 · e^(−0.1·λ) · (0.1·λ + 1)
  ```
  Fuente: Priest, S. D. y Hudson, J. A. (1976). Discontinuity spacings in rock. *IJRMMS & Geomech. Abstr.*, 13(5), 135–148. doi:10.1016/0148-9062(76)90818-4 [V2 Crossref]
- Palmström (1982), con Jv = conteo volumétrico de juntas (juntas/m³):
  ```
  RQD = 115 − 3.3·Jv
  ```
- Palmström (2005), corrección con bloques simulados:
  ```
  RQD = 110 − 2.5·Jv
  ```
  Fuente: Palmström, A. (2005). Measurements of and correlations between block size and RQD. *TUST*, 20(4), 362–377. doi:10.1016/j.tust.2005.01.005 [V2 Crossref]. Recortes de rango (RQD = 100 si Jv < 4; RQD = 0 si Jv > 44): [NV].
- Jv = Σ (1/Sᵢ) para cada familia de espaciado medio Sᵢ, más juntas aleatorias/5 m [NV en el factor de las aleatorias].

### Validez y críticas
- RQD depende de la orientación del sondaje, del umbral de 10 cm y de la calidad de perforación; no ve el relleno ni la rugosidad.
- Pells, Bieniawski, Hencher y Pells (2017), «RQD: time to rest in peace», *Canadian Geotechnical Journal*, 54(6), 825–834, doi:10.1139/cgj-2016-0012 [V2 Crossref], proponen retirar RQD de RMR y Q por su sesgo y baja reproducibilidad. Es la crítica más fuerte y la firma el propio Bieniawski.
- Hoek et al. (2013) aceptan RQD en mapeo de frentes con cinta o fotografía (Hutchinson y Diederichs 1996). [V1]

### Qué implementar
- `rqd_from_core(trozos, longitud, umbral=0.10)`, `rqd_priest_hudson(lambda_, t=0.1)` (versión general con umbral t), `rqd_from_jv(jv, metodo="palmstrom2005")` con recorte a [0, 100].
- Avisar cuando la estimación sale de su rango de calibración.

---

## 2. RMR (Rock Mass Rating) de Bieniawski

### Fuentes originales
- Bieniawski, Z. T. (1973). Engineering classification of jointed rock masses. *Transactions of the South African Institution of Civil Engineers*, 15(12), 335–344. [V2 cita; sin DOI]
- Bieniawski, Z. T. (1976). Rock mass classification in rock engineering. En Bieniawski (ed.), *Exploration for Rock Engineering*, Proc. Symp. Johannesburg, Balkema, 1, 97–106. [NV en páginas]
- Bieniawski, Z. T. (1988). The Rock Mass Rating (RMR) system in engineering practice. ASTM STP 984, 17–34. doi:10.1520/STP48461S [V2 Crossref]
- Bieniawski, Z. T. (1989). *Engineering Rock Mass Classifications*. Wiley, Nueva York. [V2]
- Celada, B., Tardáguila, I., Varona, P., Rodríguez, A. y Bieniawski, Z. T. (2014). Innovating tunnel design by an improved experience-based RMR system. *World Tunnel Congress 2014*, Foz do Iguaçu, 1–9. [V2]

### RMR89: tablas de valoración (verificadas contra el Anexo A.15 de Osinergmin 2017) [V2]

| Parámetro | Rangos → puntaje |
|---|---|
| R1 Resistencia (UCS, MPa) | >250 → 15; 100–250 → 12; 50–100 → 7; 25–50 → 4; 5–25 → 2; 1–5 → 1; <1 → 0 |
| R1 alterno (Is50, MPa) | >10 → 15; 4–10 → 12; 2–4 → 7; 1–2 → 4; (<1: usar UCS) |
| R2 RQD (%) | 90–100 → 20; 75–90 → 17; 50–75 → 13; 25–50 → 8; <25 → 3 |
| R3 Espaciado | >2 m → 20; 0.6–2 m → 15; 200–600 mm → 10; 60–200 mm → 8; <60 mm → 5 |
| R4 Condición (máx. 30) | Persistencia: <1 m 6; 1–3 m 4; 3–10 m 2; 10–20 m 1; >20 m 0 · Apertura: ninguna 6; <0.1 mm 5; 0.1–1 mm 4; 1–5 mm 1; >5 mm 0 · Rugosidad: muy rugosa 6; rugosa 5; ligeramente rugosa 3; lisa 1; pulida 0 · Relleno: ninguno 6; duro <5 mm 4; duro >5 mm 2; blando <5 mm 2; blando >5 mm 0 · Meteorización: no 6; ligera 5; moderada 3; alta 1; descompuesta 0 |
| R5 Agua | seco 15; húmedo 10; mojado 7; goteo 4; flujo 0 |
| Ajuste orientación | Túneles: 0, −2, −5, −10, −12 · Cimentaciones: 0, −2, −7, −15, −25 · Taludes: 0, −5, −25, −50, −60 (muy favorable → muy desfavorable) |

Clases: I 81–100 muy buena; II 61–80 buena; III 41–60 regular; IV 21–40 mala; V ≤20 muy mala.

Significado de clases RMR89 [V2]: tiempo de autosoporte I 20 años para 15 m; II 1 año para 10 m; III 1 semana para 5 m; IV 10 h para 2.5 m; V 30 min para 1 m. Cohesión >400, 300–400, 200–300, 100–200, <100 kPa. Fricción >45°, 35–45°, 25–35°, 15–25°, <15°.

Matriz de orientación para túneles (rumbo perpendicular al eje: avance a favor del buzamiento 45–90° muy favorable, 20–45° favorable; en contra 45–90° regular, 20–45° desfavorable; rumbo paralelo: 45–90° muy desfavorable, 20–45° regular; buzamiento 0–20° cualquier rumbo: regular). [V2]

Nota de implementación: en la práctica R4 (JCond89) se usa también como entrada del GSI cuantificado, así que conviene exponerlo como función propia.

### RMR76 (Anexo A.16 de Osinergmin) [V2]
Diferencias con RMR89: espaciado >3 m 30; 1–3 m 25; 0.3–1 m 20; 50–300 mm 10; <50 mm 5; condición 25/20/12/6/0; agua 10/7/4/0. Autosoporte: I 10 años para 5 m; II 6 meses para 4 m; III 1 semana para 3 m; IV 5 h para 1.5 m; V 10 min para 0.5 m. Cohesión >300, 200–300, 150–200, 100–150, <100 kPa.

### RMR14 (estructura verificada en Osinergmin 2017, Anexo A.14) [V2]
- Cinco parámetros básicos, total 100: resistencia de la roca intacta (máx. 15), número de discontinuidades por metro (máx. 40, reemplaza a RQD + espaciado), condición de discontinuidades (máx. 20: continuidad <1 m 5, 1–3 m 4, 3–10 m 2, >10 m 0; rugosidad 5/3/1/0; relleno duro <5 mm 5, duro >5 mm 2, blando <5 mm 2, blando >5 mm 0; alteración 5/3/1/0), agua (15/10/7/4/0) y alterabilidad por slake durability Id2 (>85 % 10; 60–85 % 8; 30–60 % 4; <30 % 0).
- Las curvas de resistencia y de número de juntas son **gráficos continuos**: hay que digitalizarlos o tomar sus funciones de Celada et al. (2014) [NV: no encontré las funciones publicadas].
- Corrección:
  ```
  RMR14 = (RMRb + F0) · Fe · Fs
  F0 = ajuste por orientación (mismos valores que RMR89 para túneles)
  Fe (excavación con TBM): RMR < 40 → Fe = 1 + 2·(RMR/100)²
                           RMR > 40 → Fe = 1.32 − √(RMR − 40)/25
  Fs (plastificación del frente, según ICE):
      ICE < 15 → Fs = 1.3 ;  15 ≤ ICE ≤ 70 → Fs = 1.3 − 0.6·(ICE/100)² ;  ICE > 70 → Fs = 1.0
  ICE (Bieniawski y Celada 2011):
      K0 ≤ 1 → ICE = 3704·σci·e^((RMR−100)/24) / ((3 − K0)·H) · f
      K0 ≥ 1 → ICE = 3704·σci·e^((RMR−100)/24) / ((3·K0 − 1)·H) · f
      f = 1.3 (circular 6 m), 1.0 (circular 10 m), 0.75 (convencional 14 m), 0.55 (caverna 25×60 m)
  ```
  Las expresiones salen de la guía de Osinergmin, que las transcribe; el PDF tiene la fórmula de Fs con un símbolo dañado («GCI») que interpreto como ICE. Confírmalo en Celada et al. (2014) antes de codificar. [V2 con reserva]
- Correlación citada por Osinergmin: **RMR14 = 1.1·RMR89 + 2** [V2]. En la literatura española también circula «RMR14 ≈ RMR89 + 10» [NV].
- Funciones continuas para RMR89 y RMR14: Kundu, Sarkar, Singh y Singh (2020), *IJRMMS*, 129, 104280, doi:10.1016/j.ijrmms.2020.104280 [V2 Crossref], con el código QuickRMR en GitHub (jagadishkundu/QuickRMR). Es la mejor base para evitar saltos de puntaje en los límites de rango.

### Tiempo de autosoporte vs luz
- El ábaco de Bieniawski (1989) relaciona luz libre (m), tiempo (h) y RMR, con zonas de colapso inmediato y de excavación sin soporte. Es un **gráfico**, no una ecuación publicada por el autor.
- Osinergmin (2017, sección 8.4) recomienda incorporar el ábaco en la tabla geomecánica de cada labor y aplicar «labor avanzada, labor sostenida» (art. 213 del DS 024-2016-EM) si el tiempo leído es **≤ 20 horas** al entrar con Span/ESR vs RMR. [V2]
- En tesis peruanas circulan expresiones como «RMR (sin sostenimiento) = 22 ln De + 25» y «ancho máximo sin sostenimiento = ESR·exp((RMR − 25)/22)» (por ejemplo, en la tesis UNSAAC de Ancalla, sección 2.3.8.1). [NV: no encontré la fuente primaria; parece una inversión de la frontera del ábaco y debe verificarse]

### Críticas
- Lowson y Bieniawski (2013, RETC) reconocen el uso excesivo de RMR para sostenimiento [NV en detalle].
- Alejano (2024/2025), *RMRE*, 58(10), 11147–11167, doi:10.1007/s00603-024-04087-y [V2]: sistemas útiles pero a menudo mal usados.
- Liu, Feng y Jiao (2025), *Rock Mechanics Bulletin*, 4(3), 100205, doi:10.1016/j.rockmb.2025.100205 [V2]: critica sumar y multiplicar datos ordinales (problema de teoría de la medición). Argumento útil para que tu librería guarde siempre los parámetros crudos y no solo el índice.

### Qué implementar
RMR76, RMR89 (con tablas discretas y modo continuo tipo Kundu), RMR14 con F0/Fe/Fs/ICE, autosoporte como capa de ábaco digitalizado, y una tabla de equivalencia RMR → clase → sostenimiento **cargada desde archivo** (cada mina la reemplaza).

---

## 3. Sistema Q de Barton

### Fuentes
- Barton, N., Lien, R. y Lunde, J. (1974). Engineering classification of rock masses for the design of tunnel support. *Rock Mechanics*, 6(4), 189–236. doi:10.1007/BF01239496 [V2 Crossref]
- Grimstad, E. y Barton, N. (1993). Updating the Q-system for NMT. *Proc. Int. Symp. on Sprayed Concrete*, Fagernes, Norwegian Concrete Association, 46–66. [V2 citado por NGI 2025]
- Barton, N. (2002). Some new Q-value correlations to assist in site characterisation and tunnel design. *IJRMMS*, 39(2), 185–216. doi:10.1016/S1365-1609(02)00011-4 [V2 Crossref]
- NGI (2013, 2015, **abril 2025**). *Using the Q-system. Rock mass classification and support design* (manual). Oslo. La edición 2025 y su registro de cambios están en ngi.no [V1].

### Ecuaciones
```
Q  = (RQD/Jn) · (Jr/Ja) · (Jw/SRF)          [V1, NGI 2025]
Q' = Qbase = (RQD/Jn) · (Jr/Ja)              [V1]  (NGI: Q' NO sirve para diseñar sostenimiento)
De = luz (o altura de pared) [m] / ESR       [V1]
```
- Rango de Q: 0.001 a 1000. RQD < 10 se toma como 10. Intersecciones: 3·Jn; portales: 2·Jn. [V2/NV]
- ESR (NGI 2025, Tabla 4-1) [V1]: A labores mineras temporales 3–5; B piques circulares 2.5, rectangulares 2.0; C labores mineras permanentes, túneles de agua, pilotos 1.6; D túneles viales menores, accesos 1.3; E casas de fuerza, túneles viales mayores, intersecciones, portales 1.0; F estaciones, instalaciones públicas 0.8; G cavernas muy importantes de ~100 años 0.5. **Usar ESR = 1.0 cuando Q ≤ 0.1** en B, C y D.
- Ajuste de Q para paredes (NGI 2025, Tabla 4-2) [V1]: Q > 10 → ×5; 1 < Q < 10 → ×2.5 (salvo esfuerzos altos: Q real); Q < 1 → Q real; altura de pared > luz → Q real en todo el perfil. (En 2015 el límite inferior era 0.1; en 2025 sube a 1).
- Longitud de perno: el manual 2025 la da en el lado derecho del gráfico (ESR = 1). La fórmula clásica **L = 2 + 0.15·B/ESR** (Barton et al. 1974) [NV en esta sesión].
- Luz máxima sin soporte: **2·ESR·Q^0.4** (Barton et al. 1974; reproducida en tesis peruanas y en Hoek 1994) [V2 débil].
- Presión de soporte del techo: P = (2/Jr)·Q^(−1/3) (1974) o P = 2·Jn^(1/2)·Q^(−1/3)/(3·Jr) [NV].
- Barton (2002): Qc = Q·σc/100; Vp ≈ 3.5 + log10 Qc (km/s); Em ≈ 10·Qc^(1/3) (GPa) [NV en esta sesión; el DOI sí está verificado].
- SRF por esfuerzos (Grimstad y Barton 1993): en NGI 2025 la relación σc/σ1 o σθ/σc **se retiró de la tabla principal**, se dejó solo para la categoría c) con la advertencia de no aplicarla sin criterio, y se eliminó para roca con squeezing por falta de datos. [V1]

### Gráfico de sostenimiento (NGI 2025) [V1]
- Nueve categorías de sostenimiento, eje Q (log) vs De; espesor de shotcrete con fibra (Sfr) interpolado entre líneas; espaciado de pernos «con Sfr» y «sin Sfr».
- RRS (costillas reforzadas de shotcrete) en Q < 1, categorías 6–8; en 2025 se llaman RRS-A, B y C. Recomienda 12–15 cm de shotcrete con fibra antes de la RRS.
- Energía de absorción: E700 en la clase 4 (antes E500) y E1000 desde la clase 6.
- Clases 7–9: exige evaluaciones adicionales de geología e ingeniería de rocas.

### Q-slope
- Bar, N. y Barton, N. (2017). The Q-slope method for rock slope engineering. *RMRE*, 50(12), 3307–3322. doi:10.1007/s00603-017-1305-0 [V2 Crossref]
```
Q_slope = (RQD/Jn) · (Jr/Ja)_O · (Jwice / SRF_slope)
β = 20·log10(Q_slope) + 65°     (ángulo máximo sin refuerzo)          [V2]
```
- (Jr/Ja)_O: factores de orientación por familia (por ejemplo 0.7 o 0.9); SRF_slope = máximo de SRFa (condición física), SRFb (esfuerzo/resistencia) y SRFc (discontinuidades mayores); Jwice incluye lluvia intensa y hielo [V2 parcial]. Valores guía: β ≈ 40–45°, 60–65° y 80–85° para Q_slope ≈ 0.1, 1 y 10. Otros autores ajustan la constante por probabilidad de falla (70.5 al 30 %, 73.5 al 50 %) [V2 débil].
- Validez: taludes de < 5 m a > 250 m, bancos y taludes de roca, sin refuerzo.

### Críticas
- Palmström y Broch (2006), *TUST*, 21(6), 575–593, doi:10.1016/j.tust.2005.10.005 [V2]: uso y mal uso del Q; Jn y RQD redundantes, SRF mezcla conceptos.
- NGI 2025 agrega un capítulo de prerrequisitos y limitaciones, y pide Qmin y Qmax cuando hay rangos de parámetros [V1].

### Qué implementar
Q y Q' con tablas de parámetros por edición (1974, 1993, 2015, 2025) seleccionables; ESR configurable (tu mina puede tener sus propios ESR, como permite NGI); gráfico de sostenimiento como polígonos digitalizados por edición; Qmin/Qmax/rango; Q-slope.

---

## 4. GSI (Geological Strength Index)

### Fuentes
- Hoek, E. (1994). Strength of rock and rock masses. *ISRM News Journal*, 2(2), 4–16. [V2 cita]
- Hoek, E., Kaiser, P. K. y Bawden, W. F. (1995). *Support of Underground Excavations in Hard Rock*. Balkema. [V2]
- Hoek, E., Marinos, P. y Benissi, M. (1998). Applicability of the GSI classification for very weak and sheared rock masses. The case of the Athens Schist Formation. *Bull. Eng. Geol. Environ.*, 57(2), 151–160. doi:10.1007/s100640050031 [V2 Crossref]
- Marinos, P. y Hoek, E. (2000). GSI: a geologically friendly tool for rock mass strength estimation. *GeoEng2000*, Melbourne, 1422–1446. [V2 cita]
- Marinos, P. y Hoek, E. (2001). Estimating the geotechnical properties of heterogeneous rock masses such as flysch. *Bull. Eng. Geol. Environ.*, 60(2), 85–92. doi:10.1007/s100640000090 [V2]
- Marinos, V., Marinos, P. y Hoek, E. (2005). The geological strength index: applications and limitations. *Bull. Eng. Geol. Environ.*, 64(1), 55–65. doi:10.1007/s10064-004-0270-5 [V2]
- Hoek, E., Carter, T. G. y Diederichs, M. S. (2013). Quantification of the Geological Strength Index chart. *47th US Rock Mechanics/Geomechanics Symposium*, ARMA 13-672, San Francisco. Copia del autor en rocscience.com [V1].
- Cai, M., Kaiser, P. K., Uno, H., Tasaka, Y. y Minami, M. (2004). Estimation of rock mass deformation modulus and strength of jointed hard rock masses using the GSI system. *IJRMMS*, 41(1), 3–19. doi:10.1016/S1365-1609(03)00025-X [V2]
- Cai, M., Kaiser, P. K., Tasaka, Y. y Minami, M. (2007). Determination of residual strength parameters of jointed rock masses using the GSI system. *IJRMMS*, 44(2), 247–265. doi:10.1016/j.ijrmms.2006.07.005 [V2]
- Sonmez, H. y Ulusay, R. (1999). Modifications to the GSI and their applicability to stability of slopes. *IJRMMS*, 36(6), 743–760. doi:10.1016/S0148-9062(99)00043-1 [V2]
- Hoek, E. y Brown, E. T. (2019). The Hoek–Brown failure criterion and GSI – 2018 edition. *JRMGE*, 11(3), 445–463. doi:10.1016/j.jrmge.2018.08.001 [V2]

### Ecuaciones
GSI cuantificado (Hoek, Carter y Diederichs 2013) [V1]:
```
GSI = 1.5·JCond89 + RQD/2                       (ec. 1)
GSI = 2·JCond76 + RQD/2                          (ec. 2, con JCond89 = 1.3·JCond76)
JCond89 = 35·(Jr/Ja) / (1 + Jr/Ja)
GSI = 52·(Jr/Ja)/(1 + Jr/Ja) + RQD/2             (ec. 3, ajuste "aceptable", peor que ec. 1)
```
- Los autores lo validaron con **un solo conjunto de datos** (un túnel de perforación y voladura) y lo presentan como «propuesto», no «recomendado» [V1]. Es aplicable a macizos fracturados que se comportan de forma homogénea e isotrópica.
- Una revisión de 2017 lo restringe a RQD ≤ 80 [V2 débil, Atlantis Press]; Song, Xue y Ju (2020), *BEGE*, 79(6), 3105–3119, doi:10.1007/s10064-020-01739-5 [V2], encuentran buen ajuste en macizos medianos y sesgo para GSI < 45. Morelli (2017), *Geotech. Geol. Eng.*, 35(6), 2803–2816, doi:10.1007/s10706-017-0279-8, propone otra cuantificación.

Relaciones con RMR y Q:
```
GSI = RMR76'            (RMR76' > 18; seco, sin ajuste por orientación)        [V1, Hoek-Diederichs 2006]
GSI = RMR89' − 5        (RMR89' > 23; agua = 15, sin ajuste)                   [V1, Hoek-Diederichs 2006]
GSI = 9·ln Q' + 44      (Hoek, Kaiser y Bawden 1995)                          [V2]
```

Cai et al. (2004): GSI desde volumen de bloque Vb y condición de junta Jc [V2 concepto; NV fórmulas]:
```
Jc = JW · JS / JA                 (ondulación a gran escala, rugosidad a pequeña escala, alteración)
Vb = s1·s2·s3 / (sen γ12 · sen γ23 · sen γ13)     (tres familias)
```
La expresión cerrada GSI(Vb, Jc) = (26.5 + 8.79 ln Jc + 0.9 ln Vb)/(1 + 0.0151 ln Jc − 0.0253 ln Vb) aparece en Cai et al. (2007) [NV: verificar antes de usar].

Sonmez y Ulusay (1999, 2002): SR = −17.5·ln(Jv) + 79.8 y SCR = Rr + Rw + Rf (0 a 18) [NV].

### Validez y críticas
- GSI no se aplica a macizos controlados por estructuras (bloques individuales, cuñas): ahí manda el análisis cinemático. Marinos et al. (2005) [V2].
- Pozo (2024, SRK Perú, *Revista Minería*): encuesta a 40 profesionales de Perú, España y Chile. La estimación visual da COV 0.14–0.35; las fórmulas cuantitativas lo bajan a 0.06–0.15. La mayoría de datos cae entre GSI = RMR' + 5 y GSI = RMR' − 15; el 90 % reportó un único valor en lugar de un rango [V2]. Argumento directo para que tu librería guarde **rangos de GSI** (mín./más probable/máx.).

### Qué implementar
GSI por tabla (carta 2D con celdas y ejes configurables), GSI cuantificado (ec. 1–3), GSI desde RMR/Q', GSI de Cai (Vb, Jc), GSI como rango o distribución, y aviso si el macizo es estructuralmente controlado.

---

## 5. Hoek-Brown generalizado, módulo y Mohr-Coulomb equivalente

### Fuentes
- Hoek, E. y Brown, E. T. (1980). Empirical strength criterion for rock masses. *J. Geotech. Eng. Div. ASCE*, 106(9), 1013–1035. doi:10.1061/AJGEB6.0001029 [V2]
- Hoek, E. y Brown, E. T. (1997). Practical estimates of rock mass strength. *IJRMMS*, 34(8), 1165–1186. doi:10.1016/S1365-1609(97)80069-X [V2]
- Hoek, E., Carranza-Torres, C. y Corkum, B. (2002). Hoek-Brown failure criterion – 2002 edition. *Proc. NARMS-TAC 2002*, Toronto, 1, 267–273. [V1 texto leído]
- Hoek, E. y Diederichs, M. S. (2006). Empirical estimation of rock mass modulus. *IJRMMS*, 43(2), 203–215. doi:10.1016/j.ijrmms.2005.06.005 [V1 texto leído]
- Hoek, E. y Brown, E. T. (2019), 2018 edition (arriba).

### Ecuaciones (Hoek et al. 2002) [V1]
```
σ1' = σ3' + σci·(mb·σ3'/σci + s)^a
mb  = mi·exp((GSI − 100)/(28 − 14D))
s   = exp((GSI − 100)/(9 − 3D))
a   = 1/2 + (1/6)·(e^(−GSI/15) − e^(−20/3))
σc  = σci·s^a                     (compresión uniaxial del macizo)
σt  = −s·σci/mb                   (tracción)
σcm = σci·(mb + 4s − a(mb − 8s))·(mb/4 + s)^(a−1) / (2(1 + a)(2 + a))     (resistencia global, rango σt < σ3 < σci/4)
```
Mohr-Coulomb equivalente, con σ3n = σ3max'/σci [V2: las ecuaciones 12–13 del paper son estándar, leí el resto del texto]:
```
φ' = asin[ 6a·mb·(s + mb·σ3n)^(a−1) / (2(1+a)(2+a) + 6a·mb·(s + mb·σ3n)^(a−1)) ]
c' = σci·[(1+2a)s + (1−a)mb·σ3n]·(s + mb·σ3n)^(a−1) /
     [(1+a)(2+a)·√(1 + 6a·mb·(s + mb·σ3n)^(a−1)/((1+a)(2+a)))]
```
Límite superior σ3max [V1]:
```
Túneles (profundos y someros sin caving):  σ3max'/σcm' = 0.47·(σcm'/(γH))^(−0.94)
Taludes (Bishop):                          σ3max'/σcm' = 0.72·(σcm'/(γH))^(−0.91)
```
Si el esfuerzo horizontal supera al vertical, se usa ese en lugar de γH. Para block caving, Hoek et al. recomiendan **no convertir** entre Hoek-Brown y Mohr-Coulomb [V1].

Módulo del macizo:
```
Hoek et al. 2002:  Em (GPa) = (1 − D/2)·√(σci/100)·10^((GSI−10)/40)     (σci ≤ 100 MPa)      [V2]
                   Em (GPa) = (1 − D/2)·10^((GSI−10)/40)                (σci > 100 MPa)      [V2]
Hoek-Diederichs 2006, simplificada:
                   Erm (MPa) = 100 000·(1 − D/2) / (1 + e^((75 + 25D − GSI)/11))              [V1]
Hoek-Diederichs 2006, generalizada:
                   Erm = Ei·(0.02 + (1 − D/2)/(1 + e^((60 + 15D − GSI)/11)))                  [V1]
                   Ei = MR·σci   (tabla de MR por tipo de roca, basada en Deere y Palmström-Singh)  [V1]
```
Base de datos de la ec. 2006: ensayos in situ de China y Taiwán, GSI > 25 [V2]. La constante 100 000 no tiene sentido físico (los autores lo aclaran) [V1].

### mi y D
- Tablas de mi por tipo de roca y textura: Marinos y Hoek (2000), Hoek (2007, *Practical Rock Engineering*, rocscience.com). Las tablas son datos; impleméntalas como CSV editable con su rango (por ejemplo, granito 32 ± 3) [V2].
- D: 0 (no perturbado) a 1 (muy perturbado). Hoek et al. (2002) dan una tabla guía con fotos (túnel TBM D = 0; voladura deficiente en túnel D = 0.8; taludes de minas grandes con voladura de producción D = 1) [V2]. Hoek y Brown (2019) advierten que D debe aplicarse solo a la zona dañada y no a todo el macizo [NV en detalle].

### Qué implementar
`hoek_brown(gsi, mi, D, sigci)` → mb, s, a; envolventes σ1–σ3 y τ–σn; c', φ' con σ3max por aplicación; σcm; Em/Erm con varias fórmulas; tabla de mi y MR editables; D por zona.

---

## 6. Minería: MRMR y gráfico de estabilidad de Mathews

### MRMR (Laubscher)
- Laubscher, D. H. (1977). Geomechanics classification of jointed rock masses – mining applications. *Trans. Inst. Min. Metall. (Sect. A)*, 86, A1–A8. [NV]
- Laubscher, D. H. (1990). A geomechanics classification system for the rating of rock mass in mine design. *J. S. Afr. Inst. Min. Metall.*, 90(10), 257–273. [V2]
- Laubscher, D. H. (1994). Cave mining – the state of the art. *J. S. Afr. Inst. Min. Metall.*, 94(10), 279–293. [NV]
- Jakubec, J. y Laubscher, D. H. (2000). The MRMR rock mass rating classification system in mining practice. *MassMin 2000*, Brisbane, AusIMM, 413–421. [V1 texto leído]
- Laubscher, D. H. y Jakubec, J. (2001). The MRMR rock mass classification for jointed rock masses. En Hustrulid y Bullock (eds.), *Underground Mining Methods*, SME, 475–481. [V2 cita]

Contenido verificado (Jakubec y Laubscher 2000) [V1]:
- IRMR (in situ) → MRMR (con ajustes mineros). La revisión 2000 introduce la **resistencia del bloque de roca (RBS)**: RBS ≈ 80 % de IRS por efecto de escala, con reducción adicional por vetillas y fracturas cerradas (según dureza de Mohs y frecuencia); ajuste por **juntas cementadas**; nuevos ajustes de condición de juntas; y el **agua pasa a ser ajuste del MRMR**.
- Espaciado de juntas (JS) máximo 35, solo juntas abiertas, máximo tres familias; condición de juntas (JC) máximo 40. Por diferencia, RBS máximo 25 [NV].
- Ajustes mineros: meteorización, voladura, esfuerzos inducidos (pueden reducir o aumentar), orientación de juntas respecto a la excavación o al esfuerzo principal, y agua/hielo. Los ajustes dependen del tiempo y del espacio.
- Recomiendan expresar IRMR/MRMR **como distribución**, no como promedio.
- Rangos de ajuste del sistema 1990 (meteorización 30–100 %, orientación 63–100 %, esfuerzos 60–120 %, voladura 80–100 %, ajuste total no menor de ~50 %): [NV].
- Gráfico de radio hidráulico vs MRMR para caving (estable, transición, hundimiento) [NV: no lo leí].

### Gráfico de estabilidad (Mathews y sucesores)
- Mathews, K. E., Hoek, E., Wyllie, D. C. y Stewart, S. B. V. (1981). *Prediction of stable excavation spans for mining at depths below 1,000 m in hard rock*. Informe CANMET DSS 0SQ80-00081. [V2, citado por Osinergmin]
- Potvin, Y. (1988). *Empirical open stope design in Canada*. Tesis doctoral, University of British Columbia. [V2 cita]
- Nickson, S. D. (1992). *Cable support guidelines for underground hard rock mine operations*. Tesis de maestría, UBC. [V2 cita]
- Clark, L. M. y Pakalnis, R. C. (1997). An empirical design approach for estimating unplanned dilution from open stope hangingwalls and footwalls. *99th CIM AGM*, Vancouver. [V2: ELOS citado por Osinergmin]
- Mawdesley, C., Trueman, R. y Whiten, W. J. (2001). Extending the Mathews stability graph for open-stope design. *Mining Technology*, 110(1), 27–39. doi:10.1179/mnt.2001.110.1.27 [V2 Crossref]
- Suorineni, F. T. (2010). The stability graph after three decades in use: experiences and the way forward. *Int. J. Min. Reclam. Environ.*, 24(4), 307–339. doi:10.1080/17480930.2010.501957 [V2 Crossref]
- Mortazavi, A. y Osserbay, B. (2022). The consolidated Mathews stability graph for open stope design. *Geotech. Geol. Eng.*, 40(5), 2409–2424. doi:10.1007/s10706-021-02034-0 [V2]

Ecuaciones y factores (Osinergmin 2017, sección 7.1.3) [V2]:
```
N' = Q' · A · B · C
Q' = (RQD/Jn)·(Jr/Ja)        (Jw = SRF = 1; base de datos de minas secas)
HR (radio hidráulico) = área / perímetro de la cara
ELOS = volumen de sobrerotura / (altura × longitud de la pared)
```
- A (esfuerzo): 1.0 si σc/σ1 ≥ 10; 0.1 si σc/σ1 ≤ 2; lineal entre ambos. La forma A = 0.1125·(σc/σ1) − 0.125 es la usual [NV en coeficientes].
- B (orientación): 1.0 con junta a 90° de la cara; 0.2 con junta a < 20° (curva por diferencia de rumbo y buzamiento) [V2].
- C (gravedad): 8 en paredes verticales, 2 en techos horizontales. La forma C = 8 − 6·cos(α) para caída y lajamiento, y otra para deslizamiento según buzamiento de la junta crítica [NV].
- Factor de radio (RF, ERF) de Milne (1997) para geometrías irregulares [V2].
- Gráfico extendido de Mawdesley et al. (2001): más de 400 casos de Australia y Canadá, líneas de isoprobabilidad de falla obtenidas por regresión logística [V2].
- ELOS: base de datos de 88 observaciones (Clark), aplicable solo a caja techo y piso, sin extrapolar [V2].

### Críticas
Suorineni (2010) y la literatura posterior: A no captura relajación/tensión en cajas, C representa mal el deslizamiento en caja piso, las zonas de transición se dibujan a ojo y la base de datos es de minas canadienses y australianas con roca dura. Por eso conviene que la librería permita **calibrar las fronteras con datos propios** (regresión logística o SVM, como hacen los trabajos recientes).

### Qué implementar
N', HR, ERF, curvas Potvin/Nickson/Mawdesley digitalizadas o ajustadas, ELOS, y un módulo de calibración de fronteras con los casos de la mina (estable/inestable/hundido).

---

## 7. Taludes: SMR, análisis cinemático y Barton-Bandis

### SMR
- Romana, M. (1985). New adjustment ratings for application of Bieniawski classification to slopes. *Int. Symp. on the Role of Rock Mechanics*, Zacatecas, 49–53. [V2 cita]
- Romana, M., Serón, J. B. y Montalar, E. (2003). SMR geomechanics classification: application, experience and validation. *10th ISRM Congress*, Johannesburgo, SAIMM, 981–984. [V2 cita]
- Tomás, R., Delgado, J. y Serón, J. B. (2007). Modification of slope mass rating (SMR) by continuous functions. *IJRMMS*, 44(7), 1062–1069. doi:10.1016/j.ijrmms.2007.02.004 [V2 Crossref]
- Riquelme, A. J., Tomás, R. y Abellán, A. (2016). Characterization of rock slopes through slope mass rating using 3D point clouds. *IJRMMS*, 84, 165–176. doi:10.1016/j.ijrmms.2015.12.008 [V2 Crossref]

Ecuaciones [NV en esta sesión; son las usuales, verificar contra los DOI]:
```
SMR = RMRb + (F1·F2·F3) + F4
F1 = (1 − sen|A|)²        A = αj − αs (planar), αj − αs − 180° (vuelco), αi − αs (cuña, línea de intersección)
F2 = tan²(βj)  planar ;  F2 = 1  vuelco
F3 = categorías 0, −6, −25, −50, −60 según βj − βs (planar) o βj + βs (vuelco)
F4 = +15 natural, +10 precorte, +8 voladura suave, 0 voladura normal o mecánica, −8 voladura deficiente
Tomás et al. (2007), continuas:
F1 = 16/25 − (3/500)·atan(0.1·|A| − 17)
F2 = 9/16 + (1/195)·atan(0.17·βj − 5)
F3 = −30 + (1/3)·atan(C) (planar) ;  F3 = −13 − (1/7)·atan(C − 120) (vuelco)
```

### Análisis cinemático
- Markland, J. T. (1972). A useful technique for estimating the stability of rock slopes when the rigid wedge sliding type of failure is expected. *Imperial College Rock Mechanics Research Report*, 19. [V2 cita]
- Hoek, E. y Bray, J. W. (1981). *Rock Slope Engineering* (3.ª ed.). IMM, Londres. Ediciones posteriores: Wyllie y Mah (2004, 4.ª), Wyllie (2018, 5.ª), CRC Press. [V2]
- Goodman, R. E. y Bray, J. W. (1976). Toppling of rock slopes. *ASCE Specialty Conf. Rock Engineering for Foundations and Slopes*, Boulder, 2, 201–234. [V2 cita]
- Goodman, R. E. (1989). *Introduction to Rock Mechanics* (2.ª ed.). Wiley. [V2]
- Hocking, G. (1976). A method for distinguishing between single and double plane sliding of tetrahedral wedges. *IJRMMS*, 13(7), 225–226. [V2 cita; **el DOI que probé no corresponde, no lo uses**]

Pruebas a implementar: falla planar (rumbo dentro de ±20° del talud, buzamiento de junta < talud y > φ), cuña (intersección en zona crítica, prueba de Markland y Hocking para una o dos caras), vuelco directo y flexural (Goodman-Bray: normal dentro de ±10–30°, βn ≤ 90° − βs − ... con φ), con cono de fricción y envolvente de «daylight». Rocscience Dips cubre exactamente planar, cuña, vuelco directo y flexural [V2].

### Barton-Bandis
- Barton, N. (1973). Review of a new shear-strength criterion for rock joints. *Engineering Geology*, 7(4), 287–332. doi:10.1016/0013-7952(73)90013-6 [V2]
- Barton, N. y Choubey, V. (1977). The shear strength of rock joints in theory and practice. *Rock Mechanics*, 10(1–2), 1–54. doi:10.1007/BF01261801 [V2]
- Bandis, S. C., Lumsden, A. C. y Barton, N. R. (1983). Fundamentals of rock joint deformation. *IJRMMS & Geomech. Abstr.*, 20(6), 249–268. doi:10.1016/0148-9062(83)90595-8 [V2]
- Barton, N. y Bandis, S. (1982). Effects of block size on the shear behaviour of jointed rock. *23rd US Symp. Rock Mech.*, Berkeley, 739–760. [NV]
- Barton, N. y Bandis, S. (1990). Review of predictive capabilities of JRC-JCS model in engineering practice. En Barton y Stephansson (eds.), *Rock Joints*, Balkema, 603–610. [V2 cita]

Ecuaciones [NV en esta sesión; estándar]:
```
τ = σn·tan[ JRC·log10(JCS/σn) + φr ]
φr = (φb − 20°) + 20°·(r/R)                 (Schmidt: r en junta meteorizada, R en roca sana)
JRCn = JRC0·(Ln/L0)^(−0.02·JRC0)            (efecto de escala)
JCSn = JCS0·(Ln/L0)^(−0.03·JRC0)
```
Método sugerido ISRM para el ángulo básico por tilt test: Alejano et al. (2018), citado por NGI 2025 [V2].

---

## 8. Correlaciones entre sistemas

Advertencias que se repiten en todas las fuentes:
1. Las correlaciones RMR–Q tienen dispersión alta (R² de 0.3 a 0.8 típicamente) porque RMR y Q pesan cosas distintas (Q incluye esfuerzos vía SRF; RMR incluye resistencia de la roca intacta).
2. Osinergmin (2017, sección 3.2.3.9) recomienda **construir la correlación propia de la mina** con una base de datos de mapeo crudo suficientemente grande y **usar la correlación una sola vez** (encadenar RMR → Q → GSI induce error). [V2]
3. Usa al menos dos sistemas para verificar (Osinergmin 2017, sección 3.2.4). [V2]

| Autor (año) | Ecuación | Datos / observación | Marca |
|---|---|---|---|
| Bieniawski (1976) | RMR = 9 ln Q + 44 | Casos de túneles de varios países (el número de casos, ~111, es NV) | V2 |
| Rutledge y Preston (1978) | RMR = 5.9 ln Q + 43 | Túneles en Nueva Zelanda; R ≈ 0.81 | V2 (compilación) |
| Moreno (1980/1982) | RMR = 5.4 ln Q + 55.2 | España; R ≈ 0.55 en una tabla | V2 (compilación) |
| Cameron-Clarke y Budavari (1981) | RMR = 5 ln Q + 60.8 (in situ); RMR = 4.6 ln Q + 55.5 (testigo) | Sudáfrica; dispersión alta. *Eng. Geol.* 17, 19–53, doi:10.1016/0013-7952(81)90019-3 | V2 |
| Abad et al. (1983/1984) | RMR = 10.5 ln Q + 41.8 | Galerías de carbón, España | V2 (compilación) |
| Kaiser y Gale (1985) / Kaiser et al. (1986) | RMR = 8.7 ln Q + 38 | Rocas sedimentarias | V2 (compilación) |
| Al-Harthi (1993) | RMR = 9 ln Q + 49 | Arabia Saudita | V2 (compilación) |
| El-Naqa (1994) | RMR = 7 ln Q + 44 | Jordania | V2 (compilación) |
| Barton (1995) | RMR = 15 ln Q + 50 | Ajuste del autor del Q | V2 (compilación) |
| Tugrul (1998) | RMR = 7 ln Q + 36 | Turquía | V2 (compilación) |
| Kumar et al. (2004) | RMR = 6.4 ln Q + 49.6 | India | V2 (compilación) |
| Castro Caicedo y Pérez Pérez (2013) | RMR = 5.7 ln Q + 43.65 | Túnel La Línea, Colombia (andino) | V2 (compilación) |
| Rehman et al. (2018) | Revisión de la mayoría de ecuaciones anteriores y sus límites | *Appl. Sci.* 8(8), 1250, doi:10.3390/app8081250 | V2 |
| Azad et al. (2024) | RMR = 9.64 ln Q + 50.53 (R² = 0.98) | Túnel ferroviario, Himalaya; compila ~30 ecuaciones. *Sci. Rep.* 14, doi:10.1038/s41598-024-60289-y | V2 |
| **Huang et al. (2026)** | **RMR = 6.70 ln Q + 46.31**; modelo OGSA-XGBoost R² = 0.95 (validación) y 0.94 (prueba) | 448 pares Q–RMR (Zimbabue + casos publicados); no linealidad marcada en Q bajo y alto; RQD y Jr suben RMR, Ja y SRF lo bajan. doi:10.1007/s00603-026-05959-1 | V2 (resumen Crossref) |
| Hoek et al. (1995) | GSI = 9 ln Q' + 44 | Usar Q' (sin Jw ni SRF) | V2 |
| Hoek (1995) / Hoek-Diederichs (2006) | GSI = RMR76' ; GSI = RMR89' − 5 | RMR76' > 18; RMR89' > 23, seco y sin ajuste | V1 |
| Pozo (2024) | GSI entre RMR' + 5 y RMR' − 15 | Encuesta y fórmulas en 4 macizos peruanos | V2 |
| Osinergmin (2017) | RMR76 = RMR89 − 5 ; RMR14 = 1.1·RMR89 + 2 | Tabla 3-11 de la guía | V2 |
| Bonilla, Quintana y Rodríguez-Peces (2016) | RMR–Q en rocas volcánicas | Túnel Transcordillerano, Ecuador | V2 (sin ecuación leída) |

Notas:
- La compilación de coeficientes viene de Azad et al. (2024) y de la búsqueda cruzada; los años de Moreno y Abad varían entre fuentes.
- El preprint «Physics-consistent monotonic ML for RMR prediction from Q» (ResearchGate, 2026) encuentra R² negativo (−0.16) para la mejor ecuación clásica en su base de datos. [V2 débil, no revisado por pares]
- RMR = 8.5 ln Q + 35 aparece en una tesis UNCP sin R² ni origen claro [V2 débil].

**Qué implementar:** un catálogo de correlaciones como datos (autor, ecuación, rango de validez, n, R², litología, contexto), una función `correlacionar(desde, hacia, autor=...)` que advierte si el valor sale del rango y bloquea el encadenamiento, y una función `calibrar_correlacion(pares)` que ajuste a·ln(Q) + b propia de la mina con bandas de predicción. Esto es justamente lo que pide Osinergmin.

---

## 9. Práctica peruana y normativa

### 9.1 Normativa vigente
Base: **DS 024-2016-EM**, Reglamento de Seguridad y Salud Ocupacional en Minería (El Peruano, 28-jul-2016), modificado por **DS 023-2017-EM** (18-ago-2017) y **DS 034-2023-EM** (firmado el 29-dic-2023). Leí el texto de 2016 y el de 2017 completos y los artículos clave de 2023.

| Artículo | Qué exige (texto vigente) | Marca |
|---|---|---|
| 33 (DS 034-2023-EM) | Estudios y actualizaciones de geología, **geomecánica**, geotecnia, hidrogeología, estabilidad de taludes, sostenimiento, ventilación, relleno y **sismicidad inducida** (minas con indicios sísmicos), firmados por ingenieros colegiados. «Los estudios geomecánicos globales (labores subterráneas y superficiales) deben comprender los aspectos indicados en el **Anexo Nº 39 A** y estar basados en ensayos de laboratorio de mecánica de rocas **acreditados**.» «Previa a la ejecución de toda labor minera subterránea se debe contar con una **evaluación geomecánica local**… Anexo Nº 39 B.» «Debe publicar en cada labor **las tablas y planos geomecánicos** que indiquen la calidad de roca, recomendaciones de sostenimiento y dimensionamiento, el estándar de las labores y PETS.» | V1 |
| 33 (texto 2016, ya reemplazado) | Los estudios de geomecánica subterráneos se actualizaban **mensualmente** o antes. La versión 2023 cambia este plazo fijo por estudio global + evaluación local «actualizada en los casos que se amerite». | V1 |
| 75 | Capacitación: prevención de caída de rocas; desate y sostenimiento. El texto 2016 incluía «el uso de las tablas geomecánicas preparadas y actualizadas por el especialista en geomecánica»; **el DS 023-2017-EM retiró ese inciso**. | V1 |
| 213 | Sostenimiento sistemático inmediato basado en estudios geomecánicos: «labor avanzada, labor sostenida». | V1 |
| 214 | a) plan de minado con las condiciones más desfavorables del macizo; b) control de calidad del sostenimiento: 2016 trimestral ≥ 20 %; 2017 **mensual ≥ 1 %**; 2023 mensual ≥ 1 % **por cada tipo de sostenimiento**; c) monitoreo de estallido de rocas; d) PETS geomecánicos actualizados por el área de Geomecánica según cambien las condiciones (2017); g) ancho y altura de **labores** (2023; antes «tajeos») dentro de los cálculos geomecánicos; k) asesoría de un ingeniero especializado en geomecánica por unidad (2017). | V1 |
| 220 | Recuperación de puentes y pilares, rehabilitación y reinicio de labores paralizadas «por un tiempo mayor al de su **auto sostenimiento**» son trabajos de alto riesgo con estudio geomecánico previo y PETAR. | V1 |
| 224–225, 228 | Desate obligatorio entre dos personas, sostenimiento hasta el tope del frente; sostenimiento según estándares; hormigón con ensayos y **pruebas de arranque de pernos** a disposición de la fiscalización. | V1 |
| 230–231 | Techo > 5 m: desatado y sostenimiento **mecanizados** obligatorios. (Osinergmin recomienda desate mecanizado desde 3.5 m.) | V1 / V2 |
| Anexo 1 (2017), plan de minado subterráneo | Estudio geomecánico detallado que caracterice el macizo **por áreas**; diseño de labores por áreas «precisando el **tiempo de sostenimiento máximo**». En tajo abierto: estudio geomecánico que sustente los ángulos de talud. | V1 |
| Anexo de refugios (2017) | Refugios en roca competente **RMR > 60**; sostenimiento adecuado si RMR < 60; área ≥ 1.5 m²/persona. | V1 |

Lo que **no** pude verificar: el contenido de los Anexos 39 A y 39 B (estructura del estudio global y de la evaluación local). Solo vi sus títulos en El Peruano. Hay copias en Scribd y Studocu, pero no son fuente oficial. Revisa el PDF oficial del DS 034-2023-EM en gob.pe.

### 9.2 Guía de Osinergmin (2017)
*Guía de criterios geomecánicos para diseño, construcción, supervisión y cierre de labores subterráneas*, Osinergmin, Gerencia de Supervisión Minera, 1.ª ed., mayo 2017, depósito legal 2017-05838 (PDF de 270 páginas en osinergmin.gob.pe). [V1 leído]

Lo que aporta a tu librería:
- Reproduce RMR76, RMR89, RMR14, Q 1974 y Q 2007, y el **GSI modificado (2002)** en el Anexo A.17.
- Formatos de mapeo por celdas (RMR14, RMR89, RMR76), línea de detalle y logueo de sondajes orientados (Anexos A.1–A.11). Te sirven para definir el **esquema de datos de entrada** de la librería.
- Sección 3.2.3.8: «El índice GSI fue modificado por **C. Vallejo (2002)** con el objetivo de utilizar las tablas originales de manera práctica y sencilla de clasificar cualitativamente al macizo rocoso y recomendar el sostenimiento requerido… Vallejo recurre a las equivalencias del GSI con RMR para recomendar y dimensionar el sostenimiento. Las tablas… corresponderá al personal especializado del área de geomecánica de cada empresa, la adecuación específica.» → **la adaptación por mina es parte de la práctica reconocida por el fiscalizador.**
- Sección 3.2.3.9: correlaciones y recomendación de correlación propia por mina, usada una sola vez.
- Sección 7.1.3: Mathews/Potvin/Nickson, Mawdesley, ELOS; 7.1.5: pilares (Lunder 1994).
- Sección 8.4: autosoporte, incluir el ábaco en la tabla geomecánica, regla de ≤ 20 h.
- Planos geomecánicos con zonificación por tipo de roca (Anexo F); supervisión de zonificación y esfuerzos in situ (por ejemplo, Sheorey 1994).

### 9.3 Origen del «GSI modificado» y la tabla geomecánica peruana
- **Autor y año documentados:** Vallejo, C. (2002). *Aplicaciones del Índice G.S.I. para el mapeo geomecánico y la definición del sostenimiento de labores mineras subterráneas*. XI Congreso Peruano de Geología, Lima (Sociedad Geológica del Perú). [V2: lo cita Osinergmin; no encontré el texto en línea]
- Continuación: Vallejos Cortez, C. (2011). *Estado actual de la aplicación del GSI modificado para el control de desprendimiento de caídas de rocas*. Seminario Internacional de Geomecánica. Incluye un ábaco que permite reemplazar cimbras o pernos sistemáticos por cuadros de madera en roca muy mala (pequeña minería). [V2 citado en una tesina del Centro Geotécnico; copia en Scribd sin autoría verificable]. Nota: las fuentes alternan «Vallejo» y «Vallejos»; puede ser la misma persona.
- Córdova Rojas, N. D. (2008). *Geomecánica en el minado subterráneo: caso Mina Condestable*. Tesis de maestría, UNI (handle 20.500.14076/595). Los textos de David Córdova («Mecánica de rocas en minería y obras civiles») y su tabla de «sostenimiento en excavaciones subterráneas a partir de GSI de Hoek y Marinos» se citan mucho en tesis [V2].
- **Estructura de la tabla (lo que se repite en tesis peruanas)** [V2]: eje vertical de **estructura** por número de fracturas por metro (levemente, moderadamente, muy, intensamente fracturada, triturada; LF, F, MF, IF, T) y eje horizontal de **condición de superficie** que combina la resistencia de la roca intacta estimada con picota (se raya, se indenta, etc.) y el estado de las juntas, en cinco categorías: muy buena (MB), buena (B), regular (R), pobre (P), muy pobre (MP). Cada celda (por ejemplo «MF/R») lleva un color y un tipo de sostenimiento (sin soporte, perno ocasional, perno sistemático con malla, shotcrete con fibra, cimbras o cuadros) para un rango de sección (las minas tienen tablas distintas para 3.5–5 m y > 5 m). Se suele imprimir con el ábaco de autosoporte y la equivalencia GSI–RMR–Q. La tesis UNSAAC de Ancalla (2019) dice citar «Hoek y Marinos (1998)» como fuente de la versión cualitativa y cuantitativa, lo que es inexacto: el GSI de Hoek y Marinos no trae sostenimiento.
- **Cartilla geomecánica:** el término se usa en tesis para la tabla de bolsillo o de labor (por ejemplo, «Cartilla geomecánica para determinar el tiempo de autosostenimiento usado en mina», «el sostenimiento recomendado según la cartilla GSI es perno helicoidal 7' + malla electrosoldada»). No es un término normativo: la norma dice «tablas y planos geomecánicos».
- **Conclusión para el diseño:** no hay una tabla GSI peruana «oficial». Cada mina tiene la suya (ejes, cortes de color, sostenimiento por sección). La librería debe tratar la tabla como **configuración** (ejes, celdas, colores, sostenimiento, sección, vigencia, autor, versión), no como dato fijo, y traer de ejemplo una tabla genérica derivada de fuentes publicadas.

### 9.4 Chile (comparación breve)
DS 132 (Reglamento de Seguridad Minera, 2002; publicado en 2004; última modificación por DS 34 en 2013, en proceso de actualización por Sernageomin en 2024). El art. 22 exige aprobar el método de explotación ante Sernageomin antes de operar [V2]. No encontré artículos específicos sobre tablas geomecánicas equivalentes a los peruanos; la exigencia peruana de publicar tablas en cada labor es más detallada. [NV en detalle]

---

## 10. Tesis y trabajos peruanos relevantes

Los títulos incluyen nombres de unidades que ya son públicos en los repositorios. Si citas esto en documentación de la librería, cita la tesis y no la mina.

| Autor (año) | Título resumido | Universidad | Por qué sirve | Enlace |
|---|---|---|---|---|
| Córdova Rojas, N. D. (2008) | Geomecánica en el minado subterráneo: caso Mina Condestable | UNI (maestría) | Autor de referencia de la tabla GSI de sostenimiento en el Perú | https://cybertesis.uni.edu.pe/handle/20.500.14076/595 |
| Oriundo Yaranga, N. (2008) | El índice de resistencia geológica (GSI) y su aplicación en la explotación de la mina Huarón | UNSCH | Implementación del GSI modificado, corrección por factores influyentes | http://repositorio.unsch.edu.pe/handle/UNSCH/2196 |
| Ancalla Monge, A. (2019) | Geomecánica y su implicancia en la investigación de desprendimiento de rocas en el CX 1870, U.O. Pallancata | UNSAAC | GSI modificado por sección (3.5–5 m y > 5 m), cartilla de autosoporte, RMR con software Geotable | https://repositorio.unsaac.edu.pe/handle/20.500.12918/4625 |
| Espinoza Varillas, M. J. (2023) | Evaluación geomecánica para determinar el tipo de sostenimiento de la cámara para el winche del Nv. 720, Yauricocha | UNDAC | Uso de cartilla GSI para sostenimiento | http://repositorio.undac.edu.pe/bitstream/undac/3508/1/T026_46869701_T.pdf |
| Barreda Barriga, K. (2018) | Estudio geotécnico-geomecánico de la Mina Fortuna, plan de minado 2018 | Tesina de diplomado, Centro Geotécnico | Cita a Vallejo (2002) vía Osinergmin y el ábaco de Vallejos (2011) | https://centrogeotecnico.com/mt-content/uploads/2018/10/tesina-tsd-diplomado-de-geomecanica-karina-barreda-barriga.pdf |
| Huerta (2025) | Cambio de sostenimiento en labores con altos esfuerzos inducidos | UNI | RMR, Q y GSI en dominios de baja calidad (GSI < 25, Q < 1) | https://repositorio.uni.edu.pe/bitstream/20.500.14076/29371/1/huerta_ep.pdf |
| Salcedo Illaconza (2023) | Reducción de costos cambiando pernos helicoidales de 22 a 19 mm | UNI | Sostenimiento y costos | https://cybertesis.uni.edu.pe/handle/20.500.14076/26922 |
| (PUCP, 2017) | Modelamiento geomecánico a nivel de prefactibilidad de una mina subterránea | PUCP | Usa RMR76 porque los gráficos empíricos se calibraron con él | https://repositorio.pucp.edu.pe/index/handle/123456789/148255 |
| Pantaleón Junco y Carbajal Isidro | Evaluación geomecánica para dimensionamiento, secuencia de minado y relleno de tajeos | PUCP | Dimensionamiento de tajeos y retroanálisis | https://core.ac.uk/download/196534953.pdf |
| (UNCP) | Caracterización geomecánica de S.M.R.L. Pablito-Uno | UNCP | Tabla geomecánica propia de la unidad; correlación RMR–Q | https://files01.core.ac.uk/download/651236555.pdf |
| (UNSCH) | By Pass 2724, Consorcio Horizonte | UNSCH | Correlación RMR–Q y GSI = RMR89 − 5 | https://repositorio.unsch.edu.pe/server/api/core/bitstreams/74e04616-6504-4c0c-9952-c481401ec1ae/content |
| (UNAP) | Unidad Minera El Porvenir | UNAP | GSI modificado del área de geomecánica de la empresa, estallido de rocas | https://repositorio.unap.edu.pe/server/api/core/bitstreams/9938b4cc-fd25-4406-bb95-a8eb3db535a6/content |
| (UNAMBA, 2024) | Clasificaciones geomecánicas y sostenimiento de rampa, Parccaccocha | UNAMBA | Cartillas GSI, costos, modelamiento numérico | https://repositorio.unamba.edu.pe/server/api/core/bitstreams/ae04101e-4294-4de0-9d50-47e500431853/content |
| (UNAM Moquegua, 2021/2022) | Sostenimiento con GSI, RMR y Q, U.M. San Antonio | UNAM | Comparación de tres sistemas | https://alicia.concytec.gob.pe/vufind/Record/UNAM_8eb83a78125f8cf7fd1c1a9f03927195/Details |
| Ordoñez Moreano, L. (2023) | Clasificaciones geomecánicas para estimar el tiempo de autosoporte, U.O. Pallancata | (universidad no confirmada) | Autosoporte con Q, GSI y RMR | https://repositorioslatinoamericanos.uchile.cl/handle/2250/9474792 |
| Pozo, R. (2022) | Modificación del sistema GSI en función de la escala (GSIe) para taludes | UNI / V Seminario Peruano de Geoingeniería | GSIe = k·GSI0, con k según H/e, persistencia, direccionalidad y condición | https://revistamineria.com.pe/tecnico-cientifico/modificacion-del-sistema-gsi-en-funcion-de-la-escala-de-analisis-de-estabilidad-de-taludes-en-macizos-rocosos |
| Pozo, R. (2024) | Comparación de métodos cualitativos y cuantitativos para el GSI | SRK Perú / VII Simposio Peruano de Geoingeniería | Dispersión del GSI y banda GSI–RMR' | https://revistamineria.com.pe/actualidad/analisis-comparativo-de-las-metodologias-para-el-calculo-del-gsi-con-base-en-enfoques-cualitativos-y-cuantitativos |

Huecos en tesis:
- **No encontré ninguna tesis peruana que calibre estadísticamente una tabla GSI de sostenimiento** (por ejemplo, con casos de caída de rocas o desempeño del sostenimiento) ni que publique una correlación RMR–Q–GSI propia con n, R² y bandas. Las tesis aplican tablas, no las validan.
- No encontré tesis relevantes en los repositorios de UNSA, UNMSM ni UNASAM con las búsquedas hechas. Conviene buscar directamente en RENATI (SUNEDU) y en cada repositorio con «GSI», «tabla geomecánica», «correlación».
- La búsqueda de ALICIA por API no devolvió conteos; las tesis listadas vienen de buscadores generales.

---

## 11. Geotecnia de suelos útil en minería: qué ya existe en Python

No dupliques esto; enlázalo o declara la dependencia opcional.

| Librería | Qué cubre | Licencia / estado | Marca |
|---|---|---|---|
| groundhog (snakesonabrain) | Correlaciones de suelos, CPT, consolidación, capacidad portante, pilotes, offshore; funciones con validación de parámetros y referencias | **Licencia inconsistente**: el README dice CC BY-NC-SA 4.0 y PyPI/encabezados dicen GPL. Revísala antes de depender de ella. | V2 |
| pyslope (JesseBonanno) | Estabilidad de taludes 2D por Bishop | PyPI 1.2.0; licencia no verificada | V2 |
| mplstereonet | Estereogramas en matplotlib (planos, polos, contornos, ajuste de guirnaldas) | PyPI; MIT [NV] | V2 |
| apsg | Geología estructural, estadística de orientaciones | PyPI | V2 |
| QuickRMR (jagadishkundu) | RMR89/RMR14 con funciones continuas | GitHub | V2 |
| BD-Hoek-Brown (berkdemir) | Hoek-Brown con Streamlit | GPL-3.0 | V2 |
| slipsurface.rock (hdaltuntas) | Hoek-Brown, MC equivalente, módulo, GSI desde carta/RMR/Q/JCond+RQD | Interfaz web; el repositorio dio 404 al consultarlo | V2 débil |
| GeotekPPU (PyPI) | Módulo geotécnico con variantes de RMR | Sin verificar | V2 débil |
| OpenSeesPy, pystrata | Análisis numérico y respuesta sísmica de sitio | Conocidas; no revisadas en esta sesión | NV |

Hueco: **ninguna** cubre clasificaciones mineras (MRMR, Mathews, ELOS), tablas GSI de sostenimiento configurables, ni la normativa peruana.

---

## 12. Software comercial de referencia: qué esperan los geomecánicos

| Programa | Funciones que conviene igualar o exportar a ellas | Marca |
|---|---|---|
| Rocscience RSData (sucesor de RocData) | Ajuste de σci y mi a ensayos triaxiales; Hoek-Brown generalizado, MC equivalente, Barton-Bandis, curvas de potencia; exportación de materiales a Slide2/3, RS2/RS3 | V2 (detalle de funciones NV) |
| Rocscience Dips | Estereogramas, conteo y familias, análisis cinemático planar, cuña, vuelco directo y flexural, exportación a Excel | V2 |
| Rocscience UnWedge | Cuñas alrededor de excavaciones, factor de seguridad, pernos (anclaje mecánico, Swellex, barra cementada, cable, Split Set), shotcrete | V2 |
| Geovia / Deswik | Diseño minero y modelos de bloques con atributos geotécnicos; útiles como destino de exportación (CSV/DXF con zonificación) | NV |

Implicancias: formatos de intercambio claros (CSV/Excel de mapeo por celdas, salida de materiales HB/MC con σ3max y D), y gráficos estándar (carta GSI coloreada, gráfico de Q con categorías, gráfico de estabilidad, ábaco de autosoporte, estereograma con zonas cinemáticas).

---

## 13. Derechos: ¿se pueden reproducir tablas y digitalizar ábacos?

No soy abogado; esto es una síntesis para decidir el diseño, no un dictamen.

1. **Ideas, métodos y fórmulas no son protegibles.** Perú: DL 822, Ley sobre el Derecho de Autor, art. 9: no son objeto de protección las ideas, los procedimientos, métodos de operación o conceptos matemáticos en sí, los sistemas, ni el contenido ideológico o técnico de obras científicas [V2: transcripciones en revistas peruanas y en jurisprudencia de CERLALC; no leí el texto oficial vigente]. Es coherente con el art. 9.2 del ADPIC. En EE. UU., *Feist v. Rural* (1991) y la doctrina sobre gráficos de datos factuales en cuadrículas funcionales apuntan a lo mismo [V2].
2. **Lo que sí se protege es la expresión:** el dibujo concreto de una figura (diseño, tipografía, colores, textos descriptivos largos, fotos de la tabla D de Hoek). Las tablas de puntajes (rango → puntaje) son datos y su selección suele estar dictada por el método, por lo que el riesgo es bajo; los **textos descriptivos** de las cartas (por ejemplo, las frases de cada celda de la carta GSI) son expresión literaria.
3. **Precauciones recomendadas:**
   - Implementa los puntajes y fórmulas como datos propios con su cita (autor, año, tabla, página). No copies imágenes de las figuras.
   - Para ábacos sin ecuación (gráfico de Q, autosoporte, Mathews, carta GSI), **digitaliza puntos tú mismo** y publica las coordenadas como tu propio conjunto de datos con licencia abierta, citando el original. Mejor aún, usa ecuaciones publicadas cuando existan (Kundu 2020 para RMR, Tomás 2007 para SMR, Mawdesley 2001 por regresión logística, Hoek 2013 para GSI).
   - Redacta tus propias descripciones cortas de celdas en lugar de copiar las frases de la carta.
   - **No incluyas en el repositorio tablas internas de minas** (cartillas o tablas GSI de una empresa): son documentos de terceros y pueden tener datos o criterios confidenciales. La librería trae solo plantillas y ejemplos genéricos; cada usuario carga su tabla localmente. Esto también te protege con la regla de datos de clientes.
   - El manual del Q de NGI y la guía de Osinergmin no traen una licencia de reutilización explícita (no la encontré). Cítalos y no reproduzcas sus figuras.
   - Prácticas observadas: groundhog cita la referencia en cada función; QuickRMR publica funciones continuas en lugar de reproducir tablas; Rocscience aloja copias de autor de los artículos de Hoek.
4. **Licencia de tu librería:** una permisiva (MIT o BSD-3) facilita su uso en minas y consultoras; Apache-2.0 suma una cláusula de patentes. Pon los datos digitalizados bajo CC BY 4.0 o CC0. Encaja con tu estrategia de anterioridad (como VentPy en PyPI).

---

## 14. Dónde publicar la librería

| Medio | Requisitos clave | Costo | Marca |
|---|---|---|---|
| **JOSS** (Journal of Open Source Software) | Licencia OSI; repositorio público sin registro; aplicación de investigación clara; contribución sustancial (no «utilidades menores»); **al menos seis meses de historia pública**, evidencia de uso en investigación y desarrollo iterativo (filtros previos a la revisión); `paper.md` en el repo (resumen, autores, afiliaciones, referencias); sin resultados de investigación nuevos; **declaración obligatoria de uso de IA** (herramientas, versiones, dónde se usó, y confirmación de revisión humana); al aprobar, release etiquetado y archivo en Zenodo o figshare con DOI. Revisión abierta en GitHub. | Gratis | V1 |
| SoftwareX (Elsevier) | Software libremente disponible; artículo «Original Software Publication» con tabla de metadatos del código (versión, enlace permanente, lenguajes, requisitos, documentación, correo de soporte); la plantilla 2026 indica que solo aceptan repositorios de GitHub en la tabla; copia archivada en el GitHub de la revista. | Acceso abierto con APC (monto no verificado; una fuente da ~US$ 760, posiblemente desactualizado) | V2 |
| Computers & Geosciences (Elsevier) | Acepta artículos con código; exige sección de disponibilidad de código | Híbrida | NV |
| Rock Mechanics Bulletin (Elsevier, acceso abierto) | Revista nueva de ingeniería de rocas, buena para un artículo metodológico (por ejemplo, calibración de tablas por mina) | APC | NV |
| Revista Minería (IIMP) / Simposio Peruano de Geoingeniería | Difusión local; ya publican trabajos sobre GSI (Pozo 2022, 2024) | — | V2 |
| Zenodo | DOI por versión; refuerza anterioridad | Gratis | V2 |
| pyOpenSci | Revisión comunitaria de paquetes Python; vía rápida a JOSS | Gratis | NV |

Ruta sugerida: PyPI + Zenodo desde la primera versión, seis meses de desarrollo público con issues y releases, luego JOSS; en paralelo, un artículo técnico (calibración de tablas GSI de sostenimiento con datos anonimizados) en una revista de ingeniería de rocas o en el Simposio Peruano de Geoingeniería.

---

## 15. Huecos que nadie cubre (oportunidad de la librería)

1. **Tablas geomecánicas como configuración versionada**: carta GSI con ejes, cortes, colores, sostenimiento por sección y vigencia, cargada desde YAML/CSV/Excel, con trazabilidad (quién, cuándo, con qué datos). Nadie lo hace en código abierto.
2. **Calibración de correlaciones propias por mina** (RMR–Q–GSI) con bandas de predicción y bloqueo de encadenamiento, como pide Osinergmin.
3. **Calibración de tablas de sostenimiento** contra desempeño (caídas de rocas, sobrerotura, ELOS) con regresión logística, al estilo de Mawdesley para Mathews.
4. **Clasificación con incertidumbre** (rangos o distribuciones para GSI, Q, RMR), como recomiendan Jakubec y Laubscher (2000) y Pozo (2024).
5. **Versiones de cada sistema** (RMR76/89/14; Q 1974/1993/2015/2025) seleccionables, con la tabla de cada edición.
6. **Cumplimiento normativo peruano**: generar la tabla y el plano para publicar en la labor (art. 33), regla de autosoporte ≤ 20 h (Osinergmin), refugios RMR > 60, control de calidad ≥ 1 % por tipo de sostenimiento.
7. Integración con mapeo digital (fotos, nubes de puntos: Riquelme et al. 2016; NGI 2025 menciona mapeo 2D/3D digital).

---

## 16. Lo que NO pude verificar (no lo codifiques sin revisar el original)

- Contenido de los **Anexos 39 A y 39 B** del DS 034-2023-EM.
- Texto original de **Vallejo (2002)** y **Vallejos Cortez (2011)**; si «Vallejo» y «Vallejos» son la misma persona.
- Fórmulas originales de **RMR14** en Celada et al. (2014): las tomé de la transcripción de Osinergmin (Fs tiene un símbolo dañado en el PDF); las curvas de resistencia y de juntas por metro de RMR14.
- **Q**: L = 2 + 0.15·B/ESR, luz máxima 2·ESR·Q^0.4, presiones de soporte y correlaciones de Barton (2002) para Vp y Em (el DOI sí está verificado). Las tablas completas de Jn, Jr, Ja, Jw y SRF de la edición 2025 están en el manual que descargué, pero no las transcribí aquí.
- **Mathews**: coeficientes exactos de A (0.1125, 0.125), formas de C para deslizamiento, ecuaciones de las fronteras de Potvin/Nickson y la regresión logística de Mawdesley.
- **SMR**: ecuaciones continuas de Tomás et al. (2007) y la tabla de F3 (las doy de memoria).
- **Barton-Bandis**: ecuaciones de escala (de memoria).
- **Cai et al.**: expresión cerrada GSI(Vb, Jc); **Sonmez y Ulusay**: SR y SCR.
- **MRMR**: rangos de ajuste de 1990 y el gráfico de caving; RBS máximo 25.
- Fórmula «RMR = 22 ln De + 25» usada en tesis peruanas.
- Detalles de RSData, Geovia y Deswik; licencias de pyslope y mplstereonet.
- Normativa chilena en detalle.
- El DOI de Hocking (1976): el que probé no corresponde.

---

## 17. Bibliografía (APA 7)

Abad, J., Caleda, B., Chacón, E., Gutiérrez, V. e Hidalgo, E. (1984). Application of geomechanical classification to predict the convergence of coal mine galleries and to design their supports. En *Proceedings of the 5th ISRM Congress* (pp. E15–E19). Melbourne. [NV en autores y páginas]

Alejano, L. R. (2025). Rock mass classification systems: A useful rock mechanics tool, often misused. *Rock Mechanics and Rock Engineering, 58*(10), 11147–11167. https://doi.org/10.1007/s00603-024-04087-y

Azad, M. A., Najeh, T., Raina, A. K., Singh, N., Ansari, A., Ali, M., et al. (2024). Development of correlations between various engineering rockmass classification systems using railway tunnel data in Garhwal Himalaya, India. *Scientific Reports, 14*. https://doi.org/10.1038/s41598-024-60289-y

Bandis, S. C., Lumsden, A. C. y Barton, N. R. (1983). Fundamentals of rock joint deformation. *International Journal of Rock Mechanics and Mining Sciences & Geomechanics Abstracts, 20*(6), 249–268. https://doi.org/10.1016/0148-9062(83)90595-8

Bar, N. y Barton, N. (2017). The Q-slope method for rock slope engineering. *Rock Mechanics and Rock Engineering, 50*(12), 3307–3322. https://doi.org/10.1007/s00603-017-1305-0

Barton, N. (1973). Review of a new shear-strength criterion for rock joints. *Engineering Geology, 7*(4), 287–332. https://doi.org/10.1016/0013-7952(73)90013-6

Barton, N. (2002). Some new Q-value correlations to assist in site characterisation and tunnel design. *International Journal of Rock Mechanics and Mining Sciences, 39*(2), 185–216. https://doi.org/10.1016/S1365-1609(02)00011-4

Barton, N. y Bandis, S. (1990). Review of predictive capabilities of JRC-JCS model in engineering practice. En N. Barton y O. Stephansson (Eds.), *Rock joints* (pp. 603–610). Balkema.

Barton, N. y Choubey, V. (1977). The shear strength of rock joints in theory and practice. *Rock Mechanics, 10*(1–2), 1–54. https://doi.org/10.1007/BF01261801

Barton, N., Lien, R. y Lunde, J. (1974). Engineering classification of rock masses for the design of tunnel support. *Rock Mechanics, 6*(4), 189–236. https://doi.org/10.1007/BF01239496

Bieniawski, Z. T. (1973). Engineering classification of jointed rock masses. *Transactions of the South African Institution of Civil Engineers, 15*(12), 335–344.

Bieniawski, Z. T. (1976). Rock mass classification in rock engineering. En Z. T. Bieniawski (Ed.), *Exploration for rock engineering* (Vol. 1, pp. 97–106). Balkema.

Bieniawski, Z. T. (1988). The Rock Mass Rating (RMR) system (Geomechanics Classification) in engineering practice. En *Rock classification systems for engineering purposes* (ASTM STP 984, pp. 17–34). ASTM. https://doi.org/10.1520/STP48461S

Bieniawski, Z. T. (1989). *Engineering rock mass classifications*. Wiley.

Cai, M., Kaiser, P. K., Tasaka, Y. y Minami, M. (2007). Determination of residual strength parameters of jointed rock masses using the GSI system. *International Journal of Rock Mechanics and Mining Sciences, 44*(2), 247–265. https://doi.org/10.1016/j.ijrmms.2006.07.005

Cai, M., Kaiser, P. K., Uno, H., Tasaka, Y. y Minami, M. (2004). Estimation of rock mass deformation modulus and strength of jointed hard rock masses using the GSI system. *International Journal of Rock Mechanics and Mining Sciences, 41*(1), 3–19. https://doi.org/10.1016/S1365-1609(03)00025-X

Cameron-Clarke, I. S. y Budavari, S. (1981). Correlation of rock mass classification parameters obtained from borecore and in-situ observations. *Engineering Geology, 17*(1–2), 19–53. https://doi.org/10.1016/0013-7952(81)90019-3

Castro Caicedo, Á. J. y Pérez Pérez, J. A. (2013). Correlaciones entre las clasificaciones geomecánicas Q y RMR en el túnel exploratorio de «La Línea», Cordillera Central de Colombia. *Boletín de Ciencias de la Tierra, 34*, 42–50.

Celada, B., Tardáguila, I., Varona, P., Rodríguez, A. y Bieniawski, Z. T. (2014). Innovating tunnel design by an improved experience-based RMR system. En *Proceedings of the World Tunnel Congress 2014* (pp. 1–9). Foz do Iguaçu.

Clark, L. M. y Pakalnis, R. C. (1997). An empirical design approach for estimating unplanned dilution from open stope hangingwalls and footwalls. En *99th CIM Annual General Meeting*. Vancouver. [NV]

Córdova Rojas, N. D. (2008). *Geomecánica en el minado subterráneo: caso Mina Condestable* [Tesis de maestría, Universidad Nacional de Ingeniería]. https://cybertesis.uni.edu.pe/handle/20.500.14076/595

Deere, D. U. (1964). Technical description of rock cores for engineering purposes. *Rock Mechanics and Engineering Geology, 1*(1), 17–22.

Deere, D. U. y Deere, D. W. (1988). The Rock Quality Designation (RQD) index in practice. En *Rock classification systems for engineering purposes* (ASTM STP 984, pp. 91–101). ASTM. https://doi.org/10.1520/STP48465S

Erharter, G. H., Bar, N., Hansen, T. F., Jain, S. y Marcher, T. (2025). International distribution and development of rock mass classification: A review. *Rock Mechanics and Rock Engineering, 58*(10), 11169–11180. https://doi.org/10.1007/s00603-024-04215-8

Goodman, R. E. (1989). *Introduction to rock mechanics* (2.ª ed.). Wiley.

Goodman, R. E. y Bray, J. W. (1976). Toppling of rock slopes. En *Proceedings of the ASCE Specialty Conference on Rock Engineering for Foundations and Slopes* (Vol. 2, pp. 201–234). Boulder.

Grimstad, E. y Barton, N. (1993). Updating the Q-system for NMT. En *Proceedings of the International Symposium on Sprayed Concrete* (pp. 46–66). Norwegian Concrete Association.

Hoek, E. (1994). Strength of rock and rock masses. *ISRM News Journal, 2*(2), 4–16.

Hoek, E. (2007). *Practical rock engineering*. Rocscience. https://www.rocscience.com/learning/hoeks-corner

Hoek, E. y Bray, J. W. (1981). *Rock slope engineering* (3.ª ed.). Institution of Mining and Metallurgy.

Hoek, E. y Brown, E. T. (1980). Empirical strength criterion for rock masses. *Journal of the Geotechnical Engineering Division, ASCE, 106*(9), 1013–1035. https://doi.org/10.1061/AJGEB6.0001029

Hoek, E. y Brown, E. T. (1997). Practical estimates of rock mass strength. *International Journal of Rock Mechanics and Mining Sciences, 34*(8), 1165–1186. https://doi.org/10.1016/S1365-1609(97)80069-X

Hoek, E. y Brown, E. T. (2019). The Hoek–Brown failure criterion and GSI – 2018 edition. *Journal of Rock Mechanics and Geotechnical Engineering, 11*(3), 445–463. https://doi.org/10.1016/j.jrmge.2018.08.001

Hoek, E., Carranza-Torres, C. y Corkum, B. (2002). Hoek-Brown failure criterion – 2002 edition. En R. Hammah, W. Bawden, J. Curran y M. Telesnicki (Eds.), *Proceedings of NARMS-TAC 2002* (Vol. 1, pp. 267–273). University of Toronto Press. https://www.eoas.ubc.ca/courses/eosc433/lecture-material/2002-HoekBrownCriterion.pdf

Hoek, E., Carter, T. G. y Diederichs, M. S. (2013). Quantification of the Geological Strength Index chart. En *47th US Rock Mechanics/Geomechanics Symposium* (ARMA 13-672). San Francisco. https://www.rocscience.com/assets/resources/learning/hoek/2013-Quantification-of-the-GSI-Chart.pdf

Hoek, E. y Diederichs, M. S. (2006). Empirical estimation of rock mass modulus. *International Journal of Rock Mechanics and Mining Sciences, 43*(2), 203–215. https://doi.org/10.1016/j.ijrmms.2005.06.005

Hoek, E., Kaiser, P. K. y Bawden, W. F. (1995). *Support of underground excavations in hard rock*. Balkema.

Hoek, E., Marinos, P. y Benissi, M. (1998). Applicability of the geological strength index (GSI) classification for very weak and sheared rock masses. The case of the Athens Schist Formation. *Bulletin of Engineering Geology and the Environment, 57*(2), 151–160. https://doi.org/10.1007/s100640050031

Huang, S., Zhou, J., Khandelwal, M., Zvarivadza, T., Mpanza, M., Lawal, A. I., et al. (2026). Toward practical rock mass classification and conversion: An interpretable data-driven framework for mapping Q-system parameters to RMR. *Rock Mechanics and Rock Engineering*. https://doi.org/10.1007/s00603-026-05959-1

International Society for Rock Mechanics. (1978). Suggested methods for the quantitative description of discontinuities in rock masses. *International Journal of Rock Mechanics and Mining Sciences & Geomechanics Abstracts, 15*(6), 319–368. https://doi.org/10.1016/0148-9062(78)91472-9

Jakubec, J. y Laubscher, D. H. (2000). The MRMR rock mass rating classification system in mining practice. En *MassMin 2000* (pp. 413–421). AusIMM.

Kundu, J., Sarkar, K., Singh, A. K. y Singh, T. N. (2020). Continuous functions and a computer application for Rock Mass Rating. *International Journal of Rock Mechanics and Mining Sciences, 129*, 104280. https://doi.org/10.1016/j.ijrmms.2020.104280

Laubscher, D. H. (1977). Geomechanics classification of jointed rock masses – mining applications. *Transactions of the Institution of Mining and Metallurgy, Section A, 86*, A1–A8.

Laubscher, D. H. (1990). A geomechanics classification system for the rating of rock mass in mine design. *Journal of the South African Institute of Mining and Metallurgy, 90*(10), 257–273.

Laubscher, D. H. y Jakubec, J. (2001). The MRMR rock mass classification for jointed rock masses. En W. A. Hustrulid y R. L. Bullock (Eds.), *Underground mining methods: Engineering fundamentals and international case studies* (pp. 475–481). SME.

Liu, J., Feng, Y. y Jiao, Y. (2025). The phlogiston theory of rock mass classification: Philosophical and mathematical critique of ordinal data usage. *Rock Mechanics Bulletin, 4*(3), 100205. https://doi.org/10.1016/j.rockmb.2025.100205

Marinos, P. y Hoek, E. (2000). GSI: A geologically friendly tool for rock mass strength estimation. En *Proceedings of GeoEng2000* (pp. 1422–1446). Technomic.

Marinos, P. y Hoek, E. (2001). Estimating the geotechnical properties of heterogeneous rock masses such as flysch. *Bulletin of Engineering Geology and the Environment, 60*(2), 85–92. https://doi.org/10.1007/s100640000090

Marinos, V., Marinos, P. y Hoek, E. (2005). The geological strength index: Applications and limitations. *Bulletin of Engineering Geology and the Environment, 64*(1), 55–65. https://doi.org/10.1007/s10064-004-0270-5

Markland, J. T. (1972). *A useful technique for estimating the stability of rock slopes when the rigid wedge sliding type of failure is expected* (Rock Mechanics Research Report 19). Imperial College.

Mathews, K. E., Hoek, E., Wyllie, D. C. y Stewart, S. B. V. (1981). *Prediction of stable excavation spans for mining at depths below 1,000 metres in hard rock* (CANMET Report DSS Serial No. 0SQ80-00081). Golder Associates.

Mawdesley, C., Trueman, R. y Whiten, W. J. (2001). Extending the Mathews stability graph for open-stope design. *Mining Technology, 110*(1), 27–39. https://doi.org/10.1179/mnt.2001.110.1.27

Ministerio de Energía y Minas. (2016). Decreto Supremo N.º 024-2016-EM: Reglamento de Seguridad y Salud Ocupacional en Minería. *El Peruano*, 28 de julio de 2016. https://sinia.minam.gob.pe/normas/aprueban-reglamento-seguridad-salud-ocupacional-mineria

Ministerio de Energía y Minas. (2017). Decreto Supremo N.º 023-2017-EM: Modifican diversos artículos y anexos del Reglamento de Seguridad y Salud Ocupacional en Minería. *El Peruano*, 18 de agosto de 2017. https://faolex.fao.org/docs/pdf/per173452.pdf

Ministerio de Energía y Minas. (2023). Decreto Supremo N.º 034-2023-EM: Decreto Supremo que modifica diversos artículos e incorpora un capítulo, artículos y anexos al Reglamento de Seguridad y Salud Ocupacional en Minería. *El Peruano*. https://busquedas.elperuano.pe/dispositivo/NL/2249422-2

Morelli, G. L. (2017). Alternative quantification of the geological strength index chart for jointed rocks. *Geotechnical and Geological Engineering, 35*(6), 2803–2816. https://doi.org/10.1007/s10706-017-0279-8

Mortazavi, A. y Osserbay, B. (2022). The consolidated Mathews stability graph for open stope design. *Geotechnical and Geological Engineering, 40*(5), 2409–2424. https://doi.org/10.1007/s10706-021-02034-0

Nickson, S. D. (1992). *Cable support guidelines for underground hard rock mine operations* [Tesis de maestría, University of British Columbia].

Norwegian Geotechnical Institute. (2025). *Using the Q-system: Rock mass classification and support design* (Handbook, revisión de abril de 2025). NGI. https://prod.ngi.no/globalassets/bilder/forskning-og-radgivning/bygg-og-anlegg/q-handbook_2025_english_final.pdf

Norwegian Geotechnical Institute. (2025). *Change log for the handbook «Using the Q-system», revision 2025*. NGI. https://www.ngi.no/globalassets/bilder/forskning-og-radgivning/bygg-og-anlegg/change-log-q-handbook-revision-2025_final.pdf

Organismo Supervisor de la Inversión en Energía y Minería. (2017). *Guía de criterios geomecánicos para diseño, construcción, supervisión y cierre de labores subterráneas* (1.ª ed.). Osinergmin. https://www.osinergmin.gob.pe/seccion/centro_documental/mineria/Documentos/Publicaciones/Guia-Criterios-Geomecanicos.pdf

Palmström, A. (1982). The volumetric joint count – A useful and simple measure of the degree of rock mass jointing. En *Proceedings of the 4th Congress of the IAEG* (Vol. 5, pp. 221–228). Nueva Delhi.

Palmström, A. (2005). Measurements of and correlations between block size and rock quality designation (RQD). *Tunnelling and Underground Space Technology, 20*(4), 362–377. https://doi.org/10.1016/j.tust.2005.01.005

Palmström, A. y Broch, E. (2006). Use and misuse of rock mass classification systems with particular reference to the Q-system. *Tunnelling and Underground Space Technology, 21*(6), 575–593. https://doi.org/10.1016/j.tust.2005.10.005

Pells, P. J., Bieniawski, Z. T., Hencher, S. R. y Pells, S. E. (2017). Rock quality designation (RQD): Time to rest in peace. *Canadian Geotechnical Journal, 54*(6), 825–834. https://doi.org/10.1139/cgj-2016-0012

Potvin, Y. (1988). *Empirical open stope design in Canada* [Tesis doctoral, University of British Columbia].

Pozo, R. (2022). Modificación del sistema GSI en función de la escala de análisis de estabilidad de taludes en macizos rocosos. *Revista Minería* (IIMP). https://revistamineria.com.pe/tecnico-cientifico/modificacion-del-sistema-gsi-en-funcion-de-la-escala-de-analisis-de-estabilidad-de-taludes-en-macizos-rocosos

Pozo, R. (2024). Análisis comparativo de las metodologías para el cálculo del GSI con base en enfoques cualitativos y cuantitativos. *Revista Minería* (IIMP). https://revistamineria.com.pe/actualidad/analisis-comparativo-de-las-metodologias-para-el-calculo-del-gsi-con-base-en-enfoques-cualitativos-y-cuantitativos

Priest, S. D. y Hudson, J. A. (1976). Discontinuity spacings in rock. *International Journal of Rock Mechanics and Mining Sciences & Geomechanics Abstracts, 13*(5), 135–148. https://doi.org/10.1016/0148-9062(76)90818-4

Rehman, H., Ali, W., Naji, A. M., Kim, J., Abdullah, R. A. y Yoo, H. (2018). Review of rock-mass rating and tunneling quality index systems for tunnel design: Development, refinement, application and limitation. *Applied Sciences, 8*(8), 1250. https://doi.org/10.3390/app8081250

Rehman, H., Naji, A. M., Kim, J. y Yoo, H. (2018). Empirical evaluation of rock mass rating and tunneling quality index system for tunnel support design. *Applied Sciences, 8*(5), 782. https://doi.org/10.3390/app8050782

Riquelme, A. J., Tomás, R. y Abellán, A. (2016). Characterization of rock slopes through slope mass rating using 3D point clouds. *International Journal of Rock Mechanics and Mining Sciences, 84*, 165–176. https://doi.org/10.1016/j.ijrmms.2015.12.008

Romana, M. (1985). New adjustment ratings for application of Bieniawski classification to slopes. En *Proceedings of the International Symposium on the Role of Rock Mechanics in Excavations for Mining and Civil Works* (pp. 49–53). Zacatecas.

Romana, M., Serón, J. B. y Montalar, E. (2003). SMR geomechanics classification: Application, experience and validation. En *Proceedings of the 10th ISRM Congress* (pp. 981–984). SAIMM.

Rutledge, J. C. y Preston, R. L. (1978). New Zealand experience with engineering classification of rock for the prediction of tunnel support. En *Proceedings of the International Tunnelling Symposium* (pp. A3.1–A3.7). Tokio.

Song, Y., Xue, H. y Ju, G. (2020). Comparison of different approaches and development of improved formulas for estimating GSI. *Bulletin of Engineering Geology and the Environment, 79*(6), 3105–3119. https://doi.org/10.1007/s10064-020-01739-5

Sonmez, H. y Ulusay, R. (1999). Modifications to the geological strength index (GSI) and their applicability to stability of slopes. *International Journal of Rock Mechanics and Mining Sciences, 36*(6), 743–760. https://doi.org/10.1016/S0148-9062(99)00043-1

Suorineni, F. T. (2010). The stability graph after three decades in use: Experiences and the way forward. *International Journal of Mining, Reclamation and Environment, 24*(4), 307–339. https://doi.org/10.1080/17480930.2010.501957

Tomás, R., Delgado, J. y Serón, J. B. (2007). Modification of slope mass rating (SMR) by continuous functions. *International Journal of Rock Mechanics and Mining Sciences, 44*(7), 1062–1069. https://doi.org/10.1016/j.ijrmms.2007.02.004

Vallejo, C. (2002). Aplicaciones del índice G.S.I. para el mapeo geomecánico y la definición del sostenimiento de labores mineras subterráneas. En *XI Congreso Peruano de Geología*. Sociedad Geológica del Perú. [Citado por Osinergmin 2017; no consultado]

Vallejos Cortez, C. (2011). Estado actual de la aplicación del GSI modificado para el control de desprendimiento de caídas de rocas. En *Seminario Internacional de Geomecánica*. [Citado en tesina; no consultado]

Wyllie, D. C. (2018). *Rock slope engineering: Civil applications* (5.ª ed.). CRC Press.

Zhang, Q., Jiang, Q., Li, Y., Wang, N. y He, L. (2021). Quality evaluation of rock mass using RMR14 based on multi-source data fusion. *Sensors, 21*(21), 7108. https://doi.org/10.3390/s21217108

### Software y repositorios citados
- groundhog: https://github.com/snakesonabrain/groundhog · https://pypi.org/project/groundhog
- pyslope: https://github.com/JesseBonanno/PySlope · https://pypi.org/project/pyslope
- mplstereonet: https://pypi.org/project/mplstereonet · apsg: https://pypi.org/project/apsg
- QuickRMR: https://github.com/jagadishkundu/QuickRMR
- BD-Hoek-Brown: https://github.com/berkdemir/BD-Hoek-Brown
- JOSS, requisitos: https://joss.readthedocs.io/en/latest/submitting.html
- Rocscience Dips: https://geoengineer.org/software/dips · UnWedge, novedades: https://www.rocscience.com/help/unwedge/overview/whats-new
