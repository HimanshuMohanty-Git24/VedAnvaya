"""Product content layers that sit beside the frozen graph rather than inside it.

The ontology and the graph census are release gates. Anything that is product content
rather than an assertion about the Vedas -- audio being the first of it -- lives here as a
sidecar keyed by ``canonical_key``, so adding it mutates neither.
"""
