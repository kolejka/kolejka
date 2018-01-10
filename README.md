Welcome to _kolejka_
====================

**kolejka** is a lightweight task scheduling platform developed for a small computational grid at Faculty of Mathematics and Computer Science of the Jagiellonian University in Kraków.

Each task is described by a set of files, and a command to run in a docker container.

See our [quickstart guide](wiki/Quickstart) if you want to quickly execute some tasks.

Example
-------
For example, the following task executes command `uname` in a standard ubuntu container with reasonable time/cpu/mem limits and collects standard output.

* `kolejka_task.json`:
```json
{
    "image"  : "ubuntu:xenial",
    "args"   : [ "uname" ],
    "limits" : {
        "memory" : "64M",
        "cpus"   : "1",
        "pids"   : "16",
        "time"   : "1s"
    },
    "stdout" : "stdout.txt"
}
```

The result of running this task in our system is described by two files:

* `kolejka_result.json`:
```json
{
    "result" : 0,
    "files"  : [
        "stdout.txt"
    ]
}
```

* `stdout.txt`:
```
Linux
```

You can check our [Task](wiki/Task), and [Result](wiki/Result) specification and see other [Examples](wiki/Examples).

Usage
-----

You can use `kolejka-client` to schedule tasks and download results from the server.
To schedule a task and wait for the result:
```
$ kolejka-client execute TASK_PATH RESULT_PATH
```
To schedule a task:
```
$ kolejka-client task put TASK_PATH
```
To fetch a result:
```
$ kolejka-client result get TASK_KEY
```

`kolejka-server` is a standard django manage script that can be used to control Kolejka Server. 
```
$ kolejka-server runserver
```
More details on Server installation and maintenance can be found in [Server Documentation](wiki/Server).
You need to run Kolejka Foreman system on the grid nodes.

You can use `kolejka-worker` to run tasks on your own computer. You need to install and run `docker-ce` and `kolejka-observer` in your system.
```
$ kolejka-worker execute TASK_PATH RESULT_PATH
```

`kolejka-foreman` is a simple script that downloads pending tasks from the server, runs them, and sends results back to the server.

Design Goals
------------

TODO

Subsystems
----------

The platform is divided into the following subsystems:

* [Server](wiki/Server) - Stores files and descriptions of tasks and results. Schedules execution of tasks. Defines security and access rights. Runs post-execution steps.
* [Client](wiki/Client) - CLI and a set of convenience wrappers.
* [Worker](wiki/Worker) - A script that runs a single task and collects the result.
* [Observer](wiki/Observer) - A standalone server that allows docker contained applications to do basic cgroups-based system usage accounting.
* [Foreman](wiki/Foreman) - An operating system image that controls one node in the grid - uses all system resources to run Workers.

Acknowledgments
---------------

The platform is written in Python using the following building blocks:

* [django](https://djangoproject.com) - For server implementation.
* [docker](https://docker.com) - For task system image description and task execution containment.
* [cgroups](https://www.kernel.org/doc/Documentation/cgroup-v1/cgroups.txt) - For grid usage accounting.
* [JSON](https::/json.org) - For task / result description and API communications.

Temporary project logo is a slightly modified Mountain Railway Emoji (🚞) from [Google](https://github.com/googlei18n/noto-emoji/blob/master/svg/emoji_u1f69e.svg)

License
-------

Kolejka system is released under MIT License.
