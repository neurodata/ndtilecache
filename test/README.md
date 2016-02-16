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

##### Multi Process Benchmark
  * Run a test on production server
  ```sh
  python parallel_benchmark.py kasthuri11 image 5
  ```

  * Run a test on dev server
  ```sh
  python parallel_benchmark.py kasthuri11 image 5 --server localhost:8000
  ```
