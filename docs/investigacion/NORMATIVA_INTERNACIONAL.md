# Normativa internacional de control de terreno y geomecánica minera

Base para el «perfil normativo» de una librería open source de geomecánica (Python con núcleo C++).

Fecha de corte: 31 de octubre de 2026. Solo fuentes web públicas. No se leyó ninguna carpeta local de clientes.

## 0. Cómo leer este informe

**Marcas de verificación**

- **[V1]**: leído en la fuente primaria (texto legal oficial o documento del organismo que mantiene el método). Se descargó el documento y se ubicó el artículo.
- **[V2]**: tomado de una fuente secundaria seria (paper revisado por pares que reproduce la tabla, borrador oficial, resolución de un fiscalizador que cita el artículo, ficha de un organismo de normalización).
- **[NV]**: no verificado. Viene de conocimiento previo o de fuentes débiles. **No usar en la librería sin revisar antes.**

**Tipo de requisito**

- **C** (cuantitativo): umbral, frecuencia, porcentaje o FS. Se vuelve un valor numérico del perfil.
- **Q** (cualitativo): obligación de hacer algo (estudio, plan o inspección). Se vuelve un *checklist*, una validación de entregables o una bandera de cumplimiento.

**Fuerza jurídica.** En cada fila se dice si el dato está en la **ley o el reglamento** (obligatorio) o en una **guía o estándar** (recomendado). Es la distinción más importante para el diseño: casi ningún país fija factores de seguridad en la ley. Los FS salen de guías (Osinergmin, DMIRS/WorkSafe WA, ANM) o del libro de Read y Stacey.

---

## 1. Estándares técnicos internacionales de los métodos (lo que manda en el cálculo)

Las leyes nacionales casi nunca dicen *cómo* calcular. Remiten a «estudios geomecánicos», «criterios de ingeniería» o «normas técnicas nacionales e internacionales vigentes» (por ejemplo NR-22, ítem 22.14.1 [V1]). El cálculo lo definen los estándares de método. Por eso **cada método de la librería debe llevar su versión explícita** y no mezclar ediciones.

### 1.1 Tabla resumen

| Estándar / método | Versión vigente (2026) | Quién lo mantiene | Dónde se publica la versión oficial | Cambios entre versiones que afectan cálculos | Marca |
|---|---|---|---|---|---|
| **ISRM Suggested Methods (SM)** | Compilación 1974–2006 («Blue Book», Ulusay y Hudson, eds., 2007). Compilación 2007–2014 («Orange Book», Ulusay, ed., Springer 2015). Desde 2015, los SM nuevos salen sueltos en *Rock Mechanics and Rock Engineering* (RMRE) | ISRM (Commission on Testing Methods) | Libros: ISRM / Springer (DOI 10.1007/978-3-319-07713-0 para 2007–2014). SM posteriores: artículos en RMRE | La descripción cuantitativa de discontinuidades (ISRM 1978) sigue siendo la base: orientación, espaciado, persistencia, rugosidad (JRC), resistencia de pared (JCS), apertura, relleno, filtración, número de familias y tamaño de bloque. Los SM revisados cambian procedimientos de ensayo, por ejemplo el corte de discontinuidades (Muralha et al., 2014) y el ángulo de fricción básico por *tilt test* (Alejano et al., 2018). **Ojo:** en la consigna se llamó «Orange» al de 1974–2006. La Springer/UPatras indexa el de 2007–2014 como «Orange Book» y el de 2007 como «Blue Book» | [V2] (ficha Springer y catálogos) |
| **ASTM D5878** (guía para usar clasificaciones de macizos) | **D5878-19** (aprobada el 1 de febrero de 2019). La D5878-08 fue retirada en 2017 y la 19 la reinstauró | ASTM, Comité D18 (Soil and Rock), vol. 04.09 | store.astm.org, DOI 10.1520/D5878-19 | Es una *guía*: describe los sistemas sin recomendar uno. Cubre RMR, RSR, URCS, RMFCS, NATM, CMRR, el sistema japonés y Q (NGI). **No hay evidencia de que incluya GSI** | [V2] (fichas BSI, ANSI y iTeh) |
| Otras ASTM de roca relevantes | D7012 (UCS, triaxial y módulos), D5731 (carga puntual), D3967 (brasileño), D4543 (preparación de probetas), D6032 (RQD), D5607 (corte directo de discontinuidades), D4644 (*slake durability*), F432 (pernos y accesorios) | ASTM D18 / F16 | store.astm.org | **Problema de trazabilidad:** 30 CFR 56/57.3203 cita **ASTM F432-95** de forma fija. La ley de EE. UU. referencia una edición congelada aunque ASTM tenga ediciones posteriores. Las ediciones vigentes de cada ASTM listada no se verificaron una por una | F432-95 en CFR: [V1]. Ediciones vigentes: [NV] |
| **ISO 14689** (identificación, descripción y clasificación de roca) | **ISO 14689:2017**, confirmada en 2023. Reemplaza a ISO 14689-1:2003. Adopción europea EN ISO 14689:2018 | ISO/TC 182 | iso.org (de pago) | Describe roca y macizo (mineralogía, génesis, estructura, grano, discontinuidades). **No cubre sistemas de clasificación de macizos** (RMR, Q, etc.). Sirve para el módulo de descripción y logueo, no para puntajes | [V2] (catálogo de normas) |
| **Eurocódigo 7, 2.ª generación** | EN 1997-1:2024 (reglas generales), EN 1997-2:2024 (propiedades del terreno), EN 1997-3:2025 (estructuras geotécnicas, con pernos de roca, *soil nailing* y relleno reforzado). Publicación nacional plena hacia el 30 de septiembre de 2027. Retiro de la 1.ª generación al 30 de marzo de 2028 (otra fuente dice «2027») | CEN/TC 250/SC 7 | Organismos nacionales (BSI, UNE, etc.) | El cambio de fondo es que «ground» incluye roca de forma explícita. Además introduce *Ground Model* y *Geotechnical Design Model*, y el valor representativo como media prudente (95 % de confianza) cuando es estadístico. **No se verificó si EN 1997-2 trae anexos con RMR, Q, GSI o Hoek-Brown.** Lamas et al. (2026, ICSMGE) desarrollan el tratamiento de roca. Es geotecnia civil: en minería sirve como referencia metodológica (valores característicos, verificación por estados límite), no como norma minera | Estructura y fechas: [V2] (Franzén et al., 2026). Contenido de roca: [NV] |
| **RMR** (Bieniawski) | **RMR89** (Bieniawski, 1989) es la versión de uso general. **RMR14** (Celada, Tardáguila, Varona, Rodríguez y Bieniawski, 2014, World Tunnel Congress) es la propuesta actualizada | Bieniawski y grupo de Celada (Geocontrol, Madrid) | Libro Wiley (1989). Ponencia WTC 2014 (biblioteca ITA-AITES). Libro de Celada et al. (2020) con la correlación RMR14–RMR89 | RMR89 suma 6 parámetros (UCS, RQD, espaciado, condición de juntas, agua y ajuste por orientación) en una escala de 0–100 con 5 clases. RMR14 cambia el esquema: reemplaza RQD y espaciado por un conteo de discontinuidades por metro, agrega alterabilidad (ensayo de *slake durability*) y aplica factores de excavación y de comportamiento tenso-deformacional. **El puntaje no es intercambiable entre versiones.** Hay que convertir con la correlación publicada. Kundu et al. (2020) propusieron funciones continuas para RMR89 y RMR14 | RMR89: [V2]. Detalle de RMR14 y su fórmula de correlación: [NV] |
| **Q** (Barton, Lien y Lunde, 1974; NGI) | **Manual NGI «Using the Q-system», Oslo, abril de 2025** (1.ª edición del manual en 2013, revisión en 2015) | NGI (Norwegian Geotechnical Institute) | ngi.no (PDF gratuito y *change log* oficial) | Revisión 2025 [V1]: (a) **SRF pasa de 4 categorías (a–d) a 5 (a–e)**: la antigua b) se divide en «roca competente con tensiones bajas o favorables» y «roca competente con problemas tensionales». (b) La relación σc/σ1 o σθ/σc sale de la tabla principal de SRF y queda en una tabla aparte, con advertencia de no usarla sin crítica (Grimstad y Barton, 1993). Para roca con *squeezing* se elimina por falta de datos. (c) Nuevo subcapítulo Q′ (Qbase). (d) Se recomiendan valores de tabla y Qmin/Qmax. (e) Se agrega Jr = 4 para rugosidad escalonada. (f) **Ábaco de sostenimiento:** RRS I/II/III pasan a A/B/C; se elimina E500 y se reemplaza por E700 en la clase 4; E1000 desde la clase 6. (g) Sostenimiento de hastiales: el límite inferior del Q elevado pasa de 0.1 a 1. (h) **ESR:** minas temporales 3–5, piques 2.0–2.5, minas permanentes 1.6. El manual dice que «los requisitos de cada país pueden dar valores de ESR distintos». Es un parámetro natural del perfil por país | [V1] |
| **GSI** (Hoek y colaboradores) | Ábaco básico (Hoek y Marinos, 2000). Cuantificación de Hoek, Carter y Diederichs (2013, ARMA): GSI = 1.5·JCond89 + RQD/2. Ábacos para rocas heterogéneas, flysch y ofiolitas (Marinos y Hoek, 2001; Marinos et al., 2005; Marinos, 2017; Marinos y Carter, 2018) | Hoek, Marinos y Carter (no hay organismo; se publica en papers y en Rocscience) | Papers (ARMA 2013; *Bull. Eng. Geol. Env.*). Notas de Hoek en rocscience.com | La cuantificación de 2013 permite calcular GSI desde datos de logueo (RMR89 y RQD) en lugar de leerlo del ábaco. Es el modo reproducible que conviene en código. GSI no sirve para diseñar sostenimiento (Hoek, 2005) | Ábacos y referencias: [V2] (Hoek y Brown, 2019). Fórmula de 2013: [V2] (la guía ANM, fig. 52, reproduce el ábaco cuantificado) |
| **Hoek-Brown generalizado** | Edición 2002 (Hoek, Carranza-Torres y Corkum, 2002, con factor D). **Edición 2018** (Hoek y Brown, 2019, *JRMGE* 11(3), 445–463, DOI 10.1016/j.jrmge.2018.08.001) | Hoek y Brown | *JRMGE* (Elsevier, acceso abierto) | Según los autores, la edición 2018 trae «pocos cambios fundamentales» y más guía de uso. Lo que afecta al código: (a) **D no se aplica a todo el macizo**, solo a la zona dañada por voladura o relajación (en taludes, una franja de 1–2 m con D ≈ 0.5 en el ejemplo); (b) corte en tracción con Griffith generalizado, porque Hoek-Brown no modela la falla en tracción; (c) ajustes para macizo masivo a moderadamente fracturado de GSI alto (módulo de Hoek y Diederichs, 2006); (d) guía para estimar mi con triaxiales | [V1] (preprint en Rocscience) y [V2] (metadatos del DOI) |
| **MRMR** (Laubscher) | Laubscher y Jakubec (2001), «The MRMR rock mass classification for jointed rock masses», en Hustrulid y Bullock (eds.), *Underground Mining Methods*, SME. IRMR en Laubscher y Jakubec (2000) | Jakubec (SRK) y comunidad de *block/cave mining* | Libro SME | IRMR incorpora la resistencia de bloque y las vetas o juntas cementadas. MRMR aplica ajustes por meteorización, orientación, esfuerzos inducidos y voladura sobre IRMR. Escala de 0 a 100 | [NV] (cita bibliográfica conocida, sin verificar en línea) |
| **Q-slope** | Bar y Barton (2017), *RMRE* 50, 3307–3322, DOI 10.1007/s00603-017-1305-0 | Bar y Barton | *RMRE* (Springer) | Adapta Q a taludes de roca excavados (de menos de 5 m a más de 250 m de alto). Usa factores O (orientación), Jwice (agua y clima) y SRFslope. El ángulo estable sale de β = 20·log10(Qslope) + 65° (forma conocida; la fórmula no se verificó en el texto completo) | Cita: [V2]. Fórmula: [NV] |
| **SMR** (Romana) | Romana (1985). **Funciones continuas de Tomás, Delgado y Serón (2007)**, *IJRMMS* 44(7), 1062–1069, DOI 10.1016/j.ijrmms.2007.02.004. Revisión de 30 años (Romana, Tomás y Serón, 2015, Congreso ISRM) | Romana y Tomás (U. Politécnica de Valencia y U. de Alicante) | *IJRMMS* (Elsevier). El repositorio de la U. de Alicante tiene acceso abierto | SMR = RMRbásico + F1·F2·F3 + F4. Tomás et al. (2007) reemplazan las tablas discretas de F1, F2 y F3 por funciones continuas, lo que elimina saltos en los bordes de clase. **El resultado numérico cambia según la variante:** discreta o continua debe ser una opción explícita | [V2] |
| **Criterios de aceptación de taludes de tajo** | Read y Stacey (eds.) (2009), *Guidelines for Open Pit Slope Design*, CSIRO Publishing. Cap. 9 de Wesseloo y Read, tabla 9.9. Hay propuestas posteriores de criterios basados en confiabilidad (Macciotta et al., 2020–2022) | Proyecto LOP (Large Open Pit), CSIRO | CSIRO Publishing (libro de pago) | Ver §2.1. Macciotta et al. advierten que los pares FoS–PoF de 2009 son estadísticamente inconsistentes entre sí: un FoS dado no implica la PoF de la misma fila | Tabla: [V2] (reproducida en Moffitt, 2023) |

