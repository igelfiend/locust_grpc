# Locust Grpc
This is Locust load tests for some endpoint. Read further for more context.


# Description
Package contains:
    - local server (in progress, lack bunch of endpoints, be aware)
    - grpc tools, allows to use locust + grpc properly (unary-unary and unary-stream cases handled, but stream-stream WIP)
    - proto directory, with some proto files
    - locustfile with all load test logic
    - scripts to simplify compile and run

# Installation
Run:
- install python dependencies: `pip3 install -r requirements.txt`
- compile python versions of proto: `./compile_protos.bash`
- recommended - create `.env` file, will be explained below.

# Run requirements
This load test supports up to 9 users and works both for local and for remote.

Required setup steps:
- define user credentials in your environment (`.env`) in format like `CREDENTIAL_1="email:password"` (up to 9 users).
- define `REMOTE_URL` path in your environment if is needed to test a remote.
- if there is required to use not 3 but more/less users, some updates should be done:
    - provide requried credentials
    - update run bash script in locust section: update `--users` argument with value `new_users_counht * 2` (because one does chores, and one check for available vacancies)

# Usage
To use this test do either:
    - run `./run_locust_for_remote.bash` (don't forget about remote url and creds) to test remote
    - run `./run_locust_on_local_server` (don't forget to update server/test in that case)
