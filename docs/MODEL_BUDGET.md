# Model routing and resource policy

## Purpose and limits of this policy

Preserve the owner's ChatGPT allowance while obtaining independent daily review. These are conservative project defaults to calibrate after several observed runs. They are not provider limits, a prediction of cost, or a guarantee that a particular percentage of the subscription will remain.

OpenAI distinguishes API token prices from included subscription allowance. Usage also depends on model, context, reasoning, tools and other account activity. Use actual readings when available. Never convert an API price into a supposed number of ChatGPT tasks. [Official pricing guidance](https://learn.chatgpt.com/docs/pricing?codex-pricing-plans=individual).

## Routes and responsibilities

- A: the exact provider route corresponding to the owner's label “qwen 3.8 flash next.” Resolve its identifier from the configured runtime/model catalog; do not guess it or substitute a similarly named model.
- B/Terra: gpt-6.1-terra when available through the owner's configured supported route. Use low effort for tightly bounded review, presentation/documentation work, evidence inspection or a separate small test task. During review, run/check tests without co-authoring the same acceptance unit. It is optional assistance, not a second all-night implementation loop.
- B/Sol: gpt-6.1-sol, standard speed, medium effort by default. One daily audit session covers the frozen evidence packet and actual diffs. Prefer reducing scope to raising effort. Higher effort requires a separately admitted budget and owner-configured policy change.

These assignments are project choices, not promises about relative model quality. Availability and provider identifiers must be checked in the installed runtime. [Official model guidance](https://learn.chatgpt.com/docs/models?surface=web).

B uses one model at a time. The launcher ends/checkpoints a Terra job before starting the Sol audit. Preserve the worker identity and authorship record across the change. Do not ask a model to impersonate another model or assume it can reconfigure its own route.

## Starting caps

All caps are ceilings, not targets. The first reached cap stops further admissions. Counters persist across retries, restarts and job/model changes.

| Scope | Cap |
|---|---|
| All workers | 2 active model workers; 1 active GPT job; 1 task per worker |
| A/Qwen nightly | 180 model requests; 40 requests per task; 60 minutes per task; 2 failed approaches before replan |
| B/Terra nightly | At most 2 jobs; each at most 4 requests, 10 minutes, 20,000 aggregate input tokens and 2,000 aggregate generated tokens |
| B/Sol nightly | At most 1 audit; 8 requests, 20 minutes, 60,000 aggregate input tokens and 8,000 aggregate generated tokens |
| B combined nightly | 16 requests, 40 summed job wall-clock minutes, 100,000 aggregate input tokens, 12,000 aggregate generated tokens |
| B per request | At most 16,000 total input tokens and 3,000 maximum generated tokens, further reduced by remaining job/night limits |
| Unknown allowance mode | No Terra; at most one Sol audit with 4 requests, 10 minutes, 40,000 aggregate input and 4,000 aggregate generated tokens |

Every job time cap is wall-clock elapsed time from dispatch through completion, including tools and waiting. The Sol audit is one continuous session of at most 20 minutes, or 10 in UNKNOWN mode. Aim to spend the first 12 minutes/up to 5 requests on initial review and reserve the remainder for scoped rechecks; under UNKNOWN mode use a smaller proportional split. A completed/expired audit cannot reopen to use leftover calls. Unverified late fixes wait for the next night.

Input accounting includes repeated conversation, system/tool definitions and retrieved context, not just the task prose. Generated-token accounting includes reasoning where exposed by the provider. The runtime must apply request/output caps through supported controls and record actual usage when returned. If a provider omits a metric, mark it unknown and rely on the independent request/time caps; do not advertise an unenforceable exact token ceiling. If request count, routing or maximum generation cannot be bounded, do not start unattended GPT work.

Reserve the entire unused Sol allocation before admitting Terra. Terra does not borrow it. An unused allocation expires at the end of the run; it does not justify extra work. The same rule applies if an audit finishes early. Auxiliary model requests, compression, retries, background helpers and any model-driven review count against the relevant route and aggregate budget.

## Subscription telemetry

Before admitting GPT, and between requests when a supported non-inference reading is available, record source, timestamp, account identifier without secrets, applicable window IDs, used/remaining amount and reset instants. Cache no longer than five minutes for admission. Prefer a supported runtime/CLI interface, not scraping login pages or sending a prompt to ask the model about its quota.

When reliable comparable readings exist:

1. Do not admit GPT if any applicable quota window has 30% or less remaining.
2. Stop further GPT admissions if observed account consumption during this run rises by 10 percentage points in any short window, or 2 percentage points in a weekly window.
3. Preserve window identities across resets. Never subtract percentages from different windows. A reset does not reset the project's nightly request/token counters.
4. Other account activity may consume the allowance; treat a reduced reserve conservatively. Do not claim all observed consumption came from this repository.

These are admission thresholds, not mathematically exact spending caps: a request may use more than expected before the next reading. The separate bounded request/context/time policy limits that exposure. If the owner needs a guaranteed monetary ceiling, require a billing route with enforceable monetary limits; do not promise that a prompt can enforce a subscription percentage.

Missing, stale or incompatible telemetry enters UNKNOWN mode only if no stronger block exists. The default explicitly permits one much smaller audit-only run under the independent caps above, labeled QUOTA UNKNOWN in the report. No Terra assistance is admitted. The owner may set worker_b_caps.unknown_quota.mode to stop_gpt for stricter preservation. Agents cannot switch from stop_gpt to audit_only themselves.

Persist known quota exhaustion, reserve, authentication and payment blocks across missing readings, restarts and nights. UNKNOWN never clears them. Require a fresh reading confirming recovery for the affected window/route, or an authorized operator action resolving the cause; a predicted reset time alone is not proof of recovery. A nightly-consumption threshold breach remains blocked for that entire run even if a provider window resets.

Entering UNKNOWN tightens remaining capacity: previous jobs, calls, tokens and time still count. Intersect remaining normal capacity with the reduced UNKNOWN caps; do not open a second audit or refill an allowance. If prior work already exceeds a reduced cap, stop further admissions. A known block always prevents the audit as well as Terra work.

## No hidden spending routes

Use only owner-configured authenticated routes. Never silently switch from a ChatGPT-linked route to a billable API key, another account, premium speed, a different model or a paid provider. Check primary and auxiliary fallback chains: title generation, compression, vision and helper tools can invoke models too. Disable unnecessary helpers and ensure permitted ones are metered under the same policy.

Do not modify credentials, credential pools, billing plans, model pins or fallback configuration to get around a limit. A 401/403 or payment/quota error parks the affected route. A transient transport error permits at most one bounded retry, counted against the budget, after reconciling whether the prior attempt ran. An unknown previous outcome is not a free retry.

Count at the outbound provider-attempt boundary, not at the agent-visible turn. One logical turn making three actual dispatches consumes three slots. Disable uncontrolled SDK/stream reconnect retries or meter them in the same durable ledger. Auxiliary calls also count. An agent cannot evade a limit through a lower-level library's retry loop.

## Efficient collaboration

Qwen prepares concise evidence packets: task intent, base/head, changed paths, actual diff location, focused check results, user-visible evidence and specific concerns. Sol independently reads the relevant code/diff; it must not approve only a builder's summary. Scope the packet to fit the available context and leave incomplete review pending.

Use deterministic scripts and existing tools for sorting tasks, collecting logs, counting calls, checking time and detecting no-work conditions. Do not spend GPT calls on polling, greetings, repetitive planning, Git status or formatting reports. Disable model jobs altogether on nights without new changes, unresolved findings or due revalidation; record an audit skip locally. If a required audit cannot run, retain pending changes and the reason rather than granting synthetic approval.

After the first three completed nights, compare accepted work and observed usage. Recommend smaller/larger caps with evidence, but only the owner may raise resource limits. Do not tune by consuming the maximum every night.
