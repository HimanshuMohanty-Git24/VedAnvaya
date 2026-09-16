"""Unified search: a deterministic rank ladder over declared surfaces.

**No fulltext index, on purpose.** ``Passage``, ``TextVersion`` and ``Translation`` carry
none, and this API creates none -- an API that alters a frozen graph's schema to answer a
GET is not a read-only API. Measured against the live graph that costs nothing worth
having: a substring scan of all 18,391 English translations takes 17ms, of all 36,462
Sanskrit text versions 89ms, an exact citation lookup 15ms, and the whole 1,917-node
knowledge-object scan 34ms. Two fulltext indexes do exist (``enrichment_concept_text``,
``enrichment_formula_text``) and are deliberately unused: Lucene would mean escaping
``" ' \\ { } ( ) ~ * ? : ^ ] [`` correctly forever, and a mis-escaped metacharacter becomes
a 503 or -- worse -- a silently different query. 229 concepts and 4,825 formulas are small
enough that deterministic matching wins on every axis that matters: it is explainable, no
input can make it throw, and every row can say which rung produced it.

**Why the ladder is the ranking.** Relevance here is not a learned function and must not
pretend to be one. :data:`~vedagraph.api.models.search.MATCH_TYPE_ORDER` is the ranking,
``score`` is a label for the rung, and the tie-break is occurrence count then ``stable_id``
so the ordering is total and reproducible across calls.

**Why the queries are staged rather than one per rung.** Ten rungs meant ten round trips,
five of which scanned the same nodes with different predicates -- measured at 725ms of the
880ms total. The five are now two queries that compute the rung per node in a ``CASE``, and
the text surfaces form a third stage that is skipped when the strong rungs have already
filled the requested page. That skip is not a heuristic: the rungs are strictly ordered, so
if rungs above ``EXACT_SANSKRIT_PHRASE`` already yield more candidates than the page holds,
no text-surface row could enter the page whatever it contained. When a stage is skipped the
response says so -- ``total`` is null and a caveat names it -- because a fast answer that
implies it read everything is the failure this project keeps finding.

**Why coverage is declared rather than assumed.** The searchable surfaces do not cover the
corpus evenly and a result list cannot show that. Measured per passage:

===========================  =====================================================
surface                      passages carrying it
===========================  =====================================================
Sanskrit as transmitted       RV 10,552 - AV 5,839 - SV 1,844 - YV 1,836
Normalised Sanskrit           AV 5,839 and nothing else
English translation           RV 10,509 - AV 5,770 - YV 1,939 - SV 173, all reused
Lemma (dictionary headword)   RV 6,560 and nothing else
===========================  =====================================================

So an English phrase search returning nothing Samavedic has established nothing about the
Samaveda, and a caller who cannot see that will conclude the opposite. The Samavedic 173 is
the case to read carefully rather than the exception that closes the gap: those verses are
searchable in English because each carries Griffith's Rigvedic rendering of text verified
character-identical, so a Samavedic hit is a hit on another corpus's English and 1,671
verses remain unreachable in English.
:data:`SURFACE_COVERAGE` holds those figures, :func:`measure_surface_coverage` re-derives
them from a live session and ``tests/api/test_search.py`` asserts the two agree -- the same
discipline as :mod:`vedagraph.domain.layer_figures`, adopted because this project has
already shipped caveats whose numbers had drifted from the data they described.

**The accent hazard.** The transmitted Sanskrit carries accent marks inline: all 10,552
Rigvedic and all 5,839 Atharvavedic primary texts are accented, the 1,844 Samavedic ones
are not, and the Yajurveda's Sanskrit is present only as Devanagari extracted from its
containers. An unaccented Latin phrase therefore matches only where the accents fall
outside it. That is a real recall limit, it is reported in the surface note rather than
hidden, and it is a corpus-layer backlog item rather than something an API can fix.
"""

from __future__ import annotations

import re
import time
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Final, Protocol

from vedagraph.api.config import MAX_PAGE_SIZE
from vedagraph.api.errors import BadRequestError
from vedagraph.api.models.common import CaveatView, KnowledgeStatus, PaginationMeta
from vedagraph.api.models.entity import DEITY_SLUGS, ENTITY_TYPES, TYPE_NAME_BY_LABEL
from vedagraph.api.models.search import (
    MATCH_TYPE_ORDER,
    MATCH_TYPE_SCORES,
    MatchType,
    SearchLanguage,
    SearchResponse,
    SearchResult,
    SearchResultType,
    SearchSurface,
    SurfaceCoverageView,
)
from vedagraph.api.repositories.neo4j_repository import validated_label
from vedagraph.api.services.deity_population import is_deity
from vedagraph.domain.layer_figures import CORPUS_MANTRAS

# ---------------------------------------------------------------------------
# The Sanskrit repertoire prefilter: proving a scan cannot match, before running it
# ---------------------------------------------------------------------------

#: Every two-letter ASCII sequence that occurs anywhere in this corpus's Sanskrit.
#:
#: **What it is for.** A phrase search over the Sanskrit surfaces costs an unindexed scan of
#: 36,462 text values plus 5,839 normalised ones plus 10,031 lemmas -- measured at 85ms,
#: 53ms and 6ms. For an ordinary English word that scan is guaranteed to return nothing, and
#: the guarantee is provable rather than probable: *a substring the corpus does not contain
#: cannot be found in it*. If the query contains the pair ``fe``, and no Sanskrit text in
#: this graph contains ``fe``, then no Sanskrit text contains ``fever`` either, and the scan
#: can be skipped with certainty instead of run for 144ms to learn nothing.
#:
#: **Why it is sound.** The set is the exhaustive union over ``PRIMARY_TEXT``,
#: ``PARALLEL_TEXT``, ``SEARCH_DERIVATIVE`` and ``Lemma.normalized_lemma``, lower-cased.
#: Lower-casing and unioning can only make the set LARGER than any one surface's, so the
#: filter can only ever be too permissive -- it can decline to skip a scan that would have
#: matched nothing, and it can never skip a scan that would have matched something. Only
#: runs of ASCII letters are collected and only such runs are tested, so a query carrying
#: IAST diacritics is simply not rejected on the strength of them.
#:
#: **Why it is a constant and not a cache.** Deriving it live costs 1,197ms (888ms to read
#: 168,884 distinct tokens out of the graph, 309ms to reduce them). Holding it as process
#: state would be a cache of corpus structure with a staleness mode; holding it here makes
#: it a measured figure in the manner of :mod:`vedagraph.domain.layer_figures`, and
#: ``tests/api/test_search.py`` re-derives it from the live graph and asserts equality, so a
#: corpus whose alphabet changes fails a test rather than silently losing recall.
#:
#: **Do not hand-edit.** Re-measure, and check that the movement is one you intended: a
#: bigram REMOVED from this set makes the filter reject more, which is where an unsound
#: skip would come from.
_SANSKRIT_ASCII_BIGRAM_TEXT: Final = (
    "ab ac ad ae ag ah ai aj ak al am an ap ar as at au av ay ba bd be bh bi bj bl bo br bu "
    "bv by ca cc ce ch ci cm co cr cu cy da db dd de dg dh di dm dn do dr du dv dy ea eb ec "
    "ed eg eh ej ek el em en ep er es et ev ey ga gb gd ge gg gh gi gl gm gn go gr gu gv gy "
    "ha he hi hk hl hm hn ho hr hu hv hy ia ib ic id ig ih ij ik il im in ip ir is it iv iy "
    "ja je jh ji jj jm jo jr ju jv jy ka ke kh ki kk kl km kn ko kp kr ks kt ku kv ky la lb "
    "ld le lg lh li lk ll lm lo lp lu lv ly ma mb mc me mg mh mi mj mk ml mm mn mo mp mr ms "
    "mt mu mv my na nd ne ng ni nm nn no nr nt nu nv ny oa ob oc od og oh oj ok ol om on oo "
    "op or os ot ov oy pa pc pe ph pi pl pm pn po pp pr ps pt pu pv py ra rb rc rd re rg rh "
    "ri rj rk rl rm rn ro rp rr rs rt ru rv ry sa se si sk sm sn so sp sr ss st su sv sy ta "
    "te th ti tk tm tn to tp tr ts tt tu tv ty ub uc ud ug uh uj uk ul um un up ur us ut uv "
    "uy va ve vi vl vn vo vr vu vy ya ye yi yo yr yu yv yy"
)

SANSKRIT_ASCII_BIGRAMS: Final[frozenset[str]] = frozenset(_SANSKRIT_ASCII_BIGRAM_TEXT.split())

assert len(SANSKRIT_ASCII_BIGRAMS) == 308, "the declared repertoire lost or gained a pair"
assert all(len(pair) == 2 and pair.isascii() and pair.isalpha() for pair in SANSKRIT_ASCII_BIGRAMS)

