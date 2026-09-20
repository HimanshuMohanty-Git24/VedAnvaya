"""Re-verify each of Agent B's 22 stale public claims against the tree as it now stands.

Anchored on the QUOTED TEXT rather than the line number, because the files moved under both
of us. A claim is CLEARED when the false string is gone; PRESENT means it survived.
"""
import json, os, pathlib, sys

sys.path.insert(0, 'src')
sys.path.insert(0, r'C:\Users\HKM49\AppData\Local\Temp\claude\d--VedaGraph\b3b65fb4-553d-43fa-9ae3-9b5ab16dede9\scratchpad')

ROOT = pathlib.Path('.')

# (family, file, the false substring that must be GONE)
CHECKS = [
    ('semantic_assertion_coverage', 'src/vedagraph/domain/layer_figures.py',
     '"HAS_SEMANTIC_ASSERTION": 4_865'),
    ('semantic_assertion_coverage', 'src/vedagraph/api/services/insight_service.py',
     'whose assertion row is NOT_BUILT for every'),
    ('rigveda_only_semantic_claims', 'src/vedagraph/api/services/entity_service.py',
     'The object dimension is derived from the Rigveda-only semantic assertion layer.'),
    ('rigveda_only_semantic_claims', 'src/vedagraph/api/services/entity_service.py',
     'The concept dimension is derived from the Rigveda-only annotation layers.'),
    ('cross_veda_directed_reuse_pair_count', 'frontend/src/lib/lab.ts',
     'was established for one corpus pair'),
    ('cross_veda_directed_reuse_pair_count', 'frontend/src/lib/lab.ts',
     'direction is only established separately, for one pair'),
    ('cross_veda_directed_reuse_pair_count', 'frontend/src/components/lab/plates/transmission.tsx',
     'The Rigveda-to-Samaveda pair is the only one for which direction was established'),
    ('cross_veda_directed_reuse_pair_count', 'frontend/src/components/lab/plates/transmission.tsx',
     'The other five pairs have no'),
    ('cross_veda_directed_reuse_pair_count', 'frontend/src/components/lab/plates/transmission.tsx',
     'the direction is recorded for this pair and not'),
    ('cross_veda_directed_reuse_pair_count', 'frontend/src/app/sources/page.tsx',
     'exists here for one corpus pair'),
    ('cross_veda_directed_reuse_pair_count', 'frontend/src/components/lab/plates/transmission.tsx',
     'Twelve of its 48 cells were never built and five'),
    ('cross_veda_matrix_cell_statuses', 'frontend/src/lib/lab.ts',
     'Twelve of the 48 cells are NOT_BUILT and five were never established'),
    ('atharvavedic_deity_ascription_scope', 'src/vedagraph/domain/taxonomy.py',
     '4,665 of its 5,839 mantras'),
    ('atharvavedic_deity_ascription_scope', 'src/vedagraph/domain/queries.py',
     '4,665 of its 5,839 mantras'),
    ('atharvavedic_deity_ascription_scope', 'src/vedagraph/domain/queries.py',
     'TWO DEITY-ATTRIBUTION PREDICATES'),
    ('atharvavedic_deity_ascription_scope', 'frontend/public/world/world.predicates.json',
     'A descriptor of the ascription\'s form, not a second deity attribution.'),
    # FAMILY-level, added after Agent B's R3 round (B-R3-C1 / m5). The first version of this
    # sweep cleared the 22 named INSTANCES and would have passed while entity_service still
    # shipped two caveats calling Atharvavedic dedication empty by construction -- the same
    # claim family, in a file nobody had listed. Clearing instances is not clearing families.
    ('atharvavedic_deity_ascription_scope', 'src/vedagraph/api/services/entity_service.py',
     'ATTRIBUTION IS NOT MENTION, AND IT IS RIGVEDIC'),
    ('atharvavedic_deity_ascription_scope', 'src/vedagraph/api/services/entity_service.py',
     'the Anukramani deity apparatus exists for the Rigveda only'),
    # Anchored on the ASSERTING form, not the words. The corrected file quotes the old
    # phrase in a note explaining why it was wrong -- "'Rigvedic by construction' was this
    # comment and it was wrong about the corpus" -- and a sweep that flagged that would be
    # demanding the project forget the defect. The claim was
    # `ASCRIBES to the deity. Rigvedic by construction.`; that exact sentence must be gone.
    ('atharvavedic_deity_ascription_scope', 'src/vedagraph/api/services/entity_service.py',
     'to the deity. Rigvedic by construction'),
    ('attribution_scope_stored_literal', 'src/vedagraph/domain/taxonomy.py',
     '"attribution_scope": ["RV"]'),
]

print(f"{'status':9s} {'family':40s} file :: quote")
present = 0
for family, rel, needle in CHECKS:
    text = (ROOT / rel).read_text(encoding='utf-8')
    gone = needle not in text
    if not gone:
        present += 1
    print(f"{'CLEARED' if gone else 'PRESENT':9s} {family:40s} {rel} :: {needle[:52]!r}")

# The measured families: declared == live, world groups, and the deity/ritual ones B verified.
from dotenv import load_dotenv
load_dotenv('D:/VedaGraph/.env')
from neo4j import GraphDatabase
from vedagraph.domain import layer_figures as lf

drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                           auth=(os.environ['NEO4J_USER'], os.environ['NEO4J_PASSWORD']))
with drv.session(database=os.environ['NEO4J_DATABASE']) as s:
    measured, declared = lf.measure(s), lf.declared()
drift = [k for k in sorted(set(declared) | set(measured)) if declared.get(k) != measured.get(k)]
print()
print('layer_figures_declared_vs_measured  drifted fields:', len(drift), drift)

import collections
raw = json.load(open('frontend/.world/world.raw.json', encoding='utf-8'))
gmap = json.load(open('frontend/scripts/world-groups.json', encoding='utf-8'))
unmapped = sum(1 for n in raw['nodes']
               if n['type'] != 'Devata' and n['type'] not in gmap)
print('world_type_group_mapping            nodes falling to "other":', unmapped)

print()
print(f'STALE_PUBLIC_CLAIMS_STILL_PRESENT = {present + len(drift) + (1 if unmapped else 0)}')
