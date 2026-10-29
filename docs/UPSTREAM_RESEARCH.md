# Research baseline and sources

Inspected on 2026-10-29. This is read-only source/documentation research, not a build, runtime test, visual assessment or security certification. The owner's fork may precede or differ from these revisions. Bootstrap must inspect and pin the actual fork independently.

## Zeron

Inspected revision: a0468502a81a568c985faeec7df0e32a2fea6487.

Current upstream describes and implements a native Rust/GPUI local-first core, a headless engine and optional multi-device synchronization. Local documents and SQLite persistence are already present; the sync-related crates are not wholly disposable. Preserve sound existing structure instead of assuming an Electron/web rewrite or an empty local-data layer.

- [README](https://github.com/zeronsh/zeron/blob/a0468502a81a568c985faeec7df0e32a2fea6487/README.md)
- [Architecture](https://github.com/zeronsh/zeron/blob/a0468502a81a568c985faeec7df0e32a2fea6487/ARCHITECTURE.md)
- [Cargo workspace](https://github.com/zeronsh/zeron/blob/a0468502a81a568c985faeec7df0e32a2fea6487/Cargo.toml)
- [Engine assembly](https://github.com/zeronsh/zeron/blob/a0468502a81a568c985faeec7df0e32a2fea6487/crates/engine/src/lib.rs)

The app embeds vendor edge/WorkOS defaults. The edge bindings include Cloudflare rooms/R2, cloud sandbox/billing and push-related services. These are concrete inventory targets, not proof that all run in local mode. Preserve local IPC authentication while removing vendor account dependence.

- [App defaults](https://github.com/zeronsh/zeron/blob/a0468502a81a568c985faeec7df0e32a2fea6487/apps/zeron/src/lib.rs)
- [Edge bindings](https://github.com/zeronsh/zeron/blob/a0468502a81a568c985faeec7df0e32a2fea6487/edge/src/env.ts)
- [IPC security](https://github.com/zeronsh/zeron/blob/a0468502a81a568c985faeec7df0e32a2fea6487/crates/rpc/src/ipc_auth.rs)

An important gap is explicit in source: local-mode tests expect public release checks, the desktop updater runs at startup, and disabling automatic installation does not disable checking. Agent/harness updates have additional external endpoints. A strict no-egress requirement therefore needs actual behavioral tests, not just “logout” or an auto-update setting.

- [Local-first tests](https://github.com/zeronsh/zeron/blob/a0468502a81a568c985faeec7df0e32a2fea6487/crates/engine/tests/local_first.rs)
- [Desktop updater](https://github.com/zeronsh/zeron/blob/a0468502a81a568c985faeec7df0e32a2fea6487/crates/ui/src/app_update.rs)
- [Update feed](https://github.com/zeronsh/zeron/blob/a0468502a81a568c985faeec7df0e32a2fea6487/crates/update/src/lib.rs)
- [Harness updates](https://github.com/zeronsh/zeron/blob/a0468502a81a568c985faeec7df0e32a2fea6487/crates/engine/src/harness_updates.rs)

The root license is MIT with a 2026 Wing copyright notice. Preserve it and applicable dependency/asset notices. Branding and data identifiers should be handled separately from attribution. [LICENSE](https://github.com/zeronsh/zeron/blob/a0468502a81a568c985faeec7df0e32a2fea6487/LICENSE), [third-party notices](https://github.com/zeronsh/zeron/blob/a0468502a81a568c985faeec7df0e32a2fea6487/THIRD_PARTY_NOTICES.md).

## Overseer

Inspected revision: fbd1e44ad0363873aa3e8a161528e6ef4bf260d3.

Overseer is a self-hosted Go hub/device application with embedded React UI and SQLite, not exclusively a vendor-operated SaaS. Its useful ideas include session visibility, capability-aware adapters, worktree isolation, attention-focused views, durable scheduling and real usage readings. These should be adapted selectively to Zeron's native architecture.

- [README and features](https://github.com/ErzenXz/overseer/blob/fbd1e44ad0363873aa3e8a161528e6ef4bf260d3/README.md)
- [Guide](https://github.com/ErzenXz/overseer/blob/fbd1e44ad0363873aa3e8a161528e6ef4bf260d3/docs/guide.md)
- [Scheduling and atomic claims](https://github.com/ErzenXz/overseer/blob/fbd1e44ad0363873aa3e8a161528e6ef4bf260d3/internal/hub/schedule.go)
- [Usage collection](https://github.com/ErzenXz/overseer/blob/fbd1e44ad0363873aa3e8a161528e6ef4bf260d3/internal/agent/usage.go)
- [ACP capabilities](https://github.com/ErzenXz/overseer/blob/fbd1e44ad0363873aa3e8a161528e6ef4bf260d3/internal/agent/adapter_acp.go)

Do not copy its budget semantics unchanged: guardrails default off, tolerate absent/error readings and focus on weekly windows; manual starting can bypass scheduled guards. The development runner and strict product mode need independent limits. Its development UI uses mock data, so attractive demo screenshots cannot prove backend integration.

- [Guardrails](https://github.com/ErzenXz/overseer/blob/fbd1e44ad0363873aa3e8a161528e6ef4bf260d3/internal/hub/guardrails.go)
- [Development mock mode](https://github.com/ErzenXz/overseer/blob/fbd1e44ad0363873aa3e8a161528e6ef4bf260d3/ui/src/mock.ts)

MIT license, copyright 2026 Erzen Krasniqi, is present. Retain notices for copied/substantially adapted source and record origin path plus revision. Check separate asset/dependency licenses. [LICENSE](https://github.com/ErzenXz/overseer/blob/fbd1e44ad0363873aa3e8a161528e6ef4bf260d3/LICENSE).

## Runtime and model references

- [Hermes scheduling](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron): operator-configured jobs, models, time zones and workspaces; verify the installed version before applying settings.
- [Hermes fallback routing](https://hermes-agent.nousresearch.com/docs/user-guide/features/fallback-providers): inspect primary and auxiliary routes as part of budget control.
- [OpenAI model guidance](https://learn.chatgpt.com/docs/models?surface=web): availability and selection guidance; runtime access must still be verified.
- [GPT-6.1 Terra model documentation](https://developers.openai.com/api/docs/models/gpt-6.1-terra): API model identity/specification, not a guarantee of the owner's Hermes route or included allowance.
- [OpenAI subscription pricing guidance](https://learn.chatgpt.com/docs/pricing?codex-pricing-plans=individual): subscription allowance and API pricing are different measures.

The numerical limits, milestones, acceptance matrix and work protocol in this kit are original project proposals. They are not represented as upstream defaults or guaranteed provider behavior.
