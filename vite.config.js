import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Port 3000 matches FRONTEND_URL in the backend, so password-reset emails link to this app.
export default defineConfig({ plugins: [react()], server: { port: 3000 } });
