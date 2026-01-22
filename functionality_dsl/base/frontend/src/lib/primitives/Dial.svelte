<script lang="ts">
    const {
        value = 50,
        min = 0,
        max = 100,
        size = 180,
        mode = "cooling",
        onChange,
        onCommit,
        disabled = false,
    } = $props<{
        value: number;
        min?: number;
        max?: number;
        size?: number;
        mode?: "heating" | "cooling" | "off";
        onChange?: (value: number) => void;
        onCommit?: (value: number) => void;
        disabled?: boolean;
    }>();

    let isDragging = $state(false);
    let startY = $state(0);
    let startValue = $state(0);
    let currentValue = $state(value);
    let wrapperEl: HTMLDivElement;

    // Sync external value changes
    $effect(() => {
        if (!isDragging) {
            currentValue = value;
        }
    });

    // Calculate percentage for arc
    const percent = $derived((currentValue - min) / (max - min));

    // Arc geometry - 270 degree arc with gap at bottom
    // Start at bottom-left (135deg from top), sweep 270deg clockwise
    const radius = $derived((size / 2) - 12);
    const circumference = $derived(2 * Math.PI * radius);
    const arcLength = $derived(circumference * 0.75); // 270 degrees
    // For the active arc: offset from end (full offset = empty, 0 = full)
    const activeArcOffset = $derived(arcLength * (1 - percent));

    // Arc color based on mode
    const arcColor = $derived(
        mode === "heating" ? "var(--warning-text)" :
        mode === "cooling" ? "var(--accent)" :
        "var(--text-muted)"
    );

    function handlePointerDown(event: PointerEvent) {
        if (disabled) return;

        isDragging = true;
        startY = event.clientY;
        startValue = currentValue;

        // Capture pointer on the wrapper element
        wrapperEl.setPointerCapture(event.pointerId);
    }

    function handlePointerMove(event: PointerEvent) {
        if (!isDragging || disabled) return;

        const deltaY = startY - event.clientY; // Inverted: up = positive
        const sensitivity = (max - min) / 150; // pixels per unit
        const newValue = Math.round(Math.min(max, Math.max(min, startValue + deltaY * sensitivity)));

        if (newValue !== currentValue) {
            currentValue = newValue;
            onChange?.(newValue);
        }
    }

    function handlePointerUp(event: PointerEvent) {
        if (!isDragging) return;
        finishDrag();
    }

    function handleLostPointerCapture() {
        if (isDragging) {
            finishDrag();
        }
    }

    function finishDrag() {
        isDragging = false;
        if (currentValue !== value) {
            onCommit?.(currentValue);
        }
    }

    function handleKeyDown(event: KeyboardEvent) {
        if (disabled) return;

        let newValue = currentValue;

        switch (event.key) {
            case "ArrowUp":
            case "ArrowRight":
                newValue = Math.min(max, currentValue + 1);
                break;
            case "ArrowDown":
            case "ArrowLeft":
                newValue = Math.max(min, currentValue - 1);
                break;
            case "PageUp":
                newValue = Math.min(max, currentValue + 10);
                break;
            case "PageDown":
                newValue = Math.max(min, currentValue - 10);
                break;
            case "Home":
                newValue = min;
                break;
            case "End":
                newValue = max;
                break;
            default:
                return;
        }

        event.preventDefault();
        currentValue = newValue;
        onChange?.(newValue);
        onCommit?.(newValue);
    }
</script>

<div
    class="dial-container"
    class:disabled
    class:dragging={isDragging}
    style="width: {size}px;"
>
    <div
        class="dial-wrapper"
        bind:this={wrapperEl}
        style="width: {size}px; height: {size}px;"
        role="slider"
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={currentValue}
        tabindex={disabled ? -1 : 0}
        onpointerdown={handlePointerDown}
        onpointermove={handlePointerMove}
        onpointerup={handlePointerUp}
        onpointercancel={handlePointerUp}
        onlostpointercapture={handleLostPointerCapture}
        onkeydown={handleKeyDown}
    >
        <!-- SVG arcs -->
        <svg class="dial-svg" viewBox="0 0 {size} {size}">
            <!-- Track (background) - 270deg arc with gap at bottom -->
            <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke="var(--edge-soft)"
                stroke-width="6"
                stroke-linecap="round"
                stroke-dasharray="{arcLength} {circumference}"
                transform="rotate(135 {size / 2} {size / 2})"
            />

            <!-- Active arc - same start, fills based on percent -->
            <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke={arcColor}
                stroke-width="6"
                stroke-linecap="round"
                stroke-dasharray="{arcLength} {circumference}"
                stroke-dashoffset={activeArcOffset}
                transform="rotate(135 {size / 2} {size / 2})"
                class="active-arc"
            />
        </svg>

        <!-- Center knob - minimal circle -->
        <div class="knob"></div>
    </div>

    <!-- Value display below dial -->
    <div class="value-display">
        <slot name="value">
            <span class="value-text">{currentValue}</span>
        </slot>
    </div>
</div>

<style>
    .dial-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.75rem;
    }

    .dial-wrapper {
        position: relative;
        touch-action: none;
        cursor: grab;
        outline: none;
    }

    .dial-wrapper:focus-visible {
        outline: 2px solid var(--accent);
        outline-offset: 4px;
        border-radius: 50%;
    }

    .dial-container.dragging .dial-wrapper {
        cursor: grabbing;
    }

    .dial-container.disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .dial-svg {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
    }

    .active-arc {
        transition: stroke-dashoffset 0.1s ease-out;
    }

    .dial-container.dragging .active-arc {
        transition: none;
    }

    /* Center knob - minimal circle with border */
    .knob {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 65%;
        height: 65%;
        border-radius: 50%;
        background: var(--card);
        border: 2px solid var(--edge-soft);
    }

    .value-display {
        text-align: center;
    }

    .value-text {
        font-family: "Approach Mono", monospace;
        font-size: 1.5rem;
        font-weight: 500;
        color: var(--text);
        line-height: 1;
    }
</style>
