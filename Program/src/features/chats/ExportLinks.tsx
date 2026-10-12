import { Download } from 'lucide-react'
import { EXPORT_FORMATS, exportHref, type ExportTarget } from './exportText'

/** "Export as HTML" and "Export as Markdown": the file is made on this computer and saved by the browser. */
export function ExportLinks({ target, onPick }: { target: ExportTarget; onPick?: () => void }) {
  return <>
    {EXPORT_FORMATS.map(({ format, label }) => (
      <a key={format} className="text-button export-link" href={exportHref(target, format)} download onClick={onPick}><Download aria-hidden="true" />{label}</a>
    ))}
  </>
}
