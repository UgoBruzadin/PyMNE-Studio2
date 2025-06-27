"""Pipeline management for QuickLab preprocessing and analysis workflows."""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

from PyQt6.QtCore import QObject, pyqtSignal

from ..utils.logger import get_logger

logger = get_logger(__name__)


class StepStatus(Enum):
    """Status of a pipeline step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineStep:
    """Represents a single step in an analysis pipeline.
    
    Parameters
    ----------
    name : str
        Name of the step.
    function : callable
        Function to execute for this step.
    parameters : dict
        Parameters to pass to the function.
    dependencies : list
        List of step names this step depends on.
    description : str
        Human-readable description of the step.
    """
    name: str
    function: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    description: str = ""
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None


class PipelineManager(QObject):
    """Manages analysis and preprocessing pipelines.
    
    The PipelineManager allows creation, execution, and monitoring of
    complex analysis workflows with dependency resolution and error handling.
    
    Signals
    -------
    step_started : str
        Emitted when a step starts execution (step_name).
    step_completed : str, Any
        Emitted when a step completes (step_name, result).
    step_failed : str, str
        Emitted when a step fails (step_name, error).
    pipeline_completed : str
        Emitted when entire pipeline completes (pipeline_name).
    pipeline_failed : str, str
        Emitted when pipeline fails (pipeline_name, error).
    """
    
    # Qt signals
    step_started = pyqtSignal(str)
    step_completed = pyqtSignal(str, object)
    step_failed = pyqtSignal(str, str)
    pipeline_completed = pyqtSignal(str)
    pipeline_failed = pyqtSignal(str, str)
    
    def __init__(self) -> None:
        """Initialize the PipelineManager."""
        super().__init__()
        self._pipelines: Dict[str, List[PipelineStep]] = {}
        self._pipeline_data: Dict[str, Dict[str, Any]] = {}
        
        logger.info("PipelineManager initialized")
    
    def create_pipeline(self, name: str) -> None:
        """Create a new empty pipeline.
        
        Parameters
        ----------
        name : str
            Name of the pipeline.
        """
        self._pipelines[name] = []
        self._pipeline_data[name] = {}
        logger.info(f"Created pipeline: {name}")
    
    def add_step(self, pipeline_name: str, step: PipelineStep) -> None:
        """Add a step to a pipeline.
        
        Parameters
        ----------
        pipeline_name : str
            Name of the pipeline.
        step : PipelineStep
            Step to add.
            
        Raises
        ------
        KeyError
            If pipeline doesn't exist.
        ValueError
            If step name already exists in pipeline.
        """
        if pipeline_name not in self._pipelines:
            raise KeyError(f"Pipeline '{pipeline_name}' does not exist")
        
        # Check for duplicate step names
        existing_names = [s.name for s in self._pipelines[pipeline_name]]
        if step.name in existing_names:
            raise ValueError(f"Step '{step.name}' already exists in pipeline '{pipeline_name}'")
        
        self._pipelines[pipeline_name].append(step)
        logger.debug(f"Added step '{step.name}' to pipeline '{pipeline_name}'")
    
    def remove_step(self, pipeline_name: str, step_name: str) -> None:
        """Remove a step from a pipeline.
        
        Parameters
        ----------
        pipeline_name : str
            Name of the pipeline.
        step_name : str
            Name of the step to remove.
            
        Raises
        ------
        KeyError
            If pipeline or step doesn't exist.
        """
        if pipeline_name not in self._pipelines:
            raise KeyError(f"Pipeline '{pipeline_name}' does not exist")
        
        pipeline = self._pipelines[pipeline_name]
        step_index = None
        
        for i, step in enumerate(pipeline):
            if step.name == step_name:
                step_index = i
                break
        
        if step_index is None:
            raise KeyError(f"Step '{step_name}' not found in pipeline '{pipeline_name}'")
        
        del pipeline[step_index]
        logger.debug(f"Removed step '{step_name}' from pipeline '{pipeline_name}'")
    
    def execute_pipeline(self, pipeline_name: str, input_data: Dict[str, Any]) -> bool:
        """Execute a complete pipeline.
        
        Parameters
        ----------
        pipeline_name : str
            Name of the pipeline to execute.
        input_data : dict
            Initial data for the pipeline.
            
        Returns
        -------
        bool
            True if pipeline completed successfully, False otherwise.
        """
        if pipeline_name not in self._pipelines:
            error_msg = f"Pipeline '{pipeline_name}' does not exist"
            logger.error(error_msg)
            self.pipeline_failed.emit(pipeline_name, error_msg)
            return False
        
        logger.info(f"Starting pipeline execution: {pipeline_name}")
        
        # Initialize pipeline data
        self._pipeline_data[pipeline_name] = input_data.copy()
        
        # Reset step statuses
        for step in self._pipelines[pipeline_name]:
            step.status = StepStatus.PENDING
            step.result = None
            step.error = None
        
        try:
            # Resolve execution order
            execution_order = self._resolve_dependencies(pipeline_name)
            
            # Execute steps in order
            for step_name in execution_order:
                step = self._get_step(pipeline_name, step_name)
                if not self._execute_step(pipeline_name, step):
                    # Step failed, abort pipeline
                    self.pipeline_failed.emit(pipeline_name, step.error or "Unknown error")
                    return False
            
            logger.info(f"Pipeline completed successfully: {pipeline_name}")
            self.pipeline_completed.emit(pipeline_name)
            return True
            
        except Exception as e:
            error_msg = f"Pipeline execution failed: {e}"
            logger.error(error_msg)
            self.pipeline_failed.emit(pipeline_name, error_msg)
            return False
    
    def _resolve_dependencies(self, pipeline_name: str) -> List[str]:
        """Resolve step dependencies and return execution order.
        
        Parameters
        ----------
        pipeline_name : str
            Name of the pipeline.
            
        Returns
        -------
        list
            List of step names in execution order.
            
        Raises
        ------
        ValueError
            If circular dependencies are detected.
        """
        pipeline = self._pipelines[pipeline_name]
        
        # Build dependency graph
        graph = {}
        for step in pipeline:
            graph[step.name] = step.dependencies.copy()
        
        # Topological sort
        result = []
        visited = set()
        temp_visited = set()
        
        def visit(node):
            if node in temp_visited:
                raise ValueError(f"Circular dependency detected involving step '{node}'")
            if node in visited:
                return
            
            temp_visited.add(node)
            for dependency in graph.get(node, []):
                visit(dependency)
            temp_visited.remove(node)
            visited.add(node)
            result.append(node)
        
        for step_name in graph:
            if step_name not in visited:
                visit(step_name)
        
        return result
    
    def _get_step(self, pipeline_name: str, step_name: str) -> PipelineStep:
        """Get a step by name from a pipeline.
        
        Parameters
        ----------
        pipeline_name : str
            Name of the pipeline.
        step_name : str
            Name of the step.
            
        Returns
        -------
        PipelineStep
            The requested step.
            
        Raises
        ------
        KeyError
            If step is not found.
        """
        for step in self._pipelines[pipeline_name]:
            if step.name == step_name:
                return step
        
        raise KeyError(f"Step '{step_name}' not found in pipeline '{pipeline_name}'")
    
    def _execute_step(self, pipeline_name: str, step: PipelineStep) -> bool:
        """Execute a single pipeline step.
        
        Parameters
        ----------
        pipeline_name : str
            Name of the pipeline.
        step : PipelineStep
            Step to execute.
            
        Returns
        -------
        bool
            True if step completed successfully, False otherwise.
        """
        logger.info(f"Executing step: {step.name}")
        step.status = StepStatus.RUNNING
        self.step_started.emit(step.name)
        
        try:
            # Prepare step input
            step_input = self._pipeline_data[pipeline_name].copy()
            step_input.update(step.parameters)
            
            # Execute step function
            result = step.function(**step_input)
            
            # Store result
            step.result = result
            step.status = StepStatus.COMPLETED
            
            # Update pipeline data with result if it's a dictionary
            if isinstance(result, dict):
                self._pipeline_data[pipeline_name].update(result)
            else:
                # Store result with step name as key
                self._pipeline_data[pipeline_name][f"{step.name}_result"] = result
            
            logger.info(f"Step completed successfully: {step.name}")
            self.step_completed.emit(step.name, result)
            return True
            
        except Exception as e:
            error_msg = str(e)
            step.error = error_msg
            step.status = StepStatus.FAILED
            
            logger.error(f"Step failed: {step.name} - {error_msg}")
            self.step_failed.emit(step.name, error_msg)
            return False
    
    def get_pipeline_result(self, pipeline_name: str) -> Dict[str, Any]:
        """Get the final result data from a pipeline.
        
        Parameters
        ----------
        pipeline_name : str
            Name of the pipeline.
            
        Returns
        -------
        dict
            Pipeline result data.
        """
        return self._pipeline_data.get(pipeline_name, {}).copy()
    
    def get_step_status(self, pipeline_name: str, step_name: str) -> StepStatus:
        """Get the status of a specific step.
        
        Parameters
        ----------
        pipeline_name : str
            Name of the pipeline.
        step_name : str
            Name of the step.
            
        Returns
        -------
        StepStatus
            Current status of the step.
        """
        step = self._get_step(pipeline_name, step_name)
        return step.status
    
    def get_pipeline_steps(self, pipeline_name: str) -> List[PipelineStep]:
        """Get all steps in a pipeline.
        
        Parameters
        ----------
        pipeline_name : str
            Name of the pipeline.
            
        Returns
        -------
        list
            List of pipeline steps.
        """
        return self._pipelines.get(pipeline_name, []).copy()
    
    def get_pipeline_names(self) -> List[str]:
        """Get names of all pipelines.
        
        Returns
        -------
        list
            List of pipeline names.
        """
        return list(self._pipelines.keys())
    
    def clear_pipeline(self, pipeline_name: str) -> None:
        """Clear all steps from a pipeline.
        
        Parameters
        ----------
        pipeline_name : str
            Name of the pipeline to clear.
        """
        if pipeline_name in self._pipelines:
            self._pipelines[pipeline_name].clear()
            self._pipeline_data[pipeline_name].clear()
            logger.info(f"Cleared pipeline: {pipeline_name}")
    
    def delete_pipeline(self, pipeline_name: str) -> None:
        """Delete a pipeline completely.
        
        Parameters
        ----------
        pipeline_name : str
            Name of the pipeline to delete.
        """
        if pipeline_name in self._pipelines:
            del self._pipelines[pipeline_name]
            del self._pipeline_data[pipeline_name]
            logger.info(f"Deleted pipeline: {pipeline_name}")