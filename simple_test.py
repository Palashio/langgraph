#!/usr/bin/env python3
"""
Simple test to verify structured response functionality
"""
import sys
import os

# Add the langgraph library to the path
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

try:
    # Import required modules
    from pydantic import BaseModel, Field
    from langchain_core.messages import HumanMessage
    
    # Try to import the create_react_agent function
    from langgraph.prebuilt.chat_agent_executor import create_react_agent
    
    print("✅ Successfully imported create_react_agent")
    
    # Check if the function has the response_format parameter
    import inspect
    sig = inspect.signature(create_react_agent)
    if 'response_format' in sig.parameters:
        print("✅ response_format parameter found in create_react_agent signature")
        print(f"   Parameter: {sig.parameters['response_format']}")
    else:
        print("❌ response_format parameter NOT found in create_react_agent signature")
        print(f"   Available parameters: {list(sig.parameters.keys())}")
        sys.exit(1)
    
    # Try to import StructuredResponse
    try:
        from langgraph.prebuilt.chat_agent_executor import StructuredResponse
        print("✅ Successfully imported StructuredResponse")
    except ImportError as e:
        print(f"❌ Failed to import StructuredResponse: {e}")
        sys.exit(1)
    
    # Try to import AgentState and check if it has structured_response field
    try:
        from langgraph.prebuilt.chat_agent_executor import AgentState
        print("✅ Successfully imported AgentState")
        
        # Check if AgentState has structured_response field
        if hasattr(AgentState, '__annotations__') and 'structured_response' in AgentState.__annotations__:
            print("✅ AgentState has structured_response field")
            print(f"   Field type: {AgentState.__annotations__['structured_response']}")
        else:
            print("❌ AgentState does NOT have structured_response field")
            if hasattr(AgentState, '__annotations__'):
                print(f"   Available fields: {list(AgentState.__annotations__.keys())}")
            sys.exit(1)
            
    except ImportError as e:
        print(f"❌ Failed to import AgentState: {e}")
        sys.exit(1)
    
    print("\n✅ All imports and basic checks passed!")
    print("The structured response implementation appears to be correctly integrated.")
    
except Exception as e:
    print(f"❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
