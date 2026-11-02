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
    "unknown_method": {"es": "sin información de verificación", "en": "no verification information"},
}


def t(key: str, lang: str) -> str:
    return REPORT_TEXTS[key][lang]
