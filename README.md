# Compass

A personal planner for students that keeps the whole week on one screen. Describe plans in plain words and Compass turns them into events, reminders and tasks on a rolling calendar. It picks the task to do next and answers questions about what's coming up in a built-in chat.

Live version: https://claude.ai/artifact/3kJPZ92F6p98idB4RvRomJ

## Features

**Calendar tab**
- **Describe what's coming up**: type something like "Calculus midterm Oct 17 at 9am / remind me to call Mom Sunday at 8pm" and Compass turns it into calendar items. Separate several with `/`. Ctrl/⌘ + Enter runs it.
- Rolling calendar (this week first) or month view. Drag items between days, and change a repeating event for one day or for the whole series.
- The selected day's list sits under the calendar.
- **Your next move**: the task to do next, ranked by due date, category and how much a miss would cost. Mark it done, add a note, or flip through the rest of the list.
- Reminder card, daily and weekly background goals to tick off, and a rotating quote.

**Chat tab**
- Ask questions like "What's due this week?" or "Am I free Friday afternoon?".
- Answers come only from your planner and from notes you add under **My notes**.
- When Claude isn't available, it falls back to basic look-ups: today, tomorrow, a weekday, this week, or a keyword search.

**Settings (gear button)**
- Completed tasks (with undo) and All items.
- Goals, quotes and the availability page link.
- Google Calendar sync, which keeps a separate calendar for each item type.
- Apple Calendar (.ics) export, calendar size, and data reset.

Works on both phone and desktop, in light and dark mode.

## How it's built

- One self-contained file, `index.html`, with plain HTML, CSS and JavaScript.
- No build step, frameworks or external dependencies.
- Font: Helvetica Neue, falling back to system fonts.

The page is made to run as a **Claude artifact**, where it uses the artifact runtime (`window.claude.use(...)`) for:

| Capability | Used for |
|---|---|
| `db` + `user` | Saving each person's planner privately (`data/users/<id>/planner`) |
| `sample` | Claude-powered Describe and Chat |
| `mcp` (Google Calendar) | Google Calendar sync |

## Running it outside Claude

Open `index.html` in a browser, or serve the folder with any static host (e.g. GitHub Pages). Without the Claude runtime the app still works, with these differences:

- It starts with sample data and saves to the browser's `localStorage` (this browser only).
- Describe uses the built-in basic parser instead of Claude.
- Chat gives basic look-ups instead of Claude answers.
- Google Calendar sync is unavailable.

## Project layout

```
index.html   the whole app: markup, styles and script
README.md    this file
```
