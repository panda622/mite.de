#!/bin/bash

# Mite CLI - Shell version using curl
# A lightweight command-line interface for Mite time tracking

set -e

# Configuration
CONFIG_FILE="$HOME/.mite_config"
ENV_FILE=".env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Load configuration
load_config() {
    # Try .env file first
    if [ -f "$ENV_FILE" ]; then
        export $(grep -v '^#' "$ENV_FILE" | xargs)
    fi
    
    # Override with config file if exists
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
    fi
    
    # Check if credentials are set
    if [ -z "$MITE_ACCOUNT" ] || [ -z "$MITE_API_KEY" ]; then
        echo -e "${RED}Error: Mite credentials not configured.${NC}"
        echo "Please use one of the following methods:"
        echo "1. Create a .env file with MITE_ACCOUNT and MITE_API_KEY"
        echo "2. Set environment variables: MITE_ACCOUNT and MITE_API_KEY"
        echo "3. Run: $0 config"
        exit 1
    fi
    
    BASE_URL="https://${MITE_ACCOUNT}.mite.de"
}

# Parse duration (2h, 90m, 1h30m, 90)
parse_duration() {
    local duration="$1"
    local minutes=0
    
    # Direct minutes
    if [[ "$duration" =~ ^[0-9]+$ ]]; then
        minutes=$duration
    # Decimal hours (1.5h)
    elif [[ "$duration" =~ ^([0-9]+\.?[0-9]*)h$ ]]; then
        local hours="${BASH_REMATCH[1]}"
        minutes=$(echo "$hours * 60" | bc | cut -d. -f1)
    # Hours and minutes (1h30m)
    elif [[ "$duration" =~ ^([0-9]+)h([0-9]+)m?$ ]]; then
        local hours="${BASH_REMATCH[1]}"
        local mins="${BASH_REMATCH[2]}"
        minutes=$((hours * 60 + mins))
    # Just hours (2h)
    elif [[ "$duration" =~ ^([0-9]+)h$ ]]; then
        local hours="${BASH_REMATCH[1]}"
        minutes=$((hours * 60))
    # Just minutes (90m)
    elif [[ "$duration" =~ ^([0-9]+)m$ ]]; then
        minutes="${BASH_REMATCH[1]}"
    else
        echo -e "${RED}Error: Invalid duration format: $duration${NC}"
        exit 1
    fi
    
    echo $minutes
}

# Format minutes to human readable
format_duration() {
    local minutes=$1
    local hours=$((minutes / 60))
    local mins=$((minutes % 60))
    
    if [ $hours -gt 0 ]; then
        if [ $mins -gt 0 ]; then
            echo "${hours}h ${mins}m"
        else
            echo "${hours}h"
        fi
    else
        echo "${mins}m"
    fi
}

# Make API request
api_request() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    
    local url="${BASE_URL}${endpoint}"
    local headers=(
        -H "X-MiteApiKey: $MITE_API_KEY"
        -H "Content-Type: application/json"
        -H "User-Agent: MiteCLI-Shell/1.0"
    )
    
    if [ -n "$data" ]; then
        curl -s -X "$method" "${headers[@]}" -d "$data" "$url"
    else
        curl -s -X "$method" "${headers[@]}" "$url"
    fi
}

# List projects
list_projects() {
    echo -e "${BOLD}Available Projects:${NC}"
    api_request GET "/projects.json" | jq -r '.[] | "  ID: \(.project.id) - \(.project.name)"'
}

# List services
list_services() {
    echo -e "${BOLD}Available Services:${NC}"
    api_request GET "/services.json" | jq -r '.[] | "  ID: \(.service.id) - \(.service.name)"'
}

# Find project by name
find_project_id() {
    local name="$1"
    local name_lower=$(echo "$name" | tr '[:upper:]' '[:lower:]')
    
    # Try exact match first
    local id=$(api_request GET "/projects.json" | jq -r --arg name "$name_lower" '.[] | select(.project.name | ascii_downcase == $name) | .project.id' | head -1)
    
    # If no exact match, try partial match
    if [ -z "$id" ]; then
        id=$(api_request GET "/projects.json" | jq -r --arg name "$name_lower" '.[] | select(.project.name | ascii_downcase | contains($name)) | .project.id' | head -1)
    fi
    
    echo "$id"
}

# Find service by name
find_service_id() {
    local name="$1"
    local name_lower=$(echo "$name" | tr '[:upper:]' '[:lower:]')
    
    # Try exact match first
    local id=$(api_request GET "/services.json" | jq -r --arg name "$name_lower" '.[] | select(.service.name | ascii_downcase == $name) | .service.id' | head -1)
    
    # If no exact match, try partial match
    if [ -z "$id" ]; then
        id=$(api_request GET "/services.json" | jq -r --arg name "$name_lower" '.[] | select(.service.name | ascii_downcase | contains($name)) | .service.id' | head -1)
    fi
    
    echo "$id"
}

