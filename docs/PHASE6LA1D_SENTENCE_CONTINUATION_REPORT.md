# Authentic sentence continuation

From the profile-owned boot/title path, the semantic sentence was submitted
through `ScummV5Engine.queue_sentence(10, 596, 0)`, the same production
sentence queue consumed by `_check_and_run_sentence_script`. No script slot or
program counter was selected by the validator.

Observed chain:

```
boot script 1 → room 68 → room 75 → START/menu → room 49
→ semantic sentence (10, 596, 0) → sentence script 2
→ object 596 verb 10 → LSCR 211
```

The accepted dense globals remain intact (`Var[164] = 204`, and
`Var[119/120/121] = 0/$FFFF/0`). Audio state remains the previously accepted
sound-80/sound-81 state.

The first unsupported operation is now the authentic LSCR 211
`loadRoomWithEgo` opcode at offset `$02DE` (`$24`). LSCR 208 was not requested
by this sentence path, and no sound-82 state was fabricated. Implementing that
room transition is explicitly outside this continuation.
