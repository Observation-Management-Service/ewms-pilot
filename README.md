<!--- Top of README Badges (automated) --->
[![PyPI](https://img.shields.io/pypi/v/ewms-pilot)](https://pypi.org/project/ewms-pilot/) [![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/Observation-Management-Service/ewms-pilot?include_prereleases)](https://github.com/Observation-Management-Service/ewms-pilot/) [![Versions](https://img.shields.io/pypi/pyversions/ewms-pilot.svg)](https://pypi.org/project/ewms-pilot) [![PyPI - License](https://img.shields.io/pypi/l/ewms-pilot)](https://github.com/Observation-Management-Service/ewms-pilot/blob/main/LICENSE) [![GitHub issues](https://img.shields.io/github/issues/Observation-Management-Service/ewms-pilot)](https://github.com/Observation-Management-Service/ewms-pilot/issues?q=is%3Aissue+sort%3Aupdated-desc+is%3Aopen) [![GitHub pull requests](https://img.shields.io/github/issues-pr/Observation-Management-Service/ewms-pilot)](https://github.com/Observation-Management-Service/ewms-pilot/pulls?q=is%3Apr+sort%3Aupdated-desc+is%3Aopen)
<!--- End of README Badges (automated) --->

# ewms-pilot

An Event-Task Pilot for EWMS

The EWMS Pilot is a non-user-facing wrapper for task container instances in the Event Workflow Management System (EWMS), running on an HTCondor Execution Point (EP). The pilot:

- **Triggers task instances** for each inbound event.
- **Interfaces with EWMS events** as input/output files.
- **Isolates [task containers](#task-container)** from one another.
- **Provides fault tolerance** for failed tasks, CPUs, etc.

The following outlines what users need to know to operate within EWMS.

## Overview

The Pilot is designed to be invisible to users. However, some key details are necessary for running a [task container](#task-container):

### Task Container Overview

A **[task container](#task-container)** is created for each inbound event, it is defined by its image, arguments, and environment variables. See the [WMS docs](https://github.com/Observation-Management-Service/ewms-workflow-management-service#the-task-container) for information on setting these within EWMS.

#### Event I/O

An **input event** is provided to the task container as a file. The task container creates an **output event** by writing to a predetermined location.

The pilot provides the filepaths to the input and output files in two ways:

1. By replacing the placeholder strings, `{{INFILE}}` and `{{OUTFILE}}`, in the container's arguments at runtime.
2. By setting the task container's environment variables `EWMS_TASK_INFILE` and `EWMS_TASK_OUTFILE`.

The files' extensions are configured by the pilot's environment variables, `EWMS_PILOT_INFILE_EXT` and `EWMS_PILOT_OUTFILE_EXT`: by default, these are `.in` and `.out`, respectively.

No other event or [message](#message-queue) handling is required by the task container.

### The Init Container

An **init container** is an optional, user-supplied image used to set up the environment, wait for conditions, or perform other preparatory actions before running task containers. It is configured using the `EWMS_PILOT_INIT_IMAGE`, `EWMS_PILOT_INIT_ARGS`, and `EWMS_PILOT_INIT_ENV_JSON` environment variables.

### File I/O

Task containers (and [init containers](#the-init-container)) can interact with external files in two ways:

#### Inter-Task Files

To transfer files between task containers, a shared directory is available to all task containers. This is provided by the environment variable `EWMS_TASK_DATA_HUB_DIR`, referred to as the "data hub".

**Note**:

- The data hub directory is writable, but there is no protection against race conditions for parallelized tasks.

#### External Files

Externally-mounted directories are supported in EWMS. See the [WMS documentation](https://github.com/Observation-Management-Service/ewms-workflow-management-service#task-file-io) for more details.

## EWMS Glossary Applied to the Pilot

### Workflow

_Does not exist within the Pilot._ _[Compare to WMS.](https://github.com/Observation-Management-Service/ewms-workflow-management-service#workflow)_

### Message Queue

The **message queue** is abstracted from the task container and can be ignored. _[Compare to WMS.](https://github.com/Observation-Management-Service/ewms-workflow-management-service#message-queue)_

#### Event

An **event** is an object transferred via [event I/O](#event-io). _[Compare to WMS.](https://github.com/Observation-Management-Service/ewms-workflow-management-service#event)_

### Task

In the context of the Pilot, the **task** is the runtime instance of the task image (a [task container](#task-container)) applied to an inbound event, possibly producing outbound events. _[Compare to WMS.](https://github.com/Observation-Management-Service/ewms-workflow-management-service#task)_

#### Task Container

The **task container** is an instance of a task image and is nearly synonymous with [task](#task).

### Task Directive

_Does not exist within the Pilot._ _[Compare to WMS.](https://github.com/Observation-Management-Service/ewms-workflow-management-service#task-directive)_

### Taskforce

_Does not exist within the Pilot._ _[Compare to WMS.](https://github.com/Observation-Management-Service/ewms-workflow-management-service#taskforce)_