### 1.2 Consecuencias para el diseño de la librería

1. **Versionar cada método.** Por ejemplo `RMR(version="1989"|"2014")`, `Q(handbook="2015"|"2025")`, `SMR(variant="romana1985"|"tomas2007")` y `HoekBrown(edition="2002"|"2018")`. El resultado debe guardar la versión usada (trazabilidad para auditorías de Osinergmin, Sernageomin, etc.).
2. **Tablas como datos, no como código.** SRF, Jr, Ja, el ESR y las clases del ábaco de sostenimiento cambiaron en 2025 y van a volver a cambiar. Conviene guardarlas en archivos de datos versionados con su fuente.
3. **Conversión explícita entre versiones** (RMR89 ↔ RMR14, GSI ↔ RMR89) con advertencia de error asociado. Nunca de forma implícita.
4. **Separar descripción (ISO 14689, ISRM) de clasificación (D5878: RMR, Q, etc.).** Son capas distintas.
5. **Normas referenciadas congeladas:** si una ley cita una edición antigua (CFR → ASTM F432-95), el perfil del país debe guardar esa edición aunque exista una más nueva.

---

## 2. Criterios de aceptación de diseño (FS y PoF) disponibles

### 2.1 Read y Stacey (2009), tabla 9.9 (Wesseloo y Read): FoS mínimo estático y PoF máxima [V2]

| Escala del talud | Consecuencia de falla | FoS mín. estático | PoF máx. |
|---|---|---|---|
| Banco | Baja a alta | 1.1 | 25–50 % |
| Interrampa | Baja | 1.15–1.20 | 25 % |
| Interrampa | Media | 1.20 | 20 % |
| Interrampa | Alta | 1.20–1.30 | 10 % |
| Global | Baja | 1.20–1.30 | 15–20 % |
| Global | Media | 1.30 | 5–10 % |
| Global | Alta | 1.30–1.50 | 5 % |

La columna de FoS dinámico (pseudoestático) del original **no se pudo verificar** [NV]. La memoria técnica la sitúa en torno a 1.0–1.1, pero hay que confirmarla en el libro. Fuente secundaria: Moffitt (2023), tabla 1. Ningún país de esta revisión adopta la tabla en su ley. La usan las guías (WA la cita como práctica) y las empresas.

### 2.2 Otras tablas oficiales de FS

