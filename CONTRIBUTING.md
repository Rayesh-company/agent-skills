# Contributing

Keep skills concise and preserve one source of truth. Put shared acceptance and
gap-routing behavior in `ACCEPTANCE-LOOP.md`; specialists should point to it and
describe only their owned scope.

Every pull request that changes workflow behavior must state:

- the implemented increment and acceptance criteria;
- changed canonical contracts;
- scenarios exercised and verification results;
- migration or compatibility impact;
- unresolved gaps and intentionally deferred work;
- evidence that router, operational skills, templates, and adapter agree.

Before requesting review, run the commands in `README.md`. Review has two
independent axes: repository standards and originating spec. A change is
accepted only when CI passes and neither axis has a blocking finding.

Do not merge a change that introduces an unknown skill/mode, an unscoped legacy
invocation, a broken relative link, ambiguous canonical tracker state, or a
claim of operational behavior that exists only in a proposed specification.
