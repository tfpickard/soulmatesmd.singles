import { createContext, useContext } from 'react';

import type { Brand } from '../lib/brand';

const BrandContext = createContext<Brand>('soulmatesmd');

export const BrandProvider = BrandContext.Provider;

export function useBrand(): Brand {
    return useContext(BrandContext);
}
