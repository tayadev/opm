# OPM - OBS Plugin Manager

A small python application to manage OBS plugins

## Installation
> Currently OPM only works on windows and requires a current installation of python

```sh
python -m venv .venv
.venv/Scripts/activate
pip install -r requiremens.txt
```

## Usage

### Installing Plugins
`py opm.py install <pluginId> <version>`\
> both `pluginId` and `version` are optional

### Uninstalling Plugins
`py opm.py uninstall <pluginId>`\
> `pluginId` is optional

### List Installed Plugins
`py opm.py list`

### List Available Plugins
`py opm.py list --remote`

## plugins.json
The plugin repository file `plugins.json` contains metadata and download links to the plugins
I am planning to integrate a system for this to be provided by a server, so it can be more up to date with less effort