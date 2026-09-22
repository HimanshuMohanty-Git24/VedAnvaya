# AuraDB Free deployment profile

This profile deploys a copy of VedaGraph. It never modifies the local Docker volume or the
local `.env` file.

## Intentional scope reduction

AuraDB Free allows at most 400,000 relationships. The full release contains 510,905. The
deployment copy removes only `MENTIONS_LEMMA` (154,261 internal lexical-index edges), leaving
353,781 relationships. Normal graph exploration and every corpus, passage, translation, entity,
deity, formula, ritual, and semantic relationship remain. Dictionary-headword search is disabled
and declares that limit in its API response.

## Cloud services

1. Create an AuraDB Free instance and copy its connection fields from the credential file.
2. In Render, create the Blueprint from `render.yaml`. Enter `NEO4J_URI`, `NEO4J_PASSWORD`,
   and `NEO4J_DATABASE` from Aura's credential file in Render's secret prompt.
3. In Vercel, deploy `frontend` as the project root. Set `VEDAGRAPH_API_URL` to the Render URL
   and `VEDANVAYA_SITE_URL` to the Vercel production URL, then deploy production.
4. Confirm `<render-url>/ready` returns `ready: true` before publishing the frontend URL.

Do not commit credentials, Aura passwords, or generated deployment dumps.
