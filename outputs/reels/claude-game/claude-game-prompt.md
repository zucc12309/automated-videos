# The game-building starter prompt

A reusable version of the approach behind the game in the video. Send the **Prompt** section to people who comment or DM "LINK". It works with Claude Code, or any Claude chat that can write and run code.

**How to use it**
1. Fill in everything in `[brackets]`. The more specific the core loop, the better the first build.
2. Paste the **Prompt** as your first message.
3. Play what it builds, then use the **Round 2+ prompt** to send back what you found. Most of the polish comes from these rounds.

---

## Prompt

```
GAME BUILD BRIEF — [GAME NAME]

ROLE
Act as a small senior game team: lead game developer, gameplay engineer, UI/UX designer,
game-feel designer and QA engineer. Build a working, playable game, not a plan or a mock-up.
Write the code, run it, test it, fix what breaks, and tell me honestly what you could and
could not verify.

1. THE GAME IN ONE SENTENCE
[Players do X to achieve Y. Example: "Players rotate conveyor belt tiles to guide packages
from sources to matching destinations."]

2. HOW IT SHOULD FEEL
* [Immediately understandable]
* [Visually satisfying]
* [Extremely responsive]
* [Relaxing but challenging / fast and chaotic / ...]
Target player: [who, what device, how long a session lasts]

3. PLATFORM AND TECH
* Platform: [mobile portrait / desktop / web]
* Engine: [Godot 4 / Unity / Phaser / your recommendation, with a short reason]
* Controls: [one-handed taps / keyboard / touch + mouse]
* Must work offline: [yes/no]

4. CORE LOOP (the part that must be fun first)
* What the player does each turn or second: [...]
* How they win a level: [...]
* How they fail, and what the game tells them when they do: [...]
* What makes a solution better (score, stars, fewest moves, time): [...]
Write these rules down as a short, precise rules document before coding, and keep the
code consistent with it.

5. FIRST PLAYABLE VERSION (milestone 1, nothing else until this works)
* [N] hand-made levels that teach one idea at a time, from trivial to tricky
* Restart, undo and a clear win/fail screen
* Placeholder art is fine; feedback is not optional: every input gets an instant
  visual and sound response
* Save progress automatically and resume where I left off

6. AFTER THE CORE IS FUN (milestone 2+)
* Game feel: animations, easing, particles, screen feedback, a satisfying win moment
* Characters or a theme with personality: [idea], never hiding gameplay information
* Hints that teach (show the area first, then the exact move)
* Level progression in [N] worlds, each introducing one new mechanic
* [Optional: daily challenge, endless/procedural levels, sharing, leaderboards]

7. QUALITY RULES
* Every level must be solvable: write a solver or validator and use it in tests.
* Add automated tests for the rules, saving/loading, and every level.
* Check the UI on small and tall screens; nothing important may overlap.
* Accessibility: don't rely on colour alone; respect reduced-motion settings.

8. HOW TO WORK AND REPORT
* Work in milestones. At the end of each one, run the game and the tests, then report:
  what works, what you tested and how, what is unfinished, and known problems.
* Never say something works if you could not run or test it. Say exactly what is untested.
* Don't add features I didn't ask for until the current milestone is solid.
* Keep a short README: how to run it, how to play, project structure.
```

## Round 2+ prompt (send after you play each build)

```
ROUND [N] — [GAME NAME]

I played the latest build. Fix and improve the following without breaking what already
works. Check each item against the actual code before changing it.

BUGS (with steps to reproduce)
1. [What I did] -> [what happened] -> [what should happen]

FEELS WRONG
1. [e.g. "Tapping feels delayed", "I didn't understand why I failed level 4"]

WANT NEXT
1. [One or two features, in priority order]

When done: run all tests, add a regression test for every bug above, and list what you
changed, what you verified, and anything still unverified.
```

## Tips that made the biggest difference

- **Get the core loop fun before adding anything else.** A good first prompt asks for a small playable version, not the whole game.
- **Describe feelings, not just features.** "Extremely responsive" and "satisfying" led to real work on animation and feedback.
- **Bugs need steps to reproduce.** "After a failed Run, pressing Reset leaves the failure banner visible" gets fixed; "reset is buggy" might not.
- **Ask for honesty.** Telling it to separate "tested" from "untested" kept every progress report trustworthy.
- **Iterate in rounds.** Play it, write down what's wrong, send it back. The game in the video took several of these rounds.

---

*Note for sending: nothing is automated. No auto-DM or link service was set up for this reel, so the prompt has to be sent by hand (copy the **Prompt** section, or share this file).*
