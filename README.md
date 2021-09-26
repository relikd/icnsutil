# icnsutil

A fully-featured python library to handle reading and writing `.icns` files.


## HTML icon viewer

Here are two tools to open icns files directly in your browser. Both tools can be used either with an icns file or a rgb / argb image file.

- The [inspector] shows the structure of an icns file (useful to understand byte-unpacking in ARGB and 24-bit RGB files).
- The [viewer] displays icons in ARGB or 24-bit RGB file format.

[inspector]: https://relikd.github.io/icnsutil/html/inspector.html[viewer]: https://relikd.github.io/icnsutil/html/viewer.html


## Usage

```
positional arguments:
  command
    extract (e)   Read and extract contents of icns file(s).
    compose (c)   Create new icns file from provided image files.
    print (p)     Print contents of icns file(s).
    test (t)      Test if icns file is valid.
```


### Use command line interface (CLI)

```sh
# extract
./cli.py e ExistingIcon.icns -o ./outdir/

# compose
./cli.py c NewIcon.icns 16x16.png 16x16@2x.png *.jp2

# print
./cli.py p ExistingIcon.icns

# verify valid format
./cli.py t ExistingIcon.icns
```


### Use python library

```python
import icnsutil

# extract
img = icnsutil.IcnsFile('ExistingIcon.icns')
img.export(out_dir, allowed_ext='png',
           recursive=True, convert_png=True)

# compose
img = icnsutil.IcnsFile()
img.add_media(file='16x16.png')
img.add_media(file='16x16@2x.png')
img.write('./new-icon.icns', toc=False)

# print
icnsutil.IcnsFile.description(fname, indent=2)

# verify valid format
icnsutil.IcnsFile.verify(fname)
```


#### Converting between (A)RGB and PNG

You can use the library without installing PIL.
However, if you want to convert between PNG and ARGB files, Pillow is required.

```sh
pip install Pillow
```

```python
import icnsutil

# Convert from ARGB to PNG
icnsutil.ArgbImage('16x16.argb').write_png('16x16.png')

# Convert from PNG to 24-bit RGB
img = icnsutil.ArgbImage('32x32.png')
with open('32x32.rgb', 'wb') as fp:
    fp.write(img.rgb_data())
with open('32x32.mask', 'wb') as fp:
    fp.write(img.mask_data())
```

Note: the CLI `export` command will fail if you run `--convert` without Pillow.


## Help needed

1. Do you have an old macOS version running somewhere?  
You can help and identify what file formats / icns types were introduced and when. Download the [format-support-icns.zip](./tests/format-support-icns.zip) file and report back which icons are displayed properly and in which macOS version.  
See the [Apple Icon Image](https://en.wikipedia.org/wiki/Apple_Icon_Image) wikipedia article.

2. You can run `make sys-icons-test` and report back whether you find some weird icons that are not handled properly by this library.
