#!/usr/bin/env python3
'''
Auto-downscale images to generate an iconset (`.iconset`) for `.icns` files.
'''
import os
import sys
from typing import TYPE_CHECKING, List, Tuple, Optional
if __name__ == '__main__':
    sys.path[0] = os.path.dirname(os.path.dirname(sys.path[0]))
from icnsutil.autosize.helper import bestImageResizer
if TYPE_CHECKING:
    from icnsutil.autosize.ImageResizer import ImageResizer
try:
    from icnsutil import ArgbImage
except ImportError:
    pass


def main() -> None:
    images, err = parse_input_args()
    if images:
        # TODO: should iconset be created at image source or CWD?
        iconset_out = images[0].fname + '.iconset'
        os.makedirs(iconset_out, exist_ok=True)
        downscale_images(images, iconset_out)
        icns_file = images[0].fname + '.icns'
        convert_icnsutil(iconset_out, icns_file)
    else:
        print(__doc__.strip())
        print()
        print('Usage: icnsutil-autosize icon.svg -16 small.svg')
        print('       icnsutil-autosize 1024.png img32px.png')
        if err:
            print()
            print(err, file=sys.stderr)
        else:
            print(parse_input_args.__doc__)
        exit(1 if err else 0)


def parse_input_args() -> Tuple[Optional[List['ImageResizer']], Optional[str]]:
    '''
    List of image files sorted by resolution in descending order.
    Manually overwrite resolution by prepending `-X` before image-name,
    where `X` is one of: [16, 32, 128, 256, 512].
    `X` applies for both, normal and retina size (`img_X.png`, `img_X@2x.png`)
    '''
    if len(sys.argv) == 1 or '-h' in sys.argv or '--help' in sys.argv:
        return None, None  # just print help
    size = 512  # assume first icon is 1024x1024 (512@2x)
    ret = []
    for arg in sys.argv[1:]:
        if arg.startswith('-'):  # size indicator (-<int>)
            new_size = int(arg[1:])
            if new_size >= size:
                return None, 'Icons must be sorted by size, largest first.'
            size = new_size
        elif os.path.isfile(arg):  # icon file
            ret.append(bestImageResizer(arg, size))
        else:
            return None, 'File "{}" does not exist.'.format(arg)
    return ret, None


def downscale_images(images: List['ImageResizer'], outdir: str) -> None:
    ''' Go through all files and apply resizer one by one. '''
    all_sizes = [x.size for x in images[1:]] + [0]
    for img, nextsize in zip(images, all_sizes):
        maxsize = img.size
        if nextsize >= maxsize:
            print('SKIP: "{}" (next image is larger, {}px <= {}px)'.format(
                img.fname, maxsize, nextsize), file=sys.stderr)
            continue

        print('downscaling from {}@2x ({}): '.format(
            maxsize, type(img).__name__), end='')
        for s in (16, 32, 128, 256, 512):
            if nextsize < s <= maxsize:
                base = os.path.join(outdir, 'icon_{0}x{0}'.format(s))
                print('.', end='')
                img.resize(s, base + '.png')
                print('.', end='')
                img.resize(s * 2, base + '@2x.png')
        print(' done.')  # finishes "...." line


def convert_icnsutil(iconset_dir: str, icns_file: str) -> None:
    ''' After downscaling, try to convert PNG to ARGB. '''
    for x in [16, 32]:
        src = os.path.join(iconset_dir, 'icon_{0}x{0}.png'.format(x))
        dst = src[:-4] + '.argb'
        if not os.path.isfile(src):
            continue
        print('converting {0}x{0}.argb (icnsutil): ... '.format(x), end='')
        try:
            argb_image = ArgbImage(file=src)
            with open(dst, 'wb') as fp:
                fp.write(argb_image.argb_data())
            print('done.')  # finishes "..." line
            os.remove(src)
        except Exception as e:
            print('error.')  # finishes "..." line
            print(' E:', e, file=sys.stderr)
            print(' E: Proceeding without ARGB images ...', file=sys.stderr)
            break
    print('''
Finished. After your adjustments (e.g. compress with ImageOptim), run:
$> icnsutil compose "{}" "{}"'''.format(icns_file, iconset_dir))


if __name__ == '__main__':
    main()
