"""Offline check of the pack's caption code in Lua 5.1 (the game's), against Spoken's own source.

    .venv/Scripts/python tools/test_captions.py                    # Spoken from vendor/spoken-wow
    .venv/Scripts/python tools/test_captions.py --spoken "<AddOns>"  # an installed Spoken

Hebrew.lua reaches into Spoken's internals, so after a Spoken update run this against the new
Spoken. It first checks that what Hebrew.lua uses is still in Spoken's source, then runs
build/dist/SpokenCommunity_ivrit's Hebrew.lua with Spoken's real Addon:ClipFont and the rest of
Spoken stood in for: a line from this pack gets its Hebrew text, font and rtl flag, another pack's
does not; a caption line is turned around once, keeps its highlight colour on the right letters,
and goes back to left-aligned for a non-Hebrew clip; a font string whose first try at the Hebrew
face failed still ends up with it; the subtitle's English name and title keep the game's face;
and with a piece of Spoken missing, or an error mid-session, the captions turn off and say so once.
"""
import argparse
import pathlib
import re
import sys

import lupa.lua51 as lupa

HERE = pathlib.Path(__file__).resolve().parent.parent
MOD = HERE / "build" / "dist" / "SpokenCommunity_ivrit"
HEBREW = r"Interface\AddOns\SpokenCommunity_ivrit\fonts\hebrew.ttf"
QUEST = r"Fonts\FRIZQT__.TTF"

ap = argparse.ArgumentParser()
ap.add_argument("--spoken", type=pathlib.Path, default=HERE / "vendor" / "spoken-wow" / "addons",
                help="the folder holding Spoken and Spoken_Quests")
ADDONS = ap.parse_args().spoken

failures = []


def check(name, got, want):
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


# 0. What Hebrew.lua uses is still in Spoken's source.
def source(rel):
    return (ADDONS / rel).read_text(encoding="utf-8")


core, subtitle = source("Spoken/Core.lua"), source("Spoken/UI/Subtitle.lua")
transcript, player = source("Spoken/UI/Transcript.lua"), source("Spoken_Quests/Player.lua")
clip_font = re.search(r"^function Addon:ClipFont\(fontString, clip\)\n.*?^end\n", core, re.M | re.S)
check("Spoken has Addon:ClipFont(fontString, clip)", bool(clip_font), True)
clip_font = clip_font.group(0) if clip_font else ""
CONTRACT = [
    ("ClipFont keeps spokenOwnFace", clip_font, r"\.spokenOwnFace\b"),
    ("ClipFont keeps spokenClipFace", clip_font, r"\.spokenClipFace\b"),
    ("ClipFont keeps spokenClipWant", clip_font, r"\.spokenClipWant\b"),
    ("ClipFont reads clip.present.font", clip_font, r"clip\.present\.font"),
    ("Core.lua runs in SpokenEnv", core, r"^setfenv\(1, SpokenEnv\)"),
    ("Subtitle is a SpokenEnv table", subtitle, r"^Subtitle = "),
    ("Subtitle:Reveal", subtitle, r"^function Subtitle:Reveal\("),
    ("Subtitle keeps self.lines", subtitle, r"self\.lines = "),
    ("Subtitle keeps self.measure", subtitle, r"self\.measure = "),
    ("Subtitle keeps self.clip", subtitle, r"self\.clip(, [\w.]+)* = "),
    ("Subtitle refonts title, label, lines with ClipFont", subtitle, r"Addon:ClipFont\(line, self\.clip\)"),
    ("Transcript is a SpokenEnv table", transcript, r"^Transcript = "),
    ("Transcript:Render", transcript, r"^function Transcript:Render\("),
    ("Transcript keeps self.labels", transcript, r"self\.labels\b"),
    ("Transcript keeps self.clip", transcript, r"self\.clip\b"),
    ("Spoken_Quests' Player:Prepare(soundData)", player, r"^function Player:Prepare\(soundData\)"),
    ("Prepare builds soundData.present", player, r"soundData\.present = \{"),
]
for name, text, pattern in CONTRACT:
    check(f"Spoken source: {name}", bool(re.search(pattern, text, re.M)), True)

