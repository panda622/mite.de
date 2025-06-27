# Mite CLI Tool

A lightweight shell script for Mite time tracking using curl and jq.

## Requirements

- `curl` - for API requests
- `jq` - for JSON parsing

Install jq:
```bash
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq
```

## Installation

Just make the script executable:
```bash
chmod +x mite.sh
```

## Configuration

Configure your credentials using one of these methods:

**Option 1: Using .env file (recommended)**
```bash
cp .env.example .env
# Edit .env and add your API key
```

**Option 2: Using config command**
```bash
./mite.sh config
```

**Option 3: Environment variables**
```bash
export MITE_ACCOUNT=collumino
export MITE_API_KEY=your_api_key_here
```

Your API key can be found in your Mite account settings.

## Usage

### Add a time entry

```bash
# Add 2 hours of work
./mite.sh add 2h "Worked on feature implementation"

# Add 90 minutes
./mite.sh add 90m "Bug fixing"

# Add 1 hour 30 minutes
./mite.sh add 1h30m "Code review"

# Add time for a specific date
./mite.sh add 2h "Meeting" --date 2025-01-15

# Add time with project and service (by name or ID)
./mite.sh add 2h "Development" --project "My Project" --service "Programming"
```

### View timesheet

```bash
# View today's entries
./mite.sh timesheet

# View this week
./mite.sh timesheet --week

# View this month (with calendar view)
./mite.sh timesheet --month

# View last month
./mite.sh timesheet --last-month

# Filter by project
./mite.sh timesheet --month --project "My Project"
```

### List resources

```bash
# List all projects
./mite.sh list projects

# List all services
./mite.sh list services
```

## Features

- ✅ Add time entries with automatic project/service name lookup
- ✅ View timesheets with multiple date filters
- ✅ Monthly calendar view showing daily hours and off days
- ✅ Colored output for better readability
- ✅ No dependencies except curl and jq
- ✅ Lightweight and fast

## Duration Formats

The tool accepts various duration formats:
- `2h` - 2 hours
- `90m` - 90 minutes
- `1h30m` - 1 hour and 30 minutes
- `90` - 90 minutes (plain number is interpreted as minutes)
- `1.5h` - 1.5 hours

## Monthly Calendar View

When using `--month` or `--last-month`, you get a visual calendar:
- ✓ = 8+ hours (full day)
- ◐ = 6-8 hours (partial day)
- ○ = <6 hours (short day)
- ✗ OFF = Working day with no time entry

### Example Output

```
$ ./mite.sh timesheet --month

📅 January 2025
+------------+------------+------------+------------+------------+------------+------------+
|    Mon     |    Tue     |    Wed     |    Thu     |    Fri     |    Sat     |    Sun     |
+------------+------------+------------+------------+------------+------------+------------+
|            |            |  1 ✓ 8h    |  2 ✓ 8h    |  3 ✓ 8h    |  4         |  5         |
|  6 ✓ 8h    |  7 ◐ 6h    |  8 ✓ 8h    |  9 ✓ 8h    | 10 ✓ 8h    | 11         | 12         |
| 13 ✓ 8h    | 14 ✓ 8h    | 15 ✗ OFF   | 16 ✓ 8h    | 17 ○ 4h    | 18         | 19         |
| 20 ✓ 8h    | 21 ✓ 8h    | 22 ✓ 8h    | 23 ✓ 8h    | 24 ✓ 8h    | 25         | 26         |
| 27 ✓ 8h    | 28 ✓ 8h    | 29 ✓ 8h    | 30 ✓ 8h    | 31 ✓ 8h    |            |            |
+------------+------------+------------+------------+------------+------------+------------+

📊 Summary
─────────────────────────────────────
Total Time: 154h
Average per Day: 7h 42m
Days Worked: 20
Off Days: 1 days
Dates: 15/01
─────────────────────────────────────
```

## Security

Your API key can be stored in three ways:

1. **.env file** (recommended) - Store in project directory, add to `.gitignore`
2. **Environment variables** - Set in your shell profile
3. **Config file** - Stored in `~/.mite_config` with restricted permissions (600)

⚠️ **Important**: Never commit your `.env` file or API key to version control.
