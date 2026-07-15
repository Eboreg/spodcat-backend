import re
import sys
from subprocess import PIPE, Popen


def mediainfo(filepath: str) -> dict:
    """Borrowed from Pydub (https://pydub.com/)"""

    command_args = [
        "-v", "quiet",
        "-show_format",
        "-show_streams",
        filepath,
    ]

    command = ["ffprobe", "-of", "old"] + command_args
    res = Popen(command, stdout=PIPE)
    output = res.communicate()[0].decode("utf-8")

    if res.returncode != 0:
        command = ["ffprobe"] + command_args
        output = Popen(command, stdout=PIPE).communicate()[0].decode("utf-8")

    rgx = re.compile(r"(?:(?P<inner_dict>.*?):)?(?P<key>.*?)\=(?P<value>.*?)$")
    info = {}

    if sys.platform == "win32":
        output = output.replace("\r", "")

    for line in output.split("\n"):
        mobj = rgx.match(line)

        if mobj:
            inner_dict, key, value = mobj.groups()

            if inner_dict:
                try:
                    info[inner_dict]
                except KeyError:
                    info[inner_dict] = {}
                info[inner_dict][key] = value
            else:
                info[key] = value

    return info
