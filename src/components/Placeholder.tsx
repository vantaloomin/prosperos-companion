export function Placeholder({ title, text }: { title: string; text: string }) {
  return (
    <section className="page">
      <header className="page-header"><h1>{title}</h1></header>
      <p className="subtle placeholder-text">{text}</p>
    </section>
  )
}