#: The same repertoire at three letters. Same soundness argument, more discriminating power,
#: and the tier is here because the measurement demanded it: bigrams alone leave ``healing``
#: (``hea``), ``horse`` (``ors``) and ``gold`` (``gol``) looking Sanskrit-shaped, and those
#: three were the whole remaining tail at 300-420ms. Sanskrit has no /heə/, no /ɔrs/ and no
#: /gol/, and the corpus confirms it: 2,419 ASCII trigrams occur, and none of those do.
#:
#: 2,419 entries is a lot of generated data for a source file, and it is here rather than
#: derived at runtime for the same reason as the bigrams -- 1,197ms to re-derive, and a
#: derived-and-held set is a cache with a staleness mode where a declared one is a measured
#: figure a test can falsify.
_SANSKRIT_ASCII_TRIGRAM_TEXT: Final = (
    "aba abd abe abh abi abj abl abo abr abu aca acc ace ach aci aco acu acy ada adb add ade "
    "adg adh adi adm adn ado adr adu adv ady aet aga agb agd age agh agi agl agm agn ago agr "
    "agu agv agy aha ahe ahi ahl ahm ahn aho ahr ahu ahv ahy aib aic aid aig aih aij aik ail "
    "aim ain aip air ais ait aiv aiy aja aje aji ajj ajm ajo ajr aju ajv ajy aka ake akh aki "
    "akl akm akn ako akr aks akt aku akv aky ala alb ald ale alg alh ali alk alm alo alp alu "
    "alv aly ama amb amc ame amg ami amj aml amm amn amo amp amr amt amu amv amy ana and ane "
    "ani anm ann ano anr ant anu anv any apa ape aph api apl apn apo apr aps apt apu apv apy "
    "ara arb arc ard are arg arh ari arj ark arl arm arn aro arp ars art aru arv ary asa ase "
    "asi ask asm asn aso asp asr ass ast asu asv asy ata ate ath ati atk atm atn ato atp atr "
    "ats att atu atv aty aub auc aud aug auh auj auk aul aum aun aup aur aus aut auv ava ave "
    "avi avn avo avr avu avy aya aye ayi ayo ayu ayy bab bac bad bah bai baj bak bal bam ban "
    "bap bar bas bat bav bay bda bde bdh bdi bdo bed beh bek bem ben ber bha bhe bhi bhm bhn "
    "bho bhr bhu bhv bhy bib bil bin bis bit bja bji bjo bob bod bra bru bub bud buj buk bun "
    "bup bus buv bya cab cac cad cah cai caj cak cal cam can cap car cas cat cau cav cay cca "
    "cch cci ceb cec ced ceh cek cem cen cer ces cet cev cey cha che chi chl chm chn cho chr "
    "chu chv chy cib cic cid cig cij cik cim cin cip cir cis cit civ ciy cma cob coc cod cok "
    "cop cor cot cov coy cre cuc cud cuk cum cun cur cus cut cya cye cyo cyu dab dac dad dag "
    "dah dai daj dak dal dam dan dap dar das dat dau dav day dba dbh dbu dda ddh ddi ddu ddv "
    "ddy deb dec ded deh dej dem den dep der det dev dey dga dgh dgi dgr dgu dha dhe dhi dhm "
    "dhn dho dhr dhu dhv dhy dib did dig dih dik dil dim din dip dir dis dit div diy dma dme "
    "dmi dmo dmy dna dne dno doa dob dod dog doh doj dok dom dor dos dot dra dre dri dro dru "
    "drv dry dub duc dud dug duh duk dum dun dup dur dus duv dva dve dvi dvo dvr dvy dya dye "
    "dyo dyu eag ean ear eav ebh eca ece ech eci ecy eda edd ede edh edi edm edo edr edu edy "
    "ega egh ego egr eha ehi eho ehy eja eje eji ejo eka eke ekh eki eko ekt eku ela elh ema "
    "eme emi emo emu emy ena end ene eni eno enu env eny epa epe epi epn epo eps epu epy era "
    "ere eri ero ert eru ery esa eso est esu esv eta ete eth eti eto etr ett etu etv ety eva "
    "eve evi evo evr evy eya eye eyi eyo eyu eyy gab gac gad gah gai gaj gak gal gam gan gap "
    "gar gas gat gau gav gay gbh gbi gda gdh gea geb geh gem gen get gev gey ggh gha ghe ghi "
    "ghm ghn gho ghr ghu ghv ghy gib gid gil gin gir git gla gma gme gmi gmo gmu gmy gna gne "
    "gni gnu gny goa gob god gog goh goj gok gom gon goo gop gor gos got gov gra gre gri gro "
    "gru gry gub gud guh guk gul gum gun gup gur gus gut guv gva gve gvi gvo gya gye gyo gyu "
    "hab hac had hag hah hai haj hak hal ham han hap har has hat hau hav hay heb hec hed heh "
    "hej hek hel hem hen hep her hes het hev hey hib hic hid hig hih hij hik hil him hin hip "
    "hir his hit hiv hiy hkh hla hlo hma hme hmi hmo hna hne hni hno hnu hny hoa hob hoc hod "
    "hog hoh hoj hok hom hon hop hor hos hot hov hoy hra hrd hre hri hro hru hry hub huc hud "
    "hug huh huj huk hul hum hun hup hur hus hut huv huy hva hve hvi hvo hvr hvy hya hye hyo "
    "hyu iba ibd ibe ibh ibi ibo ibr ibu ica icc ice ich ici ico icr icu icy ida idb idd ide "
    "idh idi idm ido idr idu idv idy iga igb igd ige igh igi igm igo igr igu igv igy iha ihe "
    "ihi ihm iho ihr ihu ihv ihy ija ije iji ijm ijo ijr iju ijy ika ike ikh iki ikl ikn iko "
    "ikr iks ikt iku ikv iky ila ilb ile ili ilm ilo ilp ilv ily ima imb ime imi imk iml imm "
    "imn imo imp imr imu imy ina ind ine ini inm inn ino inr int inu inv iny ipa ipe iph ipi "
    "ipn ipo ipp ipr ips ipt ipu ipy ira irb ird ire irg irh iri irj irm iro irr iru irv iry "
    "isa isi isk isp isr ist isu isv ita ite ith iti itk itm itn ito itp itr its itt itu itv "
    "ity iva ive ivi ivl ivo ivr ivy iya iye iyo iyu jab jad jag jah jai jaj jak jal jam jan "
    "jap jar jas jat jau jav jay jeb jeh jej jem jen jer jet jev jha jib jic jid jig jih jij "
    "jik jim jin jip jir jit jiv jja jje jjh jji jju jjv jma jme jmi jmo job jod jog joh jop "
    "jor jot joy jra jre jri jro jru jry jub jug juh juj juk jum jun jur jus jut juv jva jve "
    "jvo jya jye jyo jyu kab kac kad kag kai kaj kak kal kam kan kap kar kas kat kau kav kay "
    "keb kec ked kem ken kep ker kes ket kev kha khe khi khk khn kho khr khu khv khy kid kik "
    "kil kim kin kir kis kit kiv kiy kka kla kle kli klo kma kme kmi kmo kmy kna kni kno knu "
    "kny kok kol kom kon kop kot kra kre kri kro kru kry ksa kta kte kth kti kto ktr ktu ktv "
    "kty kub kuc kud kuh kuk kul kum kun kup kur kus kut kuv kuy kva kve kvo kya kye kyu lab "
    "lad lag lah lai laj lak lal lam lan lap lar las lat lau lav lay lba lbi lda leb led len "
    "ler lev ley lga lgu lgv lha lhe lhi lib lig lih lik lil lim lin lip lir lit lka lko lku "
    "lla llu lma lob lod log loh lok lom lon lop lpa lpe lph lpi lpy lub luc luk lul lum lun "
    "lup lur lut lva lvi lvo lya lye lyo mab mac mad mag mah mai maj mak mal mam man map mar "
    "mas mat mau mav may mba mbe mbh mbi mbu mbv mby mca meb med meg meh mej mek mem men mer "
    "met mev mey mgr mha mib mic mid mig mih mik mim min mir mis mit miv miy mka mlu mma mmi "
    "mmr mna mne mni mno mny mob moc mod mog moh mok mop mor mot mov mpa mpe mpi mpr mpu mra "
    "mri mro mru msa mta mub muc mud mug muh muk mul mum mun mur mus mut muy mva mvi mvo mya "
    "mye myo myu nab nac nad nag nah nai naj nak nal nam nan nap nar nas nat nau nav nay nda "
    "ndd nde ndh ndi ndo ndr ndu ndy neb nec ned neh nej nek nel nem nen ner nes net nev ney "
    "nib nic nid nig nih nij nik nil nim nin nip nir nis nit niv niy nma nme nmi nmo nmr nmu "
    "nmy nna nne nni nno nob noc nod nog noh noj nok nom non nop nor nos not nov noy nta nte "
    "nth nti nto ntr nts ntu ntv nty nub nuc nud nug nuh nuj nuk nul num nun nup nur nus nut "
    "nuv nuy nva nve nvi nvo nya nye nyo nyr nyu oad oag oah oaj oak oan oar oav oba obh oca "
    "occ oce och oci oco ocu ocy oda odb odd ode odh odi odn odo odr odu odv ody oga ogd oge "
    "ogg ogh ogi ogo ogr ogu ogy oha ohe ohi oho ohu ohy oja oji ojm ojo oju ojy oka oke okh "
    "oki okm oko okr okt oky ola olb oma omb ome omi omn omo omu omy ona ond one oni onm ono "
    "onu ony oop opa ope opi opo opr ops opt opu opy ora ord ore ori orj orm oro orr oru orv "
    "osa osr ota ote oth oti otm oto otp otr ots ott otu otv oty ova ovi ovr oya oyo oyu pab "
    "pac pad pag pah pai paj pak pal pam pan pap par pas pat pau pav pay pch peb pec ped peh "
    "pej pek pem pen pep per pet pev pey pha phe phi pho phr phu phy pib pid pih pij pik pil "
    "pim pin pip pir pis pit piv piy pla plu pma pna pne pno pnu pny pob poc pod poh poj pom "
    "pop por pos pot ppa pra pre pri pro pru pry psa psi psn pso psu psv psy pta pte pti pto "
    "ptr ptu ptv pty puc pud pul pum pun pup pur pus put pva pve pya pye pyo pyu rab rac rad "
    "rae rag rah rai raj rak ral ram ran rap rar ras rat rau rav ray rbh rbi rbr rbu rca rce "
    "rch rci rco rda rde rdh rdi rdm rdo rdr rdu rdy rea reb rec red reg reh rej rek rel rem "
    "ren rep rer res ret rev rey rga rge rgh rgi rgo rgr rgu rgy rha rhe rhi rho rhr rhy rib "
    "ric rid rig rih rij rik rim rin rip rir ris rit riv riy rja rje rji rjm rjo rju rjy rka "
    "rke rki rko rkr rkt rku rlo rma rme rmi rmo rmr rmu rmy rna rni roa rob roc rod rog roh "
    "roj rok rol rom rop ror rot roy rpa rpe rph rpi rpo rpy rri rsr rta rte rth rti rtm rtn "
    "rto rtr rts rtt rtu rtv rty rub ruc rud rug ruh ruj ruk rul rum run rup rur rus rut ruv "
    "ruy rva rve rvi rvo rvr rvy rya rye ryo ryu sab sac sad sag sah sai saj sak sal sam san "
    "sap sar sas sat sau sav say seb sec sed seh sek sem sen sep ser ses set sev sey sic sid "
    "sih sik sil sim sin sip sir sis sit ska ske skr sku sma sme smi smo smr smy sna sne sni "
    "sno snu sny soa sob sod sog som sop sor sot sov spa spe sph spi spr sra sre sri sro sru "
    "ssi ssu ssv sta ste sth sti sto str stu stv sty sub suc sud sug suh suj suk sul sum sun "
    "sup sur sus sut suv suy sva sve svi svo svy sya sye syo syu tab tac tad tag tah tai taj "
    "tak tal tam tan tap tar tas tat tau tav tay teb ted teg teh tej tek tel tem ten tep ter "
    "tes tet tev tey tha the thi thn tho thr thu thv thy tib tic tid tig tih tij tik til tim "
    "tin tip tir tis tit tiv tiy tka tke tkh tkr tma tme tna tne tni tno tnu tnv tny tob toc "
    "tod tog toj tok tol tom ton top tor tos tot tov tpa tpi tpu tra tre tri tro tru trv try "
    "tsa tse tsi tsm tsn tso tst tsu tsv tsy tta tte tth tti tto ttr ttu ttv tty tub tuc tud "
    "tug tuh tuj tuk tum tun tup tur tus tut tuv tuy tva tve tvi tvo tvy tya tye tyo tyu uba "
    "ubd ube ubh ubj ubo ubr ubu uca ucc uce uch uci ucm uco ucr ucu ucy uda udb udd ude udg "
    "udh udi udm udn udo udr udu udv udy uga ugb ugd uge ugh ugm ugo ugr ugu ugv uha uhe uhi "
    "uho uhr uhu uhv uhy uja uje uji ujj ujm ujo ujr uju ujy uka uke ukh uki ukk ukl ukm uko "
    "ukr ukt uku ukv uky ula ulb ule ulg uli ulk ull ulm ulo ulp ulu ulv uly uma umb ume umi "
    "umn umo ump umr umu umy una und une uni unm unn uno unr unt unu unv uny upa upc upe uph "
    "upi upo upr ups upt upu upv upy ura urb urd ure urg urh uri urj urk urm urn uro urp urr "
    "urt uru urv ury usa usi usn uso usp usr ust usv uta ute uth uti utk utm utn uto utp utr "
    "uts utt utu utv uty uva uve uvi uvo uvr uvu uvy uya uyo uyu vab vac vad vae vag vah vai "
    "vaj vak val vam van vap var vas vat vau vav vay veb vec ved veg veh vej vek vel vem ven "
    "vep ver ves vet vev vey vib vic vid vig vih vij vik vil vim vin vip vir vis vit viv viy "
    "vla vna vne vno vny voa vob voc vod vog voj vol vom von vop vor vos vot vov voy vra vre "
    "vri vro vru vur vus vya vye vyo vyr vyu yab yac yad yag yah yai yaj yak yal yam yan yap "
    "yar yas yat yau yav yay yeb yed yeh yej yek yem yen yer yes yet yev yey yib yid yik yim "
    "yin yip yir yis yit yiv yiy yoa yob yoc yod yog yoh yoj yok yol yom yon yop yor yos yot "
    "yov yoy yub yuc yud yug yuh yuj yuk yul yum yun yup yur yus yut yuv yuy yya yye yyo"
)