# The rest of Spoken, stood in for. `missing` leaves one piece out.
STUBS = r"""
SpokenCommunity_ivrit = {}
FAIL_NEXT = {}      -- path -> true: the next SetFont of that face fails, as a client may
PRINTED = {}
function print(...) local t = {} for i = 1, select("#", ...) do t[i] = tostring(select(i, ...)) end PRINTED[#PRINTED + 1] = table.concat(t, " ") end
function hooksecurefunc(t, name, hook)
  local orig = t[name]
  t[name] = function(...) local r = { orig(...) }; hook(...); return unpack(r) end
end
function format(...) return string.format(...) end
SlashCmdList = {}
function FontString()
  local fs = { text = "", justify = "LEFT", face = "Fonts\\FRIZQT__.TTF", size = 16, flags = "" }
  function fs:SetText(t) self.text = t end
  function fs:GetText() return self.text end
  function fs:SetJustifyH(j) self.justify = j end
  function fs:GetFont() return self.face, self.size, self.flags end
  function fs:GetStringWidth() return 0 end
  function fs:IsShown() return true end
  function fs:GetAlpha() return 1 end
  function fs:SetFont(path, size, flags)
    if FAIL_NEXT[path] then FAIL_NEXT[path] = nil; return false end
    self.face, self.size, self.flags = path, size, flags; return true
  end
  return fs
end
function CreateFont() return FontString() end
UIParent = { CreateFontString = function() return FontString() end }
VoiceOver = { Player = { Prepare = function(self, soundData) soundData.present = { header = "x" } end } }
SpokenEnv = {
  Addon = {},
  Transcript = { labels = { FontString(), FontString() } },
  Subtitle = { lines = { FontString() }, measure = FontString(), title = FontString(), label = FontString() },
}
function SpokenEnv.Transcript:Render() for i, l in ipairs(self.labels) do l:SetText(self.want[i] or "") end end
-- Layout as Subtitle.lua has it: the words' face, then the clip's over it.
function SpokenEnv.Subtitle:Layout()
  for _, line in ipairs(self.lines) do line:SetFont("Fonts\\FRIZQT__.TTF", 16, ""); SpokenEnv.Addon:ClipFont(line, self.clip) end
end
function SpokenEnv.Subtitle:Reveal() self.lines[1]:SetText(self.want) end
"""


def runtime(missing=None):
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(STUBS)
    lua.execute("local Addon = SpokenEnv.Addon\n" + clip_font)
    if missing:
        lua.execute(missing)
    lua.execute("SPOKEN_CLIPFONT = SpokenEnv.Addon.ClipFont")
    for f in ("generated/hebrew_text.lua", "Hebrew.lua"):
        lua.execute((MOD / f).read_text(encoding="utf-8"))
    return lua, lua.globals()


lua, g = runtime()
texts = g.SpokenCommunity_ivrit.HebrewText
stem = next(iter(k for k in texts.keys() if str(k).endswith("-accept")))


def our_line(g):
    sd = lua.table_from({"module": g.SpokenCommunity_ivrit, "fileName": stem})
    g.VoiceOver.Player.Prepare(g.VoiceOver.Player, sd)
    return sd


# 1. Our line gets text, font and rtl; another pack's does not.
sd = our_line(g)
check("transcript", sd.present.transcript, texts[stem])
check("font", sd.present.font, HEBREW)
check("rtl", sd.present.rtl, True)
other = lua.table_from({"module": lua.table_from({}), "fileName": stem})
g.VoiceOver.Player.Prepare(g.VoiceOver.Player, other)
check("other pack untouched", other.present.transcript, None)

# 2. Transcript: flipped once, colours kept, right-aligned, Hebrew face; Render again keeps it.
t = g.SpokenEnv.Transcript
t.clip = sd
t.want = lua.table_from(["שלום |cffffd100הרפתקן|r!", "(אבג)"])
t.Render(t)
label1, label2 = t.labels[1], t.labels[2]
check("visual line", label1.text, "!|cffffd100ןקתפרה|r םולש")
check("mirrored brackets", label2.text, "(גבא)")
check("justify", label1.justify, "RIGHT")
check("transcript face", label1.face, HEBREW)
t.Render(t)
check("re-render", label1.text, "!|cffffd100ןקתפרה|r םולש")

