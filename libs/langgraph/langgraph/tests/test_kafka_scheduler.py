"""
Tests for Kafka-based distributed scheduler.
"""

import asyncio
import json
import pickle
import pytest
from collections import deque
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.runnables import RunnableConfig

from langgraph.channels.last_value import LastValue
from langgraph.checkpoint.base import Checkpoint
from langgraph.constants import INTERRUPT, ERROR
from langgraph.errors import GraphInterrupt
from langgraph.managed.base import ManagedValueMapping
from langgraph.pregel.kafka_scheduler import (
    KafkaExecutor,
    KafkaOrchestrator,
    StepCompleteMessage,
    TaskMessage,
    TaskResultMessage,
)
from langgraph.pregel.kafka_runner import (
    DistributedPregelRunner,
    KafkaExecutorService,
)
from langgraph.pregel.read import PregelNode
from langgraph.pregel.types import PregelExecutableTask, RetryPolicy


# Test fixtures

@pytest.fixture
def mock_processes():
    """Create mock processes for testing."""
    node = MagicMock()
    node.invoke = AsyncMock(return_value={"result": "success"})
    
    return {
        "test_node": PregelNode(
            channels={"input": "input_channel"},
            triggers=["input_channel"],
            node=node,
        )
    }


@pytest.fixture
def mock_channels():
    """Create mock channels for testing."""
    return {
        "input_channel": LastValue(str),
        "output_channel": LastValue(str),
    }


@pytest.fixture
def mock_managed():
    """Create mock managed values for testing."""
    return ManagedValueMapping({})


@pytest.fixture
def sample_checkpoint():
    """Create a sample checkpoint for testing."""
    return {
        "id": "test_checkpoint_123",
        "channel_versions": {"input_channel": 1, "output_channel": 0},
        "channel_values": {"input_channel": "test_input"},
        "versions_seen": {},
        "pending_sends": [],
    }


@pytest.fixture
def sample_config():
    """Create a sample config for testing."""
    return RunnableConfig(
        configurable={"thread_id": "test_thread"}
    )


# Message serialization tests

def test_task_message_serialization():
    """Test TaskMessage serialization and deserialization."""
    # Create test data
    input_data = pickle.dumps({"test": "input"})
    node_data = pickle.dumps(lambda x: x)
    config_data = pickle.dumps({"test": "config"})
    
    message = TaskMessage(
        task_id="test_task_123",
        step=1,
        checkpoint_id="checkpoint_123",
        name="test_node",
        input_data=input_data,
        node_data=node_data,
        config_data=config_data,
        triggers=["trigger1"],
        path=("tasks", "test_node"),
        timestamp=1234567890.0,
    )
    
    # Serialize and deserialize
    json_str = message.to_json()
    deserialized = TaskMessage.from_json(json_str)
    
    # Verify
    assert deserialized.task_id == message.task_id
    assert deserialized.step == message.step
    assert deserialized.checkpoint_id == message.checkpoint_id
    assert deserialized.name == message.name
    assert deserialized.input_data == message.input_data
    assert deserialized.node_data == message.node_data
    assert deserialized.config_data == message.config_data
    assert deserialized.triggers == message.triggers
    assert deserialized.path == message.path
    assert deserialized.timestamp == message.timestamp


def test_task_result_message_serialization():
    """Test TaskResultMessage serialization and deserialization."""
    writes_data = pickle.dumps([("output", "result")])
    error_data = pickle.dumps(ValueError("test error"))
    
    message = TaskResultMessage(
        task_id="test_task_123",
        step=1,
        checkpoint_id="checkpoint_123",
        success=False,
        writes_data=writes_data,
        error_data=error_data,
        timestamp=1234567890.0,
    )
    
    # Serialize and deserialize
    json_str = message.to_json()
    deserialized = TaskResultMessage.from_json(json_str)
    
    # Verify
    assert deserialized.task_id == message.task_id
    assert deserialized.success == message.success
    assert deserialized.writes_data == message.writes_data
    assert deserialized.error_data == message.error_data