| Fuente | Ámbito | Criterio | Fuerza | Marca |
|---|---|---|---|---|
| Osinergmin (2017), *Guía de criterios geomecánicos…*, tabla 5-1 | Subterránea (Perú) | FS > 1.5 a largo plazo (más de 1 año); 1.3–1.5 a mediano plazo (3 meses a 1 año); 1.1–1.3 a corto plazo (menos de 3 meses). «PF de hasta 10 % puede considerarse aceptable si los riesgos se conocen y controlan» | Guía | [V1] |
| WorkSafe WA / DMIRS (2019, actualizado en 2025), *Ground control management…*, tabla 3.2 | Subterránea y superficial (Australia Occidental) | Consecuencia no seria: no aplica. Moderadamente seria: FOS 1.2. Seria o de largo plazo (TSF, rampa principal, falla grande hacia zonas de trabajo): 1.5. Extrema o de largo plazo (taludes permanentes que afectan infraestructura pública después del cierre): 2.0. Ángulos genéricos de cierre: 45° en roca fresca y 25° en roca meteorizada, con franja de 10 m en la cresta | Guía («ejemplo») | [V1] |
| ANM Colombia (2023), *Guía técnica para la gestión de riesgos… fallas geomecánicas*, §7.8.1 | Sostenimiento subterráneo | Cita a Hoek et al. (1995): 1.3 para temporales y 1.5–2.0 para permanentes. Para sostenimiento minero propone **FS = 1.5** | Guía | [V1] |
| Perú, DS 024-2016-EM, art. 264 | Tajo abierto | La pendiente general del tajo se fija en condición **seudoestática** con las aceleraciones sísmicas máximas y las lluvias de un **período de retorno de 100 años**. No fija el FS | Reglamento | [V1] |
| Brasil, NR-22, 22.24.6 | Pilas de estéril | Remite al «factor de seguridad mínimo de las normas técnicas nacionales y de la ANM». ABNT NBR 13029 (pilas de estéril) fijaría FS ≥ 1.5 estático | Reglamento → norma ABNT | Remisión: [V1]. Valor NBR: [NV] |

---

## 3. Perfiles por país

En la columna «Parámetro sugerido» va el nombre de la clave del perfil normativo, solo como propuesta de diseño, no como código.

### 3.1 Perú: DS 024-2016-EM, modificado por DS 023-2017-EM y DS 034-2023-EM

Fuente primaria: texto integrado del MINEM, «Reglamento de Seguridad y Salud Ocupacional en Minería – Guía 2026 y modificatorias», con anexos y guías (gob.pe, publicación 5631689).

**Correcciones a lo que se sabía:**

- El **art. 33 no contiene** el 1 % de control de calidad ni los refugios con RMR > 60.
- El **1 %** está en el **art. 214 b)**.
- **RMR > 60** está en el **Anexo 19** (estaciones de refugio para siniestros), no en los refugios peatonales.
- El art. 33 sí exige tablas y planos geomecánicos en cada labor.
- El DS 034-2023-EM **eliminó la actualización mensual** de los estudios geomecánicos locales que traía el texto anterior. Ahora dice «actualizada en los casos que se amerite».

| Requisito | Tipo | Parámetro sugerido | Artículo | Fuerza | Marca |
|---|---|---|---|---|---|
| Estudios de geología, geomecánica, geotecnia, hidrogeología, estabilidad de taludes, botaderos, sostenimiento, relleno y sismicidad inducida, firmados por ingenieros colegiados y habilitados | Q | `estudios_requeridos[]`, `firma_colegiado=True` | Art. 33, párr. 1 (mod. DS 034-2023-EM, art. 2) | Reglamento | [V1] |
| Estudio geomecánico **global** (subterráneo y superficial) con la estructura del **Anexo 39 A**, basado en ensayos de laboratorio de mecánica de rocas **acreditados** | Q | `estructura_estudio_global = anexo_39A`, `lab_acreditado=True` | Art. 33, párr. 2; Anexo 39 A | Reglamento | [V1] |
| El Anexo 39 A exige como mínimo: mapeo geomecánico, logueo de diamantina, modelo 3D de tajeos, ensayos (propiedades físicas, UCS, carga puntual, triaxial, brasileño, elásticas), RQD, **RMR**, sectores de diseño, parámetros de resistencia, diseño de aberturas, pilares costilla y puente, resistencia del relleno, **modelo numérico** con secuencia, diseño de sostenimiento, e instrumentación y monitoreo | Q | Checklist de entregables. El RMR es el sistema nombrado: la clasificación por defecto del perfil PE es RMR | Anexo 39 A | Reglamento | [V1] |
| Evaluación geomecánica **local** previa a toda labor subterránea (Anexo 39 B): caracterización, condiciones actuales, **cálculo empírico, análisis cinemático de cuñas y modelamiento numérico**, recomendación de excavación y sostenimiento, más una memoria con los parámetros de entrada del software y la copia electrónica de los archivos | Q | `evaluacion_local_requerida=True`, `exportar_memoria_parametros=True` | Art. 33, párr. 3; Anexo 39 B | Reglamento | [V1] |
| Actualizar la evaluación local «en los casos que se amerite». **Antes de DS 034-2023: mensual** | Q (antes C) | `frecuencia_actualizacion_local = "segun_amerite"` (histórico: `"mensual"`) | Art. 33 vigente; texto anterior citado por Osinergmin (TASTEM, 2021) | Reglamento | Vigente: [V1]. Anterior: [V2] |
| **Publicar en cada labor las tablas y planos geomecánicos** con la calidad de roca, las recomendaciones de sostenimiento y dimensionamiento, el estándar y el PETS | Q | Salida `tabla_geomecanica_labor` (formato imprimible) | Art. 33, párr. 3 | Reglamento | [V1] |
| Estudios hidrogeológicos (Anexo 39 C) y de sismicidad inducida (Anexo 39 D: microsísmica, Gutenberg-Richter «b», período de retorno, radios de ruptura, plan de acción) | Q | Módulo de sismicidad: el perfil PE exige los parámetros b y el período de retorno | Art. 33, párr. 4; Anexos 39 C y 39 D | Reglamento | [V1] |
| Estudios de estabilidad de taludes durante la operación y hasta el cierre | Q | `taludes_hasta_cierre=True` | Art. 33, último párrafo | Reglamento | [V1] |
| Sostenimiento sistemático inmediato, «labor avanzada, labor sostenida» | Q | | Art. 213 | Reglamento | [V1] |
| **Registrar mensualmente los ensayos de control de calidad de no menos del 1 % por cada tipo de sostenimiento aplicado en el periodo** | **C** | `qc_sostenimiento_min_pct = 1.0`, `qc_periodo = "mensual"`, `qc_por_tipo=True` | **Art. 214 b)** (mod. DS 034-2023-EM) | Reglamento | [V1] |
| Registro del monitoreo por estallido de rocas | Q | | Art. 214 c) | Reglamento | [V1] |
| Mantener ancho y altura de las labores dentro de los cálculos geomecánicos | Q (límite que da el estudio) | Validación de geometría contra el diseño | Art. 214 g) | Reglamento | [V1] |
| Refugios peatonales **cada 50 m** en galerías. En rampas, ≤ 50 m en tangentes largas y **≤ 30 m** en tangentes cortas y curvas | C | `refugio_peatonal_max_m = 50`, `refugio_rampa_curva_max_m = 30` | Art. 214 i); art. 216 (mod. DS 023-2017) | Reglamento | [V1] |
| Asesoría de un ingeniero especialista en geomecánica por unidad minera | Q | | Art. 214 k) | Reglamento | [V1] |
| Desatado: 2 juegos de 4 barretillas por labor; 1 juego cada **100 m** en galerías y rampas; desatado manual siempre entre **2 personas** | C | `barretillas_juegos_por_labor = 2` | Arts. 218 y 224 c) | Reglamento | [V1] |
| Recuperación de pilares y reingreso a labores paralizadas más tiempo que su autosostenimiento: estudio geomecánico previo y PETAR | Q | | Art. 220 | Reglamento | [V1] |
| Taludes de embudos (*glory hole*) ≤ ángulo de reposo | C (relativo) | `talud_embudo <= angulo_reposo` | Art. 223 | Reglamento | [V1] |
| Desatador mecánico obligatorio si el techo pasa de **4 m**. Sostenimiento mecanizado si la altura pasa de **5 m** | C | `altura_desatado_mecanico_m = 4`, `altura_sostenimiento_mecanizado_m = 5` | Arts. 230 y 231 | Reglamento | [V1] |
| Relleno: UCS «ideal» en función de la densidad y las dimensiones del tajeo. Tapones de relleno hidráulico con evaluación de FS | Q | Módulo de relleno | Arts. 226 b) y 227 c) | Reglamento | [V1] |
| Concreto con pruebas de laboratorio. **Pernos con pruebas de arranque** disponibles para la fiscalización | Q | Registro de *pull tests* | Art. 228 | Reglamento | [V1] |
| Monitoreo de vibraciones por voladura con sismografía | Q | | Arts. 236 y 268 | Reglamento | [V1] |
| **Tajo abierto:** diseño según geomecánica (altura y talud de banco, talud de operación, talud final, **ancho mínimo de bermas**, botaderos) | Q | | Art. 262 a) | Reglamento | [V1] |
| Gradiente de vías principales **≤ 12 %**. Ancho de rampa **≥ 3×** el vehículo más grande (doble vía) y **≥ 2×** (una vía). En terreno incompetente, ancho del equipo + 20 % | C | `gradiente_max_pct = 12`, `ancho_rampa_doble_factor = 3`, `ancho_rampa_simple_factor = 2` | Art. 262 b) y c) | Reglamento | [V1] |
| Muro de seguridad **≥ 3/4 de la altura de la llanta** más grande | C | `berma_seguridad_fraccion_llanta = 0.75` | Art. 262 e) | Reglamento | [V1] |
| Pendiente general del tajo en condición seudoestática, sismo máximo y lluvias con **Tr = 100 años** | C | `tr_sismo_lluvia_anios = 100`, `analisis_seudoestatico=True` | Art. 264 | Reglamento | [V1] |
| Botaderos operados según lo aprobado por la DGM o el gobierno regional. Plan de minado con estudio geomecánico que sustente los ángulos de talud del tajo y el botadero, y diseño del botadero con secuencia de llenado | Q | | Art. 266; Anexo 1 b), c), d) | Reglamento | [V1] |
| Franja no minable de **≥ 100 m** alrededor del límite final del tajo | C | `franja_no_minable_m = 100` | Anexo 1 b) y g.2) | Reglamento | [V1] |
| Radio de seguridad de voladura de **500 m** | C | `radio_voladura_m = 500` | Art. 267 a) | Reglamento | [V1] |
| Estación de refugio para siniestros: excavación en roca con **RMR > 60**; si RMR < 60, sostenimiento adecuado; distancia **≤ 500 m** de los frentes; inspección **trimestral** | C | `refugio_siniestro_rmr_min = 60`, `refugio_distancia_frente_max_m = 500` | **Anexo 19** (art. 151) | Reglamento | [V1] |
| Relaves: borde libre ≥ 1 m; interpretación del monitoreo geotécnico de no más de 2 meses; suspensión de la descarga si el FS cae bajo el mínimo | C | Fuera de alcance, pero modelable | Arts. 418–423 (mod. DS 034-2023, art. 3) | Reglamento | [V1] |
| Criterios de FS y PoF, QC de sostenimiento (pre, durante y post instalación), Mathews, ELOS, span, pilares | C (guía) | Valores por defecto del perfil PE (§2.2) | Osinergmin (2017), caps. 5, 7 y 9 | Guía | [V1] |
| Guía ambiental de estabilidad de taludes de depósitos (MINEM): FS estático 1.5 y seudoestático 1.0 | C | | No ubicada | Guía | [NV] |

