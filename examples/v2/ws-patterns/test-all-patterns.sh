#!/bin/bash
# =============================================================================
# WebSocket Patterns Testing Script
# Tests all 6 patterns automatically with generation, deployment, and wscat
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../../.."
CLEANUP_SCRIPT="$ROOT_DIR/scripts/docker_cleanup.sh"

# Find wscat - try multiple locations
if command -v wscat &> /dev/null; then
    WSCAT="wscat"
elif [ -f "$ROOT_DIR/venv_WSL/node_modules/.bin/wscat" ]; then
    WSCAT="$ROOT_DIR/venv_WSL/node_modules/.bin/wscat"
else
    WSCAT="wscat"  # Fallback to PATH
fi

# Patterns to test
PATTERNS=(
    "01-subscribe-simple"
    "02-subscribe-transformed"
    "03-publish-simple"
    "04-publish-transformed"
    "05-bidirectional-simple"
    "06-bidirectional-separate"
)

# Test configurations per pattern
declare -A PATTERN_TESTS=(
    ["01-subscribe-simple"]="subscribe:ws://localhost:8000/ws/messagefromexternal"
    ["02-subscribe-transformed"]="subscribe:ws://localhost:8000/ws/processedmessage"
    ["03-publish-simple"]="publish:ws://localhost:8000/ws/commandtoexternal:{\"command\":\"test\",\"value\":123}"
    ["04-publish-transformed"]="publish:ws://localhost:8000/ws/usercommand:{\"action\":\"test\",\"value\":5}"
    ["05-bidirectional-simple"]="bidirectional:ws://localhost:8000/ws/chatmessage:{\"text\":\"hello\",\"user\":\"tester\"}"
    ["06-bidirectional-separate"]="subscribe:ws://localhost:8000/ws/processedtelemetry"
)

# Results tracking
PASSED=0
FAILED=0
declare -a FAILED_PATTERNS

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up containers and generated files..."
    bash "$CLEANUP_SCRIPT" 2>/dev/null || true
    rm -rf "$SCRIPT_DIR"/generated-* 2>/dev/null || true
}

# Test subscribe pattern
test_subscribe() {
    local url=$1
    local pattern_name=$2

    log_info "Testing subscribe on $url"

    # Use timeout and capture output properly
    local output_file="/tmp/wscat_output_${pattern_name}.log"

    # Run wscat with timeout, capture both stdout and stderr
    timeout 5s $WSCAT -c "$url" 2>&1 | tee "$output_file" | head -n 10 &
    local wscat_pid=$!

    # Wait for wscat to run
    sleep 4

    # Kill if still running
    kill $wscat_pid 2>/dev/null || true
    wait $wscat_pid 2>/dev/null || true

    # Check if we received data (look for "<" which indicates received messages)
    if grep -q "^<" "$output_file" 2>/dev/null; then
        log_success "Received data from subscribe endpoint"
        grep "^<" "$output_file" | head -3
        return 0
    else
        log_error "No data received from subscribe endpoint"
        log_info "Output file contents:"
        cat "$output_file" 2>/dev/null || echo "(empty)"
        return 1
    fi
}

# Test publish pattern
test_publish() {
    local url=$1
    local message=$2
    local pattern_name=$3

    log_info "Testing publish on $url with message: $message"

    local output_file="/tmp/wscat_output_${pattern_name}.log"

    # Send message and capture response
    (sleep 1; echo "$message"; sleep 2) | timeout 5s $WSCAT -c "$url" 2>&1 | tee "$output_file" | head -n 10 &
    local wscat_pid=$!

    sleep 4

    # Kill wscat if still running
    kill $wscat_pid 2>/dev/null || true
    wait $wscat_pid 2>/dev/null || true

    # Check for connection success (wscat outputs "Connected" or message received with "<")
    if grep -qi "connected\|^<" "$output_file" 2>/dev/null; then
        log_success "Successfully published message"
        cat "$output_file" | head -5
        return 0
    else
        log_error "Failed to publish message"
        log_info "Output file contents:"
        cat "$output_file" 2>/dev/null || echo "(empty)"
        return 1
    fi
}

# Test bidirectional pattern
test_bidirectional() {
    local url=$1
    local message=$2
    local pattern_name=$3

    log_info "Testing bidirectional on $url"

    local output_file="/tmp/wscat_output_${pattern_name}.log"

    # Send message and wait for response
    (sleep 1; echo "$message"; sleep 3) | timeout 5s $WSCAT -c "$url" 2>&1 | tee "$output_file" | head -n 10 &
    local wscat_pid=$!

    sleep 4

    # Kill wscat
    kill $wscat_pid 2>/dev/null || true
    wait $wscat_pid 2>/dev/null || true

    # Check if we received data back (look for "connected" or received messages with "<")
    if grep -qi "connected\|^<" "$output_file" 2>/dev/null; then
        log_success "Bidirectional communication successful"
        cat "$output_file" | head -5
        return 0
    else
        log_error "Bidirectional communication failed"
        log_info "Output file contents:"
        cat "$output_file" 2>/dev/null || echo "(empty)"
        return 1
    fi
}

