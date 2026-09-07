# V3.2 prompt-policy proposal

NO HUMAN GOLD EXISTS.

MODEL SELF-AGREEMENT IS NOT ACCURACY.


Decision: `V3_2_PROMPT_POLICY_REVISION_REQUIRED`. This is a design only; no Luna run was executed and the V3.1 prompt, schema,
ontology, execution contract, sealed outputs, and receipts remain unchanged.

## Minimal proposed policy patch

1. **Emit-vs-omit floor.** After the fourteen-family pass, emit every relation whose relation force
and target/object are both directly anchored. “Optional” means the evidence does not settle a policy
boundary, not that a directly evidenced independent family may be randomly skipped.
2. **REQUESTS force.** Treat an imperative, optative, prohibitive wish, or explicit
“grant/give/bring/send/bestow/may” construction as request force when the speaker seeks an outcome
from an addressee. The requested outcome is the desired resulting state/action, not automatically
the grammatical object of the verb.
3. **REQUESTS outcomes.** Emit one outcome per independently coordinated desired state. Keep a
modifier/beneficiary inside one outcome; split only when each conjunct can stand as a separately
desired result. Do not emit an unresolved “that which ...” as an additional outcome unless its
referent is independently anchored.
4. **DESCRIBES precedence.** DESCRIBES targets an entity only for attributed state/quality or an
entity-level depiction. A clause whose only descriptive content is an action emits DESCRIBES_ACTION,
not an additional DESCRIBES. If the clause independently attributes both a state/quality and an
action, both may be emitted with separate relation anchors.
5. **DESCRIBES_ACTION scope.** Use it for asserted/narrated actions. An imperative action belongs
under REQUESTS as a desired action/outcome unless the passage also states that the action occurs.
6. **Material/ritual co-emission.** A named material or ritual referent may co-exist with an
action/request assertion only when each relation has its own direct local anchor. Repeated mentions
do not create duplicate passage-level predicate/object assertions unless distinct typed roles or
qualifiers are asserted.
7. **No-claim criterion.** No claim is permitted only when no allowed family passes the direct
relation-plus-object test after applying these precedence rules; record the failed family/boundary
in the reason without inventing semantics.

## What stays unchanged

Keep `semantic_extraction_v3.schema.json`, the predicate ontology, typed-object schema, CODEX_DIRECT
receipt contract, evidence-span validation, and assertion binding validation unchanged. The audit
found no machinery defect. The version change is the prompt policy identifier
`rigveda-semantic-extraction-v3.2`; implementation must regenerate the prompt hash and run contract
before the future bounded run.

## Anti-overfitting and authorship

The rules use generic grammatical/policy conditions and contain no benchmark IDs. Validators may
reject structural, provenance, type, span, or binding violations, but may not author a relation or
force deterministic semantic output through regex rules. Luna remains the semantic author.
