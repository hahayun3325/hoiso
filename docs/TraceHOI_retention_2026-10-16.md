# TraceHOI retention and cleanup — 2026-10-16

Never use a wildcard such as `rm -rf ~/tracehoi-*` or empty Trash for this task.

## Keep in place

- `/home/fredcui/Projects/FollowMyHold`, including `.git`, `src`, `config`, `tests`, `tools` and `docs`.
- The development-on-hold, progress-and-resumption, case-geometry-handoff and local-checkpoint progress notes in `docs`.
- `TraceHOI_WACV2027_reviews_and_next_steps_2026-10-15.md` in its original location. Its private review details are not included in the public progress note.
- All original `/home/fredcui/*.terminal.txt` run logs. They contain evidence and act as run-once guards. Removing one does not make rerunning a used command valid.
- Current Q9 folder `tracehoi-hunyuan-cpu-tool-recovery-probe-20261016-v1-Q9n6Ew3N`, its original ZIP and terminal; current publication/cleanup input and output folders.
- `tracehoi-evidence-archive`, model checkpoints and Hugging Face cache, source repositories, datasets, input images, final experiment artifacts, and Conda environments.
- All other historical attempt folders unless an explicit verified retirement plan names them.

## Two folders retired by this command

The only whole-folder moves are:

1. `/home/fredcui/tracehoi-hunyuan-cpu-load-probe-20261014-v1-N7l4Cu9L`
2. `/home/fredcui/tracehoi-hunyuan-cpu-budget-probe-20261014-v1-P8m5Dv2M`

Both recorded failures occurred before service submission; Q9 supersedes their CPU-load work.
After the new commit is verified on GitHub, each original ZIP and terminal is copied into
`/home/fredcui/tracehoi-evidence-archive/<attempt>/` and checked byte-for-byte.
Every remaining file must match that attempt's verified ZIP. Only the known empty
cache/config/tmp directories are allowed. Unknown files, changed data, symlinks,
missing ZIPs or missing original terminals cause preservation, not deletion.
The whole folder then moves to `/home/fredcui/.local/share/Trash/files/` with
matching `.trashinfo` and an exact `restore_to` path in the returned receipt.
Home-level terminals remain in place. This explicit archive migration supersedes
the older keep-in-place instruction for these two folders only.

Use the receipt to restore the exact Trash folder to `restore_to` only when that
destination is absent. Do not reconstruct or overwrite a terminal from pasted text.
Downloads copies are transfer copies; delete them only after matching retained
originals or archive copies have been verified. The new publication ZIP and terminal
should be returned before any further cleanup. This command does not empty Trash.

The previous failure was a missing original checkpoint terminal, not proof that a
progress note was unnecessary. Keep `tracehoi_checkpoint_20261015.terminal.txt`.
