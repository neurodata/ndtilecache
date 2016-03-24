### Sample Test Commands

* Run a test on production server
```sh
python ndtilecache_benchmark.py kasthuri11 image 5
```
* Run a test with a single thread
```sh
python ndtilecache_benchmark.py kasthuri11 image 5 --num 1
```
* Run a test on dev server
```sh
python ndtilecache_benchmark.py kasthuri11 image 5 --server localhost:8000
```
* Run a test on dev server till slice 2
```sh
python ndtilecache_benchmark.py kasthuri11 image 5 --server localhost:8000 --max 2
```
* Run a test on producrion server with xtile range 0 to 5
```sh
python ndtilecache_benchmark.py kasthuri11 image 5 --x 0 3
```
