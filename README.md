# serptool

## Setting up the project

### Installation

First, create a virtual environment, and install the dependencies:

```shell script
python3 -m venv virtualenv
source virtualenv/bin/activate
pip install -r requirements.txt 
```

### Configuring the project

Create a local config file from the example file:

```shell script
$ cp serptool/config.py.example serptool/config.py
```

By default, vars will be pulled from environment but you can set specific values
in this `config.py` file.

### Setting up servers

Lastly, we need to configure `nginx` and `supervisor`.

First, copy the example files where they should reside:

```shell script
cp configuration/nginx.conf /etc/nginx/sites-available/serptool.conf
cp configuration/supervisor.conf /etc/supervisor/conf.d/serptool.conf
```

Edit the new `nginx` file and set the appropriate `server_name`, and the
`supervisor` file and set `PATH_TO_PROJECT`.

After that, restart `nginx` and `supervisor` so they pick up the changes,
and visit the URL you deployed it to! Voila~
