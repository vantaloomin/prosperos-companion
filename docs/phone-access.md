# Phone access

The Companion can be used from a phone, at home or away, through [Tailscale](https://tailscale.com). The
server keeps listening only on this PC (`127.0.0.1:8775`). `tailscale serve` gives it a private https address
on your tailnet, such as `https://home-vanta.tail1234.ts.net`, that only devices signed in to your Tailscale
account can open. Nothing is opened to the internet or your router. The PC has to be on and awake for a phone
to reach it.

## Setting it up

1. Install Tailscale on the PC and on the phone, and sign in to both with the same account.
2. In the Companion on the PC, open Settings > Phone access and choose **Turn on phone access**. This runs
   `tailscale serve --bg http://127.0.0.1:<port>`. The first time, Tailscale may ask you to allow https
   certificates for your tailnet; the Companion shows the link it gives.
3. Choose **Pair a phone** and scan the QR code with the phone's camera, or open the link and type the code.
   A code works once, for ten minutes.
4. On the phone, use the browser's Add to Home Screen to install it like an app.

Turning phone access off runs `tailscale serve --https=443 off` and refuses phones until it is turned on again.
Paired phones are listed in Settings > Phone access, where each can be removed; a phone can also sign itself out.

## What a phone may do

A request is from a phone when it arrives through the Tailscale proxy (forwarded headers, or a host name other
than this PC). It needs phone access to be on, a `*.ts.net` host name, and the cookie of a paired device. Only a
hash of each device's token is stored.

A paired phone can chat and use Today, the Feed, Memories, Character and most of Settings. These stay on the PC,
because they run programs or read files there, restore data, or could send a saved API key to a new address:

- Phone access itself (turning it on or off, pairing, removing phones)
- Backups and restores, and importing from Prospero's Study
- Changing model connections and profiles, real-world lookup services, image backends, and LoRA training
  settings, runs and adapter imports (these can still be viewed)

Restoring a backup turns phone access off and unpairs every phone.

## On the phone

The interface has a bottom tab bar on narrow screens, leaves room for a notch and home bar, keeps the keyboard
from covering the message box, and keeps each message's actions behind a ⋯ button on touch screens. While the
app is open, notifications are shown through its service worker (`public/sw.js`), which caches nothing.
