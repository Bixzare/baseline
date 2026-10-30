"""OneDrive readback via a verified rclone remote; no local substitute or upload."""

import math
import os
import re
import shutil
import subprocess
from pathlib import Path

from hoop.platform.backup import BackupError


class OneDrive:
    evidence_kind = "onedrive_rclone_readback"

    def __init__(self, binary: Path, remote: str, expected_version: str):
        match = re.fullmatch(r"([A-Za-z][A-Za-z0-9_-]{0,63}):([A-Za-z0-9_ /.-]{1,240})", remote)
        if not match or any(p in {"", ".", ".."} for p in match[2].split("/")):
            raise BackupError("explicit_onedrive_remote_folder_required")
        if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", expected_version):
            raise BackupError("verified_rclone_version_required")
        self.binary, self.remote = binary, remote.rstrip("/")
        allowed = {
            "PATH",
            "SYSTEMROOT",
            "TEMP",
            "TMP",
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
            "HOME",
            "HOMEDRIVE",
            "HOMEPATH",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
            "HTTPS_PROXY",
            "HTTP_PROXY",
            "NO_PROXY",
        }
        self.env = {
            k: v for k, v in os.environ.items() if k.upper() in allowed or k.startswith("RCLONE_")
        }
        try:
            version = subprocess.run(
                [str(binary), "version"],
                capture_output=True,
                env=self.env,
                timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            listing = subprocess.run(
                [str(binary), "listremotes", "--long", "--name", match[1], "--exact"],
                capture_output=True,
                env=self.env,
                timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired):
            raise BackupError("rclone_setup_unavailable") from None
        if (
            version.returncode
            or (version.stdout.splitlines() or [b""])[0] != ("rclone " + expected_version).encode()
        ):
            raise BackupError("rclone_version_mismatch")
        rows = [line.split()[:2] for line in listing.stdout.decode().splitlines() if line.strip()]
        if listing.returncode or rows != [[match[1] + ":", "onedrive"]]:
            raise BackupError("remote_is_not_verified_onedrive")

    def download(self, relative: str, destination: Path, limit: int) -> None:
        if relative.startswith("/") or ".." in relative or "\\" in relative or limit <= 0:
            raise BackupError("unsafe_remote_download")
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with destination.open("xb") as stream:
                result = subprocess.run(
                    [
                        str(self.binary),
                        "cat",
                        self.remote + "/" + relative,
                        "--count",
                        str(limit),
                        "--retries",
                        "1",
                        "--low-level-retries",
                        "1",
                        "--contimeout",
                        "10s",
                        "--timeout",
                        "60s",
                    ],
                    stdout=stream,
                    stderr=subprocess.PIPE,
                    env=self.env,
                    timeout=120,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if result.returncode:
                    raise BackupError("onedrive_remote_readback_failed")
        except (OSError, subprocess.TimeoutExpired):
            raise BackupError("onedrive_remote_readback_unavailable") from None

    def download_many(
        self, files: dict[str, int], destination: Path, *, max_seconds: float
    ) -> None:
        """One remote-to-local process, exact paths, two workers and hard byte/time caps."""
        if (
            not files
            or len(files) > 100000
            or isinstance(max_seconds, bool)
            or not math.isfinite(max_seconds)
            or not 1 <= max_seconds <= 1800
        ):
            raise BackupError("bounded_batch_readback_required")
        if any(
            not re.fullmatch(r"objects/[0-9a-f]{2}/[0-9a-f]{64}", path)
            or type(limit) is not int
            or limit <= 0
            for path, limit in files.items()
        ):
            raise BackupError("unsafe_batch_object_inventory")
        destination = destination.resolve()
        if not destination.is_dir() or (destination / "objects").exists():
            raise BackupError("batch_requires_fresh_object_directory")
        maximum = sum(files.values())
        if shutil.disk_usage(destination).free < maximum + 16 * 1024 * 1024:
            raise BackupError("insufficient_readback_disk_capacity")
        listing = destination / "requested-objects.txt"
        with listing.open("x", encoding="ascii", newline="\n") as stream:
            stream.write("\n".join(sorted(files)) + "\n")
        try:
            result = subprocess.run(
                [
                    str(self.binary),
                    "copy",
                    self.remote,
                    str(destination),
                    "--files-from-raw",
                    str(listing),
                    "--transfers",
                    "2",
                    "--checkers",
                    "2",
                    "--multi-thread-streams",
                    "0",
                    "--max-transfer",
                    str(maximum),
                    "--max-duration",
                    str(max_seconds) + "s",
                    "--cutoff-mode",
                    "hard",
                    "--immutable",
                    "--retries",
                    "1",
                    "--low-level-retries",
                    "1",
                    "--contimeout",
                    "10s",
                    "--timeout",
                    "60s",
                ],
                capture_output=True,
                env=self.env,
                timeout=max_seconds,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode:
                raise BackupError("onedrive_batch_readback_failed")
        except (OSError, subprocess.TimeoutExpired):
            raise BackupError("onedrive_batch_readback_unavailable") from None
