-- Hebrew captions for this pack's lines, in Spoken's subtitle and in its player window.
--
-- Spoken shows the client's own (English) text under a line, unless the clip brings its own:
-- present.transcript is the text, present.font a face that has its glyphs (Spoken uses both
-- for scripts the game's font lacks). This file gives every line this pack plays its Hebrew
-- text and a Hebrew font.
--
-- The game draws text left to right and has no right-to-left layout. Spoken breaks the lines
-- itself (by measuring the words, which is the same either way round), so each line it draws is
-- turned around after it is set: characters in reverse order, highlight colours kept on their
-- letters, mirrored brackets, and the line aligned to the right. Typing-out then grows from the
-- right, as Hebrew is read.

local MODULE = SpokenCommunity_ivrit
-- Faces with Hebrew letters, tried in order; the first the client loads is used from then on.
local FONTS = {
    [[Interface\AddOns\SpokenCommunity_ivrit\fonts\hebrew.ttf]],
    [[Interface\AddOns\SpokenCommunity_ivrit\fonts\hebrew2.ttf]],
}
local FONT = FONTS[1]
local TEXT = MODULE and MODULE.HebrewText or {} -- generated\hebrew_text.lua

local function SameFace(a, b)
    if type(a) ~= "string" or type(b) ~= "string" then return false end
    return (a:lower():gsub("/", "\\")) == (b:lower():gsub("/", "\\"))
end

-- Loaded now, so the file is in by the time the first caption wants it.
local preload = CreateFont and CreateFont("SpokenHebrewCaptionFont")
if preload then
    for _, path in ipairs(FONTS) do preload:SetFont(path, 16, "") end
end

local working -- the face from FONTS the client drew with last

--- Put a Hebrew face on `fontString`, keeping its size and flags. Spoken's own Addon:ClipFont
--- would do it, but once a face fails on a font string it keeps the game's face there for good
--- (no glyphs: boxes); this tries again every time instead.
local function UseHebrewFont(fontString)
    if not fontString or not fontString.GetFont then return false end
    local face, size, flags = fontString:GetFont()
    if working and SameFace(face, working) then return true end
    -- The player's face, kept where Spoken's ClipFont looks for it: when this string's first clip
    -- is Hebrew, Spoken never saw its own face, and an English clip after would ask for none.
    if face and not SameFace(face, FONTS[1]) and not SameFace(face, FONTS[2]) then
        fontString.spokenOwnFace = face
    end
    size = size or 16
    for _, path in ipairs(working and { working, FONTS[1], FONTS[2] } or FONTS) do
        local ok = fontString:SetFont(path, size, flags or "")
        local now = fontString:GetFont()
        if ok ~= false and SameFace(now, path) then
            working = path
            -- What Spoken's ClipFont reads next time, so a later English clip gets its face back.
            fontString.spokenClipWant, fontString.spokenClipFace = FONT, now
            return true
        end
    end
    return false
end

local MIRROR = { ["("] = ")", [")"] = "(", ["["] = "]", ["]"] = "[", ["<"] = ">", [">"] = "<",
                 ["{"] = "}", ["}"] = "{", ["«"] = "»", ["»"] = "«" }

--- `text` in visual order: its characters reversed, with each one keeping the |c colour it had.
local function Visual(text)
    -- `count`, not #colors: an uncoloured letter leaves a nil in colors, and # of a table with
    -- holes is not its length.
    local chars, colors, color, count = {}, {}, nil, 0
    local i, n = 1, #text
    while i <= n do
        local c = text:sub(i, i)
        local nxt = text:sub(i + 1, i + 1)
        if c == "|" and nxt == "c" then
            color, i = text:sub(i, i + 9), i + 10
        elseif c == "|" and nxt == "r" then
            color, i = nil, i + 2
        else
            local len = 1
            if c == "|" and nxt == "|" then
                len = 2
            else
                local b = c:byte()
                len = b >= 240 and 4 or b >= 224 and 3 or b >= 192 and 2 or 1
            end
            count = count + 1
            chars[count], colors[count] = text:sub(i, i + len - 1), color
            i = i + len
        end
    end
    local out, current = {}, nil
    for k = count, 1, -1 do
        local col = colors[k]
        if col ~= current then
            if current then out[#out + 1] = "|r" end
            if col then out[#out + 1] = col end
            current = col
        end
        out[#out + 1] = MIRROR[chars[k]] or chars[k]
    end
    if current then out[#out + 1] = "|r" end
    return table.concat(out)
end

local function IsHebrew(clip)
    return clip and clip.present and clip.present.rtl
end

--- Turn a font string Spoken just set around, once: the text it holds is Spoken's (logical) only
--- when it differs from what this last put there.
local function Flip(fontString, rtl)
    if not fontString then return end
    if not rtl then
        if fontString.hebrewFlipped then
            fontString:SetJustifyH("LEFT")
            fontString.hebrewFlipped, fontString.hebrewShown = nil, nil
        end
        return
    end
    UseHebrewFont(fontString)
    local shown = fontString:GetText() or ""
    if shown ~= fontString.hebrewShown then
        shown = Visual(shown)
        fontString:SetText(shown)
        fontString.hebrewShown = shown
    end
    if not fontString.hebrewFlipped then
        fontString:SetJustifyH("RIGHT")
        fontString.hebrewFlipped = true
    end
end

-- 1. Each line this pack plays carries its Hebrew text and font.
if VoiceOver and VoiceOver.Player and VoiceOver.Player.Prepare then
    hooksecurefunc(VoiceOver.Player, "Prepare", function(_, soundData)
        if not soundData or not soundData.present then return end
        local ours = soundData.module == MODULE
            or (soundData.filePath and soundData.filePath:find("SpokenCommunity_ivrit", 1, true))
        if not ours then return end
        local stem = (soundData.fileName or ""):gsub("^[mf]%-", "")
        local text = TEXT[stem]
        if not text then return end
        soundData.present.transcript = text
        soundData.present.font = working or FONT
        soundData.present.rtl = true
    end)
end

local env = SpokenEnv

-- 2. Every font string Spoken puts a Hebrew clip's words or names in gets a Hebrew face, every
-- time (see UseHebrewFont); other clips go through Spoken as before.
if env and env.Addon and env.Addon.ClipFont then
    local ClipFont = env.Addon.ClipFont
    env.Addon.ClipFont = function(self, fontString, clip, ...)
        if IsHebrew(clip) and UseHebrewFont(fontString) then return end
        return ClipFont(self, fontString, clip, ...)
    end
end

-- 3. Spoken's two displays, turned right-to-left while one of those lines is up.
if env and env.Transcript and env.Transcript.Render then
    hooksecurefunc(env.Transcript, "Render", function(self)
        local rtl = IsHebrew(self.clip)
        for _, label in ipairs(self.labels or {}) do Flip(label, rtl) end
    end)
end
if env and env.Subtitle and env.Subtitle.Reveal then
    hooksecurefunc(env.Subtitle, "Reveal", function(self)
        local rtl = IsHebrew(self.clip)
        for _, line in ipairs(self.lines or {}) do Flip(line, rtl) end
    end)
end

-- /spokenhe: what the captions are drawn with, for when they show boxes.
SLASH_SPOKENHEBREW1 = "/spokenhe"
SlashCmdList.SPOKENHEBREW = function()
    local function say(...) print("|cffb48cffSpoken Hebrew|r", ...) end
    local probe = UIParent:CreateFontString(nil, "OVERLAY")
    for i, path in ipairs(FONTS) do
        local ok = probe:SetFont(path, 16, "")
        say(format("font %d %s: %s", i, path:match("[^\\]+$"), (ok ~= false and SameFace(probe:GetFont(), path)) and "loads" or "FAILED"))
    end
    say("in use:", working or "none yet", "| captions:", (function() local n = 0 for _ in pairs(TEXT) do n = n + 1 end return n end)())
    local sub = env and env.Subtitle
    if sub then
        say("subtitle clip is Hebrew:", tostring(IsHebrew(sub.clip) and true or false))
        if sub.measure then say("subtitle measure:", (sub.measure:GetFont())) end
        for i, line in ipairs(sub.lines or {}) do say(format("subtitle line %d: %s", i, tostring((line:GetFont())))) end
    end
end
