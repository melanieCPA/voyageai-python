import logging
import os
import re
import sys
import voyageai

VOYAGE_LOG = os.environ.get("VOYAGE_LOG")

logger = logging.getLogger("voyage")

__all__ = [
    "log_info",
    "log_debug",
    "log_warn",
    "logfmt",
]

api_key_to_header = (
    lambda key: {"Authorization": f"Bearer {key}"}
)


def _console_log_level():
    if voyageai.log in ["debug", "info"]:
        return voyageai.log
    elif VOYAGE_LOG in ["debug", "info"]:
        return VOYAGE_LOG
    else:
        return None


def log_debug(message, **params):
    msg = logfmt(dict(message=message, **params))
    if _console_log_level() == "debug":
        print(msg, file=sys.stderr)
    logger.debug(msg)


def log_info(message, **params):
    msg = logfmt(dict(message=message, **params))
    if _console_log_level() in ["debug", "info"]:
        print(msg, file=sys.stderr)
    logger.info(msg)


def log_warn(message, **params):
    msg = logfmt(dict(message=message, **params))
    print(msg, file=sys.stderr)
    logger.warn(msg)


def logfmt(props):
    def fmt(key, val):
        # Handle case where val is a bytes or bytesarray
        if hasattr(val, "decode"):
            val = val.decode("utf-8")
        # Check if val is already a string to avoid re-encoding into ascii.
        if not isinstance(val, str):
            val = str(val)
        if re.search(r"\s", val):
            val = repr(val)
        # key should already be a string
        if re.search(r"\s", key):
            key = repr(key)
        return "{key}={val}".format(key=key, val=val)

    return " ".join([fmt(key, val) for key, val in sorted(props.items())])


def convert_to_voyage_object(resp):
    # If we get a VoyageHttpResponse, we'll want to return a VoyageObject.

    if isinstance(resp, voyageai.api_resources.VoyageHttpResponse):
        resp = resp.data

    if isinstance(resp, list):
        return [
            convert_to_voyage_object(i)
            for i in resp
        ]
    elif isinstance(resp, dict) and not isinstance(
        resp, voyageai.voyage_object.VoyageObject
    ):
        resp = resp.copy()
        klass = voyageai.voyage_object.VoyageObject

        return klass.construct_from(resp)
    else:
        return resp


def convert_to_dict(obj):
    """Converts a VoyageObject back to a regular dict.

    Nested VoyageObjects are also converted back to regular dicts.

    :param obj: The VoyageObject to convert.

    :returns: The VoyageObject as a dict.
    """
    if isinstance(obj, list):
        return [convert_to_dict(i) for i in obj]
    # This works by virtue of the fact that VoyageObjects _are_ dicts. The dict
    # comprehension returns a regular dict and recursively applies the
    # conversion to each value.
    elif isinstance(obj, dict):
        return {k: convert_to_dict(v) for k, v in obj.items()}
    else:
        return obj


def merge_dicts(x, y):
    z = x.copy()
    z.update(y)
    return z


def default_api_key() -> str:
    api_key_path = voyageai.api_key_path or os.environ.get("VOYAGE_API_KEY_PATH")
    api_key = voyageai.api_key or os.environ.get("VOYAGE_API_KEY")
    
    # When api_key_path is specified, it overwrites api_key
    if api_key_path:
        with open(api_key_path, "rt") as k:
            api_key = k.read().strip()
            return api_key
    elif api_key is not None:
        return api_key
    else:
        raise voyageai.error.AuthenticationError(
            "No API key provided. You can set your API key in code using 'voyageai.api_key = <API-KEY>', "
            "or set the environment variable VOYAGE_API_KEY=<API-KEY>). If your API key is stored "
            "in a file, you can point the voyageai module at it with 'voyageai.api_key_path = <PATH>', "
            "or set the environment variable VOYAGE_API_KEY_PATH=<PATH>. "
            "API keys can be generated in Voyage AI's dashboard (https://dash.voyageai.com)."
        )
