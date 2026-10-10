# DVBViewer Media Server for Home Assistant

Unofficial custom integration for local DVBViewer Media Server instances.

## Independence and trademarks

This project is an independent, community-maintained integration. It is not
affiliated with, endorsed by, sponsored by, or supported by CM&V / DVBViewer,
the Open Home Foundation, or Home Assistant.

`DVBViewer` and `DVBViewer Media Server` are used only to identify the
third-party software this integration interoperates with. They may be
trademarks of their respective owners. This repository contains no DVBViewer
or DVBViewer Media Server binaries, source code, logos, screenshots, license
keys, recordings, channel lists, or other proprietary assets.

## Current scope

The first release provides a native device with:

- connectivity;
- service status (`idle` / `recording`);
- server version;
- next recording with timer details;
- current recording with timer details;
- timer count;
- recording-file count.
- recording archive count and privacy-minimised recent recording metadata;
- channel/subchannel count and tuner/stream diagnostics.

The integration reads DMS through read-only endpoints: `status2.html`, `timerlist.html`, `recordings.html`, `getchannelsxml.html` and `version.html`. It does not create, edit or delete timers and does not control the VideoREC PC.

When `videorec_url` is configured, the integration can ask VideoREC to verify
recording files through its read-only `recordings/verify` endpoint. The result
is used only when VideoREC reports `available=true`; the unreliable DMS
duration field is never treated as authoritative. If VideoREC is unavailable,
DMS monitoring continues unchanged.

### Future VideoREC verification contract

This optional feature is **disabled by default** and is intended for a separate
future VideoREC package and test environment. It does not alter the current
Home Assistant production configuration, DMS operation or shutdown automation.

The component calls `GET /api/v1/recordings/verify?fileName=<name>` only with
a plain file name extracted from the DMS archive. It never sends a directory or
path. A result is published only when VideoREC returns all of the following:

- `available: true`;
- the same `fileName` requested;
- a finite `verifiedDurationSeconds` greater than zero;
- `durationSource: "ffprobe"`.

The component checks at most three newly discovered archive records per update
(only the newest record after a component restart). This avoids probing a
historical archive. A missing file, a file still being written, a timeout,
malformed response or unavailable VideoREC endpoint is not a successful
verification and does not make DMS unavailable. Successful metadata is retained
only for the current archive record; archive presence by itself is never proof
that a recording completed correctly.

Users must obtain, install, configure, and license DVBViewer Media Server
separately from its rights holder. Do not upload DMS installers, support ZIPs,
recordings, credentials, or personalized configuration exports to this
repository or its issue tracker.

## Installation through HACS

Add this repository as a custom repository in HACS, category **Integration**, then install **DVBViewer Media Server** and restart Home Assistant. Add it from **Settings → Devices & services → Add integration**.

The repository is intended to be published at `https://github.com/vracioppi/ha-dvbviewer-dms`.

At this stage it is designed for installation as a **custom HACS repository**.
It is deliberately not presented as an official DVBViewer integration and it
does not ship DVBViewer brand assets. Inclusion in the default HACS catalogue
will be considered separately after the trademark and brand-asset position is
clear.

## Configuration

- Host: the computer running DMS
- Port: normally `8089`
- Optional HTTP Basic Authentication credentials
- Optional VideoREC URL for the future ffprobe verification feature; leave empty
  in the current production installation.

The integration contacts only the configured local server using the Home
Assistant instance's normal network connection. Its diagnostics redact the
password, configured host and recording paths. Before opening a public issue,
always remove personal data from logs manually as well.

## Network prerequisite and Windows Firewall

The PC running DVBViewer Media Server should be connected to a Windows network
classified as **Private**. The integration communicates with the DMS APIs over
the configured TCP port, normally `8089`.

This is not a technical requirement imposed by the custom integration itself:
marking a trusted home LAN as Private is simply the easiest way to ensure that
the applicable Windows Firewall rule permits LAN access to the DMS API. When
the network is classified as **Public**, Windows Firewall can block the API
even though the PC still responds to ping.

As an alternative to using a Private network profile, create an inbound Windows
Firewall rule that permits TCP traffic to the configured DMS port, scoped only
to the local LAN. Also verify that DVBViewer Media Server is actually listening
on that configured port.

From the Home Assistant terminal, or from another device on the same LAN, test
the TCP connection. On a Windows device, run this PowerShell command:

```powershell
Test-NetConnection <IP_DEL_SERVER_DMS> -Port <PORTA_DMS>
```

The configuration is valid only if the result contains:

```text
TcpTestSucceeded : True
```

If ping works but `TcpTestSucceeded` is `False`, check in this order:

1. Windows network profile;
2. Windows Firewall rules;
3. port configured in DVBViewer Media Server;
4. host address and port configured in the custom integration;
5. API credentials or authentication.

Restrict DMS API access to the local LAN. Do not expose the DMS port directly
to the Internet.

## Design boundary

This integration represents DMS. Wake-on-LAN, Windows boot, human usage, keep-awake, safe shutdown, notifications and household automations belong outside this component, in VideoREC and Home Assistant.

## License

The original code in this repository is released under the MIT License. The
license does not grant any right to DVBViewer, DVBViewer Media Server, Home
Assistant, or any other third-party trademark or proprietary software. See
[NOTICE.md](NOTICE.md).

## Known limitation

The recording archive is read from `/api/recordings.html`. The component exposes
its count and limited recording metadata; local recording paths, extended
programme descriptions and the media-server URL are not exposed as entity
attributes. The full archive remains only in the in-memory coordinator.
