#!/usr/bin/env python3
# AMSG read-only assets: the UI texts, the multi-tap keymap, and the APRS RX
# demodulator tables (dem_t initial state, then the 1200 Hz and 2200 Hz
# correlator cosine tables).
#
#   ./gen_assets.py amsg_assets.bin amsg_assets.h
import math, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from app_assets import Assets

a = Assets("AMSG")

a.text("T_EMPTY", "Inbox empty")
a.text("T_HINT_LIST", "F:NEW M:READ")
a.text("T_HINT_READ", "F:REPLY EXIT:BACK")
a.text("T_HINT_EDIT", "F:DEL *:MODE M:SEND")
# Indexed by status - 1 (ST_* order); the ST_ACK entry gets the sender appended.
a.table("T_STATE", ["SENT", "ACK:", "NO ACK", "TX DENIED"])
a.table("T_MODE", ["ABC", "123"])           # stride 4, indexed by mode * 4
a.const("T_TITLE_CHARS", 4)

KEYS = [" ", ".,?!", "ABC", "DEF", "GHI", "JKL", "MNO", "PQRS", "TUV", "WXYZ"]
a.raw("KEYMAP", b"".join(v.encode("ascii").ljust(5, b"\0") for v in KEYS))
a.const("KEYMAP_STRIDE", 5)

FS = 9600

def cos_table(f):
    per = FS // math.gcd(FS, f)
    return [int(round(127 * math.cos(2 * math.pi * f * n / FS))) for n in range(per)]

# dem_t prefix: dc, eight filter/correlator words, pm/ps, r/ks, ring.  Append
# the cosine tables so one read initializes the entire front end (as APRS RX).
a.u32("DEMOD_INIT", [2048 << 4] + [0] * 8 + [64, 64] + [0] * 18)
a.i8("COS1200", cos_table(1200))           # 8 entries
a.i8("COS2200", cos_table(2200))           # 48 entries
a.main()
