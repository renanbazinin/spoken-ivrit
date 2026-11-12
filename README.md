# Spoken Hebrew (עברית): quest voice pack

Hebrew voiceover for the [Spoken](https://github.com/rusty-key/spoken-wow) addon, in WoW Forever.
The pack is a Spoken data module, `SpokenCommunity_ivrit`, built the same way as Spoken's own
language packs. It covers the quests of the six starting zones: Elwynn Forest, Dun Morogh,
Teldrassil, Durotar, Mulgore and Tirisfal Glades.

**רוצים לעזור?** Want to help? Read [CONTRIBUTING.md](CONTRIBUTING.md) (in Hebrew): report a line that sounds wrong,
fix a translation, or take a zone that isn't translated yet. You don't need an ElevenLabs key.

## Install

1. Install **Spoken** and the **Spoken Manager** (0.1.13 or later).
2. In the Manager, open **Community** and install **Spoken Hebrew (Ivrit)**. Or download
   `SpokenCommunity_ivrit-<version>.zip` from [Releases](https://github.com/renanbazinin/spoken-ivrit/releases)
   and extract it into `Interface\AddOns`. Use one of the two, not both.
3. In game, open `/sp`, go to Language, and set Voice Language to **Hebrew**. Leave "If a Voice Is
   Missing" on English, so quests outside these zones still speak.

Spoken 3.8.8 and later learn Hebrew from the pack. "Auto" follows the game client, and no client
runs in Hebrew, so choose Hebrew once. An older Spoken does not list Hebrew: it reads the pack as
English and plays it in place of the English voices.

## Getting the code

```bash
git clone https://github.com/renanbazinin/spoken-ivrit
cd spoken-ivrit
git clone --filter=blob:limit=2m https://github.com/rusty-key/spoken-wow vendor/spoken-wow
```

The recordings (`audio/`), built packs (`build/`) and the game clips the voices were cloned from
(`voices/clips/`, `voices/sources/`) are not in git. Packs are published as releases.

## Choices

| | |
|---|---|
| Scope | Quest start and turn-in text, plus the NPC lines that follow a quest. Spoken never voices progress text. Gossip is not covered yet. |
| Player | One version for everyone. The player is addressed in the masculine (אתה). Lines that English splits by the player's sex use the male text. |
| Reuse | The same voice saying the same text is recorded once and copied to every file that needs it: 849 lines become 818 recordings. |
| Voices | One voice per race and gender, 17 in all, plus a narrator. Each is an ElevenLabs instant clone of the game's own NPC clips for that voice, which is how Spoken's English voices are made. The narrator is a designed voice. |
| Model | ElevenLabs v4, `language_code: he`. |
| Captions | Spoken's subtitle and player window show the Hebrew, written right to left, in a font that has Hebrew letters ([addon/Hebrew.lua](addon/Hebrew.lua)). Spoken's own `present.transcript` and `present.font` carry the text and font. The game cannot lay text out right to left, so each line Spoken draws is turned around and aligned to the right. `tools/test_captions.py` checks this offline in Lua 5.1. The quest window itself still shows the game's English. |
| Text | Translated from Spoken's English corpus with [glossary.json](glossary.json) for names and terms. No Hebrew translation of WoW existed to use. The text is only spoken, never shown, so niqqud is added where a word would otherwise be misread (ההוֹרְד, אֵלוּן). |

## The whole game (since 2026-11-06)

All remaining quests and gossip are split into units, one per zone and kind, in
`lines/index.json`. There are 123 units. The starting zones' quests are done, and the starting
zones' gossip comes next.

- **New recordings use Eleven v4 Turbo.** It costs half the credits of v4 and uses the same cloned voices. The
  starting-zone quests stay on v4.
- **Other elves use the night elf voices.** Skybourne elves and blood elves have no clone of their own.
- **One extra voice:** goblin female. That makes 19 voices.

```bash
python tools/extract_all.py                   # (re)build the units; work already done is kept
python tools/status.py                        # how much is translated, recorded, and left (credits, $)
python tools/merge_names.py                   # after a batch: new names into glossary.json
python tools/generate.py --units a,b --max-credits 25000   # record, capped by an estimated spend
```

## Steps

Each step is a script in `tools/`. Each one resumes where it stopped and skips work that is already done.

```bash
python tools/extract.py vendor/spoken-wow   # lines/<zone>.en.json from Spoken's corpus
python tools/voices.py                      # voices/voices.json: clones the game voices, or finds them
python tools/generate.py                    # audio/<id>.mp3 for every translated line
python tools/review_page.py                 # review.html: listen, tick lines to redo
python tools/build_pack.py --version 0.1.0  # build/dist/SpokenCommunity_ivrit + zip
python tools/install_local.py               # into WoW Forever (and teach a Spoken older than 3.8.8 heIL)
```

- The translations live in `lines/<zone>.he.json`, as `{"lines": {id: Hebrew}}`. Fix a line there, then
  record it again with `python tools/generate.py --force --ids <id>`.
- The ElevenLabs key is read from `.env` here or from `../hebrew-samples/.env`.
- `vendor/spoken-wow` is a checkout of Spoken. Its corpus and its own pack builder are used as they are.

## In game

1. `python tools/build_pack.py --version 0.1.0`, then `python tools/install_local.py`.
2. Start WoW Forever. Open `/sp`, go to Language, and set Voice Language to Hebrew. Keep the fallback on English
   so quests outside these zones still speak.
3. `python tools/install_local.py --undo` puts Spoken back and removes the pack.

Spoken 3.8.8 and later learn Hebrew from the pack's `.toc` (`X-SpokenQuests-Language: heIL`), and
`install_local.py` leaves them alone. On Spoken up to 3.8.7 it adds one line to each of Spoken's
language lists, the same lines Spoken added for Polish (upstream commit `e7a1a957`), and keeps a
`.before-heIL` backup of each file. A Spoken update overwrites these files, so run the script again
after updating. `addon/Hebrew.lua` hooks Spoken's internals, so after a Spoken update also run
`python tools/test_captions.py --spoken "<your AddOns folder>"`: it checks that what the captions use is
still in that Spoken. If it is not, the pack turns its captions off by itself in game (the voice still
plays, with Spoken's own text) and says so once in chat.

## Sharing

1. **Spoken support for heIL:** since Spoken 3.8.8 (first in 3.8.8-beta.1), a pack declares its own
   language: [rusty-key/spoken-wow#1037](https://github.com/rusty-key/spoken-wow/pull/1037), "Voice packs
   bring their own language". It replaced our PR [#930](https://github.com/rusty-key/spoken-wow/pull/930),
   which added Hebrew to Spoken's lists by hand.
2. **Community listing:** releases of this repo carry the zip, and the pack is in Spoken's
   `community/packs.json` since [#931](https://github.com/rusty-key/spoken-wow/pull/931) (merged
   2026-11-11). The Manager shows it from 0.1.13. For each new version, upload the zip, then open a pull
   request that updates `version`, `size`, `sha256` and `url` in that entry (`build_pack.py` prints the
   size and SHA-256).
3. **Font:** the captions use Spoken Hebrew Sans, which `tools/make_font.py` merges from Noto Sans Hebrew
   and Noto Sans's Latin and punctuation (`fonts/`, SIL Open Font License 1.1). It may be shared.
   Windows' Arial and Gisha may not. Noto Sans Hebrew alone drew every comma, period and English
   NPC name as a box.
4. **Licence and credits:** the text is our translation of Blizzard's quest text, and the voices are
   clones of Blizzard's NPC recordings. Spoken's English packs are made the same way. Present it as
   non-commercial fan work.