# 3. A non-Hebrew clip: text as Spoken set it, left-aligned, and the game's face back through ClipFont.
other.present.rtl = None
t.clip = other
t.want = lua.table_from(["Hello there"])
t.Render(t)
check("english text", label1.text, "Hello there")
check("english justify", label1.justify, "LEFT")
g.SpokenEnv.Addon.ClipFont(g.SpokenEnv.Addon, label1, other)
check("english face back", label1.face, QUEST)

# 4. Subtitle: the first try at the Hebrew face fails (Spoken alone would stay on the game face
#    from then on); the line still ends up Hebrew, and stays so on the next layout.
s = g.SpokenEnv.Subtitle
s.clip = sd
g.FAIL_NEXT[HEBREW] = True
s.Layout(s)
s.want = "שלו"
s.Reveal(s)
check("subtitle face after a failed try", s.lines[1].face, HEBREW)
check("subtitle partial", s.lines[1].text, "ולש")
check("subtitle justify", s.lines[1].justify, "RIGHT")
s.Layout(s)
check("subtitle face next layout", s.lines[1].face, HEBREW)
addon = g.SpokenEnv.Addon
addon.ClipFont(addon, s.measure, sd)
check("subtitle measure face", s.measure.face, HEBREW)

# 4b. The speaker's name and the quest title above a Hebrew line are English: the game's face,
#     also for one a session already gave the Hebrew face.
addon.ClipFont(addon, s.title, sd)
check("subtitle title face", s.title.face, QUEST)
s.label.spokenOwnFace, s.label.spokenClipFace, s.label.spokenClipWant = QUEST, HEBREW, HEBREW
s.label.face = HEBREW
addon.ClipFont(addon, s.label, sd)
check("subtitle label face back", s.label.face, QUEST)

# 5. The diagnostic command runs, and nothing so far turned the captions off.
g.SlashCmdList.SPOKENHEBREW()
check("captions on", [str(p) for p in g.PRINTED.values() if "captions: on" in str(p)] != [], True)
check("nothing turned off", [str(p) for p in g.PRINTED.values() if "are off" in str(p)], [])

# 6. An error mid-session: the captions turn off once, say so once, and Spoken takes over.
broken = g.FontString()
lua.execute("function BREAK(fs) fs.GetText = function() error('boom') end end")
g.BREAK(broken)
t.labels[1] = broken
t.clip = sd
t.want = lua.table_from(["שלום"])
t.Render(t)
t.Render(t)
said = [str(p) for p in g.PRINTED.values() if "are off" in str(p)]
check("error turns captions off, said once", len(said), 1)
check("error is named", "Transcript.Render" in (said[0] if said else ""), True)
check("no Hebrew text after the error", our_line(g).present.transcript, None)
check("flipped lines go back to the left", s.lines[1].justify, "LEFT")
s.title.face = QUEST
addon.ClipFont(addon, s.title, sd)
check("ClipFont is Spoken's after the error", s.title.face, HEBREW)

# 7. A Spoken without one of the pieces: nothing installed, said once, Spoken's text stays.
lua2, g2 = runtime(missing="SpokenEnv.Subtitle.Reveal = nil")
said = [str(p) for p in g2.PRINTED.values() if "are off" in str(p)]
check("missing piece said once", len(said), 1)
check("missing piece named", "Subtitle.Reveal" in (said[0] if said else ""), True)
sd2 = lua2.table_from({"module": g2.SpokenCommunity_ivrit, "fileName": stem})
g2.VoiceOver.Player.Prepare(g2.VoiceOver.Player, sd2)
check("missing piece: no Hebrew text", sd2.present.transcript, None)
check("missing piece: ClipFont left alone", lua2.eval("SpokenEnv.Addon.ClipFont == SPOKEN_CLIPFONT"), True)

# 8. No Latin letters or niqqud left in any caption.
bad = [k for k, v in texts.items() if any("a" <= ch.lower() <= "z" or "֑" <= ch <= "ׇ" for ch in v)]
check("captions clean", bad[:5], [])

print(f"Spoken from {ADDONS}; {len(list(texts.keys()))} captions; "
      + ("all checks passed" if not failures else "FAILED:\n  " + "\n  ".join(failures)))
sys.exit(1 if failures else 0)
