import _q

def go(s):
    o = {}
    # --- ENTITY_COVERAGE-004
    o["EC004_domainentity_total"] = _q.one(s, "MATCH (n:DomainEntity) RETURN count(n)")
    o["EC004_expected_source_null"] = _q.one(s, "MATCH (n:DomainEntity) WHERE n.expected_source IS NULL RETURN count(n)")
    o["EC004_entity_keys_sample"] = _q.rows(s, "MATCH (n:DomainEntity) RETURN n.entity_key AS k, labels(n) AS l LIMIT 5")
    o["EC004_key_prefix_dist"] = _q.rows(s, "MATCH (n:DomainEntity) WITH split(n.entity_key,':') AS p RETURN p[1] AS ns, count(*) AS c ORDER BY c DESC")
    o["EC004_label_dist"] = _q.rows(s, "MATCH (n:DomainEntity) UNWIND labels(n) AS l WITH l, count(*) AS c WHERE l<>'DomainEntity' RETURN l,c ORDER BY c DESC")
    o["EC004_props"] = sorted({k for r in _q.rows(s, "MATCH (n:DomainEntity) RETURN keys(n) AS ks") for k in r["ks"]})
    # --- ENTITY_COVERAGE-006
    o["EC006_ayas_yv_mantras"] = _q.one(s, "MATCH (m:Mantra {veda:'YV'})-[:MENTIONS_ENTITY]->(e) WHERE e.entity_key='VG:CONCEPT:AYAS-METAL' RETURN count(DISTINCT m)")
    o["EC006_recall_prop_present"] = _q.rows(s, "MATCH (n:DomainEntity) RETURN count(n) AS total, count(n.recall_measured) AS recall_measured, count(n.recall_sample_size) AS sample")
    o["EC006_attested_in"] = _q.rows(s, "MATCH (a)-[r:ATTESTED_IN]->(b) RETURN labels(a) AS al, a.entity_key AS ak, labels(b) AS bl, b.canonical_key AS bk, properties(r) AS rp")
    # --- ENTITY_COVERAGE-007
    o["EC007_np_total"] = _q.one(s, "MATCH (n:NaturalPhenomenon) RETURN count(n)")
    o["EC007_pers_status_null"] = _q.one(s, "MATCH (n:NaturalPhenomenon) WHERE n.personification_status IS NULL RETURN count(n)")
    o["EC007_pers_dist"] = _q.rows(s, "MATCH (n:NaturalPhenomenon) RETURN n.personification_status AS st, count(*) AS c ORDER BY c DESC")
    o["EC007_np_rows"] = _q.rows(s, "MATCH (n:NaturalPhenomenon) RETURN n.entity_key AS k, n.label_iast AS iast, n.personification_status AS st, n.personified_as AS pa ORDER BY k")
    o["EC007_multiword"] = _q.one(s, "MATCH (n:DomainEntity) WHERE n.label_iast CONTAINS ' ' RETURN count(n)")
    # --- RITUAL-003
    o["R003_uses_object"] = _q.one(s, "MATCH ()-[r:USES_OBJECT]->() RETURN count(r)")
    o["R003_named"] = _q.rows(s, "UNWIND ['VG:CONCEPT:MANI-AMULET','VG:CONCEPT:DUNDUBHI-DRUM','VG:CONCEPT:AUDUMBARA-AMULET','VG:CONCEPT:YUPA-SACRIFICIAL-POST'] AS k MATCH (e {entity_key:k}) RETURN k, size([(x)-[:USES_OBJECT]->(e)|1]) AS wired, e.vedas_with_matches AS vwm")
    o["R003_ritual_total"] = _q.one(s, "MATCH (r:Ritual) RETURN count(r)")
    # --- RITUAL-005
    o["R005_receives_offering"] = _q.one(s, "MATCH ()-[r:RECEIVES_OFFERING]->() RETURN count(r)")
    o["R005_rites_with_offering"] = _q.one(s, "MATCH (r:Ritual) WHERE (r)-[:USES_OFFERING|HAS_OFFERING|INVOLVES_SUBSTANCE]->() RETURN count(r)")
    o["R005_ritual_rel_types"] = _q.rows(s, "MATCH (r:Ritual)-[x]->(y) RETURN type(x) AS t, labels(y) AS yl, count(*) AS c ORDER BY c DESC")
    # --- RITUAL-006
    o["R006_ctx_notnull"] = _q.one(s, "MATCH (m:Mantra) WHERE m.ritual_context IS NOT NULL RETURN count(m)")
    o["R006_ctx_dist"] = _q.rows(s, "MATCH (m:Mantra) RETURN m.ritual_context AS c, count(*) AS n ORDER BY n DESC")
    o["R006_method_props"] = _q.rows(s, "MATCH (m:Mantra) RETURN count(m) AS total, count(m.ritual_context_method) AS method, count(m.ritual_context_precision) AS precision")
    # --- SAMAVEDA_MUSIC-003
    o["SM003_sv_running_null"] = _q.one(s, "MATCH (m:Mantra {veda:'SV'}) WHERE m.running_samhita_number IS NULL RETURN count(m)")
    o["SM003_musicalized"] = _q.one(s, "MATCH ()-[r:MUSICALIZED_AS]->() RETURN count(r)")
    o["SM003_sv_props"] = sorted({k for r in _q.rows(s, "MATCH (m:Mantra {veda:'SV'}) RETURN keys(m) AS ks LIMIT 400") for k in r["ks"]})
    # --- SEMANTICS-003
    o["SEM003_target_nondevata"] = _q.one(s, "MATCH (a:SemanticAssertion)-[:ASSERTION_TARGET]->(x) WHERE NOT x:Devata RETURN count(*)")
    o["SEM003_total"] = _q.one(s, "MATCH (a:SemanticAssertion) RETURN count(a)")
    o["SEM003_slotfull"] = _q.one(s, "MATCH (a:SemanticAssertion) WHERE (a)-[:ASSERTION_AGENT]->() AND (a)-[:ASSERTION_PREDICATE]->() AND (a)-[:ASSERTION_TARGET]->() RETURN count(a)")
    o["SEM003_slot_rels"] = _q.rows(s, "MATCH (a:SemanticAssertion)-[r]->(x) RETURN type(r) AS t, labels(x) AS xl, count(*) AS c ORDER BY c DESC LIMIT 30")
    # --- QUALITY-003
    o["Q003_const_conf"] = _q.rows(s, """
      MATCH ()-[r]->() WHERE r.confidence IS NOT NULL
      WITH type(r) AS t, collect(DISTINCT r.confidence) AS vals, count(r) AS c
      RETURN t, size(vals) AS distinct_vals, vals[0..5] AS sample, c ORDER BY c DESC""")
    # --- TRANSLATION-004
    o["T004_rv_untranslated"] = _q.one(s, "MATCH (m:Mantra {veda:'RV'}) WHERE NOT (m)-[:HAS_TRANSLATION]->() RETURN count(m)")
    o["T004_rows"] = _q.rows(s, "MATCH (m:Mantra {veda:'RV'}) WHERE NOT (m)-[:HAS_TRANSLATION]->() RETURN m.canonical_key AS k ORDER BY k")
    # --- PRODUCT_SURFACE-005
    o["PS005_four"] = _q.rows(s, "UNWIND ['VG:SV:KAU:CHANDA:P01:D08:V04','VG:SV:KAU:ARANYA:D01:V04','VG:SV:KAU:CHANDA:P04:D05:V06','VG:SV:KAU:CHANDA:P02:D07:V07'] AS k MATCH (m:Mantra {canonical_key:k}) RETURN k, m.text_devanagari AS dev, m.content_sha256 AS sha")
    return o

_q.run(go)
