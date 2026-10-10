import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ChevronLeft, ChevronRight } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { Companion, Scrapbook, ScrapbookItem, ScrapbookListing, ScrapbookPage, ScrapbookPeriod } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { imageFile } from '../feed/imageState'
import { SCRAPBOOKS_KEY, dayText, firstKey, pageAt, spanText, sparse } from './yearText'

/**
 * Our year so far: a scrapbook of your time with them, one page at a time. Swipe on a phone; arrows, the dots or
 * the arrow keys on a computer. Every page comes from what happened, written by templates.
 */
export function OurYear({ companion, go }: { companion: Companion; go: (view: View) => void }) {
  const name = companion.version.name
  const listing = useQuery({ queryKey: SCRAPBOOKS_KEY, queryFn: () => api<ScrapbookListing>('/life/year') })
  const [chosen, setChosen] = useState<string | null>(null)
  const key = chosen ?? firstKey(listing.data)
  useSeen(listing.data, setChosen)
  const book = useQuery({ queryKey: ['scrapbook', key], queryFn: () => api<Scrapbook>(`/life/year/${key}`), enabled: key !== null })
  return (
    <section className="page our-year">
      <button type="button" className="text-button" onClick={() => go('memories')}><ArrowLeft aria-hidden="true" />Memories</button>
      <YearHeader book={book.data} name={name} periods={listing.data?.periods ?? []} chosen={key} onChoose={setChosen} />
      {listing.isPending && <Loading label="Loading your scrapbook" />}
      {listing.isError && <ErrorNotice error={listing.error} />}
      {listing.isSuccess && !key && <Notice>Your scrapbook starts with your first message to {name}. Come back once you have talked for a while.</Notice>}
      {book.isError && <ErrorNotice error={book.error} />}
      {book.data && <Pages key={book.data.key} book={book.data} />}
    </section>
  )
}

/** Opening the scrapbook Today pointed to keeps Today's card away; the page stays on that scrapbook. */
function useSeen(listing: ScrapbookListing | undefined, setChosen: (key: string) => void) {
  const client = useQueryClient()
  const featured = listing?.featured ?? null
  useEffect(() => {
    if (!featured) return
    setChosen(featured)
    void api<ScrapbookListing>(`/life/year/${featured}/seen`, {}).then((listing) => client.setQueryData(SCRAPBOOKS_KEY, listing)).catch(() => undefined)
  }, [featured, setChosen, client])
}

function YearHeader({ book, name, periods, chosen, onChoose }: { book?: Scrapbook; name: string; periods: ScrapbookPeriod[]; chosen: string | null; onChoose: (key: string) => void }) {
  return (
    <header className="year-header">
      <h1>{book?.title ?? 'Our year so far'}</h1>
      <p className="subtle">{book ? spanText(book.start, book.end) : `A look back at your time with ${name}, from what really happened.`}</p>
      {periods.length > 1 && (
        <select aria-label="Which year" value={chosen ?? ''} onChange={(event) => onChoose(event.target.value)}>
          {periods.map((period) => <option key={period.key} value={period.key}>{period.title}</option>)}
        </select>
      )}
    </header>
  )
}

function Pages({ book }: { book: Scrapbook }) {
  const strip = useRef<HTMLDivElement>(null)
  const [current, setCurrent] = useState(0)
  const count = book.pages.length
  useEffect(() => { strip.current?.scrollTo({ left: 0 }) }, [book.key])
  const show = (index: number) => {
    const node = strip.current
    if (!node) return
    const next = Math.min(count - 1, Math.max(0, index))
    node.scrollTo({ left: next * node.clientWidth, behavior: 'smooth' })
    setCurrent(next)
  }
  const keys = (event: KeyboardEvent) => {
    if (event.key === 'ArrowRight') { event.preventDefault(); show(current + 1) }
    if (event.key === 'ArrowLeft') { event.preventDefault(); show(current - 1) }
  }
  return (
    <div className="year-book">
      <div ref={strip} className="year-pages" tabIndex={0} role="group" aria-roledescription="scrapbook" aria-label={`${book.title}, page ${current + 1} of ${count}`}
        onKeyDown={keys} onScroll={(event) => setCurrent(pageAt(event.currentTarget.scrollLeft, event.currentTarget.clientWidth, count))}>
        {book.pages.map((page, index) => (
          <article key={`${page.kind}-${index}`} className={`year-page year-page-${page.kind}${sparse(page) ? ' year-page-sparse' : ''}`} aria-label={`Page ${index + 1}: ${page.title}`} aria-hidden={index !== current}>
            <PageBody page={page} name={book.name} />
          </article>
        ))}
      </div>
      <nav className="year-controls" aria-label="Pages">
        <button type="button" className="icon-button" aria-label="Previous page" disabled={current === 0} onClick={() => show(current - 1)}><ChevronLeft aria-hidden="true" /></button>
        <ol className="year-dots">
          {book.pages.map((page, index) => (
            <li key={`${page.kind}-${index}`}><button type="button" aria-label={`Page ${index + 1}: ${page.title}`} aria-current={index === current ? 'step' : undefined} onClick={() => show(index)} /></li>
          ))}
        </ol>
        <button type="button" className="icon-button" aria-label="Next page" disabled={current >= count - 1} onClick={() => show(current + 1)}><ChevronRight aria-hidden="true" /></button>
      </nav>
    </div>
  )
}

function PageBody({ page, name }: { page: ScrapbookPage; name: string }) {
  if (page.kind === 'cover') return <>
    <p className="eyebrow">{page.subtitle}</p>
    <h2>{page.title}</h2>
    <dl className="year-stats">
      {page.stats.map((stat) => <div key={stat.label}><dt>{stat.label}</dt><dd>{stat.value}</dd></div>)}
    </dl>
  </>
  if (page.kind === 'first') return <>
    <p className="eyebrow">{dayText(page.date, true)}</p>
    <h2>{page.title}</h2>
    <figure className="year-quote"><blockquote>{page.said}</blockquote><figcaption>You</figcaption></figure>
    {page.reply && <figure className="year-quote reply"><blockquote>{page.reply}</blockquote><figcaption>{name}</figcaption></figure>}
  </>
  if (page.kind === 'photos') return <>
    <h2>{page.title}</h2>
    <ul className="year-photos">
      {page.photos.map((photo) => <li key={photo.ref}><img src={imageFile(photo.ref)} alt={photo.summary} loading="lazy" />{photo.date && <span>{dayText(photo.date)}</span>}</li>)}
    </ul>
  </>
  if (page.kind === 'closing') return <>
    <h2>{page.title}</h2>
    <p className="year-closing">{page.text}</p>
  </>
  return <>
    <h2>{page.title}</h2>
    <Items items={page.items} />
    {page.kind === 'jokes' && page.note && <p className="subtle">{page.note}</p>}
  </>
}

function Items({ items }: { items: ScrapbookItem[] }) {
  return (
    <ul className="year-items">
      {items.map((item, index) => <li key={`${item.date ?? ''}-${index}`}>{item.date && <time dateTime={item.date}>{dayText(item.date)}</time>}<span>{item.text}</span></li>)}
    </ul>
  )
}
