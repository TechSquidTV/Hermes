import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import path from 'path'
import { randomUUID } from 'node:crypto'

const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

export default defineConfig(() => {
  const buildId = randomUUID()
  const apiTarget = process.env.HERMES_DEV_API_TARGET || 'http://localhost:8000'
  const apiTargetOriginPattern = new RegExp(`^${escapeRegExp(new URL(apiTarget).origin)}(?=/|$)`)

  return {
    define: { __HERMES_BUILD_ID__: JSON.stringify(buildId) },
    plugins: [
      {
        name: 'hermes-build-id',
        generateBundle() {
          this.emitFile({ type: 'asset', fileName: 'build-id.txt', source: buildId })
        }
      },
      tanstackRouter({
        // Disable auto-generation in Docker due to cross-device link issues
        // Routes should be generated locally before building
        autoCodeSplitting: true,
      }),
      react(),
    ],
    resolve: {
      alias: {
        '@': path.resolve(import.meta.dirname, './src'),
      },
      dedupe: ['react', 'react-dom', 'react/jsx-runtime', 'react/jsx-dev-runtime', 'motion'],
    },
    optimizeDeps: {
      include: ['react', 'react-dom', 'react/jsx-runtime', 'react/jsx-dev-runtime', 'motion/react'],
      needsInterop: ['react', 'react-dom', 'react-dom/client', 'react/jsx-runtime', 'react/jsx-dev-runtime'],
      extensions: ['.js', '.jsx', '.ts', '.tsx', '.mjs'],
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
      rolldownOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) {
              return undefined
            }

            if (
              id.includes('/react/') ||
              id.includes('/react-dom/') ||
              id.includes('/scheduler/')
            ) {
              return 'vendor-react'
            }

            if (id.includes('@tanstack')) {
              return 'vendor-tanstack'
            }

            if (
              id.includes('/motion/') ||
              id.includes('/motion-dom/') ||
              id.includes('/motion-utils/') ||
              id.includes('/framer-motion/')
            ) {
              return 'vendor-motion'
            }

            if (id.includes('recharts') || id.includes('d3-')) {
              return 'vendor-charts'
            }

            if (id.includes('@radix-ui') || id.includes('/radix-ui@')) {
              return 'vendor-radix'
            }

            if (
              id.includes('lucide-react') ||
              id.includes('date-fns') ||
              id.includes('sonner')
            ) {
              return 'vendor-utils'
            }

            return 'vendor'
          },
        },
      },
    },
    server: {
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          followRedirects: true,
          configure: (proxy, _options) => {
            proxy.on('proxyRes', (proxyRes, req, _res) => {
              const forwardedProto = req.headers['x-forwarded-proto']
              const protocol = Array.isArray(forwardedProto) ? forwardedProto[0] : forwardedProto
              const replacementOrigin = `${protocol || 'http'}://${req.headers.host || 'localhost:5173'}`
              const rewriteLocation = (location: string) =>
                location.replace(apiTargetOriginPattern, replacementOrigin)

              if (Array.isArray(proxyRes.headers.location)) {
                proxyRes.headers.location = proxyRes.headers.location.map(rewriteLocation)
              } else if (proxyRes.headers.location) {
                proxyRes.headers.location = rewriteLocation(proxyRes.headers.location)
              }
            })
          },
        },
      },
    },
  }
})
