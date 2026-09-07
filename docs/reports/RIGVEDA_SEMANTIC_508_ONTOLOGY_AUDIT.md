# V3 508 ontology audit

Engineering diagnostics, not Vedic expertise, HUMAN_GOLD, or canonical truth. All existing output stays CANDIDATE / NEEDS_REVIEW; unlocked_predicates = []. No extraction was performed in this audit.

## Decision

`KEEP_GAPS_FOR_FULL_RUN`. No object ontology V2 is required. This is not full-run authorization.
The existing gap object safely preserves unresolved occurrences; bad gap emission/anchoring is
an extractor defect, not proof that a new type is needed. No result was repaired.

All 70 gap objects were inspected (61 person-like, 8 patron, 1 kinship), not sampled.
One gap can summarize several mentions; these are 70 objects, not a count of distinct humans.
Classifications: {"CANONICAL_ENTITY_RESOLUTION_MISSED": 2, "EXPERT_PHILOLOGY_REQUIRED": 2, "EXTRACTION_OVERREACH": 4, "INTENTIONAL_OPAQUE_CASE": 1, "TRUE_SCHEMA_GAP": 60, "WRONG_GAP_CODE": 1}.
Substring anchor defects: **14**. Offsets are zero-based, end-exclusive.
A TRUE_SCHEMA_GAP can also have defective evidence anchoring; primary ontology classification
and engineering blocker are independent. These are engineering readings of supplied translation,
checked against packet mentions; not Sanskrit adjudications.

## Person-like conclusion and options

57 of 61 person-like records support a useful generic human occurrence on supplied English evidence;
2 require philological resolution, 1 is a simile kept opaque, and 1 is an idiom overreach.
Do not convert stored gaps automatically: evidence spans and literal-human status must first pass.
PERSON_REF would improve querying but is optional, not a canonical person registry. Preserve number,
indefiniteness, negation and comparison scope; never infer a human from a divine epithet or name alone.
Packet-provided canonical identity takes precedence only when the referent itself is resolved;
traditional rishi/devata assignment is not identity proof for an occurrence.

| Option | Benefit | Risk / decision |
| --- | --- | --- |
| Keep evidenced gaps | No extraction-schema migration, auditable uncertainty | Recommended now; repair execution bugs separately |
| PERSON_REF plus evidenced role qualifiers | Human occurrence without canonical person registry; patron/kinship/ancestor avoid kind proliferation | Optional later version; roles need evidence, kinship needs relata and must allow unknown relata |
| Separate PATRON/KINSHIP/ANCESTOR kinds | Explicit role indexing | Confuses role with ontological type; divine/nonhuman kinship does not imply PERSON_REF |
| Canonical person registry | Cross-occurrence identity | Out of scope; unsupported names must never create canonical identity |

Only 3 of 8 patron records support human donor typing. The 1 kinship record concerns goddesses/rivers,
so PERSON_REF + KINSHIP is unsafe there. No ancestor occurrence was observed; its future role design
is conceptual only. A role can relate deities or natural referents and need not imply a human.

## Complete occurrence ledger

