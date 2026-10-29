export const meta = {
  name: 'devpulse-bug-scan',
  description: 'Read-only bug review of four DevPulse files in parallel',
  phases: [{ title: 'Review', detail: 'one reviewer per file' }],
}
const FILES = ['server.py', 'index.html', 'streak.js', 'mcp/devpulse_mcp.py']
const SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          line: { type: 'integer' },
          severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low'] },
          summary: { type: 'string' },
          scenario: { type: 'string' },
        },
        required: ['file', 'severity', 'summary', 'scenario'],
      },
    },
  },
  required: ['findings'],
}
const results = await parallel(FILES.map(f => () =>
  agent(`Review ${f} in the DevPulse project (cwd) for real bugs: correctness, validation gaps, security, race conditions, error handling, edge cases. Read-only: do NOT modify any files. Read the file fully; read other files only if needed for context. Report only genuine bugs with a concrete failure scenario and line number, not style nits. If the file does not exist, return no findings.`,
    { label: `review:${f}`, phase: 'Review', schema: SCHEMA, agentType: 'code-reviewer' })))
const order = { critical: 0, high: 1, medium: 2, low: 3 }
return results.filter(Boolean).flatMap(r => r.findings).sort((a, b) => order[a.severity] - order[b.severity])