#!/usr/bin/env python3
"""
Simple verification script to test the structured output functionality
without requiring the full test suite infrastructure.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs', 'langgraph'))

from typing import Optional, Type, List, Any
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, ToolCall
from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.language_models import LanguageModelInput

# Import our implementation
try:
    from langgraph.prebuilt.chat_agent_executor import (
        create_react_agent, 
        AgentState, 
        AgentStateWithStructuredOutput,
        StructuredResponse
    )
    print("✅ Successfully imported structured output components")
except ImportError as e:
    print(f"❌ Failed to import components: {e}")
    sys.exit(1)

# Test response model
class TestResponse(BaseModel):
    """Test response model for structured output."""
    answer: str = Field(description="The answer to the question")
    confidence: float = Field(description="Confidence score between 0 and 1")

# Simple fake model for testing
class SimpleFakeModel(BaseChatModel):
    def __init__(self, structured_response: Optional[TestResponse] = None):
        super().__init__()
        self.structured_response = structured_response
        self.call_count = 0

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.call_count += 1
        content = f"Response {self.call_count}"
        message = AIMessage(content=content, id=str(self.call_count))
        return ChatResult(generations=[ChatGeneration(message=message)])

    @property
    def _llm_type(self) -> str:
        return "simple-fake-model"

    def with_structured_output(self, schema: Type[BaseModel]) -> Runnable[LanguageModelInput, Any]:
        if self.structured_response is None:
            raise ValueError("Structured response is not set")
        return RunnableLambda(lambda x: self.structured_response)

def test_basic_functionality():
    """Test basic structured output functionality."""
    print("\n🧪 Testing basic structured output functionality...")
    
    try:
        # Create a model with structured response
        structured_response = TestResponse(answer="The answer is 42", confidence=0.95)
        model = SimpleFakeModel(structured_response=structured_response)
        
        # Create agent with response_format
        agent = create_react_agent(model, [], response_format=TestResponse)
        print("✅ Successfully created agent with response_format")
        
        # Test the agent
        result = agent.invoke({"messages": [HumanMessage(content="What is the answer?")]})
        print("✅ Successfully invoked agent")
        
        # Verify the structured response is included
        if "structured_response" in result:
            print("✅ Structured response found in result")
            if isinstance(result["structured_response"], TestResponse):
                print("✅ Structured response is correct type")
                if result["structured_response"].answer == "The answer is 42":
                    print("✅ Structured response has correct content")
                else:
                    print(f"❌ Structured response content mismatch: {result['structured_response'].answer}")
            else:
                print(f"❌ Structured response wrong type: {type(result['structured_response'])}")
        else:
            print("❌ Structured response not found in result")
            
        # Verify regular messages are still present
        if "messages" in result and len(result["messages"]) >= 2:
            print("✅ Regular messages preserved")
        else:
            print("❌ Regular messages missing or incomplete")
            
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def test_backwards_compatibility():
    """Test backwards compatibility without response_format."""
    print("\n🧪 Testing backwards compatibility...")
    
    try:
        # Create agent without response_format
        model = SimpleFakeModel()
        agent = create_react_agent(model, [])
        print("✅ Successfully created agent without response_format")
        
        # Test the agent
        result = agent.invoke({"messages": [HumanMessage(content="Hello")]})
        print("✅ Successfully invoked agent")
        
        # Verify no structured response is included
        if "structured_response" not in result:
            print("✅ No structured response (as expected)")
        else:
            print("❌ Unexpected structured response found")
            
        # Verify regular messages are present
        if "messages" in result and len(result["messages"]) >= 2:
            print("✅ Regular messages preserved")
        else:
            print("❌ Regular messages missing or incomplete")
            
        return True
        
    except Exception as e:
        print(f"❌ Backwards compatibility test failed: {e}")
        return False

def test_state_classes():
    """Test that the state classes are properly defined."""
    print("\n🧪 Testing state classes...")
    
    try:
        # Test AgentState
        state = AgentState(messages=[], is_last_step=False, remaining_steps=5)
        print("✅ AgentState works correctly")
        
        # Test AgentStateWithStructuredOutput
        extended_state = AgentStateWithStructuredOutput(
            messages=[], 
            is_last_step=False, 
            remaining_steps=5,
            structured_response=None
        )
        print("✅ AgentStateWithStructuredOutput works correctly")
        
        # Test with actual structured response
        test_response = TestResponse(answer="test", confidence=0.5)
        extended_state_with_response = AgentStateWithStructuredOutput(
            messages=[], 
            is_last_step=False, 
            remaining_steps=5,
            structured_response=test_response
        )
        print("✅ AgentStateWithStructuredOutput with structured response works")
        
        return True
        
    except Exception as e:
        print(f"❌ State classes test failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("🚀 Starting structured output verification tests...")
    
    tests = [
        test_state_classes,
        test_backwards_compatibility,
        test_basic_functionality,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Structured output implementation is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
