"""The semantic candidate layer: the first place in VedaGraph a model may speak.

Nothing here writes to the canonical corpus, the traditional metadata layer or the
lexical layer. Those three are inputs, they are read-only, and a semantic run that
needed to change one of them would be a bug, not a finding.

What a language model produces here is a *candidate*. It becomes knowledge only after
deterministic validation, an acceptance policy, and — for anything interpretive — a
person. That sequence is the whole point of the layer, and every module in this package
exists to keep some part of it honest.
"""
