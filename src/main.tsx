import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import '@fontsource/ibm-plex-sans/400.css'
import '@fontsource/ibm-plex-sans/500.css'
import '@fontsource/literata/400.css'
import './styles.css'
import App from './App'
import { PhoneGate } from './features/phone/PhoneGate'

const client = new QueryClient({ defaultOptions: { queries: { staleTime: 10_000, retry: 1, refetchOnWindowFocus: false } } })
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><QueryClientProvider client={client}><PhoneGate><App /></PhoneGate></QueryClientProvider></React.StrictMode>,
)

// Lets a phone install the app and show notifications (public/sw.js). It caches nothing.
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => undefined)
