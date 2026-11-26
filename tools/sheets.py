#!/usr/bin/env python3
"""Nadia's Google Sheet <-> data/site.json.

  python3 tools/sheets.py template OUT.xlsx   # workbook built from the current site.json (needs openpyxl)
  python3 tools/sheets.py sync [--csv DIR]    # read the published CSVs (or DIR/<Tab>.csv), validate, merge

The sheet owns: the timetable (Horario), the call hours (Llamadas), the texts of the existing
classes (Clases) and the contact details (Estudio). Everything else stays in site.json.

sync is all-or-nothing: one bad row and nothing is written, so the site keeps its last good
data. Exit codes: 0 = nothing changed, 1 = invalid sheet or download error, 2 = site.json updated.
"""
import csv
import io
import json
import os
import re
import sys
import unicodedata
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data/site.json")
CONFIG = os.path.join(ROOT, "data/sheets.json")
TABS = ["Clases", "Horario", "Llamadas", "Estudio"]

TYPES = {"Baile": "dance", "Fitness": "fit"}
STUDIO = [  # (row label, site.json key, hint shown in the sheet)
    ("Teléfono", "phone", "Como se lee: 654 691 336"),
    ("WhatsApp", "whatsapp", "Con el 34 delante y sin espacios: 34654691336"),
    ("Mensaje de WhatsApp", "whatsappText", "Texto que aparece ya escrito al abrir WhatsApp"),
    ("Calle", "street", ""),
    ("Código postal", "postalCode", "Cinco cifras"),
    ("Localidad", "locality", ""),
    ("Instagram", "instagram", "Enlace completo, empieza por https://www.instagram.com/"),
    ("Facebook", "facebook", "Enlace completo, empieza por https://www.facebook.com/"),
]
MAX_DESC = 600


def load():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- reading


def fetch(tab, csv_dir):
    if csv_dir:
        with open(os.path.join(csv_dir, tab + ".csv"), encoding="utf-8-sig") as f:
            text = f.read()
    else:
        with open(CONFIG, encoding="utf-8") as f:
            url = json.load(f)["tabs"].get(tab, "")
        if not url:
            raise SystemExit(f"data/sheets.json: falta el enlace CSV de la pestaña {tab}")
        with urllib.request.urlopen(url, timeout=30) as r:
            text = r.read().decode("utf-8-sig")
        if text.lstrip().startswith("<"):
            raise SystemExit(f"{tab}: Google ha devuelto una página, no un CSV (¿la hoja sigue publicada?)")
    rows = [[c.strip() for c in r] for r in csv.reader(io.StringIO(text))]
    if not rows:
        raise SystemExit(f"{tab}: la pestaña está vacía")
    head = rows[0]
    return [(i, dict(zip(head, r + [""] * (len(head) - len(r))))) for i, r in enumerate(rows[1:], 2)
            if any(r[:len(head)]) and any(v for k, v in zip(head, r) if k != "Revisión")]


def hhmm(value):
    """'9:30', '09:30', '09:30:00', '9.30', '9h30' -> '9:30' (the site's format). None if not a time."""
    m = re.fullmatch(r"(\d{1,2})\s*[:.hH]\s*(\d{2})(?::\d{2})?", value)
    if not m:
        return None
    h, mi = int(m[1]), int(m[2])
    return f"{h}:{mi:02d}" if h < 24 and mi < 60 else None


def minutes(t):
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


