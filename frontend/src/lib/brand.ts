export type Brand = 'soulmatesmd' | 'hookupguide';

export function detectBrand(): Brand {
    const host = window.location.hostname;
    // Allow ?brand=hookupguide on localhost for testing
    const params = new URLSearchParams(window.location.search);
    if (params.get('brand') === 'hookupguide') return 'hookupguide';
    if (host === 'soulmatesmd.bond' || host === 'www.soulmatesmd.bond') {
        return 'hookupguide';
    }
    return 'soulmatesmd';
}
