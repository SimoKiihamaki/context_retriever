"""
Project management module for Code Context Retriever.
Handles tracking and switching between different projects.
"""

import os
import json
from typing import Dict, Any, Optional, List
import logging

from .utils.logging import get_logger

logger = get_logger(__name__)

# User home directory for storing project config
USER_CONFIG_DIR = os.path.expanduser("~/.code_context_retriever")
PROJECTS_FILE = os.path.join(USER_CONFIG_DIR, "projects.json")
CURRENT_PROJECT_FILE = os.path.join(USER_CONFIG_DIR, "current_project")

class ProjectManager:
    """
    Manages project configuration and the current active project.
    """
    
    def __init__(self):
        """Initialize the project manager."""
        self.projects = {}
        self.current_project = None
        
        # Create config directory if it doesn't exist
        if not os.path.exists(USER_CONFIG_DIR):
            os.makedirs(USER_CONFIG_DIR, exist_ok=True)
        
        # Load projects and current project
        self._load_projects()
        self._load_current_project()
    
    def _load_projects(self) -> None:
        """Load projects from the projects file."""
        if os.path.exists(PROJECTS_FILE):
            try:
                with open(PROJECTS_FILE, 'r') as f:
                    self.projects = json.load(f)
            except Exception as e:
                logger.error(f"Error loading projects file: {e}")
                self.projects = {}
    
    def _load_current_project(self) -> None:
        """Load the current project from the current project file."""
        if os.path.exists(CURRENT_PROJECT_FILE):
            try:
                with open(CURRENT_PROJECT_FILE, 'r') as f:
                    project_name = f.read().strip()
                    if project_name in self.projects:
                        self.current_project = project_name
            except Exception as e:
                logger.error(f"Error loading current project file: {e}")
    
    def _save_projects(self) -> None:
        """Save projects to the projects file."""
        try:
            with open(PROJECTS_FILE, 'w') as f:
                json.dump(self.projects, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving projects file: {e}")
    
    def _save_current_project(self) -> None:
        """Save the current project to the current project file."""
        if self.current_project:
            try:
                with open(CURRENT_PROJECT_FILE, 'w') as f:
                    f.write(self.current_project)
            except Exception as e:
                logger.error(f"Error saving current project file: {e}")
        elif os.path.exists(CURRENT_PROJECT_FILE):
            # Remove the file if there's no current project
            try:
                os.remove(CURRENT_PROJECT_FILE)
            except Exception as e:
                logger.error(f"Error removing current project file: {e}")
    
    def add_project(self, name: str, directory: str, config_path: Optional[str] = None) -> None:
        """
        Add a new project or update an existing one.
        
        Args:
            name: Project name
            directory: Project directory
            config_path: Path to custom config file (optional)
        """
        if not os.path.isdir(directory):
            raise ValueError(f"Directory does not exist: {directory}")
        
        if config_path and not os.path.isfile(config_path):
            raise ValueError(f"Config file does not exist: {config_path}")
        
        self.projects[name] = {
            "directory": os.path.abspath(directory),
            "config_path": os.path.abspath(config_path) if config_path else None,
            "index_name": name
        }
        
        self._save_projects()
    
    def remove_project(self, name: str) -> None:
        """
        Remove a project.
        
        Args:
            name: Project name
        """
        if name in self.projects:
            del self.projects[name]
            self._save_projects()
            
            # If the current project was removed, clear it
            if self.current_project == name:
                self.current_project = None
                self._save_current_project()
    
    def set_current_project(self, name: str) -> None:
        """
        Set the current project.
        
        Args:
            name: Project name
        """
        if name not in self.projects:
            raise ValueError(f"Project not found: {name}")
        
        self.current_project = name
        self._save_current_project()
        
        # Return project information for convenience
        return self.get_project(name)
    
    def get_project(self, name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get project information.
        
        Args:
            name: Project name (if None, use current project)
            
        Returns:
            Project information or None if not found
        """
        if name is None:
            name = self.current_project
        
        if not name or name not in self.projects:
            return None
        
        return self.projects[name]
    
    def get_current_project(self) -> Optional[Dict[str, Any]]:
        """
        Get current project information.
        
        Returns:
            Current project information or None if no current project
        """
        return self.get_project(self.current_project)
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """
        List all projects.
        
        Returns:
            List of projects with their information
        """
        result = []
        for name, info in self.projects.items():
            project_info = info.copy()
            project_info["name"] = name
            project_info["current"] = (name == self.current_project)
            result.append(project_info)
        
        return result


# Create a singleton instance
project_manager = ProjectManager()
