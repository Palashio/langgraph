"""Tests for the new context API that replaces config['configurable']."""

import pytest
import warnings
from dataclasses import dataclass
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START
from langgraph.runtime import Runtime, get_runtime
from langgraph.warnings import LangGraphDeprecatedSinceV05


@dataclass
class TestContext:
    user_id: str
    temperature: float = 0.7


class SimpleState(TypedDict):
    messages: list[str]
    result: str


def test_runtime_injection_basic():
    """Test basic Runtime parameter injection."""
    
    def node_with_runtime(state: SimpleState, runtime: Runtime[TestContext]) -> SimpleState:
        user_id = runtime.context.user_id
        temp = runtime.context.temperature
        return {
            "result": f"Hello {user_id} with temp {temp}",
            "messages": state["messages"] + [f"processed by {user_id}"]
        }

    graph = StateGraph(SimpleState, context_schema=TestContext)
    graph.add_node("process", node_with_runtime)
    graph.add_edge(START, "process")
    compiled = graph.compile()

    result = compiled.invoke(
        {"messages": [], "result": ""}, 
        context={"user_id": "alice", "temperature": 0.9}
    )
    
    assert result["result"] == "Hello alice with temp 0.9"
    assert "processed by alice" in result["messages"]


def test_get_runtime_function():
    """Test get_runtime() function for accessing runtime context."""
    
    def node_with_get_runtime(state: SimpleState) -> SimpleState:
        runtime = get_runtime(TestContext)
        user_id = runtime.context.user_id
        temp = runtime.context.temperature
        return {
            "result": f"Got {user_id} with temp {temp}",
            "messages": state["messages"] + [f"got {user_id}"]
        }

    graph = StateGraph(SimpleState, context_schema=TestContext)
    graph.add_node("process", node_with_get_runtime)
    graph.add_edge(START, "process")
    compiled = graph.compile()

    result = compiled.invoke(
        {"messages": [], "result": ""}, 
        context={"user_id": "bob", "temperature": 0.5}
    )
    
    assert result["result"] == "Got bob with temp 0.5"
    assert "got bob" in result["messages"]


def test_backward_compatibility_config_schema():
    """Test that config_schema still works but shows deprecation warning."""
    
    def node_with_config(state: SimpleState, config) -> SimpleState:
        user_id = config.get("configurable", {}).get("user_id", "unknown")
        return {
            "result": f"Config user: {user_id}",
            "messages": state["messages"] + [user_id]
        }

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        graph = StateGraph(SimpleState, config_schema=TestContext)
        
        # Check deprecation warning was issued
        assert len(w) == 1
        assert issubclass(w[0].category, LangGraphDeprecatedSinceV05)
        assert "config_schema" in str(w[0].message)

    graph.add_node("process", node_with_config)
    graph.add_edge(START, "process")
    compiled = graph.compile()

    # Test with new context parameter (should work due to backward compatibility)
    result = compiled.invoke(
        {"messages": [], "result": ""}, 
        context={"user_id": "charlie"}
    )
    
    assert result["result"] == "Config user: charlie"


def test_backward_compatibility_configurable():
    """Test that old config['configurable'] pattern still works."""
    
    def node_with_config(state: SimpleState, config) -> SimpleState:
        user_id = config["configurable"].get("user_id", "unknown")
        return {
            "result": f"Old config user: {user_id}",
            "messages": state["messages"] + [user_id]
        }

    graph = StateGraph(SimpleState, context_schema=TestContext)
    graph.add_node("process", node_with_config)
    graph.add_edge(START, "process")
    compiled = graph.compile()

    # Test with old configurable pattern
    result = compiled.invoke(
        {"messages": [], "result": ""}, 
        config={"configurable": {"user_id": "david"}}
    )
    
    assert result["result"] == "Old config user: david"


def test_context_jsonschema():
    """Test get_context_jsonschema method."""
    
    graph = StateGraph(SimpleState, context_schema=TestContext)
    graph.add_node("dummy", lambda s: s)
    graph.add_edge(START, "dummy")
    compiled = graph.compile()
    
    schema = compiled.get_context_jsonschema()
    assert schema is not None
    assert "properties" in schema
    assert "user_id" in schema["properties"]
    assert "temperature" in schema["properties"]


def test_config_specs_deprecation():
    """Test that config_specs property shows deprecation warning."""
    
    graph = StateGraph(SimpleState, context_schema=TestContext)
    graph.add_node("dummy", lambda s: s)
    graph.add_edge(START, "dummy")
    compiled = graph.compile()
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        specs = compiled.config_specs
        
        # Check deprecation warning was issued
        assert len(w) == 1
        assert issubclass(w[0].category, LangGraphDeprecatedSinceV05)
        assert "config_specs" in str(w[0].message)
        
        # Should still return something for backward compatibility
        assert isinstance(specs, list)


def test_no_context_schema():
    """Test behavior when no context schema is provided."""
    
    def simple_node(state: SimpleState) -> SimpleState:
        return {
            "result": "no context",
            "messages": state["messages"] + ["processed"]
        }

    graph = StateGraph(SimpleState)  # No context schema
    graph.add_node("process", simple_node)
    graph.add_edge(START, "process")
    compiled = graph.compile()

    result = compiled.invoke({"messages": [], "result": ""})
    assert result["result"] == "no context"
    
    # get_context_jsonschema should return None
    assert compiled.get_context_jsonschema() is None


def test_mixed_node_types():
    """Test mixing nodes with and without Runtime parameters."""
    
    def node_without_runtime(state: SimpleState) -> SimpleState:
        return {
            "messages": state["messages"] + ["no runtime"],
            "result": state["result"]
        }
    
    def node_with_runtime(state: SimpleState, runtime: Runtime[TestContext]) -> SimpleState:
        user_id = runtime.context.user_id
        return {
            "messages": state["messages"] + [f"with runtime: {user_id}"],
            "result": f"processed by {user_id}"
        }

    graph = StateGraph(SimpleState, context_schema=TestContext)
    graph.add_node("no_runtime", node_without_runtime)
    graph.add_node("with_runtime", node_with_runtime)
    graph.add_edge(START, "no_runtime")
    graph.add_edge("no_runtime", "with_runtime")
    compiled = graph.compile()

    result = compiled.invoke(
        {"messages": [], "result": ""}, 
        context={"user_id": "eve", "temperature": 0.3}
    )
    
    assert "no runtime" in result["messages"]
    assert "with runtime: eve" in result["messages"]
    assert result["result"] == "processed by eve"


def test_stream_with_context():
    """Test streaming with context parameter."""
    
    def node_with_runtime(state: SimpleState, runtime: Runtime[TestContext]) -> SimpleState:
        user_id = runtime.context.user_id
        return {
            "result": f"Streamed for {user_id}",
            "messages": state["messages"] + [f"streamed: {user_id}"]
        }

    graph = StateGraph(SimpleState, context_schema=TestContext)
    graph.add_node("process", node_with_runtime)
    graph.add_edge(START, "process")
    compiled = graph.compile()

    chunks = list(compiled.stream(
        {"messages": [], "result": ""}, 
        context={"user_id": "frank", "temperature": 1.0},
        stream_mode="values"
    ))
    
    # Should get at least the final result
    final_chunk = chunks[-1]
    assert final_chunk["result"] == "Streamed for frank"
    assert "streamed: frank" in final_chunk["messages"]


if __name__ == "__main__":
    pytest.main([__file__])