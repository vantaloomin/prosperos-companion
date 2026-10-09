# Safety: AI notices and crisis help

[Back to the README](../../README.md)

Prospero's Companion is a chat app with AI characters who stay in character. This page says how the app makes clear
that they are AI and what it does when someone may be thinking about hurting themselves. It is published so anyone
can read the protocol the app follows. Everything here runs on your own computer, with rules rather than a model, and
nothing is sent anywhere.

## The characters are AI

- **On first start**, before anything else, the app shows a one-time notice that the characters are AI, that what
  they say is written by an AI model and can be wrong, and that the app is for adults. It can't be dismissed without
  ticking **I'm 18 or older**. Confirming is recorded once in your workspace.
- **Under every message box** a small line says *Characters are AI and can make mistakes.* It shows in one-on-one
  chats, group chats and Story mode, in every chat style and on a phone, the whole time you are chatting.
- **The notices come from the app, never from a character.** A character still never says it is an AI (see
  "They stay in character" in the README); a message starting with `OOC:` or wrapped in ((double parentheses)) always
  gets a plain, honest answer.

## Crisis help

- **What is checked.** Only your own messages, in one-on-one chats, group chats and Story mode. Each one is checked
  against a list of phrases about suicide and self-harm (`Program/companion/safety.py`). Characters' messages are not
  checked, and no model is asked.
- **What happens.** A message that matches gets a note from the app right under it, styled so it is clearly not the
  character. It names the 988 Suicide & Crisis Lifeline (call or text **988** in the US), the Crisis Text Line (text
  **HOME** to **741741**), [findahelpline.com](https://findahelpline.com) for other countries, and says to call the
  local emergency number in an emergency.
- **What doesn't happen.** The message is never blocked or changed, the character's reply carries on as usual, and
  nothing about it leaves your computer. There is no setting that turns the note off.
- **What the characters are told.** Every character's standing instructions (Settings > Advanced, "Who the companion
  is", and the Story narrator) include a rule never to encourage, praise or help with self-harm or suicide, never to
  describe ways to do it, and to answer with real care when someone says they want to hurt themselves. Those
  instructions can be reworded in Settings > Advanced; the crisis note is code and shows whatever they say.
- **Limits.** A list of phrases misses some ways of saying things and catches some jokes ("this exam makes me want to
  die"). It leans toward showing the note: a false alarm costs one note, a missed one costs much more.

## What the app does not do

The app has no accounts and sends nothing home, so it cannot count how often the note is shown or report it anywhere.
It is not a crisis service and does not replace one.
