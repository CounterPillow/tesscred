# tesscred
Uses tesseract to find and retrieve credit pages in manga archives


## Dependencies

* python >= 3.3
* tesseract
* tesseract-data-eng


## Usage

    ./tesscred.py [options] mangadir outdir

tesscred will recursively scan `mangadir` for .zip/.cbz archives and read
those, writing out credit pages sequentially to `outdir` together with some
metadata about the scanning contained in a json file for each page.


### Options

* `--workers, -w` Number of instances of tesseract to launch in parallel


## License

Code is licensed under MIT, see the `LICENSE` file in this repository. Author
retains the right to re-license code as they see fit.
