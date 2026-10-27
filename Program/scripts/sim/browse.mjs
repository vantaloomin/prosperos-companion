// Walk every screen of the apps a simulated run left up (scripts/sim/README.md), for each companion, at desktop,
// narrow desktop and phone sizes. Saves screens and writes <out>/browse.json with what it found: page and console
// errors, failed API calls, sideways scroll, "the user" on screen, text cut off, placeholders that do not fit their
// box, text boxes the browser would autofill, and words that do not fit the world.
// node scripts/sim/browse.mjs <out dir> [world ...]
import { createRequire } from 'module'
import fs from 'fs'
const require = createRequire(process.env.PW_REQUIRE || import.meta.url)
const { chromium } = require('playwright')

const [out, ...only] = process.argv.slice(2)
const apps = JSON.parse(fs.readFileSync(`${out}/apps.json`, 'utf8'))
const worldWords = JSON.parse(fs.readFileSync(`${out}/world-words.json`, 'utf8'))
const VIEWS = ['chats', 'conversation', 'feed', 'character', 'memories', 'today', 'people', 'map', 'groups', 'worlds',
  'story', 'dating', 'settings/general', 'settings/life', 'settings/realism', 'settings/images',
  'settings/notifications']
// Buttons that open a form without changing anything, so its text boxes are checked too.
const OPENERS = /^(Add someone|Add a pet|Add a pastime|Add memory|Write a post|New post|Edit)$/i
const SIZES = {
  desktop: { viewport: { width: 1440, height: 900 } },
  narrow: { viewport: { width: 1024, height: 768 } },
  phone: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true },
}
const HEADERS = { 'X-Companion-Client': 'workspace', 'Content-Type': 'application/json' }
const problems = []
const seen = new Set()

function note(world, size, view, kind, text) {
  const key = `${world}|${kind}|${view}|${text}`
  if (seen.has(`${world}|${kind}|${view}|${text}|${size}`)) return
  seen.add(`${world}|${kind}|${view}|${text}|${size}`)
  const found = problems.find((item) => item.key === key)
  if (found) found.sizes.push(size)
  else problems.push({ key, world, kind, view, text, sizes: [size] })
}

async function api(base, path, body) {
  const response = await fetch(`${base}${path}`, { method: body ? 'POST' : 'GET', headers: HEADERS, body: body && JSON.stringify(body) })
  return response.ok ? response.json() : null
}

// Runs in the page: what is wrong with what it shows.
function inspect(words) {
  const found = { wide: document.documentElement.scrollWidth > window.innerWidth + 1, user: /\bthe user\b/i.test(document.body.innerText), cut: [], placeholders: [], autofill: [], words: [] }
  const visible = (el) => { const box = el.getBoundingClientRect(); return box.width > 0 && box.height > 0 && getComputedStyle(el).visibility !== 'hidden' }
  for (const el of document.querySelectorAll('h1, h2, h3, h4, button, a, label, .chip, [class*="name"], [class*="title"], strong, span, p, td, li')) {
    if (!visible(el) || el.children.length > 2) continue
    const style = getComputedStyle(el)
    const clips = style.overflow === 'hidden' || style.overflowX === 'hidden' || style.textOverflow === 'ellipsis'
    const text = el.innerText.trim()
    if (clips && text && el.scrollWidth > el.clientWidth + 2) found.cut.push(text.slice(0, 80))
    if (clips && text && style.webkitLineClamp === 'none' && el.scrollHeight > el.clientHeight + 4 && style.whiteSpace !== 'nowrap' && el.clientHeight > 0) found.cut.push(text.slice(0, 80))
  }
  const canvas = document.createElement('canvas').getContext('2d')
  for (const el of document.querySelectorAll('input, textarea')) {
    if (!visible(el)) continue
    const type = (el.getAttribute('type') || 'text').toLowerCase()
    if (el.tagName === 'INPUT' && !['text', 'search', ''].includes(type)) continue
    const style = getComputedStyle(el)
    if (el.placeholder) {
      canvas.font = `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`
      const room = el.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight)
      const lines = el.tagName === 'TEXTAREA' ? Math.max(1, Math.floor((el.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom)) / (parseFloat(style.lineHeight) || parseFloat(style.fontSize) * 1.3))) : 1
      if (canvas.measureText(el.placeholder).width > room * lines + 1) found.placeholders.push(`${el.placeholder} (${Math.round(room)}px box)`)
    }
    const off = (el.getAttribute('autocomplete') || '').toLowerCase()
    if (!['off', 'new-password', 'one-time-code'].includes(off) && !(el.form && (el.form.getAttribute('autocomplete') || '') === 'off')) {
      const label = el.labels?.[0]?.innerText || el.getAttribute('aria-label') || el.placeholder || el.name || '(no label)'
      found.autofill.push(label.trim().slice(0, 60))
    }
  }
  if (words) {
    const pattern = new RegExp(`\\b(?:${words})\\b`, 'gi')
    const main = document.querySelector('main') || document.body
    for (const line of main.innerText.split('\n')) {
      for (const match of line.matchAll(pattern)) found.words.push(`${match[0]}: ${line.trim().slice(0, 140)}`)
    }
  }
  return found
}

