"""
Kafka-based distributed execution runner for LangGraph.

This module provides high-level interfaces for running distributed LangGraph
workflows using the Kafka scheduler components.
"""

import asyncio
import logging
import signal
from contextlib import asynccontextmanager
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Optional,
    Sequence,
    Union,
)

from langchain_core.callbacks.manager import AsyncParentRunManager
from langchain_core.runnables.config import RunnableConfig

from langgraph.channels.base import BaseChannel
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint
from langgraph.errors import GraphInterrupt
from langgraph.managed.base import ManagedValueMapping
from langgraph.pregel.kafka_scheduler import KafkaExecutor, KafkaOrchestrator
from langgraph.pregel.read import PregelNode
from langgraph.pregel.types import PregelTask, StreamMode

logger = logging.getLogger(__name__)


class DistributedPregelRunner:
    """
    High-level runner for distributed LangGraph execution using Kafka.
    
    This class orchestrates the distributed execution of LangGraph workflows
    by managing both the orchestrator and executor lifecycle.
    """

    def __init__(
        self,
        *,
        processes: Dict[str, PregelNode],
        channels: Dict[str, BaseChannel], 
        managed: ManagedValueMapping,
        checkpointer: Optional[BaseCheckpointSaver] = None,
        kafka_bootstrap_servers: str = "localhost:9092",
        task_topic: str = "langgraph_tasks",
        result_topic: str = "langgraph_results",
        step_complete_topic: str = "langgraph_step_complete",
        orchestrator_consumer_group: str = "langgraph_orchestrator",
        executor_consumer_group: str = "langgraph_executor",
        max_concurrent_tasks: int = 10,
        interrupt_before: Union[str, Sequence[str], None] = None,
        interrupt_after: Union[str, Sequence[str], None] = None,
        debug: bool = False,
    ):
        self.processes = processes
        self.channels = channels
        self.managed = managed
        self.checkpointer = checkpointer
        
        self.kafka_config = {
            "kafka_bootstrap_servers": kafka_bootstrap_servers,
            "task_topic": task_topic,
            "result_topic": result_topic,
            "step_complete_topic": step_complete_topic,
        }
        
        self.orchestrator_config = {
            **self.kafka_config,
            "consumer_group": orchestrator_consumer_group,
            "processes": processes,
            "channels": channels,
            "managed": managed,
            "checkpointer": checkpointer,
            "interrupt_before": interrupt_before,
            "interrupt_after": interrupt_after,
            "debug": debug,
        }
        
        self.executor_config = {
            **self.kafka_config,
            "consumer_group": executor_consumer_group,
            "max_concurrent_tasks": max_concurrent_tasks,
            "debug": debug,
        }
        
        self.orchestrator: Optional[KafkaOrchestrator] = None
        self.executors: List[KafkaExecutor] = []

    @asynccontextmanager
    async def distributed_execution(
        self, 
        num_executors: int = 1
    ) -> AsyncGenerator['DistributedPregelRunner', None]:
        """
        Context manager for distributed execution with automatic cleanup.
        
        Args:
            num_executors: Number of executor instances to run
        """
        # Create orchestrator
        self.orchestrator = KafkaOrchestrator(**self.orchestrator_config)
        
        # Create executors  
        self.executors = [
            KafkaExecutor(**{**self.executor_config, "executor_id": f"executor_{i}"})
            for i in range(num_executors)
        ]
        
        # Start all components
        await self.orchestrator.start()
        
        executor_tasks = []
        for executor in self.executors:
            await executor.start()
            # Start executor in background
            task = asyncio.create_task(
                executor.run(), 
                name=f"executor_{executor.executor_id}"
            )
            executor_tasks.append(task)
        
        # Start orchestrator consumer loop in background
        orchestrator_task = asyncio.create_task(
            self.orchestrator.run_consumer_loop(),
            name="orchestrator_consumer"
        )
        
        try:
            yield self
        finally:
            # Cleanup
            orchestrator_task.cancel()
            for task in executor_tasks:
                task.cancel()
                
            # Wait for tasks to finish
            await asyncio.gather(
                orchestrator_task, 
                *executor_tasks, 
                return_exceptions=True
            )
            
            # Stop components
            for executor in self.executors:
                await executor.stop()
            await self.orchestrator.stop()

    async def execute_step(
        self,
        checkpoint: Checkpoint,
        config: RunnableConfig,
        step: int,
        *,
        manager: Optional[AsyncParentRunManager] = None,
    ) -> tuple[Checkpoint, List[PregelTask]]:
        """Execute a single step using distributed orchestrator."""
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized. Use distributed_execution context manager.")
            
        return await self.orchestrator.execute_step(
            checkpoint, config, step, manager=manager
        )

    async def astream(
        self,
        input: Union[dict[str, Any], Any],
        config: Optional[RunnableConfig] = None,
        *,
        stream_mode: StreamMode = "values",
        interrupt_before: Optional[Union[str, Sequence[str]]] = None,
        interrupt_after: Optional[Union[str, Sequence[str]]] = None,
        debug: Optional[bool] = None,
    ) -> AsyncGenerator[Union[dict[str, Any], Any], None]:
        """
        Run the graph asynchronously with distributed execution.
        
        This is a simplified interface that handles checkpoint management
        and streaming of results.
        """
        # TODO: Implement full streaming interface
        # This would require more complex checkpoint and state management
        # For now, this is a placeholder for the full implementation
        raise NotImplementedError(
            "Full streaming interface not yet implemented. "
            "Use execute_step directly for now."
        )


