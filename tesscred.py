#!/usr/bin/env python3
import argparse
from collections import OrderedDict
from concurrent import futures
import json
import mimetypes
import os.path
from os import scandir, mkdir
import subprocess
import sys
from zipfile import ZipFile


ARCHIVE_MIMES = ["application/zip",
                 "application/x-cbz"]

IMAGE_MIMES = ["image/png",
               "image/jpeg",
               "image/gif"]


def iterate_archives(directory):
    if os.path.isfile(directory):
        yield directory
    for f in scandir(directory):
        if f.is_dir():
            yield from iterate_archives(f.path)
        elif f.is_file():
            if mimetypes.guess_type(f.path)[0] in ARCHIVE_MIMES:
                yield f.path


def scan_archive(f):
    with ZipFile(f) as z:
        for zi in z.infolist():
            tp = mimetypes.guess_type(zi.filename)[0]
            if tp in IMAGE_MIMES:
                with z.open(zi) as page:
                    data = page.read()
                    yield (data, tp, zi.filename)


def tesseract_run(filein, lang="eng"):
    tess_args = ["tesseract", "-", "-", "-l", lang]
    proc = subprocess.run(tess_args, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, input=filein)
    return proc.stdout.decode("utf-8")


def tesseract_analyze(f):
    TRIGGERS = [("translation", 1),
                ("translate", 1),
                ("translating", 1),
                ("translator", 1),
                ("credit", 1),
                ("redraw", 1),
                ("typeset", 2),
                ("proofread", 1.5),
                ("wordpress", 2),
                ("scans", 1),
                ("raws", 0.5),
                ("rizon", 1),
                ("staff", 0.5),
                ("editor", 0.5),
                ("typos", 1.5),
                ("release", 0.5),
                ("v2", 0.5),
                ("raw provider", 2),
                ("cleaner", 0.5),
                ("quality check", 1),
                ("letterer", 1),
                ("cleaning", 0.5),
                ("editing", 1),
                ("tumblr", 1.5),
                ]
    text = tesseract_run(f).lower()
    score = 0
    found = []
    for t, w in TRIGGERS:
        if text.find(t) > 0:
            score += w
            found.append(t)
    return (score, text, found)


def main():
    parser = argparse.ArgumentParser(description="Look for credits pages in "
                                     "manga archives and extract them")
    parser.add_argument("mangadir", type=str, help="Base directory of manga")
    parser.add_argument("outdir", type=str,
                        help="Output directory for credit pages")
    parser.add_argument("--workers", "-w", type=int, default=4,
                        help="Number of tesseract workers")

    args = parser.parse_args()

    if not os.path.isdir(args.mangadir):
        if not os.path.exists(args.mangadir):
            print("Directory '{}' does not exist".format(args.mangadir))
            sys.exit(1)
        else:
            if os.path.isfile(args.mangadir):
                if mimetypes.guess_type(args.mangadir)[0] in ARCHIVE_MIMES:
                    pass
                else:
                    print("'{}' is no archive file, buddy"
                          .format(args.mangadir))
                    sys.exit(1)
    if not os.path.isdir(args.outdir):
        if not os.path.exists(args.outdir):
            mkdir(args.outdir)
        else:
            print("Output directory '{}' exists and is not a directory"
                  .format(args.outdir))

    num_c_pages = 0
    for archive in iterate_archives(args.mangadir):
        print("Scanning '{}'...".format(os.path.basename(archive)))
        with futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
            futsdic = OrderedDict()
            for pdat, tp, name in scan_archive(archive):
                    fut = ex.submit(tesseract_analyze, pdat)
                    futsdic[fut] = {"pdat": pdat, "tp": tp, "name": name}
            for fo in futures.as_completed(futsdic):
                fu = futsdic[fo]
                score, text, found = fo.result()
                if score >= 2:
                    num_c_pages += 1
                    ext = mimetypes.guess_extension(fu["tp"])
                    if (ext == ".jpe"):
                        ext = ".jpeg"   # fucking hell
                    fname = os.path.join(args.outdir,
                                         "{:03d}{}".format(num_c_pages, ext))
                    with open(fname, 'w+b') as dest:
                        print("Found {} -> {}, score {:.1f}"
                              .format(os.path.join(os.path.basename(archive),
                                                   fu["name"]),
                                      fname, score))
                        dest.write(fu["pdat"])
                        dest.flush()
                        with open(fname + ".json", 'w') as meta:
                            json.dump({"score": score,
                                       "text": text,
                                       "found": found}, meta)
                            meta.flush()


if __name__ == "__main__":
    main()
