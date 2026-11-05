"""Textos del informe en es/en. Un solo diccionario: REPORT_TEXTS[clave][idioma]."""

DISCLAIMER = {
    "es": "La librería recomienda, el ingeniero decide. Este documento no reemplaza el estudio geomecánico firmado.",
    "en": "The library recommends, the engineer decides. This document does not replace the signed geomechanical study.",
}

REPORT_TEXTS: dict[str, dict[str, str]] = {
    "default_title": {"es": "Informe geomecánico", "en": "Geomechanical report"},
    "prepared_by": {"es": "Elaborado por", "en": "Prepared by"},
    "memoria_title": {"es": "Memoria de cálculo", "en": "Calculation report"},
    "s1": {"es": "Objetivo y alcance", "en": "Purpose and scope"},
    "s1_text": {
        "es": "Este documento clasifica tramos de labores subterráneas con las tablas geomecánicas de cada labor y "
              "recomienda un tipo de sostenimiento por tramo. Trae las ediciones de cada método, los resultados y los avisos.",
        "en": "This document classifies underground section tramos with the geomechanical table of each excavation and "
              "recommends a support type for each tramo. It lists the edition of each method, the results and the warnings.",
    },
    "s2": {"es": "Métodos y ediciones", "en": "Methods and editions"},
    "s3": {"es": "Tablas geomecánicas por labor", "en": "Geomechanical tables by excavation"},
    "s4": {"es": "Resultados por tramo", "en": "Results by tramo"},
    "s5": {"es": "Resumen", "en": "Summary"},
    "s6": {"es": "Mapas", "en": "Maps"},
    "s7": {"es": "Avisos", "en": "Warnings"},
    "s8": {"es": "Limitaciones", "en": "Limitations"},
    "s8_text": {
        "es": "Este documento no reemplaza el estudio geomecánico firmado. El análisis de cuñas y los modelos "
              "numéricos están fuera de su alcance. Los resultados dependen de las tablas y de los datos de entrada.",
        "en": "This document does not replace the signed geomechanical study. Wedge analysis and numerical models "
              "are outside its scope. The results depend on the tables and on the input data.",
    },
    "h_method": {"es": "Método", "en": "Method"},
    "h_verification": {"es": "Verificación", "en": "Verification"},
    "h_source": {"es": "Fuente", "en": "Source"},
    "cap_methods": {"es": "Métodos usados y su verificación", "en": "Methods used and their verification"},
    "span": {"es": "luz", "en": "span"},
    "h_class": {"es": "Clase", "en": "Class"},
    "h_range": {"es": "Rango o celda", "en": "Range or cell"},
    "h_support": {"es": "Sostenimiento", "en": "Support"},
    "h_description": {"es": "Elementos", "en": "Elements"},
    "h_labor": {"es": "Labor", "en": "Labor"},
    "h_count": {"es": "Tramos", "en": "Tramos"},
    "h_warning": {"es": "Aviso", "en": "Warning"},
    "cap_classes": {"es": "Clases y sostenimiento", "en": "Classes and support"},
    "cap_catalog": {"es": "Catálogo de sostenimiento", "en": "Support catalog"},
    "cap_results": {"es": "Resultados de la clasificación", "en": "Classification results"},
    "cap_by_class": {"es": "Tramos por labor y clase", "en": "Tramos by excavation and class"},
    "cap_by_support": {"es": "Tramos por sostenimiento", "en": "Tramos by support"},
    "cap_totals": {"es": "Totales", "en": "Totals"},
    "total": {"es": "Total de tramos", "en": "Total tramos"},
    "classified": {"es": "Clasificados", "en": "Classified"},
    "unclassified": {"es": "Sin clasificar", "en": "Unclassified"},
    "cap_warnings": {"es": "Avisos y cantidad de tramos que los tienen", "en": "Warnings and number of tramos that have them"},
    "no_warnings": {"es": "Sin avisos.", "en": "No warnings."},
    "fig_cartilla": {"es": "Cartilla", "en": "Chart"},
    "fig_hist": {"es": "Tramos por clase", "en": "Tramos by class"},
    "fig_profile": {"es": "Perfil por progresiva", "en": "Profile by chainage"},
    "fig_plan": {"es": "Planta", "en": "Plan view"},
    "plan_note": {
        "es": "El informe nunca muestra códigos de identificación (labor_codigo, zona_nivel, codigo_mina, "
              "evaluador_codigo, observaciones). El mapa en planta muestra este/norte en sus ejes como escala.",
        "en": "The report never shows identification codes (labor_codigo, zona_nivel, codigo_mina, "
              "evaluador_codigo, observaciones). The plan map shows east/north on its axes as its scale.",
    },
    "no_figures": {"es": "figuras no disponibles: instala rockmasspy[viz]", "en": "figures not available: install rockmasspy[viz]"},
    "no_maps": {"es": "Ningún tramo trae progresivas ni coordenadas: no hay mapas.",
                "en": "No tramo has chainage or coordinates: there are no maps."},
    "to_complete": {"es": "A completar por el ingeniero", "en": "To be completed by the engineer"},
    "version": {"es": "RockMassPy versión", "en": "RockMassPy version"},
    "date": {"es": "Fecha", "en": "Date"},
    "user_defined": {"es": "correlación definida por el usuario", "en": "user-defined correlation"},
    # --- Anexo 39 B (DS 024-2016-EM) ---
    "a_subtitle": {"es": "Estructura del Anexo 39 B, DS 024-2016-EM (Perú)",
                   "en": "Structure of Annex 39 B, DS 024-2016-EM (Peru)"},
    "a_s1": {"es": "Introducción", "en": "Introduction"},
    "a_s2": {"es": "Caracterización geomecánica del macizo rocoso", "en": "Geomechanical characterization of the rock mass"},
    "a_s3": {"es": "Condiciones geomecánicas actuales de la labor", "en": "Current geomechanical conditions of the excavation"},
    "a_s4": {"es": "Evaluación de estabilidad", "en": "Stability assessment"},
    "a_s41": {"es": "Cálculo empírico", "en": "Empirical design"},
    "a_s42": {"es": "Análisis cinemático de cuñas", "en": "Kinematic wedge analysis"},
    "a_s43": {"es": "Modelamiento numérico", "en": "Numerical modelling"},
    "a_s431": {"es": "Recomendación de excavación o explotación", "en": "Excavation or mining recommendation"},
    "a_s432": {"es": "Recomendación de reforzamiento o sostenimiento", "en": "Reinforcement or support recommendation"},
    "a_s5": {"es": "Conclusiones y recomendaciones", "en": "Conclusions and recommendations"},
    "a_s6": {"es": "Anexos", "en": "Appendices"},
    "a_summary": {"es": "Memoria resumen de parámetros de entrada", "en": "Summary of input parameters"},
    "g1": {"es": "Describe la unidad, la labor evaluada y el objetivo del estudio.",
           "en": "Describe the unit, the excavation assessed and the aim of the study."},
    "g42": {"es": "Incluye aquí el análisis de cuñas con las familias de discontinuidades; la librería no lo calcula.",
            "en": "Add the wedge analysis with the discontinuity sets here; the library does not compute it."},
    "g43": {"es": "Incluye aquí el modelo numérico y sus resultados; la librería no lo calcula.",
            "en": "Add the numerical model and its results here; the library does not compute it."},
    "g431": {"es": "Indica cómo conviene excavar o explotar según la evaluación.",
             "en": "State how the excavation or mining should proceed according to the assessment."},
    "g432": {"es": "Indica el refuerzo o sostenimiento que decide el ingeniero, tomando la tabla como punto de partida.",
             "en": "State the reinforcement or support the engineer decides on, taking the table as a starting point."},
    "g5": {"es": "Resume las conclusiones y las recomendaciones del ingeniero responsable.",
           "en": "Summarize the conclusions and recommendations of the responsible engineer."},
    "g6": {"es": "Adjunta planos, registros de campo y otros documentos de respaldo.",
           "en": "Attach drawings, field records and other supporting documents."},
    "cap_tramos": {"es": "Tramos de la labor, con su clase y su sostenimiento", "en": "Tramos of the excavation, with class and support"},
    "cap_q_params": {"es": "Parámetros del Q usados", "en": "Q parameters used"},
    "cap_corr": {"es": "Correlaciones propias del sitio", "en": "Site-specific correlations"},
    "h_name": {"es": "Nombre", "en": "Name"},
    "h_from": {"es": "Desde", "en": "From"},
    "h_to": {"es": "Hacia", "en": "To"},
    "h_form": {"es": "Forma", "en": "Form"},
    "h_valid_min": {"es": "Válido desde", "en": "Valid from"},
    "h_valid_max": {"es": "Válido hasta", "en": "Valid to"},
    "s5_qchart": {"es": "Carta de sostenimiento Q (referencia)", "en": "Q support chart (reference)"},
    "qchart_text": {
        "es": "Esta sección es solo una referencia: lee la carta de sostenimiento del sistema Q del NGI{edition} con el Q "
              "y la luz de cada tramo y el ESR de su labor, en el techo. Las tablas propias de la labor mandan; "
              "la carta no cambia ninguna clase ni sostenimiento. La carta está digitalizada por RockMassPy, así que "
              "su lectura cerca de una frontera puede diferir de la lámina impresa.",
        "en": "This section is a reference only: it reads the NGI Q-system support chart{edition} with the Q and the "
              "span of each tramo and the ESR of its excavation, for the roof. The own tables of the excavation govern; "
              "the chart does not change any class or support. The chart is digitized by RockMassPy, so a reading near "
              "a boundary may differ from the printed chart.",
    },
    "qchart_esr_note": {
        "es": "La longitud de perno de la carta (columnas q_carta_longitud_*) está dada para ESR = 1. Con otro ESR, "
              "compárala con la fórmula de Barton et al. (1980) y con tu criterio; es uno de los valores por confirmar.",
        "en": "The chart bolt length (q_carta_longitud_* columns) is given for ESR = 1. With another ESR, compare it "
              "with the Barton et al. (1980) formula and your own judgement; it is one of the values still to be confirmed.",
    },
    "qchart_none": {"es": "Ningún tramo obtuvo referencia de la carta Q; revisa los avisos de la carta en la sección 7.",
                    "en": "No section got a Q chart reference; see the Q chart warnings in section 7."},
    "cap_esr": {"es": "ESR por labor", "en": "ESR by excavation"},
    "cap_crosstab": {"es": "Tabla cruzada: sostenimiento propio y categoría Q",
                     "en": "Cross-table: own support and Q category"},
    "fig_qchart": {"es": "Carta de sostenimiento Q con los tramos", "en": "Q support chart with the tramos"},
    "cap_qlegend": {"es": "Categorías de la carta Q", "en": "Q chart categories"},
    "cap_qwarnings": {"es": "Avisos de la carta Q", "en": "Q chart warnings"},
    "h_esr_cat": {"es": "Categoría ESR", "en": "ESR category"},
    "h_esr": {"es": "ESR usado", "en": "ESR used"},
    "h_qcat": {"es": "Categoría", "en": "Category"},
    "h_label": {"es": "Rótulo", "en": "Label"},
    "h_shotcrete": {"es": "Shotcrete (mm)", "en": "Shotcrete (mm)"},
    "h_energy": {"es": "Energía Sfr (J)", "en": "Sfr energy (J)"},
    "h_rrs": {"es": "RRS", "en": "RRS"},
    # --- Diseño de tajeos (Mathews, gráfico de Potvin) ---
    "stope_title": {"es": "Diseño empírico de tajeos", "en": "Empirical stope design"},
    "st_s1": {"es": "Alcance", "en": "Scope"},
    "st_s2": {"es": "Métodos y ediciones", "en": "Methods and editions"},
    "st_s3": {"es": "Resultados", "en": "Results"},
    "st_s4": {"es": "Avisos", "en": "Warnings"},
    "st_s5": {"es": "Nota", "en": "Note"},
    "st_scope": {
        "es": "Este documento lee la estabilidad de caras de tajeo con el gráfico modificado de Potvin (1988), cuyas "
              "fronteras están digitalizadas por RockMassPy. Es un método empírico: la lectura cerca de una frontera "
              "puede diferir de la lámina impresa, y el ingeniero decide.",
        "en": "This document reads the stability of stope faces on the modified stability graph of Potvin (1988), whose "
              "boundaries are digitized by RockMassPy. It is an empirical method: a reading near a boundary may differ "
              "from the printed graph, and the engineer decides.",
    },
    "cap_surfaces": {"es": "Caras evaluadas", "en": "Faces assessed"},
    "cap_zones": {"es": "Caras por zona del gráfico", "en": "Faces by graph zone"},
    "fig_stability": {"es": "Gráfico de estabilidad con las caras", "en": "Stability graph with the faces"},
    "h_mode": {"es": "Modo", "en": "Mode"},
    "h_zone": {"es": "Zona", "en": "Zone"},
    "h_faces": {"es": "Caras", "en": "Faces"},
    "cap_st_warnings": {"es": "Avisos y cantidad de caras que los tienen", "en": "Warnings and number of faces that have them"},
    "zone_1": {"es": "estable", "en": "stable"},
    "zone_2": {"es": "transición", "en": "transition"},
    "zone_3": {"es": "hundimiento", "en": "caved"},
    "unknown_method": {"es": "sin información de verificación", "en": "no verification information"},
    # --- Informe de verificación normativa ---
    "verif_title": {"es": "Verificación normativa", "en": "Regulatory verification"},
    "vr_s1": {"es": "Alcance", "en": "Scope"},
    "vr_s2": {"es": "Perfil", "en": "Profile"},
    "vr_s3": {"es": "Resultados", "en": "Results"},
    "vr_s4": {"es": "No revisado por falta de datos", "en": "Not checked for lack of data"},
    "vr_s5": {"es": "No verificable por la librería", "en": "Not verifiable by the library"},
    "vr_s6": {"es": "Nota", "en": "Note"},
    "vr_scope": {
        "es": "Este documento revisa los datos entregados a RockMassPy contra los requisitos del perfil normativo "
              "indicado, vigentes en la fecha de verificación. Distingue lo que es ley (reglamento) de lo que es guía "
              "(recomendación) y lista, aparte, lo que la librería no puede verificar. No reemplaza el estudio "
              "firmado por ingenieros colegiados ni la decisión del ingeniero.",
        "en": "This document checks the data given to RockMassPy against the requirements of the stated regulatory "
              "profile in force on the verification date. It tells law (regulation) from guide (recommendation) and "
              "lists apart what the library cannot verify. It does not replace the study signed by chartered "
              "engineers or the engineer's decision.",
    },
    "cap_profile": {"es": "Perfil normativo", "en": "Regulatory profile"},
    "cap_sources": {"es": "Fuentes", "en": "Sources"},
    "cap_esr_profile": {"es": "ESR por labor del perfil", "en": "Profile ESR by excavation"},
    "cap_status_counts": {"es": "Hallazgos por estado", "en": "Findings by status"},
    "cap_findings": {"es": "Hallazgos revisados", "en": "Findings reviewed"},
    "cap_not_checked": {"es": "Requisitos sin datos para revisarlos", "en": "Requirements without data to check them"},
    "cap_not_verifiable": {"es": "Requisitos que la librería no verifica", "en": "Requirements the library does not verify"},
    "st_complies": {"es": "cumple", "en": "complies"},
    "st_does_not_comply": {"es": "no cumple", "en": "does not comply"},
    "st_attention": {"es": "atención", "en": "attention"},
    "st_note": {"es": "nota", "en": "note"},
    "st_not_checked": {"es": "no revisado", "en": "not checked"},
    "st_not_verifiable": {"es": "no verificable por la librería", "en": "not verifiable by the library"},
    "force_law": {"es": "ley", "en": "law"},
    "force_guide": {"es": "guía", "en": "guide"},
    "h_field": {"es": "Campo", "en": "Field"},
    "h_value": {"es": "Valor", "en": "Value"},
    "h_id": {"es": "Id del perfil", "en": "Profile id"},
    "h_jurisdiction": {"es": "Jurisdicción", "en": "Jurisdiction"},
    "h_instruments": {"es": "Instrumentos", "en": "Instruments"},
    "h_as_of": {"es": "Fecha de verificación", "en": "Verification date"},
    "h_title": {"es": "Título", "en": "Title"},
    "h_force": {"es": "Fuerza", "en": "Force"},
    "h_status": {"es": "Estado", "en": "Status"},
    "h_article": {"es": "Artículo", "en": "Article"},
    "h_page": {"es": "Página", "en": "Page"},
    "h_mark": {"es": "Marca", "en": "Mark"},
    "h_requirement": {"es": "Requisito", "en": "Requirement"},
    "h_requirements": {"es": "Requisitos", "en": "Requirements"},
    "none_items": {"es": "Ninguno.", "en": "None."},
    "h_detail": {"es": "Detalle", "en": "Detail"},
    "h_missing": {"es": "Dato que falta", "en": "Missing data"},
    # --- Informe de taludes (cinemática, SMR, Q-slope) ---
    "slope_title": {"es": "Estabilidad de taludes en roca", "en": "Rock slope stability"},
    "slope_title_le": {"es": "Estabilidad de taludes", "en": "Slope stability"},  # solo equilibrio límite
    "sl_s1": {"es": "Alcance", "en": "Scope"},
    "sl_s2": {"es": "Métodos y ediciones", "en": "Methods and editions"},
    "sl_s3": {"es": "Resultados", "en": "Results"},
    "sl_s4": {"es": "Avisos", "en": "Warnings"},
    "sl_s5": {"es": "Nota", "en": "Note"},
    "sl_scope": {
        "es": "Este documento reúne el análisis cinemático de Markland (deslizamiento planar, en cuña y volteo), el SMR "
              "de Romana y el Q-slope de cada talud y, si se dan bloques, su factor de seguridad (FS) por equilibrio "
              "límite (planar, cuña y volteo), su análisis probabilístico y el ancho de berma. La cinemática dice si el "
              "movimiento es posible por geometría: es factibilidad, no un factor de seguridad ni una probabilidad. El SMR "
              "y el Q-slope son métodos empíricos. El FS y la probabilidad "
              "de falla (PoF) se informan sin juzgar su aceptación: los criterios de aceptación llegan en la etapa 3D "
              "de la librería, y el ingeniero decide.",
        "en": "This document gathers Markland's kinematic analysis (planar sliding, wedge sliding and toppling), Romana's "
              "SMR and the Q-slope of each slope and, when blocks are given, their limit-equilibrium factor of safety "
              "(FS) (planar, wedge and toppling), their probabilistic analysis and the berm width. Kinematics says "
              "whether movement is geometrically possible: it is feasibility, not a factor of safety or a probability. "
              "SMR and Q-slope are empirical methods. The FS and the "
              "probability of failure (PoF) are reported without judging their acceptance: acceptance criteria arrive "
              "in stage 3D of the library, and the engineer decides.",
    },
    # --- Bloques (3B) ---
    "cap_blocks": {"es": "Bloques evaluados", "en": "Blocks assessed"},
    "cap_prob": {"es": "Análisis probabilístico", "en": "Probabilistic analysis"},
    "cap_back": {"es": "Retroanálisis (FS = 1)", "en": "Back analysis (FS = 1)"},
    "cap_topple": {"es": "Volteo, bloque {n}: fuerzas por bloque", "en": "Toppling, block {n}: forces per block"},
    "cap_berms": {"es": "Bermas", "en": "Berms"},
    "cap_bl_warnings": {"es": "Avisos y cantidad de bloques que los tienen",
                        "en": "Warnings and number of blocks that have them"},
    "h_blocks": {"es": "Bloques", "en": "Blocks"},
    "h_model": {"es": "Modelo", "en": "Model"},
    "h_block_mode": {"es": "Modo", "en": "Mode"},
    "h_fs": {"es": "FS", "en": "FS"},
    "h_fs_le1": {"es": "FS ≤ 1", "en": "FS ≤ 1"},
    "h_sampling": {"es": "Muestreo", "en": "Sampling"},
    "h_valid": {"es": "Válidas/n", "en": "Valid/n"},
    "h_seed": {"es": "Semilla", "en": "Seed"},
    "h_mean": {"es": "Media", "en": "Mean"},
    "h_sd": {"es": "Desviación", "en": "Std. dev."},
    "h_min": {"es": "Mínimo", "en": "Minimum"},
    "h_max": {"es": "Máximo", "en": "Maximum"},
    "h_pof": {"es": "PoF (%)", "en": "PoF (%)"},
    "h_beta_n": {"es": "β", "en": "β"},
    "h_beta_ln": {"es": "β_LN", "en": "β_LN"},
    "h_phi0": {"es": "φ con c = 0 (°)", "en": "φ with c = 0 (°)"},
    "h_bench_h": {"es": "Altura de banco (m)", "en": "Bench height (m)"},
    "h_berm_w": {"es": "Berma de diseño (m)", "en": "Design berm (m)"},
    "h_ritchie": {"es": "Ritchie (m)", "en": "Ritchie (m)"},
    "h_required": {"es": "Requerido (m)", "en": "Required (m)"},
    "h_ira": {"es": "Interrampa (°)", "en": "Inter-ramp (°)"},
    "h_narrower": {"es": "Más angosta que el requerido", "en": "Narrower than required"},
    "h_berm_rel": {"es": "Confiabilidad (%)", "en": "Reliability (%)"},
    "h_state": {"es": "Estado", "en": "State"},
    "fig_fs_hist": {"es": "Histograma del FS, bloque {n}", "en": "FS histogram, block {n}"},
    "fig_fs_cdf": {"es": "Curva de PoF, bloque {n}", "en": "PoF curve, block {n}"},
    "model_planar": {"es": "planar", "en": "planar"},
    "model_wedge": {"es": "cuña", "en": "wedge"},
    "model_toppling": {"es": "volteo", "en": "toppling"},
    "model_berm": {"es": "berma", "en": "berm"},
    "bmode_planar": {"es": "planar", "en": "planar"},
    "bmode_dos_planos": {"es": "dos planos", "en": "two planes"},
    "bmode_plano_1": {"es": "plano 1", "en": "plane 1"},
    "bmode_plano_2": {"es": "plano 2", "en": "plane 2"},
    "bmode_despegue": {"es": "despegue", "en": "lift-off"},
    "bmode_no_formado": {"es": "no formado", "en": "not formed"},
    "bmode_volteo": {"es": "volteo", "en": "toppling"},
    "topple_stable": {"es": "estable", "en": "stable"},
    "topple_toppling": {"es": "vuelca", "en": "toppling"},
    "topple_sliding": {"es": "desliza", "en": "sliding"},
    "att_fs_below_1": {"es": "FS ≤ 1", "en": "FS ≤ 1"},
    "att_block_warnings": {"es": "avisos", "en": "warnings"},
    "bl_attention": {"es": "Bloques que piden atención: {n} de {m}. Motivos (bloques): {why}.",
                     "en": "Blocks that need attention: {n} of {m}. Reasons (blocks): {why}."},
    "cap_slopes": {"es": "Taludes evaluados (k de n: casos críticos)", "en": "Slopes assessed (k of n: critical cases)"},
    "cap_families": {"es": "Familias de discontinuidades (Fisher)", "en": "Discontinuity families (Fisher)"},
    "cap_smr": {
        "es": "SMR por caso. D = gobierna el SMR discreto, C = gobierna el continuo. Los factores F se dan como discreto / continuo.",
        "en": "SMR per case. D = governs the discrete SMR, C = governs the continuous one. F factors are given as discrete / continuous.",
    },
    "cap_qslope": {"es": "Q-slope y ángulo de talud sin sostenimiento", "en": "Q-slope and unsupported slope angle"},
    "cap_sl_warnings": {"es": "Avisos y cantidad de taludes que los tienen", "en": "Warnings and number of slopes that have them"},
    "fig_stereo_density": {"es": "Red estereográfica con densidad de polos, talud {n}",
                           "en": "Stereonet with pole density, slope {n}"},
    "fig_stereo_mode": {"es": "Red estereográfica, {mode}, talud {n}", "en": "Stereonet, {mode}, slope {n}"},
    "h_face": {"es": "Cara (buz./dir.)", "en": "Face (dip/dir.)"},
    "h_face_dip": {"es": "Buz. cara (°)", "en": "Face dip (°)"},
    "h_case": {"es": "Caso", "en": "Case"},
    "h_mode_smr": {"es": "Modo", "en": "Mode"},
    "h_beta": {"es": "β (°)", "en": "β (°)"},
    "h_steeper": {"es": "Cara más empinada que β", "en": "Face steeper than β"},
    "h_slopes": {"es": "Taludes", "en": "Slopes"},
    "h_governing": {"es": "Gobierna", "en": "Governs"},
    "h_family": {"es": "Familia", "en": "Family"},
    "h_mean_orientation": {"es": "Orientación media (buz./dir.)", "en": "Mean orientation (dip/dir.)"},
    "h_notes": {"es": "Notas", "en": "Notes"},
    "sl_yes": {"es": "sí", "en": "yes"},
    "sl_no": {"es": "no", "en": "no"},
    "h_oblique": {"es": "Volteo directo oblicuo", "en": "Oblique direct toppling"},
    "sl_attention": {"es": "Taludes que piden atención: {n} de {m}. Motivos (taludes): {why}.",
                     "en": "Slopes that need attention: {n} of {m}. Reasons (slopes): {why}."},
    "att_planar": {"es": "deslizamiento planar", "en": "planar sliding"},
    "att_wedge_primary": {"es": "cuña primaria", "en": "primary wedge"},
    "att_wedge_secondary": {"es": "cuña secundaria", "en": "secondary wedge"},
    "att_flexural_toppling": {"es": "volteo flexural", "en": "flexural toppling"},
    "att_direct_toppling": {"es": "volteo directo", "en": "direct toppling"},
    "att_direct_toppling_oblique": {"es": "volteo directo oblicuo", "en": "oblique direct toppling"},
    "att_smr": {"es": "SMR clase IV o V", "en": "SMR class IV or V"},
    "att_qslope": {"es": "cara más empinada que β", "en": "face steeper than β"},
    "att_warnings": {"es": "avisos", "en": "warnings"},
    # --- Equilibrio límite (3C) ---
    "sl_no_slopes": {"es": "No se evaluaron taludes por cinemática, SMR ni Q-slope.",
                     "en": "No slopes were assessed by kinematics, SMR or Q-slope."},
    "le_scope": {
        "es": "Además reúne el equilibrio límite 2D por tajadas (Ordinario, Bishop, Janbu, Spencer y "
              "Morgenstern-Price/GLE) sobre la superficie crítica de cada análisis y, si se da un registro, el "
              "coeficiente de fluencia ky y el desplazamiento de Newmark de bloque rígido. El FS y el desplazamiento "
              "se informan sin juzgar su aceptación.",
        "en": "It also gathers 2D limit equilibrium by slices (Ordinary, Bishop, Janbu, Spencer and "
              "Morgenstern-Price/GLE) on the critical surface of each analysis and, when a record is given, the "
              "yield coefficient ky and the rigid-block Newmark displacement. The FS and the displacement are "
              "reported without judging their acceptance.",
    },
    "le_scope_only": {
        "es": "Este documento reúne el equilibrio límite 2D por tajadas (Ordinario, Bishop, Janbu, Spencer y "
              "Morgenstern-Price/GLE) sobre la superficie crítica de cada análisis y, si se da un registro, el "
              "coeficiente de fluencia ky y el desplazamiento de Newmark de bloque rígido. El FS y el desplazamiento "
              "se informan sin juzgar su aceptación: los criterios de aceptación llegan en la etapa 3D de la "
              "librería, y el ingeniero decide.",
        "en": "This document gathers 2D limit equilibrium by slices (Ordinary, Bishop, Janbu, Spencer and "
              "Morgenstern-Price/GLE) on the critical surface of each analysis and, when a record is given, the "
              "yield coefficient ky and the rigid-block Newmark displacement. The FS and the displacement are "
              "reported without judging their acceptance: acceptance criteria come in stage 3D of the library, and "
              "the engineer decides.",
    },
    "cap_le": {"es": "Equilibrio límite", "en": "Limit equilibrium"},
    "h_fs_static": {"es": "FS estático", "en": "Static FS"},
    "cap_le_surface": {"es": "Superficie crítica por análisis", "en": "Critical surface per analysis"},
    "cap_le_warnings": {"es": "Avisos y cantidad de análisis de equilibrio límite que los tienen",
                        "en": "Warnings and number of limit equilibrium analyses that have them"},
    "h_analyses": {"es": "Análisis", "en": "Analyses"},
    "h_le_surface": {"es": "Superficie", "en": "Surface"},
    "h_le_method": {"es": "Método", "en": "Method"},
    "h_lambda": {"es": "λ", "en": "λ"},
    "h_ky": {"es": "ky", "en": "ky"},
    "h_newmark": {"es": "Newmark (m)", "en": "Newmark (m)"},
    "h_points": {"es": "Puntos (x y)", "en": "Points (x y)"},
    "h_evaluated": {"es": "Evaluadas", "en": "Evaluated"},
    "h_discarded": {"es": "Descartadas", "en": "Discarded"},
    "le_surf_circular": {"es": "circular", "en": "circular"},
    "le_surf_block": {"es": "búsqueda de bloque", "en": "block search"},
    "le_surf_given": {"es": "dada", "en": "given"},
    "le_surf_sarma": {"es": "Sarma (cuñas no verticales)", "en": "Sarma (non-vertical wedges)"},
    "fig_le_section": {"es": "Sección de equilibrio límite, análisis {n}", "en": "Limit equilibrium section, analysis {n}"},
    "fig_newmark": {"es": "Desplazamiento de Newmark, análisis {n}", "en": "Newmark displacement, analysis {n}"},
    "att_le_fs_below_1": {"es": "FS ≤ 1", "en": "FS ≤ 1"},
    "att_le_warnings": {"es": "avisos", "en": "warnings"},
    "le_attention": {"es": "Análisis de equilibrio límite que piden atención: {n} de {m}. Motivos (análisis): {why}.",
                     "en": "Limit equilibrium analyses that need attention: {n} of {m}. Reasons (analyses): {why}."},
    "smr_class_1": {"es": "muy buena", "en": "very good"},
    "smr_class_2": {"es": "buena", "en": "good"},
    "smr_class_3": {"es": "normal", "en": "fair"},
    "smr_class_4": {"es": "mala", "en": "bad"},
    "smr_class_5": {"es": "muy mala", "en": "very bad"},
    "smr_mode_planar": {"es": "planar", "en": "planar"},
    "smr_mode_toppling": {"es": "volteo", "en": "toppling"},
    "smr_mode_wedge": {"es": "cuña", "en": "wedge"},
    # --- Informe de taludes completo con criterios de aceptación (3D) ---
    "sx_1": {"es": "Resumen ejecutivo", "en": "Executive summary"},
    "sx_2": {"es": "Alcance y criterios", "en": "Scope and criteria"},
    "sx_3": {"es": "Cinemática, SMR y Q-slope", "en": "Kinematics, SMR and Q-slope"},
    "sx_4": {"es": "Bloques", "en": "Blocks"},
    "sx_5": {"es": "Equilibrio límite y Sarma", "en": "Limit equilibrium and Sarma"},
    "sx_6": {"es": "Verificación de criterios", "en": "Criteria check"},
    "sx_7": {"es": "Normativa", "en": "Regulations"},
    "sx_8": {"es": "Avisos y notas", "en": "Warnings and notes"},
    "sx_9": {"es": "Métodos y anexos", "en": "Methods and appendices"},
    "crit_scope": {
        "es": "Este documento reúne los resultados de taludes de la librería (cinemática, SMR y Q-slope; bloques "
              "planares, en cuña y de volteo con su análisis probabilístico y la berma; equilibrio límite 2D, Sarma, "
              "ky y Newmark) y compara cada uno con el criterio de aceptación que eligió el usuario. Cada chequeo "
              "dice «cumple», «no cumple» o «no verificable», con el criterio, su fuente, su fuerza (ley o guía) y "
              "su marca. La librería recomienda y el ingeniero decide.",
        "en": "This document gathers the library's slope results (kinematics, SMR and Q-slope; planar, wedge and "
              "toppling blocks with their probabilistic analysis and the berm; 2D limit equilibrium, Sarma, ky and "
              "Newmark) and compares each one with the acceptance criterion chosen by the user. Each check says "
              "\"meets\", \"fails\" or \"not verifiable\", with the criterion, its source, its force (law or "
              "guide) and its mark. The library recommends and the engineer decides.",
    },
    "crit_profile_only": {
        "es": "No se eligió un perfil de criterios de aceptación: solo se revisa la normativa de la sección 7.",
        "en": "No acceptance criteria profile was chosen: only the regulations of section 7 are checked.",
    },
    "cap_crit_summary": {"es": "Resumen por objeto: resultados y estado frente a cada criterio",
                         "en": "Summary by object: results and status against each criterion"},
    "cap_crit_profile": {"es": "Perfil de criterios de aceptación", "en": "Acceptance criteria profile"},
    "cap_crit_checks": {"es": "Chequeos de criterios, uno por fila", "en": "Criteria checks, one per row"},
    "cap_crit_normative": {"es": "Normativa: requisitos del perfil normativo", "en": "Regulations: requirements of the "
                           "regulatory profile"},
    "crit_counts": {"es": "Chequeos: {n}. Cumple: {meets}; no cumple: {fails}; no verificable: {not_verifiable}.",
                    "en": "Checks: {n}. Meets: {meets}; fails: {fails}; not verifiable: {not_verifiable}."},
    "crit_attention": {"es": "Piden atención los «no cumple», por regla: {why}.",
                       "en": "The \"fails\" need attention, by rule: {why}."},
    "crit_not_verifiable": {"es": "Chequeos no verificables: {n}. Son nota: la razón de cada uno está en la sección 6.",
                            "en": "Checks not verifiable: {n}. They are notes: the reason for each one is in "
                                  "section 6."},
    "crit_normative_fails": {"es": "La normativa de la sección 7 tiene requisitos que no se cumplen: {n}.",
                             "en": "The regulations of section 7 have requirements that are not met: {n}."},
    "crit_no_profile": {"es": "No se pasó un perfil normativo.", "en": "No regulatory profile was given."},
    "crit_no_blocks": {"es": "No se evaluaron bloques.", "en": "No blocks were assessed."},
    "crit_no_le": {"es": "No se evaluaron análisis de equilibrio límite.",
                   "en": "No limit equilibrium analyses were assessed."},
    "crit_mark_V2": {
        "es": "Marca V2: los valores de este perfil vienen de una fuente secundaria que reproduce la tabla original; "
              "el original no se leyó. Conviene confirmarlos con la fuente antes de usarlos en un diseño.",
        "en": "Mark V2: the values of this profile come from a secondary source that reproduces the original table; "
              "the original was not read. Confirm them against the source before using them in a design.",
    },
    "crit_mark_user": {
        "es": "Marca «user»: los criterios vienen de la tabla propia del usuario. La librería no verificó su fuente; "
              "su respaldo es responsabilidad de quien los dio.",
        "en": "Mark \"user\": the criteria come from the user's own table. The library did not verify their source; "
              "backing them is the responsibility of whoever gave them.",
    },
    "h_object": {"es": "Objeto", "en": "Object"},
    "h_id_object": {"es": "Id", "en": "Id"},
    "h_scale": {"es": "Escala", "en": "Scale"},
    "h_consequence": {"es": "Consecuencia", "en": "Consequence"},
    "h_fs_pseudo": {"es": "FS seudoestático", "en": "Pseudo-static FS"},
    "h_criterion": {"es": "Criterio", "en": "Criterion"},
    "h_rule": {"es": "Regla", "en": "Rule"},
    "h_crit_required": {"es": "Requerido", "en": "Required"},
    "h_obtained": {"es": "Obtenido", "en": "Obtained"},
    "h_range_used": {"es": "Rango usado", "en": "Range used"},
    "h_reason": {"es": "Razón", "en": "Reason"},
    "years": {"es": "años", "en": "years"},
    "h_range_policy": {"es": "Política de rangos", "en": "Range policy"},
    "cr_meets": {"es": "cumple", "en": "meets"},
    "cr_fails": {"es": "no cumple", "en": "fails"},
    "cr_not_verifiable": {"es": "no verificable", "en": "not verifiable"},
    "kind_block": {"es": "Bloque", "en": "Block"},
    "kind_berm": {"es": "Berma", "en": "Berm"},
    "kind_le": {"es": "Equilibrio límite", "en": "Limit equilibrium"},
    "kind_le_set": {"es": "Conjunto de análisis", "en": "Set of analyses"},
    "rule_slope_fs_static": {"es": "FS estático mínimo", "en": "Minimum static FS"},
    "rule_slope_fs_pseudostatic": {"es": "FS seudoestático mínimo", "en": "Minimum pseudo-static FS"},
    "rule_slope_pof": {"es": "PoF máxima", "en": "Maximum PoF"},
    "rule_berm_reliability": {"es": "Confiabilidad de berma mínima", "en": "Minimum berm reliability"},
    "rule_deformation_required": {"es": "Análisis de deformación", "en": "Deformation analysis"},
    "rule_pseudostatic_analysis_present": {"es": "Análisis seudoestático global", "en": "Overall pseudo-static "
                                           "analysis"},
    "policy_conservative": {"es": "conservadora: extremo alto del rango para un mínimo y bajo para un máximo",
                            "en": "conservative: upper end of the range for a minimum and lower end for a maximum"},
    "policy_upper": {"es": "extremo alto de cada rango", "en": "upper end of each range"},
    "policy_lower": {"es": "extremo bajo de cada rango", "en": "lower end of each range"},
    # --- histórico de la mina (Fase 4A: datos, auditoría, preparación y nivel 1) ---
    "hist_title": {"es": "Histórico geomecánico y correlaciones del sitio",
                   "en": "Geomechanical history and site correlations"},
    "hist_subtitle": {"es": "Auditoría de ingesta y nivel 1", "en": "Ingestion audit and level 1"},
    "hs_1": {"es": "Datos", "en": "Data"},
    "hs_2": {"es": "Auditoría de ingesta", "en": "Ingestion audit"},
    "hs_3": {"es": "Preparación por nivel", "en": "Readiness by level"},
    "hs_4": {"es": "Nivel 1: correlaciones propias del sitio", "en": "Level 1: site correlations"},
    "hs_5": {"es": "Limitaciones", "en": "Limitations"},
    "hist_scope": {
        "es": "Este informe resume el histórico geomecánico de la mina con conteos: lo que trae cada hoja, lo que la "
              "auditoría encontró, qué nivel del modelo predictivo tiene datos suficientes y las correlaciones propias "
              "del sitio. No nombra el archivo de entrada; los dominios van con códigos (D1, D2…).",
        "en": "This report summarizes the mine's geomechanical history with counts: what each sheet holds, what the "
              "audit found, which level of the predictive model has enough data and the site's own correlations. It "
              "does not name the input file; domains go by codes (D1, D2…).",
    },
    "cap_hist_data": {"es": "Contenido del histórico", "en": "History contents"},
    "h_item": {"es": "Concepto", "en": "Item"},
    "hd_tramos": {"es": "Tramos (hoja Tramos)", "en": "Tramos (sheet Tramos)"},
    "hd_types": {"es": "Tipos de sostenimiento (hoja Tipos_sostenimiento)",
                 "en": "Support types (sheet Tipos_sostenimiento)"},
    "hd_inspections": {"es": "Inspecciones (hoja Desempeno)", "en": "Inspections (sheet Desempeno)"},
    "hd_with_insp": {"es": "Tramos con inspección", "en": "Tramos with inspections"},
    "hd_without_insp": {"es": "Tramos sin inspección (no entran al nivel 3)",
                        "en": "Tramos without inspections (left out of level 3)"},
    "hd_years_eval": {"es": "Años con evaluación (años distintos)", "en": "Years with evaluations (distinct years)"},
    "hd_years_insp": {"es": "Años con inspección (años distintos)", "en": "Years with inspections (distinct years)"},
    "cap_hist_kinds": {"es": "Hallazgos por tipo", "en": "Findings by kind"},
    "h_kind": {"es": "Tipo", "en": "Kind"},
    "h_findings": {"es": "Hallazgos", "en": "Findings"},
    "cap_hist_findings": {"es": "Hallazgos de la auditoría", "en": "Audit findings"},
    "h_sheet": {"es": "Hoja", "en": "Sheet"},
    "h_row": {"es": "Fila", "en": "Row"},
    "h_message": {"es": "Mensaje", "en": "Message"},
    "hist_no_findings": {"es": "La auditoría no encontró hallazgos.", "en": "The audit found nothing."},
    "hist_audit_text": {
        "es": "La auditoría recalcula Q y el RMR89 básico desde sus componentes, busca registros no independientes "
              "(progresivas que se solapan, componentes repetidos en tramos seguidos) y revisa la coherencia entre "
              "hojas. Avisa, nunca bloquea.",
        "en": "The audit recomputes Q and the basic RMR89 from their components, looks for records that are not "
              "independent (overlapping chainages, repeated components in consecutive tramos) and checks the "
              "coherence between sheets. It warns, it never blocks.",
    },
    "hist_readiness_text": {
        "es": "Cada nivel se compara con su mínimo: nivel 1, 30 pares de 5 labores por tipo de par; nivel 2, 10 "
              "tramos de 5 labores por tipo instalado; nivel 3, 10 eventos de la clase menor por parámetro y 3 zonas. "
              "Estos mínimos son una decisión de diseño (heurísticas del spec), no valores publicados; la simulación "
              "de la fase 4C los confirmará o los cambiará. Solo cuentan las filas completas.",
        "en": "Each level is compared with its minimum: level 1, 30 pairs from 5 excavations per pair kind; level 2, 10 "
              "tramos from 5 excavations per installed type; level 3, 10 minority-class events per parameter and 3 zones. "
              "These minimums are a design decision (heuristics of the spec), not published values; the simulation "
              "of phase 4C will confirm or change them. Only complete rows count.",
    },
    "cap_hist_readiness": {"es": "Preparación por nivel", "en": "Readiness by level"},
    "h_level": {"es": "Nivel", "en": "Level"},
    "h_available": {"es": "Disponible", "en": "Available"},
    "h_minimum_dd": {"es": "Mínimo (decisión de diseño)", "en": "Minimum (design decision)"},
    "h_lacking": {"es": "Falta", "en": "Lacking"},
    "h_ready": {"es": "Estado", "en": "Status"},
    "ready_yes": {"es": "listo", "en": "ready"},
    "ready_no": {"es": "no listo", "en": "not ready"},
    "hist_l1_none": {"es": "No se ajustaron correlaciones (en la CLI, con --correlations).",
                     "en": "No correlations were fitted (in the CLI, with --correlations)."},
    "hist_l1_text": {
        "es": "Cada par se ajusta por dominio (D1, D2…, por defecto la litología; Somodi et al. 2021 [V2]) y para "
              "toda la mina. La OLS de Y sobre X con su intervalo de predicción al 95 % es la que predice (Warton et "
              "al. 2006 [V2]); los IC de a y b salen de un bootstrap que remuestrea labores, no filas (Efron y "
              "Tibshirani 1994 [V2]; Roberts et al. 2017 [V2]); Deming solo se calcula con la razón de varianzas de "
              "error (Carroll et al. 2006 [V2]). El bayesiano parte de la correlación global como prior. Estado "
              "«sitio»: 30 pares de 5 labores y el IC de la pendiente dentro de ±25 % de la OLS; «inestable»: cumple "
              "el mínimo, pero el IC es ancho; «no calibrada al sitio»: bajo el mínimo, solo el bayesiano, cerca de "
              "la global. El umbral de ±25 % y la fuerza del prior son decisiones de diseño.",
        "en": "Each pair is fitted by domain (D1, D2…, lithology by default; Somodi et al. 2021 [V2]) and for the "
              "whole mine. The OLS of Y on X with its 95 % prediction interval is the one that predicts (Warton et "
              "al. 2006 [V2]); the CIs of a and b come from a bootstrap that resamples excavations, not rows (Efron and "
              "Tibshirani 1994 [V2]; Roberts et al. 2017 [V2]); Deming is computed only with the error-variance "
              "ratio (Carroll et al. 2006 [V2]). The Bayesian fit starts from the global correlation as prior. Status "
              "\"site\": 30 pairs from 5 excavations and the slope CI within ±25 % of the OLS; \"unstable\": it meets the "
              "minimum but the CI is wide; \"not calibrated to the site\": below the minimum, Bayesian only, close "
              "to the global one. The ±25 % threshold and the prior strength are design decisions.",
    },
    "hist_prior": {
        "es": "Prior: {method} [{mark}], a = {a:.4g}, b = {b:.4g}; desviación a priori de a {sd_a:.3g} y del nivel "
              "{sd_b:.3g} puntos, σ a priori {sigma:.3g} (fuerza del prior: decisión de diseño).",
        "en": "Prior: {method} [{mark}], a = {a:.4g}, b = {b:.4g}; prior SD of a {sd_a:.3g} and of the level "
              "{sd_b:.3g} points, prior σ {sigma:.3g} (prior strength: design decision).",
    },
    "cap_hist_fits": {"es": "Ajustes: {form}", "en": "Fits: {form}"},
    "h_fit": {"es": "Ajuste", "en": "Fit"},
    "h_labors": {"es": "Labores", "en": "Excavations"},
    "h_a_ci": {"es": "a (IC 95 %)", "en": "a (95 % CI)"},
    "h_b_ci": {"es": "b (IC 95 %)", "en": "b (95 % CI)"},
    "fit_mine": {"es": "mina", "en": "mine"},
    "fit_site": {"es": "sitio", "en": "site"},
    "fit_unstable": {"es": "inestable", "en": "unstable"},
    "fit_not_calibrated": {"es": "no calibrada al sitio", "en": "not calibrated to the site"},
    "method_ols": {"es": "OLS", "en": "OLS"},
    "method_bayesian": {"es": "bayesiano", "en": "Bayesian"},
    "hist_deming": {"es": "Deming (mina): a = {a:.4g}, b = {b:.4g}.", "en": "Deming (mine): a = {a:.4g}, b = {b:.4g}."},
    "hist_no_deming": {"es": "Deming (mina): no calculado; {reason}.", "en": "Deming (mine): not computed; {reason}."},
    "hist_not_fitted": {"es": "No ajustado: {reason}.", "en": "Not fitted: {reason}."},
    "cap_hist_warnings": {"es": "Avisos del ajuste y cantidad de ajustes que los tienen",
                          "en": "Fit warnings and number of fits that have them"},
    "h_fits": {"es": "Ajustes", "en": "Fits"},
    "fig_hist_corr": {"es": "Pares del sitio, correlación de la mina e intervalo de predicción: {form}",
                      "en": "Site pairs, mine correlation and prediction interval: {form}"},
    "cap_hist_methods": {"es": "Métodos del nivel 1 y su respaldo", "en": "Level 1 methods and their backing"},
    "hm_ols": {"es": "OLS con intervalo de predicción al 95 %", "en": "OLS with 95 % prediction interval"},
    "hm_boot": {"es": "Bootstrap por labor ({n_boot} réplicas, semilla fija)",
                "en": "Bootstrap by excavation ({n_boot} replicates, fixed seed)"},
    "hm_deming": {"es": "Deming (con la razón de varianzas de error)", "en": "Deming (with the error-variance ratio)"},
    "hm_bayes": {"es": "Bayesiano conjugado normal–gamma inversa con la correlación global como prior",
                 "en": "Conjugate normal–inverse-gamma Bayesian fit with the global correlation as prior"},
    "hm_dd": {"es": "decisión de diseño", "en": "design decision"},
    "h_role": {"es": "Uso", "en": "Use"},
    "hm_role_stat": {"es": "método estadístico", "en": "statistical method"},
    "hm_role_prior": {"es": "prior (correlación global del núcleo)", "en": "prior (global correlation in the core)"},
    "h_research_mark": {"es": "Marca de la investigación", "en": "Research mark"},
    "h_core_verification": {"es": "Verificación en el núcleo", "en": "Verification in the core"},
    "hm_prior_strength": {"es": "fuerza del prior", "en": "prior strength"},
    "hist_limits": {
        "es": "Las correlaciones son del sitio y de su rango observado: fuera de ese rango no valen. Un tramo no es "
              "independiente de sus vecinos de la misma labor; por eso el bootstrap es por labor. El histórico "
              "registra lo que la mina midió y decidió, con sus sesgos de selección y de observador. Los mínimos, "
              "el umbral de estabilidad y la fuerza del prior son decisiones de diseño por confirmar.",
        "en": "The correlations belong to the site and to its observed range: outside that range they do not hold. "
              "A tramo is not independent of its neighbours in the same excavation; that is why the bootstrap is by "
              "excavation. The history records what the mine measured and decided, with its selection and observer "
              "biases. The minimums, the stability threshold and the prior strength are design decisions to be "
              "confirmed.",
    },
    "hist_limits_none": {"es": "Los niveles 2 y 3 no se pidieron (en la CLI, con --practice y --performance).",
                         "en": "Levels 2 and 3 were not requested (in the CLI, with --practice and --performance)."},
    # --- niveles 2 y 3 (Fase 4B y 4C) ---
    "hist_subtitle_full": {"es": "Auditoría de ingesta y niveles 1 a 3", "en": "Ingestion audit and levels 1 to 3"},
    "hs_l2": {"es": "Nivel 2: auditoría de la práctica", "en": "Level 2: support practice audit"},
    "hs_l3": {"es": "Nivel 3: desempeño y recomendación", "en": "Level 3: performance and recommendation"},
    "hs_tripod": {"es": "Lista TRIPOD+AI", "en": "TRIPOD+AI checklist"},
    "hist_limits_l23": {
        "es": "La práctica pasada como etiqueta: el nivel 2 aprende lo que la mina instaló, que depende de la clase "
              "de roca que se evaluó; reproduce las decisiones del pasado, no las óptimas, y por eso describe y no "
              "recomienda. Sesgo de selección: las fallas del nivel 3 dependen del sostenimiento que se eligió (un "
              "tipo pesado se instaló donde el macizo era malo), así que el efecto del sostenimiento queda "
              "confundido con la calidad del macizo; las cotas de signo lo acotan, no lo eliminan. Extrapolación: "
              "fuera del rango de entrenamiento, o lejos de él en distancia de Mahalanobis, el modelo no vale; la "
              "recomendación lo avisa tramo por tramo. Un tramo sin inspecciones no entra al nivel 3: nunca se "
              "asume estable. La validación es interna (otra parte de la misma mina), no externa.",
        "en": "Past practice as the label: level 2 learns what the mine installed, which depends on the rock class "
              "that was assessed; it reproduces past decisions, not optimal ones, and so it describes and does not "
              "recommend. Selection bias: level 3 failures depend on the support that was chosen (a heavy type was "
              "installed where the rock was poor), so the support effect is confounded with rock quality; the sign "
              "bounds limit this, they do not remove it. Extrapolation: outside the training range, or far from it "
              "in Mahalanobis distance, the model does not hold; the recommendation flags it tramo by tramo. A tramo "
              "without inspections is left out of level 3: it is never assumed stable. The validation is internal "
              "(another part of the same mine), not external.",
    },
    "dd": {"es": "decisión de diseño", "en": "design decision"},
    "cap_dd": {"es": "Mínimos y umbrales (todos son decisión de diseño, por confirmar)",
               "en": "Minimums and thresholds (all are design decisions, to be confirmed)"},
    "h_variable": {"es": "Variable", "en": "Variable"},
    "h_coef": {"es": "Coeficiente", "en": "Coefficient"},
    "h_se": {"es": "Error estándar", "en": "Standard error"},
    "h_ci95": {"es": "IC 95 %", "en": "95 % CI"},
    "h_verdict": {"es": "Veredicto", "en": "Verdict"},
    "h_partition": {"es": "Partición", "en": "Partition"},
    "h_rows": {"es": "Filas", "en": "Rows"},
    "h_groups": {"es": "Labores", "en": "Excavations"},
    "h_gain_vs": {"es": "Mejora sobre {ref} (IC 95 %)", "en": "Gain over {ref} (95 % CI)"},
    "h_blockers": {"es": "Motivos para no recomendar", "en": "Reasons not to recommend"},
    "h_installed": {"es": "Instalado", "en": "Installed"},
    "h_most_probable": {"es": "Más probable", "en": "Most probable"},
    "h_conformal_set": {"es": "Conjunto conforme", "en": "Conformal set"},
    "h_sign": {"es": "Restricción de signo", "en": "Sign constraint"},
    "h_bound_active": {"es": "Cota activa", "en": "Bound active"},
    "h_recommended_installed": {"es": "Recomendado \\ instalado", "en": "Recommended \\ installed"},
    "yes": {"es": "sí", "en": "yes"},
    "no": {"es": "no", "en": "no"},
    "none": {"es": "ninguno", "en": "none"},
    "part_labor": {"es": "por labor (k pliegues)", "en": "by excavation (k folds)"},
    "part_zone": {"es": "zona fuera", "en": "zone left out"},
    "part_temporal": {"es": "temporal (último año)", "en": "temporal (last year)"},
    "part_random": {"es": "aleatoria por fila (optimista)", "en": "random by row (optimistic)"},
    "part_skipped": {"es": "omitida: {reason}", "en": "skipped: {reason}"},
    "cap_val_warnings": {"es": "Avisos de la validación", "en": "Validation warnings"},
    "cap_level_warnings": {"es": "Avisos del ajuste", "en": "Fit warnings"},
    # nivel 2
    "l2_text": {
        "es": "Este nivel describe la práctica de la mina, no recomienda: dice qué sostenimiento instala la mina en "
              "cada condición, nunca qué instalar. Es un logit acumulado de odds proporcionales (Bürkner y Vuorre "
              "2019 [V2]) del rango del tipo instalado sobre ln Q, ln De, la vida útil y el tipo de labor, sin "
              "restricciones de signo. Un coeficiente β > 0 empuja a un tipo más pesado. Lo esperado es β(ln Q) < 0 "
              "y β(ln De) > 0: si el IC 95 % excluye el cero con el signo contrario, la práctica es incoherente; si "
              "incluye el cero, «no significativo», nunca «coherente».",
        "en": "This level describes the mine's practice, it does not recommend: it says which support the mine "
              "installs in each condition, never what to install. It is a proportional-odds cumulative logit "
              "(Bürkner and Vuorre 2019 [V2]) of the installed type rank on ln Q, ln De, service life and "
              "excavation type, without sign constraints. A coefficient β > 0 pushes towards a heavier type. The "
              "expected signs are β(ln Q) < 0 and β(ln De) > 0: if the 95 % CI excludes zero with the opposite "
              "sign, the practice is incoherent; if it includes zero, \"not significant\", never \"coherent\".",
    },
    "cap_l2_data": {"es": "Datos del nivel 2", "en": "Level 2 data"},
    "l2_n": {"es": "Tramos usados (Q, luz y ESR > 0, tipo definido)",
             "en": "Tramos used (Q, span and ESR > 0, defined type)"},
    "l2_labors": {"es": "Labores", "en": "Excavations"},
    "l2_types": {"es": "Tipos instalados (del más liviano al más pesado)",
                 "en": "Installed types (lightest to heaviest)"},
    "l2_status": {"es": "Estado", "en": "Status"},
    "l2_missing": {"es": "Tipos bajo el mínimo", "en": "Types below the minimum"},
    "l2_dropped": {"es": "Variables fuera del ajuste (colineales o constantes)",
                   "en": "Variables left out of the fit (collinear or constant)"},
    "l2_reference": {"es": "Tipo de labor de referencia (los tipo_labor=… son contrastes contra él)",
                     "en": "Reference excavation type (the tipo_labor=… terms are contrasts against it)"},
    "l2_ready": {"es": "listo", "en": "ready"},
    "l2_insufficient": {"es": "datos insuficientes", "en": "insufficient data"},
    "cap_l2_coef": {"es": "Coeficientes del logit acumulado (ajuste final) y veredictos de signo",
                    "en": "Cumulative logit coefficients (final fit) and sign verdicts"},
    "verdict_coherent": {"es": "coherente", "en": "coherent"},
    "verdict_not_significant": {"es": "no significativo", "en": "not significant"},
    "verdict_rock": {"es": "práctica incoherente con la calidad del macizo",
                     "en": "practice incoherent with rock quality"},
    "verdict_span": {"es": "práctica incoherente con la luz", "en": "practice incoherent with span"},
    "verdict_not_estimable": {"es": "no estimable", "en": "not estimable"},
    "l2_val_text": {
        "es": "Validación agrupada (Roberts et al. 2017 [V2]) con el kappa ponderado cuadrático (Cohen 1968 [V2]) "
              "contra el clasificador ficticio (la clase más frecuente) y la línea base NGI (el mismo logit con la "
              "categoría de la carta Q como única variable). Los IC de la mejora salen de un bootstrap por labor.",
        "en": "Grouped validation (Roberts et al. 2017 [V2]) with the quadratic weighted kappa (Cohen 1968 [V2]) "
              "against the dummy classifier (the most frequent class) and the NGI baseline (the same logit with the "
              "Q chart category as its only variable). The CIs of the gain come from a bootstrap by excavation.",
    },
    "cap_l2_val": {"es": "Kappa ponderado cuadrático fuera de pliegue por partición",
                   "en": "Out-of-fold quadratic weighted kappa by partition"},
    "l2_beyond_yes": {"es": "La práctica es más predecible que la carta Q y que el ficticio: en las particiones por "
                            "labor y por zona fuera, el IC 95 % de la mejora del kappa queda sobre cero, y la temporal "
                            "no sale peor. Esto no habilita ninguna recomendación: solo dice que la mina sigue un "
                            "criterio propio y consistente.",
                      "en": "The practice is more predictable than the Q chart and the dummy: in the excavation and "
                            "zone-left-out partitions the 95 % CI of the kappa gain is above zero, and the temporal "
                            "one is not worse. This enables no recommendation: it only says the mine follows a "
                            "consistent criterion of its own."},
    "l2_beyond_no": {"es": "La práctica no es más predecible que la carta Q y el ficticio en las particiones por "
                           "labor y por zona fuera (los motivos van en la tabla), o alguna no se pudo evaluar.",
                     "en": "The practice is not more predictable than the Q chart and the dummy in the excavation "
                           "and zone-left-out partitions (the reasons are in the table), or one could not be "
                           "evaluated."},
    "cap_l2_conc": {"es": "Concordancia entre el sostenimiento recomendado y el instalado (tramos)",
                    "en": "Agreement between recommended and installed support (tramos)"},
    "l2_conc_text": {"es": "{n} tramos traen los dos; kappa ponderado cuadrático {kappa}.",
                     "en": "{n} tramos have both; quadratic weighted kappa {kappa}."},
    "l2_conc_none": {"es": "No hay tramos con sostenimiento recomendado e instalado de tipos definidos.",
                     "en": "No tramo has both a recommended and an installed support of defined types."},
    "l2_conformal": {
        "es": "Conjunto conforme agrupado al {level:.0%} (Angelopoulos y Bates 2023 [V2]): el umbral del puntaje "
              "({q}) sale de las probabilidades fuera de pliegue por labor. {k} de {n} tramos tienen un tipo "
              "instalado fuera de su conjunto: la práctica de la mina no suele instalar eso en esa condición. La "
              "cobertura es aproximada y supone labores intercambiables; con zonas muy distintas no se cumple.",
        "en": "Grouped conformal set at {level:.0%} (Angelopoulos and Bates 2023 [V2]): the score threshold ({q}) "
              "comes from the out-of-fold probabilities by excavation. {k} of {n} tramos have an installed type "
              "outside their set: the mine does not usually install that in that condition. The coverage is "
              "approximate and assumes exchangeable excavations; with very different zones it does not hold.",
    },
    "cap_l2_outside": {"es": "Tramos con el tipo instalado fuera del conjunto conforme",
                       "en": "Tramos with the installed type outside the conformal set"},
    "l2_none_outside": {"es": "Ningún tramo quedó fuera de su conjunto conforme.",
                        "en": "No tramo fell outside its conformal set."},
    "dd_l2_min": {"es": "Mínimo del nivel 2 por tipo instalado", "en": "Level 2 minimum per installed type"},
    "dd_l2_min_v": {"es": "{t} tramos de {l} labores", "en": "{t} tramos from {l} excavations"},
    "dd_conformal": {"es": "Nivel del conjunto conforme", "en": "Conformal set level"},
    "dd_gain_ci": {"es": "Mejora significativa", "en": "Significant gain"},
    "dd_gain_ci_v": {"es": "límite inferior del IC 95 % por bootstrap de labores > 0",
                     "en": "lower bound of the 95 % CI from an excavation bootstrap > 0"},
    "dd_discarded": {"es": "Réplicas degeneradas admitidas", "en": "Degenerate replicates allowed"},
    # nivel 3
    "l3_text": {
        "es": "P(falla) por tramo en un horizonte de exposición, con un modelo bayesiano MAP: prior Cauchy débil "
              "sobre las variables estandarizadas (Gelman et al. 2008 [V2]), covarianza de Laplace y restricciones "
              "de signo: peor macizo, más luz y más profundidad no bajan P(falla); más sostenimiento no la sube. La "
              "exposición entra en el modelo, así que P(falla) depende del horizonte que se pida. Un tramo falla si "
              "alguna inspección dice Falla o Reparado (por confirmar); la exposición va desde la instalación hasta "
              "la primera falla o la última inspección. La línea base es el mismo modelo con la categoría de la "
              "carta Q NGI como única variable del macizo y la misma exposición, sin cotas.",
        "en": "P(failure) per tramo over an exposure horizon, with a MAP Bayesian model: weak Cauchy prior on the "
              "standardized variables (Gelman et al. 2008 [V2]), Laplace covariance and sign constraints: poorer "
              "rock, larger span and greater depth do not lower P(failure); more support does not raise it. Exposure "
              "enters the model, so P(failure) depends on the horizon asked for. A tramo fails if any inspection "
              "says Falla or Reparado (to be confirmed); exposure runs from installation to the first failure or "
              "the last inspection. The baseline is the same model with the NGI Q chart category as its only rock "
              "variable and the same exposure, unbounded.",
    },
    "l3_rule_val": {
        "es": "Regla de calibración: «propio del sitio» exige cumplir el mínimo del nivel 3 y que las particiones "
              "por labor y por zona fuera superen al ficticio y a la línea base NGI con el límite inferior del IC "
              "95 % de la mejora del Brier sobre cero, sin pliegues fallidos y con no más del 1 % de réplicas "
              "degeneradas. La partición temporal entra como no inferioridad: bloquea solo si la mejora puntual "
              "contra alguna referencia es negativa, porque el test de un solo año es chico y su IC casi siempre "
              "toca el cero; si no se pudo armar, no bloquea y la validación lo avisa. «Parcial»: cumple el mínimo "
              "pero no lo demás; muestra P(falla) y no elige. «No calibrado al sitio»: bajo el mínimo.",
        "en": "Calibration rule: \"site\" requires the level-3 minimum and that the excavation and zone-left-out "
              "partitions beat the dummy and the NGI baseline with the lower bound of the 95 % CI of the Brier gain "
              "above zero, with no failed fold and no more than 1 % degenerate replicates. The temporal partition "
              "enters as non-inferiority: it blocks only if the point gain over a reference is negative, because "
              "the single-year test is small and its CI almost always reaches zero; if it could not be built, it "
              "does not block and the validation warns. \"Partial\": meets the minimum but not the rest; it shows "
              "P(failure) and does not choose. \"Not calibrated to the site\": below the minimum.",
    },
    "cap_l3_state": {"es": "Estado y datos del nivel 3", "en": "Level 3 status and data"},
    "l3_calibration": {"es": "Nivel de calibración", "en": "Calibration level"},
    "l3_reason": {"es": "Motivo", "en": "Reason"},
    "l3_quality": {"es": "Calidad del macizo", "en": "Rock quality"},
    "l3_tramos": {"es": "Tramos con inspección usados", "en": "Inspected tramos used"},
    "l3_failures": {"es": "Con falla", "en": "With failure"},
    "l3_non_failures": {"es": "Sin falla", "en": "Without failure"},
    "l3_labors": {"es": "Labores", "en": "Excavations"},
    "l3_zones": {"es": "Zonas", "en": "Zones"},
    "l3_params": {"es": "Parámetros", "en": "Parameters"},
    "l3_minority": {"es": "Clase menor / mínimo (decisión de diseño)",
                    "en": "Minority class / minimum (design decision)"},
    "cal_site": {"es": "propio del sitio", "en": "site"},
    "cal_partial": {"es": "parcial", "en": "partial"},
    "cal_not_calibrated": {"es": "no calibrado al sitio", "en": "not calibrated to the site"},
    "l3_no_fit": {"es": "No hay ajuste: todos los tramos usables tienen el mismo resultado.",
                  "en": "There is no fit: every usable tramo has the same outcome."},
    "cap_l3_coef": {"es": "Coeficientes del modelo MAP (escala original) con su IC 95 % de Laplace",
                    "en": "MAP model coefficients (original scale) with their 95 % Laplace CI"},
    "sign_up": {"es": "≥ 0", "en": "≥ 0"},
    "sign_down": {"es": "≤ 0", "en": "≤ 0"},
    "sign_free": {"es": "libre", "en": "free"},
    "cap_l3_val": {"es": "Brier fuera de pliegue por partición (menor es mejor)",
                   "en": "Out-of-fold Brier score by partition (lower is better)"},
    "cap_l3_oof": {"es": "Desempeño fuera de pliegue (partición por labor)",
                   "en": "Out-of-fold performance (excavation partition)"},
    "m_brier": {"es": "Brier", "en": "Brier"},
    "m_auc": {"es": "AUC", "en": "AUC"},
    "m_ap": {"es": "Precisión promedio (PR)", "en": "Average precision (PR)"},
    "m_cal_a": {"es": "Intercepto de calibración", "en": "Calibration intercept"},
    "m_cal_b": {"es": "Pendiente de calibración", "en": "Calibration slope"},
    "fig_l3_cal": {"es": "Curva de calibración fuera de pliegue por deciles (Van Calster et al. 2019 [V2])",
                   "en": "Out-of-fold calibration curve by deciles (Van Calster et al. 2019 [V2])"},
    "l3_iso_text": {
        "es": "Isoprobabilidades de falla por tipo en el plano Q–De, al estilo de Mawdesley et al. (2001) [V2 + resumen], "
              "dentro del rango de entrenamiento, a {days:.0f} días de exposición (el horizonte del ingeniero o, si "
              "no lo dio, la mediana del histórico), con el tipo de labor de referencia y, si el modelo la usa, la "
              "profundidad media. Los puntos son los tramos con ese tipo instalado.",
        "en": "Probability of failure contours by type in the Q–De plane, after Mawdesley et al. (2001) [V2 + resumen], "
              "within the training range, at {days:.0f} days of exposure (the engineer's horizon or, if none was "
              "given, the history's median), with the reference excavation type and, if the model uses it, the mean "
              "depth. The points are the tramos with that type installed.",
    },
    "l3_iso_no_horizon": {"es": "Sin histórico ni horizonte de exposición no se dibujan las isoprobabilidades.",
                          "en": "Without the history or an exposure horizon the contours are not drawn."},
    "noninf_met": {"es": "no inferioridad: cumple", "en": "non-inferiority: met"},
    "noninf_not": {"es": "no inferioridad: no cumple (bloquea)", "en": "non-inferiority: not met (blocks)"},
    "random_no_weight": {"es": "optimista: no cuenta en la decisión", "en": "optimistic: does not count"},
    "l3_iso_rmr": {"es": "El modelo usa RMR: las isoprobabilidades en el plano Q–De no aplican.",
                   "en": "The model uses RMR: the Q–De contours do not apply."},
    "fig_l3_iso": {"es": "Isoprobabilidad de falla, tipo {code}", "en": "Probability of failure contours, type {code}"},
    "l3_rule": {
        "es": "Regla de recomendación: para un tramo nuevo se calcula P(falla) con su intervalo al 90 % para cada "
              "tipo de la mina, del más liviano al más pesado, y se elige el más liviano cuyo límite superior queda "
              "bajo el umbral. El umbral lo fija el ingeniero: es obligatorio y no tiene valor por defecto, igual "
              "que el horizonte de exposición (rockmass recommend --threshold P --exposure-days D). Solo con el "
              "nivel «propio del sitio» y sin motivo de bloqueo (extrapolación, tipos sin historia suficiente, "
              "efecto del sostenimiento no significativo o cota activa) se elige un tipo; los motivos van con cada "
              "recomendación. Cada recomendación trae las tres razones principales, la "
              "alerta de extrapolación y las columnas vacías decision_ingeniero y motivo, donde el ingeniero "
              "registra lo que decidió; con el desempeño posterior, alimentan el siguiente ajuste.",
        "en": "Recommendation rule: for a new tramo, P(failure) with its 90 % interval is computed for every "
              "support type of the mine, lightest to heaviest, and the lightest type whose upper bound stays below "
              "the threshold is chosen. The engineer sets the threshold: it is mandatory and has no default, like "
              "the exposure horizon (rockmass recommend --threshold P --exposure-days D). A type is chosen only at "
              "the \"site\" level and with no blocking reason (extrapolation, types without enough history, a "
              "non-significant support effect or an active bound); the reasons go with each recommendation. Each "
              "recommendation carries the three main reasons, the extrapolation alert and "
              "the empty columns decision_ingeniero and motivo, where the engineer records the decision; with the "
              "later performance, they feed the next fit.",
    },
    "l3_threshold": {"es": "Umbral de este informe, fijado por el ingeniero: P(falla) ≤ {thr:g}.",
                     "en": "Threshold of this report, set by the engineer: P(failure) ≤ {thr:g}."},
    "l3_threshold_none": {"es": "Este informe no fija un umbral: el ingeniero lo da al pedir la recomendación.",
                          "en": "This report sets no threshold: the engineer gives it when asking for the "
                                "recommendation."},
    "dd_l3_min": {"es": "Mínimo del nivel 3", "en": "Level 3 minimum"},
    "dd_l3_min_v": {"es": "{e} eventos de la clase menor por parámetro y {z} zonas",
                    "en": "{e} minority-class events per parameter and {z} zones"},
    "dd_signs": {"es": "Restricciones de signo", "en": "Sign constraints"},
    "dd_signs_v": {"es": "por cotas (L-BFGS-B); el tipo de labor queda libre",
                   "en": "by bounds (L-BFGS-B); excavation type is free"},
    "dd_baseline": {"es": "Línea base de nivel 0", "en": "Level 0 baseline"},
    "dd_baseline_v": {"es": "categoría de la carta Q NGI con la misma exposición, sin cotas",
                      "en": "NGI Q chart category with the same exposure, unbounded"},
    "dd_temporal": {"es": "Partición temporal", "en": "Temporal partition"},
    "dd_temporal_v": {"es": "no inferioridad (mejora puntual ≥ 0)", "en": "non-inferiority (point gain ≥ 0)"},
    "dd_interval": {"es": "Intervalo de P(falla) y límite usado", "en": "P(failure) interval and bound used"},
    "dd_interval_v": {"es": "90 %, límite superior (conservador)", "en": "90 %, upper bound (conservative)"},
    "dd_maha": {"es": "Alerta de extrapolación", "en": "Extrapolation alert"},
    "dd_maha_v": {"es": "fuera del rango o Mahalanobis sobre el percentil {p:g} del entrenamiento",
                  "en": "outside the range or Mahalanobis above the training {p:g}th percentile"},
    "dd_threshold": {"es": "Umbral de P(falla)", "en": "P(failure) threshold"},
    "dd_threshold_v": {"es": "lo fija el ingeniero; sin valor por defecto", "en": "set by the engineer; no default"},
    # TRIPOD+AI
    "tripod_text": {
        "es": "TRIPOD+AI (Collins et al. 2024 [V2]) es la lista de verificación más completa para informar modelos "
              "de predicción con regresión o aprendizaje automático. Viene de la medicina y se aplica sin cambios "
              "de fondo. La tabla dice qué cubre este informe y qué no; los ítems van por nombre (la numeración "
              "está en la fuente). Lo que no cubre lo completa el autor del estudio.",
        "en": "TRIPOD+AI (Collins et al. 2024 [V2]) is the most complete checklist for reporting prediction models "
              "built with regression or machine learning. It comes from medicine and applies without substantive "
              "changes. The table says what this report covers and what it does not; items go by name (the "
              "numbering is in the source). The author of the study completes what it does not cover.",
    },
    "cap_tripod": {"es": "TRIPOD+AI: lo que cubre este informe", "en": "TRIPOD+AI: what this report covers"},
    "h_tripod_item": {"es": "Ítem", "en": "Item"},
    "h_tripod_covered": {"es": "Cubierto", "en": "Covered"},
    "h_tripod_where": {"es": "Dónde o por qué", "en": "Where or why"},
    "tr_yes": {"es": "sí", "en": "yes"},
    "tr_partial": {"es": "parcial", "en": "partial"},
    "tr_no": {"es": "no", "en": "no"},
    "tr_na": {"es": "no aplica", "en": "not applicable"},
}

