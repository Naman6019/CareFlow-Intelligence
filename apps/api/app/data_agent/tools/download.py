import hashlib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.data_agent.models import DataSource


@dataclass(frozen=True)
class DownloadResult:
    path: Path
    sha256: str
    size_bytes: int


class OfficialDatasetDownloadTool:
    """Download one allow-listed synthetic dataset with strict size limits."""

    def __init__(self, max_bytes: int, timeout_seconds: float = 60.0):
        self.max_bytes = max_bytes
        self.timeout = httpx.Timeout(timeout_seconds)

    async def run(self, source: DataSource, destination: Path) -> DownloadResult:
        parsed_url = urlparse(source.url)
        if parsed_url.scheme != "https":
            raise ValueError("Dataset URL must use HTTPS.")
        if parsed_url.hostname not in source.allowed_hosts:
            raise ValueError("Dataset host is not in the approved source list.")

        destination.parent.mkdir(parents=True, exist_ok=True)
        partial_path = destination.with_suffix(".part")
        digest = hashlib.sha256()
        size_bytes = 0

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self.timeout,
            ) as client:
                async with client.stream("GET", source.url) as response:
                    response.raise_for_status()
                    final_host = response.url.host
                    if final_host not in source.allowed_hosts:
                        raise ValueError(
                            "Dataset redirected to a non-approved host."
                        )

                    content_length = response.headers.get("content-length")
                    if (
                        content_length
                        and int(content_length) > self.max_bytes
                    ):
                        raise ValueError("Dataset exceeds the download size limit.")

                    with partial_path.open("wb") as output:
                        async for chunk in response.aiter_bytes():
                            size_bytes += len(chunk)
                            if size_bytes > self.max_bytes:
                                raise ValueError(
                                    "Dataset exceeded the download size limit."
                                )
                            digest.update(chunk)
                            output.write(chunk)

            partial_path.replace(destination)
            return DownloadResult(
                path=destination,
                sha256=digest.hexdigest(),
                size_bytes=size_bytes,
            )
        except Exception:
            partial_path.unlink(missing_ok=True)
            raise

