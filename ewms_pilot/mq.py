"""Logic for getting the installed MWClient broker/backend API."""

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
