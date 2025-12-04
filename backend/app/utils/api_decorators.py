"""
API decorators for common error handling and response formatting
"""
from functools import wraps
from typing import Callable, Any
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError


def handle_api_errors(func: Callable) -> Callable:
    """
    Decorator to handle common API errors uniformly
    
    Handles:
    - ValueError -> HTTPException 400
    - IntegrityError -> HTTPException 400 with appropriate message
    - HTTPException -> re-raise
    - Other exceptions -> HTTPException 400
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except IntegrityError as e:
            error_str = str(e).lower()
            if 'name' in error_str or 'unique' in error_str:
                raise HTTPException(status_code=400, detail="已存在对应记录，请修改名称")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    return wrapper


def handle_not_found(not_found_message: str = "Resource not found"):
    """
    Decorator factory to handle 404 errors
    
    Args:
        not_found_message: Message to return when resource is not found
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import inspect
            if inspect.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            if result is None:
                raise HTTPException(status_code=404, detail=not_found_message)
            return result
        return wrapper
    return decorator

