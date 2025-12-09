# Secure Zero Trust Game Server Setup Guide

This document outlines the complete process for setting up a secure, private game server using a Zero Trust architecture. The setup leverages Tailscale for secure networking, Vercel for hosting the web client and a serverless API, and CheerPJ to run the Java-based game client in the browser.

This architecture ensures the game server is completely invisible to the public internet, dramatically reducing its attack surface and protecting it from common threats like DDoS attacks and vulnerability scanning.

## Table of Contents

1.  [Architectural Overview](#architectural-overview)
2.  [Prerequisites](#prerequisites)
3.  [Step 1: Configure the Game Server Machine](#step-1-configure-the-game-server-machine)
4.  [Step 2: Create a Tailscale OAuth Client](#step-2-create-a-tailscale-oauth-client)
5.  [Step 3: Define the Tailscale ACL Policy](#step-3-define-the-tailscale-acl-policy)
6.  [Step 4: Assign the Server Tag](#step-4-assign-the-server-tag)
7.  [Step 5: Configure and Deploy the Vercel Project](#step-5-configure-and-deploy-the-vercel-project)
8.  [Final Verification Checklist](#final-verification-checklist)

---

## Architectural Overview

The system works as follows:

1.  A player visits the game website hosted on Vercel.
2.  The CheerPJ client loads and requests a connection key from a serverless API endpoint, also on Vercel.
3.  The Vercel API, using a secure OAuth client, asks the Tailscale API to generate a temporary, single-use authentication key. This key is tagged specifically for game clients.
4.  The Vercel API sends this key back to the player's browser.
5.  The player's browser uses the key to join your private Tailscale network (your "tailnet").
6.  Tailscale's Access Control Lists (ACLs) immediately see the client's tag and enforce a strict rule: the client can *only* communicate with the machine tagged as the game server, and only on its specific game port. All other traffic is blocked.
7.  A secure, end-to-end encrypted connection is established, and the player can play the game.

---

## Prerequisites

-   A **Tailscale account**.
-   A **Vercel account** connected to a fork of this GitHub repository.
-   A dedicated machine or Virtual Machine (VM) to run the game server.
-   The game server software and the web client files (`duskclient.jar`, etc.).

---

## Step 1: Configure the Game Server Machine

1.  **Install Tailscale:** On the machine or VM that will host your game server, install the Tailscale client by following the instructions for your operating system from the [Tailscale downloads page](https://tailscale.com/download).
2.  **Authenticate:** Run `sudo tailscale up` (or the equivalent for your OS) to authenticate and connect the machine to your tailnet.
3.  **Disable Key Expiry (Recommended):** For servers, it's best to prevent the machine from needing to be re-authenticated.
    -   Go to the [**Machines** page](https://login.tailscale.com/admin/machines) in the Tailscale admin console.
    -   Find your server machine, click the `...` menu, and select "Disable key expiry...".

---

## Step 2: Create a Tailscale OAuth Client

This client will allow our Vercel API to generate keys without needing your personal login credentials. We will strictly limit its permissions for maximum security.

1.  Go to the [**Keys** page](https://login.tailscale.com/admin/settings/keys) in your Tailscale admin console.
2.  Under "OAuth clients", click **"Generate new client..."**.
3.  **Edit Scopes:** This is the most critical security step. Click **"Customize scopes..."**.
    -   Turn **OFF** all scopes.
    -   Find the **"Auth Keys"** scope and enable it.
    -   Click the pencil icon to edit the "Keys" scope permission.
    -   Ensure only **"Write"** is checked. Uncheck "Read". This enforces the **Principle of Least Privilege**—the client can only create keys, which is its sole job. For me only option is both read/write but you also need to add the "game-client" tag here which means come back and add it after step 3.
4.  Click **"Generate client..."**.
5.  You will be shown a **Client ID** and a **Client Secret**. Copy both of these immediately and save them somewhere secure (like a password manager). You will need them for the Vercel setup. **You will not be able to see the Client Secret again.**

---

## Step 3: Define the Tailscale ACL Policy

The ACL policy acts as the firewall for your private network. This policy will create the necessary tags and define the rule that allows game clients to connect to the game server.

1.  Go to the [**Access Controls** page](https://login.tailscale.com/admin/acls).
2.  **Delete all existing content** in the policy editor.
3.  **Copy and paste** the following JSON policy.

    ```json
    {
      // This section defines who is allowed to assign these tags to machines.
      // Replace the email with your own Tailscale login email.
      "tagOwners": {
        "tag:game-server": ["your-email@example.com"],
        "tag:game-client": ["your-email@example.com"]
      },

      // This section defines the firewall rules.
      "acls": [
        {
          "action": "accept",
          "src":    ["tag:game-client"],
          // IMPORTANT: Change 2222 to your game's actual port!
          "dst":    ["tag:game-server:2222"]
        }
      ],
      
      // Optional: Add tests to verify your ACLs work as expected.
      "tests": [
        {
          "src": "tag:game-client",
          "accept": ["tag:game-server:2222"],
          "deny": ["tag:game-server:22", "autogroup:members"]
        }
      ]
    }
    ```

4.  **Crucial:**
    -   Replace `your-email@example.com` with the email you use to log into Tailscale.
    -   In the `"dst"` line, replace `2222` with the **actual port your game server listens on**.
5.  Click **"Save"**.

---

## Step 4: Assign the Server Tag

Now that the `tag:game-server` has been created in the ACL policy, you can assign it to your server machine.

1.  Go to the [**Machines** page](https://login.tailscale.com/admin/machines).
2.  Find your game server machine and click the `...` menu.
3.  Select **"Edit ACL tags..."**.
4.  The `game-server` tag should be available in the list. Check the box next to it and click **"Save"**.

Your server is now correctly tagged and protected by the ACL policy.

---

## Step 5: Configure and Deploy the Vercel Project

1.  **Fork the Repository:** Make sure you have a fork of this project's repository in your GitHub account.
2.  **Create a Vercel Project:**
    -   Log in to Vercel and go to your Dashboard.
    -   Click "Add New... -> Project".
    -   Import the forked GitHub repository.
3.  **Configure Environment Variables:** In the project settings, navigate to "Settings -> Environment Variables". Add the following, using the credentials you saved earlier:
    -   `TS_OAUTH_CLIENT_ID`: The Client ID from Step 2.
    -   `TS_OAUTH_CLIENT_SECRET`: The Client Secret from Step 2.
    -   `TS_TAILNET`: Your tailnet name. You can find this on the [**Settings** page](https://login.tailscale.com/admin/settings/general) in the Tailscale admin console (e.g., `example.ts.net`).
4.  **Deploy:** Trigger a deployment of the `main` branch. Vercel will build the project and deploy the serverless API.

---

## Final Verification Checklist

1.  [ ] Tailscale is installed and running on the game server machine.
2.  [ ] The game server machine's key expiry is disabled.
3.  [ ] The Tailscale OAuth client exists and has **only** the "Keys (Write)" scope.
4.  [ ] The ACL policy is saved and contains the correct `tagOwners` and `acls` rules.
5.  [ ] The game server port in the ACL policy is correct.
6.  [ ] The game server machine is tagged with `tag:game-server`.
7.  [ ] The Vercel project's environment variables (`TS_OAUTH_CLIENT_ID`, `TS_OAUTH_CLIENT_SECRET`, `TS_TAILNET`) are set correctly.
8.  [ ] The game server software is running on your server machine.
9.  [ ] You can successfully connect to the game by visiting your Vercel deployment URL.
