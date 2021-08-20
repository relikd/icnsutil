# ICNS-Util

A python library to handle reading and writing `.icns` files.


## Usage


```
Usage:
  extract: icnsutil.py input.icns [--png-only]
           --png-only: Do not extract ARGB, binary, and meta files.

  compose: icnsutil.py output.icns [-f] [--no-toc] 16.png 16@2x.png ...
           -f: Force overwrite output file.
           --no-toc: Do not write TOC to file.

Note: Icon dimensions are read directly from file.
However, the suffix "@2x" will set the retina flag accordingly.
```


### Extract from ICNS

```sh
cp /Applications/Safari.app/Contents/Resources/AppIcon.icns ./TestIcon.icns
python3 icnsutil.py TestIcon.icns
```


### Compose new ICNS

```sh
python3 icnsutil.py TestIcon_new.icns --no-toc ./*.png -f
```

Or call the script directly, if it has execution permissions.


### Use in python script

```python
import icnsutil
icnsutil.compose(icns_file, list_of_png_files, toc=True)
icnsutil.extract(icns_file, png_only=False)
```
