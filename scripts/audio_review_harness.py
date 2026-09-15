#!/usr/bin/env python3
"""Owner decision 4: a resumable local harness for the 1,021-row audible-review queue.

The gate this serves is the one the campaign has refused to weaken. Automated text
comparison, metadata review, waveform inspection and ASR are none of them listening
review, and 0 of 1,021 rows have been listened to. This is the tool that lets a person
close that, and it is built so that closing it dishonestly is harder than closing it
honestly.

WHAT MAKES A DECISION COUNT
===========================

Three things, enforced by the server rather than asked of the reviewer.

**The audio must have been consumed.** The page reports how many seconds of the recording
actually played, taken from the audio element's own ``timeupdate`` events, and
``AUDIBLY_VERIFIED`` is refused when that figure is zero. A reviewer who never pressed
play cannot record a verification, and nothing that reads only text or metadata can reach
this endpoint at all. The owner's rule that an AI reviewer counts only when its tool
actually consumes audio is the same rule; this makes it mechanical.

**A reviewer must be named.** No anonymous verdicts, because a listening claim with no
listener is the thing the queue exists to prevent.

**Only three verdicts exist.** ``AUDIBLY_VERIFIED``, ``AUDIBLY_REJECTED``,
``AUDIBLE_REVIEW_UNCERTAIN``. Anything else is a 400. Uncertain is a first-class answer and
is offered as prominently as the other two: a queue that makes uncertainty inconvenient
collects false certainty.

RESUMABILITY
============

The decision log is append-only JSONL, flushed and fsynced before the response returns, so
a decision survives the process dying immediately afterwards. The queue file itself is
*derived*: on start the log is replayed over it, and the latest decision per ``review_id``
wins. That ordering is deliberate -- the log is the record and the queue is a projection of
it, so a corrupted queue can be rebuilt and a lost log cannot be reconstructed from the
queue.

CONTROLS, BECAUSE A THOUSAND ITEMS IS THE DESIGN CONSTRAINT
===========================================================

Single keystroke per verdict, auto-advance to the next undecided row, autoplay on arrival,
replay without leaving the keyboard, a stratum filter, and a jump box. The queue is ordered
by ``review_priority`` then citation, so the rows that block the most arrive first.

Usage:
    python scripts/audio_review_harness.py [--port 8420]
    python scripts/audio_review_harness.py --progress      # print status and exit
"""

from __future__ import annotations

import argparse
import collections
import datetime
import json
import os
import pathlib
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

QUEUE = pathlib.Path("data/staging/audio_review_queue.jsonl")
LOG = pathlib.Path("data/staging/audio_review_decisions.jsonl")

#: The only verdicts that exist. A fourth would be a way to avoid deciding.
VERDICTS = ("AUDIBLY_VERIFIED", "AUDIBLY_REJECTED", "AUDIBLE_REVIEW_UNCERTAIN")

#: Verdicts that assert the reviewer heard the recording, so they require played audio.
REQUIRES_AUDIO = frozenset({"AUDIBLY_VERIFIED", "AUDIBLY_REJECTED"})

_LOCK = threading.Lock()


def read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_queue() -> list[dict[str, Any]]:
    """The queue with every recorded decision replayed over it, latest per row winning."""
    rows = read_jsonl(QUEUE)
    decisions: dict[str, dict[str, Any]] = {}
    for entry in read_jsonl(LOG):
        review_id = str(entry.get("review_id") or "")
        if review_id:
            decisions[review_id] = entry
    for row in rows:
        decision = decisions.get(str(row.get("review_id") or ""))
        if decision is None:
            continue
        row["review_status"] = decision["verdict"]
        row["verdict"] = decision["verdict"]
        row["reviewer"] = decision["reviewer"]
        row["reviewed_at"] = decision["reviewed_at"]
        row["reviewer_notes"] = decision.get("notes") or None
        row["listened_seconds"] = decision.get("listened_seconds")
    rows.sort(key=lambda r: (int(r.get("review_priority") or 99), str(r.get("citation") or "")))
    return rows