SANSKRIT_ASCII_TRIGRAMS: Final[frozenset[str]] = frozenset(_SANSKRIT_ASCII_TRIGRAM_TEXT.split())

assert len(SANSKRIT_ASCII_TRIGRAMS) == 2419, "the declared trigram repertoire changed size"

#: The Cypher behind :data:`SANSKRIT_ASCII_BIGRAMS`, so the test re-derives it rather than
#: reproducing it. Distinct space-separated tokens are enough: an ASCII-letter run cannot
#: span a space, so the token set determines the gram set exactly.
SANSKRIT_REPERTOIRE_QUERY: Final = """
CALL () {
        MATCH (tv:TextVersion)
        WHERE tv.text_role IN ['PRIMARY_TEXT', 'PARALLEL_TEXT', 'SEARCH_DERIVATIVE']
        RETURN toLower(tv.text_nfc) AS t
    UNION
        MATCH (l:Lemma) RETURN toLower(l.normalized_lemma) AS t
}
UNWIND split(t, ' ') AS token
RETURN collect(DISTINCT token) AS tokens
"""

_ASCII_RUN: Final = re.compile(r"[a-z]{2,}")

#: Every combining mark stripped to fold a label to its comparison key, after NFD
#: decomposition. Declared as ONE table used by both sides of the comparison -- bound into
#: Cypher as ``$fold_marks`` and applied by :func:`fold_diacritics` in Python -- because
#: two folds that disagree would silently drop matches.
#:
#: **Measured from the graph, not enumerated from knowledge of IAST.** The first version was
#: written from the transliteration scheme and missed sixteen marks that actually occur, so
#: 635 labels folded incompletely and ``q=camtati`` could not reach ``Çaṁtāti`` -- the exact
#: class of miss the fold exists to remove. The test meant to guard it asserted only that
#: the Python and Cypher folds AGREED, and they did: both read the same incomplete table.
#: *An agreement test cannot see a coverage gap*, which is the same wrong-question failure
#: as this project's two stale-claim audits.
#:
#: **The Devanagari marks are folded too, and the first fix wrongly excluded them.** The
#: reasoning for excluding them was that stripping a vowel sign does not fold Devanagari
#: toward ASCII, it mangles it -- ``का`` becomes ``क``. That is true and irrelevant: this
#: value is an internal comparison key that is never rendered, an ASCII query cannot reach
#: a Devanagari label either way, and folding them slightly HELPS a Devanagari query whose
#: vowel signs sit differently from the label's. The collisions it can create land on the
#: ``FOLDED_ENTITY_LABEL`` rung, which is documented as weaker than an exact match and
#: returns every colliding node rather than picking one.
#:
#: ``test_the_declared_marks_cover_every_mark_in_the_graph`` re-derives this from the live
#: label surfaces and asserts equality in BOTH directions, so a corpus reload introducing a
#: mark fails a test naming it instead of quietly losing labels, and a table entry that
#: stops occurring is caught rather than left implying a coverage it no longer has.
#:
#: Do not hand-edit. Re-measure with :data:`DIACRITIC_REPERTOIRE_QUERY` and
#: :func:`marks_present_in`, and check the movement is one you intended.
DIACRITIC_MARKS: Final[tuple[str, ...]] = (
    "\u0301",  # combining acute accent: the accented Rigvedic parallel text (2,213)
    "\u0303",  # combining tilde: ñ (300)
    "\u0304",  # combining macron: ā ī ū (14,258, the most common by far)
    "\u0307",  # combining dot above: ṅ ṁ (1,213)
    "\u0308",  # combining diaeresis (1)
    "\u0310",  # combining candrabindu (51)
    "\u0323",  # combining dot below: ṛ ṣ ṭ ḍ ṇ ḥ ṃ ḷ (12,258)
    "\u0325",  # combining ring below: r̥ (372)
    "\u0327",  # combining cedilla: ç (97)
    "\u0331",  # combining macron below: ḻ (30)
    "\u0902",  # devanagari sign anusvara (5)
    "\u0903",  # devanagari sign visarga (42)
    "\u093e",  # devanagari vowel sign aa (158)
    "\u093f",  # devanagari vowel sign i (104)
    "\u0940",  # devanagari vowel sign ii (36)
    "\u0941",  # devanagari vowel sign u (93)
    "\u0942",  # devanagari vowel sign uu (17)
    "\u0943",  # devanagari vowel sign vocalic r (17)
    "\u0947",  # devanagari vowel sign e (57)
    "\u0948",  # devanagari vowel sign ai (4)
    "\u094b",  # devanagari vowel sign o (30)
    "\u094c",  # devanagari vowel sign au (23)
    "\u094d",  # devanagari sign virama (290)
)

