# Phase 6L-A1D authentic-start continuation

This continuation replaces the synthetic room-49 entry with a profile-owned
title action.  The `scumm` input profile's `menu` command, when the current
room is the declared title room (75), requests the ordinary room lifecycle
transition to room 49.  No script slot, PC, variable, or sentence is injected.

## Host trace

With the Fate source archive and cooked records for rooms 49, 68, and 75:

* canonical boot starts global script 1 at PC `$0000` in room 0;
* the authentic global/title scripts naturally enter room 68 and then room 75;
* a single `START`/`menu` input at the room-75 checkpoint requests room 49;
* old room-local scripts are retired and room 49 is installed through
  `_load_room` with its generated ENCD/LSCR directory;
* the active room-49 ENCD and local scripts run on the following scheduler
  pass.  Var[164] remains source-owned (no producer-chain injection).

The probe is `tools/validate_scumm_authentic_start.py`; it records the room and
active-slot checkpoints and fails if room 49 is not reached.

## Boundary

The current host profile has no generic pointer/verb sentence-construction
subsystem.  Consequently the accepted semantic Walk-To sentence for object
596 cannot be issued from the authentic room-49 UI yet.  This is the next
genuine dependency; no synthetic sentence, LSCR allocation, sound-82 state, or
room-63 transition is performed here.
