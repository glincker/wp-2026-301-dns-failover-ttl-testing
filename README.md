# GLINR-WP-2026-301: experiments and claims

The evidence behind "DNS in Production", a whitepaper on DNS TTLs, failover and failure modes by Gagan Deep Singh (GLINR Studios). The paper is GLINR-WP-2026-301, version 0.1.0 (draft). Release tag: v0.1.0. This repository holds the harness that was run, its results and the claims the paper rests on, so that you can check them.

## Contents

- `experiments/`: the harness (`run-all.sh`, one script per experiment, a scriptable authoritative server, the client programs), `results.json` and `results.md` (tool versions, a table per experiment, tolerances and the cases that fell outside them).
- `claims/claims.md`: every factual statement in the paper that rests on an outside source or on the experiments, with the wording used, the source and an access date.
- `claims/excluded.md`: candidate claims that were left out of the paper, with the reason.

## What was measured

Two caching resolvers, Unbound 1.22.0 and BIND 9.20.30, and four client runtimes (Python, Go, curl and Java), in a Docker lab behind a scriptable authoritative server. Eight experiments cover TTL floors and caps, negative caching, serve-stale, cutover time against TTL, the stale window when a TTL is lowered, client caches, a dead first address and delegation NS TTLs. The authoritative server is a lab server, not a production one, so every figure is indicative and a lower bound for a real cutover.

## Rerun the experiments

You need Docker and python3. Images are pulled once by digest.

    EXP_SCRATCH=/path/to/empty/dir ./experiments/run-all.sh

It runs the eight experiments one at a time, then rewrites `results.json` and `results.md`. The lab uses one internal Docker network with no route out and no published ports. The script refuses to run if the scratch directory is not empty, and the whole suite takes about 40 minutes.

Every pass or fail outcome should match the published one. Timings will not match exactly: the harness polls every 0.1 to 1 s depending on the experiment, tolerates minus 1.2 s to plus 1.5 s, and two runs differed by at most 0.86 s.

The published runs used Docker 29.8.2 on one arm64 laptop, with the linux/amd64 images running under emulation.

## Corrections

If a number does not reproduce or a source no longer says what is quoted, open an issue here or write to support@glinr.com. Corrections that change a claim are recorded in the paper's changelog.

## License

Code is MIT licensed, see `LICENSE`. Text and data (the claims files and the results) are CC BY 4.0, see `LICENSE-docs.md`.
