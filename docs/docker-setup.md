# Docker

Running _Binance Trade Bot Manager Telegram_ inside a Docker container is an experimental feature.

## Setup

To run _Binance Trade Bot Manager Telegram_ inside a Docker container you must first make sure to have your _binance-trade-bot_ installation directory inside the _BTB-manager-telegram_ one.  
Your filesystem should look like this:

```
.
└── *parent_dir*
    └── BTB-manager-telegram
        └── binance-trade-bot
```

For quickly setting up the filesystem as intended you can run the `docker_setup.py` script:

```console
$ python3 docker_setup.py
```

`docker_setup.py` also takes the following optional arguments:

```console
optional arguments:
  -m, --make-image    Create a docker image for the bot.
  -u, --update-image  Update the docker image for the bot.
  -D, --delete-image  Delete the docker image for the bot.
```

## Usage

To run _Binance Trade Bot Manager Telegram_ in a Docker container you can do the following **after setting up the image**:

```console
$ python3 -m btb_manager_telegram --docker
```

⚠ Due to the nature of Docker containers, whenever you use the _Update Telegram Bot_ feature, only the repository inside the container will be updated while the one on your filesystem will remain untouched.
