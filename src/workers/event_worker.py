#!/usr/bin/env python3
"""
Event Consumer Worker

This script starts the event consumers that react to events published
by the API. Each consumer runs in its own thread and processes events
from RabbitMQ.

Usage:
    python -m workers.event_worker                  # Start all consumers
    python -m workers.event_worker virus_scanner    # Start specific consumer
    python -m workers.event_worker --list           # List available consumers
"""

import sys
import os
import logging
import signal
import threading
from typing import List

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from events.consumers import CONSUMERS, start_all_consumers
from events.event_bus import declare_event_infrastructure

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Track running threads for graceful shutdown
running_threads: List[threading.Thread] = []
shutdown_event = threading.Event()


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()


def start_consumer(name: str) -> threading.Thread:
    """Start a single consumer in a thread."""
    if name not in CONSUMERS:
        raise ValueError(f"Unknown consumer: {name}. Available: {list(CONSUMERS.keys())}")
    
    consumer_class = CONSUMERS[name]
    consumer = consumer_class()
    
    def run_consumer():
        try:
            logger.info(f"Starting consumer: {name}")
            consumer.run()
        except Exception as e:
            logger.error(f"Consumer {name} crashed: {e}")
    
    thread = threading.Thread(target=run_consumer, name=name, daemon=True)
    thread.start()
    running_threads.append(thread)
    
    return thread


def main():
    """Main entry point."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse arguments
    args = sys.argv[1:]
    
    if '--list' in args or '-l' in args:
        print("Available consumers:")
        for name, cls in CONSUMERS.items():
            print(f"  - {name}: {cls.__doc__.strip().split(chr(10))[0] if cls.__doc__ else 'No description'}")
        return
    
    if '--help' in args or '-h' in args:
        print(__doc__)
        return
    
    # Declare event infrastructure (exchanges, queues)
    logger.info("Declaring event infrastructure...")
    try:
        declare_event_infrastructure()
    except Exception as e:
        logger.error(f"Failed to declare event infrastructure: {e}")
        logger.warning("Continuing anyway - infrastructure may already exist")
    
    # Start consumers
    if args:
        # Start specific consumers
        for name in args:
            if name.startswith('-'):
                continue
            try:
                start_consumer(name)
                logger.info(f"Started consumer: {name}")
            except ValueError as e:
                logger.error(str(e))
                return 1
    else:
        # Start all consumers
        logger.info("Starting all event consumers...")
        for name in CONSUMERS.keys():
            start_consumer(name)
        logger.info(f"Started {len(CONSUMERS)} consumers")
    
    # Print status
    print("\n" + "=" * 60)
    print("EVENT-DRIVEN ARCHITECTURE - CONSUMERS RUNNING")
    print("=" * 60)
    print(f"Active consumers: {len(running_threads)}")
    for thread in running_threads:
        print(f"  ✓ {thread.name}")
    print("\nPress Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    # Wait for shutdown signal
    try:
        while not shutdown_event.is_set():
            shutdown_event.wait(timeout=1.0)
    except KeyboardInterrupt:
        pass
    
    logger.info("Shutting down consumers...")
    
    # Threads are daemon threads, so they'll be terminated when main exits
    logger.info("Event worker stopped")


if __name__ == '__main__':
    sys.exit(main() or 0)
