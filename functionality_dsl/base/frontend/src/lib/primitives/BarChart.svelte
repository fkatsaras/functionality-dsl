<script lang="ts">
    const {
        bars = [],
        title = "",
        xLabel = "",
        yLabel = "",
        height = 300,
        width = 500,
        class: className = ""
    } = $props<{
        bars: Array<{ label: string; value: number; color?: string }>;
        title?: string;
        xLabel?: string;
        yLabel?: string;
        height?: number;
        width?: number;
        class?: string;
    }>();

    const padding = { top: 40, right: 40, bottom: 80, left: 60 };
    const defaultColor = "var(--primary)";

    function calculateBars(data: typeof bars) {
        if (data.length === 0) return { bars: [], maxValue: 0, yTicks: [] };

        const maxValue = Math.max(...data.map((d) => d.value));
        const chartHeight = height - padding.top - padding.bottom;
        const chartWidth = width - padding.left - padding.right;
        const barWidth = chartWidth / data.length;
        const barPadding = barWidth * 0.2;
        const actualBarWidth = barWidth - barPadding;

        // Calculate y-axis ticks (5 ticks)
        const tickCount = 5;
        const tickInterval = maxValue / (tickCount - 1);
        const yTicks = Array.from({ length: tickCount }, (_, i) => ({
            value: Math.round(tickInterval * i),
            y: padding.top + chartHeight - (chartHeight * i) / (tickCount - 1),
        }));

        const processedBars = data.map((bar, i) => {
            const barHeight = (bar.value / maxValue) * chartHeight;
            const x = padding.left + i * barWidth + barPadding / 2;
            const y = padding.top + chartHeight - barHeight;

            return {
                ...bar,
                x,
                y,
                width: actualBarWidth,
                height: barHeight,
                color: bar.color || defaultColor,
                labelX: x + actualBarWidth / 2,
                labelY: padding.top + chartHeight + 20,
            };
        });

        return { bars: processedBars, maxValue, yTicks };
    }

    const result = $derived(calculateBars(bars));
    const processedBars = $derived(result.bars);
    const maxValue = $derived(result.maxValue);
    const yTicks = $derived(result.yTicks);
</script>

<div class={`bar-chart-container ${className}`}>
    {#if title}
        <h4 class="chart-title">{title}</h4>
    {/if}

    <svg {width} {height} viewBox={`0 0 ${width} ${height}`} class="bar-svg">
        <!-- Y-axis -->
        <line
            x1={padding.left}
            y1={padding.top}
            x2={padding.left}
            y2={height - padding.bottom}
            stroke="var(--edge)"
            stroke-width="2"
        />

        <!-- X-axis -->
        <line
            x1={padding.left}
            y1={height - padding.bottom}
            x2={width - padding.right}
            y2={height - padding.bottom}
            stroke="var(--edge)"
            stroke-width="2"
        />

        <!-- Y-axis ticks and labels -->
        {#each yTicks as tick}
            <line
                x1={padding.left - 5}
                y1={tick.y}
                x2={padding.left}
                y2={tick.y}
                stroke="var(--edge)"
                stroke-width="1"
            />
            <text
                x={padding.left - 10}
                y={tick.y}
                text-anchor="end"
                dominant-baseline="middle"
                class="axis-label"
            >
                {tick.value}
            </text>

            <!-- Grid line -->
            <line
                x1={padding.left}
                y1={tick.y}
                x2={width - padding.right}
                y2={tick.y}
                stroke="var(--edge)"
                stroke-width="0.5"
                opacity="0.2"
                stroke-dasharray="4 4"
            />
        {/each}

        <!-- Bars -->
        {#each processedBars as bar}
            <rect
                x={bar.x}
                y={bar.y}
                width={bar.width}
                height={bar.height}
                fill={bar.color}
                rx="2"
            />

            <!-- Bar value on top -->
            <text
                x={bar.labelX}
                y={bar.y - 5}
                text-anchor="middle"
                class="bar-value"
            >
                {bar.value}
            </text>

            <!-- Bar label on X-axis with wrapping -->
            {#if bar.label.length > 12}
                <!-- Split long labels into two lines -->
                {@const words = bar.label.split(' ')}
                {@const midpoint = Math.ceil(words.length / 2)}
                {@const line1 = words.slice(0, midpoint).join(' ')}
                {@const line2 = words.slice(midpoint).join(' ')}
                <text
                    x={bar.labelX}
                    y={bar.labelY}
                    text-anchor="middle"
                    class="bar-label"
                >
                    {line1}
                </text>
                <text
                    x={bar.labelX}
                    y={bar.labelY + 12}
                    text-anchor="middle"
                    class="bar-label"
                >
                    {line2}
                </text>
            {:else}
                <text
                    x={bar.labelX}
                    y={bar.labelY}
                    text-anchor="middle"
                    class="bar-label"
                >
                    {bar.label}
                </text>
            {/if}
        {/each}

        <!-- Y-axis label -->
        {#if yLabel}
            <text
                x={15}
                y={(padding.top + height - padding.bottom) / 2}
                text-anchor="middle"
                transform={`rotate(-90, 15, ${(padding.top + height - padding.bottom) / 2})`}
                class="axis-title"
            >
                {yLabel}
            </text>
        {/if}

        <!-- X-axis label -->
        {#if xLabel}
            <text
                x={(padding.left + width - padding.right) / 2}
                y={height - 10}
                text-anchor="middle"
                class="axis-title"
            >
                {xLabel}
            </text>
        {/if}
    </svg>
</div>

<style>
    .bar-chart-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.5rem;
    }

    .chart-title {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--text);
        margin: 0;
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            "Liberation Mono", "Courier New", monospace;
    }

    .bar-svg {
        overflow: visible;
    }

    .axis-label,
    .bar-value,
    .bar-label {
        font-size: 0.75rem;
        fill: var(--text-muted);
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            "Liberation Mono", "Courier New", monospace;
    }

    .bar-value {
        fill: var(--text);
        font-weight: 500;
    }

    .axis-title {
        font-size: 0.8rem;
        fill: var(--text);
        font-weight: 500;
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            "Liberation Mono", "Courier New", monospace;
    }
</style>
