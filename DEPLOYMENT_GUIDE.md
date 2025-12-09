# Deployment Guide: Dusk Game Client with Tailscale and Vercel

This guide provides a step-by-step process for deploying the Dusk game client, which uses a hybrid architecture consisting of a static frontend on Vercel, a serverless backend API on Vercel, and a self-hosted game server connected via Tailscale.

## Table of Contents

1.  [Tailscale Configuration](#1-tailscale-configuration)
    - [Create an OAuth Client](#a-create-an-oauth-client)
    - [Define Access Control Lists (ACLs)](#b-define-access-control-lists-acls)
    - [Tag the Game Server](#c-tag-the-game-server)
2.  [Vercel Project Setup](#2-vercel-project-setup)
    - [Create the Vercel Project](#a-create-the-vercel-project)
    - [Set Environment Variables](#b-set-environment-variables)
    - [`vercel.json` Configuration](#c-verceljson-configuration)
3.  [Self-Hosted Game Server Setup](#3-self-hosted-game-server-setup)
    - [Run the Game Server](#a-run-the-game-server)
    - [Run the WebSocket Proxy](#b-run-the-websocket-proxy)
    - [Connect the Server to the Tailnet](#c-connect-the-server-to-the-tailnet)

---

## 1. Tailscale Configuration

Tailscale is used to create a secure private network, allowing the in-browser client to connect to your self-hosted game server without exposing it to the public internet.

### a. Create an OAuth Client

The backend API requires an OAuth client to generate ephemeral keys for the game client.

1.  Navigate to the **Settings > OAuth clients** section of your Tailscale admin console.
2.  Click **"Generate OAuth client..."**
3.  Give the client a descriptive name (e.g., "Dusk Game Client").
4.  Grant the `tags:write` scope to the client. This allows the API to create and manage ephemeral keys with the `tag:game-client` tag.
5.  Save the generated **Client ID** and **Client Secret**. These will be used as environment variables in your Vercel project.

### b. Define Access Control Lists (ACLs)

ACLs enforce a strict security model, ensuring that only authenticated game clients can access the game server.

1.  Go to the **Access Controls** page in your Tailscale admin console.
2.  Replace the existing policy with the following JSON:

    ```json
    {
      "tagOwners": {
        "tag:game-server": ["<your-tailscale-email>"],
        "tag:game-client": ["<your-tailscale-email>"]
      },
      "acls": [
        {
          "action": "accept",
          "src":    ["tag:game-client"],
          "dst":    ["tag:game-server:8081"]
        }
      ]
    }
    ```

    **Note:** Replace `<your-tailscale-email>` with the email address you use for Tailscale.

### c. Tag the Game Server

The machine that will run the game server must be tagged appropriately.

1.  In the **Machines** list of your Tailscale admin console, find the server you intend to use.
2.  Disable key expiry for this machine to ensure it remains connected.
3.  Apply the `tag:game-server` tag to the machine.

## 2. Vercel Project Setup

### a. Create the Vercel Project

1.  Create a new project in your Vercel dashboard, linked to your Git repository.
2.  Vercel will likely detect a Python backend and may not require extensive configuration initially.

### b. Set Environment Variables

In the Vercel project settings (**Settings > Environment Variables**), add the following:

-   `TS_OAUTH_CLIENT_ID`: The Client ID from your Tailscale OAuth client.
-   `TS_OAUTH_CLIENT_SECRET`: The Client Secret from your Tailscale OAuth client.
-   `TS_TAILNET`: Your Tailscale network name (e.g., `example.com.beta.tailscale.net`).

### c. `vercel.json` Configuration

The `vercel.json` file in the root of the repository is crucial for routing and builds. It should be configured as follows:

```json
{
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    },
    {
      "src": "public/**",
      "use": "@vercel/static"
    }
  ],
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "/api/index.py"
    },
    {
      "source": "/(.*)",
      "destination": "/public/index.html"
    }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "Access-Control-Allow-Origin", "value": "*" },
        { "key": "Cross-Origin-Opener-Policy", "value": "same-origin" },
        { "key": "Cross-Origin-Embedder-Policy", "value": "require-corp" }
      ]
    }
  ]
}
```

This configuration tells Vercel how to build the Python serverless function and the static frontend, and how to route requests.

## 3. Self-Hosted Game Server Setup

This section details how to set up the game server on the machine you previously tagged as `tag:game-server` in the Tailscale admin console.

### a. Prerequisites

Before running the server, ensure the following software is installed on your server machine:

-   **Java:** Required to run the `DuskServer`.
-   **Node.js and npm:** Required to run the `websockify` proxy via `npx`.
-   **Tailscale:** Must be installed and configured on the server.

### b. Run the Game Server

The core game server is a Java application. To start it, navigate to the directory containing the server files and run the following command:

```bash
java -cp . DuskServer &
```

-   `java -cp . DuskServer`: This command starts the Java Virtual Machine, tells it to look for classes in the current directory (`-cp .`), and specifies `DuskServer` as the main class to run.
-   `&`: This runs the process in the background, so you can continue to use the terminal.

This will start the server, which listens for direct TCP connections on port `7474`.

### c. Run the WebSocket Proxy

Since the in-browser client connects using WebSockets, a proxy is needed to translate these connections to the TCP protocol used by the game server.

```bash
npx @teampanfu/websockify 8081 127.0.0.1:7474 &
```

-   `npx @teampanfu/websockify`: This command uses `npx` to run the `websockify` package without needing a global installation.
-   `8081`: This is the public-facing port that will listen for incoming WebSocket connections from the game client.
-   `127.0.0.1:7474`: This is the target address of the local game server. The proxy will forward all traffic to this address.
-   `&`: This also runs the proxy in the background.

This command listens for WebSocket connections on port `8081` and forwards them to the game server on port `7474`. This is the port your Tailscale ACLs should be configured to allow.

### d. Connect the Server to the Tailnet

Finally, ensure the Tailscale client is running and connected. This makes the server part of your private network and allows it to be reached by the game client via its Tailscale IP.

```bash
sudo tailscale up
```

-   `sudo tailscale up`: This command connects your server to your Tailnet. Once connected, the WebSocket proxy on port `8081` becomes accessible to other authorized devices on the network, such as the game client.