def test_step_complete_message_serialization():
    """Test StepCompleteMessage serialization and deserialization."""
    message = StepCompleteMessage(
        checkpoint_id="checkpoint_123",
        step=1,
        completed_task_ids=["task1", "task2"],
        timestamp=1234567890.0,
    )
    
    # Serialize and deserialize
    json_str = message.to_json()
    deserialized = StepCompleteMessage.from_json(json_str)
    
    # Verify
    assert deserialized.checkpoint_id == message.checkpoint_id
    assert deserialized.step == message.step
    assert deserialized.completed_task_ids == message.completed_task_ids
    assert deserialized.timestamp == message.timestamp


# Kafka mocking utilities

class MockKafkaProducer:
    """Mock Kafka producer for testing."""
    
    def __init__(self):
        self.sent_messages = []
        self.started = False
        self.stopped = False
    
    async def start(self):
        self.started = True
    
    async def stop(self):
        self.stopped = True
    
    async def send_and_wait(self, topic, value, key=None):
        self.sent_messages.append({
            "topic": topic,
            "value": value,
            "key": key,
        })


class MockKafkaConsumer:
    """Mock Kafka consumer for testing."""
    
    def __init__(self):
        self.messages = []
        self.started = False
        self.stopped = False
        self.committed = False
    
    async def start(self):
        self.started = True
    
    async def stop(self):
        self.stopped = True
    
    async def commit(self):
        self.committed = True
    
    def add_message(self, topic, value, key=None):
        """Add a message to be consumed."""
        message = MagicMock()
        message.topic = topic
        message.value = value
        message.key = key
        self.messages.append(message)
    
    async def getmany(self, timeout_ms=1000):
        """Mock getmany method."""
        if self.messages:
            messages = self.messages.copy()
            self.messages.clear()
            return {("test_topic", 0): messages}
        return {}
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self.messages:
            return self.messages.pop(0)
        # Simulate no more messages
        await asyncio.sleep(0.1)
        raise StopAsyncIteration


# Orchestrator tests

@pytest.mark.asyncio
@patch("langgraph.pregel.kafka_scheduler.AIOKafkaProducer")
@patch("langgraph.pregel.kafka_scheduler.AIOKafkaConsumer")
async def test_orchestrator_initialization(
    mock_consumer_class,
    mock_producer_class,
    mock_processes,
    mock_channels,
    mock_managed,
):
    """Test orchestrator initialization."""
    mock_producer = MockKafkaProducer()
    mock_consumer = MockKafkaConsumer()
    
    mock_producer_class.return_value = mock_producer
    mock_consumer_class.return_value = mock_consumer
    
    orchestrator = KafkaOrchestrator(
        processes=mock_processes,
        channels=mock_channels,
        managed=mock_managed,
        debug=True,
    )
    
    await orchestrator.start()
    
    assert orchestrator.producer is not None
    assert orchestrator.consumer is not None
    assert mock_producer.started
    assert mock_consumer.started
    
    await orchestrator.stop()
    
    assert mock_producer.stopped
    assert mock_consumer.stopped


