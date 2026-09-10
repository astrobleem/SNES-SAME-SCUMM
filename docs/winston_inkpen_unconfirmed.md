# WINSTON INKPEN: UNCONFIRMED

Documented by Luna  
Date: 2026-09-09

## Core concept

Winston Inkpen is a conspiracy podcaster investigating AI, render-boundary
glitches, suspicious infrastructure, data centers, strange power and water
usage, surveillance, and increasingly absurd clues.

Recurring cast:

- Winston Inkpen — protagonist and conspiracy podcaster
- April Irene — recurring antagonist
- Benji — supporting character
- Winston's mom — supporting character

## Fixture philosophy

These scenes are a copyright-free SCUMM/SAME conformance corpus first. They do
not need to form a complete adventure game, or obey a three-act structure,
continuous geography, or strict chronology. Each fixture primarily exercises a
particular engine feature.

Instead of incoherent test data such as “TEST ROOM / OBJECT 3 / USE ITEM A,”
each fixture should provide a plausible little room, meaningful object names,
sensible verbs, short dialogue, appropriate actors, inventory items, and tiny
puzzles or interactions. Engine-test usefulness comes first; narrative
continuity is secondary. Small scenes may connect when convenient, but they do
not have to.

## Possible feature mappings

- Verb/object/HUD: Winston investigates a suspicious equipment cabinet.
- Walkboxes/pathfinding: fencing, gates, utility equipment, or a data-center
  exterior.
- Dialogue/talk: Winston interviews an evasive employee or argues with April.
- Inventory: an RFID badge, microphone cable, ridiculous EMF meter, printed NDA,
  or suspicious USB device.
- Object state/classes: breakers, generator controls, access panels, security
  cameras, and locked doors.
- Cutscenes: April appears, alters something, and leaves before Winston reaches
  her.
- Save/restore: Winston records or preserves an “evidence checkpoint.”
- Camera/large-room behavior: a data-center campus, server hall, or utility
  facility.
- Audio: a podcast intro, machinery, electrical hum, and suspicious modem or
  data noises.
- Renderer/conformance edge cases: visual corruption and render-boundary
  glitches become phenomena Winston believes are conspiracy evidence.

Winston's mom is useful for mundane, comedic scenes in which she is
substantially less impressed by his evidence than Winston is.

## Architectural role

```text
Fate of Atlantis = real-game compatibility oracle

WINSTON INKPEN: UNCONFIRMED
    = copyright-free, redistributable SCUMM/SAME conformance corpus
```

Over time, the fixtures may accidentally form a small playable adventure; that
would be welcome. “Finish the Winston game” must never become a prerequisite
for engine work.

## Provenance rule

Winston assets, scripts, dialogue, room designs, object names, and other
fixture material must be original and copyright-free. Fate may teach us engine
behavior, but Winston supplies redistributable test content. Renaming or
transforming Fate material does not make it original.

## Current scope

This document records the future direction only. Do not convert existing Fate
fixtures or write Winston rooms during the current Fate/Open-verb milestone.
Preserve the Fate compatibility work and its checkpoint first.
