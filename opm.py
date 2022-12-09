import typer
from os.path import join, isdir, exists, basename
from os import listdir, mkdir
import json
from rich.table import Table
from rich.console import Console
console = Console()
from bullet import Bullet, colors
from rich.prompt import Confirm
import shutil
import requests
from rich.progress import Progress
import hashlib
import zipfile
import io
from typing import Optional

app = typer.Typer()
pluginsDir = 'C:\ProgramData\obs-studio\plugins'

pluginRepo = None
with open('plugins.json') as f:
    pluginRepo = json.loads(f.read())

def downloadAndVerify(url, expected_checksum):
    r = requests.get(url, stream=True)

    file = b''
    with Progress() as p:
        dl_task = p.add_task("Downloading")
        p.update(dl_task, total=int(r.headers.get('content-length', 0)))
        for chunk in r.iter_content(32 * 1024):
            if chunk:
                file += chunk
                p.advance(dl_task, len(chunk))

    hash_sha256 = hashlib.sha256()
    hash_sha256.update(file)
    checksum = hash_sha256.hexdigest()
    if checksum != expected_checksum:
        print(f'Checksum {checksum} invalid, exiting')
        exit(1)

    return file

@app.command()
def info(plugin: str):
    plugin = pluginRepo[plugin]
    console.print(plugin)

@app.command("list")
@app.command("ls")
def ls(remote: bool = False):
    table = Table(title="Installed Plugins")

    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Author", style="magenta")
    table.add_column("Version", style="green")
    table.add_column("Id", style="bright_black")

    if not remote:
        for filename in listdir(pluginsDir):
            file = join(pluginsDir, filename)
            if isdir(file):
                if exists(join(file, 'version.txt')):
                    with open(join(file, 'version.txt')) as f:
                        version = f.read()
                        plugin = pluginRepo[filename]
                        table.add_row(plugin['name'], plugin['author'], version, filename)
                else:
                    table.add_row(f"[bright_black]{filename}", None, None, filename)
    else:
        for pluginId in pluginRepo:
            plugin = pluginRepo[pluginId]
            table.add_row(plugin['name'], plugin['author'], list(plugin['versions'].keys())[0], pluginId)
    console.print(table)

@app.command()
@app.command("rm")
@app.command("del")
def uninstall(plugin: Optional[str] = typer.Argument(None)):
    if not plugin:
        installed = [pluginRepo[p]['name'] for p in listdir(pluginsDir) if p in pluginRepo]
        if len(installed) == 0:
            console.print('No plugins installed')
            return
        console.print("Select a plugin to uninstall:")
        cli = Bullet(
            choices = installed,
            margin = 1,
            background_color = "",
            background_on_switch = "",
            word_on_switch=colors.bright(colors.foreground["red"]),
            bullet = "❌"
        )
        answer = cli.launch()
        plugin = [p for p in pluginRepo if pluginRepo[p]['name'] == answer][0]

    if not plugin in pluginRepo:
        console.print(f"[red]Plugin {plugin} not installed")
        return
    
    pluginName = pluginRepo[plugin]['name']
    if not Confirm.ask(f"[red]Uninstall[/red] {pluginName}?"): return
    
    shutil.rmtree(join(pluginsDir, plugin))
    console.print(f"[green]Uninstalled {pluginName}")

@app.command()
@app.command("i")
@app.command("add")
def install(plugin: Optional[str] = typer.Argument(None), version: Optional[str] = typer.Argument(None)):
    if not plugin:
        console.print("Select a plugin to install:")
        cli = Bullet(
            choices = [pluginRepo[p]['name'] for p in pluginRepo],
            margin = 1,
            background_color = "",
            background_on_switch = "",
            word_on_switch=colors.bright(colors.foreground["green"]),
            bullet = "✅"
        )
        answer = cli.launch()
        plugin = [p for p in pluginRepo if pluginRepo[p]['name'] == answer][0]

    if not plugin in pluginRepo:
        console.print(f"[red]Plugin {plugin} not in repository")
        return
    
    pluginName = pluginRepo[plugin]['name']

    if not version: version = list(pluginRepo[plugin]['versions'].keys())[0]
    if not version in pluginRepo[plugin]['versions']:
        console.print(f"[red]Version {version} not available")
        return

    console.print(f"[green]Installing {pluginName} {version}")

    dls = pluginRepo[plugin]['versions'][version]
    url = dls['url']
    checksum = dls['sha256']

    dl = downloadAndVerify(url, checksum)

    pluginDir = join(pluginsDir, plugin)
    shutil.rmtree(pluginDir, ignore_errors=True)
    mkdir(pluginDir)
    binDir = join(pluginDir, 'bin')
    mkdir(binDir)
    dataDir = join(pluginDir, 'data')
    mkdir(dataDir)

    with zipfile.ZipFile(io.BytesIO(dl)) as zip_file:
        for zip_info in zip_file.infolist():
            if zip_info.filename[-1] == '/':
                continue

            if zip_info.filename.startswith(f'data/obs-plugins/{plugin}'):
                zip_info.filename = zip_info.filename.removeprefix(f'data/obs-plugins/{plugin}')
                zip_file.extract(zip_info, dataDir)

            if zip_info.filename.startswith(f'obs-plugins'):
                zip_info.filename = zip_info.filename.removeprefix(f'obs-plugins')
                zip_file.extract(zip_info, binDir)

    with open(join(pluginDir, 'version.txt'), 'w') as f:
        f.write(version)
    
    console.print(f"[green]Installed {pluginName}")

if __name__ == "__main__":
    app()