# Memory Migration (run once, right after setup)

Purpose: pull whatever context an AI tool has already accumulated about you
out of its own siloed memory and into Open Brain, so every other tool you
connect afterward starts from that foundation instead of zero.

Run this separately in each tool that currently has memory about you (Claude,
ChatGPT, etc.).

---

**Prompt:**

> Go through everything you remember about me — my role, my active projects,
> my constraints, the key people in my work and life, decisions I've told you
> about, and recurring topics I bring up. For each distinct fact or decision,
> write one capture-ready sentence (5 sentences or fewer) that stands on its
> own without needing this conversation as context. Group them by type:
> decisions, person notes, insights, and open action items. Output them as a
> plain numbered list — nothing else.

Then capture each item it gives you:

```
./cli/brain-capture "the sentence it gave you"
```

(If you're doing this inside Claude Code, you can just ask it to run
`./cli/brain-capture` for each line itself instead of copy-pasting manually.)
