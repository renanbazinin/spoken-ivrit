"""Every quest and gossip line not yet in the pack, by zone, ready to translate and record.

    python tools/extract_all.py

Work is kept in units, lines/<unit>.en.json (+ <unit>.he.json once translated). The units already
there (the starting zones' quests) are left as they are, except that a new line whose voice and
text match one of their clips is added to that clip's files: it is recorded once and reused.

- Quests go to the zone the quest belongs to, from Spoken's Compendium (the quest log's zone, or
  where its giver stands). Quests filed under a class, a profession or a season go to 'other-quests'.
- Gossip goes to the zone its NPC stands in (its spawns, by the client's map rectangles, the
  smallest that holds the point). NPCs with no spawn go to 'other-gossip'.
- A unit over MAX clips is split into <unit>-2, -3, ... so one translator gets a manageable share.
- Elf races without a voice of their own (Skybourne, blood elves) speak with the night elf voices.

Writes lines/index.json: every unit in working order, with its name, kind, clip and character counts.
"""
import collections
import csv
import gzip
import hashlib
import json
import pathlib
import re

from common import HERE, load_json, save_json

MAX = 200
STARTERS = {1429: "elwynn", 1426: "dunmorogh", 1438: "teldrassil", 1411: "durotar", 1412: "mulgore", 1420: "tirisfal"}
CAPITALS = [1453, 1455, 1457, 1454, 1456, 1458]
FOLDER = {"accept": "quests", "complete": "quests", "followup": "followup", "gossip": "gossip"}
ALIAS = {"skybourneelf-male": "nightelf-male", "skybourneelf-female": "nightelf-female",
         "bloodelf-male": "nightelf-male", "bloodelf-female": "nightelf-female"}
REPO = HERE / "vendor" / "spoken-wow"


def voice_of(voice):
    rg = "-".join(voice.split("-")[:2])
    return ALIAS.get(rg, rg)


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def zone_names():
    z = (REPO / "addons/Spoken_Places/Data/enUS/Zones.lua").read_text(encoding="utf-8")
    return {int(a): b for a, b in re.findall(r'\[(\d+)\]\s*=\s*\{\s*name\s*=\s*"([^"]+)"', z)}


def rectangles():
    out = []
    for r in csv.DictReader(open(HERE / "data" / "UiMapAssignment.csv", encoding="utf-8")):
        x0, y0, x1, y1 = (float(r[k]) for k in ("Region_0", "Region_1", "Region_3", "Region_4"))
        out.append((int(r["MapID"]), min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), int(r["UiMapID"]),
                    abs(x1 - x0) * abs(y1 - y0)))
    return out


