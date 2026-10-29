# Project charter

## Mission

Build a dependable, attractive local workspace for supervising coding agents, starting from the owner's existing Zeron fork. Preserve the aesthetic quality and useful workflows that motivated the fork. Make the installed application independent of a vendor's backend, account system, synchronization service, billing infrastructure and hosted storage. Adapt selected ideas from Overseer to make everyday agent work easier to start, understand, review and recover.

The owner should be able to keep using the product if the original vendor disappears, its servers are unavailable, or the computer is disconnected. The owner chooses where their code, session history and credentials live, and which optional services receive data.

## Meaning of “no external-server dependence”

The local control plane is authoritative. Opening the app, browsing projects, reading history, managing the local queue, viewing diffs, inspecting settings and restoring local work must not require network access, a hosted login, an entitlement check or a remote database.

Allowed optional connections are user-selected AI providers, explicit Git remote actions, and authenticated direct access to the user's machines. Installed local models may be supported through an existing adapter. A hosted model still needs its provider's network service; offline product acceptance must not pretend otherwise. Provider sign-in is separate from an application account.

The default installation must make zero unsolicited outbound connections. Check startup, idle work, updates, harness catalogs, usage probes, title generation, avatars, fonts, previews, telemetry and crash reporting. Connection categories must have explicit purposes and understandable controls. User-enabled provider status polling is optional and must honor offline mode.

A local engine, daemon, Unix socket or authenticated loopback service is permitted. Replacing one vendor cloud with another, a mandatory self-hosted hub, a required VPN service or a hidden relay does not meet the objective. A user-owned headless machine may run an optional engine; the laptop must still work without it.

## Preserve the product that attracted the owner

Retain the fork's coherent layout, visual density, typography, spacing, themes, surfaces, motion, keyboard interaction and fast navigation. Keep its agent conversation, tool activity, terminal, file/diff, project/worktree, approvals and questions workflows when present and functioning. Preserve existing supported harnesses; the two models building the product do not define the product's supported-agent list.

Before UI changes, capture the actual fork's main workflows in light and dark themes where supported. Use its components and design conventions. New task, usage or machine controls should feel native to that design. Screenshots from an upstream README are references, not the baseline of this checkout.

Do not turn the product into a generic administration dashboard, embed a second full UI stack to avoid integration, replace the framework gratuitously, or remove a useful feature merely because its name contains “cloud” or “sync.” Replace each affected feature's dependency, deliberately defer it, or explain its removal in the feature inventory.

## Intended daily experience

1. Open the app without creating an application account.
2. Choose a local project and a configured agent; optionally choose an owned remote machine later.
3. Start or schedule a clearly scoped task with a visible model and permission profile.
4. See whether the task is running, queued, waiting for input, limited, failed or complete.
5. Answer a question or approval, inspect the real diff and test evidence, and decide what to keep.
6. Close and reopen the app without losing durable history or silently starting the same work twice.
7. Export or back up local records and understand exactly which optional connections are enabled.

## Overseer ideas, in priority order

Adopt behavior and interaction patterns where they fill demonstrated gaps: an attention-focused session view; explicit agent capabilities; isolated worktrees; durable, idempotent scheduling; real subscription-limit readings with unknown states; pause/resume and graceful failure; readable changes and review evidence; and later protected local previews and direct-machine administration.

Use existing Zeron equivalents where they already work. Each candidate needs a short comparison: current behavior, user benefit, smallest integration, verification and ongoing maintenance cost. Do not copy the entire application or import all its dependencies. Keep copied or adapted source attributable to its pinned origin and retain applicable notices.

## Scope boundaries

The first release is a single-owner local workspace. Shared SaaS accounts, organization billing, public session sharing, vendor discovery, managed cloud provisioning, commercial licensing checks, cloud push notifications, mandatory tunnels, remote desktop streaming, and chat-platform bots are outside the first release. Arena-style agent racing is optional future work because it multiplies executions and cost.

Direct owned-machine access is in scope after the reliable local core. Start with explicit SSH access using existing user-managed keys or the system agent, host identity verification and per-machine workspace permissions. Do not promise automatic NAT traversal, seamless offline multi-master synchronization or access to unreachable machines.

Noether is a separate experiment in the same eventual organization. These agents do not alter it, share its secrets, use its compute budget or move its files.

## Engineering stance

Inspect the actual fork before designing changes. Current upstream research found Rust/GPUI, a native engine, Loro documents and local SQLite persistence; an older fork may differ. Preserve sound existing components and choose incremental changes with observable results. A rewrite needs evidence that the current implementation cannot meet a requirement and a bounded alternative, not preference.

Data belongs to the user. Use separate fork application identifiers and data roots; preserve upstream sessions and credentials. Any migration needs a versioned format, a backup, a rollback/export path and tests on disposable copies before it touches real data.

Autonomy means making and verifying bounded engineering decisions. It does not mean ignoring permissions, manufacturing progress, spending all available model quota, or shipping unreviewed changes.

## Definition of product success

- An installed app passes real blocked-egress local workflows with preserved design and usable error states.
- Durable state survives restart and cancellation; duplicate launch attempts do not produce duplicate executions.
- At least one complete Overseer-inspired workflow improves a real gap in the fork.
- The two developer workers demonstrate bounded overnight progress, independent review and a concise morning record.
- Optional provider and owned-machine connections are explicit, inspectable and dispensable for the local core.
- A release candidate has honest platform/build evidence, retained attribution, recoverable data handling and no hidden vendor runtime requirement.

Measure accepted user journeys, reproducible defects fixed and regressions avoided. Commit counts, lines changed, documents written and agents kept busy are not success metrics.