# Add time entry
add_entry() {
    local duration="$1"
    local note="$2"
    local date="$3"
    local project="$4"
    local service="$5"
    
    local minutes=$(parse_duration "$duration")
    
    # Build JSON payload
    local json="{\"time_entry\": {\"minutes\": $minutes, \"note\": \"$note\""
    
    if [ -n "$date" ]; then
        json="$json, \"date_at\": \"$date\""
    fi
    
    # Handle project
    if [ -n "$project" ]; then
        if [[ "$project" =~ ^[0-9]+$ ]]; then
            json="$json, \"project_id\": $project"
        else
            local project_id=$(find_project_id "$project")
            if [ -z "$project_id" ]; then
                echo -e "${RED}Error: No project found matching '$project'${NC}"
                list_projects
                exit 1
            fi
            json="$json, \"project_id\": $project_id"
        fi
    fi
    
    # Handle service
    if [ -n "$service" ]; then
        if [[ "$service" =~ ^[0-9]+$ ]]; then
            json="$json, \"service_id\": $service"
        else
            local service_id=$(find_service_id "$service")
            if [ -z "$service_id" ]; then
                echo -e "${RED}Error: No service found matching '$service'${NC}"
                list_services
                exit 1
            fi
            json="$json, \"service_id\": $service_id"
        fi
    fi
    
    json="$json}}"
    
    # Create entry
    local response=$(api_request POST "/time_entries.json" "$json")
    
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        echo -e "${GREEN}✓ Time entry created successfully!${NC}"
        echo -e "  Date: $(echo "$response" | jq -r '.time_entry.date_at')"
        echo -e "  Duration: $(format_duration $minutes)"
        echo -e "  Note: $(echo "$response" | jq -r '.time_entry.note')"
        
        local project_name=$(echo "$response" | jq -r '.time_entry.project_name // empty')
        if [ -n "$project_name" ]; then
            echo -e "  Project: $project_name"
        fi
        
        local service_name=$(echo "$response" | jq -r '.time_entry.service_name // empty')
        if [ -n "$service_name" ]; then
            echo -e "  Service: $service_name"
        fi
    else
        echo -e "${RED}Error creating time entry${NC}"
        exit 1
    fi
}

