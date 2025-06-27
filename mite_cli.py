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
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from datetime import date, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
import calendar
from collections import defaultdict


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
    
    def get_time_entries(self, 
                        from_date: Optional[str] = None,
                        to_date: Optional[str] = None,
                        at: Optional[str] = None,
                        user_id: Optional[int] = None,
                        project_id: Optional[int] = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get time entries with optional filters.
        
        Args:
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format
            at: Date filter like 'today', 'yesterday', 'this_week', 'last_week'
            user_id: Filter by user ID
            project_id: Filter by project ID
            limit: Maximum number of entries to return
            
        Returns:
            List of time entry dictionaries
        """
        url = f"{self.base_url}/time_entries.json"
        params = {'limit': limit}
        
        if from_date:
            params['from'] = from_date
        if to_date:
            params['to'] = to_date
        if at:
            params['at'] = at
        if user_id:
            params['user_id'] = user_id
        if project_id:
            params['project_id'] = project_id
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching time entries: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            return []
    
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


def format_duration(minutes: int) -> str:
    """Format minutes to human-readable duration."""
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
    return f"{mins}m"


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
  
  # View timesheet
  mite timesheet              # Today's entries
  mite timesheet --week       # This week
  mite timesheet --last-week  # Last week
  mite timesheet --from 2025-01-01 --to 2025-01-15
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
    
    # Timesheet command
    timesheet_parser = subparsers.add_parser('timesheet', help='View time entries')
    timesheet_parser.add_argument('--today', action='store_true', help='Show today\'s entries (default)')
    timesheet_parser.add_argument('--yesterday', action='store_true', help='Show yesterday\'s entries')
    timesheet_parser.add_argument('--week', action='store_true', help='Show this week\'s entries')
    timesheet_parser.add_argument('--last-week', action='store_true', help='Show last week\'s entries')
    timesheet_parser.add_argument('--month', action='store_true', help='Show this month\'s entries')
    timesheet_parser.add_argument('--last-month', action='store_true', help='Show last month\'s entries')
    timesheet_parser.add_argument('--from', dest='from_date', help='Start date (YYYY-MM-DD)')
    timesheet_parser.add_argument('--to', dest='to_date', help='End date (YYYY-MM-DD)')
    timesheet_parser.add_argument('--project', help='Filter by project name or ID')
    timesheet_parser.add_argument('--limit', type=int, default=100, help='Maximum entries to show')
    
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
    
    # Handle timesheet command
    elif args.command == 'timesheet':
        console = Console()
        
        # Determine date filter
        at_filter = None
        from_date = None
        to_date = None
        period_title = "Today"
        
        if args.from_date and args.to_date:
            from_date = args.from_date
            to_date = args.to_date
            # Validate date formats
            try:
                datetime.strptime(from_date, '%Y-%m-%d')
                datetime.strptime(to_date, '%Y-%m-%d')
            except ValueError:
                console.print("[red]Error: Dates must be in YYYY-MM-DD format[/red]")
                sys.exit(1)
            period_title = f"{from_date} to {to_date}"
        elif args.yesterday:
            at_filter = 'yesterday'
            period_title = "Yesterday"
        elif args.week:
            at_filter = 'this_week'
            period_title = "This Week"
        elif args.last_week:
            at_filter = 'last_week'
            period_title = "Last Week"
        elif args.month:
            at_filter = 'this_month'
            period_title = "This Month"
        elif args.last_month:
            at_filter = 'last_month'
            period_title = "Last Month"
        else:
            # Default to today
            at_filter = 'today'
            period_title = "Today"
        
        # Handle project filter
        project_id = None
        if args.project:
            try:
                project_id = int(args.project)
            except ValueError:
                project_id = client.find_project_by_name(args.project)
                if project_id is None:
                    console.print(f"[red]Error: No project found matching '{args.project}'[/red]")
                    sys.exit(1)
        
        # Fetch time entries
        entries = client.get_time_entries(
            from_date=from_date,
            to_date=to_date,
            at=at_filter,
            project_id=project_id,
            limit=args.limit
        )
        
        if not entries:
            console.print("[yellow]No time entries found.[/yellow]")
            sys.exit(0)
        
        # Process entries
        total_minutes = 0
        daily_totals = {}
        entries_by_date = defaultdict(list)
        project_totals = defaultdict(int)
        service_totals = defaultdict(int)
        
        for entry_data in entries:
            entry = entry_data.get('time_entry', {})
            date_str = entry.get('date_at', 'N/A')
            minutes = entry.get('minutes', 0)
            note = entry.get('note', 'No description')
            project = entry.get('project_name', 'No project')
            service = entry.get('service_name', 'No service')
            
            total_minutes += minutes
            daily_totals[date_str] = daily_totals.get(date_str, 0) + minutes
            project_totals[project] += minutes
            service_totals[service] += minutes
            
            entries_by_date[date_str].append({
                'minutes': minutes,
                'note': note,
                'project': project,
                'service': service
            })
        
        # Display based on period type
        if at_filter in ['this_month', 'last_month'] or (from_date and to_date and 
            (datetime.strptime(to_date, '%Y-%m-%d') - datetime.strptime(from_date, '%Y-%m-%d')).days > 20):
            # Monthly calendar view
            display_monthly_calendar(console, entries_by_date, daily_totals, period_title)
        else:
            # Detailed table view
            display_timesheet_table(console, entries_by_date, period_title)
        
        # Summary statistics
        display_summary_stats(console, total_minutes, daily_totals, project_totals, service_totals)


def find_off_days(daily_totals):
    """Find working days (Mon-Fri) that have no time entries."""
    if not daily_totals:
        return []
    
    # Get date range from entries
    dates = [datetime.strptime(d, '%Y-%m-%d') for d in daily_totals.keys()]
    start_date = min(dates)
    end_date = max(dates)
    
    # Don't go beyond today
    today = datetime.now().date()
    if end_date.date() > today:
        end_date = datetime.combine(today, datetime.min.time())
    
    off_days = []
    current = start_date
    
    while current <= end_date:
        # Check if it's a working day (Monday=0, Friday=4)
        if current.weekday() < 5:  # Monday to Friday
            date_str = current.strftime('%Y-%m-%d')
            if date_str not in daily_totals:
                off_days.append(current)
        current += timedelta(days=1)
    
    return off_days


def display_monthly_calendar(console, entries_by_date, daily_totals, period_title):
    """Display entries in a monthly calendar format."""
    if not daily_totals:
        return
    
    # Get the month and year from the first entry
    first_date = min(daily_totals.keys())
    date_obj = datetime.strptime(first_date, '%Y-%m-%d')
    year = date_obj.year
    month = date_obj.month
    
    # Create calendar
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    # Create table
    table = Table(title=f"📅 {month_name} {year} - {period_title}", box=box.ROUNDED)
    table.add_column("Mon", justify="center", style="cyan", width=10)
    table.add_column("Tue", justify="center", style="cyan", width=10)
    table.add_column("Wed", justify="center", style="cyan", width=10)
    table.add_column("Thu", justify="center", style="cyan", width=10)
    table.add_column("Fri", justify="center", style="cyan", width=10)
    table.add_column("Sat", justify="center", style="dim", width=10)
    table.add_column("Sun", justify="center", style="dim", width=10)
    
    # Fill calendar
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append("")
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                if date_str in daily_totals:
                    minutes = daily_totals[date_str]
                    hours = minutes / 60
                    # Color code based on hours
                    if hours >= 8:
                        icon = "✓"
                        color = "green"
                    elif hours >= 6:
                        icon = "◐"
                        color = "yellow"
                    else:
                        icon = "○"
                        color = "red"
                    
                    cell_text = f"[bold]{day:2d}[/bold] [{color}]{icon} {format_duration(minutes)}[/{color}]"
                    row.append(cell_text)
                else:
                    # Check if this is a working day (Mon-Fri)
                    day_of_week = datetime(year, month, day).weekday()
                    if day_of_week < 5:  # Monday to Friday
                        # Check if date is in the future
                        if datetime(year, month, day).date() > datetime.now().date():
                            row.append(f"[dim]{day:2d}[/dim]")
                        else:
                            # This is a past working day with no entry - mark as off day
                            row.append(f"[bold]{day:2d}[/bold] [bold red]✗ OFF[/bold red]")
                    else:
                        # Weekend
                        row.append(f"[dim]{day:2d}[/dim]")
        table.add_row(*row)
    
    console.print(table)
    
    # Print legend
    legend = Text()
    legend.append("\nLegend: ", style="bold")
    legend.append("✓ 8h+ ", style="green")
    legend.append("◐ 6-8h ", style="yellow")
    legend.append("○ <6h ", style="red")
    legend.append("✗ OFF ", style="bold red")
    console.print(legend)


def display_timesheet_table(console, entries_by_date, period_title):
    """Display entries in a detailed table format."""
    table = Table(title=f"⏰ Timesheet - {period_title}", box=box.ROUNDED)
    table.add_column("Date", style="cyan", width=12)
    table.add_column("Duration", justify="right", style="magenta", width=10)
    table.add_column("Project", style="blue", width=25)
    table.add_column("Service", style="green", width=20)
    table.add_column("Note", style="white", width=40)
    
    for date_str in sorted(entries_by_date.keys()):
        for i, entry in enumerate(entries_by_date[date_str]):
            # Only show date for first entry of the day
            date_display = date_str if i == 0 else ""
            table.add_row(
                date_display,
                format_duration(entry['minutes']),
                entry['project'],
                entry['service'],
                entry['note'][:40] + "..." if len(entry['note']) > 40 else entry['note']
            )
        # Add daily total
        daily_total = sum(e['minutes'] for e in entries_by_date[date_str])
        table.add_row(
            "",
            f"[bold]{format_duration(daily_total)}[/bold]",
            "[dim]Daily Total[/dim]",
            "",
            "",
            end_section=True
        )
    
    console.print(table)


def display_summary_stats(console, total_minutes, daily_totals, project_totals, service_totals):
    """Display summary statistics."""
    # Create summary panel
    summary_lines = []
    
    # Total time
    summary_lines.append(f"[bold cyan]Total Time:[/bold cyan] {format_duration(total_minutes)}")
    
    # Average per day
    if daily_totals:
        avg_minutes = total_minutes / len(daily_totals)
        summary_lines.append(f"[bold cyan]Average per Day:[/bold cyan] {format_duration(int(avg_minutes))}")
        summary_lines.append(f"[bold cyan]Days Worked:[/bold cyan] {len(daily_totals)}")
        
        # Calculate off days (working days with no entries)
        off_days = find_off_days(daily_totals)
        if off_days:
            summary_lines.append(f"[bold red]Off Days:[/bold red] {len(off_days)} days")
            # Show specific dates
            off_dates_str = ", ".join([d.strftime("%d/%m") for d in sorted(off_days)])
            summary_lines.append(f"[dim]Dates: {off_dates_str}[/dim]")
    
    console.print(Panel("\n".join(summary_lines), title="📊 Summary", box=box.ROUNDED, width=76))
    
    # Project breakdown
    if len(project_totals) > 1:
        project_table = Table(title="🏢 Time by Project", box=box.SIMPLE, width=76)
        project_table.add_column("Project", style="blue", width=40)
        project_table.add_column("Time", justify="right", style="magenta", width=15)
        project_table.add_column("Percentage", justify="right", style="yellow", width=15)
        
        for project, minutes in sorted(project_totals.items(), key=lambda x: x[1], reverse=True):
            percentage = (minutes / total_minutes) * 100
            project_table.add_row(
                project,
                format_duration(minutes),
                f"{percentage:.1f}%"
            )
        
        console.print(project_table)
    
    # Service breakdown
    if len(service_totals) > 1:
        service_table = Table(title="🛠️  Time by Service", box=box.SIMPLE, width=76)
        service_table.add_column("Service", style="green", width=40)
        service_table.add_column("Time", justify="right", style="magenta", width=15)
        service_table.add_column("Percentage", justify="right", style="yellow", width=15)
        
        for service, minutes in sorted(service_totals.items(), key=lambda x: x[1], reverse=True):
            percentage = (minutes / total_minutes) * 100
            service_table.add_row(
                service,
                format_duration(minutes),
                f"{percentage:.1f}%"
            )
        
        console.print(service_table)


if __name__ == '__main__':
    main()