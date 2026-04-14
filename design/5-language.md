# Product language

Guidelines for **on-product copy** in RunningCalendar: tone, intent, and patterns so text feels consistent with the design system and helps runners decide what to do next.

This document complements **`design/1-principles.md`** (UX principles) and **`design/2-tokens.md`** (visual tokens). Use **semantic text roles** from typography docs: primary text for main content, **`color.text.secondary`** (supporting) for hints, metadata, and empty states.

---

## Tone

- **Motivational but practical** — encourage the next step without hype.
- **Clear, not salesy** — prefer facts and constraints users can act on.
- **Grounded in data** — dates, distances, and locations beat vague urgency.

---

## Principles

### 1. Motivational → but grounded in data

Encourage action, but tie it to **real, useful information** (deadlines, distances, places).

### 2. Personalized → not generic

Copy should reflect **what the user is doing** (e.g. filtering, comparing races) and support **different experience levels** without assuming jargon. Avoid one-size-fits-all slogans when a specific cue works better.

### 3. Decision-oriented

Ask implicitly: **“Should I run this race?”** Help users **evaluate options** (timing, course, logistics), not just notice marketing.

---

## Do / don’t

| Do | Don’t |
| --- | --- |
| “Registration closes in 3 days” | “Hurry!!! Limited spots!!!” |
| “No races match your current filters. Review location, distance, and dates—small changes often surface more to compare.” | “Oops! Nothing here! Try again!” |
| Tie the next step to **filters or data** the UI already shows | Empty platitudes (“Keep searching!”) with no hint what to change |

---

## Empty and edge states

When **filters hide every race**, the UI should:

- Use **supporting** text color (`color.text.secondary`) and appropriate body/meta size per **`design/4-typography.md`**.
- **Not** appear when at least one race is visible.
- Explain **that filters are the constraint**, and suggest **reviewing** location, distance, or date—aligned with the decision-oriented goal.

---

## Guardrails

- Write from the **runner’s** perspective (planning, comparing, registering).
- Avoid fear-of-missing-out phrasing unless a **specific fact** backs it (e.g. a documented closing date).
- Prefer **calm** punctuation; avoid multiple exclamation marks and all-caps emphasis.
