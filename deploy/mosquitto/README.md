# deploy/mosquitto/ — the MQTT broker for development

`mosquitto-dev.conf` runs Mosquitto on **localhost:1883 with no password**
(OK for the desktop prototype only), logging every connection to the terminal.

## One-time install (needs sudo)

```bash
sudo apt install mosquitto mosquitto-clients
sudo systemctl disable --now mosquitto   # stop apt's background copy, so ours can use port 1883
```

## How to run it

In its own terminal:

```bash
deploy/mosquitto/run-dev.sh
```

You should see `Opening ipv4 listen socket on port 1883.` Leave it running;
Ctrl+C stops it. If the script says port 1883 is busy, the system service is
probably still running (the script tells you how to stop it).

## Check it works

In a second terminal: `mosquitto_sub -h localhost -t 'monster/#' -v`
In a third: `mosquitto_pub -h localhost -t monster/debug/test -m hello`
The first terminal prints `monster/debug/test hello`.
(Or use the project's own tool: see the root `README.md`.)

## Later stages
From Stage 1 the broker listens on the home network with a username and
password (architecture §3c). That will be a separate config file.
