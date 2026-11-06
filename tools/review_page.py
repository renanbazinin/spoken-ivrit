"""review.html: every recorded line by zone and quest, to listen through and pick what to redo.

    python tools/review_page.py

Open review.html from this folder (it plays audio/<id>.mp3 next to it). Each line shows who says
it, the English, the Hebrew that was read, a player, and its id. Tick the lines that sound wrong;
the box at the top collects their ids for:  python tools/generate.py --ids <ids> --force
Lines much shorter or longer than their text suggests are flagged, since that is how a cut-off or
garbled take usually shows.
"""
import html
import json
import subprocess

from common import HERE, load_json, pack_files, units

NAMES = {"elwynn": "Elwynn Forest", "dunmorogh": "Dun Morogh", "teldrassil": "Teldrassil",
         "durotar": "Durotar", "mulgore": "Mulgore", "tirisfal": "Tirisfal Glades"}
CHARS_PER_SEC = 9.1


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0


def main():
    index = load_json(HERE / "lines" / "index.json", {"units": []})
    NAMES.update({u["unit"]: u["name"] for u in index["units"]})
    cache = load_json(HERE / "build" / "durations.json", {})
    sections, nav, flagged, recorded, total = [], [], 0, 0, 0
    for zone in units():
        en = load_json(HERE / "lines" / f"{zone}.en.json", [])
        he = load_json(HERE / "lines" / f"{zone}.he.json", {}).get("lines", {})
        if not he:  # not translated yet
            continue
        rows, quest = [], None
        for c in en:
            if not pack_files(c):
                continue
            total += 1
            mp3 = HERE / "audio" / f"{c['id']}.mp3"
            text = he.get(c["id"], "")
            heading = c.get("quest") or (c.get("npc") if c.get("kind") == "gossip" else "")
            if heading != quest:
                quest = heading
                rows.append(f'<h3>{html.escape(quest or "")}</h3>')
            flag = ""
            if mp3.exists():
                recorded += 1
                key = f"{c['id']}:{mp3.stat().st_mtime_ns}"
                if key not in cache:
                    cache[key] = duration(mp3)
                secs = cache[key]
                expected = max(len(text) / CHARS_PER_SEC, 1.0)
                if secs < expected * 0.55 or secs > expected * 1.8:
                    flagged += 1
                    flag = f'<span class="flag">⚠ {secs:.1f}s for ~{expected:.0f}s of text</span>'
                player = f'<audio controls preload="none" src="audio/{c["id"]}.mp3"></audio>'
            else:
                player = '<span class="missing">not recorded yet</span>'
            rows.append(
                f'<div class="line" data-id="{c["id"]}"><div class="meta"><label><input type="checkbox"> redo</label> '
                f'<b>{html.escape(c["npc"] or "")}</b> <span>{c["voice"]}</span> <code>{c["id"]}</code> {flag}</div>'
                f'<p class="en">{html.escape(c["en"])}</p><p class="he" dir="rtl" lang="he">{html.escape(text)}</p>{player}</div>')
        name = NAMES.get(zone, zone)
        nav.append(f'<a href="#{zone}">{html.escape(name)}</a>')
        sections.append(f'<section id="{zone}"><h2>{html.escape(name)}</h2>{"".join(rows)}</section>')
    (HERE / "build").mkdir(exist_ok=True)
    (HERE / "build" / "durations.json").write_text(json.dumps(cache), encoding="utf-8")

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hebrew Pack Review</title><style>
:root {{ --bg:#f7f5f0; --card:#fff; --ink:#1d1b18; --muted:#6b655c; --line:#e3ddd2; --accent:#8a5a00; --warn:#b3261e; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#161512; --card:#1f1d19; --ink:#ece7de; --muted:#a39b8e; --line:#353129; --accent:#e0a640; --warn:#ff8a80; }} }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui,"Segoe UI",Arial,sans-serif; }}
main {{ max-width:900px; margin:0 auto; padding:16px 16px 80px; }}
header {{ position:sticky; top:0; background:var(--bg); padding:8px 0; border-bottom:1px solid var(--line); z-index:1; }}
nav a {{ margin-right:12px; color:var(--accent); }} textarea {{ width:100%; height:44px; font:12px monospace; }}
section {{ margin-top:16px; }} h3 {{ margin:18px 0 6px; font-size:15px; color:var(--accent); }}
.line {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:10px; margin:6px 0; }}
.meta {{ font-size:13px; color:var(--muted); }} .meta b {{ color:var(--ink); }} code {{ font-size:11px; }}
.en {{ color:var(--muted); font-size:13px; margin:4px 0; }} .he {{ font-size:17px; margin:4px 0 6px; font-family:Arial,sans-serif; }}
.flag {{ color:var(--warn); font-weight:600; }} .missing {{ color:var(--muted); font-style:italic; }} audio {{ height:32px; max-width:100%; }}
</style></head><body><main><header><b>Hebrew pack review</b> · {recorded} of {total} lines recorded · {flagged} flagged by length
<nav>{"".join(nav)}</nav>
<div>Lines marked redo (copy into <code>python tools/generate.py --force --ids …</code>):</div><textarea id="ids" readonly></textarea></header>
{"".join(sections)}
<script>
const box = document.getElementById("ids");
function refresh() {{ box.value = [...document.querySelectorAll(".line input:checked")].map(i => i.closest(".line").dataset.id).join(","); try {{ localStorage.setItem("redo", box.value); }} catch (e) {{}} }}
try {{ (localStorage.getItem("redo") || "").split(",").filter(Boolean).forEach(id => {{ const el = document.querySelector(`.line[data-id="${{id}}"] input`); if (el) el.checked = true; }}); }} catch (e) {{}}
document.addEventListener("change", e => {{ if (e.target.matches(".line input")) refresh(); }}); refresh();
</script></main></body></html>"""
    (HERE / "review.html").write_text(page, encoding="utf-8")
    print(f"review.html: {recorded}/{total} recorded, {flagged} flagged")


main()