### 3.2 Chile: DS 132/2002 (Reglamento de Seguridad Minera), texto vigente de la BCN (versión del 9 de abril de 2024)

| Requisito | Tipo | Parámetro sugerido | Artículo | Fuerza | Marca |
|---|---|---|---|---|---|
| Sostenimiento «sin retardo» según la naturaleza del terreno. Solo puede quedar sin fortificar el terreno con autosoporte demostrado por mediciones y ensayos | Q | `autosoporte_requiere_demostracion=True` | Art. 157 | Reglamento | [V1] |
| Inspección periódica de galerías (con y sin fortificación) | Q | | Art. 158 | Reglamento | [V1] |
| Revisión de piques fortificados en periodos **≤ 6 meses** | C | `revision_piques_max_meses = 6` | Art. 159 | Reglamento | [V1] |
| Acuñadura permanente; procedimiento escrito; prohibido entrar a zonas no fortificadas sin acuñar | Q | | Arts. 160–163 | Reglamento | [V1] |
| **Reglamento interno de fortificación aprobado por Sernageomin** (responde en 30 días) | Q | `requiere_aprobacion_autoridad=True` | Art. 164 | Reglamento | [V1] |
| La fortificación se funda en análisis geológico-geotécnico, solicitaciones, método, uso y duración de la labor | Q | | Art. 165 | Reglamento | [V1] |
| Pernos y malla: materiales certificados; longitud y espaciado «calculados con criterio técnico»; **golilla ≥ 20 cm** (diámetro o lado); resina en toda la longitud; diámetro de perforación adecuado para split set y swellex | C | `golilla_min_cm = 20` | Art. 166 | Reglamento | [V1] |
| Derrumbes solo como parte programada de un método aprobado. Prohibido adelgazar pilares sin reemplazo o autorización | Q | | Art. 168 | Reglamento | [V1] |
| Subsidencia: barreras y señalización en toda la zona posible de hundimiento | Q | | Art. 95 | Reglamento | [V1] |
| **Rajo:** bancos con ancho, alto y talud según geomecánica y equipos | Q | | Art. 237 | Reglamento | [V1] |
| Material no consolidado: **altura de banco ≤ altura de la cabina** del operador y **talud ≤ ángulo de reposo** | C (relativo) | `altura_banco_max = altura_cabina` | Art. 240 | Reglamento | [V1] |
| Distancia mínima de **100 m** a carreteras, líneas de alta tensión, ferrocarril y zonas urbanas | C | `distancia_rajo_infraestructura_m = 100` | Art. 241 | Reglamento | [V1] |
| Explotación rajo y subterránea en la misma vertical: requiere autorización (60 días) | Q | | Art. 243 | Reglamento | [V1] |
| Control permanente de crestas y paredes; acuñadura de bancos con procedimiento | Q | | Art. 245 | Reglamento | [V1] |
| Botaderos con proyecto aprobado que garantice la estabilidad (60 días); diseño según la resistencia del suelo, el material, **el ángulo estable incluso al cierre**, la altura, el drenaje y la **sismicidad natural o inducida** | Q | | Arts. 339–340 | Reglamento | [V1] |
| Botaderos: cordón de seguridad de **≥ 1/2 rueda** del camión más grande; **pendiente positiva ≥ 1 %** hacia el borde | C | `berma_seguridad_fraccion_rueda = 0.5`, `pendiente_botadero_min_pct = 1` | Art. 342 b) y c) | Reglamento | [V1] |
| Requiere **Proyecto Minero** (no simple declaración) en estos casos: recuperación de pilares; ingreso a caserones sin control de techo; taludes verticales o bancos altos sin control; *block caving* con subsidencia; **socavones de más de 4 m** de alto o ancho; **bancos de más de 5 m** de alto | C | `umbral_seccion_proyecto_m = 4`, `umbral_banco_proyecto_m = 5` | Art. 597 | Reglamento | [V1] |
| Guía metodológica de seguridad para proyectos de rajo abierto (Sernageomin, 2004, §4.5.4 estabilización de taludes) | Q | | Guía (archivo web) | Guía | [V2] |
| Guía metodológica para evaluar la estabilidad física de instalaciones mineras remanentes (Sernageomin y PUCV, 2018) y guía de presentación de proyectos de botaderos (2023): FS mínimos | C | | No se pudo descargar | Guía | [NV] |

### 3.3 Australia

**Australia Occidental (WA).** Desde el 31 de marzo de 2022 rigen la WHS Act 2020 y las WHS (Mines) Regulations 2022. El código de 2019 todavía cita el reglamento derogado MSI Regs 1995 (r. 10.28 y 13.8).

| Requisito | Tipo | Parámetro sugerido | Artículo | Fuerza | Marca |
|---|---|---|---|---|---|
| La «inestabilidad de estructuras geotécnicas» es un **peligro minero principal** (*principal mining hazard*: potencial de muertes múltiples) → plan de gestión obligatorio | Q | `peligro_principal=True` | WHS (Mines) Regs 2022, r. 612(2)(a), r. 627 y r. 628 | Reglamento | [V1] |
| Gestionar los riesgos de estructuras geotécnicas considerando: geología e hidrología; diseño, construcción y mantenimiento; **diseño, instalación, control de calidad y mantenimiento del sostenimiento**; vida de diseño; inspección y monitoreo; competencia de las personas. Aplica del diseño al cierre | Q | | r. 631B | Reglamento | [V1] |
| Lista Schedule 19, cl. 1 (17 materias): efecto del agua y la oxidación; geometría de aberturas y pilares; secuencia; relleno; sostenimiento (incluido el momento de instalación y su QC); voladura; **sismicidad** (probabilidad, monitoreo, análisis); fundaciones; emergencias; integración con el cierre | Q | Checklist del plan | Schedule 19, cl. 1 | Reglamento | [V1] |
| Código de práctica de control de terreno: modelo geotécnico por dominios; métodos de diseño (empírico, cinemático, equilibrio límite, numérico); criterios de aceptación justificados y documentados | Q | | *Ground control for WA mining operations – Code of practice* (2019) | Código (aprobado) | [V1] |
| Tabla de FOS por consecuencia (1.2 / 1.5 / 2.0) y ángulos de cierre de 45° y 25° con franja de 10 m | C | `fs_por_consecuencia{}`, `angulo_cierre_fresca = 45`, `angulo_cierre_meteorizada = 25` | Guía, tabla 3.2 | Guía | [V1] |