def sync(csv_dir=None):
    if not csv_dir and not os.path.exists(CONFIG):
        print("Sin configurar: falta data/sheets.json con los enlaces CSV de la hoja.")
        return 0
    D = load()
    errors = []
    days = {norm(d): i for i, d in enumerate(D["days"])}
    tabs = {t: fetch(t, csv_dir) for t in TABS}

    def err(tab, row, msg):
        errors.append(f"{tab}, fila {row}: {msg}")

    # Clases: only the classes that already exist (a new one needs a photo and a group, done by hand)
    by_id = {c["id"]: c for c in D["classes"]}
    seen, names, classes = set(), {}, {}
    for row, r in tabs["Clases"]:
        cid, name = r.get("Código", ""), r.get("Nombre", "")
        if cid not in by_id:
            err("Clases", row, f"«{name or cid}» es una clase nueva o le falta el código; las clases nuevas las añade Victor (foto y grupo)")
            continue
        if cid in seen:
            err("Clases", row, f"el código {cid} está repetido")
            continue
        seen.add(cid)
        tipo = r.get("Tipo", "")
        desc = r.get("Descripción", "")
        for field, label in (("Nombre", "el nombre"), ("Qué es", "«Qué es»"), ("Para quién", "«Para quién»")):
            if not r.get(field, ""):
                err("Clases", row, f"falta {label}")
        if tipo not in TYPES:
            err("Clases", row, f"Tipo tiene que ser Baile o Fitness, no «{tipo}»")
        if not desc:
            err("Clases", row, "falta la descripción")
        elif len(desc) > MAX_DESC:
            err("Clases", row, f"la descripción tiene {len(desc)} caracteres; el máximo es {MAX_DESC}")
        for key in (norm(name), norm(r.get("Nombre corto", ""))):
            if key and names.get(key, cid) != cid:
                err("Clases", row, f"el nombre «{name}» ya lo usa otra clase")
            if key:
                names[key] = cid
        classes[cid] = {"name": name, "short": r.get("Nombre corto", ""), "type": TYPES.get(tipo),
                        "kind": r.get("Qué es", ""), "audience": r.get("Para quién", ""),
                        "instructor": r.get("Monitora", ""), "description": desc}
    for cid in by_id.keys() - seen:
        errors.append(f"Clases: falta la fila de «{by_id[cid]['name']}» (para quitar una clase, avisa a Victor)")

    # Horario
    sessions = []
    for row, r in tabs["Horario"]:
        day = days.get(norm(r.get("Día", "")))
        start, end = hhmm(r.get("Empieza", "")), hhmm(r.get("Termina", ""))
        cid = names.get(norm(r.get("Clase", "")))
        if day is None:
            err("Horario", row, f"el día «{r.get('Día', '')}» no vale (la web muestra de {D['days'][0]} a {D['days'][-1]})")
        if not start or not end:
            err("Horario", row, "las horas se escriben así: 17:30")
        elif minutes(end) <= minutes(start):
            err("Horario", row, f"termina ({end}) antes de empezar ({start})")
        if not cid:
            err("Horario", row, f"la clase «{r.get('Clase', '')}» no está en la pestaña Clases")
        sessions.append({"class": cid, "day": day, "start": start, "end": end,
                         "label": r.get("Grupo (opcional)", ""), "note": r.get("Nota (opcional)", "")})
    if not tabs["Horario"]:
        errors.append("Horario: está vacío; la web se quedaría sin horario")

    # Llamadas
    calls = []
    for row, r in tabs["Llamadas"]:
        day = days.get(norm(r.get("Día", "")))
        start, end = hhmm(r.get("Desde", "")), hhmm(r.get("Hasta", ""))
        if day is None:
            err("Llamadas", row, f"el día «{r.get('Día', '')}» no vale")
        if not start or not end:
            err("Llamadas", row, "las horas se escriben así: 9:00")
        elif minutes(end) <= minutes(start):
            err("Llamadas", row, f"«Hasta» ({end}) es antes que «Desde» ({start})")
        calls.append({"day": day, "from": start, "to": end})
    if calls and len({c["day"] for c in calls}) != len(calls):
        errors.append("Llamadas: hay un día repetido; pon un solo horario por día")

    # Estudio
    studio = {}
    values = {r.get("Dato", ""): r.get("Valor", "") for _, r in tabs["Estudio"]}
    for label, key, _ in STUDIO:
        v = values.get(label, "")
        if not v:
            errors.append(f"Estudio: falta «{label}»")
        studio[key] = v
    digits = re.sub(r"\D", "", studio["phone"])
    if studio["phone"] and len(digits) != 9:
        errors.append(f"Estudio: el teléfono «{studio['phone']}» no tiene 9 cifras")
    if studio["whatsapp"] and not re.fullmatch(r"34\d{9}", studio["whatsapp"]):
        errors.append("Estudio: WhatsApp va con 34 delante y sin espacios, por ejemplo 34654691336")
    if studio["postalCode"] and not re.fullmatch(r"\d{5}", studio["postalCode"]):
        errors.append("Estudio: el código postal son cinco cifras")
    m = re.fullmatch(r"https://(?:www\.)?instagram\.com/([A-Za-z0-9_.]+)/?", studio["instagram"])
    if studio["instagram"] and not m:
        errors.append("Estudio: el enlace de Instagram tiene que empezar por https://www.instagram.com/")
    if studio["facebook"] and not studio["facebook"].startswith("https://www.facebook.com/"):
        errors.append("Estudio: el enlace de Facebook tiene que empezar por https://www.facebook.com/")

    if errors:
        print("La hoja tiene errores; la web se queda como estaba:", *errors, sep="\n  - ", file=sys.stderr)
        return 1

    # merge: only the keys the sheet owns
    for cid, new in classes.items():
        c = by_id[cid]
        for k in ("name", "type", "kind", "audience", "description"):
            c[k] = new[k]
        c["summary"] = new["description"]
        for k in ("short", "instructor"):
            if new[k]:
                c[k] = new[k]
            else:
                c.pop(k, None)
    D["classes"].sort(key=lambda c: [r.get("Código") for _, r in tabs["Clases"]].index(c["id"]))
    D["sessions"] = sessions
    D["callHours"] = calls
    D["studio"].update(studio)
    D["studio"]["phoneIntl"] = "+34" + digits
    D["studio"]["instagramHandle"] = "@" + m[1]

    out = json.dumps(D, ensure_ascii=False, indent=1) + "\n"
    with open(DATA, encoding="utf-8") as f:
        if f.read() == out:
            print("Sin cambios.")
            return 0
    with open(DATA, "w", encoding="utf-8") as f:
        f.write(out)
    print("data/site.json actualizado desde la hoja.")
    return 2


