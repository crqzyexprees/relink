# Track fit and next steps

Update 2026-10-25: the owner authorized the Gemini proposal below and requested
it as core functionality. It is now integrated automatically into both paper/PDF
dataset actions, with checked source excerpts and real DataCite discovery. See
[implementation, limits and live evidence](GEMINI.md). This supports a concrete
Gemini demonstration; it does not establish sponsor-prize eligibility. No event
submission, deployment, registration or purchase has been performed.

Reviewed 2026-10-24 against the event-specific
[HackPSU Fall 2026 listing](https://hackpsu-fall-2026.devpost.com/) and
[rules](https://hackpsu-fall-2026.devpost.com/rules). These are recommendations,
not claims of eligibility, award qualification, or implemented integrations.
Organizer confirmation is needed for conflicting deadlines and permitted prize combinations.

## Prioritized improvements

1. **Strengthen the research evidence first.** Finish a five-case real broken-link
   evaluation, including failures; show how a paper leads to an identified dataset
   and what remains unverified. Record actual manual versus assisted effort if
   presenting time savings. Finish the source release, browser walkthrough, and
   short video before adding multiple services.
2. **Grounded dataset identification using Gemini — now implemented as core.**
   Paper/PDF Find actions identify dataset names/versions plus short supporting excerpts/page numbers
   from extracted paper text. Check every excerpt against the actual text before
   displaying it. Pass suggested names to existing DataCite discovery; returned
   candidates still require independent evidence and retain current verification
   rules. Never accept generated URLs, hashes, or a model's assurance as recovered
   resources. Retain an operational no-key/provider-failure path.
3. **Private history with native OIDC — isolation implemented, provider setup pending.** Authentication binds
   all history reads/writes to the authenticated identity; adding a login button
   alone does not isolate data. Per-account issuer/subject storage is now the
   default, with guest/expiry checks, state cleanup and private browser-local
   exports. Existing local history remains separate; explicit local mode must not
   be used on public hosting. Auth0 can use the native adapter, but actual OAuth
   credentials and a browser login test remain pending; see [AUTH.md](AUTH.md).
   Streamlit has [native OIDC support](https://docs.streamlit.io/develop/concepts/connections/authentication).
4. **A reproducible Vultr deployment, if resources are available.** Use the same
   Streamlit app, HTTPS, corresponding source release, service configuration, and
   safe history settings. Cloud provisioning/accounts/billing need owner action;
   a public URL alone does not resolve parser or strict network-deadline limits.

The incorporated AI workflow supports a meaningful model demonstration in addition
to the research workflow. Current paper matching is whole-word keyword
scoring, not an AI model. Do not describe existing matching as model inference.

Gemini [structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)
can constrain a response shape, but do not guarantee factual correctness. Its
[billing documentation](https://ai.google.dev/gemini-api/docs/billing) offers a
limited free tier for certain models; an API key and quota handling are needed.
Check [data-use terms/pricing](https://ai.google.dev/gemini-api/docs/pricing)
before sending private/unpublished research. No paid usage has been authorized.

Database migration, blockchain proofs, and voice narration are lower priorities
for this demonstration. They add scope without first solving named-dataset
identification, which is the most relevant observed workflow gap.

The original track review made no integration changes. The later owner-authorized
Gemini implementation is recorded separately in STATUS.md and GEMINI.md.
