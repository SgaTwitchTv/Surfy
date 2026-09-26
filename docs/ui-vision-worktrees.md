# UI / vision development checkouts

The existing M8 implementation is the common baseline. The primary checkout
stays on `main`; isolated feature worktrees live under the ignored `.worktrees/`
directory. All branches initially point at the same baseline commit.

| Branch | Local directory | Scope |
| --- | --- | --- |
| `codex/ui-desktop` | `.worktrees/ui-desktop` | Desktop navigation and laboratory UI |
| `codex/ui-mobile` | `.worktrees/ui-mobile` | Phone navigation UI; native GPS remains intact |
| `codex/vision-camera` | `.worktrees/vision-camera` | Camera/video capture, inference and tracking |
| `codex/vision-association` | `.worktrees/vision-association` | Assigning visual tracks to directional stop lines |

Before implementing independent features, define and commit the shared data
contracts from `ui-vision-implementation-plan.md`, then update each feature
branch to include that commit. Do not independently invent incompatible API
or event formats in each checkout. Integration will use small reviewed changes.

Worktrees contain tracked source/configuration, not private recordings or the
local observation database. Those remain in the original checkout's ignored
`data/runs` and `data/derived` directories. Use mock data for initial UI work.
Do not copy private recordings into tracked fixture directories.

To run a checkout, change into its directory before invoking
`python -m greenwave --no-browser --port 8766`. Assign a different port to each
simultaneously running server. No extra servers are started by worktree setup.

These branches are local until explicitly pushed; creating them does not
change GitHub or install a camera/model dependency.