# ---------------------------------------------------------------- template


README = [
    ("title", "Contenido de la web · Nadia Fitness Dance Studio"),
    ("", "Lo que cambies aquí sale en nadiafitnessdance.es en una hora, más o menos. No hace falta avisar a nadie."),
    ("h", "Cómo se usa"),
    ("", "•  Escribe solo en las celdas amarillas. Las grises no se tocan."),
    ("", "•  La columna «Revisión» te dice si una fila está bien: ✔ en verde, o ✖ en rojo con lo que falla."),
    ("", "•  Si hay alguna fila en rojo, no se publica ningún cambio hasta que la corrijas. La web sigue como estaba: no la puedes romper."),
    ("", "•  Para quitar una hora del horario, borra esa fila entera."),
    ("h", "Pestañas"),
    ("", "•  Horario: una fila por cada hora de clase de la semana. La clase se elige en el desplegable."),
    ("", "•  Clases: el nombre y la descripción de cada clase. Para añadir o quitar una clase, avisa a Victor (necesita foto y grupo)."),
    ("", "•  Llamadas: cuándo cogéis el teléfono. Una fila por día."),
    ("", "•  Estudio: teléfono, dirección y redes. Casi nunca cambia."),
    ("h", "Ejemplo: el grupo intermedio 2 pasa del lunes al martes"),
    ("", "1.  En Horario, busca la fila «Lunes · Grupos de baile nivel intermedio · Grupo intermedio 2»."),
    ("", "2.  Cambia el Día a «Martes» y, si cambia, la hora."),
    ("", "3.  Mira la columna Revisión: si está en verde, listo."),
]


