# Usage: python3 -I arricchisci.py BASE_DIR(con italia/*.json) astegiudiziarie.json TEMPLATE OUT
# Applica le schede astegiudiziarie ai JSON già pubblicati (base PVP più recente).
import json, sys, os, re, glob, unicodedata, datetime
base, agf, tpl, out = sys.argv[1:5]
AG = json.load(open(agf, encoding="utf-8"))
GEN = r"^(via|viale|v\.?le|v\.|piazza|p\.zza|piazzale|largo|corso|c\.so|vicolo|strada|contrada|c\.da|localita|loc\.|frazione|fraz\.|borgo|traversa|vico|circonvallazione)\s+"
def _nz(s):
    s = unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", s).strip()
def chiave(via, citta):
    full = _nz(via); civ = re.search(r"\b(\d{1,4})\b", full)
    nome = re.sub(GEN, "", _nz((via or "").split(",")[0])); nome = re.sub(r"\b\d+\w*\b", "", nome).strip()
    nome = " ".join(w for w in nome.split() if len(w) > 2)
    return (_nz(citta), nome, civ.group(1) if civ else "")
AGIDX = {}
for r in AG:
    via = (r[1] or "").split(",")
    k = chiave(",".join(via[:2]) if len(via) > 1 and re.match(r"^\s*\d", via[1]) else via[0], r[2])
    AGIDX.setdefault(k, []).append(r); AGIDX.setdefault(k[:2] + ("",), []).append(r)
def cerca_ag(via, citta):
    k = chiave(via, citta)
    if not k[1]: return None
    c = AGIDX.get(k) or []
    if len(c) == 1: return c[0]
    if not c and k[2] == "":
        c = AGIDX.get(k[:2] + ("",)) or []
        if len(c) == 1: return c[0]
    return None
DISP = {"LIBERO": "Libero", "OCCUPATO": "Occupato", "IN CORSO DI LIBERAZIONE": "In liberazione", "OCCUPATO SENZA TITOLO": "Occupato senza titolo", "OCCUPATO DAL DEBITORE": "Occupato", "OCCUPATO DA TERZI CON TITOLO": "Occupato", "OCCUPATO DA TERZI SENZA TITOLO": "Occupato senza titolo"}
oggi = datetime.date.today(); lim = (oggi + datetime.timedelta(days=2)).isoformat()
os.makedirs(os.path.join(out, "italia"), exist_ok=True); idx = {}; nag = 0
for f in sorted(glob.glob(os.path.join(base, "italia", "*.json"))):
    L = [a for a in json.load(open(f, encoding="utf-8")) if (a.get("d") or "") >= lim]
    for a in L:
        if a.get("pz"): continue
        ag = cerca_ag(a.get("v"), a.get("c"))
        if not ag: continue
        nag += 1
        if ag[7] and 20 <= ag[7] <= 1000: a["q"] = ag[7]
        if ag[8] and a.get("n") is None: a["n"] = ag[8]
        if ag[11] and not a.get("s"): a["s"] = DISP.get(ag[11].upper(), a.get("s", ""))
        w = a.get("w")
        a["o"] = round((w["a"] + w["b"]) / 2 * a["q"], -3) if (w and w.get("t") == "z" and a.get("q")) else a.get("o")
        a.update(ag=1, bg=ag[9], pi=ag[10], pf=ag[15])
    slug = os.path.basename(f)[:-5]
    json.dump(L, open(os.path.join(out, "italia", slug + ".json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    reg = slug.replace("-", " ").title().replace("D Aosta", "d'Aosta").replace("Venezia Giulia", "Venezia Giulia")
    idx[slug] = (L, f"italia/{slug}.json")

src = open(os.path.join(base, "index.html"), encoding="utf-8").read()
j = src.index("IDX=") + 4; IDX = json.JSONDecoder().raw_decode(src[j:])[0]
new = {}
for reg, v in IDX.items():
    slug = v["f"][7:-5]
    if slug not in idx: continue
    L = idx[slug][0]
    new[reg] = dict(f=v["f"], n=len(L), nc=sum(1 for a in L if a.get("q") and (a.get("k") is not None or a.get("n") is not None)), prov=sorted({a["p"] for a in L}))
h = open(tpl, encoding="utf-8").read().replace("%%IDX_JSON%%", json.dumps(new, ensure_ascii=False)).replace("%%DATA%%", oggi.strftime("%d/%m/%Y"))
open(os.path.join(out, "aste-italia.html"), "w", encoding="utf-8").write(h)
head = '<!doctype html>\n<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="description" content="Case all\'asta in tutta Italia: offerte minime, valori OMI e consulenza per l\'asta e il mutuo.">\n'
k = h.index("</style>") + 8
open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(head + h[:k] + "\n</head><body>\n" + h[k:] + "\n</body></html>\n")
print("aste", sum(v["n"] for v in new.values()), "complete", sum(v["nc"] for v in new.values()), "da astegiudiziarie", nag)
