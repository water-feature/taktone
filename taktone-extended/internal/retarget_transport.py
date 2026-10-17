"""Address a DN-hardware hybrid update to the running DT application's SysEx.

Changes only outer transport framing/checksums. The ELE3 container and every
firmware section remain identical to the already-qualified candidate.
"""
from metadata_paths import json_path
import json
import struct

from panel_patch import ROOT, syx, DEV
from elekloader.codec import transport


def rewrap(source, envelope):
    stream = struct.pack('>II', source.total, source.checksum) + source.container
    return transport.encode_syx(stream, envelope.device_id,
        envelope.framing[0], envelope.framing[1])
