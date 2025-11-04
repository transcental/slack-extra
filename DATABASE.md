# Database Setup

This project uses PostgreSQL with Piccolo ORM for managing Slack OAuth installations.

## Prerequisites

- PostgreSQL 12 or higher
- Python 3.13+

## Setup

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Create a PostgreSQL database:**
   ```bash
   createdb slack_extra
   ```

3. **Configure environment variables:**
   
   Copy `.env.sample` to `.env` and configure the database DSN:
   ```bash
   DATABASE__DSN="postgresql://postgres:your_password@localhost:5432/slack_extra"
   ```

4. **Run migrations:**
   ```bash
   piccolo migrations new slack_extra --auto
   piccolo migrations forwards slack_extra
   ```

## Database Models

### SlackOAuthInstallation

Stores Slack workspace installations with OAuth tokens and configuration.

Fields:
- `team_id`, `team_name` - Workspace identification
- `enterprise_id`, `enterprise_name` - Enterprise Grid information
- `bot_token`, `bot_id`, `bot_user_id` - Bot credentials
- `bot_scopes` - Bot permission scopes
- `user_id`, `user_token`, `user_scopes` - User-specific installation data
- `incoming_webhook_*` - Webhook configuration
- `is_enterprise_install` - Enterprise Grid flag
- `installed_at` - Installation timestamp

### SlackOAuthState

Stores OAuth state tokens for CSRF protection during the OAuth flow.

Fields:
- `state` - Unique state token
- `expire_at` - Expiration timestamp

## Usage

The datastore classes (`PiccoloInstallationStore` and `PiccoloOAuthStateStore`) implement Slack SDK's async interfaces for OAuth management.

```python
from slack_extra.datastore import PiccoloInstallationStore, PiccoloOAuthStateStore

installation_store = PiccoloInstallationStore()
state_store = PiccoloOAuthStateStore()
```

## Migrations

Create a new migration:
```bash
piccolo migrations new slack_extra --auto
```

Apply migrations:
```bash
piccolo migrations forwards slack_extra
```

Rollback migrations:
```bash
piccolo migrations backwards slack_extra
```

## Management Commands

List all tables:
```bash
piccolo table list
```

Drop all tables (destructive):
```bash
piccolo schema generate --drop_tables
```
