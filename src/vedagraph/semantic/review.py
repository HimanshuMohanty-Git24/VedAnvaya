"""Fast, local, blinded terminal review of EvidencePackets."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from vedagraph.models.semantic import (
    AdjudicationRecord,
    EvidencePacket,
    GoldAnnotation,
    GoldEntityAnnotation,
    GoldEvidenceReference,
    GoldRelation,
    GoldReviewMetadata,
    OntologyGap,
    SemanticAssertionCandidate,
)
from vedagraph.semantic.gold import (
    DEFAULT_ADJUDICATION_FILE,
    DEFAULT_GOLD_FILE,
    DEFAULT_PILOT_CONFIG,
    DEFAULT_PILOT_RUN,
    expected_gold_ids,
    load_gold_records,
    load_packet_index,
    progress,
    save_adjudication,
    save_gold_record,
    utc_now,
    validate_annotation,
)
from vedagraph.semantic.ontology import (
    ALLOWED_PREDICATES,
    PREDICATE_RULES,
    AdjudicationDecision,
    EvidenceReferenceType,
    Explicitness,
    GoldReviewStatus,
    OntologyGapKind,
    SemanticNodeType,
)

CONSOLE = Console()
IDENTITY_FILE = Path("data/gold/.reviewer_identity.json")


def _identity(path: Path, reviewer: str | None) -> str:
    if reviewer and reviewer.strip():
        value = reviewer.strip()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"reviewer": value}, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return value
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        value = payload.get("reviewer", "") if isinstance(payload, dict) else ""
        if isinstance(value, str) and value.strip():
            return value
    answer = str(typer.prompt("Reviewer name or id (not inferred from Git)")).strip()
    if not answer:
        raise typer.BadParameter("reviewer name/id cannot be empty")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"reviewer": answer}, ensure_ascii=False) + "\n", encoding="utf-8")
    return answer


def _show_dashboard(
    gold_path: Path, adjudication_path: Path, config_path: Path, reviewer: str
) -> None:
    state = progress(gold_path, adjudication_path, config_path)
    table = Table(title="VedaGraph semantic gold review")
    table.add_column("Gold dataset")
    table.add_column("Blinded complete")
    table.add_column("Adjudications")
    table.add_column("Remaining")
    table.add_column("Current reviewer")
    table.add_column("Predicates observed")
    table.add_column("Last saved")
    table.add_column("Gold status")
    table.add_row(
        str(state.total),
        str(state.blinded_complete),
        str(state.adjudications_complete),
        str(state.remaining),
        reviewer,
        ", ".join(state.predicates) or "none",
        state.last_saved or "none",
        state.status.value,
    )
    CONSOLE.print(table)
    CONSOLE.print(
        "Commands: [A] assertion  [R] rejected tempting  [E] entity  [O] ontology gap  "
        "[N] no claim  [S] save  [C/Enter] complete+next  "
        "[X] second review  [P] previous  [J] jump  [M] reveal model  [Q] quit"
    )


def _render_packet(packet: EvidencePacket, number: int, total: int) -> None:
    lines = [
        f"Gold item {number} / {total}",
        packet.citation,
        "",
        "[TEXT] SANSKRIT",
        packet.sanskrit,
        "",
        "[GRIFFITH TRANSLATION] TRANSLATION",
        (
            f"Translator: {packet.translation.translator}\n{packet.translation.text}"
            if packet.translation is not None
            else "Translation missing in local packet"
        ),
        "",
        "[TRADITIONAL METADATA]",
        f"Rishi: {', '.join(packet.rishi_labels) or 'none'}",
        f"Devata: {', '.join(packet.devata_labels) or 'none'}",
        f"Chandas: {', '.join(packet.chandas_labels) or 'none'}",
        "",
        "[LEXICAL DETERMINISTIC] MENTIONS",
    ]
    if packet.mentions:
        for mention in packet.mentions:
            lines.append(
                f"{mention.entity_key} | {mention.entity_label} | "
                f"tokens: {', '.join(mention.token_keys)}"
            )
    else:
        lines.append("none")
    lines.extend(["", "[MORPHOLOGY DETERMINISTIC] TOKENS"])
    if packet.tokens:
        lines.extend(
            f"{token.token_key} | {token.surface} | {token.lemma} | {token.morphology}"
            for token in packet.tokens
        )
    else:
        lines.append("none")
    lines.extend(["", "[CONTEXT]"])
    for label, neighbour in (
        ("Previous", packet.previous),
        ("Current", packet),
        ("Next", packet.next),
    ):
        if neighbour is None:
            lines.append(f"{label}: none")
        else:
            lines.append(f"{label}: {neighbour.citation} — {neighbour.sanskrit}")
    lines.extend(
        [
            "",
            "[PARALLEL DETERMINISTIC]",
            f"Exact: {', '.join(packet.exact_parallel_passage_keys) or 'none'}",
            f"Near: {', '.join(packet.near_parallel_passage_keys) or 'none'}",
            "",
            "[ONTOLOGY] allowed predicates: "
            + ", ".join(
                item.value for item in sorted(ALLOWED_PREDICATES, key=lambda item: item.value)
            ),
            "[ONTOLOGY DEFINITIONS]",
            *(
                f"{predicate.value}: {PREDICATE_RULES[predicate].definition}"
                for predicate in sorted(ALLOWED_PREDICATES, key=lambda item: item.value)
            ),
            "Allowed node types: " + ", ".join(item.value for item in SemanticNodeType),
            "Traditional assignment is context, not proof of a semantic relation.",
        ]
    )
    CONSOLE.print(Panel("\n".join(lines), title="BLINDED STAGE A", expand=False))


def _references(packet: EvidencePacket) -> list[GoldEvidenceReference]:
    available: list[tuple[EvidenceReferenceType, str]] = []
    available.extend(
        (EvidenceReferenceType.PASSAGE, key) for key in sorted(packet.citable_passage_keys)
    )
    available.extend((EvidenceReferenceType.TOKEN, item.token_key) for item in packet.tokens)
    if packet.translation is not None:
        available.append((EvidenceReferenceType.TRANSLATION, packet.translation.translation_id))
    available.extend((EvidenceReferenceType.ENTITY, item.entity_key) for item in packet.mentions)
    available.extend(
        (EvidenceReferenceType.TRADITIONAL_ASSERTION, key) for key in packet.devata_keys
    )
    available.extend(
        (EvidenceReferenceType.TRADITIONAL_ASSERTION, key) for key in packet.rishi_keys
    )
    available.extend(
        (EvidenceReferenceType.TRADITIONAL_ASSERTION, key) for key in packet.chandas_keys
    )
    available.extend(
        (EvidenceReferenceType.PARALLEL, key) for key in packet.exact_parallel_passage_keys
    )
    available.extend(
        (EvidenceReferenceType.PARALLEL, key) for key in packet.near_parallel_passage_keys
    )
    if not available:
        CONSOLE.print("No deterministic evidence ids supplied by this packet.")
        return []
    for index, (kind, reference_id) in enumerate(available, 1):
        CONSOLE.print(f"{index}. {kind.value}: {reference_id}")
    answer = typer.prompt("Evidence ids (comma-separated numbers, blank for none)", default="")
    result: list[GoldEvidenceReference] = []
    for raw in answer.split(","):
        if not raw.strip():
            continue
        try:
            kind, reference_id = available[int(raw.strip()) - 1]
        except (ValueError, IndexError) as error:
            raise typer.BadParameter("evidence selection must use the displayed numbers") from error
        result.append(GoldEvidenceReference(kind=kind, reference_id=reference_id))
    return result


def _choose_enum(prompt: str, values: list[str]) -> str:
    for index, value in enumerate(values, 1):
        CONSOLE.print(f"{index}. {value}")
    answer = typer.prompt(prompt)
    try:
        return values[int(answer) - 1]
    except (ValueError, IndexError) as error:
        raise typer.BadParameter("choose one of the displayed numbers") from error


def _add_entity(annotation: GoldAnnotation, packet: EvidencePacket) -> GoldAnnotation:
    node_type = SemanticNodeType(
        _choose_enum("Node type", [item.value for item in SemanticNodeType])
    )
    label = typer.prompt("Preferred label")
    canonical = typer.prompt("Existing canonical entity key (blank if none)", default="") or None
    new_candidate = canonical is None and typer.confirm(
        "Record as a new semantic-entity candidate?", default=False
    )
    item = GoldEntityAnnotation(
        node_type=node_type,
        preferred_label=label,
        existing_entity_key=canonical,
        new_semantic_entity_candidate=new_candidate,
        evidence=_references(packet),
        notes=typer.prompt("Entity notes", default=""),
    )
    return annotation.model_copy(update={"gold_entities": [*annotation.gold_entities, item]})


def _add_assertion(
    annotation: GoldAnnotation,
    packet: EvidencePacket,
    *,
    force_rejected: bool = False,
) -> GoldAnnotation:
    predicate = _choose_enum(
        "Predicate",
        [item.value for item in sorted(ALLOWED_PREDICATES, key=lambda item: item.value)],
    )
    label = typer.prompt("Object preferred label")
    canonical = typer.prompt("Object canonical entity key (blank if none)", default="") or None
    node_type = None
    if canonical is None:
        node_type = SemanticNodeType(
            _choose_enum("Object node type", [item.value for item in SemanticNodeType])
        )
    explicitness = Explicitness(_choose_enum("Explicitness", [item.value for item in Explicitness]))
    rejected = force_rejected or typer.confirm(
        "Record as a rejected tempting relation (not a supported gold claim)?", default=False
    )
    relation = GoldRelation(
        subject=packet.passage_key,
        predicate=predicate,
        object_label=label,
        object_entity_key=canonical,
        object_node_type=node_type,
        explicitness=explicitness,
        rejected=rejected,
        evidence=_references(packet),
        note=typer.prompt("Assertion notes", default=""),
    )
    if rejected:
        return annotation.model_copy(
            update={
                "rejected_tempting_relations": [
                    *annotation.rejected_tempting_relations,
                    relation,
                ]
            }
        )
    return annotation.model_copy(
        update={"gold_assertions": [*annotation.gold_assertions, relation], "no_claim": False}
    )


def _add_ontology_gap(annotation: GoldAnnotation) -> GoldAnnotation:
    kind = OntologyGapKind(
        _choose_enum("Ontology gap kind", [item.value for item in OntologyGapKind])
    )
    gap = OntologyGap(
        kind=kind,
        requested_value=typer.prompt("Requested node type or predicate"),
        notes=typer.prompt("Ontology-gap notes", default=""),
    )
    return annotation.model_copy(update={"ontology_gaps": [*annotation.ontology_gaps, gap]})


def _edit_annotation(annotation: GoldAnnotation) -> GoldAnnotation:
    """Edit a small, high-value part of the current human annotation."""
    choices = ["assertion", "entity", "notes"]
    kind = _choose_enum("Edit", choices)
    if kind == "notes":
        return annotation.model_copy(
            update={"notes": typer.prompt("Notes", default=annotation.notes)}
        )
    if kind == "assertion":
        items = annotation.effective_assertions
        if not items:
            CONSOLE.print("No assertions to edit.")
            return annotation
        index = typer.prompt("Assertion number", type=int) - 1
        if not 0 <= index < len(items):
            raise typer.BadParameter("assertion number is out of range")
        old = items[index]
        new = old.model_copy(
            update={
                "object_label": typer.prompt("Object label", default=old.object_label),
                "note": typer.prompt("Assertion notes", default=old.note),
            }
        )
        updated = list(items)
        updated[index] = new
        return annotation.model_copy(update={"gold_assertions": updated})
    if not annotation.gold_entities:
        CONSOLE.print("No entities to edit.")
        return annotation
    index = typer.prompt("Entity number", type=int) - 1
    if not 0 <= index < len(annotation.gold_entities):
        raise typer.BadParameter("entity number is out of range")
    updated_entities = list(annotation.gold_entities)
    old_entity = updated_entities[index]
    updated_entities[index] = old_entity.model_copy(
        update={
            "preferred_label": typer.prompt("Preferred label", default=old_entity.preferred_label),
            "notes": typer.prompt("Entity notes", default=old_entity.notes),
        }
    )
    return annotation.model_copy(update={"gold_entities": updated_entities})


def _blank_from(existing: GoldAnnotation, reviewer: str) -> GoldAnnotation:
    return existing.model_copy(
        update={
            "annotator": reviewer,
            "annotated_at": utc_now(),
            "review": GoldReviewMetadata(
                reviewer=reviewer,
                reviewed_at=utc_now(),
                status=GoldReviewStatus.IN_PROGRESS,
            ),
            "status": GoldReviewStatus.IN_PROGRESS,
        }
    )


def _persist(annotation: GoldAnnotation, path: Path, *, complete: bool = False) -> GoldAnnotation:
    status = GoldReviewStatus.COMPLETE if complete else annotation.effective_status
    if status is GoldReviewStatus.UNANNOTATED:
        status = GoldReviewStatus.IN_PROGRESS
    review = GoldReviewMetadata(
        reviewer=annotation.effective_reviewer,
        reviewed_at=utc_now(),
        status=status,
        stage_a_locked=complete,
        model_revealed_at=annotation.model_revealed_at,
        gold_modified_after_model_reveal=annotation.gold_modified_after_model_reveal,
        modification_reason=annotation.modification_reason,
    )
    updated = annotation.model_copy(
        update={
            "annotator": annotation.effective_reviewer,
            "annotated_at": review.reviewed_at,
            "relations": annotation.effective_assertions,
            "entities": annotation.effective_entity_labels,
            "status": status,
            "review": review,
        }
    )
    save_gold_record(updated, path)
    return updated


def _audit_model_edit(before: GoldAnnotation, after: GoldAnnotation) -> GoldAnnotation:
    """Require a reason when Stage A changes after model visibility."""
    if before.model_revealed_at is None:
        return after
    changed = (
        before.gold_entities != after.gold_entities
        or before.gold_assertions != after.gold_assertions
        or before.no_claim != after.no_claim
        or before.notes != after.notes
    )
    if not changed:
        return after
    reason = str(typer.prompt("Reason for changing gold after model reveal")).strip()
    if not reason:
        raise typer.BadParameter("a modification reason is required")
    return after.model_copy(
        update={
            "gold_modified_after_model_reveal": True,
            "modification_reason": reason,
        }
    )


def _candidate_rows(run_dir: Path, mantra_id: str) -> list[SemanticAssertionCandidate]:
    path = run_dir / "semantic_candidates.jsonl"
    if not path.exists():
        return []
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            candidate = SemanticAssertionCandidate.model_validate(json.loads(line))
            if candidate.subject_key == mantra_id:
                result.append(candidate)
    return result


def _reveal_model(
    annotation: GoldAnnotation,
    packet: EvidencePacket,
    reviewer: str,
    gold_path: Path,
    adjudication_path: Path,
    run_dir: Path,
) -> GoldAnnotation:
    if annotation.effective_status not in {GoldReviewStatus.COMPLETE, GoldReviewStatus.SIGNED}:
        CONSOLE.print("Stage B is unavailable: Stage A must be COMPLETE first.")
        return annotation
    revealed = annotation.model_copy(update={"model_revealed_at": utc_now()})
    revealed = _persist(revealed, gold_path, complete=True)
    candidates = _candidate_rows(run_dir, packet.passage_key)
    if not candidates:
        CONSOLE.print("Model revealed: Luna emitted no candidate for this mantra.")
        return revealed
    for candidate in candidates:
        CONSOLE.print(
            Panel(
                json.dumps(candidate.model_dump(mode="json"), ensure_ascii=False, indent=2),
                title="MODEL CANDIDATE — STAGE B",
            )
        )
        decision = AdjudicationDecision(
            _choose_enum("Human decision", [item.value for item in AdjudicationDecision])
        )
        category = (
            None
            if decision in {AdjudicationDecision.ACCEPT, AdjudicationDecision.REJECT}
            else decision
        )
        save_adjudication(
            AdjudicationRecord(
                mantra_id=packet.passage_key,
                candidate_assertion_id=candidate.candidate_assertion_id,
                human_decision=decision,
                error_category=category,
                notes=typer.prompt("Adjudication notes", default=""),
                reviewer=reviewer,
                timestamp=utc_now(),
            ),
            adjudication_path,
        )
    return revealed


def review_gold(
    *,
    gold_path: Path = DEFAULT_GOLD_FILE,
    adjudication_path: Path = DEFAULT_ADJUDICATION_FILE,
    config_path: Path = DEFAULT_PILOT_CONFIG,
    run_dir: Path = DEFAULT_PILOT_RUN,
    reviewer: str | None = None,
) -> None:
    """Run the local keyboard-driven two-stage reviewer."""
    reviewer_id = _identity(IDENTITY_FILE, reviewer)
    expected = expected_gold_ids(config_path)
    records = {item.passage_key: item for item in load_gold_records(gold_path)}
    packets = load_packet_index(run_dir)
    missing_packets = sorted(set(expected) - set(packets))
    if missing_packets:
        raise typer.BadParameter(
            f"local EvidencePackets missing ({len(missing_packets)}); expected "
            f"{run_dir}/batches/*/evidence.jsonl"
        )
    keys = sorted(expected)
    _show_dashboard(gold_path, adjudication_path, config_path, reviewer_id)
    current = next(
        (
            index
            for index, key in enumerate(keys)
            if records.get(key, None) is None
            or records[key].effective_status
            not in {GoldReviewStatus.COMPLETE, GoldReviewStatus.SIGNED}
        ),
        0,
    )
    while True:
        key = keys[current]
        packet = packets[key]
        base = records.get(key)
        if base is None:
            raise typer.BadParameter(f"gold worksheet is missing row {key}")
        annotation = base
        _render_packet(packet, current + 1, len(keys))
        CONSOLE.print(
            f"Stage A status: {annotation.effective_status.value}; "
            f"entities={len(annotation.gold_entities)} "
            f"assertions={len(annotation.effective_assertions)} "
            f"no_claim={annotation.no_claim}"
        )
        command = typer.prompt("Command", default="").strip().lower()
        if command in {"q", "quit"}:
            _persist(annotation, gold_path)
            CONSOLE.print("Saved. Review paused.")
            return
        if command in {"a", "assertion"}:
            annotation = _audit_model_edit(annotation, _add_assertion(annotation, packet))
            annotation = _persist(annotation, gold_path)
            records[key] = annotation
        elif command in {"e", "entity"}:
            annotation = _audit_model_edit(annotation, _add_entity(annotation, packet))
            annotation = _persist(annotation, gold_path)
            records[key] = annotation
        elif command in {"r", "rejected", "tempting"}:
            annotation = _audit_model_edit(
                annotation, _add_assertion(annotation, packet, force_rejected=True)
            )
            records[key] = _persist(annotation, gold_path)
        elif command in {"o", "gap", "ontology gap"}:
            annotation = _audit_model_edit(annotation, _add_ontology_gap(annotation))
            records[key] = _persist(annotation, gold_path)
        elif command in {"d", "edit"}:
            annotation = _audit_model_edit(annotation, _edit_annotation(annotation))
            annotation = _persist(annotation, gold_path)
            records[key] = annotation
        elif command in {"n", "no"}:
            annotation = annotation.model_copy(update={"no_claim": True, "gold_assertions": []})
            annotation = _audit_model_edit(base, annotation)
            records[key] = _persist(annotation, gold_path)
        elif command in {"s", "save"}:
            records[key] = _persist(annotation, gold_path)
        elif command in {"x", "second"}:
            annotation = annotation.model_copy(
                update={"status": GoldReviewStatus.NEEDS_SECOND_REVIEW}
            )
            records[key] = _persist(annotation, gold_path)
        elif command in {"c", "", "enter", "next"}:
            issues = validate_annotation(annotation, packet, require_complete=False)
            if issues:
                CONSOLE.print("Cannot complete: " + "; ".join(issues))
                continue
            records[key] = _persist(annotation, gold_path, complete=True)
            if current == len(keys) - 1:
                CONSOLE.print(
                    "Gold subset reached; use validate/finalize when all rows are complete."
                )
                return
            current += 1
        elif command in {"p", "previous"}:
            current = max(0, current - 1)
        elif command in {"k", "skip", "skip-temporarily"}:
            records[key] = _persist(annotation, gold_path)
            if current < len(keys) - 1:
                current += 1
        elif command in {"summary"}:
            _show_dashboard(gold_path, adjudication_path, config_path, reviewer_id)
        elif command in {"j", "jump"}:
            wanted = typer.prompt("Gold item number", type=int)
            if not 1 <= wanted <= len(keys):
                CONSOLE.print("Item number is out of range")
            else:
                current = wanted - 1
        elif command in {"m", "model", "reveal model"}:
            records[key] = _reveal_model(
                annotation, packet, reviewer_id, gold_path, adjudication_path, run_dir
            )
        elif command in {"h", "help"}:
            CONSOLE.print(
                "A/E add; R rejected tempting; O ontology gap; D edit; N no claim; S save; "
                "C or Enter complete; X second review; "
                "K skip; P previous; J jump; M reveal model after lock; Q quit"
            )
        else:
            CONSOLE.print("Unknown command; press H for help.")
        if command not in {"q", "quit"}:
            _show_dashboard(gold_path, adjudication_path, config_path, reviewer_id)
