# No row in this artifact was reviewed by listening

Stated plainly because the alternative is to let a pile of structural evidence be read as a
listening check. It is not one.

**Reviewed population: 0 of 150 rows. Rows heard: 0. Reviewers: none.**

`GAP-AUDIO-004`'s own closure test reads:

> "/api/v1/audio/stats RV reaches 10,552, and a human listening check confirms RV 8.49.1
> plays the Valakhilya hymn rather than the hymn at that position in the continuous
> numbering."

The first clause is satisfied by this artifact once imported. **The second is not, and
remains OPEN.**

## What stands in its place, exactly

Set out in `proofs/valakhilya-permutation-not-applicable.md`. In one line each:

- the source asserts each coordinate on three surfaces (location alias set, file caption,
  file name) and in two numbering conventions;
- the text at that location is this corpus's own text and its unique best match across all
  10,552 Rigvedic stanzas, on 150 of 150 rows;
- the two corpora's stanza structures are a bijection with zero per-hymn disagreement;
- every one of the 150 files was fetched byte-for-byte and decoded, so its length is measured
  rather than assumed, and the lengths correlate with our own syllable counts at r = 0.87
  against r = 0.09 for the permuted assignment.

That is a strong chain, and it is a chain about **coordinates and file identity**. A listener
answers a different question — whether the voice on the file recites the text — and no amount
of metadata agreement answers it.

## Why the acoustic check is not a substitute

Duration against syllable count would catch a gross misattachment: a whole hymn behind one
stanza's key, a pada-patha recitation sold as samhita, an eleven-hymn shift. It would not
catch a subtle one, such as two adjacent stanzas of the same metre swapped, and it cannot
distinguish this reciter's Rigveda from another reciter's Rigveda. It is a floor, not a
verdict.

## How the sheet must be built, when someone does it

This project has been caught once already by a listening sheet whose decisive row quoted what
a *broken* mapping would have played, so the sheet confirmed the wrong answer. The failure
mode is generating the expected content from the same transform under test.

So:

1. **Give the reviewer both candidates and no answer.** For each sampled row, print the
   Sanskrit text of the row's own key *and* the text of the stanza the rejected hypothesis
   would put there — for a Valakhilya row, RV 8.49.x beside RV 8.60.x — in a randomised order,
   unlabelled. The reviewer says which one they heard, or neither.
2. **Take the text from the canonical store, not from the source.** Read
   `GRETIL.RV.AUFRECHT` out of the graph for both candidates. If the sheet quotes the source's
   own text back at the source, it tests nothing.
3. **Start with the 80 Valakhilya rows.** They are the ones the registry names, the ones no
   other public per-stanza recording carries, and the ones where a shift would be systematic
   rather than isolated.
4. **Then sample the 70.** Those verses are missing from at least two circulating parayana
   recordings (see `proofs/vedsearch-rv-150-negative.md`), so a listener should confirm that
   this collection really does carry them rather than carrying a neighbour twice. RV 9.98,
   entirely absent from both other recordings, is the sharpest case: check 9.97.58, 9.98.1 and
   9.98.12 as a contiguous run.
5. **Record the population, not the pass rate alone.** "n heard of 150" on the artifact, and
   never a figure that implies more.

## Also unheard, and worth saying

No independent check was made that the reciter on these files is Pt. D. P. Kinjawadekar. That
attribution is the National Library of Denmark's and VedaWeb's, carried through on the row as
theirs. It is the only audio source in this catalogue that names a reciter at all, which is
why it was preferred — but a named reciter is a claim by a named institution, not a
measurement.
