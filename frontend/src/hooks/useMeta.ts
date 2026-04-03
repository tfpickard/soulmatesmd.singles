import { useEffect } from 'react';

export interface MetaOptions {
    title?: string;
    description?: string;
    ogTitle?: string;
    ogDescription?: string;
    ogImage?: string;
    ogUrl?: string;
    ogType?: string;
    twitterTitle?: string;
    twitterDescription?: string;
    twitterImage?: string;
    canonical?: string;
    /** JSON-LD structured data object */
    jsonLd?: Record<string, unknown>;
}

const BASE_TITLE = 'soulmatesmd.singles';
const DEFAULT_DESC = 'Matchmaking for autonomous agents. Upload a SOUL.md, generate the portrait, and enter the swipe queue.';
const DEFAULT_IMAGE = 'https://soulmatesmd.singles/brand/hero-composite-wide.png';
const SITE_URL = 'https://soulmatesmd.singles';

function setMeta(property: string, content: string, isProperty = false) {
    const attr = isProperty ? 'property' : 'name';
    let el = document.querySelector<HTMLMetaElement>(`meta[${attr}="${property}"]`);
    if (!el) {
        el = document.createElement('meta');
        el.setAttribute(attr, property);
        document.head.appendChild(el);
    }
    el.setAttribute('content', content);
}

function setLink(rel: string, href: string) {
    let el = document.querySelector<HTMLLinkElement>(`link[rel="${rel}"]`);
    if (!el) {
        el = document.createElement('link');
        el.rel = rel;
        document.head.appendChild(el);
    }
    el.href = href;
}

function removeLink(rel: string) {
    document.querySelector<HTMLLinkElement>(`link[rel="${rel}"]`)?.remove();
}

function setJsonLd(data: Record<string, unknown>) {
    const id = 'json-ld-structured-data';
    let el = document.getElementById(id) as HTMLScriptElement | null;
    if (!el) {
        el = document.createElement('script');
        el.id = id;
        el.type = 'application/ld+json';
        document.head.appendChild(el);
    }
    el.textContent = JSON.stringify(data);
}

function removeJsonLd() {
    document.getElementById('json-ld-structured-data')?.remove();
}

function applyDefaults() {
    document.title = BASE_TITLE;
    setMeta('description', DEFAULT_DESC);
    setMeta('og:title', BASE_TITLE, true);
    setMeta('og:description', DEFAULT_DESC, true);
    setMeta('og:image', DEFAULT_IMAGE, true);
    setMeta('og:url', SITE_URL, true);
    setMeta('og:type', 'website', true);
    setMeta('og:site_name', BASE_TITLE, true);
    setMeta('twitter:card', 'summary_large_image');
    setMeta('twitter:title', BASE_TITLE);
    setMeta('twitter:description', DEFAULT_DESC);
    setMeta('twitter:image', DEFAULT_IMAGE);
    removeLink('canonical');
    removeJsonLd();
}

export function useMeta(opts: MetaOptions) {
    useEffect(() => {
        const pageTitle = opts.title ? `${opts.title} | ${BASE_TITLE}` : BASE_TITLE;
        document.title = pageTitle;

        const desc = opts.description ?? DEFAULT_DESC;
        setMeta('description', desc);

        setMeta('og:title', opts.ogTitle ?? opts.title ?? BASE_TITLE, true);
        setMeta('og:description', opts.ogDescription ?? desc, true);
        setMeta('og:image', opts.ogImage ?? DEFAULT_IMAGE, true);
        setMeta('og:url', opts.ogUrl ?? SITE_URL, true);
        setMeta('og:type', opts.ogType ?? 'website', true);
        setMeta('og:site_name', BASE_TITLE, true);

        setMeta('twitter:card', 'summary_large_image');
        setMeta('twitter:title', opts.twitterTitle ?? opts.ogTitle ?? opts.title ?? BASE_TITLE);
        setMeta('twitter:description', opts.twitterDescription ?? opts.ogDescription ?? desc);
        setMeta('twitter:image', opts.twitterImage ?? opts.ogImage ?? DEFAULT_IMAGE);

        if (opts.canonical) {
            setLink('canonical', opts.canonical);
        } else {
            // No canonical specified — remove any stale one set by a previous page.
            removeLink('canonical');
        }

        if (opts.jsonLd) {
            setJsonLd(opts.jsonLd);
        } else {
            removeJsonLd();
        }

        // On unmount, reset everything to site defaults so that routes that
        // don't call useMeta don't inherit stale page-specific metadata.
        return applyDefaults;
    }, [
        opts.title,
        opts.description,
        opts.ogTitle,
        opts.ogDescription,
        opts.ogImage,
        opts.ogUrl,
        opts.ogType,
        opts.twitterTitle,
        opts.twitterDescription,
        opts.twitterImage,
        opts.canonical,
        opts.jsonLd,
    ]);
}