# Display calendar for month - simplified version
display_calendar() {
    local entries="$1"
    local year="$2"
    local month="$3"
    local month_name="$4"
    
    echo -e "\n${BOLD}📅 $month_name $year${NC}"
    echo "+------------+------------+------------+------------+------------+------------+------------+"
    echo "|    Mon     |    Tue     |    Wed     |    Thu     |    Fri     |    Sat     |    Sun     |"
    echo "+------------+------------+------------+------------+------------+------------+------------+"
    
    # Get first day of month (0=Sunday, 1=Monday, etc)
    # BSD date (macOS) compatible
    local first_day=$(date -j -f "%Y-%m-%d" "$year-$month-01" +%w 2>/dev/null || date -d "$year-$month-01" +%w 2>/dev/null)
    # Adjust to Monday start (0=Monday)
    first_day=$(( (first_day + 6) % 7 ))

    # Days in month - use BSD date for macOS, GNU date for Linux
    local days_in_month
    if date -j -f "%Y-%m-%d" "$year-$month-01" +%d &>/dev/null; then
        # BSD date (macOS)
        days_in_month=$(date -j -v+1m -v-1d -f "%Y-%m-%d" "$year-$month-01" +%d)
    else
        # GNU date (Linux)
        days_in_month=$(date -d "$year-$month-01 +1 month -1 day" +%d)
    fi
    
    local day=1
    local off_days=""
    
    # Create calendar rows
    while [ $day -le $days_in_month ]; do
        local week=""
        for dow in {0..6}; do
            if [ $day -eq 1 ] && [ $dow -lt $first_day ]; then
                # Empty cell before month starts
                week="${week}|            "
            elif [ $day -le $days_in_month ]; then
                local date_str=$(printf "%04d-%02d-%02d" $year $month $day)
                
                # Check if we have data for this date (sum all entries for the date)
                local minutes=$(echo "$entries" | jq --arg date "$date_str" '[.[] | select(.time_entry.date_at == $date) | .time_entry.minutes] | add // empty' | grep -v "null")
                
                if [ -n "$minutes" ] && [ "$minutes" != "null" ]; then
                    local hours=$((minutes / 60))
                    local duration=$(format_duration $minutes)
                    local dur_short="${duration:0:5}"
                    
                    # Create cell content with padding
                    if [ $hours -ge 8 ]; then
                        week="${week}| $(printf "%2d" $day) ${GREEN}✓${NC} $(printf "%-5s" "$dur_short") "
                    elif [ $hours -ge 6 ]; then
                        week="${week}| $(printf "%2d" $day) ${YELLOW}◐${NC} $(printf "%-5s" "$dur_short") "
                    else
                        week="${week}| $(printf "%2d" $day) ${RED}○${NC} $(printf "%-5s" "$dur_short") "
                    fi
                else
                    # No entry for this date
                    local day_of_week=$(date -j -f "%Y-%m-%d" "$date_str" +%w 2>/dev/null || date -d "$date_str" +%w 2>/dev/null || echo 0)
                    if [ -n "$day_of_week" ] && [ "$day_of_week" -ge 1 ] && [ "$day_of_week" -le 5 ]; then
                        # Working day
                        if [[ "$date_str" < "$(date +%Y-%m-%d)" ]]; then
                            week="${week}| $(printf "%2d" $day) ${BOLD}${RED}✗ OFF${NC}   "
                            off_days="${off_days}${day}/${month} "
                        else
                            week="${week}| ${CYAN}$(printf "%2d" $day)${NC}         "
                        fi
                    else
                        # Weekend
                        week="${week}| ${CYAN}$(printf "%2d" $day)${NC}         "
                    fi
                fi
                ((day++))
            else
                # Empty cell after month ends
                week="${week}|            "
            fi
        done
        echo -e "${week}|"
    done
    
    echo "+------------+------------+------------+------------+------------+------------+------------+"
    
    # Summary
    local total_minutes=$(echo "$entries" | jq '[.[] | .time_entry.minutes] | add // 0')
    local days_worked=$(echo "$entries" | jq '[.[] | .time_entry.date_at] | unique | length // 0')
    
    echo -e "\n${BOLD}📊 Summary${NC}"
    echo "─────────────────────────────────────"
    if [ "$total_minutes" -gt 0 ] && [ "$days_worked" -gt 0 ]; then
        local avg_minutes=$((total_minutes / days_worked))
        echo -e "${BOLD}Total Time:${NC} $(format_duration $total_minutes)"
        echo -e "${BOLD}Average per Day:${NC} $(format_duration $avg_minutes)"
        echo -e "${BOLD}Days Worked:${NC} $days_worked"
        if [ -n "$off_days" ]; then
            local off_count=$(echo $off_days | wc -w)
            echo -e "${BOLD}${RED}Off Days:${NC} $off_count days"
            echo -e "${CYAN}Dates: ${off_days}${NC}"
        fi
    else
        echo "No time entries found"
    fi
    echo "─────────────────────────────────────"
}

# View timesheet
view_timesheet() {
    local filter="$1"
    local project_filter="$2"
    
    local params=""
    local title="Today"
    local is_monthly=false
    
    case "$filter" in
        "today")
            params="?at=today"
            title="Today"
            ;;
        "yesterday")
            params="?at=yesterday"
            title="Yesterday"
            ;;
        "week")
            params="?at=this_week"
            title="This Week"
            ;;
        "last-week")
            params="?at=last_week"
            title="Last Week"
            ;;
        "month")
            params="?at=this_month"
            title="This Month"
            is_monthly=true
            ;;
        "last-month")
            params="?at=last_month"
            title="Last Month"
            is_monthly=true
            ;;
    esac
    
    # Add project filter
    if [ -n "$project_filter" ]; then
        if [[ "$project_filter" =~ ^[0-9]+$ ]]; then
            params="${params}&project_id=$project_filter"
        else
            local project_id=$(find_project_id "$project_filter")
            if [ -n "$project_id" ]; then
                params="${params}&project_id=$project_id"
            fi
        fi
    fi
    
    local entries=$(api_request GET "/time_entries.json${params}&limit=100")
    
    # For monthly view, show calendar
    if [ "$is_monthly" = true ]; then
        # Get year and month from first entry or use current
        local first_date=$(echo "$entries" | jq -r '.[0].time_entry.date_at // empty')
        if [ -n "$first_date" ]; then
            # BSD date (macOS) compatible
            local year=$(date -j -f "%Y-%m-%d" "$first_date" +%Y 2>/dev/null || date -d "$first_date" +%Y 2>/dev/null)
            local month=$(date -j -f "%Y-%m-%d" "$first_date" +%m 2>/dev/null || date -d "$first_date" +%m 2>/dev/null)
            local month_name=$(date -j -f "%Y-%m-%d" "$first_date" +%B 2>/dev/null || date -d "$first_date" +%B 2>/dev/null)
        else
            local year=$(date +%Y)
            local month=$(date +%m)
            local month_name=$(date +%B)
        fi
        
        display_calendar "$entries" "$year" "$month" "$month_name"
    else
        # Regular list view
        echo -e "\n${BOLD}⏰ Timesheet - $title${NC}"
        echo "============================================"
        
        local total_minutes=0
        local current_date=""
        
        echo "$entries" | jq -r '.[] | .time_entry | "\(.date_at)|\(.minutes)|\(.project_name // "No project")|\(.service_name // "No service")|\(.note // "")"' | while IFS='|' read -r date minutes project service note; do
            if [ "$date" != "$current_date" ]; then
                if [ -n "$current_date" ]; then
                    echo ""
                fi
                echo -e "\n${CYAN}$date${NC}"
                current_date="$date"
            fi
            
            local duration=$(format_duration $minutes)
            echo -e "  ${GREEN}$duration${NC} - $project / $service"
            if [ -n "$note" ]; then
                echo -e "    ${note:0:60}..."
            fi
        done
        
        # Summary
        total_minutes=$(echo "$entries" | jq '[.[] | .time_entry.minutes] | add // 0')
        if [ "$total_minutes" -gt 0 ]; then
            echo -e "\n============================================"
            echo -e "${BOLD}Total: $(format_duration $total_minutes)${NC}"
        fi
    fi
}

