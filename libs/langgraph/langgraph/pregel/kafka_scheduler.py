"""
Kafka-based distributed scheduler for LangGraph.

This module provides distributed execution of LangGraph workflows using Kafka
as a message bus for communication between orchestrator and executor components.
"""

import asyncio
import json
import logging
import pickle
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from langchain_core.callbacks.manager import AsyncParentRunManager, ParentRunManager
from langchain_core.runnables.config import RunnableConfig

from langgraph.channels.base import BaseChannel
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint
from langgraph.constants import (
    CONFIG_KEY_RESUMING,
    INTERRUPT,
    ERROR,
    TASKS,
)
from langgraph.errors import GraphInterrupt
from langgraph.managed.base import ManagedValueMapping
from langgraph.pregel.algo import (
    apply_writes,
    increment,
    prepare_next_tasks,
    should_interrupt,
)
from langgraph.pregel.read import PregelNode
from langgraph.pregel.retry import arun_with_retry
from langgraph.pregel.types import (
    PregelExecutableTask,
    PregelTask,
    RetryPolicy,
)

# Optional Kafka imports - will fail gracefully if not available
try:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
    from aiokafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    AIOKafkaConsumer = None
    AIOKafkaProducer = None  
    KafkaError = Exception
    KAFKA_AVAILABLE = False

logger = logging.getLogger(__name__)


# Message Schemas

@dataclass
class TaskMessage:
    """Message sent from orchestrator to executor with task to execute."""
    task_id: str
    step: int
    checkpoint_id: str
    name: str
    input_data: bytes  # Pickled task input
    node_data: bytes  # Pickled runnable node
    config_data: bytes  # Pickled config
    triggers: List[str]
    retry_policy_data: Optional[bytes] = None  # Pickled retry policy
    path: Tuple[str, ...] = ()
    timestamp: float = 0.0

    def to_json(self) -> str:
        """Serialize to JSON string."""
        data = asdict(self)
        # Convert bytes to base64 for JSON serialization
        import base64
        for key in ['input_data', 'node_data', 'config_data', 'retry_policy_data']:
            if data[key] is not None:
                data[key] = base64.b64encode(data[key]).decode('utf-8')
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str) -> 'TaskMessage':
        """Deserialize from JSON string."""
        import base64
        data = json.loads(json_str)
        # Convert base64 back to bytes
        for key in ['input_data', 'node_data', 'config_data', 'retry_policy_data']:
            if data[key] is not None:
                data[key] = base64.b64decode(data[key])
        return cls(**data)


@dataclass
class TaskResultMessage:
    """Message sent from executor to orchestrator with task results."""
    task_id: str
    step: int
    checkpoint_id: str
    success: bool
    writes_data: Optional[bytes] = None  # Pickled writes
    error_data: Optional[bytes] = None  # Pickled exception
    interrupts_data: Optional[bytes] = None  # Pickled interrupts
    timestamp: float = 0.0

    def to_json(self) -> str:
        """Serialize to JSON string."""
        data = asdict(self)
        import base64
        for key in ['writes_data', 'error_data', 'interrupts_data']:
            if data[key] is not None:
                data[key] = base64.b64encode(data[key]).decode('utf-8')
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str) -> 'TaskResultMessage':
        """Deserialize from JSON string."""
        import base64
        data = json.loads(json_str)
        for key in ['writes_data', 'error_data', 'interrupts_data']:
            if data[key] is not None:
                data[key] = base64.b64decode(data[key])
        return cls(**data)


@dataclass
class StepCompleteMessage:
    """Message sent from orchestrator when step is complete."""
    checkpoint_id: str
    step: int
    completed_task_ids: List[str]
    timestamp: float = 0.0

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str) -> 'StepCompleteMessage':
        return cls(**json.loads(json_str))


