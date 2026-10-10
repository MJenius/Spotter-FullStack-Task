# AGENTS.md

Instructions for AI coding sessions in this repository.

1. **Read [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) before changing code.** It is the canonical source of product and business requirements (risk thresholds, load overrides, ranking, contracts, decisions).
2. Do not duplicate or contradict business rules in other documents or code comments — link to the spec section instead.
3. When a genuine ambiguity requires a decision, update the spec explicitly (mark it **[DEC]** and add to the §18 decision log) in the same change.
4. Explain any deviation from the assessment. Never silently weaken an acceptance criterion.
5. Never introduce secrets, real API keys, fabricated live data, fake successful analyses, or unverified claims. `GOOGLE_ROUTES_API_KEY` is backend-only; never use a `VITE_` prefix for secrets.
6. Never treat missing weather as Low risk.
7. Run relevant checks (see README "Tests") and report failures honestly. Do not fake test counts.
8. Keep scope lean: no DB models, auth, Docker, Redis, or extra services unless the spec is updated with justification.
