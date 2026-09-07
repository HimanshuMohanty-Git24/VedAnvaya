# Rigveda semantic disagreements

**NO HUMAN GOLD EXISTS YET. These are model-vs-model silver metrics, not human-gold accuracy.**

## Major patterns

- Luna emitted only `INVOKES` in this selected subset; Sol used
  **11** predicates.
- Explicit Luna-missed relations: **210**.
- Non-explicit Sol-only relations: **3**.
- Wrong-predicate alignments: **4**.
- Wrong-entity alignments: **0**.
- Partial matches: **1**.
- Luna unsupported-only claims: **0**.
- `SEMANTIC_EXTRACTION_RECALL_GAP`: **flagged**.

The large gap is a model-model diagnostic, not proof that every Sol relation is correct.
The dominant pattern supports `LUNA_TOO_CONSERVATIVE`, `PROMPT_REVISION_REQUIRED`, and
`SECOND_PILOT_REQUIRED`. Cases with opaque referents or person-role ontology gaps remain
`DISAGREEMENT_REQUIRES_EXPERT` in the audit plan rather than being treated as Sol wins.

## Complete disagreement index

- `VG:RV:SAK:M01:S005:V003` — LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/assistance and wealth
- `VG:RV:SAK:M01:S014:V004` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_OFFERING/poured juices, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_SUBSTANCE/meath drops
- `VG:RV:SAK:M01:S025:V016` — LUNA_MISSED_RELATION: Luna=none/none; Sol=EXPRESSES/yearning
- `VG:RV:SAK:M01:S035:V005` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/savitā
- `VG:RV:SAK:M01:S036:V018` — LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/bringing named allies
- `VG:RV:SAK:M01:S043:V006` — LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/health and wellbeing
- `VG:RV:SAK:M01:S051:V009` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/indraḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/destroying the lawless
- `VG:RV:SAK:M01:S058:V001` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/agniḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_OFFERING/oblation
- `VG:RV:SAK:M01:S061:V003` — LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/indraḥ
- `VG:RV:SAK:M01:S062:V008` — LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_NATURAL_PHENOMENON/night, LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_NATURAL_PHENOMENON/dawn
- `VG:RV:SAK:M01:S094:V013` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/agniḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/agniḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/protection from harm
- `VG:RV:SAK:M01:S101:V005` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/indraḥ
- `VG:RV:SAK:M01:S104:V005` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/indraḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/remembrance and continued favor
- `VG:RV:SAK:M01:S127:V002` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/agniḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/agniḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/sacrifice
- `VG:RV:SAK:M01:S136:V007` — LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/shelter and success
- `VG:RV:SAK:M01:S148:V004` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/agniḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_NATURAL_PHENOMENON/wind
- `VG:RV:SAK:M01:S154:V006` — LUNA_MISSED_RELATION: Luna=none/none; Sol=EXPRESSES/desire to reach the dwelling, LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_PLACE/the widely-striding Bull's sublimest mansion
- `VG:RV:SAK:M01:S157:V005` — WRONG_PREDICATE: Luna=INVOKES/aśvinau; Sol=DESCRIBES/aśvinau, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/storing life and sending forth fire and waters
- `VG:RV:SAK:M01:S162:V021` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/the horse's journey to the Gods, SOL_ONLY_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/animal immolation
- `VG:RV:SAK:M01:S173:V006` — LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/indraḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/indraḥ
- `VG:RV:SAK:M01:S179:V001` — LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_NATURAL_PHENOMENON/uṣāḥ
- `VG:RV:SAK:M02:S008:V006` — LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/protection and victory
- `VG:RV:SAK:M02:S017:V005` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/stabilizing hills, earth, and heaven and directing waters, LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_NATURAL_PHENOMENON/downward-rushing waters
- `VG:RV:SAK:M03:S011:V004` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/agniḥ
- `VG:RV:SAK:M03:S035:V011` — LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/indraḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/slaying the Vrtras and gathering riches
- `VG:RV:SAK:M04:S001:V008` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/agniḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/agniḥ
- `VG:RV:SAK:M04:S011:V006` — LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/agniḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/agniḥ
- `VG:RV:SAK:M04:S022:V006` — LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/indraḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/rivers moving swiftly in fear, LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_NATURAL_PHENOMENON/rivers
- `VG:RV:SAK:M04:S032:V015` — LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/Indra's approach
- `VG:RV:SAK:M04:S033:V003` — LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/protection of the sacrifice, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/making aged parents young again, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/sacrifice
- `VG:RV:SAK:M04:S034:V006` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/ṛbhavaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/sacrifice, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_OFFERING/meath offered for drinking, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_SUBSTANCE/meath
- `VG:RV:SAK:M04:S035:V009` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/ṛbhavaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/third libation, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_OFFERING/effused drink
- `VG:RV:SAK:M05:S003:V008` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/agniḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/ancestral service of Agni, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_OFFERING/offerings
- `VG:RV:SAK:M05:S017:V001` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/prepared sacrifice
- `VG:RV:SAK:M05:S020:V001` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/agniḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/wealth worthy of praise
- `VG:RV:SAK:M05:S029:V006` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/indraḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/demolishing ninety-nine castles
- `VG:RV:SAK:M05:S049:V003` — LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/auspicious days
- `VG:RV:SAK:M05:S053:V016` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/marutaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/marutaḥ
- `VG:RV:SAK:M05:S068:V001` — LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/mitrāvaruṇau
- `VG:RV:SAK:M05:S073:V006` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/stirring the spotless flame
- `VG:RV:SAK:M05:S074:V009` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/aśvinau, LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/aśvinau
- `VG:RV:SAK:M05:S080:V002` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/uṣāḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_NATURAL_PHENOMENON/dawn
- `VG:RV:SAK:M06:S013:V001` — WRONG_PREDICATE: Luna=INVOKES/agniḥ; Sol=PRAISES/agniḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_NATURAL_PHENOMENON/rain and flowing waters
- `VG:RV:SAK:M06:S039:V002` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/indraḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/breaking Vala's ridge and subduing the Panis
- `VG:RV:SAK:M06:S042:V004` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_OFFERING/expressed juice, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/safety from hostile curses
- `VG:RV:SAK:M06:S044:V012` — LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/indraḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_NATURAL_PHENOMENON/thundering rain-clouds
- `VG:RV:SAK:M06:S045:V019` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/indraḥ
- `VG:RV:SAK:M06:S047:V017` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/indraḥ
- `VG:RV:SAK:M06:S068:V006` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/indrāvaruṇau, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/food, treasure, and protection, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/sacrifice
- `VG:RV:SAK:M06:S069:V007` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/indravisṇu, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_OFFERING/Soma drink, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_SUBSTANCE/somaḥ
- `VG:RV:SAK:M07:S004:V003` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/agniḥ
- `VG:RV:SAK:M07:S004:V010` — LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/felicity, understanding, and protection
- `VG:RV:SAK:M07:S032:V020` — LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/indraḥ
- `VG:RV:SAK:M07:S044:V002` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/sacrifice with sacred grass
- `VG:RV:SAK:M07:S060:V012` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/mitrāvaruṇau, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/safe passage and preservation, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/sacrifices
- `VG:RV:SAK:M07:S077:V005` — LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/light, long life, food, and bounty, LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_NATURAL_PHENOMENON/dawn
- `VG:RV:SAK:M07:S083:V009` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/indrāvaruṇau, LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/indrāvaruṇau, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/protection, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/destroying Vrtras and maintaining holy laws
- `VG:RV:SAK:M08:S001:V017` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/Soma pressing and washing, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_SUBSTANCE/somaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/pressing, washing, and filtering Soma
- `VG:RV:SAK:M08:S005:V014` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/aśvinau, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_OFFERING/presented meath, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_SUBSTANCE/meath
- `VG:RV:SAK:M08:S005:V015` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/aśvinau, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/abundant riches and food
- `VG:RV:SAK:M08:S006:V013` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/rending Vrtra and sending waters to the sea, LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_NATURAL_PHENOMENON/waters flowing to the sea
- `VG:RV:SAK:M08:S009:V012` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/aśvinau, LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_PLACE/Visnu's striding-places
- `VG:RV:SAK:M08:S010:V006` — LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/aśvinau
- `VG:RV:SAK:M08:S021:V014` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/indraḥ
- `VG:RV:SAK:M08:S022:V014` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/aśvinau, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/protection from mortal foes
- `VG:RV:SAK:M08:S026:V008` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/aśvinau, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_OFFERING/offering
- `VG:RV:SAK:M08:S037:V002` — LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/indraḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_SUBSTANCE/somaḥ
- `VG:RV:SAK:M08:S043:V024` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/agniḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/agniḥ
- `VG:RV:SAK:M08:S046:V021` — LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_NATURAL_PHENOMENON/morning dawn
- `VG:RV:SAK:M08:S051:V007` — LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/indraḥ
- `VG:RV:SAK:M08:S052:V008` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/indraḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/indraḥ
- `VG:RV:SAK:M08:S060:V011` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/agniḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/renowned life-strengthening wealth
- `VG:RV:SAK:M08:S067:V006` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/ādityāḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/sheltering defense and blessing
- `VG:RV:SAK:M08:S073:V002` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/aśvinau, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/nearness of protecting help
- `VG:RV:SAK:M08:S080:V004` — LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/foremost place for the chariot
- `VG:RV:SAK:M08:S089:V005` — LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/indraḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/slaying Vrtras and supporting earth and heaven
- `VG:RV:SAK:M08:S093:V001` — LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_NATURAL_PHENOMENON/sūryaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/the Sun mounting up to meet the Hero
- `VG:RV:SAK:M08:S093:V005` — LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/indraḥ
- `VG:RV:SAK:M08:S093:V024` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/bay steeds bringing their rider to the banquet, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/prepared feast
- `VG:RV:SAK:M08:S096:V007` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/indraḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/friendship with the Maruts and victory
- `VG:RV:SAK:M09:S002:V008` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/pavamānaḥ somaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/pavamānaḥ somaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/joyous draught
- `VG:RV:SAK:M09:S004:V009` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/pavamānaḥ somaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/moral improvement, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/worship
- `VG:RV:SAK:M09:S040:V001` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/pavamānaḥ somaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/assailing enemies while being purified
- `VG:RV:SAK:M09:S061:V001` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/pavamānaḥ somaḥ, SOL_ONLY_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/ritual flow of Indu, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/flowing onward with food
- `VG:RV:SAK:M09:S063:V016` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/pavamānaḥ somaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/wealth, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/flowing to the sieve, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_SUBSTANCE/somaḥ
- `VG:RV:SAK:M09:S066:V028` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/Soma purification through a fleece sieve, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/flowing through the sieve toward Indra
- `VG:RV:SAK:M09:S067:V004` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/filtering through fleecy cloth, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/flowing through fleecy cloth
- `VG:RV:SAK:M09:S068:V010` — PARTIAL_MATCH: Luna=INVOKES/somaḥ; Sol=INVOKES/pavamānaḥ somaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/dyāvāpṛthivyau, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/vigour and heroic riches, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/Soma pouring
- `VG:RV:SAK:M09:S074:V001` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/pavamānaḥ somaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/wide-spreading shelter, LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_NATURAL_PHENOMENON/swelling water
- `VG:RV:SAK:M09:S086:V004` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/pouring Soma with milk into the vat, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_SUBSTANCE/milk
- `VG:RV:SAK:M09:S087:V009` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/somaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/somaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/ample food
- `VG:RV:SAK:M09:S095:V004` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/draining the Soma stalk, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/draining the stalk and bearing Varuna aloft, LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_NATURAL_PHENOMENON/ocean
- `VG:RV:SAK:M09:S104:V005` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/pavamānaḥ somaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/pavamānaḥ somaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/success
- `VG:RV:SAK:M09:S109:V022` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/Indu streaming to Indra and mingling with floods, LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_NATURAL_PHENOMENON/floods
- `VG:RV:SAK:M10:S010:V014` — LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/Yami's union with another partner
- `VG:RV:SAK:M10:S014:V001` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/yamaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_OFFERING/oblations for Yama
- `VG:RV:SAK:M10:S025:V001` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOKES/somaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/a good mind, energy, and mental power, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_SUBSTANCE/sweet juice
- `VG:RV:SAK:M10:S030:V003` — LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/worship and Soma pressing at the reservoir, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_OFFERING/oblations, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_SUBSTANCE/somaḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_PLACE/reservoir
- `VG:RV:SAK:M10:S039:V011` — LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/aśvinau, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/aśvinau
- `VG:RV:SAK:M10:S040:V001` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/radiant chariot travelling at daybreak to the sacrifice, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/sacrifice
- `VG:RV:SAK:M10:S045:V008` — LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/agniḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/agniḥ
- `VG:RV:SAK:M10:S058:V012` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/restoring the departed spirit for life here
- `VG:RV:SAK:M10:S085:V028` — SOL_ONLY_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/marriage rite, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/binding the husband in bonds
- `VG:RV:SAK:M10:S087:V025` — LUNA_MISSED_RELATION: Luna=none/none; Sol=REQUESTS/destruction of the fiends' strength
- `VG:RV:SAK:M10:S089:V008` — WRONG_PREDICATE: Luna=INVOKES/indraḥ; Sol=PRAISES/indraḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/smiting those who injure the law
- `VG:RV:SAK:M10:S091:V003` — WRONG_PREDICATE: Luna=INVOKES/agniḥ; Sol=PRAISES/agniḥ
- `VG:RV:SAK:M10:S102:V002` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/Mudgalani winning the chariot battle prize
- `VG:RV:SAK:M10:S107:V008` — LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/dakṣiṇā, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/dakṣiṇā, LUNA_MISSED_RELATION: Luna=none/none; Sol=INVOLVES_RITUAL/sacrificial guerdon
- `VG:RV:SAK:M10:S108:V001` — LUNA_MISSED_RELATION: Luna=none/none; Sol=REFERS_TO_PLACE/Rasa's waters, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/Sarama's distant journey across Rasa's waters
- `VG:RV:SAK:M10:S118:V001` — LUNA_MISSED_RELATION: Luna=none/none; Sol=PRAISES/agniḥ, LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES_ACTION/slaying the devouring fiend
- `VG:RV:SAK:M10:S146:V005` — LUNA_MISSED_RELATION: Luna=none/none; Sol=DESCRIBES/araṇyānī