assert len(DIACRITIC_MARKS) == 23, "the declared mark table changed size"
assert len(set(DIACRITIC_MARKS)) == len(DIACRITIC_MARKS), "a mark is declared twice"

#: The label surfaces the fold is applied to, so the mark repertoire is measured over
#: exactly the fields that matter rather than over a guess about which ones do.
DIACRITIC_REPERTOIRE_QUERY: Final = """
CALL () {
    CALL () {
            MATCH (n:DomainEntity) RETURN n
        UNION MATCH (n:Devata) RETURN n
        UNION MATCH (n:Rishi) RETURN n
        UNION MATCH (n:RishiFamily) RETURN n
        UNION MATCH (n:Chandas) RETURN n
        UNION MATCH (n:Epithet) RETURN n
        UNION MATCH (n:ActionPredicate) RETURN n
        UNION MATCH (n:DeityAxis) RETURN n
        UNION MATCH (n:DeityGroup) RETURN n
    }
    UNWIND [n.display_label, n.preferred_label, n.label_iast, n.preferred_label_sa,
            n.normalized_name] + coalesce(n.aliases_iast, []) + coalesce(n.aliases_sa, [])
           AS value
    RETURN value
  UNION
    CALL () { MATCH (n:Formula) RETURN n UNION MATCH (n:FormulaFamily) RETURN n }
    UNWIND [n.normalized, n.display_form] AS value
    RETURN value
}
WITH value WHERE value IS NOT NULL
RETURN collect(DISTINCT value) AS values
"""


def marks_present_in(values: Iterable[str]) -> frozenset[str]:
    """Every Unicode combining mark occurring in ``values`` after NFD decomposition.

    Enumerates the value space rather than testing for the marks we expect to find, which
    is the only way a coverage gap becomes visible.
    """
    found: set[str] = set()
    for value in values:
        for character in unicodedata.normalize("NFD", (value or "").lower()):
            if unicodedata.category(character) in {"Mn", "Mc", "Me"}:
                found.add(character)
    return frozenset(found)


#: The Cypher expression that folds ``expr`` the same way :func:`fold_diacritics` does.
#: ``normalize(..., NFD)`` is Cypher-native, so this needs no APOC, no index and no
#: in-process folded copy of the label set -- measured at 21ms over the 1,917 knowledge
#: objects, inside a scan that was happening anyway.
def _folded(expr: str) -> str:
    return f"reduce(s = normalize(toLower({expr}), NFD), m IN $fold_marks | replace(s, m, ''))"


def fold_diacritics(text: str) -> str:
    """Fold ``text`` to its ASCII skeleton: ``yajña`` -> ``yajna``, ``ṛta`` -> ``rta``.

    Must agree exactly with :func:`_folded`'s Cypher, which
    ``test_the_python_and_cypher_folds_agree_on_every_entity_label`` asserts over every
    label in the graph rather than over a sample.
    """
    folded = unicodedata.normalize("NFD", text.lower())
    for mark in DIACRITIC_MARKS:
        folded = folded.replace(mark, "")
    return folded


def sanskrit_repertoire_from(tokens: Iterable[str], size: int = 2) -> frozenset[str]:
    """Reduce a token list to its ASCII ``size``-gram repertoire. For the test, not search."""
    grams: set[str] = set()
    for token in tokens:
        for run in _ASCII_RUN.findall((token or "").lower()):
            grams.update(run[index : index + size] for index in range(len(run) - size + 1))
    return frozenset(grams)


def sanskrit_cannot_contain(query: str) -> str | None:
    """The letter pair that proves the Sanskrit surfaces cannot contain ``query``, if any.

    Returns the offending pair so the response can name it. ``None`` means the query is a
    shape this corpus's Sanskrit could carry, and the surfaces must actually be read.

    This is a proof of absence and not a sample of it, which is why it is allowed to skip a
    scan at all. Every rejection is verified against the live graph by
    ``test_the_repertoire_filter_never_skips_a_scan_that_would_have_matched``.
    """
    for run in _ASCII_RUN.findall(query.lower()):
        text = str(run)
        for index in range(len(text) - 1):
            pair = text[index : index + 2]
            if pair not in SANSKRIT_ASCII_BIGRAMS:
                return pair
        for index in range(len(text) - 2):
            triple = text[index : index + 3]
            if triple not in SANSKRIT_ASCII_TRIGRAMS:
                return triple
    return None


#: Corpus codes in a fixed order, so two coverage blocks can be read against each other.
VEDA_ORDER: Final[tuple[str, ...]] = ("RV", "AV", "YV", "SV")

#: The four works this API serves, checked before a ``work`` filter reaches a query. An
#: unknown work is a 400 and not an empty result: "no such work" and "that work has no
#: match" are different answers and this API refuses to conflate them.
KNOWN_WORK_IDS: Final[frozenset[str]] = frozenset(
    {"VG:WORK:RV:SAK", "VG:WORK:SV:KAU", "VG:WORK:YV:VSM", "VG:WORK:AV:SAU"}
)

#: Ceiling on ``offset + limit``. Search merges bounded stages in memory in order to rank
#: them, so a deep page would need more rows per stage than the ranking can justify. A
#: request past this gets a 400 telling it to narrow, rather than a page silently ranked
#: against an incomplete candidate set.
SEARCH_WINDOW_LIMIT: Final = MAX_PAGE_SIZE

#: Passage counts per surface, per Veda. Asserted against the live graph by
#: ``tests/api/test_search.py::test_declared_surface_coverage_matches_the_graph``, so a
#: corpus that grows or a translation that lands fails a test instead of quietly making
#: the coverage note in every search response a lie.
SURFACE_COVERAGE: Final[dict[SearchSurface, dict[str, int]]] = {
    SearchSurface.SANSKRIT_TEXT: {"RV": 10_552, "AV": 5_839, "YV": 1_836, "SV": 1_844},
    SearchSurface.NORMALIZED_SANSKRIT: {"AV": 5_839},
    # Raised by the translation bulk integration. The Samavedic 173 is the figure that
    # needs reading carefully and the note below does the reading: those verses are
    # searchable in English because they carry Griffith's Rigvedic rendering of
    # verified-identical text, not because the Samaveda gained a translation.
    SearchSurface.ENGLISH_TRANSLATION: {
        "RV": 10_509,
        "AV": 5_770,
        "YV": 1_939,
        "SV": 173,
    },
    SearchSurface.LEMMA: {"RV": 6_560},
}

#: What each declared surface cannot do, in its own words. Rendered onto every response
#: that read that surface, and onto none that did not.
SURFACE_NOTES: Final[dict[SearchSurface, str]] = {
    SearchSurface.SANSKRIT_TEXT: (
        "The transmitted text carries accent marks inline for the Rigveda and Atharvaveda "
        "and none for the Samaveda, and the Yajurveda's Sanskrit is present only as "
        "Devanagari extracted from its containers. An unaccented Latin phrase therefore "
        "matches only where the accents fall outside it: that is a recall limit of the "
        "corpus layer, not evidence that the phrase is absent from the text."
    ),
    SearchSurface.NORMALIZED_SANSKRIT: (
        "The accent-stripped search surface was built for the Atharvaveda only. A miss "
        "here says nothing at all about the other three corpora."
    ),
    SearchSurface.ENGLISH_TRANSLATION: (
        "Public-domain translations only: Griffith for the Rigveda and Yajurveda, "
        "Whitney-Lanman and Griffith for the Atharvaveda. NO INDEPENDENT SAMAVEDIC "
        "TRANSLATION EXISTS IN THIS GRAPH. An English search can now reach 173 Samavedic "
        "verses, and every one of them carries Griffith's Rigvedic rendering of text "
        "verified character-identical rather than a translation of the Samaveda -- so a "
        "Samavedic hit here is a hit on another corpus's English, and the remaining 1,671 "
        "verses cannot be reached in English at all. Some matches are also Latin: Griffith "
        "put the passages he judged too explicit into Latin, so an English query will not "
        "find them and their absence is his editorial choice rather than a gap here."
    ),
    SearchSurface.LEMMA: (
        "The lemma layer comes from the manual Rigvedic morphological annotation and "
        "reaches the Rigveda alone. A headword search cannot reach the other three corpora."
    ),
}

_SURFACE_COVERAGE_QUERIES: Final[dict[SearchSurface, str]] = {
    SearchSurface.SANSKRIT_TEXT: """
        MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(tv:TextVersion)
        WHERE tv.text_role IN ['PRIMARY_TEXT', 'PARALLEL_TEXT']
        RETURN p.veda AS veda, count(DISTINCT p) AS c
        """,
    SearchSurface.NORMALIZED_SANSKRIT: """
        MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(:TextVersion {text_role: 'SEARCH_DERIVATIVE'})
        RETURN p.veda AS veda, count(DISTINCT p) AS c
        """,
    SearchSurface.ENGLISH_TRANSLATION: """
        MATCH (p:Passage)-[:HAS_TRANSLATION]->(:Translation {language: 'en'})
        RETURN p.veda AS veda, count(DISTINCT p) AS c
        """,
    SearchSurface.LEMMA: """
        MATCH (p:Passage)-[:MENTIONS_LEMMA]->(:Lemma)
        RETURN p.veda AS veda, count(DISTINCT p) AS c
        """,
}


class _Repository(Protocol):
    def run(self, cypher: str, /, **parameters: Any) -> list[dict[str, Any]]: ...


