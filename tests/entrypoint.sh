#!/bin/bash

case "$1" in
    "ntrip-mock")
        exec python /app/tests/docker/ntrip_mock.py
        ;;
    "serial-mock")
        exec python /app/tests/docker/serial_mock.py
        ;;
    "gnss-worker")
        exec python /app/main.py
        ;;
    "test-unit")
        exec python /app/tests/run_tests.py --type unit
        ;;
    "test-integration")
        exec python /app/tests/run_tests.py --type integration
        ;;
    "test-real-integration")
        exec python /app/tests/run_tests.py --type real-integration
        ;;
    "test-system")
        exec python /app/tests/run_tests.py --type system
        ;;
    "test-architecture")
        exec python /app/tests/run_tests.py --type architecture
        ;;
    *)
        echo "Usage: $0 {ntrip-mock|serial-mock|gnss-worker|test-unit|test-integration|test-real-integration|test-system|test-architecture}"
        exit 1
        ;;
esac
