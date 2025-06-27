#!/usr/bin/env python3
"""
Mite Time Tracking CLI Tool
A command-line interface for adding time entries to Mite.
"""

import argparse
import json
import os
import sys
from datetime import datetime
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv


class MiteClient:
    """Client for interacting with the Mite API."""
    
    def __init__(self, account: str, api_key: str):
        self.account = account
        self.api_key = api_key
        self.base_url = f"https://{account}.mite.de"
        self.headers = {
            "X-MiteApiKey": api_key,
            "Content-Type": "application/json",
            "User-Agent": "MiteCLI/1.0"
        }
    
    def create_time_entry(self, 
                         minutes: int,
                         note: str = "",
                         date: Optional[str] = None,
                         project_id: Optional[int] = None,
                         service_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a new time entry in Mite.
        
        Args:
            minutes: Duration in minutes
            note: Description of the work done
            date: Date in YYYY-MM-DD format (defaults to today)
            project_id: ID of the project
            service_id: ID of the service
            
        Returns:
            Dictionary containing the created time entry data
        """
        url = f"{self.base_url}/time_entries.json"
        
        # Build the request payload
        payload = {
            "time_entry": {
                "minutes": minutes,
                "note": note
            }
        }
        
        if date:
            payload["time_entry"]["date_at"] = date
        if project_id:
            payload["time_entry"]["project_id"] = project_id
        if service_id:
            payload["time_entry"]["service_id"] = service_id
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error creating time entry: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            sys.exit(1)
    
    def get_projects(self) -> list:
        """Get list of all projects."""
        url = f"{self.base_url}/projects.json"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching projects: {e}")
            return []
    
    def find_project_by_name(self, name: str) -> Optional[int]:
        """Find project ID by name (case-insensitive partial match)."""
        projects = self.get_projects()
        name_lower = name.lower()
        
        # First try exact match
        for project in projects:
            if project['project']['name'].lower() == name_lower:
                return project['project']['id']
        
        # Then try partial match
        for project in projects:
            if name_lower in project['project']['name'].lower():
                return project['project']['id']
        
        return None
    
    def get_services(self) -> list:
        """Get list of all services."""
        url = f"{self.base_url}/services.json"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching services: {e}")
            return []
    
    def find_service_by_name(self, name: str) -> Optional[int]:
        """Find service ID by name (case-insensitive partial match)."""
        services = self.get_services()
        name_lower = name.lower()
        
        # First try exact match
        for service in services:
            if service['service']['name'].lower() == name_lower:
                return service['service']['id']
        
        # Then try partial match
        for service in services:
            if name_lower in service['service']['name'].lower():
                return service['service']['id']
        
        return None


def load_config() -> Dict[str, str]:
    """Load configuration from .env file, environment variables, or config file."""
    # Load .env file if it exists
    load_dotenv()
    
    config = {}
    
    # Try to load from environment variables first (includes .env)
    config['account'] = os.environ.get('MITE_ACCOUNT')
    config['api_key'] = os.environ.get('MITE_API_KEY')
    
    # Try to load from config file if not in environment
    config_file = os.path.expanduser('~/.mite_config.json')
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                config['account'] = config.get('account') or file_config.get('account')
                config['api_key'] = config.get('api_key') or file_config.get('api_key')
        except Exception as e:
            print(f"Error loading config file: {e}")
    
    return config


def save_config(account: str, api_key: str):
    """Save configuration to file."""
    config_file = os.path.expanduser('~/.mite_config.json')
    config = {
        'account': account,
        'api_key': api_key
    }
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        os.chmod(config_file, 0o600)  # Secure the file
        print(f"Configuration saved to {config_file}")
    except Exception as e:
        print(f"Error saving config: {e}")


def parse_duration(duration_str: str) -> int:
    """
    Parse duration string to minutes.
    Supports formats: '1h30m', '90m', '1.5h', '90'
    """
    duration_str = duration_str.strip()
    
    # Direct minutes
    try:
        return int(duration_str)
    except ValueError:
        pass
    
    # Hours with decimal
    if duration_str.endswith('h'):
        try:
            hours = float(duration_str[:-1])
            return int(hours * 60)
        except ValueError:
            pass
    
    # Hours and minutes format
    total_minutes = 0
    if 'h' in duration_str:
        parts = duration_str.split('h')
        try:
            total_minutes += int(parts[0]) * 60
            duration_str = parts[1]
        except (ValueError, IndexError):
            raise ValueError(f"Invalid duration format: {duration_str}")
    
    if 'm' in duration_str:
        try:
            total_minutes += int(duration_str.replace('m', ''))
        except ValueError:
            raise ValueError(f"Invalid duration format: {duration_str}")
    elif duration_str:
        try:
            total_minutes += int(duration_str)
        except ValueError:
            raise ValueError(f"Invalid duration format: {duration_str}")
    
    return total_minutes


def main():
    parser = argparse.ArgumentParser(
        description='Mite Time Tracking CLI - Add time entries to your Mite account',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add 2 hours of work with a note
  mite add 2h "Worked on feature X"
  
  # Add 90 minutes for a specific date
  mite add 90m "Bug fixing" --date 2025-01-15
  
  # Configure your account
  mite config --account yourcompany --api-key your-api-key
  
  # List available projects and services
  mite list projects
  mite list services
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new time entry')
    add_parser.add_argument('duration', help='Duration (e.g., 2h, 90m, 1h30m, 90)')
    add_parser.add_argument('note', help='Description of work done')
    add_parser.add_argument('--date', help='Date in YYYY-MM-DD format (default: today)')
    add_parser.add_argument('--project', help='Project ID or name')
    add_parser.add_argument('--service', help='Service ID or name')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Configure Mite credentials')
    config_parser.add_argument('--account', required=True, help='Your Mite account subdomain')
    config_parser.add_argument('--api-key', required=True, help='Your Mite API key')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List projects or services')
    list_parser.add_argument('resource', choices=['projects', 'services'], 
                            help='Resource to list')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Handle config command
    if args.command == 'config':
        save_config(args.account, args.api_key)
        sys.exit(0)
    
    # Load configuration for other commands
    config = load_config()
    if not config.get('account') or not config.get('api_key'):
        print("Error: Mite credentials not configured.")
        print("Please use one of the following methods:")
        print("1. Create a .env file with MITE_ACCOUNT and MITE_API_KEY")
        print("2. Set environment variables: MITE_ACCOUNT and MITE_API_KEY")
        print("3. Run: mite config --account yourcompany --api-key your-api-key")
        sys.exit(1)
    
    client = MiteClient(config['account'], config['api_key'])
    
    # Handle list command
    if args.command == 'list':
        if args.resource == 'projects':
            projects = client.get_projects()
            if projects:
                print("Available Projects:")
                for project in projects:
                    print(f"  ID: {project['project']['id']} - {project['project']['name']}")
            else:
                print("No projects found.")
        elif args.resource == 'services':
            services = client.get_services()
            if services:
                print("Available Services:")
                for service in services:
                    print(f"  ID: {service['service']['id']} - {service['service']['name']}")
            else:
                print("No services found.")
    
    # Handle add command
    elif args.command == 'add':
        try:
            minutes = parse_duration(args.duration)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        
        # Validate date format if provided
        date = args.date
        if date:
            try:
                datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                print("Error: Date must be in YYYY-MM-DD format")
                sys.exit(1)
        
        # Handle project lookup
        project_id = None
        if args.project:
            try:
                # Try to parse as ID first
                project_id = int(args.project)
            except ValueError:
                # If not an ID, search by name
                project_id = client.find_project_by_name(args.project)
                if project_id is None:
                    print(f"Error: No project found matching '{args.project}'")
                    print("Available projects:")
                    projects = client.get_projects()
                    for p in projects[:10]:  # Show first 10
                        print(f"  - {p['project']['name']}")
                    if len(projects) > 10:
                        print(f"  ... and {len(projects) - 10} more")
                    sys.exit(1)
        
        # Handle service lookup
        service_id = None
        if args.service:
            try:
                # Try to parse as ID first
                service_id = int(args.service)
            except ValueError:
                # If not an ID, search by name
                service_id = client.find_service_by_name(args.service)
                if service_id is None:
                    print(f"Error: No service found matching '{args.service}'")
                    print("Available services:")
                    services = client.get_services()
                    for s in services[:10]:  # Show first 10
                        print(f"  - {s['service']['name']}")
                    if len(services) > 10:
                        print(f"  ... and {len(services) - 10} more")
                    sys.exit(1)
        
        # Create time entry
        result = client.create_time_entry(
            minutes=minutes,
            note=args.note,
            date=date,
            project_id=project_id,
            service_id=service_id
        )
        
        entry = result.get('time_entry', {})
        print(f"✓ Time entry created successfully!")
        print(f"  Date: {entry.get('date_at', 'N/A')}")
        print(f"  Duration: {entry.get('minutes', 0)} minutes")
        print(f"  Note: {entry.get('note', 'N/A')}")
        if entry.get('project_name'):
            print(f"  Project: {entry['project_name']}")
        if entry.get('service_name'):
            print(f"  Service: {entry['service_name']}")


if __name__ == '__main__':
    main()