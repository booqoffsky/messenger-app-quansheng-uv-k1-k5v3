#!/usr/bin/env python3
# MSG read-only assets: UI texts, the multi-tap keymap and the BK4819 FSK
# register sequences: the GOGUFW Messenger framing (100-byte frames, 16-byte
# TX preamble) at the stock Aircopy 1200 baud, so the app exchanges frames
# with GOGUFW radios without any firmware change.
#
#   ./gen_assets.py msg_assets.bin msg_assets.h
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from app_assets import Assets

a = Assets("MSG")

a.text("T_TITLE", "MSG")
a.text("T_EMPTY", "Inbox empty")
a.text("T_HINT_LIST", "F:NEW M:READ")
a.text("T_HINT_READ", "F:REPLY EXIT:BACK")
a.text("T_HINT_EDIT", "F:DEL *:MODE M:SEND")
a.text("T_RX", " RX ")
# Indexed by status - 1 (ST_* order); the ST_ACK entry gets the sender appended.
a.table("T_STATE", ["SENDING", "SENT", "ACK:", "NO ACK",
                    "TX DENIED", "EMPTY"])
a.table("T_MODE", ["ABC", "abc", "123"])   # stride 4, indexed by mode * 4
a.const("T_TITLE_CHARS", 3)

KEYS = [" ", ".,?!", "ABC", "DEF", "GHI", "JKL", "MNO", "PQRS", "TUV", "WXYZ"]
a.raw("KEYMAP", b"".join(v.encode("ascii").ljust(5, b"\0") for v in KEYS))
a.const("KEYMAP_STRIDE", 5)

# Register sequences: (register, value) word pairs; register SEQ_DELAY means
# "wait value ms".  Each one mirrors the driver routine noted; the TX preamble
# values (0x..F8) are GOGUFW's 16-byte lead-in, the rest match Aircopy.
SEQ_DELAY = 0xFF
a.const("SEQ_DELAY", SEQ_DELAY)

def seq(name, pairs):
    a.u16(name, [w for pair in pairs for w in pair])

RESET = [                       # BK4819_ResetFSK
    (0x3F, 0x0000),             # disable interrupts
    (0x59, 0x0068),             # sync length 4 bytes, 7 byte preamble
    (SEQ_DELAY, 30),
    (0x30, 0x0000),             # BK4819_Idle
]
seq("SEQ_RESET", RESET)
seq("SEQ_MODEM", [              # narrow IF filter + BK4829 BK4819_SetupAircopy
    (0x43, 0x3448),             # 12.5 kHz filter (SetFilterBandwidth NARROW), as
                                # GOGUFW's messenger narrow-lock during FSK
    (0x70, 0x00C3),             # enable Tone2 (BK4829 value; the K5's bk4819
                                # driver uses 0x00E0 — wrong on the UV-K1)
    (0x72, 0x3065),             # Tone2 baudrate 1200
    (0x58, 0x00C1),             # FSK enable, 1.2K RX bandwidth, TX/RX FSK 1.2K
    (0x5C, 0x5665),             # enable CRC
    (0x5D, 0x6300),             # FSK data length 100 bytes (50 words)
    (0x5E, 0x3204),             # BK4829 SetupAircopy writes this too; the
                                # UV-K1's FSK modem does not decode without it
])
#
# REG_43/58/59/5C/5E/70/72 are borrowed from the voice setup and restored by
# the app on exit (saved at launch); the launcher's RADIO_SetupRegisters does
# not rewrite them.
seq("SEQ_RX", RESET + [         # BK4819_PrepareFSKReceive, 100-byte length
    (0x5D, 0x6300),
    (0x02, 0x0000),
    (0x3F, 0x0000),
    (0x37, 0x9F1F),             # BK4819_RX_TurnOn
    (0x30, 0x0000),
    (0x30, 0xBFF1),
    (0x3F, 0x3002),             # FSK RX sync | RX finished | FIFO almost full IRQs
                                # (GOGUFW's FSK IRQ mask: without the RX_SYNC bit
                                # the realign-on-new-frame path never fires)
    (0x59, 0x4068),             # clear RX FIFO
    (0x59, 0x3068),             # FSK RX enable
])
seq("SEQ_TX_LOAD", [            # GOGUFW's long-preamble TX setup, before the FIFO fill
    (SEQ_DELAY, 30),
    (0x3F, 0x8000),             # FSK TX finished interrupt
    (0x5D, 0x6300),
    (0x59, 0x80F8),             # clear TX FIFO, 16-byte preamble
    (0x59, 0x00F8),
])
seq("SEQ_TX_GO", [              # after the FIFO fill
    (SEQ_DELAY, 20),
    (0x59, 0x28F8),             # FSK TX enable
])
seq("SEQ_TX_END", [             # send tail + PA bias off
    (0x02, 0x0000),
    (SEQ_DELAY, 30),
] + RESET + [
    (0x36, 0x0088),             # BK4819_SetupPowerAmplifier(0, 0)
])
a.main()