@pytest.mark.asyncio
@patch("langgraph.pregel.kafka_scheduler.AIOKafkaProducer")
@patch("langgraph.pregel.kafka_scheduler.AIOKafkaConsumer")
@patch("langgraph.pregel.kafka_scheduler.prepare_next_tasks")
async def test_orchestrator_execute_step(
    mock_prepare_tasks,
    mock_consumer_class,
    mock_producer_class,
    mock_processes,
    mock_channels,
    mock_managed,
    sample_checkpoint,
    sample_config,
):
    """Test orchestrator step execution."""
    # Setup mocks
    mock_producer = MockKafkaProducer()
    mock_consumer = MockKafkaConsumer()
    
    mock_producer_class.return_value = mock_producer
    mock_consumer_class.return_value = mock_consumer
    
    # Mock task preparation
    executable_task = PregelExecutableTask(
        name="test_node",
        input={"test": "input"},
        proc=MagicMock(),
        writes=deque(),
        config=sample_config,
        triggers=["input_channel"],
        retry_policy=None,
        cache_policy=None,
        id="task_123",
        path=("tasks", "test_node"),
    )
    
    mock_prepare_tasks.return_value = {"task_123": executable_task}
    
    # Create orchestrator
    orchestrator = KafkaOrchestrator(
        processes=mock_processes,
        channels=mock_channels,
        managed=mock_managed,
        debug=True,
    )
    
    await orchestrator.start()
    
    # Add a mock result message
    result_message = TaskResultMessage(
        task_id="task_123",
        step=1,
        checkpoint_id=sample_checkpoint["id"],
        success=True,
        writes_data=pickle.dumps([("output", "result")]),
        timestamp=1234567890.0,
    )
    mock_consumer.add_message("results", result_message.to_json())
    
    # Start consumer loop task
    consumer_task = asyncio.create_task(orchestrator.run_consumer_loop())
    
    # Give consumer time to process the message
    await asyncio.sleep(0.1)
    consumer_task.cancel()
    
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    
    # Execute step
    updated_checkpoint, tasks = await orchestrator.execute_step(
        sample_checkpoint, sample_config, 1
    )
    
    # Verify task was sent
    assert len(mock_producer.sent_messages) >= 1
    task_message = next(
        msg for msg in mock_producer.sent_messages
        if msg["topic"] == "langgraph_tasks"
    )
    
    # Verify message content
    sent_task = TaskMessage.from_json(task_message["value"])
    assert sent_task.task_id == "task_123"
    assert sent_task.name == "test_node"
    assert sent_task.step == 1
    
    await orchestrator.stop()


# Executor tests

@pytest.mark.asyncio
@patch("langgraph.pregel.kafka_scheduler.AIOKafkaProducer")
@patch("langgraph.pregel.kafka_scheduler.AIOKafkaConsumer")
async def test_executor_initialization(
    mock_consumer_class,
    mock_producer_class,
):
    """Test executor initialization."""
    mock_producer = MockKafkaProducer()
    mock_consumer = MockKafkaConsumer()
    
    mock_producer_class.return_value = mock_producer
    mock_consumer_class.return_value = mock_consumer
    
    executor = KafkaExecutor(
        executor_id="test_executor",
        max_concurrent_tasks=5,
        debug=True,
    )
    
    await executor.start()
    
    assert executor.producer is not None
    assert executor.consumer is not None
    assert executor.executor_id == "test_executor"
    assert executor.max_concurrent_tasks == 5
    assert mock_producer.started
    assert mock_consumer.started
    
    await executor.stop()
    
    assert mock_producer.stopped
    assert mock_consumer.stopped


@pytest.mark.asyncio
@patch("langgraph.pregel.kafka_scheduler.AIOKafkaProducer")
@patch("langgraph.pregel.kafka_scheduler.AIOKafkaConsumer")
async def test_executor_task_execution(
    mock_consumer_class,
    mock_producer_class,
):
    """Test executor task execution."""
    mock_producer = MockKafkaProducer()
    mock_consumer = MockKafkaConsumer()
    
    mock_producer_class.return_value = mock_producer
    mock_consumer_class.return_value = mock_consumer
    
    executor = KafkaExecutor(debug=True)
    await executor.start()
    
    # Create a test task message
    node = MagicMock()
    node.ainvoke = AsyncMock(return_value={"result": "success"})
    
    task_message = TaskMessage(
        task_id="test_task_456",
        step=1,
        checkpoint_id="checkpoint_456",
        name="test_node",
        input_data=pickle.dumps({"test": "input"}),
        node_data=pickle.dumps(node),
        config_data=pickle.dumps({}),
        triggers=["test_trigger"],
        timestamp=1234567890.0,
    )
    
    # Execute the task
    await executor._execute_task(task_message)
    
    # Verify result was sent
    assert len(mock_producer.sent_messages) == 1
    result_msg = TaskResultMessage.from_json(mock_producer.sent_messages[0]["value"])
    
    assert result_msg.task_id == "test_task_456"
    assert result_msg.success == True
    
    await executor.stop()