const browser = await chromium.launch()
for (const [world, base] of Object.entries(apps)) {
  if (only.length && !only.includes(world)) continue
  const cast = (await api(base, '/api/companion/cast'))?.members || []
  const groups = (await api(base, '/api/groups'))?.groups || []
  for (const [size, options] of Object.entries(SIZES)) {
    const context = await browser.newContext({ ...options, deviceScaleFactor: 1 })
    const page = await context.newPage()
    let current = ''
    page.on('pageerror', (error) => note(world, size, current, 'page error', error.message.slice(0, 200)))
    page.on('console', (message) => { if (message.type() === 'error' && !/Failed to load resource/.test(message.text())) note(world, size, current, 'console error', message.text().slice(0, 200)) })
    page.on('response', (response) => {
      const url = new URL(response.url())
      if (url.pathname.startsWith('/api/') && response.status() >= 400 && response.status() !== 404) note(world, size, current, 'failed call', `${response.request().method()} ${url.pathname} ${response.status()}`)
    })
    for (const member of cast) {
      await api(base, '/api/companion/cast/focus', { companion_id: member.id })
      const views = [...VIEWS, ...groups.slice(0, 1).map((group) => `group/${group.id}`)]
      for (const view of views) {
        current = view
        await page.goto(`${base}/#${view}`)
        await page.waitForTimeout(1800)
        // Open what folds away, so its text is checked too.
        await page.evaluate(() => { for (const el of document.querySelectorAll('details:not([open])')) el.open = true })
        for (const button of await page.locator('main button[aria-expanded="false"]').all()) await button.click({ timeout: 500 }).catch(() => {})
        await page.waitForTimeout(300)
        let found = await page.evaluate(inspect, worldWords[world] || '')
        const shot = `${out}/screens/${world}/${size}-${member.name.split(' ')[0]}-${view.replace(/\//g, '-')}.png`
        fs.mkdirSync(`${out}/screens/${world}`, { recursive: true })
        await page.screenshot({ path: shot, fullPage: true })
        for (const opener of await page.locator('main button').filter({ hasText: OPENERS }).all()) {
          await opener.click({ timeout: 500 }).catch(() => {})
          await page.waitForTimeout(300)
          const more = await page.evaluate(inspect, '')
          found = { ...found, placeholders: [...found.placeholders, ...more.placeholders], autofill: [...found.autofill, ...more.autofill], cut: [...found.cut, ...more.cut] }
          await page.keyboard.press('Escape').catch(() => {})
          break
        }
        if (found.wide) note(world, size, view, 'sideways scroll', 'the page scrolls sideways')
        if (found.user) note(world, size, view, 'says "the user"', 'the screen says "the user"')
        for (const text of new Set(found.cut)) note(world, size, view, 'text cut off', text)
        for (const text of new Set(found.placeholders)) note(world, size, view, 'placeholder too long', text)
        for (const text of new Set(found.autofill)) note(world, size, view, 'browser autofill on', text)
        for (const text of new Set(found.words)) note(world, size, view, 'word does not fit world', text)
      }
    }
    await context.close()
  }
  if (cast[0]) await api(base, '/api/companion/cast/focus', { companion_id: cast[0].id })
}
await browser.close()
fs.writeFileSync(`${out}/browse.json`, JSON.stringify(problems.map(({ key, ...item }) => item), null, 1))
const counts = {}
for (const item of problems) counts[`${item.world} ${item.kind}`] = (counts[`${item.world} ${item.kind}`] || 0) + 1
console.log(JSON.stringify(counts, null, 1))
