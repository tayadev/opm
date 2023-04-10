import io
from os import getenv, mkdir, path, listdir, makedirs
import shutil
import tomllib
import sys
from typing import Optional
import zipfile
from platformdirs import PlatformDirs, user_config_dir, user_data_dir, site_data_dir
app_dirs = PlatformDirs("ObsPluginManager", False)
from rich.table import Table
from rich.progress import Progress
from rich.prompt import Confirm
from rich.console import Console
console = Console()
import typer
app = typer.Typer()
import json
import requests
import hashlib

# TODO: Advise user to close obs if process is found to be currently open

# Load config from file or fall back to defaults
config = {
  'obs_plugin_path':
    sys.platform == 'win32' and 'C:\ProgramData\obs-studio\plugins' or
    sys.platform == 'linux' and path.join(user_config_dir('obs-studio'), 'plugins') or
    sys.platform == 'darwin' and path.join(site_data_dir('obs-studio'), 'plugins')
}

config_path = getenv('OPM_CONFIG') or path.join(app_dirs.user_config_path, 'config.toml')

if path.exists(config_path):
  with open(config_path, 'rb') as f:
    config = config | tomllib.load(f)

# Load plugin repository data
# TODO: make repo data synced from configurable remote
# TODO: validate repo data client side to avoid format mismatch before proceeding
pluginRepo = None
with open("repo.json") as f:
  pluginRepo = json.load(f)

# Setup cli commands

@app.command("list")
@app.command("ls")
def ls():
  table = Table(title=("Installed Plugins"))

  table.add_column("Name", style="cyan", no_wrap=True)
  table.add_column("Author", style="magenta")
  table.add_column("Version", style="green")
  table.add_column("Id", style="bright_black")

  if not path.isdir(config['obs_plugin_path']):
    console.print('[red]Plugin Directory doesn\'t exist or is misconfigured')
    return
  
  installed_plugin_folders = listdir(config['obs_plugin_path'])
  if len(installed_plugin_folders) == 0:
    console.print('[yellow]No Plugins installed')
    return

  for filename in installed_plugin_folders:
    file = path.join(config['obs_plugin_path'], filename)
    if path.isdir(file):
      if path.exists(path.join(file, "version.txt")):
        with open(path.join(file, "version.txt")) as f:
          version = f.read()
          plugin = pluginRepo['plugins'][filename]
          table.add_row(
            str(plugin['name']),
            str(plugin['author']),
            version, 
            filename
          )
      else:
        table.add_row(f"[bright_black]{filename}", None, None, filename)
  console.print(table)

@app.command('install')
@app.command("i")
@app.command("add")
def install(plugin_id: str, version_number: Optional[str] = typer.Argument(None), untrusted: bool = False):
  if not plugin_id in pluginRepo['plugins']:
    console.print(f"[red]Plugin {plugin_id} not in repository")
    return

  plugin = pluginRepo['plugins'][plugin_id]
  
  if not version_number:
    version_number = list(plugin['versions'].keys())[0]
    console.print(f'[yellow]No version specified, defaulting to newest one ({version_number})')

  if not version_number in plugin['versions']:
    console.print(f"[red]Version {version_number} not available")
    return
  
  version = plugin['versions'][version_number]
  # TODO: filter by release channel and supported obs version
  # Find applicable file to download
  # FIXME: make this cross platform
  selected_file = next(filter(lambda f: f['os'] == 'windows', version['files']))

  dl_url = selected_file['url']

  sha256 = None
  if not 'sha256' in selected_file:
    if not untrusted:
      console.print('[bold][red]WARNING: No checksum for plugin found, download will not be able to be verified, run with --untrusted to still proceed')
      return
    else:
      console.print('[red]WARNING: No checksum for plugin found, download will not be able to be verified')
  else:
    untrusted = False
    sha256 = selected_file['sha256']
    
  r = requests.get(dl_url, stream=True)

  downloaded_file = b""
  with Progress() as p:
    dl_task = p.add_task("Downloading")
    p.update(dl_task, total=int(r.headers.get("content-length", 0)))
    for chunk in r.iter_content(32 * 1024):
      if chunk:
        downloaded_file += chunk
        p.advance(dl_task, len(chunk))

  hash_sha256 = hashlib.sha256()
  hash_sha256.update(downloaded_file)
  checksum = hash_sha256.hexdigest()
  if not untrusted:
    if checksum != sha256.lower():
      console.print(f"[red]Checksum {checksum} invalid, expected checksum {sha256}, exiting")
      exit(1)
  else:
    console.print(f'[gray](Untrusted Mode) Downloaded file has checksum {checksum}')

  plugin_path = path.join(config['obs_plugin_path'], plugin_id)
  shutil.rmtree(plugin_path, ignore_errors=True)
  makedirs(plugin_path)
  binDir = path.join(plugin_path, "bin")
  mkdir(binDir)
  dataDir = path.join(plugin_path, "data")
  mkdir(dataDir)

  with zipfile.ZipFile(io.BytesIO(downloaded_file)) as zip_file:
    for zip_info in zip_file.infolist():
      if zip_info.filename[-1] == "/":
        continue

      if zip_info.filename.startswith(f"data/obs-plugins/{plugin_id}"):
        zip_info.filename = zip_info.filename.removeprefix(
          f"data/obs-plugins/{plugin_id}"
        )
        zip_file.extract(zip_info, dataDir)

      if zip_info.filename.startswith(f"obs-plugins"):
        zip_info.filename = zip_info.filename.removeprefix(f"obs-plugins")
        zip_file.extract(zip_info, binDir)

    with open(path.join(plugin_path, "version.txt"), "w") as f:
      f.write(version_number)

    console.print(f"[green]Installed {plugin['name']}")

@app.command("rm")
@app.command("del")
def uninstall(plugin_id: str):
  if not plugin_id in listdir(config['obs_plugin_path']):
    console.print(f"[red]Plugin {plugin_id} not installed")
    return

  plugin = pluginRepo['plugins'][plugin_id]

  if not Confirm.ask(f"[red]Uninstall[/red] {plugin['name']}?"):
    return

  shutil.rmtree(path.join(config['obs_plugin_path'], plugin_id))
  console.print(f"[green]Uninstalled {plugin['name']}")

@app.command("update")
def update(plugin_id: Optional[str] = typer.Argument(None)):
  # TODO:
  # for every installed plugin
    # read installed version
    # find newest compatible version in repo
    # if newer, queue it for updating
  # ask user for confirmation
  # update plugins
  return

@app.command("available")
def search(query: str):
  # TODO:
  # List available plugins
  # Hide incompatible ones
  return

if __name__ == "__main__":
  app()