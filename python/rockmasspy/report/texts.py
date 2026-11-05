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
    "hm_boot": {"es": "Bootstrap por labor (2000 réplicas, semilla fija)",
                "en": "Bootstrap by excavation (2000 replicates, fixed seed)"},
    "hm_deming": {"es": "Deming (con la razón de varianzas de error)", "en": "Deming (with the error-variance ratio)"},
    "hm_bayes": {"es": "Bayesiano conjugado normal–gamma inversa con la correlación global como prior",
                 "en": "Conjugate normal–inverse-gamma Bayesian fit with the global correlation as prior"},
    "hm_dd": {"es": "decisión de diseño", "en": "design decision"},
    "hm_prior_strength": {"es": "fuerza del prior", "en": "prior strength"},
    "hist_limits": {
        "es": "Las correlaciones son del sitio y de su rango observado: fuera de ese rango no valen. Un tramo no es "
              "independiente de sus vecinos de la misma labor; por eso el bootstrap es por labor. El histórico "
              "registra lo que la mina midió y decidió, con sus sesgos de selección y de observador. Los mínimos, "
              "el umbral de estabilidad y la fuerza del prior son decisiones de diseño por confirmar. El informe no "
              "trae los niveles 2 y 3 (fase 4B y 4C).",
        "en": "The correlations belong to the site and to its observed range: outside that range they do not hold. "
              "A tramo is not independent of its neighbours in the same excavation; that is why the bootstrap is by "
              "excavation. The history records what the mine measured and decided, with its selection and observer "
              "biases. The minimums, the stability threshold and the prior strength are design decisions to be "
              "confirmed. The report does not cover levels 2 and 3 (phases 4B and 4C).",
    },
}


def t(key: str, lang: str) -> str:
    return REPORT_TEXTS[key][lang]
