import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Analytics } from '@vercel/analytics/react';

import App from './App';
import { detectBrand } from './lib/brand';
import './index.css';

// Set data-brand on <html> before first render so CSS scoping works immediately
const brand = detectBrand();
document.documentElement.setAttribute('data-brand', brand);

// Inject hookupgui.de fonts only when needed (avoids loading them for soulmatesmd users)
if (brand === 'hookupguide') {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href =
        'https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Silkscreen:wght@400;700&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Courier+Prime:ital,wght@0,400;0,700;1,400&family=DM+Mono:ital,wght@0,300;0,400;0,500;1,400&display=swap';
    document.head.appendChild(link);
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
    <Analytics />
  </React.StrictMode>,
);