def template(path):
    from datetime import time
    from openpyxl import Workbook
    from openpyxl.formatting.rule import FormulaRule
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    D = load()
    S = D["studio"]
    N = 200  # editable rows per tab
    font, bold = Font(name="Arial", size=11), Font(name="Arial", size=11, bold=True)
    yellow = PatternFill("solid", fgColor="FFF6CC")
    grey = PatternFill("solid", fgColor="E8E8E8")
    ok, bad = PatternFill("solid", fgColor="D9EAD3"), PatternFill("solid", fgColor="F4CCCC")
    wrap = Alignment(wrap_text=True, vertical="top")

    wb = Workbook()
    ws = wb.active
    ws.title = "Léeme"
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 110
    for i, (kind, text) in enumerate(README, 2):
        c = ws.cell(i, 2, text)
        c.font = Font(name="Arial", size=16 if kind == "title" else 11, bold=bool(kind))
        c.alignment = Alignment(wrap_text=True)

    def sheet(title, headers, widths, rows, inputs, review):
        ws = wb.create_sheet(title)
        ws.freeze_panes = "A2"
        for j, (h, w) in enumerate(zip(headers, widths), 1):
            ws.cell(1, j, h).font = bold
            ws.column_dimensions[chr(64 + j)].width = w
        for i in range(2, N + 2):
            r = rows[i - 2] if i - 2 < len(rows) else [None] * (len(headers) - 1)
            for j, v in enumerate(r, 1):
                c = ws.cell(i, j, v)
                c.font, c.alignment = font, wrap
                c.fill = yellow if j in inputs else grey
                if isinstance(v, time):
                    c.number_format = "h:mm"
            if review:
                c = ws.cell(i, len(headers), review(i))
                c.font, c.alignment = font, wrap
        col = chr(64 + len(headers))
        rng = f"{col}2:{col}{N + 1}"
        if review:
            ws.conditional_formatting.add(rng, FormulaRule(formula=[f'LEFT({col}2,1)="✔"'], fill=ok))
            ws.conditional_formatting.add(rng, FormulaRule(formula=[f'LEFT({col}2,1)="✖"'], fill=bad))
        return ws

    def t(s):
        h, m = s.split(":")
        return time(int(h), int(m))

    last = N + 1
    tipo = {v: k for k, v in TYPES.items()}
    cl = sheet("Clases", ["Código", "Nombre", "Nombre corto", "Tipo", "Qué es", "Para quién", "Monitora", "Descripción", "Revisión"],
               [18, 34, 16, 10, 22, 20, 14, 70, 30],
               [[c["id"], c["name"], c.get("short", ""), tipo[c["type"]], c["kind"], c["audience"], c.get("instructor", ""), c["description"]]
                for c in D["classes"]], inputs={2, 3, 4, 5, 6, 7, 8},
               review=lambda i: (f'=IF(COUNTA(A{i}:H{i})=0,"",IF(A{i}="","✖ Clase nueva: avisa a Victor",'
                                 f'IF(OR(B{i}="",D{i}="",E{i}="",F{i}="",H{i}=""),"✖ Faltan datos",'
                                 f'IF(COUNTIF($B$2:$B${last},B{i})>1,"✖ Nombre repetido",'
                                 f'IF(LEN(H{i})>{MAX_DESC},"✖ Descripción demasiado larga","✔")))))'))
    hr = sheet("Horario", ["Día", "Empieza", "Termina", "Clase", "Grupo (opcional)", "Nota (opcional)", "Revisión"],
               [12, 10, 10, 38, 22, 26, 30],
               [[D["days"][s["day"]], t(s["start"]), t(s["end"]), next(c["name"] for c in D["classes"] if c["id"] == s["class"]),
                 s["label"], s["note"]] for s in D["sessions"]], inputs={1, 2, 3, 4, 5, 6},
               review=lambda i: (f'=IF(COUNTA(A{i}:F{i})=0,"",IF(OR(A{i}="",B{i}="",C{i}="",D{i}=""),"✖ Faltan datos",'
                                 f'IF(COUNTIF(Listas!$A$2:$A$8,A{i})=0,"✖ Ese día no vale",'
                                 f'IF(NOT(ISNUMBER(B{i})*ISNUMBER(C{i})),"✖ La hora se escribe así: 17:30",'
                                 f'IF(C{i}<=B{i},"✖ Termina antes de empezar",'
                                 f'IF(COUNTIF(Clases!$B$2:$B${last},D{i})=0,"✖ Esa clase no está en Clases","✔"))))))'))
    ll = sheet("Llamadas", ["Día", "Desde", "Hasta", "Revisión"], [12, 10, 10, 30],
               [[D["days"][c["day"]], t(c["from"]), t(c["to"])] for c in D["callHours"]], inputs={1, 2, 3},
               review=lambda i: (f'=IF(COUNTA(A{i}:C{i})=0,"",IF(OR(A{i}="",B{i}="",C{i}=""),"✖ Faltan datos",'
                                 f'IF(COUNTIF(Listas!$A$2:$A$8,A{i})=0,"✖ Ese día no vale",'
                                 f'IF(NOT(ISNUMBER(B{i})*ISNUMBER(C{i})),"✖ La hora se escribe así: 9:00",'
                                 f'IF(C{i}<=B{i},"✖ «Hasta» es antes que «Desde»",'
                                 f'IF(COUNTIF($A$2:$A${last},A{i})>1,"✖ Día repetido","✔"))))))'))
    es = wb.create_sheet("Estudio")
    for j, (h, w) in enumerate(zip(["Dato", "Valor", "Cómo escribirlo"], [22, 60, 50]), 1):
        es.cell(1, j, h).font = bold
        es.column_dimensions[chr(64 + j)].width = w
    for i, (label, key, hint) in enumerate(STUDIO, 2):
        for j, (v, fill) in enumerate(((label, grey), (S[key], yellow), (hint, grey)), 1):
            c = es.cell(i, j, v)
            c.font, c.fill, c.alignment = font, fill, wrap
            if j == 2:
                c.number_format = "@"  # keep 34654691336 and 29793 as text

    li = wb.create_sheet("Listas")
    li.sheet_state = "hidden"
    li["A1"], li["B1"] = "Días", "Tipo"
    for i, d in enumerate(D["days"], 2):
        li.cell(i, 1, d)
    for i, k in enumerate(TYPES, 2):
        li.cell(i, 2, k)

    def dv(ws, formula, rng, msg, kind="list"):
        v = DataValidation(type=kind, formula1=formula, allow_blank=True, showErrorMessage=True, error=msg)
        ws.add_data_validation(v)
        v.add(rng)

    dv(cl, f"=Listas!$B$2:$B${1 + len(TYPES)}", f"D2:D{last}", "Elige Baile o Fitness")
    dv(hr, f"=Listas!$A$2:$A${1 + len(D['days'])}", f"A2:A{last}", "Elige un día de la lista")
    dv(hr, f"=Clases!$B$2:$B${last}", f"D2:D{last}", "Elige una clase de la pestaña Clases")
    dv(ll, f"=Listas!$A$2:$A${1 + len(D['days'])}", f"A2:A{last}", "Elige un día de la lista")
    for ws_, rng in ((hr, f"B2:C{last}"), (ll, f"B2:C{last}")):
        v = DataValidation(type="time", operator="between", formula1="0", formula2="0.999988", allow_blank=True,
                           showErrorMessage=True, error="Escribe la hora así: 17:30")
        ws_.add_data_validation(v)
        v.add(rng)
    wb.save(path)
    print(f"{path}: {len(D['classes'])} clases, {len(D['sessions'])} horas de clase, {len(D['callHours'])} días de llamadas")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["template"] and len(args) == 2:
        template(args[1])
    elif args[:1] == ["sync"]:
        sys.exit(sync(args[args.index("--csv") + 1] if "--csv" in args else None))
    else:
        sys.exit(__doc__)
