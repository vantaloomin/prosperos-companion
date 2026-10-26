import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import '@fontsource/ibm-plex-sans/400.css'
import '@fontsource/ibm-plex-sans/500.css'
import '@fontsource/literata/400.css'
import '@fontsource/atkinson-hyperlegible/latin-400.css'
import '@fontsource/atkinson-hyperlegible/latin-700.css'
// Name fonts for Their look in chat (src/features/conversation/theirLook.ts): one weight each, fetched only when a name uses it.
import '@fontsource/libre-baskerville/700.css'
import '@fontsource/manrope/700.css'
import '@fontsource/nunito/700.css'
import '@fontsource/courier-prime/700.css'
import '@fontsource/caveat/700.css'
import '@fontsource/oswald/600.css'
import './styles.css'
import App from './App'
import { PhoneGate } from './features/phone/PhoneGate'

const client = new QueryClient({ defaultOptions: { queries: { staleTime: 10_000, retry: 1, refetchOnWindowFocus: false } } })
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><QueryClientProvider client={client}><PhoneGate><App /></PhoneGate></QueryClientProvider></React.StrictMode>,
)

// Lets a phone install the app and show notifications (public/sw.js). It caches nothing.
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => undefined)
