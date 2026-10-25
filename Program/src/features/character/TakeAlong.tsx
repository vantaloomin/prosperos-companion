import { Download } from 'lucide-react'

/** Save a companion with everything that happened, to open in another world under Bring your characters
 * (companion/carry.py). A plain link: the server answers with the file, so it works on a phone too. */
export function TakeAlong({ id, name }: { id: string; name: string }) {
  return (
    <section className="settings-section form-stack" aria-labelledby="take-along-heading">
      <div>
        <h2 id="take-along-heading">Take {name} to another world</h2>
        <p className="subtle">Saves {name} to a file with everything that happened between you: chats, memories, how close you are and where things stand, their kids, home, wardrobe, look and voice. Open it under Bring your characters in another world and they arrive there with all of it. If that world is in another city, they move there and find the same kind of work. Trained looks stay behind because of their size; their reference pictures come along.</p>
      </div>
      <div className="form-actions">
        <a className="button" href={`/api/export/companion/${encodeURIComponent(id)}`} download><Download aria-hidden="true" />Save {name} to a file</a>
      </div>
    </section>
  )
}
