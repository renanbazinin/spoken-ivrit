"""Install the Hebrew pack into the local WoW Forever, and teach the installed Spoken the language.

    python tools/install_local.py            # patch Spoken + copy the pack
    python tools/install_local.py --undo     # restore Spoken's files, remove the pack

Spoken 3.8.x does not know Hebrew (heIL) yet. This adds one line to each list of languages it
keeps, the same lines Spoken added for Polish (upstream commit e7a1a957), after backing each
file up as <file>.before-heIL. A Spoken update replaces those files, so run this again after one
(until Spoken ships heIL itself). Then in game: /sp -> Language -> Voice Language: עברית / Hebrew.
"""
import argparse
import pathlib
import shutil

from common import HERE

ADDONS = pathlib.Path(r"C:\Program Files (x86)\World of Warcraft\_forever_\Interface\AddOns")
MODULE = "SpokenCommunity_ivrit"
# file -> (the Polish line to find, the Hebrew line to add after it)
PATCHES = {
    "Spoken_Quests/Language.lua": (
        '{ code = "plPL", name = "Polish", native = "Polski", client = false },',
        '{ code = "heIL", name = "Hebrew", native = "עברית", client = false },'),
    "Spoken_Readables/Language.lua": (
        '{ code = "plPL", name = "Polish", native = "Polski", client = false },',
        '{ code = "heIL", name = "Hebrew", native = "עברית", client = false },'),
    "Spoken/UI/Options.lua": (
        '{ code = "plPL", native = "Polski", english = "Polish" },',
        '{ code = "heIL", native = "עברית", english = "Hebrew", script = "hebrew" },'),
}


def patch():
    for rel, (anchor, line) in PATCHES.items():
        path = ADDONS / rel
        if not path.exists():
            print(f"skip {rel}: not installed")
            continue
        text = path.read_text(encoding="utf-8")
        if line in text:
            print(f"ok   {rel}: already knows heIL")
            continue
        if anchor not in text:
            print(f"WARN {rel}: Polish line not found; Spoken changed, patch by hand")
            continue
        backup = path.with_name(path.name + ".before-heIL")
        if not backup.exists():
            shutil.copyfile(path, backup)
        i = text.index(anchor)
        indent = text[text.rfind("\n", 0, i) + 1:i]
        path.write_text(text.replace(anchor, f"{anchor}\n{indent}{line}", 1), encoding="utf-8")
        print(f"done {rel}")


def install():
    src = HERE / "build" / "dist" / MODULE
    if not src.exists():
        raise SystemExit("build the pack first: python tools/build_pack.py --version ...")
    dest = ADDONS / MODULE
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    print(f"installed {dest}")


def undo():
    for rel in PATCHES:
        path = ADDONS / rel
        backup = path.with_name(path.name + ".before-heIL")
        if backup.exists():
            shutil.copyfile(backup, path)
            backup.unlink()
            print(f"restored {rel}")
    if (ADDONS / MODULE).exists():
        shutil.rmtree(ADDONS / MODULE)
        print(f"removed {MODULE}")


ap = argparse.ArgumentParser()
ap.add_argument("--undo", action="store_true")
if ap.parse_args().undo:
    undo()
else:
    patch()
    install()
