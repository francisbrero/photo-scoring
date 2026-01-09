# ADR-010: Supabase Claude Code Integration

## Status

Accepted

## Date

2026-01-09

## Context

When working with Supabase, Claude Code can generate code and SQL but cannot directly execute changes. This creates friction as users must manually:
- Run migration scripts in the Supabase SQL editor
- Deploy Edge Functions via `supabase functions deploy`
- Configure Database Webhooks in the Dashboard
- Set secrets via `supabase secrets set`

We investigated three approaches to enable direct Supabase interaction from Claude Code.

## Research Findings

### Option A: Direct CLI Usage

The Supabase CLI (v2.67.1) is already installed and authenticated on this system. Available commands include:

| Operation | Command | Status |
|-----------|---------|--------|
| Push migrations | `supabase db push` | ✅ Works |
| Deploy functions | `supabase functions deploy <name>` | ✅ Works |
| Set secrets | `supabase secrets set KEY=value` | ✅ Works |
| List projects | `supabase projects list` | ✅ Works |
| View logs | `supabase functions logs <name>` | ✅ Works |

**Pros:**
- Already installed and authenticated
- Full feature coverage
- Session persists across conversations (login stored in `~/.supabase`)

**Cons:**
- Requires initial `supabase login` and `supabase link`
- Some commands require project to be linked first

### Option B: Supabase Management API

The Management API provides programmatic access but is designed for platform integrations, not direct AI usage. Most operations are available through the CLI which wraps the API.

**Not recommended** as standalone approach—the CLI provides better ergonomics.

### Option C: Supabase MCP Server

An official MCP server exists at `https://mcp.supabase.com/mcp` (maintained by supabase-community).

**Available Tools:**
- Database: List tables, execute SQL, manage migrations
- Edge Functions: Deploy, list, retrieve code
- Projects: Create, pause, restore
- Logs: Access by service type
- TypeScript: Generate types from schema
- Documentation: Search Supabase docs

**Notable Gaps:**
- ❌ No webhook management
- ❌ No secrets management
- ⚠️ Read-only mode recommended for production

**Configuration:**
```json
{
  "mcpServers": {
    "supabase": {
      "url": "https://mcp.supabase.com/mcp?project_ref=jbgkafsmdtotdrrgitzw"
    }
  }
}
```

## Decision

**Use a hybrid approach: CLI for full operations, MCP for enhanced capabilities.**

1. **Primary: Supabase CLI** - Use for all operations (migrations, deployments, secrets)
   - Already authenticated and linked to `Photo-scoring` project
   - Full feature coverage including secrets and webhooks
   - Claude Code can invoke via Bash tool

2. **Supplementary: MCP Server** - Configure for:
   - Documentation search (up-to-date Supabase docs)
   - TypeScript type generation
   - Project-scoped, read-only for safety

### Recommended MCP Configuration

Add to `.mcp.json` in project root:

```json
{
  "mcpServers": {
    "supabase": {
      "url": "https://mcp.supabase.com/mcp?project_ref=jbgkafsmdtotdrrgitzw&read_only=true&features=database,docs"
    }
  }
}
```

### CLI Usage Examples

```bash
# Deploy Edge Function
supabase functions deploy process-triage --project-ref jbgkafsmdtotdrrgitzw

# Push migrations
supabase db push --project-ref jbgkafsmdtotdrrgitzw

# Set secrets
supabase secrets set OPENROUTER_API_KEY=sk-xxx --project-ref jbgkafsmdtotdrrgitzw

# View function logs
supabase functions logs process-triage --project-ref jbgkafsmdtotdrrgitzw
```

## Consequences

### Positive

- Claude Code can now execute Supabase operations directly
- No additional tooling or API keys required
- Full coverage of desired operations (migrations, functions, secrets)
- MCP provides documentation search for staying current

### Negative

- CLI requires initial setup (`supabase login`, `supabase link`)
- MCP server doesn't cover webhooks or secrets (CLI fills this gap)
- Need to be careful with production operations

### Neutral

- Webhook configuration still requires Dashboard or direct API calls
- MCP should be project-scoped and read-only for safety

## Security Considerations

1. **Never use MCP with production data** - Use read-only mode
2. **CLI credentials** stored in `~/.supabase` - protect this directory
3. **Secrets** - Use `supabase secrets set` rather than hardcoding
4. **Review operations** - Claude Code should confirm destructive operations

## Alternatives Considered

1. **MCP-only approach**: Rejected because MCP lacks secrets management and webhook configuration
2. **Management API direct**: Rejected because CLI provides better ergonomics and is already authenticated
3. **Custom MCP server**: Rejected because official tools cover our needs

## References

- [Supabase CLI Reference](https://supabase.com/docs/reference/cli/introduction)
- [Supabase MCP Server](https://github.com/supabase-community/supabase-mcp)
- [Supabase MCP Docs](https://supabase.com/docs/guides/getting-started/mcp)
- [Supabase Edge Functions Deployment](https://supabase.com/docs/guides/functions/deploy)
- [Database Migrations](https://supabase.com/docs/guides/deployment/database-migrations)