def main():
    names = zone_names()
    rects = rectangles()

    def zone_at(map_id, x, y):
        best = None
        for m, xa, xb, ya, yb, ui, area in rects:
            if m == map_id and xa <= x <= xb and ya <= y <= yb and (best is None or area < best[1]):
                best = (ui, area)
        return best and best[0]

    comp = (REPO / "addons/Spoken_Quests/Data/Compendium.lua").read_text(encoding="utf-8")
    quest_zone = {}
    for qid, zs in re.findall(r'\[(\d+)\] = \{ "(?:[^"\\]|\\.)*", zones = \{ ([\d, ]+) \}', comp):
        quest_zone[int(qid)] = int(zs.split(",")[0])

    # What the pack already has: every clip by id, and the unit file it lives in.
    existing, owner = {}, {}
    index = load_json(HERE / "lines" / "index.json", {"units": []})
    old_units = [u["unit"] for u in index["units"]] or list(STARTERS.values())
    for unit in old_units:
        for clip in load_json(HERE / "lines" / f"{unit}.en.json", []):
            existing[clip["id"]], owner[clip["id"]] = clip, unit

    corpus = json.load(gzip.open(REPO / "pipelines/quests/corpus/corpus.json.gz", "rt", encoding="utf-8"))
    spawns = corpus["spawns"]
    new = {}                                   # id -> clip, not in any unit yet
    bucket = collections.defaultdict(list)     # base unit -> ids, in corpus order
    touched = set()
    for line in corpus["lines"]:
        source = line["source"]
        if source not in FOLDER or not line.get("generatable"):
            continue
        text = re.sub(r"[ \t]+", " ", line["text"]).strip()
        voice = voice_of(line["voice"])
        cid = hashlib.sha1(f"{voice}\n{text}".encode()).hexdigest()[:12]
        rel = f"{FOLDER[source]}/{line['fileName']}"
        if cid in existing:
            if rel not in existing[cid]["files"]:
                existing[cid]["files"].append(rel)
                touched.add(owner[cid])
            continue
        if source == "gossip":
            pts = spawns.get(f"{line.get('npcType', 'creature')}:{line['npcId']}") or []
            zones = collections.Counter(z for z in (zone_at(p["map"], p["x"], p["y"]) for p in pts) if z)
            z = zones.most_common(1)[0][0] if zones else None
            base = (f"{STARTERS[z]}-gossip" if z in STARTERS else f"{slug(names.get(z, str(z)))}-gossip") \
                if z else "other-gossip"
        else:
            z = quest_zone.get(line.get("questId"))
            base = (f"{STARTERS[z]}-more" if z in STARTERS else slug(names.get(z, str(z)))) if z else "other-quests"
        rank = (0 if z in STARTERS else 1 if z in CAPITALS else 2 if z else 3, len(new))
        if cid in new:
            # A line said in several places is recorded with the place that is done first.
            clip = new[cid]
            if rel not in clip["files"]:
                clip["files"].append(rel)
            if rank[0] < clip["_rank"][0]:
                clip.update(zone=base, uiMap=z, _rank=rank)
            continue
        new[cid] = {"id": cid, "zone": base, "kind": "gossip" if source == "gossip" else "quest", "voice": voice,
                    "speakerGender": line.get("gender"), "npc": line.get("npcName"),
                    "quest": line.get("questTitle"), "en": text, "files": [rel], "uiMap": z, "_rank": rank}

    for cid, clip in new.items():
        bucket[clip.pop("_rank") and clip["zone"]].append(cid)

    for unit in touched:  # reuse: only the files lists of the existing units change
        save_json(HERE / "lines" / f"{unit}.en.json", [c for c in existing.values() if owner[c["id"]] == unit])

    # Units: female-player-only clips dropped (this pack has one version, the male one); big
    # units split; ordered starting-zone gossip, capitals, then the rest by size.
    def shipped(c):
        return any(not f.rsplit("/", 1)[1].startswith("f-") for f in c["files"])

    units = [u for u in index["units"]] or [
        {"unit": STARTERS[z], "name": names[z], "kind": "quest", "uiMap": z} for z in STARTERS]
    known = {u["unit"] for u in units}
    plan = []
    for base, ids in bucket.items():
        items = [new[i] for i in ids if shipped(new[i])]
        items.sort(key=lambda c: (c["quest"] or "", c["npc"] or "", c["files"][0]))
        parts = [items[i:i + MAX] for i in range(0, len(items), MAX)] or []
        for n, part in enumerate(parts, 1):
            unit = base if n == 1 else f"{base}-{n}"
            for c in part:
                c["zone"] = unit
            z = part[0]["uiMap"]
            name = names.get(z, "Other") if z else "Other"
            kind = part[0]["kind"]
            label = f"{name} ({'gossip' if kind == 'gossip' else 'quests'}{'' if n == 1 else f', part {n}'})"
            rank = (0 if z in STARTERS and kind == "gossip" else 1 if z in CAPITALS else 2 if z else 3)
            plan.append((rank, -len(part), unit, label, kind, z, part))
    plan.sort(key=lambda p: (p[0], p[2]))
    for rank, _, unit, label, kind, z, part in plan:
        if unit in known:
            continue
        save_json(HERE / "lines" / f"{unit}.en.json", part)
        units.append({"unit": unit, "name": label, "kind": kind, "uiMap": z})
    for u in units:
        clips = load_json(HERE / "lines" / f"{u['unit']}.en.json", [])
        u["clips"], u["chars"] = len(clips), sum(len(c["en"]) for c in clips)
        u["done"] = (HERE / "lines" / f"{u['unit']}.he.json").exists()
    save_json(HERE / "lines" / "index.json", {"units": units})

    todo = [u for u in units if not u["done"]]
    print(f"units: {len(units)} ({len(todo)} to translate) | new clips: {sum(u['clips'] for u in todo):,} "
          f"| English chars to translate: {sum(u['chars'] for u in todo):,} | reused files added to existing clips: "
          f"{len(touched)} unit(s)")
    for u in todo[:12]:
        print(f"  {u['unit']:28} {u['clips']:4} clips {u['chars']:7,} chars  {u['name']}")


main()