def measure_surface_coverage(repository: _Repository) -> dict[SearchSurface, dict[str, int]]:
    """Re-derive :data:`SURFACE_COVERAGE` from a live graph, in the same shape."""
    return {
        surface: {
            str(row["veda"]): int(row["c"])
            for row in repository.run(cypher)
            if row["veda"] is not None
        }
        for surface, cypher in _SURFACE_COVERAGE_QUERIES.items()
    }


# ---------------------------------------------------------------------------
# Type resolution: a raw Neo4j label never leaves this module
# ---------------------------------------------------------------------------

#: Specificity order for a node carrying several product labels, most specific first. The
#: frozen graph gives a jujube ``Concept:DomainEntity:Offering:Substance`` and barley
#: ``Concept:Crop:DomainEntity:Plant``; ``labels()`` has no guaranteed order, so picking
#: ``labels(n)[0]`` would type the same node differently on different calls. That bug is
#: already documented in ``ritual_step_sequence``; this is the same fix applied to the
#: whole entity surface.
_LABEL_SPECIFICITY: Final[tuple[str, ...]] = (
    "Devata",
    "Crop",
    "Weapon",
    "Metal",
    "River",
    "Offering",
    "Condition",
    "Ritual",
    "SocialRite",
    "RitualRole",
    "PhilosophicalConcept",
    "HumanConcern",
    "Tribe",
    "CosmicEntity",
    "NaturalPhenomenon",
    "Plant",
    "Animal",
    "Substance",
    "Object",
    "Place",
    "Quality",
    "State",
    "Epithet",
    "ActionPredicate",
    "DeityAxis",
    "DeityGroup",
    "RishiFamily",
    "Rishi",
    "Chandas",
    "FormulaFamily",
    "Formula",
    "Concept",
)

assert set(_LABEL_SPECIFICITY) <= set(TYPE_NAME_BY_LABEL), (
    "a label in the specificity order has no product type name: "
    f"{sorted(set(_LABEL_SPECIFICITY) - set(TYPE_NAME_BY_LABEL))}"
)


def result_type_for_labels(labels: list[str] | None) -> SearchResultType:
    """Most specific product type for a node's labels. Falls back to CONCEPT, never a label."""
    present = set(labels or ())
    for label in _LABEL_SPECIFICITY:
        if label in present:
            return SearchResultType(TYPE_NAME_BY_LABEL[label])
    return SearchResultType.CONCEPT


# ---------------------------------------------------------------------------
# Stage 1: exact passage identity. Two index-backed lookups, 3ms and 15ms.
# ---------------------------------------------------------------------------

#: Passage filters, bound rather than concatenated. ``$veda IS NULL`` is how an absent
#: filter is expressed, so the query text is byte-identical whether or not the client sent
#: one -- which is what makes the injection assertion in the tests meaningful.
_PASSAGE_FILTER: Final = """
  AND $passages_wanted
  AND ($veda IS NULL OR p.veda = $veda)
  AND ($work IS NULL OR p.work_id = $work)
"""

_PASSAGE_RETURN: Final = """
RETURN match_type, p.canonical_key AS stable_id, p.canonical_citation AS citation,
       p.veda AS veda, p.entity_type AS entity_type, snippet_source, weight
ORDER BY weight DESC, stable_id
LIMIT $fetch
"""

_PASSAGE_KEY_QUERY: Final = (
    "MATCH (p:Passage) WHERE p.canonical_key = $q_raw\n"
    + _PASSAGE_FILTER
    + "WITH p, 'EXACT_CANONICAL_KEY' AS match_type, null AS snippet_source, 0 AS weight\n"
    + _PASSAGE_RETURN
)

_PASSAGE_CITATION_QUERY: Final = (
    "MATCH (p:Passage) WHERE toUpper(p.canonical_citation) = toUpper($q_raw)\n"
    + _PASSAGE_FILTER
    + "WITH p, 'EXACT_CITATION' AS match_type, null AS snippet_source, 0 AS weight\n"
    + _PASSAGE_RETURN
)

# ---------------------------------------------------------------------------
# Stage 2: knowledge objects. Every label rung in one pass over each node set.
# ---------------------------------------------------------------------------

#: The knowledge objects the label rungs read, split in two because the split is worth
#: 100ms. Formulas and formula families are 5,545 of the 7,462 searchable nodes and carry
#: none of the label, alias or definition properties the others do; scanning them together
#: measured 170ms against 34ms + 37ms apart.
_CORE_LABELS: Final[tuple[str, ...]] = (
    "DomainEntity",
    "Devata",
    "Rishi",
    "RishiFamily",
    "Chandas",
    "Epithet",
    "ActionPredicate",
    "DeityAxis",
    "DeityGroup",
)

_FORMULA_LABELS: Final[tuple[str, ...]] = ("Formula", "FormulaFamily")

#: Checked against the frozen ontology at import. The labels are literals in the Cypher
#: below rather than client values, and this is the guard that keeps them so: a label that
#: stopped being a product label -- or became internal -- would fail the import rather than
#: leak into a traversal.
for _label in (*_CORE_LABELS, *_FORMULA_LABELS):
    validated_label(_label)


def _label_union(labels: tuple[str, ...]) -> str:
    body = "\n  UNION\n".join(f"  MATCH (n:{label}) RETURN n" for label in labels)
    return f"CALL () {{\n{body}\n}}\n"


#: Every property holding a name, gathered once so the exact and prefix rungs read exactly
#: the same fields and cannot diverge.
_CORE_ENTITY_QUERY: Final = (
    _label_union(_CORE_LABELS)
    + """
WITH n,
  [n.display_label, n.preferred_label, n.label_iast, n.label_en, n.preferred_label_en,
   n.preferred_label_sa, n.normalized_name, n.predicate, n.axis, n.patronymic_iast,
   n.eponym_iast, n.personal_name_iast] AS names,
  coalesce(n.aliases_iast, []) + coalesce(n.aliases_en, []) + coalesce(n.aliases_sa, []) +
  coalesce(n.patronymics_iast, []) + coalesce(n.personal_names_iast, []) AS aliases,
  coalesce(n.entity_key, n.concept_id, n.family_key, n.epithet_key, n.axis_key,
           n.group_key, n.predicate) AS stable_id,
  coalesce(n.profile_mentions_total, n.mention_edges_total, n.occurrence_count,
           n.member_count, n.root_count, 0) AS weight
// Folded over the Sanskrit-bearing fields only. label_en / preferred_label_en are
// English, and predicate / axis are ASCII enum values, so folding them costs the scan
// and can never change an answer: trimming 12 fields to 5 halved the fold's cost.
WITH n, stable_id, weight, names, aliases,
  [x IN [n.display_label, n.preferred_label, n.label_iast, n.preferred_label_sa,
         n.normalized_name] WHERE x IS NOT NULL |
   reduce(s = normalize(toLower(x), NFD), m IN $fold_marks | replace(s, m, ''))
  ] AS folded_names,
  [x IN coalesce(n.aliases_iast, []) + coalesce(n.aliases_sa, []) |
   reduce(s = normalize(toLower(x), NFD), m IN $fold_marks | replace(s, m, ''))
  ] AS folded_aliases
WITH n, stable_id, weight,
  CASE
    WHEN stable_id = $q_raw THEN 'EXACT_CANONICAL_KEY'
    WHEN any(x IN names WHERE x IS NOT NULL AND toLower(x) = $q) THEN 'EXACT_ENTITY_LABEL'
    WHEN any(x IN aliases WHERE toLower(x) = $q) THEN 'EXACT_ALIAS'
    WHEN $q_folded <> '' AND (any(x IN folded_names WHERE x = $q_folded)
      OR any(x IN folded_aliases WHERE x = $q_folded)) THEN 'FOLDED_ENTITY_LABEL'
    WHEN any(x IN names WHERE x IS NOT NULL AND toLower(x) STARTS WITH $q)
      OR ($q_folded <> '' AND any(x IN folded_names WHERE x STARTS WITH $q_folded))
      THEN 'PREFIX_ENTITY_LABEL'
    WHEN toLower(coalesce(n.definition, '')) CONTAINS $q
      OR toLower(coalesce(n.short_description, '')) CONTAINS $q THEN 'CONCEPT_MATCH'
  END AS match_type
WHERE match_type IS NOT NULL
  AND ($type_labels IS NULL OR any(l IN labels(n) WHERE l IN $type_labels))
RETURN match_type, stable_id, labels(n) AS node_labels, n.display_label AS display_label,
       n.short_description AS short_description, n.definition AS definition,
       n.structure AS structure, weight
ORDER BY $rung_order[match_type], weight DESC, stable_id
LIMIT $fetch
"""
)

