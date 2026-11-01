# Genera la plantilla Excel vacía para reunir el histórico geomecánico de una mina (RockMassPy, módulo predictivo).
# Uso: py -3 -X utf8 plantilla_historico.py <ruta_salida.xlsx>
import sys
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation

LISTAS = {
    'tipo_labor': 'Rampa,Galería,Crucero,Subnivel,Tajeo,Chimenea,Cámara,Pique,Bypass,Banco,Talud',
    'vida_util': 'Temporal,Permanente',
    'metodo_excavacion': 'Perforación y voladura,Mecanizada,Raise boring,Otro',
    'metodo_ucs': 'Ensayo de laboratorio,Carga puntual,Martillo Schmidt,Martillo de geólogo,Estimado',
    'agua': 'Seco,Húmedo,Mojado,Goteo,Flujo',
    'rmr_edicion': 'RMR76,RMR89,RMR14',
    'q_edicion': 'Q-1974,Q-NGI-2015,Q-NGI-2025',
    'gsi_tabla': 'GSI clásico,GSI cuantificado 2013,GSI modificado (Perú),Tabla propia',
    'si_no': 'Sí,No',
    'estado': 'Estable,Falla,Reparado,Abandonado',
    'tipo_falla': 'Caída de cuña,Desprendimiento,Sobreexcavación,Deformación excesiva,Estallido de roca,Falla del sostenimiento,Otro',
}

