import { execSync } from 'child_process';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

function gitInfo() {
    try {
        const hash = execSync('git rev-parse --short HEAD').toString().trim();
        const count = execSync('git rev-list --count HEAD').toString().trim();
        return { hash, count };
    } catch {
        return { hash: 'dev', count: '0' };
    }
}

const { hash, count } = gitInfo();

export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
    },
    define: {
        __GIT_HASH__: JSON.stringify(hash),
        __COMMIT_COUNT__: JSON.stringify(count),
    },
});
