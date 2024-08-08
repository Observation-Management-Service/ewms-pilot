# CHANGELOG



## v0.24.2 (2024-08-08)

###  

* &lt;bot&gt; update dependencies*.log files(s) ([`5ed749f`](https://github.com/Observation-Management-Service/ewms-pilot/commit/5ed749f1ca3af4b7b125037c2a4f5eed2eeeb25e))

* Quick Fix Chirping ([`91028ac`](https://github.com/Observation-Management-Service/ewms-pilot/commit/91028ac364d53caa956ebae81102c53870d5b553))

* Use Module-based Logging ([`328a21c`](https://github.com/Observation-Management-Service/ewms-pilot/commit/328a21c7d78a00b5e4bcb2c8727f9a341db3982b))


## v0.24.1 (2024-08-07)

###  

* Support Singularity/Apptainer Directory Image (#86) ([`466e46e`](https://github.com/Observation-Management-Service/ewms-pilot/commit/466e46ed0528c30ac552d84baef781c5e0ce0075))


## v0.24.0 (2024-08-06)

### [minor]

* Apptainer-in-Apptainer Improvements [minor] (#85) ([`23df1ed`](https://github.com/Observation-Management-Service/ewms-pilot/commit/23df1eda4515965877553a0e62fb411ae07da067))


## v0.23.12 (2024-08-02)

###  

* Support Apptainer-in-Apptainer (#84) ([`ed15b71`](https://github.com/Observation-Management-Service/ewms-pilot/commit/ed15b71d5348a7af70a5121f48a900f29754f6e2))


## v0.23.11 (2024-08-02)

###  

* Only Run `dockerd` If Needed - 3 ([`9fdba69`](https://github.com/Observation-Management-Service/ewms-pilot/commit/9fdba69365119ec8bbf5e2b95b5108d40da79c63))

* Only Run `dockerd` If Needed - 2 ([`b87961a`](https://github.com/Observation-Management-Service/ewms-pilot/commit/b87961a44e232cf776a73b1c328e627c64b0870c))

* Only Run `dockerd` If Needed ([`7fcafbc`](https://github.com/Observation-Management-Service/ewms-pilot/commit/7fcafbc73228666737265cb23e11d47d00ab87fc))


## v0.23.10 (2024-08-02)

###  

* In-Task Docker Fixes ([`63dac58`](https://github.com/Observation-Management-Service/ewms-pilot/commit/63dac582e5d06cc50e9f3b423aeec2bc9e32853a))


## v0.23.9 (2024-08-01)

###  

* Root `ewms-pilot-data/` at `$PWD` (`entrypoint.sh`) ([`b7decf5`](https://github.com/Observation-Management-Service/ewms-pilot/commit/b7decf551af3b54f366ae82c88cd385fe2bb32fe))


## v0.23.8 (2024-08-01)

###  

* Root `ewms-pilot-data/` at `$HOME` (`entrypoint.sh`) ([`28584ad`](https://github.com/Observation-Management-Service/ewms-pilot/commit/28584ad78d441828767e72d4dc72561e825ef6f5))


## v0.23.7 (2024-08-01)

###  

* Add Debugging Info to `entrypoint.sh` - 2 ([`73f8dbd`](https://github.com/Observation-Management-Service/ewms-pilot/commit/73f8dbdf5bac2ba28e724cca7cfa85fb3efe767d))


## v0.23.6 (2024-08-01)

###  

* Add Debugging Info to `entrypoint.sh` ([`d629aca`](https://github.com/Observation-Management-Service/ewms-pilot/commit/d629aca68daeca6447497995c3dc4daecc23ad6f))


## v0.23.5 (2024-08-01)

###  

* Move `ewms-pilot-data/` Setup to `entrypoint.sh` ([`c9143b9`](https://github.com/Observation-Management-Service/ewms-pilot/commit/c9143b976ffb3b5084f999d468cf8a829e46877c))


## v0.23.4 (2024-08-01)

###  

* Add Env Var for Setting Pilot Root Dir on Host (#83)

* Add Env Var for Setting Pilot Root Dir on Host

* call it the data hub

* now, in task containers

* use var ([`f1bcdc1`](https://github.com/Observation-Management-Service/ewms-pilot/commit/f1bcdc1f84c37564b95afeec1e7017e37b6d7db6))


## v0.23.3 (2024-07-31)

###  

* File Permissions for `/ewms-pilot/` - 2 ([`b65d407`](https://github.com/Observation-Management-Service/ewms-pilot/commit/b65d40788b5152e2451a374c2167b0a3baac9d0f))


## v0.23.2 (2024-07-31)

###  

* File Permissions for `/ewms-pilot/` ([`f4521cc`](https://github.com/Observation-Management-Service/ewms-pilot/commit/f4521cc83cf5079bc40e3e4c4b12a4bf37948c49))


## v0.23.1 (2024-07-31)

###  

* Update `entrypoint.sh` Startup Dump ([`749736c`](https://github.com/Observation-Management-Service/ewms-pilot/commit/749736c9bf009b77cdb1effa098232ae808c10f8))


## v0.23.0 (2024-07-30)

###  

* make some env vars required ([`3473a2b`](https://github.com/Observation-Management-Service/ewms-pilot/commit/3473a2ba2d26f905ac014366b2c75a2427395b74))

### [minor]

* Remove CL Args [minor] (#82)

* no more cl args

* flake8

* misc ([`7ebc53a`](https://github.com/Observation-Management-Service/ewms-pilot/commit/7ebc53af9f15bf86ce5be5937040e57e4a716415))


## v0.22.4 (2024-07-29)

###  

* Set CL Args Defaults ([`207925f`](https://github.com/Observation-Management-Service/ewms-pilot/commit/207925f40e48e5ea91a039d355313794880475c5))


## v0.22.3 (2024-07-29)

###  

* Fix CL Args - 2 ([`8538c71`](https://github.com/Observation-Management-Service/ewms-pilot/commit/8538c71850820ce5b8d78ba6d5ec73096d85ba16))

* Fix CL Args ([`0b91a17`](https://github.com/Observation-Management-Service/ewms-pilot/commit/0b91a178508e154ba4ab386b4a83d6e904abe13c))


## v0.22.2 (2024-07-29)

###  

* Fix CVMFS Publishing - 2 ([`cefd4ee`](https://github.com/Observation-Management-Service/ewms-pilot/commit/cefd4ee7c50b24387452ad70c8fe06c88dacb86a))


## v0.22.1 (2024-07-29)

###  

* Fix CVMFS Publishing ([`9c681ad`](https://github.com/Observation-Management-Service/ewms-pilot/commit/9c681ad702de93ac1dbad5a827424ba028ce1c31))


## v0.22.0 (2024-07-29)

###  

* update release ci ([`7f117a1`](https://github.com/Observation-Management-Service/ewms-pilot/commit/7f117a107e9b57d2cc554ae493cce3e3ce53d40a))

* Use `WIPACrepo/wipac-dev-py-setup-action@v4.1`/`pyproject.toml` (#81)

* Use `WIPACrepo/wipac-dev-py-setup-action@v4.0`/`pyproject.toml`

* args

* &lt;bot&gt; update dependencies*.log files(s)

* use `WIPACrepo/wipac-dev-py-setup-action@auto-create-toml`

* &lt;bot&gt; added pyproject.toml -- user needs to set values for auto-added fields

* manually set fields

* manually set fields - 2

* manually set fields - 3

* manually set fields - 4

* manually set fields - 5

* manually set fields - 6

* rm setup.cfg

* &lt;bot&gt; update pyproject.toml

* &lt;bot&gt; update README.md

* use `WIPACrepo/wipac-dev-py-versions-action@v2.4`

* &lt;bot&gt; update pyproject.toml

* `pypi_name: ewms-pilot`

* &lt;bot&gt; update pyproject.toml

* &lt;bot&gt; update README.md

* &lt;bot&gt; update README.md

* use `WIPACrepo/wipac-dev-py-setup-action@v4.1`

---------

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`c9abdbb`](https://github.com/Observation-Management-Service/ewms-pilot/commit/c9abdbb05d89e28c5751082f4709fe9b45cca04f))

### [minor]

* Define a Task via Image &amp; Args (Also, &#34;Init Container&#34;) [minor] (#80)

* Define a Task via `--task-image` &amp; `--task-args` (init too)

* run as container

* &lt;bot&gt; update dependencies*.log files(s)

* upde

* mypy

* `--exitfirst`

* temp: don&#39;t do test concurrently

* work w/ `python -c`

* temp: don&#39;t use `python -c`

* dump task outputs on error always

* fix bind mount

* Revert &#34;temp: don&#39;t use `python -c`&#34;

This reverts commit 2dfa5840c27d45ca6cc913e6311e27d331507dd7.

* add check if outfile was not written

* tests: simplify debug dir check

* tests: simplify debug dir check - 2

* tests: simplify debug dir check - 3

* tests: simplify debug dir check - 4

* tests: simplify file tree check

* mypy

* Revert &#34;work w/ `python -c`&#34;

This reverts commit 918778b9c2eb333984ab2b3a69b405ca150257a9.

* pre-pull images for testing

* tests: increase expected runtime per task by 3 sec

* tests: remove unused, commented-out args

* use `__name__`-based logging

* revamp dir handling -- tests will fail

* remove extra cleanup

* run test individually in containers - 1

* run test individually in containers - 2

* run test individually in containers - 3

* run test individually in containers - 4

* run test individually in containers - 5

* run test individually in containers - 5 (ubuntu)

* run test individually in containers - 7 (ubuntu)

* run test individually in containers - 8 (`python:alpine /bin/sh`)

* run test individually in containers - 9 (`cd /repo/`)

* make `Dockerfile`; run `pytest` inside

* &lt;bot&gt; update dependencies*.log files(s)

* make `Dockerfile`; run `pytest` inside - 2

* make `Dockerfile`; run `pytest` inside - 3 (install pytest)

* make `Dockerfile`; run `pytest` inside - 4 (docker args)

* syntax

* docker arg placement

* tests: add missing install - 3

* tests: add missing install - 4

* tests: fix pytest run with nodeid

* docker: pre-create `/ewms-pilot` w/ chown

* docker: install docker in docker

* docker: install docker in docker - 2

* `-v /var/run/docker.sock:/var/run/docker.sock`

* install `sysbox`

* docker run with `--runtime=sysbox-runc --hostname syscont`

* remove `--network=&#34;host&#34;`; map each port

* `-P`

* revert

* `--net=mynet`

* `--net=mynet` - 2

* `--net=mynet` - 3 (`-p 5672:5672`)

* `--net=mynet` - 4 (remove all `-p`)

* copypasta typo

* add sleep for broker startup

* (debug)

* (debug - 2)

* (debug - 3)

* (debug - 4)

* (debug - 5)

* (debug - 6 - 180s)

* (debug - 7 - subshell)

* (debug - 8 - no `&amp;`)

* (debug - 9 - pre-pull images)

* (debug - 10 - 20s)

* (debug - 11 - `docker network inspect mynet`)

* (debug - 12 - `--runtime=sysbox-runc \`)

* tests: use broker container name for `*BROKER_ADDRESS`

* tests: use `BROKER_CONTAINER_NAME`

* add back `--hostname=syscont` for pilot container

* `sudo systemctl status sysbox -n20`

* add `dockerd &gt; /var/log/dockerd.log 2&gt;&amp;1 &amp;` to `entrypoint.sh`

* `RUN chown app /var/log/dockerd.log`

* `RUN chown app /var/log/dockerd.log` - 2

* (debug)

* (debug - 2)

* remove docker `app` user - 2

* `RUN mkdir -p /ewms-pilot/store`

* comments

* decrease wait time after `dockerd`

* in an incredible effort, clean up today&#39;s ci updates

* for the third time today, fix the examples

* too fast

* cleanup

* tests: fix dir checks

* (debug)

* mypy

* `EWMS_PILOT_KEEP_ALL_TASK_FILES: True`

* mypy - 2

* call it `DirectoryCatalog`

* tests: fix n dir check

* fix dir check - 2

* fix filetree check

* fix filetree check - 2

* fix filetree check - 3

* mypy

* remove file system check - was overkill anyway

* remove `docker ps` from `entrypoint.sh`

* for loop fix

* (debug)

* remove `-i`

* run tests in parallel

* run tests in parallel - 2

* run tests in parallel - 3

* run tests in parallel - 4

* cleanup test refactor

* run tests in parallel - 5

* `jlumbroso/free-disk-space@main`

* Revert &#34;`jlumbroso/free-disk-space@main`&#34;

This reverts commit 4bbdc6eae0cbdedabefe73d3d381822fbc1e24a9.

* sleep so the broker doesn&#39;t get overwhelmed

* pass `EWMS_TASK_PILOT_STORE_DIR` to each container

* test typo

* mypy

* no trailing `/`

* `--shm-size=2g`

* `sleep 5`

* `--retries 3 --retry-delay 3 `

* put nats in a container

* remove pytest retries

* mkdirs

* typo

* tests: adjust timeout

* update broker runs

* try nat&#39;s docker image (probably won&#39;t work)

* add extra sleep

* try creating docker network in own step

* add `pytest container outputs` step

* remove `time`

* remove `time` - 2

* add `get list of pytest tests` step

* add `get list of pytest tests` step - use file

* add `get list of pytest tests` step - use file - 2

* add `get list of pytest tests` step - use file - 3

* add `get list of pytest tests` step - use file - 4

* add `get list of pytest tests` step - use file - 5

* adjust sleeps

* adjust sleeps - 2

* `nats:2.10.18 -js`

* try image caching (again)

* try image caching (again) - 2

* (temp: pre-pull in entrypoint.sh)

* do `docker save` &amp; `docker load` for caching

* do `docker save` &amp; `docker load` for caching - 2

* do `docker save` &amp; `docker load` for caching - 3

* clean up rabbitmq `docker run`

* move `docker load` to command

* `SORTED_LIST_OF_TESTS_FILE`

* get a preview of the test output

* use `/bin/bash -c`

* `set +x` / `set -x`

* add env vars for broker image tags

* speed up rabbitmq tests

* don&#39;t build extra images

* `date --rfc-3339=seconds`

* adjust sleep

* Revert &#34;speed up rabbitmq tests&#34;

This reverts commit ce1824e16907f1ec48f0a5288f3255aae91f2cd3.

* rename test

* speed up rabbitmq tests

* make it okay if docker-in-docker setup fails in `entrypoint.sh`

* add entrypoint terminal message

* pytest arg

* use `ts` with `entrypoint.sh`

* tweak terminal echo

* tweak terminal echo

* Revert &#34;use `ts` with `entrypoint.sh`&#34;

This reverts commit 86552e33

* tweak terminal echo - 2

* tweak terminal echo - 3

* tweak terminal echo - 4

* remove `Dockerfile_example`

* adjust image names

* remove `pytest-xdist`

* `--retries 1 --retry-delay 5`

* add `EWMS_PILOT_EXTERNAL_DIRECTORIES`

* &lt;bot&gt; update setup.cfg

* add `EWMS_PILOT_EXTERNAL_DIRECTORIES` - 2

* ok if output file not exist when tests fail

* `EWMS_PILOT_EXTERNAL_DIRECTORIES` - 3

* &#34;Entering the Task Pilot Container Environment&#34;

* `sleep .1`

* print pip-supplied info

* fix bind mount string

* (debug)

* print pip info after activation

* print pip info after activation - 2

* `docker rm $(docker ps -a -q) -f  ||  true`

* reorg Dockerfile

* use `WIPACrepo/wipac-dev-py-dependencies-action@image`

* fix Dockerfile

* edit echo message

* edit (another) echo message

* &lt;bot&gt; update dependencies*.log files(s)

* &lt;bot&gt; update dependencies*.log files(s)

* (test pre-building images for deps gha)

* (test pre-building images for deps gha - 2)

* (test pre-building images for deps gha - 3)

* (test pre-building images for deps gha - 4)

* (test pre-building images for deps gha - 5 - temp)

* (test pre-building images for deps gha - 7)

* (debug)

* use py-versions for deps

* all combos

* use `jlumbroso/free-disk-space@main`

* don&#39;t use `jlumbroso/free-disk-space@main`

* `docker system prune --force`

* pre-pull to speed up dependent images

* pre-pull to speed up dependent images - 2

* adjust entrypoint echo

* &lt;bot&gt; update dependencies*.log files(s)

* use `use_directory`

* &lt;bot&gt; update dependencies*.log files(s)

* &lt;bot&gt; update dependencies*.log files(s)

* first, build the vanilla/default image

* &lt;bot&gt; update dependencies*.log files(s)

* &lt;bot&gt; update dependencies*.log files(s)

* &lt;bot&gt; update dependencies*.log files(s)

* use `WIPACrepo/wipac-dev-py-dependencies-action@v2.0`

* use helper script to start brokers

* use helper script to start brokers - 2

* `git update-index --chmod=+x`

* source the scripts

* (debug)

* (debug - 2)

* fix docker logs

* `--network=host` - 2

* &lt;bot&gt; update dependencies*.log files(s)

* add more to example job

* remove examples, if needed, that should be in the README

* &lt;bot&gt; update README.md

* remove extra TODO

* revert README

* &lt;bot&gt; update README.md

---------

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`d24e052`](https://github.com/Observation-Management-Service/ewms-pilot/commit/d24e052ce1eafef4f38a2465968fc94ad1581924))


## v0.21.0 (2024-06-21)

### [minor]

* Require: Broker Info for Each Queue, Use of Env Vars [minor] (#79)

* gut cl args, rely on env vars

* add incoming / outgoing env vars

* reorganize env vars

* &lt;bot&gt; update dependencies*.log files(s)

* call it `EWMS_PILOT_MAX_CONCURRENT_TASKS`/`max_concurrent_tasks` (not multitasking)

* fix ci

* fix tests

---------

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`378f1d8`](https://github.com/Observation-Management-Service/ewms-pilot/commit/378f1d8cd4dd27aa486e6a50e5860f62db116249))


## v0.20.0 (2024-06-19)

### [minor]

* Replace Multi-Queue Auth with Per-Queue Auth [minor] (#77)

* Replace Multi-Queue Auth with Per-Queue Auth

* &lt;bot&gt; update dependencies*.log files(s)

* test comments

* fix merge

* &lt;bot&gt; update setup.cfg

* pt 2

* remove `--auth-token`

* ci: remove unused env var

---------

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`7951096`](https://github.com/Observation-Management-Service/ewms-pilot/commit/7951096ec83c88a8812afb4e4b8a346659881264))

* Simplify Queue-File Data Transfer [minor] (#78)

* reorganize `consume_and_reply()` args

* remove io-tool, aka don&#39;t deserialize/reserialize data

* &lt;bot&gt; update dependencies*.log files(s)

* update tests

* update tests - 2

* remove extra args

* ``--maxfail=1`

* fix file write

* make user serialize

* make user serialize - 2

* bytes are okay

* fix data writing

* fix data reading

* mypy

* always bytes

* &lt;bot&gt; update dependencies*.log files(s)

* use `try-except` for file reading detection

* mypy

* &lt;bot&gt; update dependencies*.log files(s)

* &lt;bot&gt; update dependencies*.log files(s)

* &lt;bot&gt; update dependencies*.log files(s)

* &lt;bot&gt; update dependencies*.log files(s)

* add `io.FileExtension`; remove pylint comments

* use `apptainer-version: 1.3.2`

* force extension to lower case

* py 3.12

* &lt;bot&gt; update setup.cfg

* &lt;bot&gt; update dependencies*.log files(s)

* file extension redux

* fix test

* move file io to `io.py`

* wording

* comments

* fix tests

* update pickle test

* flake8

* fix test - 2

* comment

* fix test - 3

* rename infile/outfile to `infile-...` &amp; `outfile-...`

* pt 2

* fix user pkl test (no newline)

* use uuid in pattern

* mypy

* allow json data

* add json test

---------

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`f8fd854`](https://github.com/Observation-Management-Service/ewms-pilot/commit/f8fd85401c01b2b75894d23dec4d891f357ec86f))


## v0.19.0 (2024-05-03)

### [minor]

* Update Queue Timeout Config [minor] (#75)

* remove needless &#34;outgoing timeout&#34;

* update example script

* add env vars for queue timeouts

* update ci example job ([`cc69c8e`](https://github.com/Observation-Management-Service/ewms-pilot/commit/cc69c8e8da4721051d46f653716be8e3d03d0b78))


## v0.18.7 (2024-05-02)

###  

* Add `EWMS_PILOT_QUEUE_INCOMING` &amp; `EWMS_PILOT_QUEUE_OUTGOING` (#74)

* Add `EWMS_PILOT_QUEUE_INCOMING` &amp; `EWMS_PILOT_QUEUE_OUTGOING`

* &lt;bot&gt; update setup.cfg

* &lt;bot&gt; update dependencies*.log files(s)

* update ci

* update ci - 2

---------

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`dbf2544`](https://github.com/Observation-Management-Service/ewms-pilot/commit/dbf2544bc18b8370ceea3836e0600a4dc0c6b72a))


## v0.18.6 (2024-03-15)

###  

* Add `entrypoint.sh` (#72)

* Add `entrypoint.sh`

* add to Dockerfile ([`00d955d`](https://github.com/Observation-Management-Service/ewms-pilot/commit/00d955dd888a850938d87595818fdb5acb8a7c23))


## v0.18.5 (2024-03-15)

###  

* Fix Container Tag ([`81f44cd`](https://github.com/Observation-Management-Service/ewms-pilot/commit/81f44cd709cd7564ab91ca5aa4a25791238bcaf5))


## v0.18.4 (2024-03-14)

###  

* CI: Update Versions &amp; Patch Args ([`ea25f6f`](https://github.com/Observation-Management-Service/ewms-pilot/commit/ea25f6f20800a25046ef29c288c21e1398552390))


## v0.18.3 (2024-03-14)

###  

* Update Example Script &amp; Add Dockerfile for CVMFS (#71)

* Update Example Script

* mv example.py

* update ci

* &lt;bot&gt; update dependencies*.log files(s)

* pt 2

* use gha `concurrency`

* pt 3

* add `test-build-singularity`

* update example

* check output

* update docker jobs

* python -c update

* add env var

* add image publish ci

---------

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`b8806d9`](https://github.com/Observation-Management-Service/ewms-pilot/commit/b8806d939ca82351a6cde9495106a08e52719e39))


## v0.18.2 (2024-03-14)

###  

* &lt;bot&gt; update dependencies*.log files(s) ([`b81931b`](https://github.com/Observation-Management-Service/ewms-pilot/commit/b81931b80d709b38c163583819338eb781f0ca60))


## v0.18.1 (2024-03-14)

###  

* Use `EWMS_PILOT_HTCHIRP_DEST` (#69)

* Use `EWMS_PILOT_HTCHIRP_DEST`

* (test)

* don&#39;t use `Literal`

* flake8

* Revert &#34;(test)&#34;

This reverts commit eac9e3adb12d6280707e6d30c4197db166e39f2a. ([`4394c45`](https://github.com/Observation-Management-Service/ewms-pilot/commit/4394c45cdc35328d1f870efdb47808ad50ee708d))


## v0.18.0 (2024-03-08)

### [minor]

* Chirp to Job Event Log (Opt. by `EWMS_PILOT_HTCHIRP_VIA_JOB_EVENT_LOG`) [minor] (#68)

* Chirp to Job Event Log (Opt. by `EWMS_PILOT_HTCHIRP_VIA_JOB_EVENT_LOG`)

* &lt;bot&gt; update dependencies*.log files(s)

* append `HTChirpEWMSPilot` when chirping (condense)

* fix chirp name

* use const

---------

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`a06aa3d`](https://github.com/Observation-Management-Service/ewms-pilot/commit/a06aa3daa131009d739db864a280836fcb43f3ac))


## v0.17.7 (2023-12-01)

###  

* Bump `mqclient` (#66)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`9211545`](https://github.com/Observation-Management-Service/ewms-pilot/commit/9211545aac88aae95306c454fef449706d6b9dde))


## v0.17.6 (2023-11-30)

###  

* Refactor to `EWMS_PILOT_CL_LOG` and `EWMS_PILOT_CL_LOG_THIRD_PARTY` (#65)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`633474f`](https://github.com/Observation-Management-Service/ewms-pilot/commit/633474f80ac77e5df8aeb2a5984084ebb3540150))


## v0.17.5 (2023-11-17)

###  

* HTChirp: Send Backlog at End (#64) ([`f6c860d`](https://github.com/Observation-Management-Service/ewms-pilot/commit/f6c860d8d5744a9ac6a8b846057294488379564e))


## v0.17.4 (2023-11-15)

###  

* HTChirp: Use Enums for Status (#63)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`5c61231`](https://github.com/Observation-Management-Service/ewms-pilot/commit/5c61231aa10e4b4dcc62279b3ba669a025d38f86))


## v0.17.3 (2023-11-08)

###  

* HTChirp: Rate Limit Very Frequently Updated Attrs (#62) ([`d9501b5`](https://github.com/Observation-Management-Service/ewms-pilot/commit/d9501b5860cc30762ff3550f3c2cb8dadcdd3ae2))


## v0.17.2 (2023-11-08)

###  

* HTChirp: Reduce Number of Connections - 2 ([`6c9a977`](https://github.com/Observation-Management-Service/ewms-pilot/commit/6c9a977b765fa602e360664405c1aa56943233c0))

* &lt;bot&gt; update dependencies*.log files(s) ([`e7bbb66`](https://github.com/Observation-Management-Service/ewms-pilot/commit/e7bbb66fd0ee1ae936acacec7f224f5fe86dc7b9))

* &lt;bot&gt; update setup.cfg ([`0c236dd`](https://github.com/Observation-Management-Service/ewms-pilot/commit/0c236ddc20185f2c133995a8e84e9076f900400b))

* HTChirp: Update Dependencies - 2 ([`68955be`](https://github.com/Observation-Management-Service/ewms-pilot/commit/68955be294fd012a2fa99ad3414b959719b24e09))

* HTChirp: Update Dependencies ([`1361d26`](https://github.com/Observation-Management-Service/ewms-pilot/commit/1361d26491974b3490313dd76bc63917bbdeb49f))

* HTChirp: Reduce Number of Connections ([`4732e97`](https://github.com/Observation-Management-Service/ewms-pilot/commit/4732e9753b074e2bebfe595f2bc7c95c1e917d29))

* HTChirp: Use `classad.quote()` ([`9a99e29`](https://github.com/Observation-Management-Service/ewms-pilot/commit/9a99e29fd4ccf20eae1b5bb396e2df5bc9cae3c5))


## v0.17.1 (2023-11-07)

###  

* HTChirp: Fix Condor Type Usage ([`7723254`](https://github.com/Observation-Management-Service/ewms-pilot/commit/77232544387740a6425ea77524f78b14a8fa9a41))


## v0.17.0 (2023-11-06)

###  

* HTChirp: Improved Error Handling - 2 ([`de704ca`](https://github.com/Observation-Management-Service/ewms-pilot/commit/de704ca547ff9336a10602429a4606453d077c88))

* HTChirp: improved error handling ([`363a38f`](https://github.com/Observation-Management-Service/ewms-pilot/commit/363a38fe3197e403d632323650df58bced143969))

### [minor]

* Add `EWMS_PILOT_STOP_LISTENING_ON_TASK_ERROR` [minor] (#61) ([`d772bc7`](https://github.com/Observation-Management-Service/ewms-pilot/commit/d772bc720fbe9734ff4d73881fda47625ecd1154))


## v0.16.3 (2023-11-03)

###  

* CI Testing: Handle Occasional Pulsar Connection Issues - 2 ([`4bc6b40`](https://github.com/Observation-Management-Service/ewms-pilot/commit/4bc6b40a1c27eb35b7155cd6edd4f71982450e44))

* CI Testing: Handle Occasional Pulsar Connection Issues (#60) ([`60fa378`](https://github.com/Observation-Management-Service/ewms-pilot/commit/60fa378f079fe680ab382ae873d061d730a96445))

* HTChirp: Add `HTChirpEWMSPilotErrorTraceback` (#59) ([`5aaeae2`](https://github.com/Observation-Management-Service/ewms-pilot/commit/5aaeae202b63305e0e9bbf2f86bbf0c2e6ae4d04))


## v0.16.2 (2023-11-02)

###  

* Bump Python Min to 3.9 &amp; Update Tests (#58)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`806e8ed`](https://github.com/Observation-Management-Service/ewms-pilot/commit/806e8ed371ac1cb5cc5daffdae9c6a0fc6c912e9))

* Add More Info for a Subprocess `TimeoutError` - 2 (#57) ([`c9fc397`](https://github.com/Observation-Management-Service/ewms-pilot/commit/c9fc39706a973c1f42d53e2d1a694d5bbde490aa))

* Add More Info for a Subprocess `TimeoutError` (#56) ([`469ecf6`](https://github.com/Observation-Management-Service/ewms-pilot/commit/469ecf6c11c87b170ed4d7d36f91d9fabf03e1ba))


## v0.16.1 (2023-11-02)

###  

* HTChirp Attr Updates (#55) ([`998e4b4`](https://github.com/Observation-Management-Service/ewms-pilot/commit/998e4b40b7d285e7fa56a8cd8080478f4ac6ad9c))


## v0.16.0 (2023-11-01)

### [minor]

* HTChirp: Validation, Fix Typing Syntax, &amp; Update Attrs [minor] (#54)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`68ba5ca`](https://github.com/Observation-Management-Service/ewms-pilot/commit/68ba5ca1dc72e1882afdfc8e9cf4b969efbbd0e9))


## v0.15.1 (2023-10-02)

###  

* Permit Multiple Init Directories (#53)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`f8b857c`](https://github.com/Observation-Management-Service/ewms-pilot/commit/f8b857c84adb5f969e0a8dfcb5f8e948fc0afb90))


## v0.15.0 (2023-09-29)

### [minor]

* Init Command [minor] (#52) ([`aab5ad5`](https://github.com/Observation-Management-Service/ewms-pilot/commit/aab5ad53908f0ae07f2d375a196590d6fe7cba8c))


## v0.14.1 (2023-09-29)

###  

* Finish Restructuring Directories ([`1bbd1d6`](https://github.com/Observation-Management-Service/ewms-pilot/commit/1bbd1d6b9c55dd8e7cc8fd0ab75cdbc37eb9e301))

* Restructure Directories ([`034ff46`](https://github.com/Observation-Management-Service/ewms-pilot/commit/034ff46963dd45bafb4e31c1694cfc1f69418a7f))

* Split Off `subproc.py` ([`6da47b3`](https://github.com/Observation-Management-Service/ewms-pilot/commit/6da47b33b784c4a81668e73dc0d7aff466dee1e8))

* [split: restore `task.py`] ([`d0a2229`](https://github.com/Observation-Management-Service/ewms-pilot/commit/d0a22290ab5ab22b8535947280fdf49acb08f0ca))

* [split: add `subproc.py`] ([`8ef66b7`](https://github.com/Observation-Management-Service/ewms-pilot/commit/8ef66b77f45c1e9a3a552dfb1399a84965df56c9))

* [split: temp] ([`cf4422a`](https://github.com/Observation-Management-Service/ewms-pilot/commit/cf4422a23b961f6bdff8e053c9c351b250aa9ca5))

* [split: make `subproc.py`] ([`c2240c8`](https://github.com/Observation-Management-Service/ewms-pilot/commit/c2240c877de2e147b1a07b1870504015238e8e57))


## v0.14.0 (2023-09-27)

### [minor]

* Optionally Dump Subprocess Output On Task Finish [minor] (#50) ([`f507cce`](https://github.com/Observation-Management-Service/ewms-pilot/commit/f507cce8376dd7467db8614ba85de92681d9bc4a))


## v0.13.0 (2023-09-27)

###  

* Split Off `htchirp_tools.py.py` ([`5d8375e`](https://github.com/Observation-Management-Service/ewms-pilot/commit/5d8375e592b0fe4dba67bbb627c9acf960669a07))

* [split: restore `utils.py`] ([`7193f30`](https://github.com/Observation-Management-Service/ewms-pilot/commit/7193f308bbb5b634e3575b6d51518e39680860b0))

* [split: add `htchirp.py`] ([`1c78a5c`](https://github.com/Observation-Management-Service/ewms-pilot/commit/1c78a5c8d28baeb09a367198ec3d447b65568c07))

* [split: temp] ([`5ac2843`](https://github.com/Observation-Management-Service/ewms-pilot/commit/5ac28431efd2300a0be4d2f7e460023df2a6059a))

* [split: make `htchirp.py`] ([`9152398`](https://github.com/Observation-Management-Service/ewms-pilot/commit/91523982f913dfd7e965145a087657a509efe58b))

* Split Off `__main__.py` ([`e83771c`](https://github.com/Observation-Management-Service/ewms-pilot/commit/e83771c422e3a1a2e7eb473183567c5cf9a06f16))

* [split: restore `pilot.py`] ([`22a6094`](https://github.com/Observation-Management-Service/ewms-pilot/commit/22a6094e6043845ff47ae50535ea11db43eb4ff7))

* [split: add `__main__.py`] ([`a922844`](https://github.com/Observation-Management-Service/ewms-pilot/commit/a922844ff6b05bee6b22972f9fae03e62714a7a5))

* [split: temp] ([`9561406`](https://github.com/Observation-Management-Service/ewms-pilot/commit/9561406160a7da0f6af1f65ca95b2bda9e5920f2))

* [split: make `__main__.py`] ([`8082a41`](https://github.com/Observation-Management-Service/ewms-pilot/commit/8082a4169e97c09f7e3746ed347109d022808c81))

* Split Off `housekeeping.py` ([`1a45a3f`](https://github.com/Observation-Management-Service/ewms-pilot/commit/1a45a3f7f34148718b05bc93c50fa42e1ca83ae8))

* [split: restore `pilot.py`] ([`960904c`](https://github.com/Observation-Management-Service/ewms-pilot/commit/960904c422417209d50ddee541ce58368096a33f))

* [split: add `housekeeping.py`] ([`3d01199`](https://github.com/Observation-Management-Service/ewms-pilot/commit/3d011997ed8c76acaed0a7277b1357e72582230e))

* [split: temp] ([`7c77763`](https://github.com/Observation-Management-Service/ewms-pilot/commit/7c7776370a151c9c3ac8e17e2a6a20d23483d2cd))

* [split: make `housekeeping.py`] ([`8da00db`](https://github.com/Observation-Management-Service/ewms-pilot/commit/8da00dbec1f67cb6a715be9f4dc1d13044ef5363))

* Split Off `wait_on_tasks.py` ([`0495d31`](https://github.com/Observation-Management-Service/ewms-pilot/commit/0495d31af4f67b1b00a2be5959b53ce96dafa229))

* [split: restore `pilot.py`] ([`c7d033f`](https://github.com/Observation-Management-Service/ewms-pilot/commit/c7d033f4315090b617d005375d4182bd86aa2b10))

* [split: add `wait_on_tasks.py`] ([`1d42849`](https://github.com/Observation-Management-Service/ewms-pilot/commit/1d42849a25b8b1a551152af9779ae5e4534b9f1c))

* [split: temp] ([`52f7c7c`](https://github.com/Observation-Management-Service/ewms-pilot/commit/52f7c7cdfbe7bca0c80cbe0f68522da936c1545b))

* [split: make `wait_on_tasks.py`] ([`cc3b0ab`](https://github.com/Observation-Management-Service/ewms-pilot/commit/cc3b0ab5f62b6dd83c156898a07326871a9737cc))

* Split Off `io.py` ([`0642c1e`](https://github.com/Observation-Management-Service/ewms-pilot/commit/0642c1e87e038ca3c4c7577237f7d45b974b78c4))

* [split: restore `pilot.py`] ([`83456e6`](https://github.com/Observation-Management-Service/ewms-pilot/commit/83456e6f07f6a2c406e38dbdababc48fef7f9c5e))

* [split: add `io.py`] ([`5876b8f`](https://github.com/Observation-Management-Service/ewms-pilot/commit/5876b8ff6297fdea1f4875e113c8e81807bbe320))

* [split: temp] ([`1ec4919`](https://github.com/Observation-Management-Service/ewms-pilot/commit/1ec4919567ca8137b2e1cfd05198b5ff09c19122))

* [split: make `io.py`] ([`a2013bb`](https://github.com/Observation-Management-Service/ewms-pilot/commit/a2013bb63bae4cac6ef9a2484dcf63d3c95f90c3))

* Split Off `task.py` - 2 ([`00333a0`](https://github.com/Observation-Management-Service/ewms-pilot/commit/00333a0e7d75008bfe6e1bdd93605377fde9b08e))

* Split Off `task.py` ([`880663a`](https://github.com/Observation-Management-Service/ewms-pilot/commit/880663a51f68b6f47a58d09ade7cd4c2e00a54e6))

* [split: restore `pilot.py`] ([`28105c7`](https://github.com/Observation-Management-Service/ewms-pilot/commit/28105c72c3ae0dc1826dd25c6781eb9acec336a9))

* [split: add `task.py`] ([`4b71c5b`](https://github.com/Observation-Management-Service/ewms-pilot/commit/4b71c5bfa673d70c2daa12e4d6109b4b7135cb68))

* [split: temp] ([`107d826`](https://github.com/Observation-Management-Service/ewms-pilot/commit/107d82649e402666d0b9f1c4cb2be1d187d1587e))

* [split: make `task.py`] ([`b49b15e`](https://github.com/Observation-Management-Service/ewms-pilot/commit/b49b15e72d96edadab7b0ded1b24fe13f12f43b0))

### [minor]

* Finish Splitting Modules [minor] ([`bb68f4f`](https://github.com/Observation-Management-Service/ewms-pilot/commit/bb68f4f134d67bec7c3ed95229efc31d8fcc67ba))


## v0.12.4 (2023-09-21)

###  

* Use `Message.uuid` for Tracking (#49) ([`382754b`](https://github.com/Observation-Management-Service/ewms-pilot/commit/382754ba25389e56361b155bda35cd7b01c146bf))


## v0.12.3 (2023-09-21)

###  

* Heartbeat Fix for Long Asynchronous Tasks Followup (#48) ([`de98af9`](https://github.com/Observation-Management-Service/ewms-pilot/commit/de98af997f659b74fef5dd988a4c21c3d20db8df))

* Heartbeat Fix for Long Asynchronous Tasks (#45)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`4d95a43`](https://github.com/Observation-Management-Service/ewms-pilot/commit/4d95a435417ea644eb581499a46800c6cba4c708))


## v0.12.2 (2023-09-15)

###  

* Pin `oms-mqclient==2.4.4` (#47)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`86b9a5a`](https://github.com/Observation-Management-Service/ewms-pilot/commit/86b9a5ad54600137fd127bd0bb42d9af1c1dd1ab))


## v0.12.1 (2023-09-15)

###  

* Slow Down Heartbeat (#46)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`30b6a69`](https://github.com/Observation-Management-Service/ewms-pilot/commit/30b6a698ede14e0869efbb42b87605c0a6d0cf21))


## v0.12.0 (2023-07-31)

### [minor]

* Error Handling &amp; Rabbitmq Heartbeat Workaround [minor] (#44)

Co-authored-by: David Schultz &lt;davids24@gmail.com&gt;
Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`3a9a117`](https://github.com/Observation-Management-Service/ewms-pilot/commit/3a9a117198cf6040c5a06dceb3069bedc29be10d))


## v0.11.2 (2023-07-25)

###  

* Bump Dependencies (#43)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`b988260`](https://github.com/Observation-Management-Service/ewms-pilot/commit/b9882604985871a3c2ba0b35d52c4aa1e1b16020))


## v0.11.1 (2023-07-17)

###  

* `mqclient` Updates Follow-up (#42) ([`bb55670`](https://github.com/Observation-Management-Service/ewms-pilot/commit/bb556709170765a8e4b4ad451d287c233a863b75))


## v0.11.0 (2023-07-17)

### [minor]

* `mqclient` Updates [minor] (#41)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`b257cfa`](https://github.com/Observation-Management-Service/ewms-pilot/commit/b257cfab3efcf0e7aa6dc761ee31752f5ae239d3))


## v0.10.3 (2023-06-08)

###  

* Use `1` if `EWMS_PILOT_CONCURRENT_TASKS &lt; 1` (#40)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`c046bf2`](https://github.com/Observation-Management-Service/ewms-pilot/commit/c046bf25d0910c7c422942725bcc2655b5a0a9b7))


## v0.10.2 (2023-05-09)

###  

* Cleanup Temp Files (#35)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`57e212d`](https://github.com/Observation-Management-Service/ewms-pilot/commit/57e212d6fd25bc5723c1fc80cee503374f858374))


## v0.10.1 (2023-05-05)

###  

* Add `EWMS_PILOT_HTCHIRP` (#34)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`f748449`](https://github.com/Observation-Management-Service/ewms-pilot/commit/f748449f33607f903c5ef61ae4f30ea9b961ed3d))


## v0.10.0 (2023-05-02)

### [minor]

* HTChirp [minor] (#32)

Co-authored-by: David Schultz &lt;davids24@gmail.com&gt;
Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`6ba2138`](https://github.com/Observation-Management-Service/ewms-pilot/commit/6ba21387c8397d2226cc2d726e7988b2ad93c77f))


## v0.9.1 (2023-04-28)

###  

* Fix `EWMS_PILOT_SUBPROC_TIMEOUT` Backward Compatibility ([`28ef634`](https://github.com/Observation-Management-Service/ewms-pilot/commit/28ef63478e3aca3ac6f243fd73408bf6954e34c4))


## v0.9.0 (2023-04-28)

### [minor]

* Multitasking (Multi-Processing) [minor] (#28)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`6056971`](https://github.com/Observation-Management-Service/ewms-pilot/commit/6056971f8c32ec526478b51c53de06bbf4b304a3))


## v0.8.0 (2023-04-28)

### [minor]

* Refactor `task_timeout`/`--task-timeout`/`EWMS_PILOT_TASK_TIMEOUT` [minor] (#30)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`3ab5855`](https://github.com/Observation-Management-Service/ewms-pilot/commit/3ab585502b14a872200cd3733f2e6259de8199a6))


## v0.7.0 (2023-04-28)

### [minor]

* Remove GCP Support [minor] (#31)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`6c40e21`](https://github.com/Observation-Management-Service/ewms-pilot/commit/6c40e2154a8078099c4c45d2e993abf3d001fcdb))


## v0.6.0 (2023-04-05)

### [minor]

* Python 3.11 [minor] (#22)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`c467344`](https://github.com/Observation-Management-Service/ewms-pilot/commit/c467344eea1ea727b6ed2ad4057c2bf7e5be61de))


## v0.5.0 (2023-04-03)

### [minor]

* Auto-Set MQClient&#39;s `ack_timeout` [minor] (#21)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`161a6f4`](https://github.com/Observation-Management-Service/ewms-pilot/commit/161a6f4947569b1061177a8c3290b101af40ff80))


## v0.4.2 (2023-03-30)

###  

* An Empty Queue is Not a Failure (#20)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`3df1acb`](https://github.com/Observation-Management-Service/ewms-pilot/commit/3df1acbe6bcf8747f0f893e52c2a3397b83a77e6))


## v0.4.1 (2023-03-02)

###  

* Fix Corner Case w/ One Received Message (#18)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`eeaf824`](https://github.com/Observation-Management-Service/ewms-pilot/commit/eeaf824db52e38b662ed66315d14e676fe6be55b))


## v0.4.0 (2023-02-28)

### [minor]

* Bump MQClient + Blackhole Protection (Quarantine) [minor] (#16)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`301a249`](https://github.com/Observation-Management-Service/ewms-pilot/commit/301a2493b6f07780529fb4f1d0fb6c509261a71c))


## v0.3.1 (2023-02-17)

###  

* CI Updates (#14)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`9fd253f`](https://github.com/Observation-Management-Service/ewms-pilot/commit/9fd253f06e9e2bc8e99d88593202ddb9a731a71f))


## v0.3.0 (2023-02-14)

### [minor]

* Bump Dependencies [minor] (#13)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`8f89b7d`](https://github.com/Observation-Management-Service/ewms-pilot/commit/8f89b7d1d67afa1c3d7c6f6b16c0c250fe00f50b))


## v0.2.0 (2023-01-20)

### [minor]

* [minor] change to no-default queue installation

* change to no-default queue installation, prep for rabbitmq switch

* &lt;bot&gt; update requirements-all.txt

* &lt;bot&gt; update requirements-gcp.txt

* &lt;bot&gt; update requirements-nats.txt

* &lt;bot&gt; update requirements-rabbitmq.txt

* &lt;bot&gt; update requirements-test.txt

* &lt;bot&gt; update requirements.txt

* remove null case for broker

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`01d7a3c`](https://github.com/Observation-Management-Service/ewms-pilot/commit/01d7a3ce7520aad355ff62f4e4607ac964a18e95))


## v0.1.6 (2023-01-19)

###  

* &lt;bot&gt; update requirements-gcp.txt ([`7fc476a`](https://github.com/Observation-Management-Service/ewms-pilot/commit/7fc476adbb49aa01bb4a3cadc8168a628cd35a63))

* &lt;bot&gt; update requirements-all.txt ([`a040bea`](https://github.com/Observation-Management-Service/ewms-pilot/commit/a040bea76d2da19830a069b09607640bb9ea8604))

* Add Support for Environment Variables (#11) ([`11a04d5`](https://github.com/Observation-Management-Service/ewms-pilot/commit/11a04d533a0bc3ea7fe3acf5e905277b34cf50a8))


## v0.1.5 (2023-01-17)

###  

* Add Timeout for Waiting for First Message (#10)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`c54820e`](https://github.com/Observation-Management-Service/ewms-pilot/commit/c54820e3a02e28d9abe826dace09c09e06470eba))


## v0.1.4 (2023-01-05)

###  

* Stream Output &amp; Add Timeout (#9)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`8f5c178`](https://github.com/Observation-Management-Service/ewms-pilot/commit/8f5c178e3b664d9632973e1ff614c6645a5d74ce))


## v0.1.3 (2022-10-07)

###  

* Bump `wipac-mqclient` (#7)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`791993b`](https://github.com/Observation-Management-Service/ewms-pilot/commit/791993b4ad14d83e409bb3a4467ddd0e671efb78))


## v0.1.2 (2022-10-05)

###  

* Pathlib `rename()` Workaround (#6)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`b1cc913`](https://github.com/Observation-Management-Service/ewms-pilot/commit/b1cc91302e2381d2c5acc2f38c29f8d531ec1e65))


## v0.1.1 (2022-09-30)

###  

* &lt;bot&gt; update setup.cfg ([`606dc6e`](https://github.com/Observation-Management-Service/ewms-pilot/commit/606dc6e01307befc9163fffc98e1c5f8af2b52dc))


## v0.1.0 (2022-09-30)

### [minor]

* Add Tests [minor] (#5)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`662b68a`](https://github.com/Observation-Management-Service/ewms-pilot/commit/662b68a94101b9548837663f8db69b6d071baa55))


## v0.0.4 (2022-09-16)

###  

* Support Various File Types (#4)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`154329b`](https://github.com/Observation-Management-Service/ewms-pilot/commit/154329b93894f86803f45c808a9393ede7d98bba))


## v0.0.3 (2022-09-14)

###  

* use `relekang/python-semantic-release@master` ([`9497c60`](https://github.com/Observation-Management-Service/ewms-pilot/commit/9497c6063b1eeefabf578f38ed4d3dfc012846a4))


## v0.0.2 (2022-09-14)

###  

* &lt;bot&gt; update setup.cfg ([`b5c193e`](https://github.com/Observation-Management-Service/ewms-pilot/commit/b5c193e83afd1f9dc4fc2230589ac05534a3de1e))


## v0.0.1 (2022-09-14)

###  

* Add Python Package (#2) ([`f410436`](https://github.com/Observation-Management-Service/ewms-pilot/commit/f410436a9fd4593d21fb3e01b3dd32795ec382ca))

* Initial commit ([`4c96d0c`](https://github.com/Observation-Management-Service/ewms-pilot/commit/4c96d0cf9663f6035590b6328a23c0bc1d8289f1))
