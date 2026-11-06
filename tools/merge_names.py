"""Fold the translators' new names (lines/*.he.json "newNames") into glossary.json "names".

    python tools/merge_names.py

A name already in the glossary keeps its spelling; a name two units spelled differently is
reported and the glossary's (or the first unit's) spelling is kept, so the next units use one.
"""
import collections

from common import HERE, load_json, save_json, units


def main():
    glossary = load_json(HERE / "glossary.json")
    names = glossary.setdefault("names", {})
    seen = collections.defaultdict(dict)
    for unit in units():
        for en, he in load_json(HERE / "lines" / f"{unit}.he.json", {}).get("newNames", {}).items():
            seen[en.strip()][unit] = he.strip()
    added, clashes = 0, []
    for en, by_unit in seen.items():
        spellings = set(by_unit.values())
        if en in names or en in glossary.get("terms", {}):
            known = names.get(en) or glossary["terms"][en]
            if spellings - {known}:
                clashes.append((en, known, by_unit))
            continue
        if len(spellings) > 1:
            clashes.append((en, None, by_unit))
        names[en] = next(iter(by_unit.values()))
        added += 1
    save_json(HERE / "glossary.json", glossary)
    print(f"names: {len(names)} ({added} new)")
    for en, known, by_unit in clashes:
        print(f"  spelled differently: {en}: glossary {known!r}, units {by_unit}")


main()