_FORMULA_ENTITY_QUERY: Final = (
    _label_union(_FORMULA_LABELS)
    + """
WITH n, coalesce(n.formula_id, n.family_id) AS stable_id,
     coalesce(n.mantra_count, n.member_count, 0) AS weight,
     [n.normalized, n.display_form, n.representative_normalized,
      n.representative_display_form] AS names
WITH n, stable_id, weight, names,
     [x IN [n.normalized, n.display_form] WHERE x IS NOT NULL |
      reduce(s = normalize(toLower(x), NFD), m IN $fold_marks | replace(s, m, ''))
     ] AS folded_names
WITH n, stable_id, weight,
  CASE
    WHEN stable_id = $q_raw THEN 'EXACT_CANONICAL_KEY'
    WHEN any(x IN names WHERE x IS NOT NULL AND toLower(x) = $q) THEN 'EXACT_ENTITY_LABEL'
    WHEN $q_folded <> '' AND any(x IN folded_names WHERE x = $q_folded)
      THEN 'FOLDED_ENTITY_LABEL'
    WHEN any(x IN names WHERE x IS NOT NULL AND toLower(x) STARTS WITH $q)
      OR ($q_folded <> '' AND any(x IN folded_names WHERE x STARTS WITH $q_folded))
      THEN 'PREFIX_ENTITY_LABEL'
  END AS match_type
WHERE match_type IS NOT NULL
  AND ($type_labels IS NULL OR any(l IN labels(n) WHERE l IN $type_labels))
RETURN match_type, stable_id, labels(n) AS node_labels, n.display_label AS display_label,
       null AS short_description, null AS definition, null AS structure, weight
ORDER BY $rung_order[match_type], weight DESC, stable_id
LIMIT $fetch
"""
)

# ---------------------------------------------------------------------------
# Stage 3: the textual surfaces. Skipped when the strong rungs filled the page.
# ---------------------------------------------------------------------------

_SANSKRIT_PHRASE_QUERY: Final = (
    "MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(tv:TextVersion)\n"
    "WHERE tv.text_role IN ['PRIMARY_TEXT', 'PARALLEL_TEXT']\n"
    "  AND tv.text_nfc CONTAINS $q_raw\n"
    + _PASSAGE_FILTER
    + "WITH p, 'EXACT_SANSKRIT_PHRASE' AS match_type, tv.text_nfc AS snippet_source,\n"
    "     1 AS weight\n" + _PASSAGE_RETURN
)

_NORMALIZED_PHRASE_QUERY: Final = (
    "MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(tv:TextVersion)\n"
    "WHERE tv.text_role = 'SEARCH_DERIVATIVE' AND toLower(tv.text_nfc) CONTAINS $q\n"
    + _PASSAGE_FILTER
    + "WITH p, 'NORMALIZED_SANSKRIT_PHRASE' AS match_type, tv.text_nfc AS snippet_source,\n"
    "     1 AS weight\n" + _PASSAGE_RETURN
)

_TRANSLATION_PHRASE_QUERY: Final = (
    "MATCH (p:Passage)-[:HAS_TRANSLATION]->(tr:Translation)\n"
    "WHERE tr.language = 'en' AND toLower(tr.text) CONTAINS $q\n"
    + _PASSAGE_FILTER
    + "WITH p, 'TRANSLATION_PHRASE' AS match_type, tr.text AS snippet_source, 1 AS weight\n"
    + _PASSAGE_RETURN
)

#: The lemma rung returns PASSAGES, not lemmas. All 10,031 ``:Lemma`` nodes are marked
#: ``:Internal`` -- V3 demoted the whole layer because 39 deity lemmas were surfacing in
#: product traversal looking like deities while carrying none of a Devata's profile -- so a
#: lemma may be matched against and must never be rendered as a result. The five strongest
#: headwords are taken before the passage join, so a broad prefix cannot fan out.
_LEMMA_QUERY: Final = (
    "MATCH (l:Lemma)\n"
    "WHERE toLower(l.lemma) = $q OR l.normalized_lemma STARTS WITH $q\n"
    "WITH l ORDER BY coalesce(l.mantra_count, 0) DESC, l.lemma LIMIT 5\n"
    "MATCH (p:Passage)-[:MENTIONS_LEMMA]->(l)\n"
    "WHERE true\n"
    + _PASSAGE_FILTER
    + "WITH p, 'LEMMA_FORM' AS match_type, l.lemma AS snippet_source,\n"
    "     coalesce(l.mantra_count, 0) AS weight\n" + _PASSAGE_RETURN
)


@dataclass(frozen=True)
class _Stage:
    """One group of queries, the surfaces they read, and the best rung they can produce.

    ``first_rung`` is what makes a stage skippable: nothing this stage returns can outrank
    it, so once the requested page is full of candidates above that rung, running the stage
    cannot change the answer. Stages are therefore as SMALL as their rung granularity
    allows -- the three Sanskrit surfaces were one stage until it was measured that
    splitting them lets ``somam``, whose plain-Sanskrit scan fills the page on its own, skip
    the normalised, lemma and translation scans behind it.
    """

    name: str
    queries: tuple[str, ...]
    surfaces: tuple[SearchSurface, ...]
    first_rung: MatchType
    #: True where every query in the stage reads a Sanskrit surface, so the repertoire
    #: prefilter can prove in advance that it cannot match.
    reads_sanskrit: bool = False

    @property
    def first_rung_index(self) -> int:
        return MATCH_TYPE_ORDER.index(self.first_rung)


_STAGE_IDENTITY: Final = _Stage(
    name="identity",
    queries=(_PASSAGE_KEY_QUERY, _PASSAGE_CITATION_QUERY),
    surfaces=(SearchSurface.CANONICAL_KEY, SearchSurface.CANONICAL_CITATION),
    first_rung=MatchType.EXACT_CANONICAL_KEY,
)

#: NEVER ``reads_sanskrit``. The repertoire prefilter's grams are derived from the
#: UNFOLDED text surfaces, so it is only sound against those; the entity stage folds
#: diacritics on both sides, and gating it by that prefilter would reject ``yajna`` before
#: the fold could match ``yajña``. Asserted by
#: ``test_the_repertoire_prefilter_never_gates_the_entity_stage``.
_STAGE_ENTITIES: Final = _Stage(
    name="entities",
    queries=(_CORE_ENTITY_QUERY, _FORMULA_ENTITY_QUERY),
    surfaces=(SearchSurface.ENTITY_LABELS, SearchSurface.CONCEPT_TEXT),
    first_rung=MatchType.EXACT_CANONICAL_KEY,
)

_STAGE_SANSKRIT_TEXT: Final = _Stage(
    name="sanskrit-text",
    queries=(_SANSKRIT_PHRASE_QUERY,),
    surfaces=(SearchSurface.SANSKRIT_TEXT,),
    first_rung=MatchType.EXACT_SANSKRIT_PHRASE,
    reads_sanskrit=True,
)

_STAGE_NORMALIZED_TEXT: Final = _Stage(
    name="normalised-sanskrit",
    queries=(_NORMALIZED_PHRASE_QUERY,),
    surfaces=(SearchSurface.NORMALIZED_SANSKRIT,),
    first_rung=MatchType.NORMALIZED_SANSKRIT_PHRASE,
    reads_sanskrit=True,
)

_STAGE_LEMMA: Final = _Stage(
    name="lemma",
    queries=(_LEMMA_QUERY,),
    surfaces=(SearchSurface.LEMMA,),
    first_rung=MatchType.LEMMA_FORM,
    reads_sanskrit=True,
)

_STAGE_TEXT_ENGLISH: Final = _Stage(
    name="english-translation",
    queries=(_TRANSLATION_PHRASE_QUERY,),
    surfaces=(SearchSurface.ENGLISH_TRANSLATION,),
    first_rung=MatchType.TRANSLATION_PHRASE,
)

#: Every Cypher template search can issue, as a closed set. Nothing a caller sends can
#: produce a query outside it -- which is a stronger property than "the query text does not
#: vary with the input", because the repertoire prefilter makes WHICH templates run depend
#: on the query's letters. ``tests/api/test_search.py`` asserts every query the driver was
#: asked is a member.
ALL_QUERY_TEMPLATES: Final[frozenset[str]] = frozenset(
    {
        _PASSAGE_KEY_QUERY,
        _PASSAGE_CITATION_QUERY,
        _CORE_ENTITY_QUERY,
        _FORMULA_ENTITY_QUERY,
        _SANSKRIT_PHRASE_QUERY,
        _NORMALIZED_PHRASE_QUERY,
        _LEMMA_QUERY,
        _TRANSLATION_PHRASE_QUERY,
    }
)

#: Stages that may be skipped, and are therefore reported when they are. The two cheap
#: identity/entity stages always run: they are 15ms and 58ms, and they are what makes the
#: skip decisions possible.
_SKIPPABLE_STAGES: Final[frozenset[str]] = frozenset(
    {
        _STAGE_SANSKRIT_TEXT.name,
        _STAGE_NORMALIZED_TEXT.name,
        _STAGE_LEMMA.name,
        _STAGE_TEXT_ENGLISH.name,
    }
)

#: The ladder as a bound map, so ``ORDER BY $rung_order[match_type]`` inside the entity
#: queries sorts by RANK and not alphabetically. Getting this wrong is not cosmetic: sorted
#: as strings, ``CONCEPT_MATCH`` precedes ``EXACT_ENTITY_LABEL``, and a probe of the live
#: graph showed a bounded query for "Indra" spending its whole row budget on definition
#: matches and never returning ``VG:DEVATA:INDRAH`` at all. Built from
#: :data:`~vedagraph.api.models.search.MATCH_TYPE_ORDER` so the Cypher ordering IS the
#: documented ladder rather than a copy of it.
RUNG_ORDER: Final[dict[str, int]] = {
    match_type.value: index for index, match_type in enumerate(MATCH_TYPE_ORDER)
}

#: The last rung that means "the caller named one object exactly" rather than "the caller
#: described something". Above this line a query is an identifier; below it, a phrase.
_EXACT_IDENTITY_LAST_RUNG: Final = MATCH_TYPE_ORDER.index(MatchType.EXACT_CITATION)

