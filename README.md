# Discord Welcome Self-Bot

A Discord self-bot using [discord.py-self](https://github.com/dolfies/discord.py-self) that notifies you when new users join servers you're monitoring.

> **Warning**: Self-bots are against Discord's Terms of Service. Use at your own risk.

## Features

- Sends notifications to a group DM when members join monitored servers
- Shows member count, username, avatar, and account age
- Warns about new accounts (< 7 days old)
- **Commands** to manage which servers to monitor
- By default monitors NOTHING (opt-in per server)
- Docker support for easy deployment

## Commands

| Command | Description |
|---------|-------------|
| `!servers` | List all servers the bot is in |
| `!monitor <guild_id>` | Add a server to the monitored list |
| `!unmonitor <guild_id>` | Remove a server from the monitored list |
| `!monitored` | List all monitored servers |
| `!clear` | Clear monitored list (monitor nothing) |
| `!whelp` | Show help for all commands |

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Your Discord user token
- A Group DM channel ID for notifications

## Setup

### 1. Get Your Discord Token

1. Open Discord in your browser (not the desktop app)
2. Press `F12` to open Developer Tools
3. Go to the "Network" tab
4. Send a message in any channel
5. Look for a request to `messages` and click it
6. In the "Headers" tab, find the `Authorization` header - that's your token

### 2. Create a Group DM & Get Channel ID

1. Create a group DM with at least one other person (you can remove them later or use an alt)
2. Enable Developer Mode: User Settings > App Settings > Advanced > Developer Mode
3. Right-click the group DM and select "Copy Channel ID"

### 3. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd discordjs-bot

# Install dependencies with uv
uv sync

# Copy environment file
cp .env.example .env

# Edit .env and add your token and channel ID
```

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_TOKEN` | Yes | Your Discord user token |
| `NOTIFICATION_CHANNEL_ID` | Yes | Group DM channel ID for notifications |
| `LOG_LEVEL` | No | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`) |
| `COMMAND_PREFIX` | No | Prefix for commands (default: `!`) |
| `DATA_DIR` | No | Directory for persistent data (default: `.`) |

## Running Locally

```bash
# Using uv (recommended)
uv run python -m discord_welcome_bot.main

# Or activate the virtual environment first
source .venv/bin/activate  # Linux/macOS
python -m discord_welcome_bot.main
```

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Create .env file
cp .env.example .env
# Edit .env with your DISCORD_TOKEN and NOTIFICATION_CHANNEL_ID

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
  -e NOTIFICATION_CHANNEL_ID=your_channel_id \
  discord-welcome-bot
```

## Cloud Deployment

### Railway

1. Connect your GitHub repository
2. Add environment variables:
   - `DISCORD_TOKEN`
   - `NOTIFICATION_CHANNEL_ID`
3. Deploy

#### Persistent Storage on Railway

To persist your monitored servers list across restarts:

1. In your Railway project, press `Cmd+K` (or `Ctrl+K`) and select "Create Volume"
2. Connect the volume to your service
3. Set the mount path to `/app/data`
4. Add environment variable: `DATA_DIR=/app/data`
5. Redeploy

Your `monitored_guilds.json` will now persist across restarts.

### Fly.io

```bash
fly launch
fly secrets set DISCORD_TOKEN=your_token_here NOTIFICATION_CHANNEL_ID=your_channel_id
fly deploy
```

## Project Structure

```
.
├── discord_welcome_bot/
│   ├── __init__.py      # Package init
│   ├── bot.py           # Bot class with events and commands
│   ├── config.py        # Pydantic settings configuration
│   └── main.py          # Entry point
├── Dockerfile           # Multi-stage Docker build with uv
├── docker-compose.yml   # Docker Compose configuration
├── pyproject.toml       # Project configuration
├── uv.lock              # Locked dependencies
└── README.md
```

## How It Works

1. Bot connects to Discord using your user token
2. Notifications are sent to your configured group DM
3. By default, NO servers are monitored (opt-in)
4. Use `!monitor <guild_id>` to start monitoring a server
5. Use `!unmonitor <guild_id>` to stop monitoring
6. Monitored server list is persisted to `monitored_guilds.json`

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