# Test a single pattern
test_pattern() {
    local pattern=$1
    local test_config="${PATTERN_TESTS[$pattern]}"

    echo ""
    echo "========================================================================="
    log_info "Testing pattern: $pattern"
    echo "========================================================================="

    # Parse test configuration
    local test_type=$(echo "$test_config" | cut -d: -f1)
    local ws_url=$(echo "$test_config" | cut -d: -f2-3)
    local message=$(echo "$test_config" | cut -d: -f4-)

    # Step 1: Generate code
    log_info "Step 1/4: Generating FDSL code..."
    cd "$SCRIPT_DIR"

    if make gen EXAMPLE="$pattern" OUTPUT="generated-$pattern" > /tmp/gen_${pattern}.log 2>&1; then
        log_success "Code generation successful"
    else
        log_error "Code generation failed"
        cat /tmp/gen_${pattern}.log | tail -20
        return 1
    fi

    # Step 2: Start generated FDSL service first (creates the Docker network)
    log_info "Step 2/4: Starting generated FDSL service..."
    cd "$SCRIPT_DIR/generated-$pattern"
    docker compose -p thesis up -d > /dev/null 2>&1
    sleep 10

    # Step 3: Start dummy WebSocket service
    log_info "Step 3/4: Starting dummy WebSocket service..."
    cd "$SCRIPT_DIR/dummy-service"
    docker compose -p thesis up -d > /dev/null 2>&1
    sleep 10

    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 5

    # Step 4: Test with wscat
    log_info "Step 4/4: Testing WebSocket endpoints..."

    local test_result=0

    case $test_type in
        "subscribe")
            test_subscribe "$ws_url" "$pattern" || test_result=1
            ;;
        "publish")
            test_publish "$ws_url" "$message" "$pattern" || test_result=1
            ;;
        "bidirectional")
            test_bidirectional "$ws_url" "$message" "$pattern" || test_result=1
            ;;
        *)
            log_error "Unknown test type: $test_type"
            test_result=1
            ;;
    esac

    # Cleanup logs
    rm -f /tmp/wscat_output_${pattern}.log /tmp/gen_${pattern}.log

    return $test_result
}

# Main test loop
main() {
    echo "========================================================================="
    echo "  WebSocket Patterns Testing Suite"
    echo "  Testing ${#PATTERNS[@]} patterns"
    echo "========================================================================="

    # Check prerequisites
    if [ ! -f "$CLEANUP_SCRIPT" ]; then
        log_error "Cleanup script not found: $CLEANUP_SCRIPT"
        exit 1
    fi

    if ! command -v $WSCAT &> /dev/null; then
        log_error "wscat not found in PATH"
        log_info "Install with: npm install -g wscat"
        log_info "Or use NVM: nvm install node && npm install -g wscat"
        exit 1
    fi

    log_info "Using wscat: $(which $WSCAT)"

    # Initial cleanup
    cleanup

    # Test each pattern
    for pattern in "${PATTERNS[@]}"; do
        if test_pattern "$pattern"; then
            log_success "Pattern $pattern PASSED"
            ((PASSED++))
        else
            log_error "Pattern $pattern FAILED"
            ((FAILED++))
            FAILED_PATTERNS+=("$pattern")

            # Stop on first failure
            log_error "Stopping test suite due to failure"
            break
        fi

        # Cleanup before next test
        log_info "Cleaning up before next test..."
        cleanup
        sleep 2
    done

    # Final summary
    echo ""
    echo "========================================================================="
    echo "  Test Summary"
    echo "========================================================================="
    log_info "Total patterns: ${#PATTERNS[@]}"
    log_success "Passed: $PASSED"

    if [ $FAILED -gt 0 ]; then
        log_error "Failed: $FAILED"
        echo ""
        log_error "Failed patterns:"
        for failed_pattern in "${FAILED_PATTERNS[@]}"; do
            echo "  - $failed_pattern"
        done
        echo ""
        exit 1
    else
        echo ""
        log_success "All patterns passed! ✓"
        echo ""
        exit 0
    fi
}

# Trap to ensure cleanup on exit
trap cleanup EXIT INT TERM

# Run main
main "$@"
