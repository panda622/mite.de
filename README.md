# Mite CLI Tool

A command-line interface for adding time entries to your Mite account (collumino.mite.de).

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your Mite credentials using one of these methods:

   **Option 1: Using .env file (recommended)**
   ```bash
   cp .env.example .env
   # Edit .env and add your API key
   ```

   **Option 2: Using environment variables**
   ```bash
   export MITE_ACCOUNT=collumino
   export MITE_API_KEY=your_api_key_here
   ```

   **Option 3: Using config command**
   ```bash
   ./mite_cli.py config --account collumino --api-key YOUR_API_KEY
   ```

Your API key can be found in your Mite account settings.

## Usage

### Add a time entry

```bash
# Add 2 hours of work
./mite_cli.py add 2h "Worked on feature implementation"

# Add 90 minutes
./mite_cli.py add 90m "Bug fixing"

# Add 1 hour 30 minutes
./mite_cli.py add 1h30m "Code review"

# Add time for a specific date
./mite_cli.py add 2h "Meeting" --date 2025-01-15

# Add time with project and service IDs
./mite_cli.py add 2h "Development" --project 123 --service 456

# Add time with project and service names
./mite_cli.py add 2h "Development" --project "My Project" --service "Programming"
```

### List projects and services

```bash
# List all available projects
./mite_cli.py list projects

# List all available services
./mite_cli.py list services
```

### View timesheet

```bash
# View today's time entries
./mite_cli.py timesheet

# View this week's entries
./mite_cli.py timesheet --week

# View last week's entries
./mite_cli.py timesheet --last-week

# View specific date range
./mite_cli.py timesheet --from 2025-01-01 --to 2025-01-15

# Filter by project
./mite_cli.py timesheet --week --project "Your Project"

# Other options
./mite_cli.py timesheet --yesterday
./mite_cli.py timesheet --month
./mite_cli.py timesheet --last-month
```

## Configuration

The tool supports multiple configuration methods (in order of priority):

1. **.env file** - Create a `.env` file in the project directory
2. **Environment variables** - Set MITE_ACCOUNT and MITE_API_KEY
3. **Config file** - Stored in `~/.mite_config.json`

## Project and Service Names

You can use either IDs or partial names when specifying projects and services:
- The tool will first try exact name matches (case-insensitive)
- If no exact match, it will search for partial matches
- If multiple matches exist, it will use the first one found

## Duration Formats

The tool accepts various duration formats:
- `2h` - 2 hours
- `90m` - 90 minutes
- `1h30m` - 1 hour and 30 minutes
- `90` - 90 minutes (plain number is interpreted as minutes)
- `1.5h` - 1.5 hours

## Security

Your API key can be stored in three ways:

1. **.env file** (recommended) - Store in project directory, add to `.gitignore`
2. **Environment variables** - Set in your shell profile
3. **Config file** - Stored in `~/.mite_config.json` with restricted permissions (600)

⚠️ **Important**: Never commit your `.env` file or API key to version control. Add `.env` to your `.gitignore` file.
