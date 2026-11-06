# Spoken Hebrew (עברית): quest voice pack

Hebrew voiceover for the [Spoken](https://github.com/rusty-key/spoken-wow) addon, in WoW Forever.
The pack is a Spoken data module, `SpokenCommunity_ivrit`, built the same way as Spoken's own
language packs. It covers the quests of the six starting zones: Elwynn Forest, Dun Morogh,
Teldrassil, Durotar, Mulgore and Tirisfal Glades.

**רוצים לעזור?** Want to help? Read [CONTRIBUTING.md](CONTRIBUTING.md) (in Hebrew): report a line that sounds wrong,
fix a translation, or take a zone that isn't translated yet. You don't need an ElevenLabs key.

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
python tools/install_local.py               # into WoW Forever, and teach the installed Spoken heIL
```

- The translations live in `lines/<zone>.he.json`, as `{"lines": {id: Hebrew}}`. Fix a line there, then
  record it again with `python tools/generate.py --force --ids <id>`.
- The ElevenLabs key is read from `.env` here or from `../hebrew-samples/.env`.
- `vendor/spoken-wow` is a checkout of Spoken. Its corpus and its own pack builder are used as they are.

## In game

1. `python tools/build_pack.py --version 0.1.0`, then `python tools/install_local.py`.
2. Start WoW Forever. Open `/sp`, go to Language, and set Voice Language to עברית (Hebrew). Keep the fallback on English
   so quests outside these zones still speak.
3. `python tools/install_local.py --undo` puts Spoken back and removes the pack.

Spoken 3.8.3 does not know Hebrew yet. `install_local.py` adds one line to each of Spoken's language
lists, the same lines Spoken added for Polish (upstream commit `e7a1a957`), and keeps a
`.before-heIL` backup of each file. A Spoken update overwrites these files, so run the script again
after updating.

## Before sharing it

**Only install the pack on a Spoken that knows Hebrew (`heIL`).** An older Spoken reads the pack as
English. It would then play Hebrew to English listeners, because `SpokenCommunity_…` sorts ahead of
the official packs. Until a Spoken release has Hebrew, `tools/install_local.py` patches your own copy.

Where sharing stands:

1. **Spoken support for heIL:** draft PR [rusty-key/spoken-wow#930](https://github.com/rusty-key/spoken-wow/pull/930),
   from the `add-hebrew-language` branch of [renanbazinin/spoken-wow](https://github.com/renanbazinin/spoken-wow).
   It mirrors the Polish commit `e7a1a957`.
2. **Community listing:** releases of this repo carry the zip, and draft PR [rusty-key/spoken-wow#931](https://github.com/rusty-key/spoken-wow/pull/931) adds the pack to
   `community/packs.json` with the zip's size and SHA-256, which `build_pack.py` prints. It can merge only
   after Spoken ships heIL. For each new version, upload the zip, then update `version`, `size`, `sha256`
   and `url` in that entry.
3. **Font:** the captions use Noto Sans Hebrew (`fonts/`, SIL Open Font License 1.1), which may be shared.
   Windows' Arial and Gisha may not.
4. **Licence and credits:** the text is our translation of Blizzard's quest text, and the voices are
   clones of Blizzard's NPC recordings. Spoken's English packs are made the same way. Present it as
   non-commercial fan work.
