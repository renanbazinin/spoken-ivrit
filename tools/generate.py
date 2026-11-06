"""Record the Hebrew lines with the pack's voices (ElevenLabs).

    python tools/generate.py                         # every translated unit, clips not recorded yet
    python tools/generate.py --units elwynn-gossip,durotar-gossip
    python tools/generate.py --max-credits 30000     # stop before an estimated spend
    python tools/generate.py --ids 1a2b3c4d5e6f,0f9e8d7c6b5a --force   # re-record chosen clips

New recordings use Eleven v4 Turbo (half the credits of v4); the starting zones' quests were made
with v4 and are kept as they are (a re-record with --force uses whatever --model says).

A clip is recorded once and copied to every file name that needs it (tools/build_pack.py).
Writes audio/<id>.mp3 (44.1 kHz, 128 kbps: the masters Spoken's packs are encoded from) and
appends each recording to audio/log.jsonl. Re-running skips what exists, so it resumes.
"""
import argparse
import concurrent.futures
import json
import threading
import time

from common import HERE, api_key, call, load_json, pack_files, units

MODEL = "eleven_v4_turbo"
# Credits per Hebrew character, as measured on this account (and as the API price list has it).
RATE = {"eleven_v4": 0.44, "eleven_v3": 0.44, "eleven_v4_turbo": 0.22, "eleven_v3_conversational": 0.22}


def clips(zones):
    out = []
    for zone in zones:
        en = load_json(HERE / "lines" / f"{zone}.en.json", [])
        he = load_json(HERE / "lines" / f"{zone}.he.json", {}).get("lines", {})
        if not he:
            continue
        for clip in en:
            if not pack_files(clip):  # only a female-player variant: not shipped
                continue
            if clip["id"] in he:
                out.append({**clip, "he": he[clip["id"]]})
            else:
                print(f"{zone}: {clip['id']} has no translation, skipped")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", "--zones", dest="units", default=None, help="comma-separated units (default: all)")
    ap.add_argument("--max-credits", type=float, default=None, help="record only as much as this estimate allows")
    ap.add_argument("--ids", help="comma-separated clip ids")
    ap.add_argument("--force", action="store_true", help="re-record clips that already have audio")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    key = api_key()
    voices = load_json(HERE / "voices" / "voices.json")
    todo = clips(args.units.split(",") if args.units else units())
    if args.ids:
        wanted = set(args.ids.split(","))
        todo = [c for c in todo if c["id"] in wanted]
    out = HERE / "audio"
    out.mkdir(exist_ok=True)
    if not args.force:
        todo = [c for c in todo if not (out / f"{c['id']}.mp3").exists()]
    if args.max_credits is not None:
        rate, budget, kept = RATE.get(args.model, 0.44), args.max_credits, []
        for c in todo:
            if budget - len(c["he"]) * rate < 0:
                break
            budget -= len(c["he"]) * rate
            kept.append(c)
        if len(kept) < len(todo):
            print(f"--max-credits {args.max_credits:,.0f}: recording {len(kept)} of {len(todo)} clips")
        todo = kept
    chars = sum(len(c["he"]) for c in todo)
    print(f"{len(todo)} clips to record, {chars:,} Hebrew characters, model {args.model}")
    if not todo:
        return

    before = json.loads(call(key, "GET", "/v1/user/subscription"))["character_count"]
    lock = threading.Lock()
    done = failed = 0

    def record(clip):
        vid = voices.get(clip["voice"])
        if not vid:
            raise RuntimeError(f"no voice for {clip['voice']}")
        for attempt in range(3):
            try:
                return call(key, "POST", f"/v1/text-to-speech/{vid}?output_format=mp3_44100_128",
                            {"text": clip["he"], "model_id": args.model, "language_code": "he"})
            except RuntimeError as e:
                if "429" in str(e) or "HTTP 5" in str(e):  # busy: wait and retry
                    time.sleep(5 * (attempt + 1))
                    continue
                raise
        raise RuntimeError("still busy after 3 tries")

    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool, \
            open(out / "log.jsonl", "a", encoding="utf-8") as log:
        futures = {pool.submit(record, c): c for c in todo}
        for f in concurrent.futures.as_completed(futures):
            c = futures[f]
            try:
                (out / f"{c['id']}.mp3").write_bytes(f.result())
                with lock:
                    done += 1
                    log.write(json.dumps({"id": c["id"], "zone": c["zone"], "voice": c["voice"], "chars": len(c["he"]),
                                          "model": args.model, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}, ensure_ascii=False) + "\n")
                    if done % 25 == 0:
                        print(f"  {done}/{len(todo)}")
            except Exception as e:  # noqa: BLE001 - report every failure, keep going
                failed += 1
                print(f"FAILED {c['zone']} {c['id']} ({c['voice']}): {str(e)[:200]}")
    after = json.loads(call(key, "GET", "/v1/user/subscription"))
    print(f"recorded {done}, failed {failed}; credits used {after['character_count'] - before:,} "
          f"(now {after['character_count']:,} of {after['character_limit']:,})")


main()