class KafkaOrchestrator:
    """
    Orchestrator component that runs the Pregel algorithm and coordinates task execution.
    
    The orchestrator:
    1. Manages the graph state and checkpoints
    2. Runs the Pregel algorithm to determine next tasks
    3. Sends tasks to executors via Kafka
    4. Collects results and updates state
    5. Handles interrupts and errors
    """

    def __init__(
        self,
        *,
        kafka_bootstrap_servers: str = "localhost:9092",
        task_topic: str = "langgraph_tasks",
        result_topic: str = "langgraph_results", 
        step_complete_topic: str = "langgraph_step_complete",
        consumer_group: str = "langgraph_orchestrator",
        processes: Dict[str, PregelNode],
        channels: Dict[str, BaseChannel],
        managed: ManagedValueMapping,
        checkpointer: Optional[BaseCheckpointSaver] = None,
        interrupt_before: Union[str, Sequence[str], None] = None,
        interrupt_after: Union[str, Sequence[str], None] = None,
        debug: bool = False,
    ):
        if not KAFKA_AVAILABLE:
            raise ImportError(
                "Kafka dependencies not available. Install with: pip install aiokafka"
            )
            
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.task_topic = task_topic
        self.result_topic = result_topic
        self.step_complete_topic = step_complete_topic
        self.consumer_group = consumer_group
        
        self.processes = processes
        self.channels = channels
        self.managed = managed
        self.checkpointer = checkpointer
        self.interrupt_before = interrupt_before
        self.interrupt_after = interrupt_after
        self.debug = debug
        
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumer: Optional[AIOKafkaConsumer] = None
        
        # Track ongoing executions
        self.active_executions: Dict[str, Dict] = {}  # checkpoint_id -> execution state
        
        # Result tracking
        self.pending_results: Dict[str, Dict[str, TaskResultMessage]] = defaultdict(dict)  # checkpoint_id -> task_id -> result

    async def start(self):
        """Start Kafka producer and consumer."""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_serializer=lambda v: v.encode('utf-8'),
        )
        await self.producer.start()
        
        self.consumer = AIOKafkaConsumer(
            self.result_topic,
            bootstrap_servers=self.kafka_bootstrap_servers,
            group_id=self.consumer_group,
            value_deserializer=lambda v: v.decode('utf-8'),
        )
        await self.consumer.start()
        
        logger.info("Kafka orchestrator started")

    async def stop(self):
        """Stop Kafka producer and consumer."""
        if self.producer:
            await self.producer.stop()
        if self.consumer:
            await self.consumer.stop()
        logger.info("Kafka orchestrator stopped")

    async def execute_step(
        self,
        checkpoint: Checkpoint,
        config: RunnableConfig,
        step: int,
        *,
        manager: Optional[Union[ParentRunManager, AsyncParentRunManager]] = None,
    ) -> Tuple[Checkpoint, List[PregelTask]]:
        """
        Execute a single step of the Pregel algorithm using distributed executors.
        
        This is the main orchestration method that:
        1. Determines tasks to execute using prepare_next_tasks
        2. Sends tasks to executors via Kafka
        3. Waits for all results
        4. Applies writes and updates checkpoint
        5. Returns updated checkpoint and task results
        """
        checkpoint_id = checkpoint["id"]
        
        # Check for interrupts before execution
        tasks = prepare_next_tasks(
            checkpoint,
            self.processes,
            self.channels,
            self.managed,
            config,
            step,
            for_execution=True,
            is_resuming=config.get("configurable", {}).get(CONFIG_KEY_RESUMING, False),
            checkpointer=self.checkpointer,
            manager=manager,
        )
        
        if not tasks:
            return checkpoint, []
        
        # Check for interrupts
        if self.interrupt_before and should_interrupt(
            checkpoint, self.interrupt_before, list(tasks.values())
        ):
            raise GraphInterrupt(
                [PregelTask(task.id, task.name) for task in tasks.values()]
            )
        
        # Track this execution
        self.active_executions[checkpoint_id] = {
            "step": step,
            "tasks": tasks,
            "pending_task_ids": set(tasks.keys()),
            "completed_task_ids": set(),
            "start_time": time.time(),
        }
        
        try:
            # Send tasks to executors
            await self._send_tasks_to_executors(list(tasks.values()), checkpoint_id, step)
            
            # Wait for all task results
            results = await self._wait_for_task_results(checkpoint_id, list(tasks.keys()))
            
            # Apply results to checkpoint
            updated_checkpoint = await self._apply_task_results(
                checkpoint, results, step
            )
            
            # Check for interrupts after execution
            task_list = [PregelTask(task.id, task.name) for task in tasks.values()]
            if self.interrupt_after and should_interrupt(
                updated_checkpoint, self.interrupt_after, task_list
            ):
                raise GraphInterrupt(task_list)
            
            # Notify step completion
            await self._notify_step_complete(checkpoint_id, step, list(tasks.keys()))
            
            return updated_checkpoint, task_list
            
        finally:
            # Clean up execution tracking
            self.active_executions.pop(checkpoint_id, None)

    async def _send_tasks_to_executors(
        self, 
        tasks: List[PregelExecutableTask],
        checkpoint_id: str, 
        step: int
    ):
        """Send tasks to executor topic."""
        for task in tasks:
            # Serialize task components
            try:
                input_data = pickle.dumps(task.input)
                node_data = pickle.dumps(task.proc)
                config_data = pickle.dumps(task.config)
                retry_policy_data = pickle.dumps(task.retry_policy) if task.retry_policy else None
                
                message = TaskMessage(
                    task_id=task.id,
                    step=step,
                    checkpoint_id=checkpoint_id,
                    name=task.name,
                    input_data=input_data,
                    node_data=node_data,
                    config_data=config_data,
                    triggers=task.triggers,
                    retry_policy_data=retry_policy_data,
                    path=task.path,
                    timestamp=time.time(),
                )
                
                await self.producer.send_and_wait(
                    self.task_topic,
                    message.to_json(),
                    key=task.id.encode('utf-8'),
                )
                
                if self.debug:
                    logger.debug(f"Sent task {task.id} ({task.name}) to executors")
                    
            except Exception as e:
                logger.error(f"Failed to send task {task.id}: {e}")
                raise

    async def _wait_for_task_results(
        self, 
        checkpoint_id: str, 
        task_ids: List[str],
        timeout: Optional[float] = 300.0  # 5 minute default timeout
    ) -> Dict[str, TaskResultMessage]:
        """Wait for results from all tasks in this step."""
        results = {}
        remaining_task_ids = set(task_ids)
        start_time = time.time()
        
        while remaining_task_ids:
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(
                    f"Timeout waiting for task results. Remaining: {remaining_task_ids}"
                )
            
            try:
                # Poll for messages with short timeout
                msg_pack = await self.consumer.getmany(timeout_ms=1000)
                
                for tp, messages in msg_pack.items():
                    for message in messages:
                        try:
                            result = TaskResultMessage.from_json(message.value)
                            
                            # Check if this result belongs to our execution
                            if (result.checkpoint_id == checkpoint_id and 
                                result.task_id in remaining_task_ids):
                                results[result.task_id] = result
                                remaining_task_ids.remove(result.task_id)
                                
                                if self.debug:
                                    logger.debug(
                                        f"Received result for task {result.task_id}: "
                                        f"{'success' if result.success else 'failed'}"
                                    )
                                    
                        except Exception as e:
                            logger.error(f"Failed to parse task result message: {e}")
            
            except Exception as e:
                if "Consumer has not subscribed to topic" not in str(e):
                    logger.error(f"Error consuming task results: {e}")
                await asyncio.sleep(0.1)
        
        return results

    async def _apply_task_results(
        self,
        checkpoint: Checkpoint,
        results: Dict[str, TaskResultMessage],
        step: int,
    ) -> Checkpoint:
        """Apply task execution results to the checkpoint."""
        # Collect all writes from successful tasks
        all_writes = []
        
        for task_id, result in results.items():
            if result.success and result.writes_data:
                try:
                    writes = pickle.loads(result.writes_data)
                    all_writes.extend(writes)
                except Exception as e:
                    logger.error(f"Failed to deserialize writes for task {task_id}: {e}")
            
            elif not result.success:
                if result.error_data:
                    try:
                        error = pickle.loads(result.error_data)
                        logger.error(f"Task {task_id} failed with error: {error}")
                        all_writes.append((ERROR, error))
                    except Exception as e:
                        logger.error(f"Failed to deserialize error for task {task_id}: {e}")
                        
                if result.interrupts_data:
                    try:
                        interrupts = pickle.loads(result.interrupts_data)
                        all_writes.extend([(INTERRUPT, interrupt) for interrupt in interrupts])
                    except Exception as e:
                        logger.error(f"Failed to deserialize interrupts for task {task_id}: {e}")

        # Apply writes using existing Pregel algorithm
        task_writes = [
            type('TaskWrites', (), {
                'name': f'task_{i}',
                'writes': [write],
                'triggers': [],
            })()
            for i, write in enumerate(all_writes)
        ]
        
        # Create a copy of checkpoint to modify
        updated_checkpoint = {
            "id": str(uuid.uuid4()),
            "channel_versions": checkpoint["channel_versions"].copy(),
            "channel_values": checkpoint["channel_values"].copy(),
            "versions_seen": checkpoint["versions_seen"].copy(),
            "pending_sends": checkpoint["pending_sends"].copy(),
        }
        
        apply_writes(
            updated_checkpoint, 
            self.channels, 
            task_writes, 
            increment
        )
        
        return updated_checkpoint

    async def _notify_step_complete(
        self, 
        checkpoint_id: str, 
        step: int, 
        task_ids: List[str]
    ):
        """Notify that step execution is complete."""
        message = StepCompleteMessage(
            checkpoint_id=checkpoint_id,
            step=step,
            completed_task_ids=task_ids,
            timestamp=time.time(),
        )
        
        await self.producer.send_and_wait(
            self.step_complete_topic,
            message.to_json(),
            key=checkpoint_id.encode('utf-8'),
        )

    async def run_consumer_loop(self):
        """Run the result consumer loop continuously."""
        logger.info("Starting orchestrator consumer loop")
        
        async for message in self.consumer:
            try:
                result = TaskResultMessage.from_json(message.value)
                checkpoint_id = result.checkpoint_id
                
                # Store result for later processing
                self.pending_results[checkpoint_id][result.task_id] = result
                
                if self.debug:
                    logger.debug(f"Queued result for task {result.task_id}")
                    
            except Exception as e:
                logger.error(f"Error processing task result: {e}")

    @asynccontextmanager
    async def lifecycle(self):
        """Async context manager for orchestrator lifecycle."""
        await self.start()
        try:
            yield self
        finally:
            await self.stop()


