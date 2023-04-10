import requests
from rich.console import Console
import re, json

console = Console()

# obs forums
# github

def list_versions_github(profile, project):
    r = requests.get(f"https://api.github.com/repos/{profile}/{project}/releases")
    versions = r.json()
    versions = [
        {
            "number": extractVersionFromName(version["name"]),
            "timestamp": version["published_at"],
            "files": [
                {
                    "os": extractPlatformFromArchiveName(file["name"])[0],
                    "arch": extractPlatformFromArchiveName(file["name"])[1],
                    "url": file["browser_download_url"],
                }
                for file in version["assets"] if not 'installer' in file['name'].lower()
            ],
        }
        for version in versions
    ]

    versions_dict = {}
    for version in versions:
        number = version.pop('number', None)
        versions_dict[number] = version

    return versions_dict


def extractPlatformFromArchiveName(name):
    name = name.lower()
    os = ""
    arch = []
    if "win" in name:
        os = "windows"
    elif "linux" in name or '.deb' in name or '.tar.gz' in name:
        os = "linux"
    elif "mac" in name or '.pkg' in name:
        os = "mac"
    else:
        print(f"Can't guess OS from name {name}, defaulting to windows")
        os = "windows"

    if "x64" in name:
        arch.append("x64")
    if "x86" in name:
        arch.append("x86")
    if "x32" in name:
        arch.append("x86")
    if "x86_64" in name:
        arch = ["x64"]
    if "arm64" in name:
        arch = ["arm64"]
    if "universal" in name and os == "mac":
        arch = ["x64", "x86", "arm64"]
    if len(arch) == 0:
        print(f"Can't guess architecture from name {name}, defaulting to x64")
        arch = ["x64"]

    return os, arch

def extractVersionFromName(name):
  match = re.sub('[^0-9\.]','', name)
  if match.count('.') == 1: match += '.0'
  return match

# console.print(list_versions_github('fzwoch', 'obs-teleport'))
# with open('durchblick.json', 'w') as f:
#   json.dump(
#     list_versions_github("univrsal","durchblick"),
#     f
#   )