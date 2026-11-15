#!/usr/bin/env python3
"""Bring the loopback interface up without iproute2 (SIOCSIFFLAGS)."""
import fcntl, socket, struct
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
name = b"lo"
flags = struct.unpack("16sh", fcntl.ioctl(s, 0x8913, struct.pack("16sh", name, 0)))[1]
fcntl.ioctl(s, 0x8914, struct.pack("16sh", name, flags | 0x1))
