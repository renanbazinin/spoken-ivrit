"""Offline check of the pack's caption code in Lua 5.1 (the game's), with Spoken stood in for.

    .venv/Scripts/python tools/test_captions.py

Loads build/dist/SpokenCommunity_ivrit's generated\\hebrew_text.lua and Hebrew.lua as the game
would (after Module.lua's global), with Spoken's Addon:ClipFont copied as it is in 3.8.3, then
checks: a line from this pack gets its Hebrew text, font and rtl flag, another pack's does not;
a caption line is turned around once, keeps its highlight colour on the right letters, and goes
back to left-aligned for a non-Hebrew clip; and a font string whose first try at the Hebrew face
failed still ends up with it (Spoken's ClipFont alone would keep the game's face there for good).
"""
import pathlib
import sys

import lupa.lua51 as lupa

HERE = pathlib.Path(__file__).resolve().parent.parent
MOD = HERE / "build" / "dist" / "SpokenCommunity_ivrit"

lua = lupa.LuaRuntime(unpack_returned_tuples=True)
lua.execute(r"""
SpokenCommunity_ivrit = {}
FAIL_NEXT = {}      -- path -> true: the next SetFont of that face fails, as a client may
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
  Subtitle = { lines = { FontString() }, measure = FontString() },
}
-- Spoken 3.8.3's Addon:ClipFont, as it is (Core.lua).
function SpokenEnv.Addon:ClipFont(fontString, clip)
  local face, size, flags = fontString:GetFont()
  if not face then return end
  if face ~= fontString.spokenClipFace then fontString.spokenOwnFace = face end
  local want = clip and clip.present and clip.present.font or fontString.spokenOwnFace
  if face == fontString.spokenClipFace and want == fontString.spokenClipWant then return end
  local asked = want
  if want ~= face and (fontString:SetFont(want, size, flags or "") == false or not fontString:GetFont()) then
    want = fontString.spokenOwnFace
    fontString:SetFont(want, size, flags or "")
  end
  fontString.spokenClipWant, fontString.spokenClipFace = asked, fontString:GetFont() or want
end
function SpokenEnv.Transcript:Render() for i, l in ipairs(self.labels) do l:SetText(self.want[i] or "") end end
-- Layout as Subtitle.lua has it: the words' face, then the clip's over it.
function SpokenEnv.Subtitle:Layout()
  for _, line in ipairs(self.lines) do line:SetFont("Fonts\\FRIZQT__.TTF", 16, ""); SpokenEnv.Addon:ClipFont(line, self.clip) end
end
function SpokenEnv.Subtitle:Reveal() self.lines[1]:SetText(self.want) end
""")
for f in ("generated/hebrew_text.lua", "Hebrew.lua"):
    lua.execute((MOD / f).read_text(encoding="utf-8"))

failures = []


def check(name, got, want):
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


g = lua.globals()
ARIAL = r"Interface\AddOns\SpokenCommunity_ivrit\fonts\hebrew.ttf"
QUEST = r"Fonts\FRIZQT__.TTF"
texts = g.SpokenCommunity_ivrit.HebrewText
stem = next(iter(k for k in texts.keys() if str(k).endswith("-accept")))

# 1. Our line gets text, font and rtl; another pack's does not.
sd = lua.table_from({"module": g.SpokenCommunity_ivrit, "fileName": stem})
g.VoiceOver.Player.Prepare(g.VoiceOver.Player, sd)
check("transcript", sd.present.transcript, texts[stem])
check("font", sd.present.font, ARIAL)
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
check("transcript face", label1.face, ARIAL)
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
g.FAIL_NEXT[ARIAL] = True
s.Layout(s)
s.want = "שלו"
s.Reveal(s)
check("subtitle face after a failed try", s.lines[1].face, ARIAL)
check("subtitle partial", s.lines[1].text, "ולש")
check("subtitle justify", s.lines[1].justify, "RIGHT")
s.Layout(s)
check("subtitle face next layout", s.lines[1].face, ARIAL)

# 5. The diagnostic command runs.
g.print = lambda *a: None
g.SlashCmdList.SPOKENHEBREW()

# 6. No Latin letters or niqqud left in any caption.
bad = [k for k, v in texts.items() if any("a" <= ch.lower() <= "z" or "֑" <= ch <= "ׇ" for ch in v)]
check("captions clean", bad[:5], [])

print(f"{len(list(texts.keys()))} captions; " + ("all checks passed" if not failures else "FAILED:\n  " + "\n  ".join(failures)))
sys.exit(1 if failures else 0)