**Nueva Gales del Sur (NSW).** WHS (Mines and Petroleum Sites) Regulation 2022, vigente desde el 1 de septiembre de 2022. El texto oficial no se pudo descargar (legislation.nsw.gov.au bloquea). Lo que sigue sale del **borrador oficial de consulta pública** del regulador: la numeración final puede variar.

| Requisito | Tipo | Parámetro sugerido | Artículo (borrador) | Fuerza | Marca |
|---|---|---|---|---|---|
| *Ground or strata failure* y *subsidence* son peligros principales | Q | | cl. 5 | Reglamento | [V2] |
| Nadie entra a terreno sin sostener; sostenimiento temporal suficiente para instalar el definitivo; **planos del sostenimiento expuestos** donde los trabajadores los vean | Q | Salida «plano de sostenimiento» (análoga a la tabla geomecánica de Perú) | cl. 57 | Reglamento | [V2] |
| Schedule 1, cl. 1: 24 materias del plan, entre ellas estabilidad de taludes, botaderos, desatado, QC de pernos, dimensiones de caserones y pilares, y **estallidos de roca** | Q | | Sch. 1, cl. 1(1)(a)–(x) | Reglamento | [V2] |
| Carbón subterráneo: incluir en el plan el **ancho máximo entre pilares y la dimensión mínima de pilar** con su cálculo; ensanche de galerías a **más de 5.5 m** requiere planos firmados, informe geotécnico y control de estratos | C | `ancho_galeria_carbon_umbral_m = 5.5` | Sch. 1, cl. 1(2)–(3) | Reglamento | [V2] |
| El plan debe declarar que el sostenimiento indicado es **mínimo** y que siempre se permite agregar más | Q | | Sch. 1, cl. 1(4) | Reglamento | [V2] |

**Queensland (QLD).** Mining and Quarrying Safety and Health Regulation 2017 (texto vigente).

| Requisito | Tipo | Parámetro sugerido | Artículo | Fuerza | Marca |
|---|---|---|---|---|---|
| Prevenir o controlar fallas locales y de área. Considerar geología, geometría, labores antiguas, agua y datos geotécnicos (incluido el monitoreo) | Q | | s. 44(1)–(2) | Reglamento | [V1] |
| Las medidas **deben incluir**: minimizar el daño por voladura en el perímetro; equipos y procedimientos de desatado; diseño, instalación y **QC del sostenimiento**; momento de instalación según el comportamiento de la roca | Q | | s. 44(3) | Reglamento | [V1] |
| *Recognised standards* o *guidance notes* (QGN) específicos de control de terreno | — | | No se encontraron | — | [NV] |

### 3.4 Canadá

**Ontario.** R.R.O. 1990, Reg. 854 (Mines and Mining Plants), texto consolidado de e-Laws, Word del 7 de julio de 2025.

| Requisito | Tipo | Parámetro sugerido | Artículo | Fuerza | Marca |
|---|---|---|---|---|---|
| Diseño de mina que evalúe la estabilidad del terreno (subterránea y tajo de mena metálica), preparado bajo la dirección de un **ingeniero**. Contenido: geología y geotecnia, geometría, historial de inestabilidad, método y secuencia, **sistema de sostenimiento**, instrumentación y modelamiento | Q | | s. 6(1)–(2.1) | Reglamento | [V1] |
| **Actualizar el diseño al menos una vez al año** y antes de cambios significativos | C | `frecuencia_actualizacion_diseno = "anual"` | s. 6(3) | Reglamento | [V1] |
| Alterar o crear una excavación sin sostenimiento requiere un informe de ingeniero | Q | | s. 6.1 | Reglamento | [V1] |
| Pilar de **60 m** a cada lado del límite de propiedad | C | `pilar_limite_m = 60` | s. 19 | Reglamento | [V1] |
| Examinar el terreno antes de trabajar; procedimientos escritos de instalación del sostenimiento y de exposición a terreno sin sostener; no hacer otros trabajos durante el desatado | Q | | ss. 66, 67, 67.1 | Reglamento | [V1] |
| Iluminación de **≥ 1500 lux a 1.2 m** (lámpara de casco) para evaluar el terreno | C | | s. 69(2) | Reglamento | [V1] |
| **Programa de gestión de riesgo sísmico**: zonas de alto riesgo, monitoreo microsísmico y frecuencia de análisis, protocolo de reingreso; revisión **anual** | C | `revision_programa_sismico = "anual"` | s. 71.1 (O. Reg. 69/23) | Reglamento | [V1] |
| Registro de estallidos, caídas no controladas y eventos sísmicos significativos | Q | | s. 72 | Reglamento | [V1] |
| **Programa de control de calidad** del sostenimiento con registro de ensayos | Q | | s. 73 | Reglamento | [V1] |
| Tajo en suelo con equipo: cara al ángulo de reposo o **≤ 1.5 m sobre el alcance del equipo**; manual, **≤ 3 m**; sin socavar | C | `altura_cara_sobre_alcance_m = 1.5` | s. 88 | Reglamento | [V1] |
| Tajo en roca: **cara ≤ 25 m**, salvo que un ingeniero certifique otra cosa | C | `altura_cara_roca_max_m = 25` | s. 89 | Reglamento | [V1] |
| Retirar el material suelto a **2 m** del borde; sobrecarga por debajo del ángulo de reposo; **6 m** al límite de propiedad (roca) o 1/2 de la profundidad (suelo) | C | | ss. 91–92 | Reglamento | [V1] |
| Inspección de la cara tras la voladura o tras **más de 7 días** sin operar; no acumular rocas en las bermas | C | | s. 93 | Reglamento | [V1] |

**Columbia Británica (BC).** Health, Safety and Reclamation Code for Mines in BC, revisión de **junio de 2026**.

| Requisito | Tipo | Parámetro sugerido | Artículo | Fuerza | Marca |
|---|---|---|---|---|---|
| Sostenimiento eficaz, instalado y mantenido, más un **programa de control de calidad** según una persona calificada | Q | | 6.3.5 | Código (obligatorio) | [V1] |
| Inspección de las áreas subterráneas por el supervisor **al menos 2 veces por turno** | C | `inspecciones_por_turno_min = 2` | 6.4.1(2) | Código | [V1] |
| Retirar el material no consolidado a **2 m** del borde | C | | 6.23.1 | Código | [V1] |
| **Berma de captura con ancho final ≥ 8 m** | C | `berma_captura_min_m = 8` | 6.23.2(1) | Código | [V1] |
| Sin voladizos; componente vertical de la cara **≤ 2 m más allá del alcance** del equipo de carguío (con excepciones: bancos múltiples autorizados, material suelto de ≤ 60° y ≤ 30 m) | C | `altura_cara_sobre_alcance_m = 2` | 6.23.3–6.23.5 | Código | [V1] |
| Desatado de verificación (*check scaling*) periódico de labores y vías | Q | | 6.25.2 | Código | [V1] |
| Botaderos mayores operados y monitoreados según las ***Interim Guidelines* del BC Mine Waste Rock Pile Research Committee**; informe anual de desempeño de botaderos de alto riesgo (31 de marzo) | Q | Perfil BC: criterio de FS de botaderos = Interim Guidelines (1991) | 10.7.1 | Código → guía | [V1] |
| Retiro de **5 m** al límite en suelo y talud ≤ **1.5H:1V** | C | | 10.7.4 | Código | [V1] |

**Quebec.** Règlement sur la santé et la sécurité du travail dans les mines (RLRQ c. S-2.1, r. 14). LégisQuébec bloqueó la descarga. **No verificado** [NV]: queda pendiente para una sesión con acceso.

### 3.5 Sudáfrica: MHSA 29 de 1996 y reglamentos

