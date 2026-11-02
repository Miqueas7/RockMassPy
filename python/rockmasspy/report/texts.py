"""Textos del informe en es/en. Un solo diccionario: REPORT_TEXTS[clave][idioma]."""

DISCLAIMER = {
    "es": "La librería recomienda, el ingeniero decide. Este documento no reemplaza el estudio geomecánico firmado.",
    "en": "The library recommends, the engineer decides. This document does not replace the signed geomechanical study.",
}

REPORT_TEXTS: dict[str, dict[str, str]] = {
    "memoria_title": {"es": "Memoria de cálculo", "en": "Calculation report"},
    "s1": {"es": "Objetivo y alcance", "en": "Purpose and scope"},
    "s1_text": {
        "es": "Este documento clasifica tramos de labores subterráneas con las tablas geomecánicas de cada labor y "
              "recomienda un tipo de sostenimiento por tramo. Trae las ediciones de cada método, los resultados y los avisos.",
        "en": "This document classifies underground section tramos with the geomechanical table of each labor and "
              "recommends a support type for each tramo. It lists the edition of each method, the results and the warnings.",
    },
    "s2": {"es": "Métodos y ediciones", "en": "Methods and editions"},
    "s3": {"es": "Tablas geomecánicas por labor", "en": "Geomechanical tables by labor"},
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
    "cap_by_class": {"es": "Tramos por labor y clase", "en": "Tramos by labor and class"},
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
    "unknown_method": {"es": "sin información de verificación", "en": "no verification information"},
}


def t(key: str, lang: str) -> str:
    return REPORT_TEXTS[key][lang]