# TRIPOD+AI (Collins et al. 2024): (estado, {idioma: (ítem, dónde o por qué)}). Estado: yes, partial, no, na.
TRIPOD_ITEMS: tuple[tuple[str, dict[str, tuple[str, str]]], ...] = (
    ("yes", {"es": ("Fuente de los datos y fechas", "Datos: hojas y años cubiertos (nunca el archivo)"),
             "en": ("Data source and dates", "Data: sheets and years covered (never the file)")}),
    ("yes", {"es": ("Unidades y criterios de elegibilidad", "Preparación por nivel y datos de cada nivel"),
             "en": ("Units and eligibility criteria", "Readiness by level and the data of each level")}),
    ("yes", {"es": ("Preparación de los datos", "Auditoría de ingesta (Q y RMR recalculados, independencia)"),
             "en": ("Data preparation", "Ingestion audit (Q and RMR recomputed, independence)")}),
    ("yes", {"es": ("Resultado y cómo se define", "Nivel 2: tipo instalado; nivel 3: Falla o Reparado y exposición"),
             "en": ("Outcome and its definition", "Level 2: installed type; level 3: Falla or Reparado and exposure")}),
    ("yes", {"es": ("Predictores", "Tablas de coeficientes de los niveles 2 y 3"),
             "en": ("Predictors", "Coefficient tables of levels 2 and 3")}),
    ("partial", {"es": ("Tamaño de muestra", "Mínimos por nivel (decisión de diseño), sin el cálculo de Riley et al. "
                                             "(2020)"),
                 "en": ("Sample size", "Minimums by level (design decision), without the Riley et al. (2020) "
                                       "calculation")}),
    ("partial", {"es": ("Datos faltantes", "Casos completos: las filas incompletas no entran; sin imputación"),
                 "en": ("Missing data", "Complete cases: incomplete rows are left out; no imputation")}),
    ("yes", {"es": ("Métodos analíticos y validación interna", "Particiones por labor, zona fuera y temporal; "
                                                               "bootstrap por labor"),
             "en": ("Analytical methods and internal validation", "Excavation, zone-left-out and temporal "
                                                                  "partitions; excavation bootstrap")}),
    ("yes", {"es": ("Desbalance de clases", "Sin rebalanceo; kappa ponderado y Brier"),
             "en": ("Class imbalance", "No rebalancing; weighted kappa and Brier")}),
    ("na", {"es": ("Equidad entre grupos de personas", "Las unidades son tramos, no personas; la heterogeneidad entre "
                                                       "zonas se mide con la zona fuera"),
            "en": ("Fairness across groups of people", "The units are tramos, not people; heterogeneity across "
                                                       "zones is measured with the zone left out")}),
    ("yes", {"es": ("Salida del modelo", "P(falla) con su intervalo y la regla de recomendación"),
             "en": ("Model output", "P(failure) with its interval and the recommendation rule")}),
    ("yes", {"es": ("Entrenamiento frente a evaluación", "Métricas fuera de pliegue"),
             "en": ("Training versus evaluation", "Out-of-fold metrics")}),
    ("yes", {"es": ("Desempeño: discriminación y calibración", "Nivel 3: Brier, AUC, PR y curva de calibración; "
                                                               "nivel 2: kappa ponderado"),
             "en": ("Performance: discrimination and calibration", "Level 3: Brier, AUC, PR and calibration curve; "
                                                                   "level 2: weighted kappa")}),
    ("yes", {"es": ("Especificación completa del modelo", "Coeficientes en el informe; el modelo JSON"),
             "en": ("Full model specification", "Coefficients in the report; the model JSON")}),
    ("partial", {"es": ("Actualización del modelo", "decision_ingeniero y el desempeño posterior; sin reajuste "
                                                    "automático"),
                 "en": ("Model updating", "decision_ingeniero and later performance; no automatic refit")}),
    ("no", {"es": ("Validación externa", "Solo interna: otra mina o un periodo largo nuevo no están en el histórico"),
            "en": ("External validation", "Internal only: another mine or a long new period is not in the history")}),
    ("yes", {"es": ("Interpretación y limitaciones", "Limitaciones"),
             "en": ("Interpretation and limitations", "Limitations")}),
    ("partial", {"es": ("Uso del modelo en la práctica", "rockmass recommend; sin evaluación de impacto"),
                 "en": ("Use of the model in practice", "rockmass recommend; no impact assessment")}),
    ("partial", {"es": ("Datos y código disponibles", "Código abierto (MIT); los datos son de la mina y no se "
                                                      "publican"),
                 "en": ("Data and code availability", "Open source code (MIT); the data belong to the mine and are "
                                                       "not published")}),
    ("no", {"es": ("Protocolo, registro, financiamiento, conflictos y ética", "Fuera del informe automático: los "
                                                                             "completa el autor"),
            "en": ("Protocol, registration, funding, conflicts and ethics", "Outside the automatic report: the "
                                                                           "author completes them")}),
    ("na", {"es": ("Participación de pacientes y del público", "No aplica a tramos de labores"),
            "en": ("Patient and public involvement", "Does not apply to excavation tramos")}),
)


def t(key: str, lang: str) -> str:
    return REPORT_TEXTS[key][lang]