# (hoja, columna, descripción, unidad, lista o tipo, obligatoria para niveles)
# Niveles del módulo: 1 = correlaciones propias, 2 = auditoría de la práctica, 3 = desempeño (probabilidad de falla).
COLUMNAS = [
    ('Tramos', 'id_tramo', 'Código único del tramo evaluado (T0001…)', '', 'texto', '1,2,3'),
    ('Tramos', 'codigo_mina', 'Código de la mina, nunca el nombre (Cliente A)', '', 'texto', '1,2,3'),
    ('Tramos', 'zona_nivel', 'Código de zona o nivel (Z1, NV-3940)', '', 'texto', '1,2,3'),
    ('Tramos', 'labor_codigo', 'Código de la labor (L001)', '', 'texto', '1,2,3'),
    ('Tramos', 'tipo_labor', 'Tipo de labor', '', 'tipo_labor', '1,2,3'),
    ('Tramos', 'fecha_evaluacion', 'Fecha del mapeo o evaluación', 'aaaa-mm-dd', 'fecha', '1,2,3'),
    ('Tramos', 'progresiva_inicio_m', 'Progresiva de inicio del tramo', 'm', 'número', '3'),
    ('Tramos', 'progresiva_fin_m', 'Progresiva de fin del tramo', 'm', 'número', '3'),
    ('Tramos', 'este_m', 'Coordenada Este del centro del tramo', 'm', 'número', ''),
    ('Tramos', 'norte_m', 'Coordenada Norte del centro del tramo', 'm', 'número', ''),
    ('Tramos', 'cota_m', 'Cota del tramo', 'm s. n. m.', 'número', ''),
    ('Tramos', 'datum', 'Sistema de coordenadas (WGS84 UTM 18S, PSAD56, local)', '', 'texto', ''),
    ('Tramos', 'profundidad_m', 'Cobertura de roca sobre el tramo', 'm', 'número', '3'),
    ('Tramos', 'ancho_m', 'Ancho de la sección', 'm', 'número', '2,3'),
    ('Tramos', 'alto_m', 'Alto de la sección', 'm', 'número', '2,3'),
    ('Tramos', 'luz_m', 'Luz o abertura máxima sin sostener', 'm', 'número', '2,3'),
    ('Tramos', 'esr', 'ESR usado (relación de soporte de la excavación)', '', 'número', '2,3'),
    ('Tramos', 'rumbo_labor_grados', 'Rumbo del eje de la labor', '°', 'número', '3'),
    ('Tramos', 'vida_util', 'Vida útil de la labor', '', 'vida_util', '2,3'),
    ('Tramos', 'metodo_excavacion', 'Cómo se excavó', '', 'metodo_excavacion', '3'),
    ('Tramos', 'litologia', 'Litología (texto corto)', '', 'texto', '1,2,3'),
    ('Tramos', 'alteracion', 'Grado de alteración (ISRM: fresca a descompuesta)', '', 'texto', ''),
    ('Tramos', 'ucs_mpa', 'Resistencia a la compresión simple de la roca intacta', 'MPa', 'número', '1,3'),
    ('Tramos', 'metodo_ucs', 'Cómo se obtuvo la UCS', '', 'metodo_ucs', '1,3'),
    ('Tramos', 'rqd_pct', 'RQD', '%', 'número', '1,2,3'),
    ('Tramos', 'jv', 'Conteo volumétrico de juntas', 'juntas/m³', 'número', ''),
    ('Tramos', 'num_familias', 'Número de familias de discontinuidades', '', 'número', '1'),
    ('Tramos', 'espaciamiento_m', 'Espaciamiento típico de discontinuidades', 'm', 'número', '1'),
    ('Tramos', 'puntaje_condicion_juntas', 'Puntaje de condición de juntas del RMR (0–30)', 'pts', 'número', '1'),
    ('Tramos', 'agua', 'Condición de agua', '', 'agua', '1,3'),
    ('Tramos', 'jn', 'Q: número de familias Jn', '', 'número', '1'),
    ('Tramos', 'jr', 'Q: rugosidad Jr', '', 'número', '1'),
    ('Tramos', 'ja', 'Q: alteración Ja', '', 'número', '1'),
    ('Tramos', 'jw', 'Q: agua Jw', '', 'número', '1'),
    ('Tramos', 'srf', 'Q: factor de reducción de esfuerzos SRF', '', 'número', '1,3'),
    ('Tramos', 'rmr_valor', 'RMR calculado', 'pts', 'número', '1,2,3'),
    ('Tramos', 'rmr_edicion', 'Edición del RMR usada', '', 'rmr_edicion', '1,2,3'),
    ('Tramos', 'q_valor', 'Q calculado', '', 'número', '1,2,3'),
    ('Tramos', 'q_edicion', 'Edición del Q usada', '', 'q_edicion', '1,2,3'),
    ('Tramos', 'gsi_valor', 'GSI asignado', 'pts', 'número', '1'),
    ('Tramos', 'gsi_tabla', 'Tabla GSI usada', '', 'gsi_tabla', '1'),
    ('Tramos', 'sost_recomendado', 'Tipo de sostenimiento que pedía la tabla (código de la hoja Tipos_sostenimiento)', '', 'texto', '2'),
    ('Tramos', 'sost_instalado', 'Tipo de sostenimiento realmente instalado (código)', '', 'texto', '2,3'),
    ('Tramos', 'fecha_instalacion', 'Fecha en que se terminó de sostener', 'aaaa-mm-dd', 'fecha', '3'),
    ('Tramos', 'tiempo_sin_sostener_h', 'Horas entre la voladura y el sostenimiento', 'h', 'número', '3'),
    ('Tramos', 'evaluador_codigo', 'Código del evaluador, nunca el nombre (E01)', '', 'texto', ''),
    ('Tramos', 'observaciones', 'Notas técnicas, sin nombres de personas', '', 'texto', ''),

    ('Familias', 'id_tramo', 'Tramo al que pertenece (de la hoja Tramos)', '', 'texto', '3'),
    ('Familias', 'familia', 'Número de familia (F1, F2…)', '', 'texto', '3'),
    ('Familias', 'buzamiento_grados', 'Buzamiento', '°', 'número', '3'),
    ('Familias', 'dir_buzamiento_grados', 'Dirección de buzamiento', '°', 'número', '3'),
    ('Familias', 'espaciamiento_m', 'Espaciamiento de la familia', 'm', 'número', ''),
    ('Familias', 'persistencia_m', 'Persistencia', 'm', 'número', ''),
    ('Familias', 'apertura_mm', 'Apertura', 'mm', 'número', ''),
    ('Familias', 'rugosidad', 'Rugosidad (ISRM o JRC)', '', 'texto', ''),
    ('Familias', 'relleno', 'Tipo y espesor de relleno', '', 'texto', ''),
    ('Familias', 'alteracion_paredes', 'Alteración de las paredes', '', 'texto', ''),

    ('Tipos_sostenimiento', 'codigo_tipo', 'Código del tipo que usa la mina (I, II, III… o el suyo)', '', 'texto', '2,3'),
    ('Tipos_sostenimiento', 'orden', 'Orden de menor a mayor: 1 = el más liviano', '', 'número', '2,3'),
    ('Tipos_sostenimiento', 'descripcion', 'Descripción corta', '', 'texto', ''),
    ('Tipos_sostenimiento', 'perno_tipo', 'Tipo de perno (Split Set, Swellex, helicoidal, cable…)', '', 'texto', '3'),
    ('Tipos_sostenimiento', 'perno_longitud_m', 'Longitud del perno', 'm', 'número', '3'),
    ('Tipos_sostenimiento', 'perno_espaciamiento_m', 'Espaciamiento entre pernos', 'm', 'número', '3'),
    ('Tipos_sostenimiento', 'shotcrete_espesor_mm', 'Espesor de shotcrete (0 si no lleva)', 'mm', 'número', '3'),
    ('Tipos_sostenimiento', 'shotcrete_fibra', 'Lleva fibra', '', 'si_no', ''),
    ('Tipos_sostenimiento', 'malla', 'Tipo de malla (vacío si no lleva)', '', 'texto', '3'),
    ('Tipos_sostenimiento', 'cimbra', 'Tipo y espaciamiento de cimbra (vacío si no lleva)', '', 'texto', '3'),
    ('Tipos_sostenimiento', 'costo_relativo', 'Costo por metro relativo al tipo más liviano (opcional)', '', 'número', ''),

    ('Desempeno', 'id_tramo', 'Tramo inspeccionado', '', 'texto', '3'),
    ('Desempeno', 'fecha_inspeccion', 'Fecha de la inspección o del evento', 'aaaa-mm-dd', 'fecha', '3'),
    ('Desempeno', 'estado', 'Estado del tramo', '', 'estado', '3'),
    ('Desempeno', 'tipo_falla', 'Tipo de falla (si hubo)', '', 'tipo_falla', '3'),
    ('Desempeno', 'volumen_m3', 'Volumen desprendido', 'm³', 'número', ''),
    ('Desempeno', 'sobreexcavacion_pct', 'Sobreexcavación respecto a la sección de diseño', '%', 'número', ''),
    ('Desempeno', 'convergencia_mm', 'Convergencia medida', 'mm', 'número', ''),
    ('Desempeno', 'reparacion_tipo', 'Tipo de sostenimiento con que se reparó (código)', '', 'texto', ''),
    ('Desempeno', 'observaciones', 'Notas técnicas, sin nombres de personas', '', 'texto', ''),

    ('Control_calidad', 'id_tramo', 'Tramo controlado', '', 'texto', ''),
    ('Control_calidad', 'fecha', 'Fecha del control', 'aaaa-mm-dd', 'fecha', ''),
    ('Control_calidad', 'ensayo', 'Ensayo (arranque de perno, espesor de shotcrete, torque…)', '', 'texto', ''),
    ('Control_calidad', 'resultado', 'Valor medido', '', 'número', ''),
    ('Control_calidad', 'unidad', 'Unidad del valor', '', 'texto', ''),
    ('Control_calidad', 'cumple', 'Cumple el criterio de diseño', '', 'si_no', ''),

    ('Ensayos', 'id_muestra', 'Código de la muestra', '', 'texto', ''),
    ('Ensayos', 'id_tramo', 'Tramo de donde salió (si se sabe)', '', 'texto', ''),
    ('Ensayos', 'litologia', 'Litología', '', 'texto', ''),
    ('Ensayos', 'ucs_mpa', 'Compresión simple', 'MPa', 'número', ''),
    ('Ensayos', 'mi', 'Constante mi de Hoek-Brown (triaxial)', '', 'número', ''),
    ('Ensayos', 'densidad_t_m3', 'Densidad', 't/m³', 'número', ''),
    ('Ensayos', 'modulo_e_gpa', 'Módulo de Young de la roca intacta', 'GPa', 'número', ''),
    ('Ensayos', 'poisson', 'Coeficiente de Poisson', '', 'número', ''),
]

