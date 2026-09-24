# Operator-only v0.2 family coverage review

Do not distribute this file to annotators or route implementers before their artifacts are sealed. `operator_scenario_map.jsonl` maps opaque case IDs to these families. Each has two contrasts; all 24 cases are reserved for unseen evaluation, with v0.1 development cases as the only tuning set.

| Family | New scenario decision | Closest v0.1 dimension and separation |
| --- | --- | --- |
| U01 | Nested chain of report/quote and pronoun speaker inside the forwarded message | B04/B15 have one attribution layer; no nested source chain. |
| U02 | Counterfactual nonactual world versus observed alternate outcome | B05 has possibility/intention, not a contrary-to-fact conditional world. |
| U03 | Explicitly negated candidate cause alongside a two-link causal sequence and temporal distractors | B03/B17 test positive cause and BEFORE; this tests **scope of negated cause plus replacement**, and is the new F8 probe family. Relation primitives overlap by design, scenario family does not. |
| U04 | External policy obligation and whether action later satisfied it | B01/B05 distinguish event from intention, not deontic authority. |
| U05 | Quantified group with exception scope and changing membership status | No v0.1 quantifier/cardinality family. |
| U06 | Two distinct occurrences versus a repeated alert about one occurrence | B09 tests recap support, not event cardinality across days. |
| U07 | Withdrawal of earlier source support and historical authority | B16 clarifies an ambiguous referent; it does not retract a source or invalidate a numeric claim. |
| U08 | Approximate duration, exact log duration, and incompatible units | No v0.1 numerical precision/unit family. |
| U09 | Reciprocal lending/borrowing with actor, recipient, owner and return direction | B11 has two claims, but no reversible role mapping. |
| U10 | Passive event with audit-log agent provenance versus unknown agent | B04 reports a quote, not passive action/agent extraction. |
| U11 | Disjunction over alternative event sources versus a confirmed one | B07 has pronoun referent ambiguity, not competing event alternatives. |
| U12 | UTC/local-date boundary and source precision | B18 separates event and admission time; it does not test timezone conversion. |

“Unseen” means no scenario family or case text appears in v0.1 development/prompt examples and no v0.2 case is used for Route E tuning. It does **not** mean every relation primitive is novel; CAUSE and temporal ordering must recur to test transfer. The packet validator checks exact text nonreuse; family novelty is a human design judgment documented here. If access logs later show route developers viewed v0.2 cases before sealing, mark those families contaminated instead of claiming unseen generalization.