| Requisito | Tipo | Parámetro sugerido | Artículo | Fuerza | Marca |
|---|---|---|---|---|---|
| Código de práctica obligatorio (COP) según secciones 9(2) y 9(3) de la MHSA, cuando el inspector jefe lo exige mediante guía | Q | `requiere_cop=True` | MHSA s. 9 | Ley | [V2] (Durrheim et al., ACG) |
| Guía para elaborar el COP contra caída de rocas y estallidos en minas metalíferas tabulares (DME 16/3/2/1-A3, rev. 1, febrero de 2002). Pide monitorear el desempeño del sostenimiento en excavaciones importantes | Q | | Guía DME/DMR | Guía obligatoria para el COP | [V2] |
| Capítulo 14 de los reglamentos (*Fall of ground*, GN R.959, 12 de julio de 2002): examen y saneamiento antes de entrar (14.1, 14.2); **designación de una persona competente en ingeniería de rocas** (14.1(8)) | Q | | Reg. 14.1–14.2 | Reglamento | [V2] (texto no accesible) |
| Guías equivalentes para estabilidad de taludes en minas a cielo abierto | — | | No ubicadas | — | [NV] |

### 3.6 Estados Unidos: 30 CFR (eCFR al 1 de octubre de 2026)

| Requisito | Tipo | Parámetro sugerido | Artículo | Fuerza | Marca |
|---|---|---|---|---|---|
| Métodos que mantengan la estabilidad de paredes y taludes. **Ancho y altura de banco según el equipo** de limpieza y desatado | Q | | §56.3130 | Reglamento | [V1] |
| Material suelto en el perímetro del tajo: al ángulo de reposo o retirado **≥ 10 ft** desde el borde | C | `franja_perimetro_ft = 10` (unidades imperiales) | §56.3131 | Reglamento | [V1] |
| Condiciones peligrosas: bajar o sostener antes de trabajar; señalizar y poner barrera | Q | | §56/57.3200 | Reglamento | [V1] |
| Pernos según **ASTM F432-95** (certificado del fabricante) | Q | `norma_pernos = "ASTM F432-95"` | §56/57.3203(a) | Reglamento | [V1] |
| Tolerancia de broca de acabado **±0.030 in** | C | | §57.3203(d) | Reglamento | [V1] |
| Pernos tensados por torque: tensión **≥ 50 %** del menor valor entre la fluencia del perno y la capacidad de anclaje, y ≤ ese valor. Medir el torque del **primero, cada décimo y el último** perno por área y turno | C | `qc_torque_muestreo = "1ro, cada 10, ultimo"`, `tension_min_frac = 0.5` | §57.3203(f) | Reglamento | [V1] |
| Pernos con lechada: el primero de cada lugar de trabajo se prueba a **150 ft·lb**; si gira, se prueba un segundo; si este también gira, acción correctiva | C | `torque_prueba_lechada_ftlb = 150` | §57.3203(g) | Reglamento | [V1] |
| Sostenimiento donde las condiciones o la experiencia lo indiquen; diseñado, instalado y mantenido | Q | | **§57.3360** | Reglamento | [V1] |
| Examinar el terreno antes del trabajo, después de la voladura y según las condiciones. Vías subterráneas y paredes junto a vías: **semanalmente** | C | `inspeccion_vias = "semanal"` | §57.3401 | Reglamento | [V1] |
| Estallido de roca: aviso a MSHA en **24 h** (si obliga a retirar personas, afecta la ventilación, impide el paso o detiene más de 1 h); **plan de control en 90 días** | C | `aviso_estallido_h = 24`, `plazo_plan_estallido_d = 90` | §57.3461 | Reglamento | [V1] |
| Carbón subterráneo: plan de control de techo **aprobado por el District Manager** | Q | | §75.220 | Reglamento | [V1] |
| Carbón superficial: plan de control de terreno para *highwalls* y botaderos; examen de paredes **después de cada lluvia, helada o deshielo** | C (evento) | | §77.1000 y §77.1004 | Reglamento | [V1] |
| Guías NIOSH (por ejemplo, para el diseño de pilares) | — | | No revisadas en esta sesión | — | [NV] |

### 3.7 México: NOM-023-STPS-2012 (DOF, 11 de octubre de 2012; vigente desde el 11 de octubre de 2013)

| Requisito | Tipo | Parámetro sugerido | Artículo | Fuerza | Marca |
|---|---|---|---|---|---|
| Reconocimiento de la seguridad de frentes y tajos **en cada turno**, con registro (subterránea: fortificación; cielo abierto: estabilidad de taludes) | C | `inspeccion_frente = "por_turno"` | 5.8 | NOM obligatoria | [V1] |
| Antes de trabajar: estudios geotécnicos (mecánica de rocas o suelos), geológicos e hidrológicos; actualizarlos cuando cambien las condiciones; conservarlos durante la vida de la mina | Q | | 8.1.1–8.1.3 (subterránea); 9.1.1–9.1.3 (cielo abierto) | NOM | [V1] |
| **Plan de fortificación** con dimensiones, planos, diseño de pilares, criterios de selección del ademe, control de desplazamientos y modificación ante cambios geológicos | Q | Checklist | 8.2.4 | NOM | [V1] |
| Profundidad máxima de avance (minero continuo) según el estudio de mecánica de rocas; registro de revisiones de ademes | Q | | 8.2.11 d) y e) | NOM | [V1] |
| Cielo abierto: procedimientos de excavación y estabilización basados en los estudios | Q | | 9.2.2–9.2.5 | NOM | [V1] |
| Contrapeso de la excavadora a **≥ 2 m** del borde del banco o escombrera; pendiente de apoyo ≤ la del estudio de mecánica de rocas | C | `distancia_borde_excavadora_m = 2` | 9.2.9 d) y e) | NOM | [V1] |

### 3.8 Colombia

| Requisito | Tipo | Parámetro sugerido | Artículo | Fuerza | Marca |
|---|---|---|---|---|---|
| **Subterránea:** plan de sostenimiento obligatorio (Título IV), con estudio geomecánico y ensayos geológicos y geomecánicos cuando sea necesario | Q | | Decreto 1886 de 2015, Título IV, art. 76 (citado en autos de la ANM); arts. 81–82; modificado por el Decreto 944 de 2022 | Decreto | [V2] |
| Requisitos para elaborar planes de sostenimiento | Q | | NTC 6620:2022 (ICONTEC) | Norma técnica | [V2] |
| Guía técnica ANM–UPTC (noviembre de 2023): RMR, Q, GSI cuantificado; FS de sostenimiento = 1.5 | C | `fs_sostenimiento_default = 1.5` | Guía, §7.3 y §7.8.1 | Guía | [V1] |
| **Cielo abierto:** diseño previo según la geomecánica (altura y talud de banco, talud final, ancho mínimo de bermas, escombreras) | Q | | Decreto 539 de 2022, art. 85 | Decreto | [V1] |
| **Taludes de más de 20 m:** estudio geotécnico con cálculo de FS **aprobado por la autoridad minera** antes de iniciar | C | `umbral_talud_estudio_aprobado_m = 20` | Decreto 539/2022, art. 86 | Decreto | [V1] |
| Inspección de taludes después de lluvias fuertes y de la ladera sobre la corona | Q | | art. 88 | Decreto | [V1] |
| Bermas en material no consolidado con el ancho que fije el estudio geotécnico. Zonas de retención en bancos | Q | | arts. 89–90 | Decreto | [V1] |
| Escombreras: ángulo estable incluso al cierre; **pendiente positiva ≥ 1 %**; cordón de **≥ 1/2 diámetro de rueda**; protocolo con revisión de los sistemas de control geotécnico de movimiento | C | `pendiente_botadero_min_pct = 1`, `berma_seguridad_fraccion_rueda = 0.5` | arts. 71–73 | Decreto | [V1] |

### 3.9 Brasil: NR-22 (nueva redacción por la Portaria MTE n.º 225/2024 y modificatorias)

