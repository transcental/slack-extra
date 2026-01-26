# Slack++

Slack. Enhanced.

## Prerequisites

- Python (3.13 or later)
- uv
- A Slack workspace where you have permissions to install apps
- Tunneling tool (for local development)

## Setting up the Slack App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps) and click "Create New App".
2. Choose "From an app manifest" and select your workspace.
3. Copy and paste the manifest in `manifest.yml`, replacing `YOUR_URL` with your URL (we'll set this up later). Also change the command to be `/your-name-se` (ie: `/amber-se`) instead of `/dev-se` (You will need to change this in `register_commands()` in `commands/__init__.py` too):
4. Review and create the app.
5. In the "Basic Information" section, note down the `App Id`, `Client Id`, `Client Secret`, `Signing Secret` .
6. Go to "OAuth & Permissions" and install the app to your workspace. Note down the "Bot User OAuth Token".

## Setting up the Project

1. Clone the repository:

   ```
   git clone https://github.com/your-repo/slack-plus-plus.git
   cd slack-plus-plus
   ```

2. Install dependencies:

   ```
   uv sync
   source .venv/bin/activate # for bash/zsh
   source .venv/bin/activate.fish # for fish
   source .venv/bin/activate.csh # for csh
   source .venv/bin/activate.ps1 # for powershell
   ```

3. Copy the `.env.sample` file to `.env`:

   ```
   cp .env.sample .env
   ```

4. Edit the `.env` file and fill in the values:

   ```
   PORT=3000
   ENVIRONMENT="development"
   
   SLACK_BOT_TOKEN="bot-token"
   SLACK_SIGNING_SECRET="signing-secret"
   SLACK_APP_TOKEN="app-token" # This is optional - recommended to use socket mode in dev because it allows you to run the app locally without needing to tunnel. Not recommended for production.

   SLACK_HEARTBEAT_CHANNEL="channel-id"
   ```

   Replace the values with your actual parameters.


## Running the Application

1. Start your tunneling tool and expose the local server. (Not needed in socket mode with `SLACK_APP_TOKEN` set)

   Note the HTTPS URL you get.

2. Update your Slack app's request URLs:

   - Go to your Slack app's settings.
   - In "Event Subscriptions" and "Interactivity & Shortcuts", update the request URL to your HTTPS URL followed by `/slack/events`.
   - In "OAuth & Permissions", update `Redirect URLs` to your HTTPS URL followed by `/slack/oauth_redirect`.

3. Start the application:
   ```
   slack_extra
   ```

Your Slack app should now be running and connected to your Slack workspace!

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
