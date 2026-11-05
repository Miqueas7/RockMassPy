"""Conteos agregados de los accidentes mortales por desprendimiento de rocas en los compendios de Osinergmin.

Uso: python -I compendio_desprendimientos.py <compendio1.txt> [<compendio2.txt> ...]
(los .txt salen de `pdftotext -layout` del PDF público). Solo imprime conteos de palabras clave por bloque de
accidente: nunca nombres de empresas, unidades ni personas, ni texto de los relatos.
"""
import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CLAVES = {  # etiqueta: expresión regular sobre el texto sin tildes y en minúsculas
    "tajeo": r"\btajeo", "galeria/crucero/rampa/by pass": r"\b(galeria|crucero|rampa|by ?pass|subnivel)",
    "chimenea": r"\bchimenea", "frente": r"\bfrente\b",
    "corona/techo": r"\b(corona|techo)\b", "hastial/caja": r"\b(hastial|caja techo|caja piso)",
    "cuna/bloque": r"\b(cuna|bloque|banco)\b",
    "sin sostener o falta de sostenimiento": r"(sin sostenimiento|no (se )?(habia|contaba|instal)\w* (con )?(el )?sostenimiento|falta de sostenimiento|sin sostener)",
    "con sostenimiento instalado (perno/shotcrete/malla/cimbra)": r"\b(perno|shotcrete|malla|cimbra|split ?set|hydrabolt|swellex)",
    "desatado": r"\bdesat", "voladura reciente": r"\bvoladura",
    "falla geologica/estructura": r"\b(falla geologica|estructura|fractura)",
}


def plano(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


tot, cuenta = 0, {k: 0 for k in CLAVES}
for ruta in sys.argv[1:]:
    txt = plano(open(ruta, encoding="utf-8", errors="replace").read())
    bloques = re.split(r"1\.\s*segun el tipo", txt)[1:]
    n = 0
    for b in bloques:
        b = b[:6000]  # el relato y las causas de un accidente
        if not b.lstrip(" (*):").startswith("desprendimiento de roca"):
            continue
        n += 1
        for k, rx in CLAVES.items():
            cuenta[k] += bool(re.search(rx, b))
    print(f"{ruta.split('/')[-1]}: {n} bloques de desprendimiento de rocas")
    tot += n
print(f"total bloques: {tot}")
for k, c in cuenta.items():
    print(f"  {k}: {c} ({c / tot:.0%})" if tot else f"  {k}: 0")
