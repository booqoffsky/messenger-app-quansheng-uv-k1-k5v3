# AMessenger

An AFSK radio-to-radio text messenger for the Labs overlay-apps platform:
text messages carried in AX.25 UI frames, Bell 202 AFSK at 1200 bauds.

## Usage

Install `AMessenger.app` via [UV Studio](https://armel.github.io/uvstudio/#apps). Requires firmware v6.3.0+ (API level 3 for PA4 audio capture). Once installed, it appears in the Apps menu.

Set your callsign in CHIRP (*Message Line 1*). The app uses up to 6 uppercase alphanumeric characters (AX.25 width) and falls back to `UVK1` otherwise. Tune the VFO to **FM** on a shared simplex channel.

Messages are sent on the current VFO (up to 36 characters). New messages from the inbox are broadcasts (`ALL`); pressing `F` on an open message replies directly to the sender (`TO <call>`). The app receives in the background while open, storing the 6 most recent messages in RAM. Closing the app clears the inbox, but the next message ID is persisted.

### Controls

| Screen | Key | Action |
| --- | --- | --- |
| Inbox | `UP` / `DOWN` | Select a message |
| Inbox | `MENU` | Open the selected message |
| Inbox | `F` | Compose a new message |
| Inbox | `EXIT` | Close the app |
| Read | `F` | Reply to the sender (directed) |
| Read | `EXIT` / `MENU` | Return to the inbox |
| Compose | `0`–`9` | Enter text using multi-tap (append only) |
| Compose | `*` | Switch between `ABC` and `123` |
| Compose | `F` | Delete the last character |
| Compose | `MENU` / `PTT` | Send |
| Compose | `EXIT` | Cancel and return to the inbox |

Optimized for a 4 KiB overlay: no lowercase, append-only text, and no title. `TX DENIED` is shown if transmission fails (low battery or TX disabled).

### Delivery status

After transmission, the status line shows `SENT`, followed by `ACK:<call>` upon receipt, or `NO ACK` after a 6-second timeout. An ACK confirms receipt by that specific station, not the whole network.

No automatic retries. Press `MENU` to resend after `NO ACK`. Unedited text retains the message ID, allowing the recipient to ACK the duplicate without creating a new inbox entry. Editing or resending after an `ACK` generates a new ID.

UI updates and key handling run between frames. The UI pauses briefly (<1s) during frame reception. Channel noise does not lock the UI; only back-to-back HDLC flags (preambles) will temporarily hold inputs.

## Build

```sh
build.sh
```


## Protocol

Standard AX.25 transport, custom payload. The physical layer is Bell 202
AFSK at 1200 bauds (1200/2200 Hz tones, NRZI, HDLC flags and bit stuffing,
CRC-16/X.25): sent via BK4829 tone generator (MCW-keyed).

### Frame layout

AX.25 UI frame, no digipeaters, SSID 0 everywhere:

| Offset | Size | Field |
| --- | --- | --- |
| 0 | 7 | Destination: 6 chars shifted left, SSID byte `0x60`; `ALL` for a broadcast, the call for a reply |
| 7 | 7 | Source: sender's call, SSID byte `0x61` (address-field end bit) |
| 14 | 1 | Control `0x03` (UI) |
| 15 | 1 | PID `0xF0` |
| 16 | 6+ | Payload (below) |
| — | 2 | CRC-16/X.25 over the frame, little-endian |

A full 36-character TEXT is 60 bytes (50 without text), about 0.5 s on the
air between the 16 lead flags and 2 tail flags.

### Payload

| Offset | Size | Field |
| --- | --- | --- |
| 0 | 2 | Magic: `AM` |
| 2 | 1 | Version: `1` |
| 3 | 1 | Type: `1` TEXT, `2` ACK |
| 4 | 2 | Message ID, little-endian |
| 6 | 0–36 | Text (TEXT only) |

The receive path accepts only frames of this protocol: HDLC/FCS/UI checks
first, then the address-field end bit, control, PID and magic.

### Message exchange

- A TEXT addressed to `ALL` or to the local call is accepted; other
  recipients are ignored. A directed reply is therefore stored and
  acknowledged only by the station it names - other stations still see
  the frame on any AX.25 monitor.
- Duplicate detection compares the sender address and the ID with the last
  accepted text. A duplicate is acknowledged again without another inbox
  entry or alert.
- An ACK is scheduled after a random delay of 16–47 housekeeping slots
  (nominally 0.8–2.35 seconds after the frame). A new accepted TEXT replaces
  any pending ACK.
- The ACK is a single frame addressed to the TEXT sender. If the radio
  cannot transmit at that moment, the ACK is silently dropped; the sender's
  same-ID resend recovers it.
- A matching ACK (right ID, addressed to us) ends the current delivery
  wait. Only the first matching acknowledgement is shown.