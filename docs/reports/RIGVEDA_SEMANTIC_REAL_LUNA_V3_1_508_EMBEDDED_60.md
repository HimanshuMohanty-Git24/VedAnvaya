# Embedded real-Luna 60 replication

NO HUMAN GOLD EXISTS.

Historical V3 semantic runs were heuristic artifacts. This section compares the 60 overlapping tasks only with the sealed bounded real-Luna regression `vedagraph-rigveda-semantic-luna-v3.1-regression`. The result is observed Luna replication agreement, never determinism.

## Aggregate agreement

| Metric | Count / 60 |
| --- | --- |
| canonical entity agreement | 53 |
| evidence anchor agreement | 11 |
| exact set agreement | 12 |
| no claim agreement | 30 |
| predicate presence agreement | 18 |
| typed object agreement | 12 |

## Differences

- low: 0
- medium: 6
- high: 42
- tasks with assertion-set differences: 48

The high-severity difference rate is a readiness concern: the fresh run agrees with the bounded run on only 12/60 exact assertion sets and 18/60 predicate-presence sets. This is observed Luna replication behavior, not a determinism claim.

| Passage | Luna-only assertions | Regression-only assertions | Predicate differences | Target differences |
| --- | --- | --- | --- | --- |
| VG:RV:SAK:M01:S051:V009 | 1 | 1 | DESCRIBES, DESCRIBES_ACTION | VG:DEVATA:INDRAH |
| VG:RV:SAK:M01:S061:V003 | 1 | 1 | DESCRIBES_ACTION, INVOLVES_OFFERING | — |
| VG:RV:SAK:M01:S137:V003 | 1 | 1 | INVOLVES_SUBSTANCE, REQUESTS | — |
| VG:RV:SAK:M02:S011:V013 | 1 | 0 | — | — |
| VG:RV:SAK:M02:S020:V009 | 1 | 0 | — | — |
| VG:RV:SAK:M03:S004:V008 | 2 | 0 | INVOKES | VG:DEVATA:AGNIH, VG:DEVATA:SARASVATI |
| VG:RV:SAK:M03:S031:V014 | 1 | 1 | — | — |
| VG:RV:SAK:M04:S001:V007 | 0 | 1 | DESCRIBES | VG:DEVATA:AGNIH |
| VG:RV:SAK:M04:S017:V021 | 1 | 0 | REQUESTS | — |
| VG:RV:SAK:M04:S022:V011 | 2 | 0 | REQUESTS | — |
| VG:RV:SAK:M04:S023:V011 | 2 | 0 | REQUESTS | — |
| VG:RV:SAK:M04:S053:V005 | 1 | 1 | DESCRIBES, DESCRIBES_ACTION | VG:DEVATA:SAVITA |
| VG:RV:SAK:M06:S047:V017 | 0 | 1 | DESCRIBES | VG:DEVATA:INDRAH |
| VG:RV:SAK:M06:S073:V002 | 0 | 1 | DESCRIBES_ACTION | — |
| VG:RV:SAK:M07:S083:V009 | 0 | 1 | INVOKES | — |
| VG:RV:SAK:M08:S001:V013 | 0 | 1 | REQUESTS | — |
| VG:RV:SAK:M08:S010:V006 | 0 | 1 | REQUESTS | — |
| VG:RV:SAK:M08:S035:V006 | 0 | 1 | REQUESTS | — |
| VG:RV:SAK:M08:S035:V007 | 1 | 1 | INVOLVES_SUBSTANCE, REQUESTS | — |
| VG:RV:SAK:M08:S035:V008 | 1 | 1 | INVOLVES_SUBSTANCE, REQUESTS | — |
| VG:RV:SAK:M08:S035:V009 | 1 | 1 | INVOLVES_SUBSTANCE, REQUESTS | — |
| VG:RV:SAK:M08:S036:V004 | 0 | 1 | INVOLVES_SUBSTANCE | — |
| VG:RV:SAK:M08:S036:V005 | 0 | 1 | INVOLVES_SUBSTANCE | — |
| VG:RV:SAK:M08:S036:V006 | 0 | 2 | DESCRIBES_ACTION, INVOLVES_SUBSTANCE | — |
| VG:RV:SAK:M08:S060:V011 | 2 | 2 | — | — |
| VG:RV:SAK:M09:S004:V009 | 0 | 1 | REQUESTS | — |
| VG:RV:SAK:M09:S020:V002 | 0 | 1 | DESCRIBES_ACTION | — |
| VG:RV:SAK:M09:S043:V003 | 0 | 2 | DESCRIBES, DESCRIBES_ACTION | VG:DEVATA:SOMAH |
| VG:RV:SAK:M09:S052:V005 | 0 | 1 | REQUESTS | — |
| VG:RV:SAK:M09:S086:V038 | 1 | 2 | — | — |
| VG:RV:SAK:M09:S087:V004 | 1 | 2 | DESCRIBES, DESCRIBES_ACTION, INVOLVES_SUBSTANCE | VG:DEVATA:SOMAH |
| VG:RV:SAK:M09:S087:V009 | 0 | 1 | DESCRIBES_ACTION | — |
| VG:RV:SAK:M09:S109:V017 | 0 | 1 | DESCRIBES_ACTION | — |
| VG:RV:SAK:M10:S018:V008 | 0 | 1 | REQUESTS | — |
| VG:RV:SAK:M10:S025:V001 | 1 | 1 | — | — |
| VG:RV:SAK:M10:S041:V001 | 1 | 1 | INVOKES, INVOLVES_RITUAL | — |
| VG:RV:SAK:M10:S058:V001 | 0 | 1 | DESCRIBES_ACTION | — |
| VG:RV:SAK:M10:S058:V004 | 0 | 1 | DESCRIBES_ACTION | — |
| VG:RV:SAK:M10:S058:V005 | 0 | 1 | DESCRIBES_ACTION | — |
| VG:RV:SAK:M10:S058:V006 | 0 | 1 | DESCRIBES_ACTION | — |
| VG:RV:SAK:M10:S058:V007 | 0 | 1 | DESCRIBES_ACTION | — |
| VG:RV:SAK:M10:S058:V009 | 0 | 1 | DESCRIBES_ACTION | — |
| VG:RV:SAK:M10:S058:V011 | 0 | 1 | DESCRIBES_ACTION | — |
| VG:RV:SAK:M10:S102:V002 | 0 | 1 | DESCRIBES_ACTION | — |
| VG:RV:SAK:M10:S126:V006 | 0 | 1 | DESCRIBES_ACTION | — |
| VG:RV:SAK:M10:S170:V001 | 0 | 1 | REQUESTS | — |
| VG:RV:SAK:M10:S183:V002 | 0 | 1 | REQUESTS | — |
| VG:RV:SAK:M10:S189:V002 | 0 | 2 | DESCRIBES_ACTION | — |
