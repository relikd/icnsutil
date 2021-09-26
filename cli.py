#!/usr/bin/env python3
'''
Export existing icns files or compose new ones.
'''
import os  # path, mkdir
import icnsutil
from sys import stderr
from argparse import ArgumentParser, ArgumentTypeError, RawTextHelpFormatter

__version__ = icnsutil.__version__


def cli_extract(args):
    ''' Read and extract contents of icns file(s). '''
    multiple = len(args.file) > 1
    for i, fname in enumerate(args.file):
        # PathExist ensures that all files and directories exist
        out = args.export_dir
        if out and multiple:
            out = os.path.join(out, str(i))
            os.makedirs(out, exist_ok=True)

        pred = 'png' if args.png_only else None
        icnsutil.IcnsFile(fname).export(
            out, allowed_ext=pred, recursive=args.recursive,
            convert_png=args.convert, key_suffix=args.keys)


def cli_compose(args):
    ''' Create new icns file from provided image files. '''
    dest = args.target
    if not os.path.splitext(dest)[1]:
        dest += '.icns'  # for the lazy people
    if not args.force and os.path.exists(dest):
        print(f'File "{dest}" already exists. Force overwrite with -f.',
              file=stderr)
        return 1
    img = icnsutil.IcnsFile()
    for x in args.source:
        img.add_media(file=x)
    img.write(dest, toc=not args.no_toc)


def cli_print(args):
    ''' Print contents of icns file(s). '''
    for fname in args.file:
        print('File:', fname)
        print(icnsutil.IcnsFile.description(
            fname, verbose=args.verbose, indent=2))


def cli_verify(args):
    ''' Test if icns file is valid. '''
    for fname in args.file:
        is_valid = True
        if not args.quiet:
            print('File:', fname)
            is_valid = None
        for issue in icnsutil.IcnsFile.verify(fname):
            if is_valid:
                print('File:', fname)
            is_valid = False
            print(' ', issue)
        if not args.quiet and is_valid is not False:
            print('OK')


def main():
    class PathExist:
        def __init__(self, kind=None):
            self.kind = kind

        def __call__(self, path):
            if not os.path.exists(path) or \
                    self.kind == 'f' and not os.path.isfile(path) or \
                    self.kind == 'd' and not os.path.isdir(path):
                raise ArgumentTypeError('Does not exist "{}"'.format(path))
            return path

    # Args Parser
    parser = ArgumentParser(description=__doc__,
                            formatter_class=RawTextHelpFormatter)
    parser.set_defaults(func=lambda _: parser.print_help(stderr))
    parser.add_argument(
        '-v', '--version', action='version', version='icnsutil ' + __version__)
    sub_parser = parser.add_subparsers(metavar='command')

    # Extract
    cmd = sub_parser.add_parser(
        'extract', aliases=['e'], formatter_class=RawTextHelpFormatter,
        help=cli_extract.__doc__, description=cli_extract.__doc__.strip())
    cmd.add_argument(
        '-r', '--recursive', action='store_true',
        help='extract nested icns files as well')
    cmd.add_argument(
        '-o', '--export-dir', type=PathExist('d'), metavar='DIR',
        help='set custom export directory')
    cmd.add_argument(
        '-k', '--keys', action='store_true',
        help='use icns key as filenam')
    cmd.add_argument(
        '-c', '--convert', action='store_true',
        help='convert ARGB and RGB images to PNG')
    cmd.add_argument(
        '--png-only', action='store_true',
        help='do not extract ARGB, binary, and meta files')
    cmd.add_argument(
        'file', nargs='+', type=PathExist('f'), metavar='FILE',
        help='One or more .icns files.')
    cmd.set_defaults(func=cli_extract)

    # Compose
    cmd = sub_parser.add_parser(
        'compose', aliases=['c'], formatter_class=RawTextHelpFormatter,
        help=cli_compose.__doc__, description=cli_compose.__doc__.strip())
    cmd.add_argument(
        '-f', '--force', action='store_true',
        help='force overwrite output file')
    cmd.add_argument(
        '--no-toc', action='store_true',
        help='do not write table of contents to file')
    cmd.add_argument(
        'target', type=str, metavar='destination',
        help='Output file for newly created icns file.')
    cmd.add_argument(
        'source', nargs='+', type=PathExist('f'), metavar='src',
        help='One or more media files: png, argb, plist, icns.')
    cmd.set_defaults(func=cli_compose)
    cmd.epilog = f'''
Notes:
- TOC is optional but only a few bytes long (8b per media entry).
- Icon dimensions are read directly from file.
- Filename suffix "@2x.png" or "@2x.jp2" sets the retina flag.
- Use one of these suffixes to automatically assign icns files:
   {', '.join(f'{x.name.lower()}.icns' for x in icnsutil.IcnsType.Role)}
'''

    # Print
    cmd = sub_parser.add_parser(
        'print', aliases=['p'], formatter_class=RawTextHelpFormatter,
        help=cli_print.__doc__, description=cli_print.__doc__.strip())
    cmd.add_argument(
        '-v', '--verbose', action='store_true',
        help='print all keys with offsets and sizes')
    cmd.add_argument(
        'file', nargs='+', type=PathExist('f'), metavar='FILE',
        help='One or more .icns files.')
    cmd.set_defaults(func=cli_print)

    # Verify
    cmd = sub_parser.add_parser(
        'test', aliases=['t'], formatter_class=RawTextHelpFormatter,
        help=cli_verify.__doc__, description=cli_verify.__doc__.strip())
    cmd.add_argument(
        '-q', '--quiet', action='store_true',
        help='do not print OK results')
    cmd.add_argument(
        'file', nargs='+', type=PathExist('f'), metavar='FILE',
        help='One or more .icns files.')
    cmd.set_defaults(func=cli_verify)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
