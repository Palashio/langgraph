#!/usr/bin/env python3
"""
Simple test script to verify structured output functionality works correctly.
This bypasses the complex test infrastructure and directly tests the implementation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs/langgraph'))

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, ToolCall, ToolMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import tool as dec_tool

from langgraph.prebuilt import create_react_agent


class WeatherResponse(BaseModel):
    """Simple Pydantic model for testing structured output."""
    temperature: float
    wind_direction: str
    wind_speed: float


class FakeStructuredModel(BaseChatModel):
    """Fake model that supports structured output for testing."""
    
    def __init__(self, tool_calls: Optional[List[List[ToolCall]]] = None, **kwargs):
        super().__init__(**kwargs)
        self._tool_calls = tool_calls or [[]]
        self._index = 0
    
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """Generate a response."""
        messages_string = "-".join([m.content for m in messages])
        tool_calls = (
            self.tool_calls[self.index % len(self.tool_calls)]
            if self.tool_calls
            else []
        )
        message = AIMessage(
            content=messages_string, id=str(self.index), tool_calls=tool_calls.copy()
        )
        self.index += 1
        return ChatResult(generations=[ChatGeneration(message=message)])
    
    @property
    def _llm_type(self) -> str:
        return "fake-structured-model"
    
    def with_structured_output(self, schema, **kwargs):
        """Add structured output support for testing."""
        def _parse_output(ai_message):
            # Create a mock structured response
            if isinstance(schema, type) and issubclass(schema, BaseModel):
                if schema == WeatherResponse:
                    return WeatherResponse(
                        temperature=75.5,
                        wind_direction="North",
                        wind_speed=10.2
                    )
                else:
                    # Generic response for other models
                    return schema()
            return {"test": "response"}
        
        return self | RunnableLambda(_parse_output)


def test_basic_structured_output():
    """Test basic structured output generation."""
    print("Testing basic structured output generation...")
    
    model = FakeStructuredModel(tool_calls=[[]])  # No tool calls
    agent = create_react_agent(model, [], response_format=WeatherResponse)
    
    result = agent.invoke({"messages": [HumanMessage("What's the weather?")]})
    
    # Check that regular messages are present
    assert len(result["messages"]) == 2
    assert isinstance(result["messages"][0], HumanMessage)
    assert isinstance(result["messages"][1], AIMessage)
    
    # Check that structured_response is included
    assert "structured_response" in result
    assert isinstance(result["structured_response"], WeatherResponse)
    
    # Verify the structured response has expected values
    structured_resp = result["structured_response"]
    assert structured_resp.temperature == 75.5
    assert structured_resp.wind_direction == "North"
    assert structured_resp.wind_speed == 10.2
    
    print("✓ Basic structured output test passed!")


def test_without_response_format():
    """Test that agent works normally when response_format is not provided."""
    print("Testing agent without response_format...")
    
    model = FakeStructuredModel(tool_calls=[[]])  # No tool calls
    agent = create_react_agent(model, [])  # No response_format
    
    result = agent.invoke({"messages": [HumanMessage("Hello")]})
    
    # Check that regular messages are present
    assert len(result["messages"]) == 2
    assert isinstance(result["messages"][0], HumanMessage)
    assert isinstance(result["messages"][1], AIMessage)
    
    # Check that structured_response is NOT included
    assert "structured_response" not in result
    
    print("✓ No response_format test passed!")


def test_with_tools_then_structured():
    """Test tool calls followed by structured output generation."""
    print("Testing tool calls followed by structured output...")
    
    @dec_tool
    def get_weather(location: str) -> str:
        """Get weather for a location."""
        return f"Weather in {location}: sunny, 75°F"
    
    # First call has tool calls, second call has no tool calls
    tool_calls = [
        ToolCall(name="get_weather", args={"location": "NYC"}, id="1")
    ]
    model = FakeStructuredModel(tool_calls=[tool_calls, []])
    agent = create_react_agent(model, [get_weather], response_format=WeatherResponse)
    
    result = agent.invoke({"messages": [HumanMessage("What's the weather in NYC?")]})
    
    # Should have: HumanMessage, AIMessage with tool calls, ToolMessage, AIMessage
    assert len(result["messages"]) == 4
    assert isinstance(result["messages"][0], HumanMessage)
    assert isinstance(result["messages"][1], AIMessage)
    assert len(result["messages"][1].tool_calls) == 1
    assert isinstance(result["messages"][2], ToolMessage)
    assert isinstance(result["messages"][3], AIMessage)
    
    # Check that structured_response is included after tool execution
    assert "structured_response" in result
    assert isinstance(result["structured_response"], WeatherResponse)
    
    print("✓ Tool calls + structured output test passed!")


def test_no_tools_immediate_structured():
    """Test structured output when no tools are provided."""
    print("Testing immediate structured output with no tools...")
    
    model = FakeStructuredModel(tool_calls=[[]])  # No tool calls
    agent = create_react_agent(model, [], response_format=WeatherResponse)  # No tools
    
    result = agent.invoke({"messages": [HumanMessage("What's the weather?")]})
    
    # Should immediately generate structured output since no tools are available
    assert len(result["messages"]) == 2  # Human, AI
    assert "structured_response" in result
    assert isinstance(result["structured_response"], WeatherResponse)
    
    print("✓ No tools immediate structured output test passed!")


def main():
    """Run all tests."""
    print("Running structured output tests...\n")
    
    try:
        test_basic_structured_output()
        test_without_response_format()
        test_with_tools_then_structured()
        test_no_tools_immediate_structured()
        
        print("\n🎉 All tests passed! Structured output functionality is working correctly.")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

