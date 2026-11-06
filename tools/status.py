"""Where the pack stands: units translated and recorded, what is left, and the credits it needs.

    python tools/status.py
"""
from common import HERE, load_json, pack_files, units

TURBO = 0.22      # credits per Hebrew character, Eleven v4 Turbo
HEBREW = 0.78     # Hebrew length / English length, as measured on this pack


def main():
    index = {u["unit"]: u for u in load_json(HERE / "lines" / "index.json", {"units": []})["units"]}
    rows = {"translated": [0, 0], "recorded": [0, 0], "to translate": [0, 0], "to record": [0, 0]}
    he_left = 0
    for unit in units():
        en = [c for c in load_json(HERE / "lines" / f"{unit}.en.json", []) if pack_files(c)]
        he = load_json(HERE / "lines" / f"{unit}.he.json", {}).get("lines", {})
        for c in en:
            if c["id"] in he:
                rows["translated"][0] += 1
                if (HERE / "audio" / f"{c['id']}.mp3").exists():
                    rows["recorded"][0] += 1
                else:
                    rows["to record"][0] += 1
                    he_left += len(he[c["id"]])
            else:
                rows["to translate"][0] += 1
                rows["to translate"][1] += len(c["en"])
                he_left += len(c["en"]) * HEBREW
    done_units = sum(1 for u in units() if (HERE / "lines" / f"{u}.he.json").exists())
    print(f"units: {done_units} of {len(units())} translated")
    print(f"recordings: {rows['recorded'][0]:,} done, {rows['to record'][0]:,} translated and waiting, "
          f"{rows['to translate'][0]:,} still to translate ({rows['to translate'][1]:,} English characters)")
    credits = he_left * TURBO
    print(f"left to record: ~{he_left:,.0f} Hebrew characters = ~{credits:,.0f} credits on Turbo "
          f"(~${he_left / 1000 * 0.04:,.0f} at the API's $0.04 per 1,000 characters)")


main()
