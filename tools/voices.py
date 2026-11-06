"""Make (or find) one ElevenLabs voice per race-gender, and the narrator.

    python tools/voices.py

Clones are made from the game's own NPC clips for one voice set per race-gender (greeting,
farewell, vendor and pissed clips from wago.tools, 0.5 s apart), as Spoken's English clones
are. A voice that already exists under its name is reused, so re-running costs nothing.
Writes voices/voices.json: race-gender -> voice id.
"""
import html
import json
import re
import subprocess
import urllib.parse
import urllib.request

from common import HERE, api_key, call, load_json, multipart, save_json

# race-gender -> the game voice set it is cloned from (sound/creature/<set>npc/). A list is tried in
# order: ElevenLabs refuses some clones ("requires verification"), and the next set stands in.
SETS = {
    "human-male": "humanmaleofficial", "human-female": "humanfemalestandard",
    "dwarf-male": "dwarfmalestandard", "dwarf-female": "dwarffemalematernal",
    "gnome-male": "gnomemalestandard", "gnome-female": "gnomefemalestandard",
    "nightelf-male": ["nightelfmalestandard", "nightelfmaleofficial", "nightelfmalewarrior"], "nightelf-female": "nightelffemalestandard",
    "orc-male": "orcmalestandard", "orc-female": "orcfemalestandard",
    "troll-male": "trollmalestandard", "troll-female": "trollfemalestandard",
    "tauren-male": "taurenmalewarrior", "tauren-female": "taurenfemalestandard",
    "scourge-male": "undeadmalestandard", "scourge-female": "undeadfemalestandard",
    "goblin-male": ["goblinmalegruff", "goblinmalezany", "goblinmaleguard"],
    "goblin-female": "goblinfemalezany",
}
# Clones the samples kit already made, named after Spoken's slot names.
EXISTING = {
    "human-male": "WoW human-male-official (clone)", "human-female": "WoW human-female-standard (clone)",
    "dwarf-male": "WoW dwarf-male-standard (clone)", "nightelf-female": "WoW nightelf-female-standard (clone)",
    "orc-male": "WoW orc-male-standard (clone)", "troll-male": "WoW troll-male-standard (clone)",
    "tauren-female": "WoW tauren-female-standard (clone)",
}
NARRATOR = {
    "name": "Hebrew narrator (HE)",
    "description": "A calm, mature male narrator in his fifties, speaking Hebrew with a native Israeli accent. "
                   "Warm, clear, slightly deep storyteller voice, like an audiobook reader of a fantasy saga. "
                   "Measured pace, neutral and trustworthy. Studio quality.",
    "text": "על לוח המודעות תלויה הודעה ישנה. היא מבקשת מכל הרפתקן אמיץ לעזור לתושבי הכפר, "
            "ומבטיחה פרס הוגן למי שישיב את הסחורה הגנובה לבעליה.",
}
ORDER = ["greet", "farewell", "vendor", "pissed"]


def wago_files(folder):
    """(fdid, filename) for every .ogg in sound/creature/<folder>/."""
    out = []
    for page in range(1, 4):
        url = "https://wago.tools/files?" + urllib.parse.urlencode({"search": f"sound/creature/{folder}/", "page": page})
        text = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode()
        files = json.loads(html.unescape(re.search(r'data-page="([^"]+)"', text).group(1)))["props"]["files"]
        # A page past the last comes back as a bare (empty) list rather than a paginated object.
        data = files["data"] if isinstance(files, dict) else files
        out += [(f["fdid"], f["filename"]) for f in data
                if f["filename"].startswith(f"sound/creature/{folder}/") and f["filename"].endswith(".ogg")]
        if not isinstance(files, dict) or page >= files.get("last_page", 1):
            break
    return sorted(set(out), key=lambda f: f[1])


def source(rg, voice_set):
    """voices/sources/<race-gender>.mp3, built from the set's clips if missing."""
    out = HERE / "voices" / "sources" / f"{rg}.mp3"
    if out.exists():
        return out
    clips = HERE / "voices" / "clips" / voice_set
    clips.mkdir(parents=True, exist_ok=True)
    for fdid, name in wago_files(f"{voice_set}npc"):
        dest = clips / name.rsplit("/", 1)[1]
        if not dest.exists():
            dest.write_bytes(urllib.request.urlopen(urllib.request.Request(
                f"https://wago.tools/api/casc/{fdid}", headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read())
    files = sorted(clips.glob("*.ogg"), key=lambda f: (next((i for i, k in enumerate(ORDER) if k in f.name), 9), f.name))
    if not files:
        raise RuntimeError(f"no clips found for {voice_set}")
    args, flt = [], []
    for i, f in enumerate(files):
        args += ["-i", str(f)]
        flt.append(f"[{i}:a]aresample=44100,aformat=channel_layouts=mono,apad=pad_dur=0.5[a{i}]")
    flt.append("".join(f"[a{i}]" for i in range(len(files))) + f"concat=n={len(files)}:v=0:a=1[out]")
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args, "-filter_complex", ";".join(flt),
                    "-map", "[out]", "-b:a", "128k", str(out)], check=True)
    return out


def usable(key, vid):
    """False when ElevenLabs will not speak with the voice (it asks for voice verification)."""
    try:
        call(key, "POST", f"/v1/text-to-speech/{vid}?output_format=mp3_22050_32",
             {"text": "שלום.", "model_id": "eleven_v4", "language_code": "he"})
        return True
    except RuntimeError as e:
        if "requires verification" in str(e) or "captcha" in str(e):
            return False
        raise


def narrator(key, have):
    if NARRATOR["name"] in have:
        return have[NARRATOR["name"]]
    previews = json.loads(call(key, "POST", "/v1/text-to-voice/design", {
        "voice_description": NARRATOR["description"], "model_id": "eleven_ttv_v3", "text": NARRATOR["text"],
    }))["previews"]
    made = json.loads(call(key, "POST", "/v1/text-to-voice", {
        "voice_name": NARRATOR["name"], "voice_description": NARRATOR["description"],
        "generated_voice_id": previews[0]["generated_voice_id"],
    }))
    return made["voice_id"]


def main():
    key = api_key()
    have = {v["name"]: v["voice_id"] for v in json.loads(call(key, "GET", "/v1/voices"))["voices"]}
    ids = load_json(HERE / "voices" / "voices.json", {})
    for rg, sets in SETS.items():
        sets = [sets] if isinstance(sets, str) else sets
        for i, voice_set in enumerate(sets):
            # The first set keeps the plain name; a stand-in names its set.
            name = EXISTING.get(rg) if i == 0 and rg in EXISTING else                 f"WoW {rg} (HE pack)" if i == 0 else f"WoW {rg} {voice_set} (HE pack)"
            if name in have:
                vid = have[name]
            else:
                body, ctype = multipart({
                    "name": name,
                    "description": f"Instant clone of World of Warcraft's {voice_set} NPC voice set. Hebrew pack for Spoken.",
                    "remove_background_noise": "false",
                }, [("files", source(f"{rg}-{voice_set}" if i else rg, voice_set))])
                vid = json.loads(call(key, "POST", "/v1/voices/add", body, ctype))["voice_id"]
                have[name] = vid
            if usable(key, vid):
                ids[rg] = vid
                print(f"{rg:16} {name}")
                break
            print(f"{rg:16} {name} is blocked by ElevenLabs verification, trying the next set")
        else:
            print(f"{rg:16} NO USABLE VOICE")
    ids["narrator-male"] = narrator(key, have)
    print(f"{'narrator-male':16} {NARRATOR['name']}")
    save_json(HERE / "voices" / "voices.json", ids)


main()
