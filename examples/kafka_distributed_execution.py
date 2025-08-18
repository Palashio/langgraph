"""
Example: Distributed LangGraph Execution with Kafka

This example demonstrates how to use the Kafka-based distributed scheduler
to run LangGraph workflows across multiple executor processes.

Prerequisites:
- Apache Kafka running on localhost:9092
- Install dependencies: pip install aiokafka

Usage:
1. Start Kafka (e.g., using Docker):
   docker run -p 9092:9092 -e KAFKA_ZOOKEEPER_CONNECT=localhost:2181 confluentinc/cp-kafka

2. Run the orchestrator:
   python kafka_distributed_execution.py orchestrator

3. Run executors (in separate terminals):
   python kafka_distributed_execution.py executor
   python kafka_distributed_execution.py executor

4. Run the workflow:
   python kafka_distributed_execution.py workflow
"""

import asyncio
import sys
from typing import Any, Dict

from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.config import RunnableConfig

from langgraph.channels.last_value import LastValue
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.managed.base import ManagedValueMapping
from langgraph.pregel.kafka_runner import (
    DistributedPregelRunner,
    KafkaExecutorService,
    run_kafka_executors,
)
from langgraph.pregel.read import PregelNode


# Define a simple workflow state
class WorkflowState(Dict[str, Any]):
    pass


# Define workflow nodes
def data_processing_node(state: WorkflowState) -> WorkflowState:
    """Simulate data processing work."""
    import time
    import random
    
    # Simulate some processing time
    processing_time = random.uniform(1, 3)
    time.sleep(processing_time)
    
    input_data = state.get("input", "")
    processed_data = f"processed_{input_data}_{random.randint(1000, 9999)}"
    
    return {
        **state,
        "processed_data": processed_data,
        "processing_time": processing_time,
    }


def analysis_node(state: WorkflowState) -> WorkflowState:
    """Simulate analysis work."""
    import time
    import random
    
    # Simulate analysis time
    analysis_time = random.uniform(0.5, 2)
    time.sleep(analysis_time)
    
    processed_data = state.get("processed_data", "")
    analysis_result = {
        "word_count": len(processed_data.split("_")),
        "complexity_score": random.uniform(0.1, 1.0),
        "confidence": random.uniform(0.7, 0.99),
    }
    
    return {
        **state,
        "analysis": analysis_result,
        "analysis_time": analysis_time,
    }


def summary_node(state: WorkflowState) -> WorkflowState:
    """Generate final summary."""
    processed_data = state.get("processed_data", "")
    analysis = state.get("analysis", {})
    processing_time = state.get("processing_time", 0)
    analysis_time = state.get("analysis_time", 0)
    
    summary = {
        "total_time": processing_time + analysis_time,
        "data_length": len(processed_data),
        "analysis_summary": f"Processed with {analysis.get('confidence', 0):.2f} confidence",
        "status": "completed",
    }
    
    return {
        **state,
        "summary": summary,
    }


def create_distributed_workflow():
    """Create a distributed workflow graph."""
    # Define the workflow graph
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("data_processing", data_processing_node)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("summary", summary_node)
    
    # Define edges
    workflow.add_edge("data_processing", "analysis")
    workflow.add_edge("analysis", "summary")
    
    # Set entry point
    workflow.set_entry_point("data_processing")
    workflow.set_finish_point("summary")
    
    return workflow.compile(checkpointer=MemorySaver())


async def run_orchestrator():
    """Run the orchestrator component."""
    print("Starting Kafka Orchestrator...")
    
    # Create workflow
    graph = create_distributed_workflow()
    
    # Extract components for distributed runner
    # Note: This is a simplified example - in practice you'd need to
    # properly extract the processes, channels, and managed values
    # from the compiled graph
    
    processes = {
        "data_processing": PregelNode(
            channels={"state": "state_channel"},
            triggers=["state_channel"],
            node=RunnableLambda(data_processing_node),
        ),
        "analysis": PregelNode(
            channels={"state": "state_channel"},
            triggers=["state_channel"],
            node=RunnableLambda(analysis_node),
        ),
        "summary": PregelNode(
            channels={"state": "state_channel"},
            triggers=["state_channel"],
            node=RunnableLambda(summary_node),
        ),
    }
    
    channels = {
        "state_channel": LastValue(WorkflowState),
    }
    
    managed = ManagedValueMapping({})
    
    # Create distributed runner
    runner = DistributedPregelRunner(
        processes=processes,
        channels=channels,
        managed=managed,
        checkpointer=MemorySaver(),
        kafka_bootstrap_servers="localhost:9092",
        debug=True,
    )
    
    print("Orchestrator ready. Waiting for executors and workflow requests...")
    
    # In a real application, this would listen for workflow execution requests
    # For this example, we'll just keep the orchestrator running
    try:
        async with runner.distributed_execution(num_executors=0):  # No local executors
            # Keep orchestrator running
            await asyncio.sleep(3600)  # Run for 1 hour
    except KeyboardInterrupt:
        print("Orchestrator shutting down...")


async def run_executor():
    """Run an executor service."""
    print("Starting Kafka Executor...")
    
    try:
        await run_kafka_executors(
            num_executors=1,
            kafka_bootstrap_servers="localhost:9092",
            debug=True,
        )
    except KeyboardInterrupt:
        print("Executor shutting down...")


async def run_workflow():
    """Run a sample workflow using the distributed system."""
    print("Running distributed workflow...")
    
    # Create workflow
    graph = create_distributed_workflow()
    
    # For this example, we'll use the regular (non-distributed) execution
    # In practice, you'd integrate the distributed runner more deeply
    
    input_data = {
        "input": "sample_workflow_data",
        "timestamp": "2024-01-01T00:00:00",
    }
    
    print(f"Starting workflow with input: {input_data}")
    
    # Run the workflow
    config = RunnableConfig(
        configurable={"thread_id": "example_workflow_123"}
    )
    
    result = await graph.ainvoke(input_data, config)
    
    print("Workflow completed!")
    print(f"Result: {result}")
    
    return result


async def run_multiple_workflows():
    """Run multiple workflows concurrently to test distributed execution."""
    print("Running multiple concurrent workflows...")
    
    tasks = []
    for i in range(5):
        input_data = {
            "input": f"workflow_batch_{i}",
            "batch_id": i,
            "timestamp": "2024-01-01T00:00:00",
        }
        
        # In practice, these would be submitted to the distributed system
        task = asyncio.create_task(
            run_single_workflow(input_data, f"workflow_{i}"),
            name=f"workflow_{i}"
        )
        tasks.append(task)
    
    # Wait for all workflows to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    print(f"Completed {len(results)} workflows")
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Workflow {i} failed: {result}")
        else:
            print(f"Workflow {i} completed successfully")
    
    return results


async def run_single_workflow(input_data: Dict[str, Any], thread_id: str):
    """Run a single workflow instance."""
    graph = create_distributed_workflow()
    
    config = RunnableConfig(
        configurable={"thread_id": thread_id}
    )
    
    return await graph.ainvoke(input_data, config)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python kafka_distributed_execution.py [orchestrator|executor|workflow|multiple]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "orchestrator":
        asyncio.run(run_orchestrator())
    elif command == "executor":
        asyncio.run(run_executor())
    elif command == "workflow":
        asyncio.run(run_workflow())
    elif command == "multiple":
        asyncio.run(run_multiple_workflows())
    else:
        print(f"Unknown command: {command}")
        print("Available commands: orchestrator, executor, workflow, multiple")
        sys.exit(1)


if __name__ == "__main__":
    main()