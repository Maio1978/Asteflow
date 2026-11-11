"""Aste Flow — ricostruisce la pagina pubblica dalle aste scaricate dal PVP.
Uso: python3 -I aggiorna.py CARTELLA_BLOCCHI OMI_DB TEMPLATE CARTELLA_USCITA
CARTELLA_BLOCCHI: file con i blocchi '#N#...' restituiti da scarica.js (anche dentro i file tool-results JSON).
Scrive CARTELLA_USCITA/aste-italia.html e CARTELLA_USCITA/italia/<regione>.json"""
import json, re, sys, os, sqlite3, datetime, glob
blk_dir, omi_db, tpl, out = sys.argv[1:5]
AG = json.load(open(sys.argv[6], encoding="utf-8")) if len(sys.argv) > 6 and os.path.exists(sys.argv[6]) else []
PERIZIE = json.load(open(sys.argv[5], encoding="utf-8")) if len(sys.argv) > 5 and os.path.exists(sys.argv[5]) else {}
NUMERI = {"una": 1, "due": 2, "tre": 3, "quattro": 4, "cinque": 5}
CENTRO = (41.9028, 12.4964)
def testo_blocco(raw):
    s = raw
    for _ in range(3):
        s = s.strip()
        m = re.match(r"^#(\d+)#", s)
        if m: return int(m.group(1)), s[m.end():]
        try: v = json.loads(s)
        except Exception:
            try: v, _ = json.JSONDecoder().raw_decode(s)
            except Exception: return None
        if isinstance(v, list) and v and isinstance(v[0], dict) and "text" in v[0]: v = v[0]["text"]
        if not isinstance(v, str): return None
        s = v
    return None
parts = {}
for f in glob.glob(os.path.join(blk_dir, "*")):
    r = testo_blocco(open(f, encoding="utf-8").read())
    if r: parts[r[0]] = r[1]
n = max(parts) + 1 if parts else 0
missing = [i for i in range(n) if i not in parts]
if missing or not n: sys.exit(f"Blocchi mancanti: {missing or 'nessun blocco'}")
rows = [r for i in range(n) for r in json.loads(parts[i])]
print("righe", len(rows))
REG = {"Piemonte":"Torino|Vercelli|Novara|Cuneo|Asti|Alessandria|Biella|Verbano-Cusio-Ossola","Valle d'Aosta":"Aosta|Valle d'Aosta","Lombardia":"Milano|Bergamo|Brescia|Como|Cremona|Lecco|Lodi|Mantova|Monza e della Brianza|Monza Brianza|Pavia|Sondrio|Varese",
"Trentino-Alto Adige":"Trento|Bolzano","Veneto":"Venezia|Belluno|Padova|Rovigo|Treviso|Verona|Vicenza","Friuli-Venezia Giulia":"Trieste|Gorizia|Pordenone|Udine","Liguria":"Genova|Imperia|La Spezia|Savona",
"Emilia-Romagna":"Bologna|Ferrara|Forlì-Cesena|Forli'-Cesena|Modena|Parma|Piacenza|Ravenna|Reggio nell'Emilia|Reggio Emilia|Rimini","Toscana":"Firenze|Arezzo|Grosseto|Livorno|Lucca|Massa-Carrara|Massa Carrara|Pisa|Pistoia|Prato|Siena",
"Umbria":"Perugia|Terni","Marche":"Ancona|Ascoli Piceno|Fermo|Macerata|Pesaro e Urbino|Pesaro Urbino","Lazio":"Roma|Frosinone|Latina|Rieti|Viterbo","Abruzzo":"L'Aquila|Chieti|Pescara|Teramo","Molise":"Campobasso|Isernia",
"Campania":"Napoli|Avellino|Benevento|Caserta|Salerno","Puglia":"Bari|Barletta-Andria-Trani|Brindisi|Foggia|Lecce|Taranto","Basilicata":"Potenza|Matera","Calabria":"Catanzaro|Cosenza|Crotone|Reggio di Calabria|Reggio Calabria|Vibo Valentia",
"Sicilia":"Palermo|Agrigento|Caltanissetta|Catania|Enna|Messina|Ragusa|Siracusa|Trapani","Sardegna":"Cagliari|Nuoro|Oristano|Sassari|Sud Sardegna|Carbonia-Iglesias|Medio Campidano|Ogliastra|Olbia-Tempio"}
P2R = {p.lower(): r for r, s in REG.items() for p in s.split("|")}
OCC = {"OCCUP": "Occupato", "LIBER": "Libero", "OCCST": "Occupato senza titolo", "INCOR": "In liberazione"}
def zona_roma(lat, lon, via):
    if not lat: return "Roma"
    if "ostia" in (via or "").lower() or lon < 12.36: return "Ostia e litorale"
    dlat, dlon = lat - CENTRO[0], (lon - CENTRO[1]) * 0.75
    if abs(dlat) >= abs(dlon): return "Roma nord" if dlat > 0 else "Roma sud"
    return "Roma est" if dlon > 0 else "Roma ovest"
