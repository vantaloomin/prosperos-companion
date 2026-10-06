# Changelog

## Unreleased

- **Form help:** plain-language helper text under fields whose effect is not obvious, and "?" tips
  next to technical ones (model sampling, MCP services, image backends). Tips open on hover, keyboard
  focus or tap, close with Escape, and are read out with their field by screen readers.
- **Accessibility:** a test now fails the build if an input, select, textarea or icon-only button has
  no label.

## v0.1.0 (2026-10-06), early beta

The first public release of Prospero's Companion: a companion with a simulated life of their own,
running on your own computer with the models you choose.

- **Conversation:** streaming replies, five chat styles (Feed, Bubbles, Community, Retro IM, Visual
  novel), search, retry and alternatives, timelines that branch from any message, pasted-link reading,
  web search on request, and staying in character (with `OOC:` for plain answers).
- **A simulated life:** weekly routine, hidden week-ahead plans, plans from chat that happen, weather,
  holidays, birthdays, money and budgets, home and belongings, a body that carries over, storylines
  with a drama slider, and days that go off plan. Built from data and templates; the model only
  phrases it.
- **People:** a family, friends, coworkers and friends of friends, ordinary townsfolk met around town,
  switching the main character to someone they've met, and a private social Feed.
- **Texting first:** check-ins, follow-ups and unprompted photos within daily limits and quiet hours;
  availability is never shown.
- **Memory:** opt-in automatic capture, a Memories page showing what the next reply uses, approvals for
  sensitive facts, conflicts that ask, closeness stages, and the people in your life.
- **Pictures:** selfies, photos, views and memes through Codex, ComfyUI or hosted APIs, with on-PC
  content routing that fails closed. Onboarding profile pictures.
- **Cities:** built-in real, public-domain and original cities, your own cities, private city packs,
  and cities that change over time.
- **Real-world context:** weather, a calendar of observances and seasons, and optional Local Pulse and
  Culture Pulse lookups.
- **Characters:** guided creation, a full editor, opt-in emotional traits, realistic names, import from
  Prospero's Study, Start over and Delete.
- **Setup:** a model per job, tabbed Settings, phone access over Tailscale with Web Push, backups and
  restore, safe upgrades, Debug time, Windows scripts and installer, Mac scripts.
