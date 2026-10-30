# Changelog

## Unreleased

- **Comment on posts:** "Talk about this" under a post looked like it would let you comment, but it sent a chat
  message. Posts now have a Comment button: your comment goes under the post, and whoever posted answers you there,
  your companion on their own posts and a friend on theirs, once they would have seen it (sooner or later by
  Settings > Realism > "How quickly they read your texts", and after work or sleep). You can keep the thread going.
  "Message them instead" next to Comment still takes the post to chat.
- **Books, shows and songs from their own world:** a companion in a made-up world used to read, watch and hum the
  same generic made-up titles whether they lived in Camelot, Oz or a fan-made world of your own. Now the titles come
  from their world: a city can list its own books, shows and songs (`media` in the city file, see Making a city),
  and one without a list gets titles built from its own places, people, festivals, food and lore ("A History of the
  Emerald City", "Last Round at the Blue Cloth"), mixed with the shared ones. What they are on today changes over.
- **Post something of your own:** the top of the Posts page has a box to share something with everyone. All your
  companions see it, and so do their friends, so it is how you get to know friends of friends. They like and
  comment on it in their own time: the closer you are to a companion, the likelier they and their circle join
  in. The You filter shows only your posts.
- **Companions who know each other join in on the Feed:** other companions a companion knows (from how
  they know each other, a group chat, or running into each other in town) now like and comment on their posts,
  more often the closer they are. A reserved one, like a Vulcan, likes now and then and says little; a warm one
  joins in more.
- **Built-in voice on Windows 11:** the built-in voice could fail with "The requested API version is not available"
  when Windows loaded its own older copy of onnxruntime instead of the voice's. The voice now puts its own copy
  back beside its program before each note and runs from its own folder, and if it still happens, Settings >
  Models > Voice notes explains it and offers Repair the built-in voice, which downloads only the program again.
- **Take a companion to another world:** the Character page can save a companion to a file with everything that
  happened between you: chats, memories, Closeness, kids, home, look and voice. Open it under Bring your
  characters in another world and they arrive there with all of it, moving to that world's city if it is another
  one. Opening an updated city file for one of your own cities now updates it in place, so a world in it keeps
  its companions.
- **Memories stay in the right chat:** a memory found in one companion's chat could be saved to whichever
  companion was open when the app got round to it, for example after you switched chats or opened another one
  on your phone. Memories, things they say about themselves, and Remember this now always go to the companion
  whose chat it was, a reply keeps being written when you open another chat meanwhile, and a message sent from
  a window still showing a chat goes to that chat.
- **Edit a reply you stopped:** a reply you stopped (or one the model cut short) now has Edit. Finish it or keep
  it as it is, and the conversation goes on from it.
- **Add image APIs from your phone:** on a paired phone, Settings > Images can now add OpenRouter, Google, the
  OpenAI API or NanoGPT with a key typed on the phone, and turn backends on or off, reorder or remove them. A
  ComfyUI server, Codex, or an image API at an address of your own is still added on the PC, since those name
  addresses and programs on it, and the phone says so. Keys are only typed over Tailscale, never over the
  unencrypted home Wi-Fi option.

- **Phone access that tells you why it isn't loading:** Settings > Phone access now shows which phones are
  signed in to your Tailscale account and warns when there are none, or when Tailscale is switched off on
  them, the usual reason the pairing link opens and nothing loads. Under the QR code, "If nothing opens on
  the phone" walks through the fixes, including a backup address that works without Tailscale's name lookup.
- **Use on home Wi-Fi:** a new switch in Settings > Phone access lets a paired phone on the same network open
  the Companion without Tailscale. It is off by default and only meant for a network you trust, as the
  connection is not encrypted; notifications still need Tailscale.
- **Always know what the chat is doing:** a small line above the message box says when a reply is
  being got ready, waiting for the model or being written, or simply "Delivered" while your companion
  gets to it in their own time. A reply that times out or fails now shows straight away with Retry, even while your companion
  is busy, instead of staying hidden until they would have answered. While a reply waits for later you
  can keep writing.
- **Photos load like photos:** while a picture is being made, the chat holds its space with a blurry
  photo filling in, like one coming through on a slow connection, and the real picture fades in without
  moving anything, in chat and in Posts. A picture that fails or times out says why and has a Try again
  button.

- **Running from an external drive on a Mac:** macOS leaves a hidden `._` file beside every file copied
  to a drive formatted for Windows, and the app read those as cities. Matchlight, the city pickers and
  Today's local news then failed with "Something went wrong". Those files are skipped now.
- **Easier to report a problem:** when something goes wrong, the message gives the log file's full
  path, and on the PC an "Open the log folder" button shows it.
- **Posts opens again after Debug time:** keeping what happened in Debug time could leave the Posts tab
  (and Today) failing with "The request could not be completed". It opens now, a failed load says what
  went wrong with a Try again button, and the profile card has a Message button back to the chat.
- **Recall has its own profiles:** embedding models moved out of text model profiles into a Recall
  section of Settings > Models, beside Built-in recall. A recall profile is just a service and an
  embedding model, so recall can use a different service from the one that writes replies (for example
  Claude for chat and Ollama on this PC for embeddings). Existing embedding models move into recall
  profiles on their own, sharing the saved key, and recall keeps working as before.
- **Duplicate a model profile:** each profile in Settings > Models has a Duplicate button that copies
  its provider, model, settings and saved key into "… copy". Jobs stay with the original, and a new
  key on either one leaves the other's alone. Profile buttons also wrap on narrow windows now.

## v1.2.1 (2026-10-30)

- **People in your life:** each person has Tell more (a note or a topic like work, age or likes) and one card
  with what's known about them, plus Edit details, Rename and Forget.
- **Plans close on their own:** past plans, and undated ones not mentioned for two weeks, are taken as done and
  fold under Done and cancelled; Assumed done offers It happened, It didn't happen and It moved.
- **Work projects:** seasonal projects only when due; a job the city doesn't list is read from who they are.
- **Fixes:** no claimed photos that never come, and asking for one sends it; small talk about the world is no
  longer saved as memories, and older strays are cleared.

## v1.2.0 "The Dark Backward" (2026-10-29)

- **Back when:** go back with a companion to a year in the past, back to 1990, from a new section on the Character
  page. A new world opens in that year in the same town, everyone younger, as strangers by default or worked out
  from your history; what hadn't happened yet hasn't, and jobs fit the year. New worlds can start in a past year,
  and past-year worlds show their year.
- **The decade around them:** real cities in a past year take on the 1990s, 2000s or 2010s: how people keep in
  touch, the app's words, books, shows and songs, jobs, pastimes, memes and Matchlight, with nothing from later.
  Companions know the year and haven't heard of anything newer.
- **Posts and people:** comments on posts that whoever posted answers; one-sided ties (a fan, a singer); the
  Watching page says why each person is there and adds the companions' people in town; Try life as.
- **Voices:** no texting habits in person or on calls; a companion's own storyline news says whose it is; a
  declined call is remembered as theirs.
- **Pictures:** NovelAI; booru tags for Illustrious, NoobAI and Pony; graphics-card fit for Qwen Image, Z-Image
  and Anima; a saved model file stays pickable.
- **Fixes:** reply versions stay chosen and rerolls work while busy; Work life projects say where they come from
  and their due date can move; posts stay in the companion's own voice; same-sex parents in past years are
  partners until they could marry.

## v1.1.9 (2026-10-28)

- **Talk of the town:** every city has local issues and era questions that move from whispers to settled,
  factions that back sides and gain or lose pull, and everyone's view on them; all editable. Chat, the town paper
  and Today know about it, Settings > Realism has a Local politics slider, and an opt-in switch reads a real
  city's political headlines.
- **Pictures:** every OpenRouter image model; your own picture as a companion's reference picture, followed on
  every backend that takes one; New picture and Remove picture in chat; Krea 2 files that fit the graphics card
  (NVFP4, GGUF); card words win over drawn looks; a per-character name switch; clearer errors and a local
  fallback when a hosted image API fails.
- **Each world its own way:** a world can have its own drama level, image backends and text models.
- **Homes and the map:** homes sit where their words say, can be moved on the map, show for everyone in the city,
  and have editable insides and quirks.
- **Their people:** hand-added people start where their words say, family keeps out of chance friendships, links
  between circle people are editable, and circle closeness counts on your posts.
- **Fixes:** held replies show when they arrived; the app's own suggestion lists replace the browser's popups.

## v1.1.8 (2026-10-27)

- **Families that look like real families:** a new companion's family is planned at true-to-life rates for their
  era (divorce, remarriage, step and half family, adoption, two moms or two dads, only children, family long gone
  or out of touch); Today > People groups them, and Settings > Realism has a Family shapes slider.
- **One saved key for everything:** a key saved for a service is used by every profile on that service, and image
  services without a key borrow the one saved for the same service's text models.
- **Switch models fast, or mix them:** Add another model on a profile, a Model choice in the chat's More menu,
  Try with another model on a failed reply, and Mix models in chat (in turn or at random).
- **Tester fixes:** name styles fit who they are; Work lists a made-up city's own jobs; books, shows and songs
  come from their own world; a city's well-known people stand out around town; a notification no longer opens
  a blank message; other tabs follow a world switch; whole group names in the phone message box; strangers
  start at Just met; pastimes you add read as long-standing; no browser autofill in text boxes.
- **Found before testers did:** no second mom when you add one; jobs and money in written fantasy cities; ship
  and era-fitting pets, clothes and posts; tips and menus stay on a phone screen.

## v1.1.7 (2026-10-26)

- **People your companions both know:** someone in one companion's circle can be added to another companion's life
  too (Today > Add someone another companion knows); they stay one person, both chats know them, and the app-made
  mom, dad or spouse they replace steps aside until they're taken out.
- **Your own posts:** a box at the top of Posts shares a post of your own, seen on every companion's feed; companions
  and their circles like and comment by how close you are, and a You filter shows just yours.
- **Companions react to each other's posts:** companions who know each other like and comment on each other's posts
  by closeness and manner.

## v1.1.6 (2026-10-26)

- **They take a moment to read your texts:** a free companion waits a seeded little while before answering and
  answers texts in a row together; Settings > Realism > How quickly they read your texts, and a per-companion
  Quick to reply switch.
- **Check for updates:** a button in Settings > General that compares this copy with the latest release.
- **Pets in the circle:** edit, remove and add circle pets; fewer pets, and only cabin-sized ones aboard.
- **A resizable chat box:** a grip on its top edge, a fold-to-one-line button, and the newest message stays in view.
- **Fixes:** circle "Where they live" says aboard and off the ship on ships and stations; circle ages spread per
  relation, and people the city names take its age and role.

## v1.1.5 (2026-10-26)

- **What's on their mind this week:** an opt-in Settings > Life switch that has the model add a few lines on the open
  companion's mind once a week.
- **Matchlight answers every like:** a like that isn't returned says so, and a yes comes after three misses in a row.
- **Find your chats:** the desktop rail's Profile button is now Chats; the sidecar has a lightbulb icon.
- **Fixes:** a reply stuck on "…" after its connection dropped, and Getting started hidden behind Visual novel's stage.

## v1.1.0 (2026-10-26)

- **Prospero's Draft Table:** a window that draws up a whole place from one line, to change, check, polish and save
  with your cities, with nearby places and Marinara maps as a start.
- **People of other kinds:** elves, fae, dwarves and the peoples of Oz live in town by a share per kind, and pack
  characters can be another kind.
- **Their look in chat:** each companion's own name color and font, picked by the app, easy to read on every style.
- **On your clock:** wake a sleeping companion, hours fitted to your evenings, and Live on my clock.
- **Take a companion to another world** with their whole history, in a `.companion` file.
- **Who they know:** the Character page and one-on-one chats know the other companions someone knows.
- **Their circle and their work:** edit and add people in the circle, jobs and ages from the description, and students
  working in their own field.
- **Family, personas and cities:** add children by hand, copy a persona to a new world, and update a city from a newer file.
- **Fixes:** the built-in voice on some Windows 11 PCs, and a message box that refilled after editing a message.

## v1.0.1 (2026-10-25)

- **Choose what to import from a file:** a preview of a character, lorebook or world map file with every part ticked;
  untick to bring in only the lorebook, some entries, or the character without their lore or picture.
- **Create another companion:** a button on the Character page makes a new companion from scratch.
- **Remember something, back when it happened:** a memory added by hand can carry the day it happened.
- **Your own words on the adult side:** Also into and Not into in your own words, and What draws them in.
- **Fixes:** your own cities and packs in Where you live, an imported character lives in the world's city, a new
  companion's picks survive a trip to Settings, and a refused reasoning level falls back to the nearest one.

## v1.0.0 (2026-10-22)

- **Words that fit the era:** period cities use period words in the chat, Today, Watching, the circle, the matchmaker,
  the feed and notifications, with each city's own words and a switch in Settings > Appearance.
- **Their voice stays theirs:** companions hear a few lines they said before, picked from kept replies, and Pin their
  voice keeps up to three.
- **A reference library:** books, scripts, transcripts and wikis for a companion or the world, with up to three
  matching passages per reply, and Oak's Neokosmos wiki one click away in Grandport.
- **Lore that fits the moment:** lore entries for weather, seasons, times of day, holidays, places and work, rule-read
  from imported lorebooks, and in thirteen built-in cities.
- **Love life in the Watching feed:** steps, breaks, breakups and making up told on the day, with the line under a
  name following how things stand.
- **Fixes:** no phones in period cities, and a link to the Discord in Settings.

## v0.16.0 (2026-10-21)

- **Just watch:** a switch on any world and a Watch a city option, where your persona sits out and a Watching feed
  tells the day of whoever you follow, with a Focus picker, Step in and an Inner voice slider.
- **Ships and stations:** a city can be a ship or a station, with no weather or Earth seasons, ship lighting in
  pictures, more than 120 future-era jobs and travel by shuttle between made-up places.
- **The Long Meridian:** a built-in generation ship with its station Port Vesper, Start from a ship in Settings >
  Cities, and Featured in v0.16 with Baltimore, Grandport and Osaka.
- **Memes and GIFs:** memes without a picture model from a starter pack, classic formats and your own folder,
  reaction GIFs with your own GIPHY key, and a Memes and GIFs slider.
- **Visits with the other parent:** planned stays on the calendar and Today with Move and Skip this one, and stays in
  another city that work like trips.
- **Fixes:** mum in UK cities, jobs that fit the era and age, the 1895 polling station, baby things when adopting or
  fostering, and "you" in the Backstories box.

## v0.15.0 (2026-10-20)

- **Wanting children:** every companion wants children, wants them someday or doesn't, shown on a new Family panel, and
  a romance can reach Starting a family once you live together, asked and answered in chat.
- **Expecting or adopting together:** a pregnancy, a surrogate, adoption, fostering or an older city's ward, with
  appointments in Life admin, a nursery, a baby shower and a name the companion suggests.
- **Our child:** a child who grows up in real time with milestones, care that changes work and money, family days out,
  another child later, and a Family life slider.
- **Companions' own babies:** friends start families with their partners, with a naming day, a godparent and babysitting.
- **Companions who already have kids:** kids from descriptions or seeded, a co-parent with custody, and step-parenting
  after moving in.
- **When families change:** custody after a breakup, with whose week it is on Today and weekend visits across cities.
- **Lifespans:** kinds such as Elf, Dwarf and Doesn't age with their own lifespans and ages in human terms, including
  for your persona.
- **Fixes:** truer death rates and a grandparent for younger companions, era words and jobs in older cities, mother and
  father before about 1920, child costs that fit the city and era, and baby odds under Hidden values.

## v0.14.0 (2026-10-19)

- **Everyone gets older:** companions, their circle and townsfolk age from today one birthday at a time, with milestone
  birthday parties, looks that change slowly with age, and a Keeps their age switch.
- **Bigger life chapters:** back to school, career changes, buying a place, retirement, and on Real life and Drama a
  business, a health turn or caring for a parent, each running over months with a life lately panel.
- **Big days in the circle:** weddings, graduations, retirement parties and milestone birthdays as outings with gifts,
  outfits and you as the plus-one, and a friend who asks you to stand up at their wedding.
- **Growing families:** pregnancies and babies in the circle who grow up, with companions as aunts, uncles and
  godparents. Children appear only in words.
- **Loss and grief:** an opt-in People can pass away switch with a Loss slider, funerals by the city's customs,
  obituaries, anniversaries and grief that lifts over weeks. Never a companion, a partner or a child.
- **The town changes hands:** townsfolk move away, retire and are replaced by newcomers, and the paper reports it.
- **More Realism settings:** Life's big turns and Growing families sliders, People can pass away and Loss.
- **Fixes:** meeting their people and proposals on long-distance stays, impressions that cool after a breakup, a plain
  "sorry" as an apology, closer-to-real modern pay, and shared memories newest first.

## v0.13.0 (2026-10-17)

- **Next steps:** romances move from dating through exclusive, "I love you", meeting their people and a key to their
  place; friendships through best friends and a first trip. Either of you can ask, your answer in chat counts, and
  now and then a friend falls for you.
- **Meeting their people:** dinner with their family or drinks with their friends, with first impressions that change
  over time and people who remember you.
- **Moving in together:** the app picks whose place, sets a moving day, splits rent and chores, and asks everyone
  before a second partner moves in.
- **Rough patches and making up:** hurtful words, missed plans and broken promises on either side, colder contact while
  it lasts, and apologies, gestures, good plans or calm days to mend it.
- **Breaks and breakups:** on Real life and Drama, strain with warnings first, breaks that end in trying again or
  ending things, friendships that fall out, and exes who may reach out.
- **Their own love life:** friends date and split, romances see others only when open or in secret on Drama, and the
  town paper reports townsfolk engagements and weddings.
- **Engagement and wedding:** proposals on an evening out, wedding planning on the Character page following city
  customs, and a big day out with guests, a photo and a notice in the paper.
- **Clearer odds:** Hidden values groups reasons as "More likely because..." and "Less likely because...".
- **More Realism settings:** Relationship pace, Rough patches and Their love life sliders, and Friends can fall for you
  and Breaks and breakups switches, set by the presets.
- **Fixes:** fewer misread hurtful words, era-fitting reasons for called-off plans, friends moving to cities of their
  own time, and visit memories worded the right way round.

## v0.12.0 (2026-10-16)

- **A home of your own:** your persona lives in a city and neighborhood in each world, changeable on the persona
  form, and Matchlight looks there and moves with you.
- **Together or apart:** visits both ways, close companions who sometimes knock, suggestions to get together, chats
  written in person while together, and a where-you-are strip with Head home, Say goodbye and Not now.
- **Long distance:** the city and time difference on the chat list and Character page, weekend visits both ways
  (rarer for faraway cities), asked for in chat and called off on Today.
- **Phone calls:** a Call button and "Can I call you?", companions who call now and then, Answer and Decline on the
  strip, spoken replies read aloud with a voice set up, and calls that end on a goodbye or when it goes quiet.
- **Shifts and gigs:** weekly rotas for service and shift jobs and freelance gigs in busy and dry spells, with pay
  following the work and plans with you kept.
- **More Realism sliders:** Getting together, set by the presets.
- **Fixes:** phone-width lookup buttons and the running-joke picker no longer scroll sideways.

## v0.11.0 (2026-10-14)

- **Work life:** slammed, ordinary and slow weeks with a project deadline, a yearly review with raises by country and
  era, vacation days, late nights that can move dinner plans, layoffs on Drama, and a Work life panel.
- **Hobbies that progress:** up to three pastimes (yours first) with practice, milestones, gear and class costs,
  invitations along, and a pastimes panel.
- **Reading, watching and listening:** a book, a show and a song they're in the middle of, era-fitting titles,
  verdicts when they finish, and your own picks on their Character page.
- **Group chat guests:** companions bring in people they know, **Add someone**, regulars and **Keep in group**, and
  guests who sound like themselves.
- **Our history at a glance:** weekly, monthly and yearly lines about your whole time together, with an **All of it**
  scrapbook view you can correct.
- **Personality sliders:** five plain-word sliders for every companion and townsperson, set by the app, tunable in
  **Show details**.
- **Swipe in Matchlight:** drag or flick through profile cards, with **Undo** for the last answer.
- **More Realism sliders:** work life, pastimes, reading and watching, and guests, set by the presets.
- **Fixes:** "I'll cook" invitations become dinner plans, looks with each companion's pronouns, era-fitting topics,
  old errand prices re-priced once, and first names in panel headings.

## v0.10.0 (2026-10-13)

- **Pets with lives of their own:** off days, vet visits, checkups and old age (a rare death on Real life and Drama,
  never on Easy life, with a switch); a Pets panel; sitters and dogs on trips; pet photos; everyone can have pets, and
  your persona can list yours.
- **Home upkeep:** laundry, dishes and clutter build through their week, a neat, average or messy habit, big cleans on
  days off, and a Home panel with Set it.
- **Kitchen and food:** diets, cooking skill, favorite dishes, nightly dinners, staples and grocery runs, a kitchen
  panel with Change how they eat, and dinner at their place both ways.
- **Looks that change:** hair, nails and tans drift, with a bold new look every few months; looks you wrote stay put.
- **Life admin calendar:** appointments, bills, errands and paperwork by country and era, on Today and a Life admin
  panel, movable, never cancelling plans with you.
- **Author's note:** a note per chat, group chat and Story that steers every reply while it's on.
- **Around the home:** a Realism slider per home feature, set by the presets; numbers behind a Hidden values switch.
- **Also:** full-size picture viewer, replies through Claude Code on your Claude plan, a city picker for new personas
  and worlds, the built-in model's recommended settings, a ComfyUI model family picker with built-in workflows,
  clearer lookup settings, and adult careers with Adult side of life on.
- **Fixes:** character sheet people and pets kept, posts in the poster's voice, every picture in the chats list,
  camera-friendly picture wording, Matchlight profiles and photos, "next Thursday" plans, Today times in their time
  zone, US spelling in US cities, and roomier cards.

## v0.9.0 (2026-10-12)

- **Ready on first launch:** Set it up for me picks, downloads (pause, resume, checked) and runs a chat model that fits
  your graphics card, with nothing downloaded until you confirm; a companion made meanwhile is finished afterwards.
- **Look and accessibility:** Paper light profile, Match my computer for new installs, and per-device text size
  (85-200%), reading fonts (Atkinson Hyperlegible, OpenDyslexic) and motion.
- **Photos that fit them:** an editable In photos line on the character form.
- **Bring your old chats:** SillyTavern JSONL and role/content JSON become earlier shared history.
- **Export a chat or story** as a web page or Markdown.
- **Bring your Marinara world:** Marinara Engine characters, lorebooks and world maps.
- **Also:** Retro IM away messages, credits and usage on model profiles, editable ComfyUI workflows, and a Codex
  character reference sheet for steadier pictures.
- **Fixes:** home cities and key facts kept, she/he where set, month-first dates, US spelling in US towns, plans
  mentioned in replies, trips from invented towns, steadier life events, map labels, the voice download waits for its
  button, ComfyUI on its own Python, backups keep profile pictures, proxy settings honored, and copy fixes.

## v0.8.1 (2026-10-11)

- **Going out together:** staying in, a call or a story no longer counts as an outing; a vague "sometime" stays a
  wish; dates like "Saturday, November 14" land on the right day; the named place is the place, free places are
  free, and undo or a work shift can't double up a day.
- **Trips and traditions:** trips avoid planned days and traditions and check the real budget; postcards arrive on
  their own; Christmas Eve and New Year's Eve are days off; reworded traditions keep their voice.
- **Maps and Who knows who:** plans don't count as visits, New York 1925 gets a drawn map, no modern spots in
  period places, a stalled street map falls back to the drawn one, keyboard pins, and the close-circle filter works.
- **Chats:** chats open at the newest message, a held reply no longer shows "Delivered", and narrow-window message
  buttons no longer cover text.
- **Also:** pack characters can't become a starter companion, Looks says "none" for blanks, and a new day is about
  twice as fast.

## v0.8.0 (2026-10-11)

- **Maps:** street maps for real cities and drawn maps (districts, streets, parks, water) for the rest; place cards
  show who goes there, with Suggest going together and, in Story mode, Go there.
- **Who knows who:** a draggable web of everyone you've met or heard about, with search, filters and a list view.
- **Status messages:** an AIM-style status line for every companion, away lines while they sleep, work or go out,
  and editable on the profile card. Still no presence dots.
- **Spots inside places:** named spots in places and homes for life events and Story scenes.
- **Go somewhere together:** ask a companion out and it really happens, at a real place in town, and the outing
  shows up in their day and their memories.
- **Trips and postcards:** companions take trips of their own and send postcards while they're away.
- **Family traditions:** their families keep their own holidays and traditions through the year.
- **Our year so far:** a scrapbook that looks back on your year together.
- **Eight new cities and the Jazz Age:** Chicago, New Orleans, London today, Jeju, Osaka, New York 1925, Haddon
  Harbor and Pellmouth, plus a 1920s era; townsfolk jobs fit their town.
- **Grandport** from Oak's Neokosmos, with its named characters in town; any city pack can place named characters.
- **Featured and sorted cities:** Real / Modern, Other Eras, Fictional and Custom shelves with search, and a
  Featured strip (Baltimore, Grandport, Pellmouth, Osaka).
- **Townsfolk with a past** and **Looks** sheets for everyone, so pictures stay one person.
- **Phone tab bar:** five tabs (Chats, Today, Story, Matchlight, Settings).
- **Adult side of life:** an opt-in Realism switch, off by default, adults only.
- **Fixes:** no duplicate Today plans, no repeated unnamed locals in Story, no blank gaps in phone chats, and
  message buttons in one row in narrow windows.

## v0.7.1 (2026-10-10)

- **Livelier replies:** companions skip recaps and filler questions, replies are about a quarter shorter, and an
  upset mood shows in how they write.
- **Less stereotyped characters:** drafting no longer defaults to the cool, in-control type for a job, and
  contradictions vary.

## v0.7.0 (2026-10-10)

- **Life deck:** a small moment drawn into each day with the seeded dice; the companion knows it, Today lists the
  week's Little things, and with odds shown you can draw another card.
- **Dreams:** some nights the day turns into a short, odd dream the companion remembers the morning after.
- **Become a townsperson:** start a new world as someone you met around town, in the same town.
- **They can ask to remember more:** a wider look back for messages about the past, and one hidden request to
  look again.
- **OOC to the sidecar:** out-of-character asides go to the helper, never into the story; the sidecar can pop out
  into its own window.
- **Realism in one place:** a new Realism tab in Settings gathers everything that makes the world feel like
  real life. Start from one of four presets (I want real life, Bring on the drama, I want an easy life, I pull
  the strings), picked on the welcome screen or at the top of the tab, then dial anything up or down: how close you get with each companion (step it closer, set it,
  keep it there, never closer than, gentle cooling), whether they reply at their own pace, whether their days
  go off plan, how much drama there is, and Hidden values. Closeness can now be changed there for any
  companion, not only the one that's open.

## v0.6.1 (2026-10-10)

- **On their mind:** companions are "they" in the app's wording unless a character's own pronouns say otherwise.
- **ComfyUI launch scripts:** the launch button can run your own .bat/.cmd/.sh script as it is; plainer launch
  errors.
- **Faster catch-ups:** a month away with 25 companions catches up in about 3 s instead of 11, without "database
  is locked" errors meanwhile.
- **Service default:** blank model settings say the service you connect to picks the value.
- **Fixes:** memories kept when you switch worlds, evening-made companions get a home straight away, instant local
  replies retry a server that was still loading, profile tabs stay at the top, feed pictures keep faces in frame,
  friends' posts say whose friend they are, weekly backups start right away, the phone bottom bar fits.

## v0.6.0 (2026-10-09)

- **Worlds and personas:** each persona has worlds of their own, each with its own companions, town, chats
  and memories; existing data becomes the first world.
- **Bring your characters:** character cards (V1-V3 JSON/PNG, CHARX, Backyard, Pygmalion) and lorebooks
  (card, SillyTavern, NovelAI, Agnai, RisuAI) become a companion and keyword lore.
- **While you were away:** a rule-based catch-up after a few days away.
- **Launch your local models:** LM Studio, Ollama, KoboldCpp and ComfyUI from Settings, optionally at start.
- **Instant local replies** with llama-server slot saving; **automatic backups** of every world.
- **Remember this** on companion replies keeps what they said about themselves.

## v0.5.1 (2026-10-09)

- **Color schemes** from Prospero's Study (Ink, Slate, Umber, Moss, Wine, Ash) and a custom palette.
- **Number settings** use steppers, sliders and presets, save on change and stay within their limits.
- **Check for models** and rescans on return to the app; home folder shown as `~` in paths.
- **Paired phones** can add and manage hosted image services (keys only over Tailscale).
- Fixed: memories filed under the wrong companion after switching chats; stopped replies can be edited;
  PC-only messages say where to make the change.

## v0.5.0 (2026-10-09)

- **News travels:** news spreads one person a day; companions can text "Did you hear about…?"; Today
  shows who has heard.
- **Moods** for every companion, by rules; the cold shoulder in groups and an opt-in "People can walk out".
- **On their mind:** one private thought a day on Today.
- **Hidden values** in Settings > Life: moods, who heard the news and the odds stay hidden by default.
- **AI notices and crisis help:** first-run notice with an 18+ checkbox, an "AI can make mistakes" line
  in every chat, an app note with crisis lines when a message sounds like self-harm.
- **Record model calls** (Settings > Debug, off by default) with "Save for support".
- Release names carry a title (this one: "Word Gets Around"); a roadmap in the README.

## v0.4.0 (2026-10-09)

- **Everyone keeps living:** every companion lives their days; group chats start conversations.
- **Small world:** companions meet where their days take them; a weekly town paper on Today.
- **Consequence engine:** turnings decided from state with "Why it went this way" and a way to change
  them, lasting marks, user-action consequences, OOC odds; Life chapters every few months.
- **Voice notes:** built-in offline voice (about 378 MB on first use), or OpenAI, ElevenLabs, Google.
- **Sensible defaults:** everyday life events on, corrections apply at once, running jokes and circle
  fill themselves, rule-only background life, restores keep current settings.
- **Prompt caching** and small-model prompts; local background work waits for a pause in chat.

## v0.3.0 (2026-10-08)

- **Group chats:** several companions in one chat, each answering from what they know; secrets kept
  from those who mustn't know (set up from memories, editable, optional slip note); "how others see
  them" lines; two-way closeness between companions, their circle and townsfolk.
- **Every companion texts first** with one shared daily cap, a Chats list with unread counts per chat
  style, and openers at the times you usually show up.
- **Closeness controls:** step, set, cap and pre-set stages, shared moments, optional gentle cooling.
- **Branch from and edit any message;** the app's own notes get a box of their own.
- **Phone:** opt-in home Wi-Fi access, Tailscale checks and a backup address, press-and-hold actions.
- **Cities and errors:** Los Angeles built in, a city guide, plain-language errors, image model lists.

## v0.2.1 (2026-10-08)

- **Portable data:** Settings > Data shows where data lives and can move it into a Data folder beside
  the app.
- **Hardware check:** reads the graphics card and memory, says what local models fit, and warns about
  setups that will run badly (Settings, welcome screen, installer).
- **Chat status:** a line above the message box says what the reply is waiting on; failed or
  timed-out replies show at once with Retry; photos load with a blurry preview and Try again.
- **Timestamps** on messages and posts in every chat style.
- **NanoGPT** for chat models and pictures; image backends get an editable Connection panel.
- **Forgiving city import:** shared city files load despite small mistakes and keep new kinds of
  places, schools and jobs.
- **Fixes:** macOS "._" files on external drives broke the city catalog; reinstall rebuilds a broken
  .venv; errors name the log file. CI runs faster.

## v0.2.0 (2026-10-08)

- **Matchlight:** a dating app in the sidebar for meeting townsfolk and app-only singles; a match can
  become your companion. Personal ads or the town matchmaker in older eras.
- **Easier start:** model setup first, a quick start of name, age and where and when, character paste
  or card import, and life details behind Show details.
- **Helper sidecar:** an app-wide helper that proposes edits to character fields, replies and memories.
- **Profile** page with Messages, Posts and Character tabs, and a Message button.
- **Realism:** tracked wardrobe, consistent self-facts over months, corrections that stick everywhere,
  conflicts waiting in Character Studio, memory on by default, a daily sense of what's out and trending.
- **Townsfolk and names:** seed new townsfolk; about 100 names per decade for every culture and era.
- **Story mode** (optional, Settings > Advanced): a narrator for your own story, people-met list, dates.
- **Pictures:** Krea 2 prompt shaping, per-backend prompt style, NSFW switch for OpenRouter-style image
  APIs, ComfyUI model pickers, style LoRAs and sampler settings.
- **Models:** recall profiles of their own, Duplicate profile, Codex model list on Test connection.
- **Fixes:** Posts tab after Debug time, Home City showing only None, updating a ZIP copy, blank replies
  from thinking models, chat hover jump, panel spacing, and more. Scale results in docs/scale.md.

## v0.1.4 (2026-10-07)

- **Editable prompts:** Settings > Show advanced settings adds an Advanced tab to reword the core
  prompts, with defaults, placeholder checks and Reset to default.
- **Fixes from real-AI and browser test runs:** plain answers to OOC questions; no ((asides)) or
  "no real-time data" lines in character; OpenRouter 429 retried once; ESPN schedules and away games;
  more jobs and people details remembered; Help me write never writes JSON into a field; drafted homes
  match where they live and their rent; lowercase first texts; switching companions keeps the page;
  smaller Feed, Start over and life-event fixes.

## v0.1.3 (2026-10-07)

- **Fix:** every chat reply failed in v0.1.0 to v0.1.2 (a townsfolk lookup in the reply context).
  Unexpected reply failures are now logged.
- **Built-in recall:** the first model file found is preselected, a newly added model file shows up
  when you return to the window, the status reads "Loading the model…" right after you switch it on,
  and a model llama.cpp cannot load shows llama.cpp's reason.

## v0.1.2 (2026-10-07)

- **Send pictures in chat:** attach, paste or drop up to four pictures with a message, or send one on
  its own. They are shrunk and stripped of location data first. The model for **Seeing pictures** in
  Settings > Models (the conversation model unless you pick another) describes each picture once, so
  the companion sees it and remembers it later. A model that cannot look at pictures leaves it unseen:
  the companion says it would not load, and the real reason shows under the picture.
- **Built-in recall:** Settings > Models can run an embedding model on this PC with llama.cpp, apart
  from LM Studio, Kobold or Ollama, so recall finds related memories without an embeddings service. You
  download the model file (EmbeddingGemma 2 or Qwen3 Embedding 0.6B are suggested); llama.cpp
  downloads on request and is checked against a pinned checksum. It runs on the processor only and
  stops with the Companion. **Test recall** checks whatever does recall now.
- **Better recall with instruction-trained embedding models:** EmbeddingGemma, Qwen3 Embedding,
  nomic-embed-text, mxbai and Arctic now get the search instructions they were trained with. Their
  stored vectors are re-made once in the background.

## v0.1.1 (2026-10-07)

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