#: How much text a snippet may carry, and how much of it precedes the match.
_SNIPPET_WIDTH: Final = 220
_SNIPPET_LEAD: Final = 60


@dataclass(frozen=True)
class _Candidate:
    """One merged row, before it becomes a :class:`SearchResult`."""

    rung_index: int
    match_type: MatchType
    result_type: SearchResultType
    stable_id: str
    display_label: str
    subtitle: str | None
    snippet: str | None
    veda: str | None
    weight: int


def _snippet(text: Any, needle: str) -> str | None:
    """A window of ``text`` around ``needle``, or its head where the needle is not in it.

    The needle can be absent from the stored text even though the query matched, because
    the normalised and translation rungs match case-insensitively and the lemma rung
    matches a headword rather than a surface form. Degrading to the head of the passage is
    better than returning nothing and letting a client think there was no text.
    """
    if not isinstance(text, str) or not text:
        return None
    position = text.lower().find(needle.lower()) if needle else -1
    if position < 0:
        return text[:_SNIPPET_WIDTH] + ("..." if len(text) > _SNIPPET_WIDTH else "")
    start = max(0, position - _SNIPPET_LEAD)
    end = min(len(text), start + _SNIPPET_WIDTH)
    return f"{'...' if start > 0 else ''}{text[start:end]}{'...' if end < len(text) else ''}"


def _first_line(text: Any, width: int = 160) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None
    line = text.strip().splitlines()[0]
    return line if len(line) <= width else line[: width - 3] + "..."


def _passage_subtitle(row: dict[str, Any]) -> str | None:
    parts = [str(p) for p in (row.get("veda"), row.get("entity_type")) if p]
    return " / ".join(parts) if parts else None


def _coverage_view(surface: SearchSurface) -> SurfaceCoverageView | None:
    counts = SURFACE_COVERAGE.get(surface)
    if counts is None:
        return None
    return SurfaceCoverageView(
        surface=surface,
        passages_by_veda=dict(counts),
        vedas_not_covered=[v for v in VEDA_ORDER if v not in counts],
        note=SURFACE_NOTES.get(surface),
    )


def timed[T](work: Callable[[], T]) -> tuple[T, float]:
    """Run ``work`` and return its result with its wall time in milliseconds.

    Used by the latency assertions in the tests, not by any request path: a route that
    timed itself would be publishing a number nobody checks.
    """
    started = time.perf_counter()
    result = work()
    return result, (time.perf_counter() - started) * 1000


