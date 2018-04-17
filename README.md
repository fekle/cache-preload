# cache-preload
A simple utility to preload/warmup webserver and cdn caches using sourcemaps - also can take screenshots
Writting in Python 3 using selenium and geckodriver.

## Installation

### Docker
The easiest way to run this is by using the pre-built docker image [fekle/cache-preload:latest](https://hub.docker.com/r/fekle/cache-preload/)
or building the image yourself with `./cli docker-build`. You can then run via `./cli docker-run <cmd>` 
or simply by running:
```bash
docker run --rm -t --shm-size=2g \
    --user "$(id -u):$(id -g)" \
    -v "$(pwd):/workdir:rw" \
    cache-preload:latest <cmd>
```

Notice the `--shm-size=2g` (shared memory size) flag - this is important, as otherwise Firefox will crash.

### Local
To install locally, use `pipenv install` and `pipenv run ./cache-preload.py`.
For development, you can start a shell in the venv with `pipenv shell`.
External prerequisites: firefox, geckodriver

## Usage
```
Usage: cache-preload.py [OPTIONS] URL

Options:
  -d, --desktop / -nd, --no-desktop
                                  enable desktop browser  [default: True]
  -m, --mobile / -nm, --no-mobile
                                  enable mobile browser  [default: False]
  -gp, --geckodriver-path PATH    path to geckodriver binary  [default:
                                  /usr/bin/geckodriver]
  -sd, --screenshot-dir DIRECTORY
                                  save screenshots to directory
  -ld, --log-dir DIRECTORY        save logs to directory
  -h, --help                      Show this message and exit.
```

This program parses the specified site maps and stores all included urls while also
querying child site maps. Each url will then be visited by each enabled browser, including
taking screenshots if desired. 

The only argument required for operation is `URL`, which expects a site map.

By default, only a desktop browser (window size 1920x1080) is used, using the `--mobile` flag
also enables an emulated mobile browser (iPhone X user-agent, window size 375x633). To only
use one of those browsers use the `--no-desktop` or `--no-mobile` flags respectively.

Another option is the `--geckodriver-path`, which allows you to specify the location of the geckodriver binary.
The default, however, should work on most systems.

The option `--screenshot-dir` allows you to specify a directory where screenshots will be saved to. No screenshots
will be created if omitted.

Lastly, `--log-dir` specifies the directory where Firefox logs are saved to. This too is disabled if omitted.