"""Delete one PR preview; a preview that was never built is already absent."""

import json
import os
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


def delete_preview(account_id: str, worker: str, preview: str, token: str) -> None:
    """Delete the preview, tolerating only the API's not-found response."""
    request = Request(
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{quote(account_id, safe='')}/workers/workers/"
        f"{quote(worker, safe='')}/previews/{quote(preview, safe='')}",
        method="DELETE",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
    except HTTPError as error:
        error.close()
        if error.code != 404:
            raise
        print(f"{worker}/{preview} is already absent")
        return
    if not isinstance(result, dict) or result.get("success") is not True:
        raise RuntimeError(f"Cloudflare did not confirm deletion of {worker}/{preview}")
    print(f"Deleted {worker}/{preview}")


if __name__ == "__main__":
    delete_preview(
        os.environ["CLOUDFLARE_ACCOUNT_ID"],
        os.environ["WORKER"],
        f"pr-{int(os.environ['PR_NUMBER'])}",
        os.environ["CLOUDFLARE_API_TOKEN"],
    )
