"""Imprime solo la estructura de xlsx/docx (hojas, filas, columnas, tipos, categorías de pocas clases). Sin filas."""
import sys, re, zipfile, collections
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SOLO_HOJA = None  # nombre de hoja opcional vía --hoja=

def tipo(vals):
    v = [x for x in vals if x not in (None, "")]
    if not v:
        return "vacía", 0
    num = sum(isinstance(x, (int, float)) for x in v)
    return ("num" if num == len(v) else "texto" if num == 0 else "mixta"), len(v)

def xlsx(p):
    import openpyxl
    wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
    for ws in wb.worksheets:
        rows = [r for r in ws.iter_rows(values_only=True) if any(c not in (None, "") for c in r)]
        if not rows:
            print(f"  hoja '{ws.title}': vacía"); continue
        # cabecera = primera fila con >=2 textos
        hi = next((i for i, r in enumerate(rows[:15]) if sum(isinstance(c, str) for c in r) >= 2), 0)
        head = rows[hi]; body = rows[hi + 1:]
        print(f"  hoja '{ws.title}': {len(body)} filas de datos, {len(head)} columnas (cabecera en fila {hi+1})")
        for j, h in enumerate(head):
            col = [r[j] if j < len(r) else None for r in body]
            t, n = tipo(col)
            if t == "vacía" and h in (None, ""):
                continue
            extra = ""
            nn = [c for c in col if c not in (None, "")]
            uniq = set(map(str, nn))
            if t != "num" and 0 < len(uniq) <= 8:
                extra = " clases=" + str(dict(collections.Counter(map(str, nn))))
            elif t == "num" and nn and len(uniq) <= 5:
                extra = " valores=" + str(dict(collections.Counter(nn)))
            print(f"    - {str(h)[:60]!r}: {t}, no nulos={n}{extra}")

def docx(p):
    with zipfile.ZipFile(p) as z:
        xml = z.read("word/document.xml").decode("utf8", "ignore")
    tablas = re.findall(r"<w:tbl>.*?</w:tbl>", xml, flags=re.S)
    print(f"  docx: {len(tablas)} tablas")
    for k, t in enumerate(tablas):
        filas = re.findall(r"<w:tr[ >].*?</w:tr>", t, flags=re.S)
        def celdas(f):
            return ["".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", c)).strip() for c in re.findall(r"<w:tc>.*?</w:tc>", f, flags=re.S)]
        cab = celdas(filas[0]) if filas else []
        print(f"   tabla {k+1}: {len(filas)} filas (incl. cabecera), cabecera={[c[:30] for c in cab]}")

for a in sys.argv[1:]:
    p = Path(a); print("==", p.parent.name + "/" + p.name)
    try:
        xlsx(p) if p.suffix.lower() in (".xlsx", ".xlsm") else docx(p)
    except Exception as e:
        print("  error:", type(e).__name__, e)
