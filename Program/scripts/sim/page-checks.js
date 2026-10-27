// Runs in the page (browse.mjs adds it with addScriptTag): what is wrong with what the screen shows.
;(() => {
  const visible = (el) => {
    const box = el.getBoundingClientRect()
    return box.width > 0 && box.height > 0 && getComputedStyle(el).visibility !== 'hidden'
  }
  // Text kept only for screen readers (.visually-hidden) is cut on purpose.
  const forReaders = (el) => el.getBoundingClientRect().width <= 2 || getComputedStyle(el).clip.startsWith('rect(0')
  const px = (value) => parseFloat(value) || 0
  const textOf = (el) => (el.innerText ?? el.textContent ?? '').trim()

  function clips(style) {
    return style.overflow === 'hidden' || style.overflowX === 'hidden' || style.textOverflow === 'ellipsis'
  }

  function cutSideways(el) {
    return el.scrollWidth > el.clientWidth + 2
  }

  function cutDown(el, style) {
    if (style.webkitLineClamp !== 'none' || style.whiteSpace === 'nowrap' || el.clientHeight <= 0) return false
    return el.scrollHeight > el.clientHeight + 4
  }

  function cutText() {
    const found = []
    for (const el of document.querySelectorAll('h1, h2, h3, h4, button, a, label, .chip, [class*="name"], [class*="title"], strong, span, p, td, li')) {
      if (!visible(el) || forReaders(el) || el.children.length > 2) continue
      const style = getComputedStyle(el)
      const text = textOf(el)
      if (!text || !clips(style)) continue
      if (cutSideways(el) || cutDown(el, style)) found.push(text.slice(0, 80))
    }
    return found
  }

  function textBoxes() {
    return [...document.querySelectorAll('input, textarea')].filter((el) => {
      if (!visible(el)) return false
      const type = (el.getAttribute('type') || 'text').toLowerCase()
      return el.tagName === 'TEXTAREA' || ['text', 'search', ''].includes(type)
    })
  }

  function linesOf(el, style) {
    if (el.tagName !== 'TEXTAREA') return 1
    const line = px(style.lineHeight) || px(style.fontSize) * 1.3
    return Math.max(1, Math.floor((el.clientHeight - px(style.paddingTop) - px(style.paddingBottom)) / line))
  }

  function placeholderTooLong(el, canvas) {
    if (!el.placeholder) return ''
    const style = getComputedStyle(el)
    canvas.font = `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`
    const room = el.clientWidth - px(style.paddingLeft) - px(style.paddingRight)
    const fits = canvas.measureText(el.placeholder).width <= room * linesOf(el, style) + 1
    return fits ? '' : `${el.placeholder} (${Math.round(room)}px box)`
  }

  function autofills(el) {
    const own = (el.getAttribute('autocomplete') || '').toLowerCase()
    if (['off', 'new-password', 'one-time-code'].includes(own)) return false
    return !(el.form && el.form.getAttribute('autocomplete') === 'off')
  }

  function labelOf(el) {
    const label = el.labels?.[0]?.innerText || el.getAttribute('aria-label') || el.placeholder || el.name || '(no label)'
    return label.trim().slice(0, 60)
  }

  function boxes() {
    const canvas = document.createElement('canvas').getContext('2d')
    const found = { placeholders: [], autofill: [] }
    for (const el of textBoxes()) {
      const long = placeholderTooLong(el, canvas)
      if (long) found.placeholders.push(long)
      if (autofills(el)) found.autofill.push(labelOf(el))
    }
    return found
  }

  function worldWords(words) {
    if (!words) return []
    const pattern = new RegExp(`\\b(?:${words})\\b`, 'gi')
    const main = document.querySelector('main') || document.body
    const found = []
    for (const line of main.innerText.split('\n')) {
      for (const match of line.matchAll(pattern)) found.push(`${match[0]}: ${line.trim().slice(0, 140)}`)
    }
    return found
  }

  function inspect(words) {
    return {
      wide: document.documentElement.scrollWidth > window.innerWidth + 1,
      user: /\bthe user\b/i.test(document.body.innerText),
      cut: cutText(),
      ...boxes(),
      words: worldWords(words),
    }
  }

  function laidOver(el) {
    const style = getComputedStyle(el)
    if (!['absolute', 'fixed'].includes(style.position)) return false
    return style.visibility !== 'hidden' && style.display !== 'none'
  }

  // Wholly outside is hidden on purpose (a skip link, a closed drawer); partly outside is cut off.
  function partlyOutside(box) {
    const right = box.right > window.innerWidth + 2 && box.left < window.innerWidth
    return right || (box.left < -2 && box.right > 0)
  }

  function nameOf(el) {
    return String(el.innerText || el.getAttribute('aria-label') || el.className || el.tagName).trim().slice(0, 60)
  }

  // What sits partly outside the window, sideways, among things laid over the page.
  function offScreen() {
    const found = []
    for (const el of document.querySelectorAll('body *')) {
      if (!laidOver(el)) continue
      const box = el.getBoundingClientRect()
      if (box.width < 8 || box.height < 8 || !partlyOutside(box)) continue
      found.push(`${nameOf(el)} (${Math.round(box.left)} to ${Math.round(box.right)} of ${window.innerWidth})`)
    }
    return found.slice(0, 3)
  }

  window.simChecks = { inspect, offScreen }
})()
