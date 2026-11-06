"""Make one spelling of a name win everywhere: replace other spellings in the Hebrew lines.

    python tools/respell.py            # apply SPELLINGS, print the clips that changed
    python tools/respell.py --dry-run

SPELLINGS maps an English name to (the spelling to keep, [spellings to replace]). The kept one is
also written into glossary.json "names", so later units use it. Clips whose text changed and that
already have audio are listed in build/respelled.txt, for:
    python tools/generate.py --force --ids $(cat build/respelled.txt)
"""
import argparse

from common import HERE, load_json, save_json, units

SPELLINGS = {
    "Bolvar": ("בּוֹלְבָר", ["בּוֹלְוָר"]),
    "Camp Taurajo": ("מחנה טָאוּרָאחוֹ", ["מחנה טָאוּרָאגְ'וֹ"]),
    "Taurajo": ("טָאוּרָאחוֹ", ["טָאוּרָאגְ'וֹ"]),
    "Deadmines": ("המכרות המתים", ["דֶּדְמַיינְס"]),
    "Sandfury": ("זעם-החול", ["סַנְדְפְיוּרִי"]),
    "Uther Lightbringer": ("אוּתֶ'ר מביא האור", ["אוּתֶ'ר לַייטְבְּרִינְגֶר"]),
    "Archmage Arugal": ("הארכי-קוסם אָרוּגָל", ["רב-הקוסמים אָרוּגָל"]),
    "Great Sundering": ("השבירה הגדולה", ["השבר הגדול"]),
    "Veiled Sea": ("הים המצועף", ["הים הרעול"]),
    "Wailing Caverns": ("מערות היללות", ["מערות היללה"]),
    "Mirage Raceway": ("מסלול מרוצי התעתועים", ["מסלול מרוצי התעתוע"]),
    "Razorfen Kraul": ("רֵייזוֹרְפֶן קְרוֹל", ["רֵייזוֹרְפֶן קְרָאוּל"]),
    "Wind Rider Master": ("אמן רוכבי רוח", ["אמן רוכבי הרוח"]),
    "love token": ("אסימון אהבה", ["פתק אהבה", "פתקי אהבה"]),
    "hearthstone": ("אבן האח", ["אבן אח"]),
    "gryphon master": ("מאלף הגריפונים", ["אמן הגְרִיפוֹנִים"]),
    "Guild Master": ("ראש הגילדות", ["אדון הגילדות"]),
    "The Bass and You": ("הלַבְרָק ואתה", ["האוקונון ואתה"]),
    # The capitals (2026-11-06)
    "Chillwind Camp": ("מחנה רוח הצינה", ["מחנה צִ'ילְוִינְד"]),
    "Un'Goro": ("אוּן-גוֹרוֹ", ["אוּן'גוֹרוֹ"]),
    "morrowgrain": ("דגן המחר", ["מוֹרוֹגְרֵיין"]),
    "Silverwing Sentinels": ("זקיפות כנף הכסף", ["זקיפות סִילְבֶרְוִינְג"]),
    "Silverwing Hold": ("מעוז כנף הכסף", ["מעוז סִילְבֶרְוִינְג", "מבצר כנף הכסף"]),
    "The Defilers": ("המחללים", ["המטמאים"]),
    "Commendation Officer": ("קצין ציונים לשבח", ["קצין הוקרה", "קצין ציון לשבח"]),
    "Commendation Officer (f)": ("קצינת ציונים לשבח", ["קצינת הוקרה", "קצינת ציון לשבח"]),
    "Commendation Signet": ("חותמת ציון לשבח", ["חותם הוקרה", "חותם ציון לשבח", "חותם הצטיינות"]),
    "Winter Veil": ("צעיף החורף", ["מעטה החורף"]),
    "Ahn'Qiraj": ("אָן'קִירָאג'", ["אָן'קִירָאז'", "אַן'קִירָאג'"]),
    # The Barrens (2026-11-06)
    "Stagnant Oasis": ("נווה המים העומדים", ["נווה המדבר העכור"]),
    "Barak Kodobane": ("בָּארָק קוֹדוֹבֵּיין", ["בָּרָק קוֹדוֹבֵּיין"]),
    "Heralath": ("הֶרָלָאת'", ["הֶרָלָת'"]),
    "Southsea Freebooters": ("שודדי ים הדרום", ["פיראטי ים-הדרום"]),
    # Levels 20-30 (2026-11-07)
    "Cragpool Lake": ("אגם קְרָאגְפּוּל", ["אגם קְרָגְפּוּל"]),
}


# Plain text fixes, applied the same way: mistakes a name change or a reused line spread.
FIXES = {
    "ההמכרות": "המכרות", "בהמכרות": "במכרות", "להמכרות": "למכרות", "כהמכרות": "כמכרות",
    "ההארכי-קוסם": "הארכי-קוסם", "להארכי-קוסם": "לארכי-קוסם", "בהארכי-קוסם": "בארכי-קוסם",
    "השבירה הגדולה ניפץ את המקדש והטביע אותו": "השבירה הגדולה ניפצה את המקדש והטביעה אותו",
    "טרולי הזעם-החול": "טרולי זעם-החול",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    changed, recorded = [], []
    for unit in units():
        path = HERE / "lines" / f"{unit}.he.json"
        data = load_json(path)
        if not data:
            continue
        dirty = False
        for cid, text in data["lines"].items():
            new = text
            for keep, others in SPELLINGS.values():
                for other in others:
                    # The kept spelling is set aside first: where a variant is part of it
                    # ("התעתוע" in "התעתועים"), replacing in place would grow it every run.
                    new = new.replace(keep, "\0").replace(other, keep).replace("\0", keep)
            for wrong, right in FIXES.items():
                new = new.replace(wrong, right)
            if new != text:
                data["lines"][cid] = new
                dirty = True
                changed.append((unit, cid))
                if (HERE / "audio" / f"{cid}.mp3").exists():
                    recorded.append(cid)
        if dirty and not args.dry_run:
            save_json(path, data)
    if not args.dry_run:
        glossary = load_json(HERE / "glossary.json")
        for en, (keep, _) in SPELLINGS.items():
            glossary.setdefault("names", {})[en] = keep
        save_json(HERE / "glossary.json", glossary)
        (HERE / "build").mkdir(exist_ok=True)
        (HERE / "build" / "respelled.txt").write_text(",".join(recorded), encoding="utf-8")
    by_unit = {}
    for unit, _ in changed:
        by_unit[unit] = by_unit.get(unit, 0) + 1
    print(f"lines changed: {len(changed)} {by_unit}; already recorded, to record again: {len(recorded)}")


main()
