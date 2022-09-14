"""Init."""

import logging

from .pilot import consume_and_reply, main

__all__ = ["consume_and_reply", "mq"]

LOGGER = logging.getLogger("ewms-pilot")

# find the installed MQClient package
try:
    import mqclient_nats  # type: ignore[import]

    mq = mqclient_nats
except ImportError:
    try:
        import mqclient_rabbitmq  # type: ignore[import]

        mq = mqclient_rabbitmq
    except ImportError:
        try:
            import mqclient_gcp  # type: ignore[import]

            mq = mqclient_gcp
        except ImportError:
            try:
                # Pulsar is the default, so try it last
                import mqclient_pulsar  # type: ignore[import]

                mq = mqclient_pulsar
            except ImportError:
                raise ImportError("No MQClient package installed.")

# version is a human-readable version number.
__version__ = "0.0.3"

# version_info is a four-tuple for programmatic comparison. The first
# three numbers are the components of the version number. The fourth
# is zero for an official release, positive for a development branch,
# or negative for a release candidate or beta (after the base version
# number has been incremented)
version_info = (
    int(__version__.split(".")[0]),
    int(__version__.split(".")[1]),
    int(__version__.split(".")[2]),
    0,
)

# main
if __name__ == "__main__":
    main()