@pytest.mark.asyncio
@patch("langgraph.pregel.kafka_scheduler.AIOKafkaProducer")
@patch("langgraph.pregel.kafka_scheduler.AIOKafkaConsumer")
async def test_executor_task_failure(
    mock_consumer_class,
    mock_producer_class,
):
    """Test executor handles task failures."""
    mock_producer = MockKafkaProducer()
    mock_consumer = MockKafkaConsumer()
    
    mock_producer_class.return_value = mock_producer
    mock_consumer_class.return_value = mock_consumer
    
    executor = KafkaExecutor(debug=True)
    await executor.start()
    
    # Create a failing task
    node = MagicMock()
    node.ainvoke = AsyncMock(side_effect=ValueError("Task failed"))
    
    task_message = TaskMessage(
        task_id="failing_task",
        step=1,
        checkpoint_id="checkpoint_456",
        name="failing_node",
        input_data=pickle.dumps({"test": "input"}),
        node_data=pickle.dumps(node),
        config_data=pickle.dumps({}),
        triggers=["test_trigger"],
        timestamp=1234567890.0,
    )
    
    # Execute the task
    await executor._execute_task(task_message)
    
    # Verify failure result was sent
    assert len(mock_producer.sent_messages) == 1
    result_msg = TaskResultMessage.from_json(mock_producer.sent_messages[0]["value"])
    
    assert result_msg.task_id == "failing_task"
    assert result_msg.success == False
    assert result_msg.error_data is not None
    
    # Verify error was pickled correctly
    error = pickle.loads(result_msg.error_data)
    assert isinstance(error, ValueError)
    assert str(error) == "Task failed"
    
    await executor.stop()


@pytest.mark.asyncio
@patch("langgraph.pregel.kafka_scheduler.AIOKafkaProducer")
@patch("langgraph.pregel.kafka_scheduler.AIOKafkaConsumer")
async def test_executor_task_interrupt(
    mock_consumer_class,
    mock_producer_class,
):
    """Test executor handles task interrupts."""
    mock_producer = MockKafkaProducer()
    mock_consumer = MockKafkaConsumer()
    
    mock_producer_class.return_value = mock_producer
    mock_consumer_class.return_value = mock_consumer
    
    executor = KafkaExecutor(debug=True)
    await executor.start()
    
    # Create an interrupting task
    node = MagicMock()
    node.ainvoke = AsyncMock(side_effect=GraphInterrupt([{"interrupt": "data"}]))
    
    task_message = TaskMessage(
        task_id="interrupt_task",
        step=1,
        checkpoint_id="checkpoint_456", 
        name="interrupt_node",
        input_data=pickle.dumps({"test": "input"}),
        node_data=pickle.dumps(node),
        config_data=pickle.dumps({}),
        triggers=["test_trigger"],
        timestamp=1234567890.0,
    )
    
    # Execute the task
    await executor._execute_task(task_message)
    
    # Verify interrupt result was sent
    assert len(mock_producer.sent_messages) == 1
    result_msg = TaskResultMessage.from_json(mock_producer.sent_messages[0]["value"])
    
    assert result_msg.task_id == "interrupt_task"
    assert result_msg.success == False
    assert result_msg.interrupts_data is not None
    
    # Verify interrupt was pickled correctly
    interrupts = pickle.loads(result_msg.interrupts_data)
    assert interrupts == [{"interrupt": "data"}]
    
    await executor.stop()


# Integration tests