| Requisito | Tipo | Parámetro sugerido | Artículo | Fuerza | Marca |
|---|---|---|---|---|---|
| Procedimientos técnicos para controlar la estabilidad de los macizos: monitoreo de estratos, tratamiento de techo y paredes, **monitoreo de bancos y taludes**, áreas ya minadas, agua y fallas | Q | | 22.13.2 | NR (obligatoria) | [V1] |
| Métodos con hundimiento controlado o recuperación de pilares: monitoreo permanente bajo un profesional habilitado | Q | | 22.13.2.1 | NR | [V1] |
| **Lista de indicadores de inestabilidad** que obligan a paralizar y retirar al personal (cielo abierto: grietas en la cresta, bloques sueltos, subsidencia, taludes negativos, agua en fracturas; subterránea: bloques, roturas en pilares, agua anómala, deformación del sostenimiento) | Q | Reglas de alarma del módulo de monitoreo | 22.13.3–22.13.3.2.1 | NR | [V1] |
| Distancia mínima de material y equipos a la cresta según la estabilidad y la altura del banco, declarada en el PGR | C (la define el proyecto) | | 22.13.4 | NR | [V1] |
| Aberturas subterráneas diseñadas según la NR, **las normas de la ANM y las normas nacionales e internacionales vigentes**; evaluadas por un profesional habilitado | Q | Remisión a estándares de método (§1) | 22.14.1–22.14.1.1 | NR | [V1] |
| Abatimiento de chocos: mecanizado de preferencia; **mínimo 2 trabajadores** en abatimiento, contención y perforación del macizo | C | | 22.6.3; 22.14.7.2 | NR | [V1] |
| Material desmontado a **> 10 m** de los accesos a piques; protección de vías con inclinación de **más de 35°** | C | | 22.14.9–22.14.10 | NR | [V1] |
| Vías: ancho **≥ 2×** el vehículo más grande (simple) y **≥ 3×** (doble); leiras de **≥ 1/2 del diámetro del neumático** más grande | C | `berma_seguridad_fraccion_llanta = 0.5` (diámetro) | 22.7.6 b) y c) | NR | [V1] |
| Pilas de estéril: estudios geotécnicos, hidrológicos e hidrogeológicos previos; monitoreo de percolación, nivel freático y desplazamientos; **FS mínimo de las normas ABNT y de la ANM** | C (por remisión) | `fs_pilas = norma_nacional` | 22.24.4–22.24.6 | NR → ABNT/ANM | [V1] |

### 3.10 Bolivia, Ecuador y Argentina

- **Argentina:** Decreto 249/2007, Reglamento de Higiene y Seguridad para la Actividad Minera. Existe, pero no se pudo descargar el anexo para ubicar los artículos de sostenimiento y taludes [NV].
- **Ecuador:** hay versiones en conflicto del Reglamento de SST del Ámbito Minero (ARCOM 2014 y ARCERNNR 013-2020). No se encontraron disposiciones geomecánicas específicas [NV].
- **Bolivia:** no se encontró una norma específica de control de terreno en esta sesión [NV].

Recomendación: no crear perfiles para estos tres países hasta verificar la fuente. Mientras tanto, solo un perfil «genérico» con Read y Stacey.

---

## 4. Síntesis para el diseño del «perfil normativo»

### 4.1 Lo común a todos los países (núcleo, no configurable)

1. **Estudio geomecánico o geotécnico obligatorio**, firmado por un profesional habilitado y actualizado cuando cambian las condiciones (PE, CL, MX, BR, CO, ON, BC, WA, NSW, QLD).
2. **Inspección del terreno y desatado o acuñadura antes de trabajar y después de cada voladura** (todos).
3. **Plan o programa escrito de sostenimiento y control de terreno**, más un **programa de control de calidad del sostenimiento** (PE art. 214, ON s. 73, BC 6.3.5, WA r. 631B, QLD s. 44, NSW Sch. 1, US §57.3203, CL art. 164).
4. **Taludes de tajo y botaderos diseñados por estudio geotécnico.** La ley casi nunca fija el FS: lo delega a guías o normas técnicas.
5. **Monitoreo sísmico o de estallidos** donde aplique (PE Anexo 39 D, ON s. 71.1, US §57.3461, WA Sch. 19, NSW Sch. 1 (x)).
6. **Cordón o berma de seguridad proporcional al neumático** y **ancho de vía proporcional al vehículo** en casi todos los países de Latinoamérica.

### 4.2 Lo que varía y debe ser configurable

| Familia de parámetros | Ejemplos de valores (fuente) |
|---|---|
| **Criterio de aceptación** (FS o PoF por escala, plazo y consecuencia) | Osinergmin 1.1–1.5 por plazo; WA 1.2/1.5/2.0 por consecuencia; Read y Stacey por escala; ANM 1.5. **Siempre como «guía» y nunca como «ley»**, salvo una remisión expresa (BR → ABNT) |
| **QC del sostenimiento** (muestreo y frecuencia) | PE ≥ 1 % mensual por tipo; US primero, cada décimo y último perno por turno, y 150 ft·lb |
| **Frecuencia de actualización e inspección** | ON diseño anual; PE «según amerite» (antes mensual); BC 2 inspecciones por turno; MX por turno; US semanal en vías; CL piques cada 6 meses o menos; US carbón tras lluvia o helada |
| **Geometría de tajo** | Altura de cara relativa al alcance (ON +1.5 m, BC +2 m); cara de roca de 25 m o menos (ON); berma de captura de 8 m o más (BC); banco no consolidado no más alto que la cabina (CL); gradiente de 12 % o menos (PE); franjas de 100 m (PE, CL), 2 m (ON, BC) y 10 ft (US) |
| **Cordón de seguridad** | ¾ de la altura de la llanta (PE) frente a ½ rueda o diámetro (CL, CO, BR) |
| **Umbrales que activan aprobación de la autoridad** | CL: sección de más de 4 m y banco de más de 5 m; CO: talud de más de 20 m; ON: cara de más de 25 m (ingeniero); NSW: galería de carbón de más de 5.5 m |
| **Sismo y clima de diseño** | PE: seudoestático con Tr = 100 años |
| **Sistema de clasificación por defecto y su versión** | PE nombra RMR (Anexo 39 A); NGI dice que el ESR depende del país; CO usa RMR, Q y GSI |
| **Requisitos de entregables** | PE: tablas y planos en cada labor más la memoria de parámetros del software (Anexo 39 B); NSW: planos de sostenimiento expuestos |
| **Unidades y normas referenciadas congeladas** | US en imperial y ASTM F432-95 |

### 4.3 Recomendación de estructura (descriptiva, sin código)

- Cada valor del perfil se guarda con estos campos: **jurisdicción, norma, artículo, versión o fecha de vigencia, fuerza jurídica (ley, reglamento, código o guía), marca de verificación ([V1]/[V2]/[NV]), unidad y URL de la fuente**.
- Hay dos capas independientes: **perfil normativo** (país o estado) y **perfil de método** (versión de RMR, Q, GSI, Hoek-Brown, SMR o Q-slope).
- Los perfiles con datos [NV] se cargan, pero el resultado debe advertirlo (por ejemplo, «criterio no verificado»).
- La librería **verifica el cumplimiento y documenta**, pero no reemplaza el estudio firmado que exigen todas las normas.

---

## 5. Vacíos y pendientes

- Quebec (S-2.1, r. 14), el texto oficial final de NSW, los *recognised standards* y QGN de QLD, el texto del capítulo 14 de Sudáfrica y sus guías de taludes: no se pudieron descargar.
- Sernageomin: los FS de las guías de estabilidad física (2018) y de botaderos (2023), sin verificar.
- El FoS dinámico de Read y Stacey (2009), el contenido de roca de EN 1997-2:2024, la fórmula de correlación RMR14 ↔ RMR89 y la fórmula de Q-slope: verificar en las fuentes originales (de pago o con DOI).
- La guía ambiental de taludes de depósitos del MINEM (FS 1.5 y 1.0) y la ABNT NBR 13029 (FS 1.5): sin verificar.
- Las ediciones vigentes de cada norma ASTM de ensayo (D7012, D5731, D3967, D4543, D6032, D5607, F432).

---

## 6. Bibliografía (APA 7)

Ministério do Trabalho e Emprego. (2024). *Portaria MTE n.º 225, de 26 de fevereiro de 2024: Nova redação da Norma Regulamentadora n.º 22 – Segurança e saúde ocupacional na mineração*. https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/inspecao-do-trabalho/seguranca-e-saude-no-trabalho/sst-portarias/2024/portaria-mte-no-225-nova-nr-22.pdf

Agencia Nacional de Minería & Universidad Pedagógica y Tecnológica de Colombia. (2023). *Guía técnica para la gestión de los riesgos mineros causados por fallas geomecánicas*. https://www.anm.gov.co/sites/default/files/guia_tecnica_gestipn_de_riesgos_geomecanicos_140224.pdf

ASTM International. (2019). *Standard guides for using rock-mass classification systems for engineering purposes* (ASTM D5878-19). https://doi.org/10.1520/D5878-19

Bar, N., & Barton, N. (2017). The Q-slope method for rock slope engineering. *Rock Mechanics and Rock Engineering, 50*, 3307–3322. https://doi.org/10.1007/s00603-017-1305-0

