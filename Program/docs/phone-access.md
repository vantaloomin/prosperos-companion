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
from covering the message box, and keeps each message's actions behind a ⋯ button on touch screens.

## Notifications on a phone

In Settings > Notifications on a paired phone, **Notify this phone** subscribes it to Web Push (RFC 8030). The PC
encrypts each notification for that phone (RFC 8291) and sends it to the phone's push service (Apple's or
Google's), signed with a key kept in the OS credential vault (VAPID, RFC 8292). The push service carries it but
cannot read it. On an iPhone this needs iOS 16.4 or later and the Companion opened from the home screen.

What a notification says and when it comes are decided as on the PC: quiet hours, the daily cap, the gap
between notifications and the preview setting all apply. Every notification the PC shows also goes to subscribed
phones. When no window is asking, the Companion checks once a minute and sends to phones itself, but holds off
while the Companion is open and focused on the PC. The PC has to be on. Removing a phone, or a push service
saying a subscription is gone, stops its notifications. The service worker (`public/sw.js`) caches nothing.
