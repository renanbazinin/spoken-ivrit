"""Make the captions' font: Noto Sans Hebrew's letters plus Noto Sans's Latin, digits and punctuation.

    python tools/make_font.py        # fonts/SpokenHebrewSans-Regular.ttf

A WoW font string draws in one face, and Noto Sans Hebrew has only the Hebrew block: every
comma, period, quote and digit in a caption, and the English NPC name above it, drew as a box.
Both fonts are SIL OFL 1.1 without reserved font names, so they may be merged and shared.
The game lays text out without shaping, so the layout tables and the hinting are left out.
"""
import pathlib
import tempfile

from fontTools import subset
from fontTools.merge import Merger
from fontTools.ttLib import TTFont

HERE = pathlib.Path(__file__).resolve().parent.parent
FONTS = HERE / "fonts"
HEBREW = FONTS / "NotoSansHebrew-Regular.ttf"
LATIN = FONTS / "NotoSans-Regular.ttf"
OUT = FONTS / "SpokenHebrewSans-Regular.ttf"
FAMILY = "Spoken Hebrew Sans"

# What players' captions and NPC names use besides Hebrew: ASCII, Latin-1 and Latin Extended-A
# (names such as Thrall'jin or Mazen Mac'Nadir), dashes, quotes, the ellipsis and a few signs.
LATIN_RANGES = [(0x20, 0x7E), (0xA0, 0x17F), (0x2010, 0x2027), (0x2030, 0x203A), (0x20AC, 0x20AC),
                (0x2122, 0x2122)]


def stripped(path, unicodes, out):
    options = subset.Options()
    options.hinting = False
    options.layout_features = []
    options.drop_tables += ["GSUB", "GPOS", "GDEF", "gasp"]
    options.name_IDs = ["*"]
    options.notdef_outline = True
    font = TTFont(path)
    sub = subset.Subsetter(options)
    sub.populate(unicodes=unicodes)
    sub.subset(font)
    font.save(out)


def main():
    hebrew_cmap = TTFont(HEBREW).getBestCmap()
    latin = [cp for lo, hi in LATIN_RANGES for cp in range(lo, hi + 1)]
    with tempfile.TemporaryDirectory() as tmp:
        he, la = pathlib.Path(tmp) / "he.ttf", pathlib.Path(tmp) / "la.ttf"
        stripped(HEBREW, list(hebrew_cmap), he)
        # Hebrew first: a code point both fonts have (space, no-break space) keeps the Hebrew width.
        stripped(LATIN, [cp for cp in latin if cp not in hebrew_cmap], la)
        font = Merger().merge([str(he), str(la)])

    name = font["name"]
    copyright_ = " ".join(TTFont(p)["name"].getDebugName(0) for p in (HEBREW, LATIN))
    for nid, value in {0: copyright_, 1: FAMILY, 2: "Regular", 3: f"{FAMILY} Regular; merged",
                       4: f"{FAMILY} Regular", 6: FAMILY.replace(" ", "") + "-Regular",
                       16: FAMILY, 17: "Regular"}.items():
        name.setName(value, nid, 3, 1, 0x409)
        name.setName(value, nid, 1, 0, 0)
    for nid in (13, 14):
        value = TTFont(LATIN)["name"].getDebugName(nid)
        name.setName(value, nid, 3, 1, 0x409)
    font.save(OUT)
    cmap = font.getBestCmap()
    print(f"{OUT.name}: {len(cmap)} characters, {OUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