LEEME = [
    'PLANTILLA DEL HISTÓRICO GEOMECÁNICO · RockMassPy',
    '',
    'Para qué sirve: reunir el histórico de una mina para calibrar sus correlaciones (nivel 1), revisar si su práctica de',
    'sostenimiento es coherente (nivel 2) y estimar la probabilidad de falla por tipo de sostenimiento (nivel 3).',
    '',
    'Una fila por tramo evaluado en la hoja Tramos. Cada tramo puede tener varias familias, inspecciones, controles y ensayos.',
    'La hoja Tipos_sostenimiento la define la mina: sus tipos, en orden de más liviano a más pesado, con sus elementos.',
    'La hoja Diccionario dice qué es cada columna, su unidad y para qué nivel es obligatoria.',
    '',
    'Mínimos para que el modelo se active (heurísticos, se confirmarán):',
    '  Nivel 1: 30 tramos o más con RMR y Q (o RMR y GSI), de al menos 5 labores.',
    '  Nivel 2: 10 tramos o más por cada tipo de sostenimiento instalado.',
    '  Nivel 3: inspecciones con fallas registradas: 10 fallas o más por cada variable del modelo, en 3 zonas o más.',
    '  Lo más valioso y lo que casi nadie registra: las fallas y los tramos que NO fallaron, con su fecha.',
    '',
    'REGLAS DE CONFIDENCIALIDAD (obligatorias):',
    '  - Nada de nombres de personas, DNI, teléfonos ni correos. Evaluadores con código (E01, E02…).',
    '  - La mina con código (Cliente A), nunca su nombre. Labores y zonas con código.',
    '  - El archivo lleno se guarda solo en la carpeta protegida de esa mina (zona del arnés de datos),',
    '    nunca en el repositorio ni en servicios externos.',
    '',
    'Celdas vacías: déjalas vacías si el dato no existe; no pongas cero ni «s/d».',
]

