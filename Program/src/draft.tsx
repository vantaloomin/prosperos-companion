import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import '@fontsource/ibm-plex-sans/400.css'
import '@fontsource/ibm-plex-sans/500.css'
import '@fontsource/literata/400.css'
import '@fontsource/atkinson-hyperlegible/latin-400.css'
import '@fontsource/atkinson-hyperlegible/latin-700.css'
import './styles.css'
import { DraftTable } from './features/draft/DraftTable'
import { PhoneGate } from './features/phone/PhoneGate'

// Prospero's Draft Table (draft.html): its own window, served by the same Companion, with the same look.
const client = new QueryClient({ defaultOptions: { queries: { staleTime: 10_000, retry: 1, refetchOnWindowFocus: false } } })
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><QueryClientProvider client={client}><PhoneGate><DraftTable /></PhoneGate></QueryClientProvider></React.StrictMode>,
)