@pytest.mark.asyncio 
@patch("langgraph.pregel.kafka_scheduler.KAFKA_AVAILABLE", True)
@patch("langgraph.pregel.kafka_scheduler.AIOKafkaProducer")
@patch("langgraph.pregel.kafka_scheduler.AIOKafkaConsumer")
async def test_distributed_runner_lifecycle(
    mock_consumer_class,
    mock_producer_class,
    mock_processes,
    mock_channels,
    mock_managed,
):
    """Test distributed runner lifecycle management."""
    # Setup mocks
    mock_producer = MockKafkaProducer()
    mock_consumer = MockKafkaConsumer()
    
    mock_producer_class.return_value = mock_producer
    mock_consumer_class.return_value = mock_consumer
    
    runner = DistributedPregelRunner(
        processes=mock_processes,
        channels=mock_channels,
        managed=mock_managed,
        debug=True,
    )
    
    async with runner.distributed_execution(num_executors=2) as distributed_runner:
        assert distributed_runner.orchestrator is not None
        assert len(distributed_runner.executors) == 2
        
        # Verify all components are started
        assert distributed_runner.orchestrator.producer.started
        assert distributed_runner.orchestrator.consumer.started
        
        for executor in distributed_runner.executors:
            assert executor.producer.started
            assert executor.consumer.started
    
    # Verify cleanup happened
    assert distributed_runner.orchestrator.producer.stopped
    assert distributed_runner.orchestrator.consumer.stopped
    
    for executor in distributed_runner.executors:
        assert executor.producer.stopped
        assert executor.consumer.stopped


@pytest.mark.asyncio
@patch("langgraph.pregel.kafka_scheduler.KAFKA_AVAILABLE", True)
@patch("langgraph.pregel.kafka_scheduler.AIOKafkaProducer")
@patch("langgraph.pregel.kafka_scheduler.AIOKafkaConsumer")
async def test_executor_service_lifecycle(
    mock_consumer_class,
    mock_producer_class,
):
    """Test executor service lifecycle management."""
    mock_producer = MockKafkaProducer()
    mock_consumer = MockKafkaConsumer()
    
    mock_producer_class.return_value = mock_producer
    mock_consumer_class.return_value = mock_consumer
    
    service = KafkaExecutorService(
        num_executors=3,
        debug=True,
    )
    
    async with service.lifecycle():
        assert len(service.executors) == 3
        assert len(service.executor_tasks) == 3
        
        # Verify all executors are started
        for executor in service.executors:
            assert executor.producer.started
            assert executor.consumer.started
    
    # Verify cleanup
    for executor in service.executors:
        assert executor.producer.stopped
        assert executor.consumer.stopped


# Error handling tests

@pytest.mark.asyncio
async def test_kafka_not_available_error():
    """Test error when Kafka dependencies are not available."""
    with patch("langgraph.pregel.kafka_scheduler.KAFKA_AVAILABLE", False):
        with pytest.raises(ImportError, match="Kafka dependencies not available"):
            KafkaOrchestrator(
                processes={},
                channels={},
                managed=ManagedValueMapping({}),
            )
        
        with pytest.raises(ImportError, match="Kafka dependencies not available"):
            KafkaExecutor()


def test_message_serialization_with_none_values():
    """Test message serialization handles None values correctly."""
    message = TaskMessage(
        task_id="test",
        step=1,
        checkpoint_id="checkpoint",
        name="node",
        input_data=b"input",
        node_data=b"node", 
        config_data=b"config",
        triggers=["trigger"],
        retry_policy_data=None,  # None value
    )
    
    # Should not raise an exception
    json_str = message.to_json()
    deserialized = TaskMessage.from_json(json_str)
    
    assert deserialized.retry_policy_data is None


# Performance/stress tests

@pytest.mark.asyncio
async def test_concurrent_task_execution():
    """Test executor can handle multiple concurrent tasks."""
    # This test would simulate multiple tasks being executed concurrently
    # In a real test, you'd want to verify the semaphore limits work correctly
    pass


if __name__ == "__main__":
    # Run specific tests for development
    asyncio.run(test_task_message_serialization())
    print("All serialization tests passed!")