encabezado = Font(bold=True, color='FFFFFF')
relleno = PatternFill('solid', fgColor='1F4E5F')

def main(salida):
    wb = Workbook()
    ws = wb.active; ws.title = 'LEEME'
    for i, t in enumerate(LEEME, 1):
        ws.cell(i, 1, t).font = Font(bold=(i == 1), size=13 if i == 1 else 11)
    ws.column_dimensions['A'].width = 120

    for hoja in dict.fromkeys(h for h, *_ in COLUMNAS):
        ws = wb.create_sheet(hoja)
        cols = [c for c in COLUMNAS if c[0] == hoja]
        for j, (_, nombre, desc, unidad, tipo, niveles) in enumerate(cols, 1):
            celda = ws.cell(1, j, nombre)
            celda.font, celda.fill = encabezado, relleno
            celda.alignment = Alignment(wrap_text=True, vertical='center')
            letra = celda.column_letter
            ws.column_dimensions[letra].width = max(14, len(nombre) + 2)
            if tipo in LISTAS:
                dv = DataValidation(type='list', formula1=f'"{LISTAS[tipo]}"', allow_blank=True)
                ws.add_data_validation(dv); dv.add(f'{letra}2:{letra}5000')
            elif tipo == 'número':
                dv = DataValidation(type='decimal', operator='greaterThanOrEqual', formula1='-1000000', allow_blank=True)
                ws.add_data_validation(dv); dv.add(f'{letra}2:{letra}5000')
            elif tipo == 'fecha':
                for r in range(2, 5001): ws.cell(r, j).number_format = 'yyyy-mm-dd'
        ws.freeze_panes = 'B2'

    ws = wb.create_sheet('Diccionario')
    cab = ['hoja', 'columna', 'descripción', 'unidad', 'tipo o lista', 'obligatoria para nivel']
    for j, t in enumerate(cab, 1):
        c = ws.cell(1, j, t); c.font, c.fill = encabezado, relleno
    for i, (hoja, nombre, desc, unidad, tipo, niveles) in enumerate(COLUMNAS, 2):
        tipo_txt = f'lista: {LISTAS[tipo]}' if tipo in LISTAS else tipo
        for j, v in enumerate([hoja, nombre, desc, unidad, tipo_txt, niveles], 1):
            ws.cell(i, j, v).alignment = Alignment(wrap_text=True, vertical='top')
    for letra, w in zip('ABCDEF', [20, 26, 60, 12, 50, 14]):
        ws.column_dimensions[letra].width = w
    ws.freeze_panes = 'A2'
    wb.save(salida)

if __name__ == '__main__':
    main(sys.argv[1])
    # autocomprobación: cada hoja tiene sus encabezados y el diccionario cubre todas las columnas
    from openpyxl import load_workbook
    wb = load_workbook(sys.argv[1])
    for hoja in dict.fromkeys(h for h, *_ in COLUMNAS):
        esperadas = [c[1] for c in COLUMNAS if c[0] == hoja]
        reales = [c.value for c in wb[hoja][1]]
        assert reales == esperadas, hoja
    assert wb['Diccionario'].max_row == len(COLUMNAS) + 1
    print('OK', [ (h, len([c for c in COLUMNAS if c[0]==h])) for h in dict.fromkeys(h for h,*_ in COLUMNAS)])