class SearchService:
    """Runs the ladder in stages, merges them, and declares what it read."""

    def __init__(self, repository: _Repository) -> None:
        self._repository = repository

    def search(
        self,
        query: str,
        *,
        limit: int,
        offset: int,
        result_type: str | None = None,
        veda: str | None = None,
        work: str | None = None,
        language: SearchLanguage = SearchLanguage.ANY,
    ) -> SearchResponse:
        """Search the declared surfaces and return one ranked page.

        ``query`` is never interpolated. It travels as ``$q`` (lower-cased) and ``$q_raw``
        (verbatim, for the case-sensitive Sanskrit and identity surfaces) and as nothing
        else, so a query containing Cypher or Lucene metacharacters is a string compared
        against data rather than syntax compared against a parser.
        """
        cleaned = query.strip()
        if not cleaned:
            raise BadRequestError(
                "A search needs a non-empty q.",
                hint="q accepts a canonical key, a citation, a Sanskrit or English phrase, "
                "a dictionary headword, or an entity name.",
            )
        folded = fold_diacritics(cleaned)
        if not folded:
            # str.strip() removes whitespace and NOT combining marks, so a query of bare
            # marks survived the emptiness check above, folded to "", and then matched
            # every entity in the graph through `x STARTS WITH ''` -- returning arbitrary
            # deities at a real ranking score, in 668ms. Emptiness has to be tested after
            # folding, because folding is what can create it.
            raise BadRequestError(
                "A search needs at least one character that is not a combining mark.",
                hint="Combining marks are folded away before matching, so a query made "
                "only of them has nothing left to match. Include the letters they sit on.",
            )
        if offset + limit > SEARCH_WINDOW_LIMIT:
            raise BadRequestError(
                f"offset + limit may not exceed {SEARCH_WINDOW_LIMIT} on search.",
                hint="Narrow the query, or filter by type, veda or work. Deep paging is "
                "refused rather than served against an incomplete candidate set.",
            )

        type_labels = self._resolve_type_filter(result_type)
        self._validate_veda(veda)
        self._validate_work(work)

        parameters: dict[str, Any] = {
            "q": cleaned.lower(),
            "q_raw": cleaned,
            "veda": veda,
            "work": work,
            "type_labels": sorted(type_labels) if type_labels is not None else None,
            # A type filter has to silence the surfaces it does not name, or type=devata
            # would still be served Rigvedic passages by the text rungs.
            "passages_wanted": type_labels is None or "Passage" in type_labels,
            "q_folded": folded,
            "fold_marks": list(DIACRITIC_MARKS),
            "rung_order": RUNG_ORDER,
            "fetch": min(offset + limit + 1, SEARCH_WINDOW_LIMIT),
        }

        window = offset + limit
        candidates: dict[tuple[str, str], _Candidate] = {}
        surfaces: list[SearchSurface] = []
        excluded_ascriptions = 0
        truncated = False

        skipped: dict[str, str] = {}
        for stage in self._stages(language):
            reason = self._skip_reason(stage, candidates, window, cleaned)
            if reason is not None:
                skipped[stage.name] = reason
                continue
            for surface in stage.surfaces:
                if surface not in surfaces:
                    surfaces.append(surface)
            stage_parameters = {**parameters, "fetch": self._stage_fetch(stage, candidates, window)}
            for cypher in stage.queries:
                rows = self._repository.run(cypher, **stage_parameters)
                truncated = truncated or len(rows) >= int(stage_parameters["fetch"])
                for row in rows:
                    candidate, excluded = self._to_candidate(row, cleaned)
                    excluded_ascriptions += excluded
                    if candidate is None:
                        continue
                    key = (candidate.result_type.value, candidate.stable_id)
                    existing = candidates.get(key)
                    if existing is None or candidate.rung_index < existing.rung_index:
                        candidates[key] = candidate

        ordered = sorted(candidates.values(), key=lambda c: (c.rung_index, -c.weight, c.stable_id))
        page = ordered[offset : offset + limit]
        total = None if (truncated or skipped) else len(ordered)

        return SearchResponse(
            items=[self._to_result(c) for c in page],
            pagination=PaginationMeta(
                limit=limit,
                offset=offset,
                returned=len(page),
                total=total,
                has_more=(offset + len(page)) < total if total is not None else len(page) == limit,
            ),
            data_status=KnowledgeStatus.PARTIAL,
            caveats=self._caveats(
                surfaces, excluded_ascriptions, truncated, skipped, language, veda
            ),
            surfaces_searched=surfaces,
            surface_coverage=[
                view for surface in surfaces if (view := _coverage_view(surface)) is not None
            ],
        )

    # -- staging ----------------------------------------------------------------

    def _stages(self, language: SearchLanguage) -> tuple[_Stage, ...]:
        """The stages a language filter leaves in play, strongest rung first."""
        stages: list[_Stage] = [_STAGE_IDENTITY, _STAGE_ENTITIES]
        if language is not SearchLanguage.ENGLISH:
            stages += [_STAGE_SANSKRIT_TEXT, _STAGE_NORMALIZED_TEXT, _STAGE_LEMMA]
        if language is not SearchLanguage.SANSKRIT:
            stages.append(_STAGE_TEXT_ENGLISH)
        return tuple(stages)

    def _stage_fetch(
        self, stage: _Stage, candidates: dict[tuple[str, str], _Candidate], window: int
    ) -> int:
        """How many rows this stage can still contribute to the requested page.

        The rungs are strictly ordered, so a stage whose best rung is beaten by ``above``
        candidates already collected can place at most ``window - above`` rows. Asking the
        database for fewer shrinks the sort it has to perform, and the sort is the cost: an
        unindexed text scan with ``ORDER BY stable_id LIMIT n`` must see every match before
        it can return the first row, so ``n`` is the size of the heap it keeps.

        This matters only for deep pages, which is where it was measured to matter: at
        ``limit=200`` a Sanskrit-shaped query read 472ms because every text stage was asked
        for 201 rows even when the entity stage had already filled 190 of the page.
        Never below 1, so a stage is either skipped outright by :meth:`_skip_reason` or
        asked a real question.
        """
        base = min(window + 1, SEARCH_WINDOW_LIMIT)
        if stage.name not in _SKIPPABLE_STAGES:
            return base
        above = sum(1 for c in candidates.values() if c.rung_index < stage.first_rung_index)
        return max(1, min(base, window - above + 1))

    def _skip_reason(
        self,
        stage: _Stage,
        candidates: dict[tuple[str, str], _Candidate],
        window: int,
        query: str,
    ) -> str | None:
        """Why reading ``stage`` cannot change the answer, or ``None`` if it could.

        Three reasons, each a proof rather than a heuristic, and each reported in the
        response so a fast answer never implies it read everything.

        *The corpus provably cannot contain the query.* No Sanskrit text in this graph
        contains the letter pair ``fe``, so none contains ``fever``, so the three Sanskrit
        scans -- 144ms together -- would return nothing. See
        :func:`sanskrit_cannot_contain`.

        *The caller named one object exactly.* A hit at ``EXACT_CANONICAL_KEY`` or
        ``EXACT_CITATION`` means someone pasted ``VG:DEVATA:INDRAH`` or ``RV 1.1.1`` and
        wants that object, not the verses whose text happens to contain the string.

        *The page is already full of rows this stage cannot outrank.* The rungs are
        strictly ordered, so once ``window`` candidates sit above ``stage.first_rung``,
        nothing the stage returns can enter the page. This is why the Sanskrit surfaces are
        three stages and not one: ``somam`` fills the page from the plain-Sanskrit scan
        alone, and the normalised, lemma and translation scans behind it -- 112ms -- cannot
        affect the result.
        """
        if stage.name not in _SKIPPABLE_STAGES:
            return None
        if stage.reads_sanskrit and (pair := sanskrit_cannot_contain(query)) is not None:
            return (
                f"no Sanskrit text in this corpus contains the letter pair '{pair}', so "
                "none can contain this query"
            )
        if any(c.rung_index <= _EXACT_IDENTITY_LAST_RUNG for c in candidates.values()):
            return "the query matched an object by its exact id or citation"
        above = sum(1 for c in candidates.values() if c.rung_index < stage.first_rung_index)
        if above >= window:
            return "the requested page is already full of rows this surface cannot outrank"
        return None

    # -- row mapping ------------------------------------------------------------

    def _to_candidate(self, row: dict[str, Any], needle: str) -> tuple[_Candidate | None, int]:
        """Turn one graph row into a candidate, applying the deity population contract.

        Returns the candidate and how many non-deity Anukramani ascriptions were dropped,
        which is 0 or 1. The count is reported in a caveat rather than swallowed:
        searching "Vasistha" matches a ``:Devata`` node whose ``structure`` is HUMAN, and a
        caller told nothing reads the absence as "the graph does not know that name".
        """
        stable_id = row.get("stable_id")
        if not isinstance(stable_id, str) or not stable_id:
            return None, 0
        try:
            match_type = MatchType(str(row.get("match_type")))
        except ValueError:  # pragma: no cover - a coding error, not a client error
            return None, 0
        rung_index = MATCH_TYPE_ORDER.index(match_type)

        if "node_labels" in row:
            result_type = result_type_for_labels(row.get("node_labels"))
            if result_type is SearchResultType.DEVATA and not is_deity(row.get("structure")):
                return None, 1
            body = row.get("definition") or row.get("short_description")
            return (
                _Candidate(
                    rung_index=rung_index,
                    match_type=match_type,
                    result_type=result_type,
                    stable_id=stable_id,
                    display_label=str(row.get("display_label") or stable_id),
                    subtitle=_first_line(body),
                    snippet=(
                        _snippet(body, needle) if match_type is MatchType.CONCEPT_MATCH else None
                    ),
                    veda=None,
                    weight=int(row.get("weight") or 0),
                ),
                0,
            )

        citation = row.get("citation")
        return (
            _Candidate(
                rung_index=rung_index,
                match_type=match_type,
                result_type=SearchResultType.PASSAGE,
                stable_id=stable_id,
                display_label=str(citation or stable_id),
                subtitle=_passage_subtitle(row),
                snippet=_snippet(row.get("snippet_source"), needle),
                veda=row.get("veda"),
                weight=int(row.get("weight") or 0),
            ),
            0,
        )

    def _to_result(self, candidate: _Candidate) -> SearchResult:
        return SearchResult(
            type=candidate.result_type,
            stable_id=candidate.stable_id,
            display_label=candidate.display_label,
            subtitle=candidate.subtitle,
            snippet=candidate.snippet,
            score=MATCH_TYPE_SCORES[candidate.match_type],
            match_type=candidate.match_type,
            veda=candidate.veda,
        )

    # -- filters ----------------------------------------------------------------

    def _resolve_type_filter(self, result_type: str | None) -> frozenset[str] | None:
        """Map a requested type onto graph labels, or refuse it by name.

        An unknown type is a 400 listing what is available, never an empty 200. A deity
        type IS accepted here, unlike on the generic entity surface, because search applies
        the population contract to every row it returns.
        """
        if result_type is None:
            return None
        requested = result_type.strip()
        slug = requested.lower()
        if slug in DEITY_SLUGS or requested.upper() == "DEVATA":
            return frozenset({validated_label("Devata")})
        if slug in {"passage", "mantra"} or requested.upper() == "PASSAGE":
            return frozenset({validated_label("Passage")})
        spec = ENTITY_TYPES.get(slug) or {s.type_name: s for s in ENTITY_TYPES.values()}.get(
            requested.upper()
        )
        if spec is None:
            raise BadRequestError(
                f"'{requested}' is not a searchable result type.",
                hint="Available: passage, devata, "
                + ", ".join(sorted(ENTITY_TYPES))
                + ". GET /api/v1/entities lists them with counts.",
            )
        return frozenset({validated_label(spec.label)})

    def _validate_veda(self, veda: str | None) -> None:
        if veda is not None and veda not in CORPUS_MANTRAS:
            raise BadRequestError(
                f"'{veda}' is not a corpus in this graph.",
                hint="Corpora: " + ", ".join(VEDA_ORDER) + ".",
            )

    def _validate_work(self, work: str | None) -> None:
        if work is not None and work not in KNOWN_WORK_IDS:
            raise BadRequestError(
                f"'{work}' is not a work in this graph.",
                hint="GET /api/v1/works lists the four works and their ids.",
            )

    # -- caveats ----------------------------------------------------------------

    def _caveats(
        self,
        surfaces: list[SearchSurface],
        excluded_ascriptions: int,
        truncated: bool,
        skipped: dict[str, str],
        language: SearchLanguage,
        veda: str | None,
    ) -> list[CaveatView]:
        caveats = [
            CaveatView(
                text=(
                    "A search miss is not textual absence. This response read the surfaces "
                    "in `surfaces_searched`, and `surface_coverage` states which corpora "
                    "each of them reaches; several reach fewer than four."
                ),
                source="measured",
            )
        ]
        for surface in surfaces:
            note = SURFACE_NOTES.get(surface)
            coverage = SURFACE_COVERAGE.get(surface)
            if note is None or coverage is None:
                continue
            reached = ", ".join(f"{v} {coverage[v]:,}" for v in VEDA_ORDER if v in coverage)
            missing = [v for v in VEDA_ORDER if v not in coverage]
            suffix = f" Not reached at all: {', '.join(missing)}." if missing else ""
            caveats.append(
                CaveatView(
                    text=f"{surface.value} reaches {reached} passages.{suffix} {note}",
                    source="measured",
                )
            )
        if excluded_ascriptions:
            caveats.append(
                CaveatView(
                    text=(
                        f"{excluded_ascriptions} match(es) were Anukramani devata-slot "
                        "ascriptions that are not gods -- a human patron, a "
                        "praise-of-a-gift label, or a non-divine subject -- and are "
                        "excluded from DEVATA results rather than typed as deities. See "
                        "GET /api/v1/devatas?population=all_ascriptions to read the slot "
                        "as the Anukramani leaves it."
                    ),
                    source="deity_population_contract",
                )
            )
        for stage_name, reason in skipped.items():
            caveats.append(
                CaveatView(
                    text=(
                        f"The {stage_name} surface was NOT read, because {reason}. `total` "
                        "is therefore null. This is a proof that reading it could not have "
                        "changed the answer, NOT a sample of it and NOT a statement that "
                        "the corpus lacks those matches -- but if you wanted that surface "
                        "specifically, narrow the query or set the language filter."
                    ),
                    source="measured",
                )
            )
        if truncated:
            caveats.append(
                CaveatView(
                    text=(
                        f"At least one surface returned the maximum {SEARCH_WINDOW_LIMIT} "
                        "candidates it is allowed, so `total` is null: not counted, which "
                        "is not the same as small. Narrow the query for an exact total."
                    ),
                    source="measured",
                )
            )
        if language is not SearchLanguage.ANY:
            caveats.append(
                CaveatView(
                    text=(
                        f"language={language.value} restricted the ladder to the rungs "
                        "reading that language. The excluded rungs were not run, so their "
                        "silence is this filter and not a finding about the corpus."
                    ),
                    source="measured",
                )
            )
        if veda is not None:
            caveats.append(
                CaveatView(
                    text=(
                        f"veda={veda} filters PASSAGE rows only. A deity, seer, concept or "
                        "formula is a corpus-wide object with no single Veda, so entity "
                        "rows are returned unfiltered rather than dropped -- open one to "
                        "see its own per-Veda distribution."
                    ),
                    source="measured",
                )
            )
        return caveats


__all__ = [
    "ALL_QUERY_TEMPLATES",
    "DIACRITIC_MARKS",
    "DIACRITIC_REPERTOIRE_QUERY",
    "RUNG_ORDER",
    "SANSKRIT_ASCII_BIGRAMS",
    "SANSKRIT_ASCII_TRIGRAMS",
    "SANSKRIT_REPERTOIRE_QUERY",
    "SEARCH_WINDOW_LIMIT",
    "SURFACE_COVERAGE",
    "SURFACE_NOTES",
    "SearchService",
    "fold_diacritics",
    "marks_present_in",
    "measure_surface_coverage",
    "result_type_for_labels",
    "sanskrit_cannot_contain",
    "sanskrit_repertoire_from",
    "timed",
]
