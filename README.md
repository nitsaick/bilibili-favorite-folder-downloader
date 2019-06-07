bilibili-favorite-folder-downloader
===

bilibili 收藏夾下載工具

Usage
---
```sh
python main.py [OPTIONS]

Options:
  --type [user|fav|video]         type
  -i, --id INTEGER                user or fav folder ID  [required]
  -o, --output PATH               output path  [required]
  --pubdate [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%d %H:%M:%S]
                                  pubdate
  --fav_time [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%d %H:%M:%S]
                                  fav_time
  --exc_fav                       exclusion fav
  --exc_vid                       exclusion video
  -p, --port INTEGER RANGE        port  [default: 5555]
  -t, --thread INTEGER RANGE      thread  [default: 1]
  --help                          Show this message and exit.
```

## TODO
* Complete usage
* Add english README
* Add requirements
* ...