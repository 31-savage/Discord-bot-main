# Discord Welcome Self-Bot

A Discord self-bot using [discord.py-self](https://github.com/dolfies/discord.py-self) that sends welcome messages when new users join your servers.

> **Warning**: Self-bots are against Discord's Terms of Service. Use at your own risk.

## Features

- Sends an embed message when a new member joins any server you're in
- Shows member count, username, avatar, and account age
- Warns about new accounts (< 7 days old)
- Configurable welcome channel (or auto-detects `#welcome`, `#general`, or system channel)
- Subscribes to guild member events automatically (required for large servers)
- Docker support for easy deployment
- Graceful shutdown handling

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Your Discord user token

## Getting Your Discord Token

1. Open Discord in your browser (not the desktop app)
2. Press `F12` to open Developer Tools
3. Go to the "Network" tab
4. Send a message in any channel
5. Look for a request to `messages` and click it
6. In the "Headers" tab, find the `Authorization` header - that's your token

## Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd discordjs-bot

# Install dependencies with uv
uv sync

# Copy environment file
cp .env.example .env

# Edit .env and add your Discord token
```

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_TOKEN` | Yes | Your Discord user token |
| `WELCOME_CHANNEL_ID` | No | Specific channel ID for welcome messages |
| `LOG_LEVEL` | No | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`) |
| `SUBSCRIBE_TO_MEMBER_EVENTS` | No | Subscribe to member events for guilds (default: `true`) |

## Running Locally

```bash
# Using uv (recommended)
uv run python -m discord_welcome_bot.main

# Or activate the virtual environment first
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
python -m discord_welcome_bot.main
```

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Create .env file with your token
cp .env.example .env
# Edit .env and add your DISCORD_TOKEN

# Build and run
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Using Docker directly

```bash
# Build the image
docker build -t discord-welcome-bot .

# Run the container
docker run -d \
  --name discord-welcome-bot \
  --restart unless-stopped \
  -e DISCORD_TOKEN=your_token_here \
  discord-welcome-bot
```

## Cloud Deployment

### Railway

1. Connect your GitHub repository
2. Add environment variable `DISCORD_TOKEN`
3. Deploy

### Fly.io

```bash
# Install flyctl and login
fly launch
fly secrets set DISCORD_TOKEN=your_token_here
fly deploy
```

### Render

1. Create a new "Background Worker"
2. Connect your repository
3. Set build command: `pip install uv && uv sync`
4. Set start command: `uv run python -m discord_welcome_bot.main`
5. Add environment variable `DISCORD_TOKEN`

## Project Structure

```
.
├── discord_welcome_bot/
│   ├── __init__.py      # Package init
│   ├── bot.py           # Main bot class with event handlers
│   ├── config.py        # Pydantic settings configuration
│   └── main.py          # Entry point
├── Dockerfile           # Multi-stage Docker build with uv
├── docker-compose.yml   # Docker Compose configuration
├── pyproject.toml       # Project configuration
├── uv.lock              # Locked dependencies
└── README.md
```

## Guild Subscriptions

For receiving `on_member_join` events, especially in larger guilds, the bot subscribes to member events. This is handled automatically but can be disabled via `SUBSCRIBE_TO_MEMBER_EVENTS=false`.

See the [discord.py-self documentation on guild subscriptions](https://discordpy-self.readthedocs.io/en/latest/guild_subscriptions.html) for more details.

## Development

```bash
# Install with dev dependencies
uv sync

# Run linting
uv run ruff check .

# Run type checking
uv run pyright
```

## License

ISC
