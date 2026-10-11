from __future__ import annotations
import re
from typing import Any, Dict
from ..utils import first_match

class DarshanDXTSource:
    def parse(self, text: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if not text:
            return out

        blocks = re.split(r"(?=# DXT, file_id:)", text)
        candidates = []

        for block in blocks:
            if "# DXT, file_id:" not in block:
                continue

            file_name = first_match(block, [r"# DXT, file_id:.*?file_name:\s*(.+)"])
            mount_point = first_match(block, [r"# DXT, mnt_pt:\s*(.+)"])
            fs_type = first_match(block, [r"# DXT, .*?fs_type:\s*([^\s]+)"])
            stripe_size = first_match(block, [r"# DXT, Lustre stripe_size:\s*(\d+)"])
            stripe_count = first_match(block, [r"# DXT, Lustre stripe_count:\s*(\d+)"])
            read_count = first_match(block, [r"# DXT, write_count:\s*\d+,\s*read_count:\s*(\d+)"])
            write_count = first_match(block, [r"# DXT, write_count:\s*(\d+),\s*read_count:"])

            lname = file_name.lower()
            score = 0
            if any(ext in lname for ext in (".h5", ".hdf5", ".npz", ".tfrecord", ".jpg", ".jpeg", ".png", ".bin")):
                score += 10
            if "__pycache__" in lname or lname.endswith(".py"):
                score -= 10

            candidates.append((score, {
                "mount_point": mount_point,
                "filesystem": fs_type,
                "stripe_size_bytes": int(stripe_size) if stripe_size else None,
                "stripe_count": int(stripe_count) if stripe_count else None,
                "data_file": file_name,
                "read_ops": int(read_count) if read_count else None,
                "write_ops": int(write_count) if write_count else None,
            }))

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            out.update({k: v for k, v in candidates[0][1].items() if v not in ("", None)})

        # Sum DXT read/write counts only for dataset-like files
        total_reads = 0
        total_writes = 0
        found = False
        for _, meta in candidates:
            fname = (meta.get("data_file") or "").lower()
            if any(ext in fname for ext in (".h5", ".hdf5", ".npz", ".tfrecord", ".jpg", ".jpeg", ".png", ".bin")):
                if meta.get("read_ops") is not None:
                    total_reads += meta["read_ops"]
                    found = True
                if meta.get("write_ops") is not None:
                    total_writes += meta["write_ops"]
                    found = True
        if found:
            out["read_ops"] = total_reads
            out["write_ops"] = total_writes

        return out
