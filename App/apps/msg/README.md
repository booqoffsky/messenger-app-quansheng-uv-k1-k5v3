# GMessenger

A radio-to-radio text messenger for the Labs overlay-apps platform. It uses
the GGM2 v2 packet format used by [GOGUFW](https://github.com/Gogu-Qs/GOGUFW-UV-K1-Messenger).

## Usage

Install `GMessenger.app` through [UV Studio](https://armel.github.io/uvstudio/#apps), using a build that
matches the firmware release installed on the radio. The app appears as
`GMessenger` in the Apps menu.

Set your callsign in the radio's first boot-message line, exposed as
*Message Line 1* in CHIRP. Use the firmware-specific CHIRP driver supplied
with the release. The app uses up to eight characters and falls back to
`UVK1` if the line is empty.

Messages are sent on the current VFO and can contain up to 36 characters.
All outgoing text messages are broadcasts (`ALL`), including messages
composed from the read screen. The app receives while open and keeps the
six most recent messages in RAM. Closing the app clears the inbox; the
next message ID is saved between sessions.

### Controls

| Screen | Key | Action |
| --- | --- | --- |
| Inbox | `UP` / `DOWN` | Select a message |
| Inbox | `MENU` | Open the selected message |
| Inbox | `F` | Compose a new message |
| Inbox | `EXIT` | Close the app |
| Read | `F` | Compose a new broadcast |
| Read | `EXIT` / `MENU` | Return to the inbox |
| Compose | `0`–`9` | Enter text using multi-tap input |
| Compose | `*` | Switch between `ABC`, `abc`, and `123` |
| Compose | `F` | Delete the character before the cursor |
| Compose | `UP` / `DOWN` | Move the cursor |
| Compose | `MENU` / `PTT` | Send |
| Compose | `EXIT` | Cancel and return to the inbox |

### Delivery status

After transmission, `SENT` changes to `ACK:<call>` when a matching
acknowledgement arrives, or to `NO ACK` when the wait expires. The nominal
wait is six seconds; blocking transmit and alert operations can extend it.
An ACK confirms receipt by the named station. It does not confirm that all
stations received the broadcast.

There is no automatic text retry. To resend after `NO ACK`, press `MENU`.
While the text is unedited, the resend keeps the message ID: the receiver
acknowledges the duplicate again without a second inbox entry. Editing the
text, or resending after `ACK`, uses a new message ID and may appear as a
separate message at the receiver.

## Build

Run these commands from the full project checkout:

```sh
./build.sh
```

## Protocol

The packet layout follows the
[GOGUFW messenger](https://github.com/Gogu-Qs/GOGUFW-UV-K1-Messenger)
implementation in version 3.1.1: magic `GGM2`, packet version `2`.
The app handles TEXT, ACK, and WAKE packets. PING and PONG (Range Check)
are ignored.

### Frame layout

Each transmission contains 50 FSK words (100 bytes):

| Words | Content |
| --- | --- |
| 0 | Start marker: `0xABCD` |
| 1–47 | 94-byte GGFW packet, packed as little-endian byte pairs |
| 48 | CRC-16 of the 94 packet bytes |
| 49 | End marker: `0xDCBA` |

The receive parser searches for the start marker and validates the packet
header, type, payload length, and internal CRC. It accepts a packet at a
small word offset and does not validate the frame's trailing CRC or end
marker.

### Packet layout

| Byte offset | Size | Field |
| --- | --- | --- |
| 0 | 4 | Magic: `GGM2` |
| 4 | 1 | Version: `2` |
| 5 | 1 | Type: `1` TEXT, `2` ACK, `3` PING, `4` PONG, `5` WAKE |
| 6 | 1 | Reserved flags; sent as `0` |
| 7 | 2 | Message ID, little-endian |
| 9 | 1 | Initial TTL; sent as `1` |
| 10 | 1 | Remaining TTL; sent as `1` |
| 11 | 8 | Sender callsign, NUL-padded if shorter than eight bytes |
| 19 | 8 | Recipient callsign, NUL-padded if shorter than eight bytes; `ALL` for broadcast |
| 27 | 1 | Payload length, 0–36 bytes |
| 28 | 36 | Payload, zero-padded |
| 64 | 28 | Zero padding |
| 92 | 2 | CRC-16-CCITT of bytes 0–91, little-endian |

Both software CRCs use polynomial `0x1021` and initial value `0xFFFF`.
ACK packets carry the acknowledged message ID in both the header and the
two-byte payload. Incoming ACKs are matched by header ID and recipient.

### Message exchange

- Sending transmits a WAKE frame, waits 100 ms, then transmits TEXT.
- Non-empty TEXT packets addressed to `ALL` or the local callsign are
  accepted. Other recipients are ignored.
- Duplicate detection compares the sender and ID with the last accepted
  text message. A duplicate is acknowledged again without another inbox
  entry or alert. Older duplicates can reappear after an intervening message.
- An ACK is scheduled after a random delay of 80–207 main-loop ticks
  (nominally 0.8–2.07 seconds). A new accepted TEXT replaces any pending ACK.
- The ACK is a single frame. A lost ACK is recovered by the sender resending
  the unchanged text under the same ID, which the duplicate check above
  acknowledges again. If the radio cannot transmit at that moment, the ACK is
  silently dropped; the sender's resend recovers it.
- A matching ACK ends the current delivery wait. Only the first matching
  acknowledgement is shown.
