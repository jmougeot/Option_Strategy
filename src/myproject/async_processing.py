"""
Async Processing Module for Streamlit
Handles background processing with proper stop/cancel functionality
Uses a file-based approach for cross-process communication (more robust than Queue for large objects)
"""

import pickle
import tempfile
from multiprocessing import Process
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

# Temp directory for result files
TEMP_DIR = Path(tempfile.gettempdir()) / "option_strategy_results"
TEMP_DIR.mkdir(exist_ok=True)


@dataclass
class ProcessingState:
    """State of the background processing"""
    is_running: bool = False
    process: Optional[Process] = None
    result_file: Optional[Path] = None
    error: Optional[str] = None


def get_result_file_path(session_id: str) -> Path:
    """Get the path for the result file"""
    return TEMP_DIR / f"result_{session_id}.pkl"


def get_error_file_path(session_id: str) -> Path:
    """Get the path for the error file"""
    return TEMP_DIR / f"error_{session_id}.txt"


def cleanup_result_files(session_id: str):
    """Clean up result files from previous runs"""
    result_file = get_result_file_path(session_id)
    error_file = get_error_file_path(session_id)
    if result_file.exists():
        result_file.unlink()
    if error_file.exists():
        error_file.unlink()


def run_processing_worker(session_id: str, params_dict: Dict[str, Any]):
    """
    Worker function that runs in a separate process.
    Saves results to a file instead of using Queue (more robust for large objects).
    """
    try:
        # Import here to avoid issues with multiprocessing
        from myproject.main import process_bloomberg_to_strategies
        
        # Reconstruct filter and scenarios from dict if needed
        filter_data = params_dict["filter"]
        scenarios_data = params_dict["scenarios"]
        
        result = process_bloomberg_to_strategies(
            brut_code=params_dict["brut_code"],
            underlying=params_dict["underlying"],
            months=params_dict["months"],
            years=params_dict["years"],
            strikes=params_dict["strikes"],
            price_min=params_dict["price_min"],
            price_max=params_dict["price_max"],
            max_legs=params_dict["max_legs"],
            scoring_weights=params_dict["scoring_weights"],
            scenarios=scenarios_data,
            filter=filter_data,
            roll_expiries=params_dict["roll_expiries"],
        )
        
        # Save result to file
        result_file = get_result_file_path(session_id)
        with open(result_file, 'wb') as f:
            pickle.dump(result, f)
            
    except Exception as e:
        import traceback
        error_file = get_error_file_path(session_id)
        with open(error_file, 'w') as f:
            f.write(f"{str(e)}\n\n{traceback.format_exc()}")


def start_processing(session_id: str, params_dict: Dict[str, Any]) -> Process:
    """
    Start a background process for strategy computation.
    Returns the Process object.
    """
    cleanup_result_files(session_id)
    
    process = Process(
        target=run_processing_worker,
        args=(session_id, params_dict)
    )
    process.start()
    return process


def check_processing_status(session_id: str, process: Optional[Process]) -> Tuple[bool, bool, Optional[Any], Optional[str]]:
    """
    Check the status of the background processing.
    
    Returns:
        Tuple of (is_running, is_complete, result, error)
    """
    if process is None:
        return False, False, None, None
    
    is_alive = process.is_alive()
    
    if is_alive:
        return True, False, None, None
    
    # Process finished - check for results or errors
    result_file = get_result_file_path(session_id)
    error_file = get_error_file_path(session_id)
    
    if error_file.exists():
        with open(error_file, 'r') as f:
            error = f.read()
        return False, True, None, error
    
    if result_file.exists():
        try:
            with open(result_file, 'rb') as f:
                result = pickle.load(f)
            return False, True, result, None
        except Exception as e:
            return False, True, None, f"Failed to load result: {str(e)}"
    
    # Process finished but no result file - probably terminated
    return False, True, None, "Processing was terminated"


def stop_processing(process: Optional[Process]) -> bool:
    """
    Stop the background process immediately.
    Returns True if the process was terminated.
    """
    if process is None or not process.is_alive():
        return False
    
    process.terminate()
    process.join(timeout=2)
    
    # If still alive, force kill
    if process.is_alive():
        process.kill()
        process.join(timeout=1)
    
    return True