Barton, N., Lien, R., & Lunde, J. (1974). Engineering classification of rock masses for the design of tunnel support. *Rock Mechanics, 6*(4), 189–236. [Cita no verificada en línea]

Bieniawski, Z. T. (1989). *Engineering rock mass classifications*. Wiley.

British Columbia Ministry of Mining and Critical Minerals. (2026). *Health, safety and reclamation code for mines in British Columbia* (rev. junio de 2026). https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/mineral-exploration-mining/documents/health-and-safety/code-review/minescode_june_2026.pdf

Celada, B., Tardáguila, I., Varona, P., Rodríguez, A., & Bieniawski, Z. T. (2014). Innovating tunnel design by an improved experience-based RMR system. En *Proceedings of the World Tunnel Congress 2014*. ITA-AITES. https://library.ita-aites.org/wtc/986-innovating-tunnel-design-by-an-improved-experience-based-rmr-system.html

Chile, Ministerio de Minería. (2004). *Decreto Supremo N.º 132: Reglamento de Seguridad Minera* (versión del 9 de abril de 2024). Biblioteca del Congreso Nacional. https://www.bcn.cl/leychile/navegar?idNorma=221064

Colombia, Ministerio de Minas y Energía. (2022). *Decreto 539 de 2022: Reglamento de higiene y seguridad en las labores mineras a cielo abierto*. https://www.anm.gov.co/sites/default/files/decreto_539_del_8_de_abril_de_2022.pdf

Department of Mines, Industry Regulation and Safety. (2019). *Ground control for Western Australian mining operations: Code of practice*. Government of Western Australia. https://worksafe.wa.gov.au/system/files/documents/2025-02/MSH_CoP_GroundControl.pdf

Department of Mines, Industry Regulation and Safety. (2019). *Ground control management in Western Australian mining operations: Guideline*. Government of Western Australia. https://worksafe.wa.gov.au/system/files/documents/2025-02/MSH_GL_GroundControl.pdf

Franzén, G., Batali, L., & Burlon, S. (2026). 2nd generation of Eurocode 7: Overview. En *Proceedings of the 21st International Conference on Soil Mechanics and Geotechnical Engineering* (Viena). https://doi.org/10.53243/ICSMGE2026-769

Hoek, E., & Brown, E. T. (2019). The Hoek–Brown failure criterion and GSI – 2018 edition. *Journal of Rock Mechanics and Geotechnical Engineering, 11*(3), 445–463. https://doi.org/10.1016/j.jrmge.2018.08.001

Hoek, E., Carranza-Torres, C., & Corkum, B. (2002). Hoek-Brown failure criterion – 2002 edition. En *Proceedings of NARMS-TAC 2002* (pp. 267–273). Toronto. [Cita no verificada en línea]

Hoek, E., Carter, T. G., & Diederichs, M. S. (2013). Quantification of the Geological Strength Index chart. En *47th US Rock Mechanics/Geomechanics Symposium* (ARMA 13-672). [Cita no verificada en línea]

International Organization for Standardization. (2017). *Geotechnical investigation and testing — Identification, description and classification of rock* (ISO 14689:2017).

Laubscher, D. H., & Jakubec, J. (2001). The MRMR rock mass classification for jointed rock masses. En W. A. Hustrulid & R. L. Bullock (Eds.), *Underground mining methods: Engineering fundamentals and international case studies*. SME. [Cita no verificada en línea]

México, Secretaría del Trabajo y Previsión Social. (2012). *NOM-023-STPS-2012, Minas subterráneas y minas a cielo abierto – Condiciones de seguridad y salud en el trabajo*. Diario Oficial de la Federación. https://platiica.economia.gob.mx/normalizacion/wp-content/uploads/sites/2/PDF_Normas_Publicas/023stps2012.pdf

Ministerio de Energía y Minas. (2026). *Reglamento de seguridad y salud ocupacional en minería (D.S. N.º 024-2016-EM y modificatorias)*, anexos y guías. https://www.gob.pe/institucion/minem/informes-publicaciones/5631689-reglamento-de-seguridad-y-salud-ocupacional-en-mineria-ed-2024

Moffitt, K. (2023). Critical challenges impacting the advancement of slope design reliability. En P. M. Dight (Ed.), *SSIM 2023: Third International Slope Stability in Mining Conference* (pp. 23–36). Australian Centre for Geomechanics. https://papers.acg.uwa.edu.au/d/2335_0.02_Moffitt/0.02_Moffitt.pdf

Norwegian Geotechnical Institute. (2025). *Using the Q-system: Rock mass classification and support design* (handbook, rev. abril de 2025) y *Change log for the handbook "Using the Q-system", revision 2025*. https://www.ngi.no/globalassets/bilder/forskning-og-radgivning/bygg-og-anlegg/change-log-q-handbook-revision-2025_final.pdf

NSW Resources Regulator. (2022). *Work Health and Safety (Mines and Petroleum Sites) Regulation 2022: Public consultation draft*. https://www.resources.nsw.gov.au/sites/default/files/2022-06/Public-consulation-draft-WHS-MPS-Regulation-2022.pdf

Ontario. (1990, consolidado a 2025). *R.R.O. 1990, Reg. 854: Mines and mining plants* (Occupational Health and Safety Act). https://www.ontario.ca/laws/regulation/900854

Osinergmin. (2017). *Guía de criterios geomecánicos para diseño, construcción, supervisión y cierre de labores subterráneas*. https://www.osinergmin.gob.pe/seccion/centro_documental/mineria/Documentos/Publicaciones/Guia-Criterios-Geomecanicos.pdf

Osinergmin, Tribunal de Apelaciones de Sanciones en Temas de Energía y Minería. (2021). *Otros criterios resolutivos 2021-II*. https://cdn.www.gob.pe/uploads/document/file/7443261/6340236-tastem-otros-criterios-resolutivos-2021-ii.pdf

Queensland. (2017). *Mining and Quarrying Safety and Health Regulation 2017* (texto vigente). https://www.legislation.qld.gov.au/view/whole/html/inforce/current/sl-2017-0166

Read, J., & Stacey, P. (Eds.). (2009). *Guidelines for open pit slope design*. CSIRO Publishing.

Romana, M. (1985). New adjustment ratings for application of Bieniawski classification to slopes. En *Proceedings of the International Symposium on the Role of Rock Mechanics* (pp. 49–53). ISRM. [Cita no verificada en línea]

Servicio Nacional de Geología y Minería. (2004). *Guía metodológica de seguridad para proyectos mineros de rajo abierto*. https://bac-lac.wayback.archive-it.org/web/20060201165435/http://www.idrc.ca/uploads/user-S/11199737701rajo_sernageomin.pdf

Tomás, R., Delgado, J., & Serón, J. B. (2007). Modification of slope mass rating (SMR) by continuous functions. *International Journal of Rock Mechanics and Mining Sciences, 44*(7), 1062–1069. https://doi.org/10.1016/j.ijrmms.2007.02.004

Ulusay, R. (Ed.). (2015). *The ISRM suggested methods for rock characterization, testing and monitoring: 2007–2014*. Springer. https://doi.org/10.1007/978-3-319-07713-0

Ulusay, R., & Hudson, J. A. (Eds.). (2007). *The complete ISRM suggested methods for rock characterization, testing and monitoring: 1974–2006*. ISRM Turkish National Group.

United States. (2026). *Code of Federal Regulations, Title 30, Parts 56, 57 (Subpart B – Ground Control), 75.220 y 77 (Subpart K)*. eCFR. https://www.ecfr.gov/current/title-30

Velarde, [inicial por verificar], & Macciotta, R. (2023). [Título exacto por verificar: aplica criterios de aceptación basados en confiabilidad (RBDAC 2020) y los compara con la DAC 2009]. En *SSIM 2023*. Australian Centre for Geomechanics. https://papers.acg.uwa.edu.au/d/2335_08_Velarde/08_Velarde.pdf

Western Australia. (2022). *Work Health and Safety (Mines) Regulations 2022*. https://legislation.wa.gov.au/legislation/prod/filestore.nsf/FileURL/mrdoc_45831.htm/$FILE/Work%20Health%20and%20Safety%20(Mines)%20Regulations%202022%20-%20%5B00-d0-00%5D.html

Wesseloo, J., & Read, J. (2009). Acceptance criteria. En J. Read & P. Stacey (Eds.), *Guidelines for open pit slope design* (cap. 9). CSIRO Publishing.