| # | Mantra | Object ID | Original code | Classification | PERSON_REF | Stored span | Diagnostic | Gate | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | RV 1.13.11 | VG:SEMOBJ:F8CF7C27140FFEE3C797 | PATRON_ROLE_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 76:81 'giver' | Oblation giver is a donor role, separate from the addressed Wood deity. | DOES_NOT_BLOCK_FULL_RUN |  |
| 2 | RV 1.35.5 | VG:SEMOBJ:16F7FAFCADF25A5C2890 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 56:59 'man' | All men is a human collective distinct from Savitar; the stored span instead hits manifested. | BLOCKS_FULL_RUN | B02 |
| 3 | RV 1.43.6 | VG:SEMOBJ:8C760A88CDB657888F7B | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 72:75 'men' | Men and women are explicitly contrasted with livestock; one group occurrence need not identify persons. | DOES_NOT_BLOCK_FULL_RUN |  |
| 4 | RV 1.51.9 | VG:SEMOBJ:2B1FB41CD503A34D0061 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 40:43 'man' | The pious man is the beneficiary, distinct from the mentioned Indra. | DOES_NOT_BLOCK_FULL_RUN |  |
| 5 | RV 1.61.3 | VG:SEMOBJ:832DD9EF729F319EAB6F | PATRON_ROLE_UNMODELED | EXTRACTION_OVERREACH | UNSAFE | 171:176 'Giver' | Most bounteous Giver qualifies the addressed Lord, not an evidenced human patron. | BLOCKS_FULL_RUN | B01 |
| 6 | RV 1.83.1 | VG:SEMOBJ:902B68ED70B2ED1797D5 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 18:21 'man' | Mortal man is the beneficiary guarded by Indra, not Indra himself. | DOES_NOT_BLOCK_FULL_RUN |  |
| 7 | RV 1.120.8 | VG:SEMOBJ:99008A083CE83BDF02C2 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 22:25 'man' | Any man who hates us is an indefinite adversary; do not invent an identity. | DOES_NOT_BLOCK_FULL_RUN |  |
| 8 | RV 1.122.8 | VG:SEMOBJ:42615F880B92B826A3A2 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 99:102 'man' | Men with hero children is a human group; wealthy chief is a separate donor context. | BLOCKS_FULL_RUN | B02 |
| 9 | RV 1.127.2 | VG:SEMOBJ:DC01F3196969AA781714 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 207:210 'men' | Priest of men includes a human collective distinct from the invoked Priest. | DOES_NOT_BLOCK_FULL_RUN |  |
| 10 | RV 1.133.6 | VG:SEMOBJ:9E1C46BB5DAB4BFB71DA | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 236:239 'men' | Not slaying men still mentions humans; negation must remain attached to any proposed event. | DOES_NOT_BLOCK_FULL_RUN |  |
| 11 | RV 1.137.3 | VG:SEMOBJ:F6B32CFAEBB72E5D7E59 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 182:185 'men' | The men pressed juice identifies human ritual participants, distinct from Soma and the addressees. | DOES_NOT_BLOCK_FULL_RUN |  |
| 12 | RV 1.150.3 | VG:SEMOBJ:283BD66BA3D0980AAE7C | PERSON_LIKE_REFERENT_UNMODELED | EXPERT_PHILOLOGY_REQUIRED | EXPERT_REQUIRED | 28:31 'man' | That man, mightiest in heaven may be a figurative or divine referent; human typing is unsafe. | DOES_NOT_BLOCK_FULL_RUN |  |
| 13 | RV 3.4.8 | VG:SEMOBJ:BE8AE343984497D95C59 | KINSHIP_ROLE_UNMODELED | WRONG_GAP_CODE | UNSAFE | 106:113 'kindred' | Sisters and kindred Rivers relate to Three Goddesses; the human kinship gap code is misapplied. | BLOCKS_FULL_RUN | B01 |
| 14 | RV 3.17.3 | VG:SEMOBJ:8B634F34B4CF1EEC1A28 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 176:179 'man' | The man who worships is the beneficiary of help, distinct from Agni. | DOES_NOT_BLOCK_FULL_RUN |  |
| 15 | RV 3.62.2 | VG:SEMOBJ:706335D939736454F154 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 5:8 'man' | This diligent man invokes the addressees; the worshipper is not the canonical Maruts or Earth. | DOES_NOT_BLOCK_FULL_RUN |  |
| 16 | RV 4.1.1 | VG:SEMOBJ:6B51D7A700BF30B87628 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 173:176 'men' | Mortal men explicitly contrast with immortal Agni. | DOES_NOT_BLOCK_FULL_RUN |  |
| 17 | RV 4.19.10 | VG:SEMOBJ:3A14479DD5D3749E2792 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 12:15 'man' | Wise man and man's advantage supply a human referent without establishing a named person. | DOES_NOT_BLOCK_FULL_RUN |  |
| 18 | RV 5.17.1 | VG:SEMOBJ:E6AF8391B1A080164B07 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 71:74 'man' | A mortal/man calls Agni; human actor and invoked deity remain separate. | DOES_NOT_BLOCK_FULL_RUN |  |
| 19 | RV 5.53.16 | VG:SEMOBJ:E777B236161E97E5F57A | PATRON_ROLE_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 40:46 'patron' | Liberal patron's rite supports a donor role; Free-givers elsewhere does not identify that patron. | DOES_NOT_BLOCK_FULL_RUN |  |
| 20 | RV 5.87.8 | VG:SEMOBJ:E67E7DD133D3AA6A78CA | PERSON_LIKE_REFERENT_UNMODELED | INTENTIONAL_OPAQUE_CASE | UNSAFE | 111:114 'men' | Like car-borne men is a comparison applied to Maruts; retain opaque comparison, not literal humans. | DOES_NOT_BLOCK_FULL_RUN |  |
| 21 | RV 6.45.19 | VG:SEMOBJ:3C89C743EFFC34A4F8A8 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 68:71 'man' | Lowly man is the one helped by the addressed Friend; identity unresolved but human type supportable. | DOES_NOT_BLOCK_FULL_RUN |  |
| 22 | RV 6.47.17 | VG:SEMOBJ:3FECEADE9790BDD51D1D | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 163:166 'man' | Men whose worship is rejected are distinct from Indra. | BLOCKS_FULL_RUN | B02 |
| 23 | RV 6.48.15 | VG:SEMOBJ:BE7F6BAF849A4A601550 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 138:141 'men' | Our men are human beneficiaries; the canonical Pusan is not their identity. | DOES_NOT_BLOCK_FULL_RUN |  |
| 24 | RV 7.4.3 | VG:SEMOBJ:C150245D08C8952CC04C | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 166:169 'man' | Men seize Agni and he shines for man; human collective contrasts with Agni. | DOES_NOT_BLOCK_FULL_RUN |  |
| 25 | RV 7.15.7 | VG:SEMOBJ:38434ABF08EA094EF05B | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 24:27 'men' | Men must seek the Lord of the house; humans and Agni are distinct. | DOES_NOT_BLOCK_FULL_RUN |  |
| 26 | RV 7.32.20 | VG:SEMOBJ:41D69E310BF329764969 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 41:44 'man' | Active man gains spoil; the later named Indra is not that man's registry identity. | DOES_NOT_BLOCK_FULL_RUN |  |
| 27 | RV 8.1.17 | VG:SEMOBJ:DAE51FC332AF19D729EF | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 73:76 'men' | Men wash and dress Soma; physical milk and human operators are separate occurrences. | DOES_NOT_BLOCK_FULL_RUN |  |
| 28 | RV 8.2.6 | VG:SEMOBJ:5339288468AC790E2BB6 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 12:15 'men' | Other men than we identifies people without canonical identities. | DOES_NOT_BLOCK_FULL_RUN |  |
| 29 | RV 8.2.39 | VG:SEMOBJ:D5B8148C25B67F504377 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 70:73 'men' | Cattle restored to men distinguishes human beneficiaries from livestock. | DOES_NOT_BLOCK_FULL_RUN |  |
| 30 | RV 8.6.37 | VG:SEMOBJ:F947ECB327DF4961021A | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 23:26 'men' | Men with prepared grass invoke the unnamed addressee; no deity identity for the human group. | DOES_NOT_BLOCK_FULL_RUN |  |
| 31 | RV 8.21.14 | VG:SEMOBJ:06C8A7EE875243DECD97 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 29:32 'man' | Wealthy man and scorners are human referents; Father is a separate comparison. | DOES_NOT_BLOCK_FULL_RUN |  |
| 32 | RV 8.23.14 | VG:SEMOBJ:10D60618AA400F347C99 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 21:24 'men' | Lord of men refers to a human collective governed by Agni. | DOES_NOT_BLOCK_FULL_RUN |  |
| 33 | RV 8.43.24 | VG:SEMOBJ:460C9F92154884B955B4 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 24:27 'men' | King of men similarly distinguishes human collective from Agni. | DOES_NOT_BLOCK_FULL_RUN |  |
| 34 | RV 8.45.42 | VG:SEMOBJ:1BB478FFAFC4819B8660 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 32:35 'men' | World of men denotes a human collective; do not mint a world/person canonical entity. | DOES_NOT_BLOCK_FULL_RUN |  |
| 35 | RV 8.46.2 | VG:SEMOBJ:FC47DD6B982F2168153C | PATRON_ROLE_UNMODELED | EXTRACTION_OVERREACH | UNSAFE | 48:53 'giver' | Giver refers to the addressed Hurler of the Bolt; no human patron is evidenced by that epithet. | BLOCKS_FULL_RUN | B01 |
| 36 | RV 8.46.21 | VG:SEMOBJ:F76BA8FD5C8B841D1812 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 20:23 'man' | Godless man and named recipients are human; names alone are not supplied canonical IDs. | DOES_NOT_BLOCK_FULL_RUN |  |
| 37 | RV 8.46.27 | VG:SEMOBJ:0A9E044472193AA5DD62 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 134:137 'man' | A man yet more devout is a recipient in gift context; do not resolve Nahup from memory. | DOES_NOT_BLOCK_FULL_RUN |  |
| 38 | RV 8.60.11 | VG:SEMOBJ:7828FF617C5E5EF63E48 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 105:108 'man' | Wealth renowned with men supports human audience; stored span hits many instead. | BLOCKS_FULL_RUN | B02 |
| 39 | RV 8.93.1 | VG:SEMOBJ:B73A5D14EFB0F2ACD40D | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 97:100 'man' | Works for man supports human beneficiary distinct from Surya and the Hero. | DOES_NOT_BLOCK_FULL_RUN |  |
| 40 | RV 9.4.9 | VG:SEMOBJ:A678CCEB5978653A8F53 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 16:19 'man' | Men have strengthened Pavamana supplies human worshippers; stored span hits Pavamana. | BLOCKS_FULL_RUN | B02 |
| 41 | RV 9.20.2 | VG:SEMOBJ:0DC4F8B26A9253989CB4 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 15:18 'man' | Singing-men are human recipients of treasure, distinct from Pavamana. | BLOCKS_FULL_RUN | B02 |
| 42 | RV 9.39.2 | VG:SEMOBJ:08898BD88BD68FDB57A2 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 60:63 'man' | Food to man supplies human beneficiary; rain/heaven are separate referents. | DOES_NOT_BLOCK_FULL_RUN |  |
| 43 | RV 9.45.6 | VG:SEMOBJ:AFBCC451DB6AAA196F76 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 68:71 'man' | The man who worships Indu is human; no new Indu identity may be invented. | DOES_NOT_BLOCK_FULL_RUN |  |
| 44 | RV 9.52.5 | VG:SEMOBJ:902140BABC5B9113978C | PATRON_ROLE_UNMODELED | EXTRACTION_OVERREACH | UNSAFE | 13:18 'giver' | Wealth-giver addresses Indu; a human patron cannot be inferred from giver. | BLOCKS_FULL_RUN | B01 |
| 45 | RV 9.64.13 | VG:SEMOBJ:9C1C326D4EEBB7F7C763 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 62:65 'men' | Sapient men prepare the flow; Indu remains distinct from human operators. | DOES_NOT_BLOCK_FULL_RUN |  |
| 46 | RV 9.86.38 | VG:SEMOBJ:FBBA2642A3AB526107C5 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 50:53 'man' | Men seen by Soma are distinct from the addressed Soma/Pavamana. | BLOCKS_FULL_RUN | B02 |
| 47 | RV 9.87.4 | VG:SEMOBJ:57FDA1FC392FFECBBC61 | PATRON_ROLE_UNMODELED | CANONICAL_ENTITY_RESOLUTION_MISSED | UNSAFE | 110:115 'giver' | Free-giver continues the supplied Soma referent; an existing SOMAH mention is available, not a new patron. | BLOCKS_FULL_RUN | B01 |
| 48 | RV 9.87.9 | VG:SEMOBJ:A87A920F3FE97AB232CD | PATRON_ROLE_UNMODELED | CANONICAL_ENTITY_RESOLUTION_MISSED | UNSAFE | 133:138 'Giver' | Prompt Giver continues the addressed Soma; supplied SOMAH exists, while Indra is the companion. | BLOCKS_FULL_RUN | B01 |
| 49 | RV 10.7.5 | VG:SEMOBJ:E13EEDB36EF5C1D34854 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 0:3 'Men' | Men generate/stablish Agni; human actors are not the AGNIH or MITRAH mention. | DOES_NOT_BLOCK_FULL_RUN |  |
| 50 | RV 10.14.1 | VG:SEMOBJ:48999B99D1D9CF8439AC | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 170:173 'man' | Yama gathers men; Vivasvan's Son identifies the King, not requested offspring or the human group. | BLOCKS_FULL_RUN | B02 |
| 51 | RV 10.18.8 | VG:SEMOBJ:58E4609B2C25E2F1BA23 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 39:42 'man' | Woman, wife and husband are evidenced humans; the stored man substring inside woman is not a full referent span. | BLOCKS_FULL_RUN | B02 |
| 52 | RV 10.20.4 | VG:SEMOBJ:0115ACB11CF481804B8E | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 19:22 'men' | Furtherer of men distinguishes human beneficiaries from the described agent. | DOES_NOT_BLOCK_FULL_RUN |  |
| 53 | RV 10.25.1 | VG:SEMOBJ:B3A81CD5D3561DDFD3A4 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 47:50 'men' | Let men joy names a human group; stored men inside mental is a misleading span. | BLOCKS_FULL_RUN | B02 |
| 54 | RV 10.27.13 | VG:SEMOBJ:4D2ABF72CD8068FFAB46 | PERSON_LIKE_REFERENT_UNMODELED | EXPERT_PHILOLOGY_REQUIRED | EXPERT_REQUIRED | 35:38 'man' | The man eaten in this riddle is not safely resolvable as literal human; retain philological uncertainty. | DOES_NOT_BLOCK_FULL_RUN |  |
| 55 | RV 10.39.11 | VG:SEMOBJ:8AE85486DA5DBCB71AD7 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 102:105 'man' | The man protected by the Asvins is a human beneficiary; no supplied named person identity. | DOES_NOT_BLOCK_FULL_RUN |  |
| 56 | RV 10.41.1 | VG:SEMOBJ:ADAA67E7C2A1BA344A9C | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 38:41 'man' | Many a man invokes the Car; Dawn metadata/mention does not make Dawn the invoked target. | BLOCKS_FULL_RUN | B02 |
| 57 | RV 10.50.3 | VG:SEMOBJ:A96A39423F19065E4AC2 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 12:15 'men' | Question who are the men explicitly concerns humans; no named identity is established. | DOES_NOT_BLOCK_FULL_RUN |  |
| 58 | RV 10.86.1 | VG:SEMOBJ:DA8AD1026262D55B9E6A | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 0:3 'MEN' | Men abstain from pouring; preserve negation rather than infer actual offering from the action word. | DOES_NOT_BLOCK_FULL_RUN |  |
| 59 | RV 10.89.8 | VG:SEMOBJ:BCA8077058D1FB64CA8B | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 99:102 'men' | Men who injure law are distinct from Indra, Varuna and Mitra. | DOES_NOT_BLOCK_FULL_RUN |  |
| 60 | RV 10.97.7 | VG:SEMOBJ:20F5C66433C07F8AE961 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 120:123 'man' | This man may be whole again identifies a human beneficiary of herbs. | DOES_NOT_BLOCK_FULL_RUN |  |
| 61 | RV 10.98.8 | VG:SEMOBJ:CB96CDF2F28C30B0D83B | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 41:44 'man' | Devapi Arstisena is called mortal man, but no person entity key is supplied in packet mentions. | DOES_NOT_BLOCK_FULL_RUN |  |
| 62 | RV 10.102.2 | VG:SEMOBJ:9F3B3ACDDDD654EDE60B | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 24:27 'man' | Woman and Mudgalani support a human occurrence; do not equate a name with a canonical key. | BLOCKS_FULL_RUN | B02 |
| 63 | RV 10.107.10 | VG:SEMOBJ:DA5E4CDBA2C96973749F | PATRON_ROLE_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 44:49 'giver' | Bounteous giver, maid and his home support a human donor role without a global patron registry. | DOES_NOT_BLOCK_FULL_RUN |  |
| 64 | RV 10.118.1 | VG:SEMOBJ:EDFE96AE21E512A3678A | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 22:25 'men' | Men among whom Agni shines are human collective, distinct from Agni. | DOES_NOT_BLOCK_FULL_RUN |  |
| 65 | RV 10.126.6 | VG:SEMOBJ:E9DE2354F9495F60B11C | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 50:53 'man' | Living men are governed by the named gods; stored man inside Aryaman is wrong anchoring. | BLOCKS_FULL_RUN | B02 |
| 66 | RV 10.146.5 | VG:SEMOBJ:A30FD65B1B9B8647A906 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 63:66 'Man' | Man eats fruit contrasts with Goddess; do not type Aranyani as this person. | DOES_NOT_BLOCK_FULL_RUN |  |
| 67 | RV 10.151.2 | VG:SEMOBJ:561933FE114CE426EF01 | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 15:18 'man' | Man who gives and liberal worshippers support humans with optional donor role. | DOES_NOT_BLOCK_FULL_RUN |  |
| 68 | RV 10.151.4 | VG:SEMOBJ:95C5C925EF83756D5E1E | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 64:67 'Man' | Gods and men explicitly distinguish humans from deities in sacrificial context. | DOES_NOT_BLOCK_FULL_RUN |  |
| 69 | RV 10.170.1 | VG:SEMOBJ:1992DB70F9C8B38FC568 | PERSON_LIKE_REFERENT_UNMODELED | EXTRACTION_OVERREACH | UNSAFE | 121:127 'person' | In person is an idiom about the Bright God, not an additional human referent. | BLOCKS_FULL_RUN | B01 |
| 70 | RV 10.183.2 | VG:SEMOBJ:46291DEF49F108C5B10C | PERSON_LIKE_REFERENT_UNMODELED | TRUE_SCHEMA_GAP | USEFUL | 115:118 'man' | Youthful woman and her offspring support human occurrence; no canonical person registry is implied. | BLOCKS_FULL_RUN | B02 |
