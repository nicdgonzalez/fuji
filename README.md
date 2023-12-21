# Fuji

## Introduction

**Fuji** is a command-line tool for managing Minecraft servers.

This project was built to demonstrate how [clap](../../../clap) works.

> [!NOTE]
> Fuji uses [PaperMC](https://papermc.io/) for the server backend.

## Getting Started

### Requirements

* Java 17.0+
* tmux 3.2+
* Python 3.8+

### Installation

This project is not available on PyPI, so you need to install it locally:

```bash
git clone https://github.com/nicdgonzalez/fuji && cd ./fuji
python -m pip install -U .
```

The `fuji` command should now be available; verify by running:

```console
$ fuji -V
Fuji vX.Y.Z
```

Next, run the following command to initialize Fuji. By default, all
Fuji-related files will be stored in `$HOME/.fuji`.

```bash
fuji init
# or
fuji init ./target/path
```

Now run `fuji --help` to view the full list of available commands.

### Quickstart

#### Important Safety Information

Fuji will **not** make any alterations to your network configuration.
The following example demonstrates the initiation of a new Minecraft server
exclusively for LAN players.

If you intend to allow players from outside your network to join,
please follow these steps carefully:

1. **Research Port Forwarding:**
Understand the concept of port forwarding. Log in to your router settings
and create a port forwarding rule for the Minecraft server's port
(default is 25565). This allows external connections to reach your server
through the specified port.

1. **Find Your External IP Address:**
Discover your network's external IP address. Players from outside your local
network will use this address to connect to your server.

1. **Configure Firewall Settings:**
Adjust your firewall settings to permit inbound connections on the port
you've specified for Minecraft. This is crucial for allowing external
players to connect while maintaining security.

1. **Update Minecraft Server Properties:**
Open the server.properties file in your Minecraft server directory and ensure
that the server-ip property is either blank or set to your internal
network IP. This ensures that the server listens for connections on all
available network interfaces.

> [!IMPORTANT]
> Always prioritize the security of your network. Failure to properly configure
> these settings may expose your system to potential risks. If you are
> uncertain about any aspect, seek guidance from reliable sources or consult
> with a network security professional.

#### Example Server

Now, here is how to create a new Minecraft server and run it:

```bash
git clone https://github.com/nicdgonzalez/fuji
cd ./fuji
fuji init
fuji create "test" --accept-eula
fuji start "test" --auto-reconnect
```