class KafkaExecutorService:
    """
    Standalone service for running Kafka executors.
    
    This can be used to run executors as separate processes or services,
    independent of the orchestrator.
    """

    def __init__(
        self,
        *,
        kafka_bootstrap_servers: str = "localhost:9092",
        task_topic: str = "langgraph_tasks",
        result_topic: str = "langgraph_results",
        consumer_group: str = "langgraph_executor",
        num_executors: int = 1,
        max_concurrent_tasks: int = 10,
        debug: bool = False,
    ):
        self.kafka_config = {
            "kafka_bootstrap_servers": kafka_bootstrap_servers,
            "task_topic": task_topic,
            "result_topic": result_topic,
            "consumer_group": consumer_group,
            "max_concurrent_tasks": max_concurrent_tasks,
            "debug": debug,
        }
        self.num_executors = num_executors
        self.executors: List[KafkaExecutor] = []
        self.executor_tasks: List[asyncio.Task] = []
        self.shutdown_event = asyncio.Event()

    async def start(self):
        """Start all executor instances."""
        logger.info(f"Starting {self.num_executors} Kafka executors")
        
        # Create executors
        for i in range(self.num_executors):
            executor = KafkaExecutor(
                **{**self.kafka_config, "executor_id": f"service_executor_{i}"}
            )
            await executor.start()
            self.executors.append(executor)
            
            # Start executor task
            task = asyncio.create_task(
                executor.run(),
                name=f"executor_service_{i}"
            )
            self.executor_tasks.append(task)
        
        logger.info("All executors started successfully")

    async def stop(self):
        """Stop all executor instances."""
        logger.info("Stopping executor service")
        
        # Signal shutdown
        self.shutdown_event.set()
        
        # Cancel all tasks
        for task in self.executor_tasks:
            task.cancel()
        
        # Wait for tasks to finish
        if self.executor_tasks:
            await asyncio.gather(*self.executor_tasks, return_exceptions=True)
        
        # Stop executors
        for executor in self.executors:
            await executor.stop()
        
        logger.info("Executor service stopped")

    async def run_until_stopped(self):
        """Run executors until manually stopped."""
        await self.start()
        
        try:
            # Setup signal handlers for graceful shutdown
            def signal_handler():
                logger.info("Received shutdown signal")
                self.shutdown_event.set()
            
            # Register signal handlers
            if hasattr(signal, 'SIGTERM'):
                loop = asyncio.get_event_loop()
                loop.add_signal_handler(signal.SIGTERM, signal_handler)
                loop.add_signal_handler(signal.SIGINT, signal_handler)
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        finally:
            await self.stop()

    @asynccontextmanager
    async def lifecycle(self):
        """Context manager for service lifecycle."""
        await self.start()
        try:
            yield self
        finally:
            await self.stop()


# Utility functions

async def run_kafka_executors(
    *,
    num_executors: int = 1,
    kafka_bootstrap_servers: str = "localhost:9092",
    task_topic: str = "langgraph_tasks", 
    result_topic: str = "langgraph_results",
    consumer_group: str = "langgraph_executor",
    max_concurrent_tasks: int = 10,
    debug: bool = False,
):
    """
    Convenience function to run Kafka executors as a service.
    
    Example:
        asyncio.run(run_kafka_executors(num_executors=5, debug=True))
    """
    service = KafkaExecutorService(
        kafka_bootstrap_servers=kafka_bootstrap_servers,
        task_topic=task_topic,
        result_topic=result_topic,
        consumer_group=consumer_group,
        num_executors=num_executors,
        max_concurrent_tasks=max_concurrent_tasks,
        debug=debug,
    )
    
    await service.run_until_stopped()


def create_distributed_runner(
    graph: Any,  # LangGraph graph instance
    *,
    kafka_bootstrap_servers: str = "localhost:9092",
    num_executors: int = 1,
    max_concurrent_tasks: int = 10,
    debug: bool = False,
) -> DistributedPregelRunner:
    """
    Create a distributed runner from a LangGraph graph.
    
    Args:
        graph: LangGraph graph instance
        kafka_bootstrap_servers: Kafka bootstrap servers
        num_executors: Number of executor instances
        max_concurrent_tasks: Max concurrent tasks per executor
        debug: Enable debug logging
        
    Returns:
        Configured DistributedPregelRunner
    """
    # Extract graph components
    # This assumes the graph has the necessary attributes
    # In a real implementation, this would need to be adapted
    # based on the actual LangGraph API
    
    if not hasattr(graph, 'nodes') or not hasattr(graph, 'channels'):
        raise ValueError(
            "Graph must have 'nodes' and 'channels' attributes. "
            "Make sure you're passing a properly constructed LangGraph graph."
        )
    
    return DistributedPregelRunner(
        processes=graph.nodes,
        channels=graph.channels,
        managed=getattr(graph, 'managed', {}),
        checkpointer=getattr(graph, 'checkpointer', None),
        kafka_bootstrap_servers=kafka_bootstrap_servers,
        max_concurrent_tasks=max_concurrent_tasks,
        debug=debug,
    )