#!/usr/bin/env python3
"""
Simple test runner for the structured response test
"""
import sys
import os

# Add the langgraph library to the path
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

# Import required modules
from typing import Any, List, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.language_models import BaseChatModel
from langchain_core.callbacks import CallbackManagerForLLMRun

# Import the modules we need to test
from langgraph.prebuilt.chat_agent_executor import create_react_agent

class WeatherResponse(BaseModel):
    temperature: float = Field(description="The temperature in fahrenheit")

class FakeToolCallingModel(BaseChatModel):
    """Fake model for testing that supports structured output"""
    
    def __init__(self, tool_calls=None, structured_response=None, **kwargs):
        super().__init__(**kwargs)
        self.tool_calls = tool_calls or []
        self.structured_response = structured_response
        self.index = 0

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a response"""
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
        return "fake-tool-call-model"

    def with_structured_output(self, schema, **kwargs):
        """Return a version that outputs structured responses"""
        class StructuredModel(BaseChatModel):
            def __init__(self, parent_model):
                super().__init__()
                self.parent_model = parent_model
                
            def _generate(self, messages, stop=None, run_manager=None, **kwargs):
                # Return the structured response directly
                return ChatResult(generations=[ChatGeneration(message=self.parent_model.structured_response)])
                
            @property
            def _llm_type(self):
                return "structured-fake-model"
                
            async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
                return self._generate(messages, stop, run_manager, **kwargs)
        
        return StructuredModel(self)

    def bind_tools(self, tools, **kwargs):
        """Bind tools to the model"""
        return self

def get_weather():
    """Get the weather"""
    return "The weather is sunny and 75°F."

def test_react_agent_with_structured_response():
    """Test the structured response functionality"""
    print("Running test_react_agent_with_structured_response...")
    
    tool_calls = [[{"args": {}, "id": "1", "name": "get_weather"}], []]
    expected_structured_response = WeatherResponse(temperature=75)
    
    model = FakeToolCallingModel(
        tool_calls=tool_calls, structured_response=expected_structured_response
    )
    
    # Test both response format types
    for i, response_format in enumerate([WeatherResponse, ("Meow", WeatherResponse)]):
        print(f"  Testing response format {i+1}: {response_format}")
        
        try:
            agent = create_react_agent(
                model, [get_weather], response_format=response_format
            )
            response = agent.invoke({"messages": [HumanMessage("What's the weather?")]})
            
            # Check if structured_response is in the response
            if "structured_response" not in response:
                print(f"    ❌ FAIL: 'structured_response' key not found in response")
                print(f"    Response keys: {list(response.keys())}")
                return False
                
            # Check if structured response matches expected
            if response["structured_response"] != expected_structured_response:
                print(f"    ❌ FAIL: structured_response mismatch")
                print(f"    Expected: {expected_structured_response}")
                print(f"    Got: {response['structured_response']}")
                return False
                
            # Check if messages are present
            if "messages" not in response:
                print(f"    ❌ FAIL: 'messages' key not found in response")
                return False
                
            print(f"    ✅ PASS: Response format {i+1} works correctly")
            print(f"    Structured response: {response['structured_response']}")
            print(f"    Messages count: {len(response['messages'])}")
            
        except Exception as e:
            print(f"    ❌ FAIL: Exception occurred: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("✅ All tests passed!")
    return True

if __name__ == "__main__":
    success = test_react_agent_with_structured_response()
    sys.exit(0 if success else 1)