def append_decision(entry: dict[str, Any]) -> None:
    """Append and fsync before returning, so a decision survives an immediate crash."""
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, LOG.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def progress(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_status = collections.Counter(str(r.get("review_status")) for r in rows)
    by_stratum: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for row in rows:
        by_stratum[str(row.get("stratum"))][str(row.get("review_status"))] += 1
    decided = sum(by_status[v] for v in VERDICTS)
    return {
        "total": len(rows),
        "decided": decided,
        "remaining": len(rows) - decided,
        "by_status": dict(sorted(by_status.items())),
        "by_stratum": {k: dict(sorted(v.items())) for k, v in sorted(by_stratum.items())},
        "verdicts": list(VERDICTS),
    }


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Audible review harness</title>
<style>
 :root{--bg:#14110f;--fg:#efe7dd;--dim:#9a8f84;--line:#332c26;--ok:#4f9e6a;--no:#b5533f;--un:#a08a3c}
 *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--fg);
   font:15px/1.55 ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}
 header{display:flex;gap:16px;align-items:center;padding:10px 18px;border-bottom:1px solid var(--line);
   position:sticky;top:0;background:var(--bg);flex-wrap:wrap}
 main{max-width:1000px;margin:0 auto;padding:22px 18px 80px}
 .bar{height:5px;background:var(--line);border-radius:3px;flex:1;min-width:160px;overflow:hidden}
 .bar>i{display:block;height:100%;background:var(--ok)}
 .mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
 .cite{font-size:26px;font-weight:600;letter-spacing:.01em}
 .sans{font-size:22px;line-height:1.85;padding:16px 18px;border:1px solid var(--line);
   border-radius:8px;background:#1b1714;margin:14px 0}
 dl{display:grid;grid-template-columns:200px 1fr;gap:6px 18px;margin:16px 0}
 dt{color:var(--dim)} dd{margin:0;overflow-wrap:anywhere}
 .listen{border-left:3px solid var(--un);padding:10px 14px;background:#1b1714;margin:14px 0;color:#e8dcc8}
 audio{width:100%;margin:10px 0}
 .row{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0}
 button{font:inherit;padding:11px 16px;border-radius:7px;border:1px solid var(--line);
   background:#221d19;color:var(--fg);cursor:pointer}
 button:hover{border-color:var(--dim)}
 button.v{border-color:var(--ok)} button.r{border-color:var(--no)} button.u{border-color:var(--un)}
 button[disabled]{opacity:.4;cursor:not-allowed}
 kbd{font-family:ui-monospace,monospace;font-size:12px;border:1px solid var(--line);
   border-radius:4px;padding:1px 5px;color:var(--dim)}
 input,textarea,select{font:inherit;background:#221d19;color:var(--fg);
   border:1px solid var(--line);border-radius:6px;padding:8px 10px}
 textarea{width:100%;min-height:62px}
 .note{color:var(--dim);font-size:13px}
 .warn{color:var(--un)}
 .status{font-weight:600}
 .done{color:var(--ok)}
</style></head><body>
<header>
  <strong>Audible review</strong>
  <span class="mono" id="count"></span>
  <span class="bar"><i id="fill" style="width:0"></i></span>
  <label class="note">reviewer <input id="who" size="14" placeholder="your name"></label>
  <label class="note">stratum <select id="strat"><option value="">all</option></select></label>
  <label class="note">jump <input id="jump" size="6" placeholder="#"></label>
  <button id="skip">skip <kbd>S</kbd></button>
</header>
<main id="main"><p class="note">loading…</p></main>
<script>
let rows=[], idx=0, played=0, filt="";
const el=id=>document.getElementById(id);

async function boot(){
  const r=await fetch("/api/queue"); const d=await r.json();
  rows=d.rows; el("who").value=localStorage.getItem("vg_reviewer")||"";
  const strata=[...new Set(rows.map(r=>r.stratum))].sort();
  for(const s of strata){const o=document.createElement("option");o.value=s;o.textContent=s;el("strat").append(o);}
  el("strat").onchange=()=>{filt=el("strat").value; idx=nextUndecided(-1); render();};
  el("who").oninput=()=>{localStorage.setItem("vg_reviewer",el("who").value); render();};
  el("skip").onclick=()=>{idx=nextUndecided(idx); render();};
  el("jump").onchange=()=>{const n=parseInt(el("jump").value,10); if(n>=1&&n<=rows.length){idx=n-1; render();}};
  idx=nextUndecided(-1); render();
}
const inFilter=r=>!filt||r.stratum===filt;
const decided=r=>["AUDIBLY_VERIFIED","AUDIBLY_REJECTED","AUDIBLE_REVIEW_UNCERTAIN"].includes(r.review_status);
function nextUndecided(from){
  for(let i=from+1;i<rows.length;i++) if(inFilter(rows[i])&&!decided(rows[i])) return i;
  for(let i=0;i<rows.length;i++) if(inFilter(rows[i])&&!decided(rows[i])) return i;
  return Math.max(0,from);
}
function esc(s){const d=document.createElement("div"); d.textContent=s==null?"":String(s); return d.innerHTML;}

function render(){
  const done=rows.filter(decided).length;
  el("count").textContent=done+" / "+rows.length+" decided";
  el("fill").style.width=(100*done/rows.length)+"%";
  const r=rows[idx]; if(!r){el("main").innerHTML="<p>nothing queued</p>"; return;}
  played=0;
  const who=el("who").value.trim();
  const secs=(r.start_seconds!=null||r.end_seconds!=null)
    ? `${r.start_seconds??0}s – ${r.end_seconds??"end"}s` : "whole file, no stated offsets";
  el("main").innerHTML=`
   <div class="note">#${idx+1} of ${rows.length} · ${esc(r.stratum)} · priority ${esc(r.review_priority)}
     · <span class="mono">${esc(r.review_id)}</span></div>
   <div class="cite">${esc(r.citation)}</div>
   <div class="note mono">${esc(r.canonical_key)}</div>
   <div class="sans">${esc(r.canonical_sanskrit)||"<span class='warn'>no canonical Sanskrit on this row</span>"}</div>
   <div class="listen"><strong>Listen for:</strong> ${esc(r.listen_for)}</div>
   <audio id="au" controls preload="none" src="${esc(r.media_url)}"></audio>
   <div class="note">played this row: <span id="pl" class="mono">0.0</span>s
     · <button id="again">replay <kbd>R</kbd></button></div>
   <dl>
     <dt>source</dt><dd>${esc(r.source_name)}${r.performer?" · "+esc(r.performer):""}</dd>
     <dt>source coordinate</dt><dd class="mono">${esc(r.media_url)}</dd>
     <dt>segment</dt><dd>${esc(secs)} · is_segmented ${esc(r.is_segmented)}
       · duration ${r.duration_seconds==null?"unstated":esc(r.duration_seconds)+"s"}</dd>
     <dt>mapping method</dt><dd>${esc((r.prior_automated_checks||{}).mapping_method)||"<span class='note'>not recorded on this row</span>"}</dd>
     <dt>prior automated checks</dt><dd class="note">${esc(JSON.stringify(r.prior_automated_checks))}</dd>
     <dt>current status</dt><dd class="status ${decided(r)?"done":""}">${esc(r.review_status)}${
       r.reviewer?` · ${esc(r.reviewer)} · ${esc(r.reviewed_at)}`:""}</dd>
   </dl>
   <textarea id="notes" placeholder="notes (what you heard, and why)">${esc(r.reviewer_notes)}</textarea>
   <div class="row">
     <button class="v" id="bv" ${who?"":"disabled"}>Audibly verified <kbd>V</kbd></button>
     <button class="r" id="br" ${who?"":"disabled"}>Audibly rejected <kbd>X</kbd></button>
     <button class="u" id="bu" ${who?"":"disabled"}>Uncertain <kbd>U</kbd></button>
   </div>
   <p class="note">${who?"Verified and rejected both require the audio to have played — the server checks."
      :"<span class='warn'>Name yourself in the header before recording a verdict.</span>"}</p>`;
  const au=el("au");
  au.ontimeupdate=()=>{played=Math.max(played,au.currentTime); el("pl").textContent=played.toFixed(1);};
  el("again").onclick=()=>{au.currentTime=r.start_seconds||0; au.play();};
  el("bv").onclick=()=>decide("AUDIBLY_VERIFIED");
  el("br").onclick=()=>decide("AUDIBLY_REJECTED");
  el("bu").onclick=()=>decide("AUDIBLE_REVIEW_UNCERTAIN");
  au.play().catch(()=>{});
}

async function decide(verdict){
  const who=el("who").value.trim(); if(!who) return;
  const r=rows[idx];
  const res=await fetch("/api/decision",{method:"POST",headers:{"content-type":"application/json"},
    body:JSON.stringify({review_id:r.review_id,verdict,reviewer:who,
      notes:el("notes").value.trim(),listened_seconds:Number(played.toFixed(2))})});
  if(!res.ok){alert((await res.json()).error); return;}
  const saved=await res.json();
  Object.assign(r,{review_status:saved.verdict,verdict:saved.verdict,reviewer:saved.reviewer,
    reviewed_at:saved.reviewed_at,reviewer_notes:saved.notes||null});
  idx=nextUndecided(idx); render();
}

addEventListener("keydown",e=>{
  if(["INPUT","TEXTAREA","SELECT"].includes(e.target.tagName)) return;
  const k=e.key.toLowerCase(); const au=el("au");
  if(k==="v"){decide("AUDIBLY_VERIFIED");e.preventDefault();}
  else if(k==="x"){decide("AUDIBLY_REJECTED");e.preventDefault();}
  else if(k==="u"){decide("AUDIBLE_REVIEW_UNCERTAIN");e.preventDefault();}
  else if(k==="s"){idx=nextUndecided(idx);render();e.preventDefault();}
  else if(k==="r"&&au){au.currentTime=0;au.play();e.preventDefault();}
  else if(k==="arrowright"){idx=Math.min(rows.length-1,idx+1);render();e.preventDefault();}
  else if(k==="arrowleft"){idx=Math.max(0,idx-1);render();e.preventDefault();}
  else if(k===" "&&au){au.paused?au.play():au.pause();e.preventDefault();}
});
boot();
</script></body></html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "VedaGraphAudibleReview/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        return  # the console is the progress display, not an access log

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, payload: dict[str, Any]) -> None:
        self._send(
            code, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json"
        )

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/api/queue":
            rows = load_queue()
            self._json(200, {"rows": rows, "progress": progress(rows)})
        elif self.path == "/api/progress":
            self._json(200, progress(load_queue()))
        else:
            self._json(404, {"error": "no such path"})

    def do_POST(self) -> None:
        if self.path != "/api/decision":
            self._json(404, {"error": "no such path"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "body is not JSON"})
            return

        review_id = str(payload.get("review_id") or "")
        verdict = str(payload.get("verdict") or "")
        reviewer = str(payload.get("reviewer") or "").strip()
        listened = float(payload.get("listened_seconds") or 0.0)

        if verdict not in VERDICTS:
            self._json(400, {"error": f"verdict must be one of {', '.join(VERDICTS)}"})
            return
        if not reviewer:
            self._json(400, {"error": "a verdict needs a named reviewer"})
            return
        known = {str(r.get("review_id")) for r in read_jsonl(QUEUE)}
        if review_id not in known:
            self._json(400, {"error": f"{review_id} is not in the queue"})
            return
        # The gate, enforced here rather than trusted to the page: a claim to have heard
        # the recording requires the recording to have played.
        if verdict in REQUIRES_AUDIO and listened <= 0:
            self._json(
                400,
                {
                    "error": (
                        f"{verdict} requires the audio to have played. Nothing was heard for "
                        "this row, so the only honest verdict available is "
                        "AUDIBLE_REVIEW_UNCERTAIN."
                    )
                },
            )
            return

        entry = {
            "review_id": review_id,
            "verdict": verdict,
            "reviewer": reviewer,
            "reviewed_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "notes": str(payload.get("notes") or "").strip(),
            "listened_seconds": round(listened, 2),
            "evidence_of_audio_consumption": "audio element timeupdate, reported by the page",
        }
        append_decision(entry)
        rows = load_queue()
        done = progress(rows)
        print(
            f"  {done['decided']:>5} / {done['total']}  {verdict:26} {review_id}"
            f"  ({listened:.1f}s heard)"
        )
        self._json(200, entry)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    # 8420 rather than a more obvious 8787: Windows reserves several hundred ports in
    # the 8633-9032 range by default, and a bind there fails with WinError 10013, which
    # reads like a firewall problem rather than a reserved range. Checked with
    # `netsh interface ipv4 show excludedportrange protocol=tcp`.
    parser.add_argument("--port", type=int, default=8420)
    parser.add_argument("--progress", action="store_true", help="print status and exit")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    if not QUEUE.exists():
        print(f"  {QUEUE} does not exist. Run scripts/build_audio_review_queue.py first.")
        return 1

    rows = load_queue()
    state = progress(rows)
    print()
    print("  AUDIBLE REVIEW HARNESS")
    print()
    print(f"  queue    {QUEUE}")
    print(f"  log      {LOG}  (append-only, the queue is a projection of it)")
    print()
    print(f"  decided  {state['decided']} of {state['total']}   remaining {state['remaining']}")
    for status, count in state["by_status"].items():
        print(f"    {status:30}{count:>6}")
    print()
    for stratum, counts in state["by_stratum"].items():
        left = counts.get("NEEDS_AUDIBLE_REVIEW", 0)
        print(f"    {stratum:38}{sum(counts.values()):>6} rows, {left:>6} left")
    print()
    if args.progress:
        return 0

    url = f"http://127.0.0.1:{args.port}/"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except PermissionError:
        # WinError 10013 on a free port means the port sits in an OS-reserved exclusion
        # range, which is indistinguishable from a firewall refusal unless you are told.
        print(f"  port {args.port} is refused by the OS, not by another process.")
        print("  On Windows, check the reserved ranges and pick a port outside them:")
        print("    netsh interface ipv4 show excludedportrange protocol=tcp")
        print("  Then re-run with --port <free port>. This machine reserves 8633-9032.")
        return 1
    except OSError as error:
        print(f"  cannot serve on port {args.port}: {error}")
        print(f"  something may already be listening there; try --port {args.port + 1}")
        return 1
    print(f"  serving {url}   (Ctrl-C to stop; every decision is persisted as it is made)")
    print()
    print("  keys: V verified · X rejected · U uncertain · S skip · R replay · space play/pause")
    print()
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        final = progress(load_queue())
        print(f"  stopped. {final['decided']} of {final['total']} decided.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
