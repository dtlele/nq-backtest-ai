import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'serve-output',
      configureServer(server) {
        server.middlewares.use('/api/output/', (req, res, next) => {
          const filePath = path.resolve(process.cwd(), '../output', req.url.slice(1));
          if (fs.existsSync(filePath)) {
            res.setHeader('Content-Type', filePath.endsWith('.json') ? 'application/json' : 'text/csv');
            fs.createReadStream(filePath).pipe(res);
          } else {
            next();
          }
        });
      }
    }
  ],
})
