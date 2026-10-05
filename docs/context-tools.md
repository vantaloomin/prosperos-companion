# Current context tools (MCP)

[Back to the README](../README.md)

The Companion can look up real weather, news and local events through
[Model Context Protocol](https://modelcontextprotocol.io) servers the user configures
(PRD X1–X3), and read links the user pastes. Nothing needs a paid API or key. Lookups run only once the
user turns them on; reading pasted links is on by default and can be turned off. One server ships with
the app, a keyless weather server; any other service the user adds. The code is in `companion/mcp/`.

## How it works

1. **Location.** The user types their own city or region, and optionally coordinates, under
   Settings. It is stored apart from the companion's fictional location and never detected.
2. **Service.** The user adds an MCP server: a local program (stdio) or an HTTPS address
   (streamable HTTP; plain HTTP only for a service on this computer). An optional key is kept in
   the OS credential vault and sent only to that server, as an environment variable or header.
3. **Check.** The app connects, lists the server's tools and suggests one tool per category
   (weather, news, local events) with arguments filled from the tool's input schema. Only
   properties a known source can fill are used; optional ones it can't fill are left out.
4. **Disclosure and enabling.** Saving a mapping leaves it off. Its disclosure says which tool at
   which destination receives which arguments, with today's values, when it runs, and what is never
   sent. Enabling requires the digest of that disclosure; any change to the destination, tool,
   arguments or timing needs a new confirmation. Changing a server's program, address or key turns
   its lookups off.

### What a lookup can send

| Source | Value |
| --- | --- |
| `place` | The user's city or region as typed, or the companion's city for companion lookups |
| `latitude`, `longitude` | Coordinates the user entered, or the centre of the companion's city |
| `topic` | Up to six words naming what the user asked about ("news about the harbor bridge") |
| `date` | Today's date where the lookup applies |
| `literal` | A fixed value the user chose (for example units) |
| `url` | The link the user pasted (link reading only; a tool that takes a list, such as `urls`, gets a list of one) |

The conversation, memories, the user's name, the character definition and other services' keys
are never sent. A local program starts with only the environment variables it needs to run (such as
`PATH` and `TEMP`) plus its own key, so `COMPANION_API_KEY` never reaches it.

### When lookups run

The model is never given tools. The app decides, with fixed rules on the user's message:

| Category | Runs when the message | Applies to |
| --- | --- | --- |
| Weather | mentions the weather, forecast, rain, snow, temperature, an umbrella… | The user's location |
| News | mentions news, headlines or current events; "news about X" sends X as the topic | No location |
| Local events | mentions events, concerts, festivals or things to do, with "near me", "tonight", "this weekend"… | The user's location |
| Reading links | contains a link that this computer could not read (see [Links you paste](#links-you-paste)) | Sends only the link |

When the message asks about the companion's whereabouts ("what's the weather like where you
are?"), weather and events target the companion's city instead, but only for mappings that allow
companion lookups and only when that city is a real, modern place in the world data. Oz, a
steampunk city or an unknown location is never looked up.

A retried send or an alternative reply reuses the lookups already made for that message. Without a
model connection no reply is written, so nothing is looked up.

### Limits

| Limit | Value |
| --- | --- |
| Deadline for lookups before a reply | 5 seconds; the reply goes ahead without them |
| Deadline for a lookup started from Settings | 20 seconds |
| Retries | One, only for a timeout or a transport failure, when time remains |
| Pause after a failure | 5 minutes per service |
| Requests per service | 20 an hour, 100 a day |
| Services per category | 2 |
| Message size | 512 KB per message; stored text 2,000 characters |
| Reuse | A fresh result with the same tool and arguments is reused instead of asking again |

### Freshness and failures

Results stay fresh for an hour (weather), three hours (news) or twelve hours (events). A fresh
result is quoted in the reply's context with its service, tool and retrieval time. When a lookup is
refused by a limit, the latest earlier result for the same arguments is included but labelled out
of date ("do not describe it as current"). A failed lookup tells the companion it does not know the
current conditions and should carry on. Results for one category from two services carry a note
that they may disagree.

Tool output is data. It is stored as plain text, quoted between « » under a heading that says it
cannot change the companion's rules, reveal memories or ask for more lookups, and nothing in it is
ever parsed for instructions or used to call another tool. Servers' requests back to the app
(sampling, roots, elicitation) are refused; only `ping` is answered.

Observations are not personal memories (M6): they are never extracted into memories, they are
listed separately, and each one can be deleted. The receipt of a reply lists the observations it
was given under `outside`.

## Real weather for the companion's day

A weather mapping that allows companion lookups can also give the companion's simulated day real
weather, in place of the city's typical weather from its climate data (W2). While background
activity is on and the workspace is not paused, each life tick asks for the companion's city; the
fresh-result reuse keeps that to about once an hour. A conversation question about the weather
where the companion is counts too.

`companion/mcp/weather.py` reads a high, a low and rain from the result: from structured fields
named for their unit (`high_f`, `temp_c`…) or from temperatures in the text ("61°F", "30 °C"), with
rain from words such as rain, showers or storms. A result with no readable temperature changes
nothing. Only a lookup made on that local date applies, and only for a real, modern city. After a
readable lookup, that day's schedule entries that have not started are removed and composed again
with the same seeds, so only the weather (and whether an outdoor plan moves indoors) can change.
Entries already under way keep their weather. The day's weather then carries `observed` (source,
tool, time), and the reply's context gives it under "Today's real weather where you live (looked up
by the app…)" with its source and time, instead of the typical-weather heading.

## Real events in the companion's city

A local-events mapping that allows companion lookups is also asked, on the same background ticks
(at most every twelve hours, the events freshness), for the companion's real city. While that
result is fresh, every reply's context lists it under "Real events listed for your city", which
says the companion may want to go or plan to, but has not attended any of them unless its
committed events say so. A real event can inspire a plan or an imagined outing; it never becomes a
life event or proof of attendance by itself (PRD X intro, T7).

## Links you paste

A link in the user's message is its own trigger: the app opens it so the companion can talk about
it. It is on by default (**Open links I paste** in Settings) and reads at most two links per message.
The model is never given a fetch tool. `companion/mcp/links.py` does the reading on the user's
computer:

| Link | How it is read |
| --- | --- |
| Reddit post (including `/s/` share links and `redd.it`, which redirect to one) | Reddit's public JSON view of the post: title, subreddit, author, score, text and the top five comments |
| Subreddit (`reddit.com/r/name`) | The subreddit's current hot posts, by title |
| X or Twitter post (`x.com/user/status/id`) | X's public oEmbed endpoint (`publish.twitter.com/oembed`): the post's text, author and date; not replies or images |
| X profile, search or other X page | Not read: X shows them only to signed-in users |
| YouTube video | YouTube's oEmbed endpoint: the title and channel only |
| Any other page | The page's HTML: title, description and the paragraph text, preferring `<article>`/`<main>` and leaving out navigation, scripts, headers and footers |

Limits: 6 seconds and 1.5 MB per page, four redirects, 6,000 characters kept, 30 links an hour, and a
read link stays fresh (reused, not fetched again) for six hours. Only `http` and `https` links to public
addresses are opened: a link whose host is or resolves to this computer, the local network, a
link-local or any other private address is refused, and so is every redirect to one, so a pasted link
cannot reach the app itself or a router. (A host that changes its DNS answer between the check and the
request is not caught.) PDFs, images, video and pages that only render in a browser are not read.

When a page cannot be read on this computer, an enabled **Reading links** mapping (a fetch tool on an
MCP service, such as Parallel's `web_fetch` or Firecrawl's scrape) is tried next. It runs only then,
sends only the link and needs the same disclosure and confirmation as other lookups.

What the companion is told:

- **Read:** the page's text, quoted, under the outside-information heading, saying the companion has
  looked at the link and can talk about it.
- **Not read:** that the link would not open for them and they have not seen it, so they must not
  guess, summarise or pretend to know what it says. They give a brief in-character reason, matched to
  what their simulated day says they are doing right now (a blocked site on a work network, bad signal
  while out, a page that just won't load), and ask what it says. The real reason is not given to the
  model, so error codes never reach the chat.

Under the user's message, a small out-of-character note says **Opened example.com** or **Couldn't
load example.com: the real reason**, so the user always knows what happened.

## The built-in weather server

`companion/mcp/servers/weather.py` is a small read-only MCP server that ships with the app. Settings
offers **Add the built-in weather server**, which adds and checks it in one step; its weather lookup
then needs the same disclosure and confirmation as any other service. The app runs it with its own
Python (`python -I companion/mcp/servers/weather.py`), so it works from a checkout or the installed
bundle with nothing else installed. It is stored as the command `@builtin:weather`.

| | |
| --- | --- |
| Tool | `get_forecast(location, latitude?, longitude?)`; the suggested mapping sends only `location` (your city or region as typed) |
| Finding the place | [Open-Meteo geocoding](https://open-meteo.com/en/docs/geocoding-api), searching the city name; text after a comma (state, US state abbreviation or country) chooses among matches |
| Forecast | [Open-Meteo](https://open-meteo.com) for today: conditions, high, low, chance of precipitation and the current temperature, in °F |
| Fallback | The [National Weather Service](https://www.weather.gov/documentation/services-web-api) API, only for US places (or coordinates) when Open-Meteo fails |
| Result | Text such as "Baltimore, Maryland, US: light rain, high 61°F, low 52°F, 70% chance of precipitation, now 58°F", plus `high_f`, `low_f`, `condition`, `precipitation_chance`, `temperature_f`, `source`, so real weather for the companion's day reads it directly |
| Network | Only the place name or coordinates are sent. 8-second timeout, no redirects, User-Agent `ProsperoCompanion/1.0 (built-in weather server)` as the NWS asks. It starts with the same minimal environment as other local programs, plus proxy and certificate settings; never the app's keys |

Open-Meteo's free API is for non-commercial use and its data is licensed CC BY 4.0, so every result
carries "Weather data by Open-Meteo.com (CC BY 4.0)". A commercial distribution of the app would need
an Open-Meteo subscription or a different source. NWS data is public domain.

## Interface

Settings has a **Real-world lookups** section: your location, the services, a suggested tool for
each category with its arguments, the disclosure to confirm, and a way to try an enabled lookup.
Memories has a **Real-world lookups** list kept apart from memories, showing what each lookup
sent, where, when, and whether it still counts as current, with delete.

## API

| Method and path | Purpose |
| --- | --- |
| `GET /api/context` | Location, services with their mappings and disclosures, and the source and timing labels |
| `PUT /api/context/location` | `{user_place, user_latitude, user_longitude}` |
| `PUT /api/context/links` | `{read_links}`: whether links pasted in chat are opened |
| `POST /api/context/services/builtin` | `{kind: weather}`: add the built-in weather server (once) |
| `POST /api/context/services` | `{name, transport: stdio\|http, command: [program, args…], url, secret, secret_name}` |
| `PUT`, `DELETE /api/context/services/{id}` | Edit (`clear_secret` removes the key) or remove a service |
| `POST /api/context/services/{id}/check` | Connect and list tools; returns `suggestions` per category |
| `PUT`, `DELETE /api/context/services/{id}/tools/{category}` | `{tool, arguments: {name: {source, value?}}, run_in: [conversation, companion_city]}` |
| `POST /api/context/services/{id}/tools/{category}/enable` | `{digest}` from the mapping's disclosure |
| `POST /api/context/services/{id}/tools/{category}/disable` | Turn a mapping off |
| `POST /api/context/lookup` | `{category, purpose, topic}`: try enabled lookups now, under the same limits |
| `GET /api/context/observations` | Every lookup attempt, newest first, with `fresh` |
| `GET /api/context/messages/{id}/observations` | The observations a user message's reply was given |
| `DELETE /api/context/observations/{id}`, `POST /api/context/observations/clear` | Delete records |

## Tested transports

Supporting MCP does not make every server compatible. The client speaks the protocol revisions
with an `initialize` handshake (2025-03-26, 2025-06-18 and 2025-11-25) and only lists and calls
tools. CI runs these combinations on Linux and Windows:

| Server | Transport | Response | Session | Result |
| --- | --- | --- | --- | --- |
| Stand-in (`tests/mcp_standin.py`) | stdio | — | — | Passes |
| Stand-in | Streamable HTTP | JSON | Session id | Passes |
| Stand-in | Streamable HTTP | Event stream, with a notification first | Session id | Passes |
| Stand-in | Streamable HTTP | JSON, bearer key | Session id | Passes; a wrong key is reported as refused |
| Official MCP Python SDK 2.3.0 (`MCPServer`) | stdio | — | — | Passes |
| Official MCP Python SDK 2.3.0 | Streamable HTTP | JSON | Stateful | Passes |
| Official MCP Python SDK 2.3.0 | Streamable HTTP | Event stream | Stateful | Passes |
| Official MCP Python SDK 2.3.0 | Streamable HTTP | JSON | Stateless | Passes |
| Official MCP Python SDK 2.3.0 | Streamable HTTP | Event stream | Stateless | Passes |
| Built-in weather server | stdio | — | — | Passes, against recorded Open-Meteo and NWS answers |

Each SDK case lists tools, calls a tool and checks that a tool error is reported as a failure.
No public weather, news or events server has been tested yet, and the built-in weather server has
not yet reached the live Open-Meteo or NWS APIs: the development environment blocks outbound access to
them, so its tests use recorded answers (`tests/test_weather_server.py`). Not supported: the older HTTP+SSE transport (2024-11-05), the 2026-07-28
single-exchange HTTP revision, OAuth sign-in, resources, prompts and any tool that writes, posts,
reads private inboxes or calendars, or makes transactions (out of scope for the first release).
