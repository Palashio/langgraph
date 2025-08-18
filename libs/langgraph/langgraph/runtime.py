"""Runtime context API for LangGraph.

This module provides a new API for accessing runtime context in LangGraph nodes,
replacing the previous config['configurable'] pattern with a cleaner, type-safe approach.
"""

from __future__ import annotations

import contextvars
import inspect
import warnings
from functools import wraps
from typing_extensions import Any, Callable, Generic, TypeVar, cast

from langchain_core.runnables import RunnableConfig

from langgraph.config import get_config, get_store, get_stream_writer
from langgraph.store.base import BaseStore
from langgraph.types import StreamWriter
from langgraph.warnings import LangGraphDeprecatedSinceV05

ContextSchema = TypeVar("ContextSchema")

# Context variable to store the current runtime instance
_current_runtime: contextvars.ContextVar[Runtime[Any] | None] = contextvars.ContextVar(
    "_current_runtime", default=None
)


class Runtime(Generic[ContextSchema]):
    """Runtime context object that provides access to context, store, and stream writer.
    
    This class replaces the previous pattern of accessing config['configurable'] and
    provides a unified interface for runtime dependencies.
    
    Attributes:
        context: The typed context object containing user-provided configuration
        store: The LangGraph store instance (if available)
        stream_writer: The stream writer for custom output (if available)
    """
    
    def __init__(
        self, 
        context: ContextSchema,
        store: BaseStore | None = None,
        stream_writer: StreamWriter | None = None,
        config: RunnableConfig | None = None,
    ):
        """Initialize a Runtime instance.
        
        Args:
            context: The typed context object
            store: Optional store instance
            stream_writer: Optional stream writer
            config: Optional runnable config (for backward compatibility)
        """
        self.context = context
        self._store = store
        self._stream_writer = stream_writer
        self._config = config
    
    @property
    def store(self) -> BaseStore:
        """Get the LangGraph store instance.
        
        Returns:
            The store instance
            
        Raises:
            RuntimeError: If no store is available
        """
        if self._store is not None:
            return self._store
        
        # Fall back to the global store access pattern for backward compatibility
        try:
            return get_store()
        except RuntimeError:
            raise RuntimeError("No store available in runtime context")
    
    @property
    def stream_writer(self) -> StreamWriter:
        """Get the stream writer for custom output.
        
        Returns:
            The stream writer function
        """
        if self._stream_writer is not None:
            return self._stream_writer
        
        # Fall back to the global stream writer access pattern for backward compatibility
        return get_stream_writer()


def get_runtime(context_schema: type[ContextSchema] | None = None) -> Runtime[ContextSchema]:
    """Get the current runtime context.
    
    This function can be called from within any LangGraph node to access the
    runtime context, store, and stream writer without needing explicit parameters.
    
    Args:
        context_schema: Optional type hint for the context schema (for better typing)
        
    Returns:
        The current Runtime instance with typed context access
        
    Raises:
        RuntimeError: If called outside of a runtime context
        
    Example:
        ```python
        from dataclasses import dataclass
        from langgraph.runtime import get_runtime
        
        @dataclass
        class MyContext:
            user_id: str
            temperature: float
            
        def my_node(state: State):
            runtime = get_runtime(MyContext)
            user_id = runtime.context.user_id
            temperature = runtime.context.temperature
            
            # Access store and stream writer
            runtime.store.put(("users", user_id), "data", {"temp": temperature})
            runtime.stream_writer({"debug": f"Processing for user {user_id}"})
            
            return {"result": "processed"}
        ```
    """
    current = _current_runtime.get()
    if current is None:
        raise RuntimeError(
            "get_runtime() can only be called within a LangGraph node execution context. "
            "Make sure you're calling this from within a node function."
        )
    
    return cast(Runtime[ContextSchema], current)


def _set_runtime(runtime: Runtime[Any] | None) -> None:
    """Internal function to set the current runtime context.
    
    This is used internally by the LangGraph execution engine and should not
    be called directly by user code.
    """
    _current_runtime.set(runtime)


def _create_runtime_from_config(
    config: RunnableConfig, 
    context_schema: type[ContextSchema] | None = None
) -> Runtime[ContextSchema]:
    """Create a Runtime instance from a RunnableConfig.
    
    This function handles the migration from the old config['configurable'] pattern
    to the new context API. It looks for context in both the new 'context' key and
    the legacy 'configurable' key.
    
    Args:
        config: The RunnableConfig containing context information
        context_schema: Optional schema type for the context
        
    Returns:
        Runtime instance with context extracted from config
    """
    # Try to get context from new 'context' key first
    context_data = config.get("context")
    
    if context_data is None:
        # Fall back to legacy 'configurable' pattern
        configurable = config.get("configurable", {})
        if configurable:
            # Issue a deprecation warning
            warnings.warn(
                "Using config['configurable'] is deprecated. "
                "Please use the new 'context' parameter instead. "
                "See the migration guide for details.",
                category=LangGraphDeprecatedSinceV05,
                stacklevel=3,
            )
            context_data = configurable
    
    if context_data is None:
        context_data = {}
    
    # If we have a context schema, try to instantiate it
    if context_schema is not None:
        if hasattr(context_schema, '__annotations__'):
            # For dataclasses, TypedDict, etc.
            try:
                context = context_schema(**context_data)  # type: ignore
            except (TypeError, ValueError):
                # If instantiation fails, just use the raw data
                context = cast(ContextSchema, context_data)
        else:
            context = cast(ContextSchema, context_data)
    else:
        context = cast(ContextSchema, context_data)
    
    # Try to get store and stream writer from config
    store = None
    stream_writer = None
    
    try:
        store = get_store()
    except RuntimeError:
        pass
        
    try:
        stream_writer = get_stream_writer()
    except RuntimeError:
        pass
    
    return Runtime(
        context=context,
        store=store,
        stream_writer=stream_writer,
        config=config,
    )


def _wrap_node_function(
    func: Callable[..., Any], 
    context_schema: type[ContextSchema] | None = None
) -> Callable[..., Any]:
    """Wrap a node function to inject Runtime parameter if expected.
    
    This function inspects the node function's signature and if it expects a Runtime
    parameter, injects it automatically from the current execution context.
    
    Args:
        func: The node function to wrap
        context_schema: Optional context schema type for the runtime
        
    Returns:
        Wrapped function that injects Runtime when needed
    """
    if not callable(func):
        return func
        
    try:
        sig = inspect.signature(func)
        
        # Check if function expects Runtime parameter
        runtime_param = None
        for param_name, param in sig.parameters.items():
            if param.annotation is not None and hasattr(param.annotation, '__origin__'):
                # Handle Generic types like Runtime[ContextSchema]
                if param.annotation.__origin__ is Runtime:
                    runtime_param = param_name
                    break
            elif param.annotation is Runtime:
                runtime_param = param_name
                break
        
        # If no Runtime parameter expected, return original function
        if runtime_param is None:
            return func
            
        @wraps(func)
        def wrapped(*args, **kwargs):
            # Create Runtime from current config context
            try:
                config = get_config()
                runtime = _create_runtime_from_config(config, context_schema)
                
                # Set in context variable for get_runtime() calls
                token = _current_runtime.set(runtime)
                try:
                    # Inject runtime as keyword argument
                    kwargs[runtime_param] = runtime
                    return func(*args, **kwargs)
                finally:
                    _current_runtime.reset(token)
            except RuntimeError:
                # Fallback: call function without Runtime injection
                return func(*args, **kwargs)
                
        return wrapped
        
    except Exception:
        # If inspection fails, return original function
        return func