"""Starting-zone quest lines from Spoken's corpus, one entry per clip to record.

    python tools/extract.py <spoken-wow checkout>

A clip is one Hebrew recording: lines whose speaker voice (race-gender) and English text are the
same share it, and the pack gets a copy under every file name that needs it. Writes
lines/<zone>.en.json and prints the counts.

Voice is race-gender only (human-male, orc-female...): this pack uses one voice per race and
gender, not Spoken's flavours. The narrator (gameobjects, items) is its own voice.
"""
import collections
import gzip
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
ZONES = {
    "elwynn": 1429, "dunmorogh": 1426, "teldrassil": 1438,
    "durotar": 1411, "mulgore": 1412, "tirisfal": 1420,
}
SOURCES = ("accept", "complete", "followup")  # progress text is never voiced
FOLDER = {"accept": "quests", "complete": "quests", "followup": "followup"}


def race_gender(voice):
    parts = voice.split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else voice


def main():
    repo = pathlib.Path(sys.argv[1])
    comp = (repo / "addons/Spoken_Quests/Data/Compendium.lua").read_text(encoding="utf-8")
    zone_of = {}
    by_id = {v: k for k, v in ZONES.items()}
    for qid, zs in re.findall(r'\[(\d+)\] = \{ "(?:[^"\\]|\\.)*", zones = \{ ([\d, ]+) \}', comp):
        for z in zs.split(","):
            if int(z) in by_id:
                zone_of[int(qid)] = by_id[int(z)]
                break

    corpus = json.load(gzip.open(repo / "pipelines/quests/corpus/corpus.json.gz", "rt", encoding="utf-8"))
    clips = {}
    for line in corpus["lines"]:
        if line["source"] not in SOURCES or not line.get("generatable"):
            continue
        zone = zone_of.get(line.get("questId"))
        if zone is None:
            continue
        text = re.sub(r"[ \t]+", " ", line["text"]).strip()
        voice = race_gender(line["voice"])
        key = hashlib.sha1(f"{voice}\n{text}".encode()).hexdigest()[:12]
        clip = clips.setdefault(key, {
            "id": key, "zone": zone, "voice": voice, "speakerGender": line.get("gender"),
            "npc": line.get("npcName"), "quest": line.get("questTitle"), "en": text, "files": [],
        })
        clip["files"].append(f"{FOLDER[line['source']]}/{line['fileName']}")

    out = HERE / "lines"
    out.mkdir(exist_ok=True)
    per_zone = collections.defaultdict(list)
    for clip in clips.values():
        per_zone[clip["zone"]].append(clip)
    for zone in ZONES:
        items = sorted(per_zone[zone], key=lambda c: (c["quest"] or "", c["files"][0]))
        (out / f"{zone}.en.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{zone:11} clips={len(items):4} files={sum(len(c['files']) for c in items):4} "
              f"chars={sum(len(c['en']) for c in items):7,}")
    voices = collections.Counter(c["voice"] for c in clips.values())
    print("voices:", dict(voices.most_common()))


main()