# Configure credentials
configure() {
    echo "Configure Mite credentials"
    read -p "Account (subdomain): " account
    read -p "API Key: " api_key
    
    cat > "$CONFIG_FILE" << EOF
MITE_ACCOUNT="$account"
MITE_API_KEY="$api_key"
EOF
    
    chmod 600 "$CONFIG_FILE"
    echo -e "${GREEN}Configuration saved to $CONFIG_FILE${NC}"
}

# Show usage
usage() {
    cat << EOF
Mite CLI - Shell version

Usage: $0 <command> [options]

Commands:
  add <duration> <note> [options]  Add a time entry
    Options:
      --date YYYY-MM-DD            Specific date (default: today)
      --project "name or ID"       Project name or ID
      --service "name or ID"       Service name or ID
    
    Examples:
      $0 add 2h "Worked on feature X"
      $0 add 90m "Bug fixing" --date 2025-01-15
      $0 add 2h "Development" --project "My Project" --service "Programming"
  
  timesheet [filter] [options]     View time entries
    Filters:
      --today                      Today's entries (default)
      --yesterday                  Yesterday's entries
      --week                       This week
      --last-week                  Last week
      --month                      This month
      --last-month                 Last month
      --project "name or ID"       Filter by project
    
    Examples:
      $0 timesheet
      $0 timesheet --week
      $0 timesheet --month --project "My Project"
  
  list <resource>                  List resources
    Resources:
      projects                     List all projects
      services                     List all services
  
  config                           Configure credentials

EOF
}

# Check dependencies
check_dependencies() {
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}Error: jq is required but not installed.${NC}"
        echo "Install it with: sudo apt-get install jq (Ubuntu/Debian) or brew install jq (macOS)"
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}Error: curl is required but not installed.${NC}"
        exit 1
    fi
}

# Main
main() {
    check_dependencies
    
    case "$1" in
        "config")
            configure
            ;;
        "add")
            load_config
            shift
            duration="$1"
            note="$2"
            shift 2
            
            date=""
            project=""
            service=""
            
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --date)
                        date="$2"
                        shift 2
                        ;;
                    --project)
                        project="$2"
                        shift 2
                        ;;
                    --service)
                        service="$2"
                        shift 2
                        ;;
                    *)
                        echo "Unknown option: $1"
                        usage
                        exit 1
                        ;;
                esac
            done
            
            add_entry "$duration" "$note" "$date" "$project" "$service"
            ;;
        "timesheet")
            load_config
            shift
            
            filter="today"
            project=""
            
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --today)
                        filter="today"
                        shift
                        ;;
                    --yesterday)
                        filter="yesterday"
                        shift
                        ;;
                    --week)
                        filter="week"
                        shift
                        ;;
                    --last-week)
                        filter="last-week"
                        shift
                        ;;
                    --month)
                        filter="month"
                        shift
                        ;;
                    --last-month)
                        filter="last-month"
                        shift
                        ;;
                    --project)
                        project="$2"
                        shift 2
                        ;;
                    *)
                        echo "Unknown option: $1"
                        usage
                        exit 1
                        ;;
                esac
            done
            
            view_timesheet "$filter" "$project"
            ;;
        "list")
            load_config
            case "$2" in
                "projects")
                    list_projects
                    ;;
                "services")
                    list_services
                    ;;
                *)
                    echo "Unknown resource: $2"
                    usage
                    exit 1
                    ;;
            esac
            ;;
        *)
            usage
            exit 0
            ;;
    esac
}

main "$@"