NUMW={'una':1,'un':1,'due':2,'tre':3,'quattro':4,'cinque':5,'sei':6,'sette':7,'otto':8}
W=r'(\d+|una|un|due|tre|quattro|cinque|sei|sette|otto)'
def _n(s): return int(s) if s.isdigit() else NUMW[s]
def camere(t):
    t=(t or '').lower()
    m=re.search(W+r'\s+(?:camere|camera|stanze da letto|stanza da letto|camerette)\b',t)
    if m:
        v=_n(m.group(1)); return v if 1<=v<=8 else None
    if re.search(r'\bcamer(?:a|etta)\b|\bstanza da letto\b',t): return 1
    return None
def superficie(t):
    t=(t or '').lower().replace('²','2')
    for p in [r'(\d{2,3}(?:[.,]\d+)?)\s*(?:mq|m2|m\.q\.|metri quadr|mt\.?q)',
              r'(?:mq|m2|m\.q\.)\.?\s*(?:di\s*|circa\s*|commerciali\s*|lordi\s*|:)*\s*(\d{2,3}(?:[.,]\d+)?)',
              r'superficie[^.\d]{0,40}?(\d{2,3}(?:[.,]\d+)?)\s*(?:mq|m2|metri)']:
        m=re.search(p,t)
        if m:
            v=float(m.group(1).replace(',','.'))
            if 20<=v<=600: return v
    return None
def vani(t):
    t=(t or '').lower()
    m=re.search(r'(\d{1,2}(?:[.,]5)?)\s*vani\b',t) or re.search(r'\bvani\s*(?:catastali\s*)?(\d{1,2}(?:[.,]5)?)\b',t)
    if m:
        v=float(m.group(1).replace(',','.')); return v if 1<=v<=20 else None
    m=re.search(W+r'\s+(?:locali|vani)\b',t)
    if m:
        v=_n(m.group(1)); return v if 1<=v<=15 else None
    m=re.search(r'\b(mono|bi|tri|quadri|penta)locale',t)
    if m: return {'mono':1,'bi':2,'tri':3,'quadri':4,'penta':5}[m.group(1)]
    return None
def camere_mq(testo):
    return camere(testo), superficie(testo)
def in_ring(x, y, ring):
    inside = False; j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]; xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: inside = not inside
        j = i
    return inside
db = sqlite3.connect(omi_db); cc = {}
def comuni(nome):
    k = nome.upper()
    if k not in cc: cc[k] = [x[0] for x in db.execute("SELECT DISTINCT comune_amm FROM zone WHERE upper(comune)=?", (k,))]
    return cc[k]
def _civ(rows):
    return next((x for x in rows if x[0] == "Abitazioni civili"), None) or next((x for x in rows if "bitazion" in x[0]), None)
def omi_info(citta, lat, lon):
    """Valori OMI (€/mq) della zona esatta se ci sono le coordinate, altrimenti l'intervallo del comune."""
    if not citta: return None
    cs = comuni(citta)
    if lat and lon:
        for c in cs:
            for zona, gj in db.execute("SELECT zona, geojson FROM perimetri WHERE comune_amm=?", (c,)):
                for p in json.loads(gj):
                    if any(in_ring(lon, lat, o) for o in p["outer"]) and not any(in_ring(lon, lat, h) for h in p["inner"]):
                        v = _civ(db.execute("SELECT tipologia, compr_min, compr_max, loc_min, loc_max FROM valori WHERE comune_amm=? AND zona=?", (c, zona)).fetchall())
                        if v and v[1]:
                            d = db.execute("SELECT descrizione FROM zone WHERE comune_amm=? AND zona=?", (c, zona)).fetchone()
                            return dict(t="z", z=zona, zd=(d[0] if d else "") or "", a=v[1], b=v[2], la=v[3], lb=v[4])
                        break
    for c in cs:
        rows = db.execute("SELECT zona, tipologia, compr_min, compr_max, loc_min, loc_max FROM valori WHERE comune_amm=?", (c,)).fetchall()
        by = {}
        for z, *r in rows: by.setdefault(z, []).append(r)
        vals = [v for v in (_civ(r) for r in by.values()) if v and v[1]]
        if vals:
            if len(vals) == 1:
                z = next(iter(by)); d = db.execute("SELECT descrizione FROM zone WHERE comune_amm=? AND zona=?", (c, z)).fetchone()
                return dict(t="z", z=z, zd=(d[0] if d else "") or "", a=vals[0][1], b=vals[0][2], la=vals[0][3], lb=vals[0][4])
            return dict(t="c", a=min(v[1] for v in vals), b=max(v[2] for v in vals), la=min(v[3] or 0 for v in vals) or None, lb=max(v[4] or 0 for v in vals) or None)
    return None

import unicodedata
GEN = r"^(via|viale|v\.?le|v\.|piazza|p\.zza|piazzale|largo|corso|c\.so|vicolo|strada|contrada|c\.da|localita|loc\.|frazione|fraz\.|borgo|traversa|vico|circonvallazione)\s+"
def _nz(s):
    s = unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", s).strip()