class KafkaExecutor:
    """
    Executor component that processes tasks sent by the orchestrator.
    
    The executor:
    1. Listens for tasks on Kafka
    2. Executes the task's runnable node
    3. Handles retries according to retry policy
    4. Sends results back to orchestrator
    """

    def __init__(
        self,
        *,
        kafka_bootstrap_servers: str = "localhost:9092",
        task_topic: str = "langgraph_tasks",
        result_topic: str = "langgraph_results",
        consumer_group: str = "langgraph_executor",
        executor_id: Optional[str] = None,
        max_concurrent_tasks: int = 10,
        debug: bool = False,
    ):
        if not KAFKA_AVAILABLE:
            raise ImportError(
                "Kafka dependencies not available. Install with: pip install aiokafka"
            )
            
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.task_topic = task_topic
        self.result_topic = result_topic
        self.consumer_group = consumer_group
        self.executor_id = executor_id or f"executor_{uuid.uuid4().hex[:8]}"
        self.max_concurrent_tasks = max_concurrent_tasks
        self.debug = debug
        
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumer: Optional[AIOKafkaConsumer] = None
        
        # Task execution tracking
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)

    async def start(self):
        """Start Kafka producer and consumer."""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_serializer=lambda v: v.encode('utf-8'),
        )
        await self.producer.start()
        
        self.consumer = AIOKafkaConsumer(
            self.task_topic,
            bootstrap_servers=self.kafka_bootstrap_servers,
            group_id=self.consumer_group,
            value_deserializer=lambda v: v.decode('utf-8'),
            enable_auto_commit=False,  # Manual commit after processing
        )
        await self.consumer.start()
        
        logger.info(f"Kafka executor {self.executor_id} started")

    async def stop(self):
        """Stop executor and wait for active tasks."""
        # Cancel all active tasks
        for task_id, task in list(self.active_tasks.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
        if self.producer:
            await self.producer.stop()
        if self.consumer:
            await self.consumer.stop()
            
        logger.info(f"Kafka executor {self.executor_id} stopped")

    async def run(self):
        """Run the executor loop, processing tasks as they arrive."""
        logger.info(f"Executor {self.executor_id} listening for tasks...")
        
        async for message in self.consumer:
            try:
                task_message = TaskMessage.from_json(message.value)
                
                # Create background task for execution
                task = asyncio.create_task(
                    self._execute_task(task_message),
                    name=f"task_{task_message.task_id}"
                )
                self.active_tasks[task_message.task_id] = task
                
                # Clean up completed tasks
                self._cleanup_completed_tasks()
                
                # Commit the message after queuing
                await self.consumer.commit()
                
            except Exception as e:
                logger.error(f"Error processing task message: {e}")

    async def _execute_task(self, task_message: TaskMessage):
        """Execute a single task and send the result."""
        async with self.semaphore:  # Limit concurrent executions
            try:
                if self.debug:
                    logger.debug(f"Starting execution of task {task_message.task_id}")
                
                # Deserialize task components
                task_input = pickle.loads(task_message.input_data)
                node = pickle.loads(task_message.node_data)
                config = pickle.loads(task_message.config_data)
                retry_policy = (
                    pickle.loads(task_message.retry_policy_data) 
                    if task_message.retry_policy_data else None
                )
                
                # Create executable task
                writes = deque()
                executable_task = PregelExecutableTask(
                    name=task_message.name,
                    input=task_input,
                    proc=node,
                    writes=writes,
                    config=config,
                    triggers=task_message.triggers,
                    retry_policy=retry_policy,
                    cache_policy=None,
                    id=task_message.task_id,
                    path=task_message.path,
                )
                
                # Execute with retry policy
                try:
                    await arun_with_retry(executable_task, retry_policy)
                    
                    # Task succeeded
                    result = TaskResultMessage(
                        task_id=task_message.task_id,
                        step=task_message.step,
                        checkpoint_id=task_message.checkpoint_id,
                        success=True,
                        writes_data=pickle.dumps(list(writes)) if writes else None,
                        timestamp=time.time(),
                    )
                    
                    if self.debug:
                        logger.debug(
                            f"Task {task_message.task_id} completed successfully "
                            f"with {len(writes)} writes"
                        )
                        
                except GraphInterrupt as e:
                    # Task was interrupted
                    result = TaskResultMessage(
                        task_id=task_message.task_id,
                        step=task_message.step,
                        checkpoint_id=task_message.checkpoint_id,
                        success=False,
                        interrupts_data=pickle.dumps(e.args[0]) if e.args else None,
                        timestamp=time.time(),
                    )
                    
                    if self.debug:
                        logger.debug(f"Task {task_message.task_id} was interrupted")
                        
                except Exception as e:
                    # Task failed
                    result = TaskResultMessage(
                        task_id=task_message.task_id,
                        step=task_message.step,
                        checkpoint_id=task_message.checkpoint_id,
                        success=False,
                        error_data=pickle.dumps(e),
                        timestamp=time.time(),
                    )
                    
                    logger.error(f"Task {task_message.task_id} failed: {e}")
                
                # Send result back to orchestrator
                await self.producer.send_and_wait(
                    self.result_topic,
                    result.to_json(),
                    key=task_message.task_id.encode('utf-8'),
                )
                
            except Exception as e:
                logger.error(f"Critical error executing task {task_message.task_id}: {e}")
                
                # Send failure result
                try:
                    result = TaskResultMessage(
                        task_id=task_message.task_id,
                        step=task_message.step,
                        checkpoint_id=task_message.checkpoint_id,
                        success=False,
                        error_data=pickle.dumps(e),
                        timestamp=time.time(),
                    )
                    
                    await self.producer.send_and_wait(
                        self.result_topic,
                        result.to_json(),
                        key=task_message.task_id.encode('utf-8'),
                    )
                except Exception as send_error:
                    logger.error(f"Failed to send error result: {send_error}")
            
            finally:
                # Remove from active tasks
                self.active_tasks.pop(task_message.task_id, None)

    def _cleanup_completed_tasks(self):
        """Remove completed tasks from tracking."""
        completed_task_ids = [
            task_id for task_id, task in self.active_tasks.items()
            if task.done()
        ]
        for task_id in completed_task_ids:
            self.active_tasks.pop(task_id)

    @asynccontextmanager
    async def lifecycle(self):
        """Async context manager for executor lifecycle."""
        await self.start()
        try:
            yield self
        finally:
            await self.stop()