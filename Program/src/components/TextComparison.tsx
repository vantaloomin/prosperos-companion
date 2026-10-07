/** Before and after, side by side. Copied from prosperos-study src/features/textEdits/EditPresentation.tsx at bbcbde4. */
export function TextComparison({ before, after }: { before: string; after: string }) {
  return <div className="text-edit-comparison"><section><h4>Before</h4><pre>{before || '(empty)'}</pre></section><section><h4>After</h4><pre>{after || '(empty)'}</pre></section></div>
}
