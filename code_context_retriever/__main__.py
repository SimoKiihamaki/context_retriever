import os
import sys
import argparse
import logging
from typing import List, Optional

from .config import Config
from .retrieval.retriever import CodeContextRetriever, EnhancedCodeRetriever
from .projects import project_manager

def main():
    """Main entry point for the command-line interface."""
    parser = argparse.ArgumentParser(description='Code Context Retriever')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Project commands
    project_parser = subparsers.add_parser('project', help='Project management commands')
    project_subparsers = project_parser.add_subparsers(dest='project_command', help='Project command to run')
    
    # Set project command
    set_project_parser = project_subparsers.add_parser('set', help='Set the current project')
    set_project_parser.add_argument('name', help='Project name')
    set_project_parser.add_argument('directory', nargs='?', help='Project directory (required for new projects)')
    set_project_parser.add_argument('--config', '-c', help='Path to custom configuration file')
    
    # List projects command
    list_projects_parser = project_subparsers.add_parser('list', help='List all projects')
    
    # Remove project command
    remove_project_parser = project_subparsers.add_parser('remove', help='Remove a project')
    remove_project_parser.add_argument('name', help='Project name')
    
    # Current project command
    current_project_parser = project_subparsers.add_parser('current', help='Show current project')
    
    # Index command
    index_parser = subparsers.add_parser('index', help='Index a codebase')
    index_parser.add_argument('root_dir', nargs='?', help='Root directory of the codebase (optional if project is set)')
    index_parser.add_argument('--config', '-c', help='Path to configuration file')
    index_parser.add_argument('--extensions', '-e', nargs='+', help='File extensions to index')
    index_parser.add_argument('--no-parallel', dest='parallel', action='store_false', 
                             help='Disable parallel processing')
    index_parser.add_argument('--no-save', dest='save', action='store_false',
                             help='Do not save the index after building')
    index_parser.add_argument('--project', '-p', help='Project name (uses current project if not specified)')
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Query the indexed codebase')
    query_parser.add_argument('query', help='Query string')
    query_parser.add_argument('--threshold', '-t', type=float, help='Minimum similarity score threshold (0.0 to 1.0)')
    query_parser.add_argument('--output', '-o', help='Output file path (default: context.txt)')
    query_parser.add_argument('--terminal', '-T', action='store_true', help='Also print full results to terminal')
    query_parser.add_argument('--config', '-c', help='Path to configuration file')
    query_parser.add_argument('--index', '-i', help='Name of the index to load')
    query_parser.add_argument('--project', '-p', help='Project name (uses current project if not specified)')
    
    # API command
    api_parser = subparsers.add_parser('api', help='Start the REST API server')
    api_parser.add_argument('--config', '-c', help='Path to configuration file')
    api_parser.add_argument('--host', default='0.0.0.0', help='Host to bind the server to')
    api_parser.add_argument('--port', '-p', type=int, default=8000, help='Port to bind the server to')
    api_parser.add_argument('--project', '-j', help='Project name (uses current project if not specified)')
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    try:
        # Handle project management commands
        if args.command == 'project':
            if args.project_command == 'set':
                if args.name not in project_manager.projects and not args.directory:
                    print(f"Error: Project '{args.name}' does not exist. To create a new project, specify a directory.")
                    return 1
                
                if args.directory:
                    project_manager.add_project(args.name, args.directory, args.config)
                
                project = project_manager.set_current_project(args.name)
                print(f"Current project set to '{args.name}' ({project['directory']})")
                return 0
                
            elif args.project_command == 'list':
                projects = project_manager.list_projects()
                if not projects:
                    print("No projects found.")
                    return 0
                
                print("Projects:")
                for project in projects:
                    current = " (current)" if project['current'] else ""
                    print(f"  {project['name']}{current}: {project['directory']}")
                return 0
                
            elif args.project_command == 'remove':
                if args.name not in project_manager.projects:
                    print(f"Error: Project '{args.name}' does not exist.")
                    return 1
                
                project_manager.remove_project(args.name)
                print(f"Project '{args.name}' removed.")
                return 0
                
            elif args.project_command == 'current':
                current = project_manager.get_current_project()
                if not current:
                    print("No current project set.")
                    return 0
                
                print(f"Current project: {project_manager.current_project}")
                print(f"  Directory: {current['directory']}")
                if current['config_path']:
                    print(f"  Config: {current['config_path']}")
                print(f"  Index name: {current['index_name']}")
                return 0
            
            else:
                project_parser.print_help()
                return 1
        
        # Use current project settings if applicable
        project_name = None
        if hasattr(args, 'project') and args.project:
            project_name = args.project
        
        project = None
        if project_name:
            project = project_manager.get_project(project_name)
            if not project:
                print(f"Error: Project '{project_name}' not found.")
                return 1
        elif project_manager.current_project:
            project = project_manager.get_current_project()
        
        # Handle other commands
        if args.command == 'index':
            # Determine root directory
            root_dir = args.root_dir
            if not root_dir and project:
                root_dir = project['directory']
            
            if not root_dir:
                print("Error: No root directory specified and no current project set.")
                return 1
            
            # Determine config path
            config_path = args.config
            if not config_path and project and project.get('config_path'):
                config_path = project['config_path']
            
            # Determine index name
            index_name = None
            if project:
                index_name = project['index_name']
            
            # Create retriever
            retriever = CodeContextRetriever(config_path)
            
            # Set index name if specified
            if index_name:
                retriever.config['index_name'] = index_name
            
            # Index the codebase
            retriever.index_codebase(
                root_dir, 
                extensions=args.extensions,
                parallel=args.parallel,
                save_index=args.save
            )
            print(f"Successfully indexed codebase at {root_dir}")
            
        elif args.command == 'query':
            # Determine config path
            config_path = args.config
            if not config_path and project and project.get('config_path'):
                config_path = project['config_path']
            
            # Initialize configuration
            config = Config(config_path).config
            
            # Set index name if specified in args
            if args.index:
                config['index_name'] = args.index
            # Or use project index name
            elif project and 'index_name' in project:
                config['index_name'] = project['index_name']
                
            # Create retriever
            retriever = CodeContextRetriever(config_path)
            
            # Set index name in retriever config
            if args.index or (project and 'index_name' in project):
                retriever.config['index_name'] = config['index_name']
            
            # Load index if needed
            if not retriever.retriever:
                index_name = retriever.config.get('index_name', 'default')
                if not retriever.vector_index.load(index_name):
                    print(f"Error: Could not load index '{index_name}'")
                    return 1
                retriever.retriever = EnhancedCodeRetriever(
                    retriever.vector_index, 
                    retriever.embedder,
                    retriever.config.get('retriever', {})
                )
                
            # Perform query
            results = retriever.query(args.query, threshold=args.threshold)
            
            # Create a string with the formatted results
            output_content = f"Results for query: {args.query}\n\n"
            for i, result in enumerate(results, 1):
                output_content += f"Result {i}:\n{result}\n\n"
            
            # Determine output file path
            output_file = args.output if args.output else "context.txt"
            
            # Write to the output file (overwriting any existing content)
            with open(output_file, "w") as file:
                file.write(output_content)
            
            # Print a message to the terminal
            print(f"Results for query: {args.query}")
            print(f"Found {len(results)} results. Saved to {output_file}")
            
            # If --terminal flag is used, also print full results to terminal
            if args.terminal:
                print("\nFull results:")
                for i, result in enumerate(results, 1):
                    print(f"Result {i}:\n{result}\n")
                
        elif args.command == 'api':
            # Determine config path
            config_path = args.config
            if not config_path and project and project.get('config_path'):
                config_path = project['config_path']
            
            try:
                from .api.server import start_server
                start_server(args.host, args.port, config_path)
            except ImportError:
                print("Error: API dependencies not installed. Run 'pip install code-context-retriever[api]'")
                return 1
                
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())