#!/bin/bash
# Run Pipecat Voice Agent and auto-open browser

echo "🚀 Starting Pipecat Voice Agent..."
echo ""

# Flag to track if we've already opened the browser
URL_OPENED=false

# Run the agent and capture output
.venv/bin/python main.py --debug 2>&1 | while IFS= read -r line; do
    echo "$line"
    
    # Check if line contains the room URL AND we haven't opened it yet
    if [[ $line == *"https://"*".daily.co/"* ]] && [ "$URL_OPENED" = false ]; then
        # Extract URL (finds any URL in the line)
        url=$(echo "$line" | grep -oE 'https://[^ ]+\.daily\.co/[^ ]+' | head -1)
        if [ ! -z "$url" ]; then
            echo ""
            echo "🌐 Opening browser to: $url"
            echo ""
            open "$url"
            URL_OPENED=true  # Prevent opening again
        fi
    fi
done
