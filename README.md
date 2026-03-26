<!--- Top of README Badges (automated) --->
[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/Observation-Management-Service/ewms-pilot?include_prereleases)](https://github.com/Observation-Management-Service/ewms-pilot) [![GitHub issues](https://img.shields.io/github/issues/Observation-Management-Service/ewms-pilot)](https://github.com/Observation-Management-Service/ewms-pilot/issues?q=is%3Aissue+sort%3Aupdated-desc+is%3Aopen) [![GitHub pull requests](https://img.shields.io/github/issues-pr/Observation-Management-Service/ewms-pilot)](https://github.com/Observation-Management-Service/ewms-pilot/pulls?q=is%3Apr+sort%3Aupdated-desc+is%3Aopen)
<!--- End of README Badges (automated) --->

# Task Pilot

EWMS's Pilot: A Job Pilot for Processing EWMS Events/Tasks
<!--- Top of README Metadata Section (automated) --->

<!--- note: this information is pulled from the pyproject.toml --->

<dl>
    <dt><sub>Authors</sub></dt>
    <dd><sub>WIPAC Developers / <a href='mailto:developers@icecube.wisc.edu'>developers@icecube.wisc.edu</a></sub></dd>
    <dt><sub>Keywords</sub></dt>
    <dd><sub>pilot&nbsp;&nbsp;·&nbsp;&nbsp;task pilot&nbsp;&nbsp;·&nbsp;&nbsp;Observation Management Service&nbsp;&nbsp;·&nbsp;&nbsp;Event Workflow Management System&nbsp;&nbsp;·&nbsp;&nbsp;EWMS&nbsp;&nbsp;·&nbsp;&nbsp;message passing&nbsp;&nbsp;·&nbsp;&nbsp;MQ</sub></dd>
    <dt><sub>URLs</sub></dt>
    <dd><sub><a href='https://github.com/Observation-Management-Service/ewms-pilot'>Homepage</a>&nbsp;&nbsp;·&nbsp;&nbsp;<a href='https://github.com/Observation-Management-Service/ewms-pilot/issues'>Tracker</a>&nbsp;&nbsp;·&nbsp;&nbsp;<a href='https://github.com/Observation-Management-Service/ewms-pilot'>Source</a>&nbsp;&nbsp;·&nbsp;&nbsp;<a href='https://observation-management-service.github.io/ewms-docs/internal/pilot.html'>Documentation</a></sub></dd>
</dl>

<br>
<!--- End of README Metadata Section (automated) --->

The EWMS Pilot is a non-user-facing wrapper for task container instances in the Event Workflow Management System (EWMS), running on an HTCondor Execution Point (EP). The pilot:

- **Triggers task instances** for each inbound event.
- **Interfaces with EWMS events** as input/output files.
- **Isolates [task containers](#task-container)** from one another.
- **Provides fault tolerance** for failed tasks, CPUs, etc.

The following outlines what users need to know to operate within EWMS.

## Overview

The Pilot is designed to be invisible to users. However, some key details are necessary for running a [task container](#task-container):

### Task Container Overview

A **[task container](#task-container)** is created for each inbound event, it is defined by its image, arguments, and environment variables. Also, see the [WMS docs](https://observation-management-service.github.io/ewms-docs/services/wms.html#the-task-container) for information on setting these within EWMS.

#### Event I/O

An **input event** is provided to the task container as a file. The task container creates an **output event** by writing to a predetermined location.

The pilot provides the filepaths to the input and output files in two ways:

1. By replacing the placeholder strings, `{{INFILE}}` and `{{OUTFILE}}`, in the container's arguments at runtime.
2. By setting the task container's environment variables: `EWMS_TASK_INFILE` and `EWMS_TASK_OUTFILE`.

The files' extensions are configured by the pilot's environment variables, `EWMS_PILOT_INFILE_EXT` and `EWMS_PILOT_OUTFILE_EXT`: by default, these are `.in` and `.out`, respectively.

No other event or [message](#message-queue) handling is required by the task container.

### The Init Container

An **init container** is an optional, user-supplied image used to set up the environment, wait for conditions, or perform other preparatory actions before running task containers. It is configured using the `EWMS_PILOT_INIT_IMAGE`, `EWMS_PILOT_INIT_ARGS`, and `EWMS_PILOT_INIT_ENV_JSON` environment variables.

### File I/O

Task containers (and [init containers](#the-init-container)) can interact with external files in two ways:

#### Inter-Task Files

To transfer files between task containers, a shared directory is available to all task containers and the init container.

The pilot provides the filepath to the "data hub" in two ways:

1. By replacing the placeholder string, `{{DATA_HUB}}`, in the container's arguments at runtime.
2. By setting the task container's environment variable: `EWMS_TASK_DATA_HUB_DIR`.

**Note**:

- The data hub directory is writable, but there is no protection against race conditions for parallelized tasks.

#### External Files

Externally-mounted directories are supported in EWMS. See the `pilot_config.input_files` in [WMS documentation](https://observation-management-service.github.io/ewms-docs/apis/wms.html#post--v1-workflows) for more details.

## EWMS Glossary Applied to the Pilot

### Workflow

_Is not relevant to the Pilot._ _[Compare to WMS.](https://observation-management-service.github.io/ewms-docs/services/wms.html#workflow)_

### Message Queue

The **message queue** is abstracted from the task container and can be ignored. _[Compare to WMS.](https://observation-management-service.github.io/ewms-docs/services/wms.html#message-queue)_

#### Event

An **event** is an object transferred via [event I/O](#event-io). _[Compare to WMS.](https://observation-management-service.github.io/ewms-docs/services/wms.html#event)_

### Task

In the context of the Pilot, the **task** is the runtime instance of the task image (a [task container](#task-container)) applied to an inbound event, possibly producing outbound events. _[Compare to WMS.](https://observation-management-service.github.io/ewms-docs/services/wms.html#task)_

#### Task Container

The **task container** is an instance of a task image and so, is nearly synonymous with [task](#task).

### Task Directive

_Is not relevant to the Pilot._ _[Compare to WMS.](https://observation-management-service.github.io/ewms-docs/services/wms.html#task-directive)_

### Taskforce

_Is not relevant to the Pilot._ _[Compare to WMS.](https://observation-management-service.github.io/ewms-docs/services/wms.html#taskforce)_
