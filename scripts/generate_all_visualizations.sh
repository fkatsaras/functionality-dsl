#!/bin/bash
# Generate model visualizations for all examples

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$PROJECT_ROOT/docs/visualizations"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo "Generating visualizations for all examples"
echo "=========================================="
echo ""

# Counter for statistics
total=0
success=0
failed=0

# Find all main.fdsl files and generate visualizations
for fdsl_file in $(find "$PROJECT_ROOT/examples" -name "main.fdsl" -type f | sort); do
    total=$((total + 1))

    # Get the example name from the path
    example_dir=$(dirname "$fdsl_file")
    example_name=$(basename "$example_dir")

    echo "[$total] Processing: $example_name"
    echo "    File: $fdsl_file"

    # Generate the visualization (suppress output)
    ./venv_WIN/Scripts/fdsl.exe visualize-model "$fdsl_file" -o "$OUTPUT_DIR" > /dev/null 2>&1

    # Convert DOT to PNG using WSL GraphViz
    dot_file="$OUTPUT_DIR/main_diagram.dot"
    png_file="$OUTPUT_DIR/${example_name}_diagram.png"

    if [ -f "$dot_file" ]; then
        if wsl bash -c "cd /mnt/c/ffile/functionality-dsl && dot -Tpng docs/visualizations/main_diagram.dot -o docs/visualizations/${example_name}_diagram.png 2>&1" > /dev/null 2>&1; then
            # Cleanup DOT files
            rm -f "$OUTPUT_DIR/main_diagram.dot" "$OUTPUT_DIR/main_diagram"
            success=$((success + 1))
            echo "    OK Generated: ${example_name}_diagram.png"
        else
            failed=$((failed + 1))
            echo "    X Failed to convert DOT to PNG"
        fi
    else
        failed=$((failed + 1))
        echo "    X Failed to generate DOT file"
    fi

    echo ""
done

echo "=========================================="
echo "Summary:"
echo "  Total examples: $total"
echo "  Successful:     $success"
echo "  Failed:         $failed"
echo "=========================================="
echo ""
echo "Visualizations saved to: $OUTPUT_DIR"
