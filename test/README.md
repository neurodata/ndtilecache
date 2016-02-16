### Sample Test Commands

##### Single Process benchmark
  * Run a test on production server
  ```sh
  python simple_benchmark.py kasthuri11 image 5
  ```
  
  * Run a test on dev server
  ```sh
  python simple_benchmark.py kasthuri11 image 5 --server localhost:8000
  ```
  * Run a test on dev server till slice 2
  ```sh
  python simple_benchmark.py kasthuri11 image 5 --server localhost:8000 --max 2
  ```

##### Multi Process Benchmark
  * Run a test on production server
  ```sh
  python parallel_benchmark.py kasthuri11 image 5
  ```

  * Run a test on dev server
  ```sh
  python parallel_benchmark.py kasthuri11 image 5 --server localhost:8000
  ```
