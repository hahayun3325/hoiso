# Phase 0.16b — Dataset Readiness

## OakInk

OakInk image archive has been extracted successfully.

The flexible split resolver found the first 10 OakInk split images.

Status:

OakInk image split readiness: PASS

Next action:

- use OakInk for a small official-split smoke panel,
- inspect GT annotation/object mesh files for metric reconstruction.

## ARCTIC

ARCTIC cropped image download is currently running through the official repository script.

The script requires:

ARCTIC_USERNAMEARCTIC_PASSWORD

These credentials should be stored only in a private ignored file such as `~/.foho_secrets`.

Next action:

- wait for download to finish,
- extract cropped image zips,
- create symlink if needed,
- re-run flexible split resolver.

## DexYCB

DexYCB toolkit exists, but the actual DexYCB image data was not found.

Status:

DexYCB image split readiness: FAIL

Next action:

- do not test DexYCB yet,
- download/link DexYCB after OakInk and ARCTIC are stable.

## Readiness rule

A dataset is ready only when the split image paths resolve to real files.  
