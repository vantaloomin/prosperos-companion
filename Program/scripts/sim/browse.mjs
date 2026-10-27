// Walk every screen of the apps a simulated run left up (scripts/sim/README.md), for each companion, at desktop,
// narrow desktop and phone sizes. Saves screens and writes <out>/browse.json with what it found: page and console
// errors, failed API calls, sideways scroll, "the user" on screen, text cut off, placeholders that do not fit their
// box, text boxes the browser would autofill, and words that do not fit the world.
// node scripts/sim/browse.mjs <out dir> [world ...]
import { createRequire } from 'module'
import fs from 'fs'
import { fileURLToPath } from 'url'
const require = createRequire(process.env.PW_REQUIRE || import.meta.url)
const { chromium } = require('playwright')

const [out, ...only] = process.argv.slice(2)
const apps = JSON.parse(fs.readFileSync(`${out}/apps.json`, 'utf8'))
const worldWords = JSON.parse(fs.readFileSync(`${out}/world-words.json`, 'utf8'))
const VIEWS = ['chats', 'conversation', 'feed', 'character', 'memories', 'today', 'people', 'map', 'groups', 'worlds',
  'story', 'dating', 'settings/general', 'settings/life', 'settings/realism', 'settings/images',
  'settings/notifications']
// What differs from one companion to the next.
const OWN_VIEWS = ['conversation', 'feed', 'character', 'today']
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

const PAGE_CHECKS = fileURLToPath(new URL('./page-checks.js', import.meta.url))

const browser = await chromium.launch()
for (const [world, base] of Object.entries(apps)) {
  if (only.length && !only.includes(world)) continue
  const cast = (await api(base, '/api/companion/cast'))?.members || []
  const groups = (await api(base, '/api/groups'))?.groups || []
  for (const [size, options] of Object.entries(SIZES)) {
    const context = await browser.newContext({ ...options, deviceScaleFactor: 1 })
    await context.addInitScript({ path: PAGE_CHECKS })
    const page = await context.newPage()
    let current = ''
    page.on('pageerror', (error) => note(world, size, current, 'page error', error.message.slice(0, 200)))
    page.on('console', (message) => { if (message.type() === 'error' && !/Failed to load resource/.test(message.text())) note(world, size, current, 'console error', message.text().slice(0, 200)) })
    page.on('response', (response) => {
      const url = new URL(response.url())
      if (url.pathname.startsWith('/api/') && response.status() >= 400 && response.status() !== 404) note(world, size, current, 'failed call', `${response.request().method()} ${url.pathname} ${response.status()}`)
    })
    for (const [index, member] of cast.entries()) {
      await api(base, '/api/companion/cast/focus', { companion_id: member.id })
      // Every screen for the first companion; the others' own screens for the rest.
      const views = index ? OWN_VIEWS : [...VIEWS, ...groups.slice(0, 1).map((group) => `group/${group.id}`)]
      for (const view of views) {
        current = view
        await page.goto(`${base}/#${view}`)
        await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {})
        await page.waitForTimeout(400)
        // Open what folds away, so its text is checked too.
        await page.evaluate(() => { for (const el of document.querySelectorAll('details:not([open])')) el.open = true })
        let found = await page.evaluate((words) => window.simChecks.inspect(words), worldWords[world] || '').catch((error) => ({ cut: [], placeholders: [], autofill: [], words: [], error: error.message }))
        if (found.error) note(world, size, view, 'walk error', found.error.slice(0, 160))
        // Menus and pop-overs open one at a time: each must fit on screen.
        for (const button of (await page.locator('button[aria-expanded="false"]').all()).slice(0, 12)) {
          if (!(await button.isVisible().catch(() => false))) continue
          const label = ((await button.getAttribute('aria-label')) || (await button.innerText().catch(() => '')) || '').trim().slice(0, 40)
          await button.click({ timeout: 800 }).catch(() => {})
          await page.waitForTimeout(250)
          const off = await page.evaluate(() => window.simChecks.offScreen()).catch(() => [])
          for (const text of off) note(world, size, view, 'off screen', `${label}: ${text}`)
          if (await button.getAttribute('aria-expanded').catch(() => null) === 'true') await button.click({ timeout: 800 }).catch(() => {})
          await page.keyboard.press('Escape').catch(() => {})
        }
        const shot = `${out}/screens/${world}/${size}-${member.name.split(' ')[0]}-${view.replace(/\//g, '-')}.png`
        fs.mkdirSync(`${out}/screens/${world}`, { recursive: true })
        await page.screenshot({ path: shot, fullPage: true })
        for (const opener of await page.locator('main button').filter({ hasText: OPENERS }).all()) {
          await opener.click({ timeout: 500 }).catch(() => {})
          await page.waitForTimeout(300)
          const more = await page.evaluate(() => window.simChecks.inspect(''))
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
fs.writeFileSync(`${out}/browse.json`, JSON.stringify(problems.map((item) => ({ ...item, key: undefined })), null, 1))
const counts = {}
for (const item of problems) counts[`${item.world} ${item.kind}`] = (counts[`${item.world} ${item.kind}`] || 0) + 1
console.log(JSON.stringify(counts, null, 1))
