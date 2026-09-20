# VedAnvaya Local Setup

The canonical guide for running VedAnvaya on a local Windows machine: what to install, how
to configure it, how to start and stop the three services, and how to tell the difference
between "it started" and "it works".

VedAnvaya is three processes:

| Service | What it is | Port |
|---|---|---|
| **Neo4j** | The graph, in Docker. Holds the corpus. Never started by the product scripts. | 7474 (HTTP), 7687 (Bolt) |
| **Backend** | FastAPI, read-only against Neo4j. | 8000 |
| **Frontend** | Next.js. Talks only to the backend, never to Neo4j. | 3000 |

They start in that order, and the order matters — see
[Fresh runtime restart](#fresh-runtime-restart).

---

## Prerequisites

Versions below are the ones the repository actually pins, followed by what this guide was
verified against.

| Tool | Required | Where the requirement comes from | Verified with |
|---|---|---|---|
| **Git** | any recent | — | 2.38.1.windows.1 |
| **Python** | 3.12 or newer | `requires-python = ">=3.12"` in `pyproject.toml`; `.python-version` pins `3.12` | 3.12.1 |
| **uv** | any recent | the project's installer; `Makefile` and `README.md` use it throughout | 0.7.13 |
| **Node.js** | 20 or newer | `README.md` quick start (`package.json` declares no `engines` field) | 26.5.0 |
| **pnpm** | 10.34.5 | `"packageManager": "pnpm@10.34.5"` in `frontend/package.json` | 10.34.5 |
| **Docker Desktop** | any version with Compose v2 | `infra/docker-compose.neo4j.yml` | Docker 29.7.2, Compose 5.4.0 |

Neo4j itself is **not** installed on the host. It runs as the `neo4j:5.26-community`
container defined in `infra/docker-compose.neo4j.yml`.

pnpm is the package manager for this repository. Do not use `npm` or `npx` here: when
`node_modules/.bin` is incomplete, `npx <tool>` will silently fetch and run a different
package of the same name instead of failing. Use `pnpm run <script>` or `pnpm exec <tool>`.

---

## Clone

```powershell
git clone <REPOSITORY-URL>
cd VedaGraph
```

This working copy has **no git remote configured** (`git remote -v` returns nothing), so
this guide cannot state the real clone URL. Substitute your own for `<REPOSITORY-URL>`.

Confirm you are on the expected revision:

```powershell
git branch --show-current
git rev-parse HEAD
git status
```

---

## Environment

```powershell
copy .env.example .env
```

Then fill in the values. `.env` is gitignored and must never be committed.

`.env.example` documents every variable. These are the ones that matter for running the
product locally — **names only; this guide contains no values**:

**Required — Neo4j.** Without these the API starts but every knowledge route returns 503.

- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD` — must match the credential in `infra/docker-compose.neo4j.yml`'s
  `NEO4J_AUTH`, which is where the local container's password is actually set
- `NEO4J_DATABASE`

**Optional — backend.** Defaults apply when absent.

- `API_HOST`, `API_PORT`, `API_DEBUG`

**Optional — Ask VedAnvaya (the LLM answer layer).** Absent, the entire browsing product
still works and `/ask` reports `NOT_CONFIGURED` rather than erroring.

- `VEDAGRAPH_LLM_PROVIDER` — `gemini`, `openai`, `anthropic`, `groq`, `openrouter`, `xai`
  or `openai_compatible`
- `VEDAGRAPH_LLM_MODEL`
- `VEDAGRAPH_LLM_API_KEY`

**Optional — frontend.** `frontend/.env.local` holds `VEDAGRAPH_API_URL`, the base URL of
the backend. The frontend reads only this; it never connects to Neo4j and never runs Cypher.

**Optional — public identity.** `VEDANVAYA_SITE_URL` is the origin canonical URLs and
social cards are derived from. Leave it at localhost for local development.

---

## Python backend setup

```powershell
uv sync --extra dev --extra ask
```

This creates and populates `.venv` at the repository root from `uv.lock`. Every backend
command runs from that interpreter, either via `uv run <command>` or directly as
`.venv\Scripts\python.exe`. There is no separate `activate` step in this guide's commands.

Two cautions, both measured on this repository:

- **Include `--extra ask` if you want Ask VedAnvaya.** `uv sync` prunes anything outside
  the extras you name. A bare `uv sync --extra dev` uninstalls 36 packages here, including
  `anthropic` and `openai` — the Ask adapters — which breaks `/ask` without touching any
  other surface. `README.md`'s quick start shows the bare form because it describes the
  browsing product only.
- **`uv sync` reconciles an existing `.venv` to the lockfile**, so it can also remove
  packages an earlier corpus-building session installed. That is correct behaviour, but on
  a machine with a running backend it mutates the interpreter that backend is using. Stop
  the backend first, or preview with `uv sync --extra dev --extra ask --dry-run`.

---

## Frontend setup

```powershell
cd frontend
pnpm install
cd ..
```

Other frontend commands, all run from `frontend/`:

```powershell
pnpm dev
pnpm build
pnpm start
pnpm typecheck
pnpm lint
pnpm test
pnpm test:e2e
pnpm run audit
```

`pnpm dev` is the development server and what `start-product.ps1` uses; `pnpm build` then
`pnpm start` serve the production build.

**`pnpm run audit`, not `pnpm audit`.** This repository defines an `audit` script that runs
the design-system build gates — tokens, contrast, class collisions, z-index, motion, and a
check that the frontend's completeness fallback still matches the live API. But `audit` is
also one of pnpm's own built-in commands, and the built-in wins: bare `pnpm audit` queries
the npm registry for vulnerabilities and never runs this repository's gates at all. Use
`pnpm run` whenever a script name might collide with a package-manager subcommand.

---

## Database setup

Start the container from the repository root:

```powershell
docker compose -f infra\docker-compose.neo4j.yml up -d
```

It is named `vedagraph-neo4j` and stores the graph in the Docker volumes `infra_neo4j_data`
and `infra_neo4j_logs`. **Those volumes are what hold the corpus.** Stopping or restarting
the container preserves them; `docker compose down -v` or `docker volume rm` destroys them.
Nothing in this guide does that.

The container declares a healthcheck, so wait for it rather than assuming:

```powershell
docker inspect --format "{{.State.Health.Status}}" vedagraph-neo4j
```

Neo4j takes tens of seconds to go from `starting` to `healthy`. The product scripts never
start, stop or migrate it — the graph is treated as frozen, and a start script that
silently brought one up would be the wrong kind of convenient.

### How a genuinely new developer gets the graph

**There is no automatic bootstrap, and this guide will not invent one.**

`.gitignore` excludes `data/canonical/**`, `data/knowledge/**`, `data/derived/**`,
`data/staged/**` and `data/raw/**`, keeping only each canonical build's `manifest.json`. A
fresh clone therefore arrives **without the corpus records**, and
`scripts/build_neo4j_projection.py` — which loads Neo4j from those records — has nothing to
read.

So a working VedAnvaya currently requires one of:

1. **A preloaded local Neo4j volume** — the situation this machine is in, and the one the
   product assumes. The graph already lives in `infra_neo4j_data`.
2. **A Neo4j dump restored into the container.** This machine holds
   `data/backup/pre_translation_bulk_import_neo4j.dump`; only its `.sha256` is tracked in
   git, so the dump itself must be transferred out of band.
3. **Rebuilding the corpus from sources**, then projecting it:

   ```powershell
   uv run python scripts\build_neo4j_projection.py
   ```

   The rebuild that produces its input is a long, multi-stage ingestion campaign (polite
   network fetches at 1 req/s, per-Mandala staging and gating). `README.md`'s
   "Corpus-building environment" and "CLI" sections document it. It is not part of ordinary
   local setup.

If you have been handed this repository without a populated Neo4j volume or a dump, say so
before starting — `doctor.ps1` will report `neo4j-loaded FAIL`, and every count the product
shows would otherwise be a false zero.

---

## Start everything

### Recommended: the repository's launcher

`scripts/start-product.ps1` runs the preflight checks, starts the API, waits for it to
report ready, then starts the frontend. Neo4j must already be running.

```powershell
# Terminal 1 - Neo4j (once; it restarts with Docker)
docker compose -f infra\docker-compose.neo4j.yml up -d

# Terminal 2 - everything else
powershell -ExecutionPolicy Bypass -File scripts\start-product.ps1
```

Both servers are launched detached, so the terminal returns to a prompt while they keep
running. Their output goes to `.tmp\api.log` and `.tmp\frontend.log`, and their process ids
to `.tmp\api.pid` and `.tmp\frontend.pid`.

Useful switches:

| Switch | Effect |
|---|---|
| `-SkipDoctor` | Start without the preflight checks |
| `-ApiOnly` | Start the API and not the frontend |
| `-Production` | `pnpm build` then `pnpm start` instead of `pnpm dev` |

### Manual: three terminals

Equivalent to the above, if you want each service in its own window:

```powershell
# Terminal 1 - Neo4j
docker compose -f infra\docker-compose.neo4j.yml up -d

# Terminal 2 - backend (from the repository root)
uv run uvicorn vedagraph.api.app:app --host 127.0.0.1 --port 8000

# Terminal 3 - frontend
cd frontend
pnpm dev
```

`make api` runs the same backend command with `--reload` added.

---

## URLs

| Surface | URL |
|---|---|
| Frontend | <http://localhost:3000> |
| Backend | <http://127.0.0.1:8000> |
| Backend interactive docs | <http://127.0.0.1:8000/docs> |
| Neo4j Browser | <http://localhost:7474> |
| Neo4j Bolt | `bolt://localhost:7687` |

---

## Verify installation

### The preflight, first

```powershell
powershell -ExecutionPolicy Bypass -File scripts\doctor.ps1
```

Fourteen checks: the Python environment, the frontend install, Neo4j connectivity **and
whether the corpus is actually loaded**, the LLM configuration, the audio catalog and both
ports. It names whichever one is wrong, and exits non-zero only when a REQUIRED check
fails. It never prints a secret — where a credential matters it reports only that it is set
and how many characters long it is. Add `-Json` for machine-readable output.

### Neo4j health

```powershell
docker inspect --format "{{.State.Health.Status}}" vedagraph-neo4j
curl.exe -s -o NUL -w "%{http_code}\n" http://localhost:7474
```

Expect `healthy` and `200`.

### Backend

```powershell
curl.exe -s http://127.0.0.1:8000/health
curl.exe -s http://127.0.0.1:8000/ready
```

`/health` answers even when Neo4j is down — it says the process is up, nothing more.
`/ready` is the one that matters: it checks Neo4j connectivity, that all four works are
present, the ontology version and the required constraints.

### The canonical corpus totals

```powershell
curl.exe -s http://127.0.0.1:8000/api/v1/completeness
```

The four corpora should report **20,210 canonical mantras** in total:

| Veda | Mantras |
|---|---|
| RV — Rigveda Saṃhitā (Śākala) | 10,552 |
| SV — Samaveda Saṃhitā (Kauthuma ārcika) | 1,844 |
| YV — Vājasaneyi Saṃhitā (Śukla, Mādhyandina) | 1,975 |
| AV — Atharvaveda Saṃhitā (Śaunaka) | 5,839 |
| **Total** | **20,210** |

**Read this endpoint for what it is.** `/api/v1/completeness` serves the `CORPUS_MANTRAS`
constant in `src/vedagraph/domain/layer_figures.py` — a certified figure, deliberately
fixed, not a live count. It will keep reporting 20,210 against an empty database. To check
that the **graph** holds them, count the nodes:

```powershell
docker exec vedagraph-neo4j cypher-shell -u neo4j -p <NEO4J_PASSWORD> "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS c ORDER BY veda"
```

The certified graph is **165,737 nodes** and **510,905 relationships** across **4 works**.
`doctor.ps1`'s `neo4j-loaded` check reports all three without needing a password on the
command line.

### Frontend

```powershell
curl.exe -s -o NUL -w "%{http_code}\n" http://localhost:3000
```

Then open <http://localhost:3000> and confirm a real page, not a fallback. Two renders mean
something is wrong:

- **"The atlas is offline"** — the page loaded but the backend did not answer.
- **"This thread is not held here"** — the identifier is not in the corpus.

If you are scripting these checks rather than looking at the page, use the **HTTP status
code** to detect the not-found case, not a string match. Next.js serialises the not-found
boundary into the React flight payload of *every* page, so both `This thread is not held
here` and its `va-missing-code` class are present byte-for-byte in the HTML of a perfectly
healthy homepage. A real miss is an HTTP 404; a healthy page is a 200. `The atlas is
offline` is safe to grep for, because that component is only ever emitted when data is
actually absent.

A quick end-to-end sweep, each of which should answer 200 with real content:

```text
/                                          the homepage
/vedas                                     all four corpora
/vedas/samaveda                            one corpus
/passage/VG%3ARV%3ASAK%3AM01%3AS001%3AV001 the reader, at RV 1.1.1
/search?q=agni                             search
/ask                                       Ask VedAnvaya
/connections                               cross-Veda reuse
/graph                                     the graph view
/limits                                    the stated limits
```

Passage routes take the canonical key URL-encoded, so `VG:RV:SAK:M01:S001:V001` becomes
`VG%3ARV%3ASAK%3AM01%3AS001%3AV001`.

---

## Stop everything

### Frontend and backend

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop-product.ps1
```

This stops the recorded process ids and their children, then sweeps for any server process
whose **command line points into this repository**. The sweep is the part that actually
works for the frontend: `pnpm` on Windows is a `.cmd` shim that spawns Node and exits, so
the recorded pid is dead within a second while the Node server it launched keeps listening
with no parent to walk down from. Because the sweep is scoped by command line to this
repository's own directory, it cannot touch an unrelated Node or Python process on the same
machine.

Never kill every `node.exe` or `python.exe` on the machine. To see what actually holds a
port:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 3000 | ForEach-Object { Get-Process -Id $_.OwningProcess }
```

`stop-product.ps1` never touches Neo4j.

### Stopping Neo4j

```powershell
docker compose -f infra\docker-compose.neo4j.yml stop
```

`stop` halts the container and keeps the volumes. `docker compose -f
infra\docker-compose.neo4j.yml down` also removes the container, which is still safe — the
named volumes survive.

**Never run `docker compose down -v` or `docker volume rm` against this project.** Those
delete `infra_neo4j_data`, and with it the loaded corpus, which this repository cannot
rebuild from a clone.

---

## Fresh runtime restart

Restarts the processes without touching any data. This does **not** erase the graph: no
volume is removed, no database is wiped, and `data/`, `.env`, `.venv`,
`frontend/node_modules` and `frontend/.world` are all left alone.

```powershell
# 1. Stop the frontend and backend
powershell -ExecutionPolicy Bypass -File scripts\stop-product.ps1

# 2. Restart Neo4j (volumes preserved)
docker compose -f infra\docker-compose.neo4j.yml restart neo4j

# 3. Wait for it to report healthy before going on
docker inspect --format "{{.State.Health.Status}}" vedagraph-neo4j

# 4. Optional: clear the frontend build cache
Remove-Item -Recurse -Force frontend\.next

# 5. Start the backend and frontend again
powershell -ExecutionPolicy Bypass -File scripts\start-product.ps1
```

Step 3 is not optional politeness. Starting the backend against a Neo4j that is still
initialising gives an API that reports not-ready and a frontend that renders "The atlas is
offline" — and in production mode that render can then be cached.

`frontend\.next` is disposable generated output (around 700 MB here); Next.js rebuilds it.
Clearing it costs a slower first page load and nothing else.

---

## Common problems

**Port already in use.** `doctor.ps1` reports it as a warning, since the most likely cause
is that VedAnvaya is already running. Identify the holder before killing anything:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8000 | ForEach-Object { Get-Process -Id $_.OwningProcess }
```

Ports 7474 and 7687 normally show `com.docker.backend` and `wslrelay` — that is Docker
forwarding them, not a conflict.

**Backend cannot reach Neo4j.** `/ready` fails while `/health` still answers 200, and
knowledge routes return 503. Check, in order: the container is running
(`docker ps --filter name=vedagraph-neo4j`), it is `healthy` rather than `starting`, and
`NEO4J_PASSWORD` in `.env` matches `NEO4J_AUTH` in `infra/docker-compose.neo4j.yml`.
`doctor.ps1` distinguishes these: `neo4j-reachable` failing is credentials or connectivity,
`neo4j-loaded` failing means it connected to an empty or partial graph.

**Frontend shows "The atlas is offline".** The backend was not answering when that page
rendered. Start the backend, then reload. If you are running the production build
(`pnpm start`), the offline render can be cached — restart the frontend rather than just
refreshing the browser.

**The browser shows an old version after a fix.** Stop the frontend, delete
`frontend\.next`, start it again. A stale build directory pairs this build's code with the
previous build's generated assets, and the result looks like a bug in the code rather than
a stale artifact.

**`.env` missing.** `doctor.ps1` reports `env-file FAIL`. Copy `.env.example` to `.env` and
set at least `NEO4J_PASSWORD`.

**Docker container not running.** `docker ps -a --filter name=vedagraph-neo4j` shows it
stopped or absent; `docker compose -f infra\docker-compose.neo4j.yml up -d` brings it back.
The volumes persist across container removal, so the graph survives.

**Neo4j still initialising.** `docker inspect` reports `starting`, and the API's `/ready`
fails against it. Wait for `healthy`. Logs: `docker logs vedagraph-neo4j --tail 50`.

**pnpm dependencies missing.** `doctor.ps1` reports `frontend-deps FAIL`, or `next` is not
found. Run `pnpm install` in `frontend/`. Use `pnpm`, not `npm` — see
[Prerequisites](#prerequisites).

**Ask VedAnvaya reports NOT_CONFIGURED.** No LLM key was found. Set
`VEDAGRAPH_LLM_PROVIDER`, `VEDAGRAPH_LLM_MODEL` and `VEDAGRAPH_LLM_API_KEY` in `.env`, and
make sure the adapters are installed (`uv sync --extra dev --extra ask`). Check it with
`curl.exe -s http://127.0.0.1:8000/api/v1/ask/health`. Everything except `/ask` works
without a key.

**The servers started but the terminal never returns.** Use `scripts\start-product.ps1`
rather than `Start-Process -RedirectStandardOutput`: PowerShell holds the child's output
handles and waits for them to close, so a script that starts `next dev` that way never
returns to the prompt even though the server is up and answering.
