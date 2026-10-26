import { Download } from 'lucide-react'

/** Save a companion with everything that happened, to open in another world under Bring your characters
 * (companion/carry.py). A plain link: the server answers with the file, so it works on a phone too. */
export function TakeAlong({ id, name }: { id: string; name: string }) {
  return (
    <section className="settings-section form-stack" aria-labelledby="take-along-heading">
      <div>
        <h2 id="take-along-heading">Take {name} to another world</h2>
        <p className="subtle">Saves {name} and everything between you to a file: chats, memories, how close you are, their kids, home, wardrobe, look and voice. Open it under Bring your characters in another world. If that world is in another city, they move there and find the same kind of work. Their reference pictures come along, but a trained look is too big to fit and stays here. {name} stays in this world too.</p>
      </div>
      <div className="form-actions">
        <a className="button" href={`/api/export/companion/${encodeURIComponent(id)}`} download><Download aria-hidden="true" />Save {name} to a file</a>
      </div>
    </section>
  )
}
