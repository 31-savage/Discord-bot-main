# Build stage with uv
FROM ghcr.io/astral-sh/uv:python3.13-alpine AS builder

WORKDIR /app

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (no dev dependencies)
RUN uv sync --frozen --no-install-project --no-dev

# Copy source code
COPY discord_welcome_bot ./discord_welcome_bot

# Install the project itself
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.13-alpine AS production

# Add non-root user for security
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy the source code
COPY --from=builder /app/discord_welcome_bot ./discord_welcome_bot

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

USER appuser

CMD ["python", "-m", "discord_welcome_bot.main"]
