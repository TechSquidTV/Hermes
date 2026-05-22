import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { spawnSync } from 'node:child_process'
import process from 'node:process'

const appDir = resolve(import.meta.dirname, '..')
const repoRoot = resolve(appDir, '../..')
const apiDir = join(repoRoot, 'packages/hermes-api')
const outputPath = join(appDir, 'src/types/api.generated.ts')
const tempDir = mkdtempSync(join(tmpdir(), 'hermes-openapi-types-'))
const schemaPath = join(tempDir, 'openapi.json')

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    stdio: 'inherit',
    env: process.env,
    ...options,
  })

  if (result.status !== 0) {
    process.exit(result.status ?? 1)
  }
}

try {
  run('uv', ['run', 'python', 'scripts/export_openapi.py', schemaPath], {
    cwd: apiDir,
    env: {
      ...process.env,
      HERMES_SECRET_KEY: process.env.HERMES_SECRET_KEY ?? 'openapi-schema-export',
    },
  })
  run('pnpm', ['exec', 'openapi-typescript', schemaPath, '-o', outputPath], {
    cwd: appDir,
  })
} finally {
  rmSync(tempDir, { recursive: true, force: true })
}
