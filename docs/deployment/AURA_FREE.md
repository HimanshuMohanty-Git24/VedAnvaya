# AuraDB Free deployment profile

This profile deploys a copy of VedaGraph. It never modifies the local Docker volume or the
local `.env` file.

## Intentional scope reduction

AuraDB Free allows at most 400,000 relationships. The full release contains 510,905. The
deployment copy removes only `MENTIONS_LEMMA` (154,261 internal lexical-index edges), leaving
about 356,644 relationships. Normal graph exploration and every corpus, passage, translation,
entity, deity, formula, ritual, and semantic relationship remain. Dictionary-headword search is
disabled and declares that limit in its API response.

## Build the isolated Aura upload dump

Use a separate Docker volume and ports, never `infra_neo4j_data` or port 7687. The source dump
is `data/staging/final_stabilization/neo4j_backup_20260917/neo4j.dump`. Start a temporary
Neo4j 5.26 container from that dump, expose Bolt at `17687`, and run:

```powershell
uv run python scripts/deployment/trim_aura_free.py --uri bolt://127.0.0.1:17687 --password <temporary-password>
```

Stop the temporary container, then use `neo4j-admin database dump neo4j` against its separate
volume. Upload the resulting `neo4j.dump` to Aura with `neo4j-admin database upload`.

## Cloud services

1. Create an AuraDB Free instance and copy its `neo4j+s://...` URI and password.
2. In Render, create the Blueprint from `render.yaml`. Enter `NEO4J_URI`,
   `NEO4J_PASSWORD`, and `NEO4J_DATABASE` from Aura's credential file in Render's
   secret prompt.
3. In Vercel, deploy `frontend` as the project root. Set `VEDAGRAPH_API_URL` to the Render URL
   and `VEDANVAYA_SITE_URL` to the Vercel production URL, then deploy production.
4. Confirm `<render-url>/ready` returns `ready: true` before publishing the frontend URL.

Do not commit credentials, Aura passwords, or generated deployment dumps.
