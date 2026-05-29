# Vetic MCP gateway

One FastMCP Python server that:

1. Authenticates Vetic users with Google (popup happens inside Claude on first
   connect — no per-user ToolHive Desktop install, no token paste).
2. Fronts multiple existing MCP servers from the public registry (Postgres,
   Mongo, …) under one URL with namespace prefixes (`pg_<dbname>_*`, `mongo_*`).

## Adding more Postgres databases

Drop five lines in `.env` with a new `<NAME>`:

```
POSTGRES_REPORTING_HOST=...
POSTGRES_REPORTING_PORT=5432
POSTGRES_REPORTING_USER=readonly
POSTGRES_REPORTING_PASSWORD=...
POSTGRES_REPORTING_DB=reporting
```

Restart `python server.py`. Tools surface in Claude as
`pg_reporting_query`, `pg_reporting_list_schemas`, etc. No code change.

## Repo layout

```
.
├── server.py            entry point — wires the parts, runs HTTP server
├── app/
│   ├── config.py        env vars (.env) → Settings dataclass
│   ├── auth.py          Google OAuth provider for FastMCP
│   └── backends.py      mount Postgres + Mongo registry MCP servers
├── .env.example         template; copy to .env and fill in
├── requirements.txt
└── README.md            (this file)
```

```
Claude (any tool: Desktop, Code, claude.ai)
       │
       │  paste URL + first call → 401 → discovery → DCR
       ▼
https://mcp.vetic.in/mcp                  ← public, only entry point
       │
       │  Google popup → @vetic.in only (enforced by Google OAuth consent screen)
       ▼
FastMCP gateway (server.py)
       │
       ├─► npx @modelcontextprotocol/server-postgres   (stdio child, namespace "pg_<dbname>")
       └─► npx mongo-mcp                                (stdio child, namespace "mongo")
```

The child MCP servers are spawned by the gateway via `npx`. They are not
reachable from outside. Only the FastMCP gateway is exposed.

---

## Local setup

### 1. Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Also install Node + npx — the gateway spawns the Postgres/Mongo MCP servers
via npx:

```bash
# Ubuntu
sudo apt -y install nodejs npm
# macOS
brew install node
```

### 2. Create a Google OAuth client

<https://console.cloud.google.com/apis/credentials>:

1. **OAuth consent screen** → User type: **Internal** (this is what restricts
   sign-in to `@vetic.in` — enforced by Google, no code needed).
2. **Create OAuth client ID** → Web application.
3. **Authorized redirect URI:** `http://localhost:8080/auth/callback`
4. Save the **Client ID** and **Client Secret**.

### 3. Configure secrets

```bash
cp .env.example .env
# edit .env and fill in GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, POSTGRES_URL, MONGO_URL
```

`.env` is gitignored — never commit it.

### 4. Run

```bash
python server.py
```

Should print:
```
FastMCP server running on http://0.0.0.0:8080
```

### 5. Connect from Claude

```bash
claude mcp add --transport http vetic http://localhost:8080/mcp
```

In a Claude Code session, ask:

> List the tables in the Postgres database.

What happens:
1. Claude makes its first MCP call → 401.
2. Claude discovers OAuth → opens browser.
3. **Google sign-in popup** → pick an `@vetic.in` account.
4. Token cached. Tool result comes back.

You'll see tools like `pg_query`, `pg_describe_table`, `mongo_find`, etc.,
automatically prefixed with the namespace.

---

## Production deploy (EC2 + nginx)

The Python file does not change. What changes:

- Set `BASE_URL=https://mcp.vetic.in` in `.env` on the EC2 host.
- Update the Google OAuth client's **Authorized redirect URI** to
  `https://mcp.vetic.in/auth/callback`.
- Run via `systemd` (or supervisord, tmux for a quick demo).
- Front with your existing nginx + Let's Encrypt:
  ```nginx
  server {
      server_name mcp.vetic.in;
      listen 443 ssl;
      # ... certbot-managed cert lines ...
      location / {
          proxy_pass http://127.0.0.1:8080;
          proxy_set_header Host              $host;
          proxy_set_header X-Forwarded-Proto $scheme;
          proxy_http_version 1.1;
          proxy_set_header Connection        "";
      }
  }
  ```

That's it.

---

## What's missing for the full PRD (add when you hit each need)

This v1 ships **Google login + Postgres + Mongo behind one URL**. To get the
rest of the PRD:

| PRD requirement | Where it goes |
|---|---|
| 5-role RBAC (ops/analyst/business/engineer/cxo) | Add a `ROLE_MAP: {email: role}` table; check role inside custom tools before delegating to `pg_*` / `mongo_*`. |
| PII masking on `owner_email`, etc. | Wrap `pg_query` with a custom tool that post-processes rows; or replace the raw `pg_query` with domain tools (`query_appointments`) that mask in-Python. |
| Bounded query cost (≤ 7-day window) | Reject input args at the gateway level; or replace raw SQL tools with constrained domain tools. |
| Read-only enforcement | Connection string uses a read-only Postgres role + read-only Mongo user. |
| Server-authored system prompt | `@mcp.prompt` in `server.py`. |
| Audit log | `logger.info(...)` per tool call, ship to CloudWatch. |

Each of these is a small addition to `server.py` or a wrapper tool — not a
rewrite. The auth + fan-out wiring is already in place.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Google says `redirect_uri_mismatch` | The redirect URI in Google Console must exactly match `http://localhost:8080/auth/callback` (or your prod equivalent). Trailing slashes count. |
| Google says "this app isn't verified" | OAuth consent screen is set to External. Switch to **Internal** so only Workspace users can sign in. |
| `npx: command not found` from FastMCP | Node not installed on the host. `node -v` should print v18+. |
| `Import "fastmcp" could not be resolved` (Pylance) | `pip install -r requirements.txt` not run. Activate the venv too. |
| Mongo proxy errors on startup | `mongo-mcp` npm package name varies. Try `mcp-mongo-server` or whichever is current on npm and update `package=` in `app/backends.py`. |
| Mongo warning `Invalid arguments for tool 'mongo_listCollections'` | `mongo-mcp` returns a slightly off-spec response shape; the call still succeeds. Harmless log noise. |
| Claude can connect but tool returns 401 | Token expired (1h default). Re-trigger the OAuth flow by removing and re-adding the connector in Claude. |
