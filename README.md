# icnsutil

A fully-featured python library to handle reading and writing `.icns` files.

## Install

The easy way is to use the PyPi.org index:

```sh
pip3 install icnsutil
```

Or you can install it **manually** by creating a symlink to `cli.py`:

```sh
ln -s '/absolute/path/to/icnsutil/icnsutil/cli.py' /usr/local/bin/icnsutil
ln -s '/absolute/path/to/icnsutil/icnsutil/autosize/cli.py' /usr/local/bin/icnsutil-autosize
```

Or call the python module (if the module is in the search path):

```sh
python3 -m icnsutil
python3 -m icnsutil.autosize
```


## Usage

See [#tools](#tools) for further options on icns processing (e.g., autosize).

```
positional arguments:
  command
    extract (e)   Read and extract contents of icns file(s).
    compose (c)   Create new icns file from provided image files.
    update (u)    Update existing icns file by inserting or removing media entries.
    info (i)      Print contents of icns file(s).
    test (t)      Test if icns file is valid.
    convert (img) Convert images between PNG, ARGB, or RGB + alpha mask.
```


### Use command line interface (CLI)

```sh
# extract
icnsutil e Existing.icns -o ./outdir/

# compose
icnsutil c New.icns 16x16.png 16x16@2x.png *.jp2 --toc

# update
icnsutil u Existing.icns -rm toc ic04 ic05
icnsutil u Existing.icns -set is32=16.rgb dark="dark icon.icns"
icnsutil u Existing.icns -rm dark -set ic04=16.argb -o Updated.icns

# print
icnsutil i Existing.icns

# verify valid format
icnsutil t Existing.icns

# convert image
icnsutil img 1024.png 512@2x.jp2
# or reuse original filename
icnsutil img argb 16x16.png
icnsutil img rgb 32.png
icnsutil img png 16.rgb 16.mask
```


### Use python library

```python
import icnsutil

# extract
img = icnsutil.IcnsFile('Existing.icns')
img.export(out_dir, allowed_ext='png',
           recursive=True, convert_png=True)

# compose
img = icnsutil.IcnsFile()
img.add_media(file='16x16.png')
img.add_media(file='16x16@2x.png')
img.write('./new-icon.icns')

# update
img = icnsutil.IcnsFile('Existing.icns')
img.add_media('icp4', file='16x16.png', force=True)
if img.remove_media('TOC '):
    print('table of contents removed')
img.write('Existing.icns', toc=True)

# print
# return type str
desc = icnsutil.IcnsFile.description(fname, indent=2)
print(desc)

# verify valid format
# return type Iterator[str]
itr = icnsutil.IcnsFile.verify(fname)
print(list(itr))
# If you just want to check if a file is faulty, you can use `any(itr)` instead.
# This way it will not test all checks but break early after the first hit.
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
icnsutil.ArgbImage(file='16x16.argb').write_png('16x16.png')

# Convert from PNG to 24-bit RGB
img = icnsutil.ArgbImage(file='32x32.png')
with open('32x32.rgb', 'wb') as fp:
    fp.write(img.rgb_data())
with open('32x32.mask', 'wb') as fp:
    fp.write(img.mask_data())
```

Note: the CLI `export` command will fail if you run `--convert` without Pillow.


## Tools

### Autosize

`icnsutil.autosize` is a tool to automatically generate smaller icon sizes from a larger one.
Currently, autosize has support for “normal” raster images (via sips or Pillow) and SVG images (via [resvg] or Chrome Headless).

```sh
icnsutil-autosize icon.svg -32 intermediate.png -16 small.svg
# or
python3 -m icnsutil.autosize icon.svg -32 intermediate.png -16 small.svg
```

Additionally, `autosize` will also try to convert 32px and 16px PNG images to ARGB.
If Pillow is not installed, this step will be skipped (without negative side effects).
The output is an iconset folder with all necessary images.

You may ask why this tool does not create the icns file immediatelly?
This way you can modify the generated images before packing them into an icns file.
For example, you can run [ImageOptim] to compress the images and reduce the overall icns filesize.

[resvg]: https://github.com/RazrFalcon/resvg/
[ImageOptim]: https://github.com/ImageOptim/ImageOptim


### HTML icon viewer

Here are two tools to open icns files directly in your browser. Both tools can be used either with an icns file or a rgb / argb image file.

- The [inspector] shows the structure of an icns file (useful to understand byte-unpacking in ARGB and 24-bit RGB files).
- The [viewer] displays icons in ARGB or 24-bit RGB file format.

[inspector]: https://relikd.github.io/icnsutil/html/inspector.html
[viewer]: https://relikd.github.io/icnsutil/html/viewer.html

## Help needed

1. Do you have an old macOS version running somewhere?  
You can help and identify what file formats / icns types were introduced and when. Download the [format-support-icns.zip] file and report back which icons are displayed properly and in which macOS version.  
See the [Apple Icon Image](https://en.wikipedia.org/wiki/Apple_Icon_Image) wikipedia article.

2. You can run `make sys-icons-test` and report back whether you find some weird icons that are not handled properly by this library.

[format-support-icns.zip]: https://github.com/relikd/icnsutil/raw/main/tests/format-support-icns.zip