def chiave(via, citta):
    v = _nz(via.split(",")[0] if "," in (via or "") and not re.match(r"^\D+,\s*\d", via or "") else via)
    full = _nz(via)
    civ = re.search(r"\b(\d{1,4})\b", full)
    nome = re.sub(GEN, "", _nz((via or "").split(",")[0]))
    nome = re.sub(r"\b\d+\w*\b", "", nome).strip()
    nome = " ".join(w for w in nome.split() if len(w) > 2)
    return (_nz(citta), nome, civ.group(1) if civ else "")
AGIDX = {}
for r in AG:
    ind, citta = r[1], r[2]
    via = (ind or "").split(",")
    k = chiave(",".join(via[:2]) if len(via) > 1 and re.match(r"^\s*\d", via[1]) else via[0], citta)
    AGIDX.setdefault(k, []).append(r)
    AGIDX.setdefault(k[:2] + ("",), []).append(r)
DISP_AG = {"LIBERO": "LIBER", "OCCUPATO": "OCCUP", "IN CORSO DI LIBERAZIONE": "INCOR", "OCCUPATO SENZA TITOLO": "OCCST", "OCCUPATO DAL DEBITORE": "OCCUP", "OCCUPATO DA TERZI CON TITOLO": "OCCUP", "OCCUPATO DA TERZI SENZA TITOLO": "OCCST"}
def cerca_ag(via, citta):
    k = chiave(via, citta)
    if not k[1]: return None
    c = AGIDX.get(k) or []
    if len(c) == 1: return c[0]
    if not c and k[2] == "":
        c = AGIDX.get(k[:2] + ("",)) or []
        if len(c) == 1: return c[0]
    return None
oggi = datetime.date.today(); lim = (oggi + datetime.timedelta(days=2)).isoformat()
by, seen = {}, set()
for (i, trib, via, citta, prov, lat, lon, base, minima, data, disp, desc) in rows:
    if i in seen or (data or "") < lim: continue
    seen.add(i)
    reg = P2R.get((prov or "").strip().lower())
    if not reg: continue
    cam, mq = camere_mq(desc); nv = vani(desc)
    oi = omi_info(citta, lat, lon)
    o = round((oi['a'] + oi['b']) / 2 * mq, -3) if (oi and oi['t'] == 'z' and mq) else None
    zona = zona_roma(lat, lon, via) if (citta or "").lower() == "roma" else (citta or "").title()
    ag = cerca_ag(via, citta) if AG else None
    if ag:
        if ag[7] and 20 <= ag[7] <= 1000: mq = ag[7]
        if ag[8] and nv is None: nv = ag[8]
        if ag[11] and disp in ("", "NON_SPECIFICATA"): disp = DISP_AG.get(ag[11].upper(), disp)
        o = round((oi['a'] + oi['b']) / 2 * mq, -3) if (oi and oi['t'] == 'z' and mq) else None
    pz = PERIZIE.get(str(i))
    if pz:
        mq = pz.get("q", mq); cam = pz.get("k", cam); nv = pz.get("n", nv)
        if pz.get("s"): disp = {"Libero": "LIBER", "Occupato": "OCCUP", "Occupato senza titolo": "OCCST", "In liberazione": "INCOR"}.get(pz["s"], disp)
        o = round((oi['a'] + oi['b']) / 2 * mq, -3) if (oi and oi['t'] == 'z' and mq) else None
    rec = dict(i=i, v=(via or "").strip(" ,"), c=(citta or "").title(), z=zona, p=(prov or "").strip(), t=(trib or "").title(), m=minima, b=base, d=data, k=cam, n=nv, q=mq, o=o, w=oi, s=OCC.get(disp, ""), x=desc)
    if ag:
        rec.update(ag=1, bg=ag[9], pi=ag[10], pf=ag[15])
    if pz:
        rec.update(pz=1, bg=pz.get("bg"), pi=pz.get("pi"))
    by.setdefault(reg, []).append(rec)
os.makedirs(os.path.join(out, "italia"), exist_ok=True); idx = {}
for reg, L in by.items():
    L.sort(key=lambda a: a["d"]); slug = re.sub(r"[^a-z]+", "-", reg.lower()).strip("-")
    json.dump(L, open(os.path.join(out, "italia", slug + ".json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    idx[reg] = dict(f=f"italia/{slug}.json", n=len(L), nc=sum(1 for a in L if a["q"] and (a["k"] is not None or a["n"] is not None)), prov=sorted({a["p"] for a in L}))
h = open(tpl, encoding="utf-8").read().replace("%%IDX_JSON%%", json.dumps(idx, ensure_ascii=False)).replace("%%DATA%%", oggi.strftime("%d/%m/%Y"))
open(os.path.join(out, "aste-italia.html"), "w", encoding="utf-8").write(h)
# versione per il sito asteflow.it (GitHub Pages): documento completo
head = '<!doctype html>\n<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="description" content="Case all\'asta in tutta Italia: offerte minime, valori OMI e consulenza per l\'asta e il mutuo.">\n'
k = h.index("</style>") + 8
open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(head + h[:k] + "\n</head><body>\n" + h[k:] + "\n</body></html>\n")
print("aste", sum(v["n"] for v in idx.values()), "| regioni", len(idx), "| con OMI", sum(1 for L in by.values() for a in L if a["o"]))
