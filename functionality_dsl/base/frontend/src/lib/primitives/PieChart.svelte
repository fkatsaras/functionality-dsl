<script lang="ts">
    const {
        slices = [],
        title = "",
        size = 200,
        class: className = ""
    } = $props<{
        slices: Array<{ label: string; value: number; color: string }>;
        title?: string;
        size?: number;
        class?: string;
    }>();

    function calculateSlices(data: typeof slices) {
        const total = data.reduce((sum, slice) => sum + slice.value, 0);
        if (total === 0) return [];

        let currentAngle = -90; // Start at top
        return data.map((slice) => {
            const percentage = (slice.value / total) * 100;
            const angle = (slice.value / total) * 360;
            const startAngle = currentAngle;
            const endAngle = currentAngle + angle;

            // Calculate path for pie slice
            const startRad = (startAngle * Math.PI) / 180;
            const endRad = (endAngle * Math.PI) / 180;
            const radius = size / 2 - 10;
            const centerX = size / 2;
            const centerY = size / 2;

            const x1 = centerX + radius * Math.cos(startRad);
            const y1 = centerY + radius * Math.sin(startRad);
            const x2 = centerX + radius * Math.cos(endRad);
            const y2 = centerY + radius * Math.sin(endRad);

            const largeArcFlag = angle > 180 ? 1 : 0;

            const path = [
                `M ${centerX} ${centerY}`,
                `L ${x1} ${y1}`,
                `A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2}`,
                `Z`,
            ].join(" ");

            currentAngle = endAngle;

            return {
                ...slice,
                path,
                percentage: percentage.toFixed(1),
            };
        });
    }

    const processedSlices = $derived(calculateSlices(slices));
</script>

<div class={`pie-chart-container ${className}`}>
    {#if title}
        <h4 class="pie-title">{title}</h4>
    {/if}

    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} class="pie-svg">
        {#each processedSlices as slice}
            <path d={slice.path} fill={slice.color} stroke="var(--surface)" stroke-width="2" />
        {/each}
    </svg>

    <div class="legend">
        {#each processedSlices as slice}
            <div class="legend-item">
                <div class="legend-color" style={`background-color: ${slice.color}`}></div>
                <span class="legend-label">{slice.label}</span>
                <span class="legend-value">{slice.percentage}%</span>
            </div>
        {/each}
    </div>
</div>

<style>
    .pie-chart-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1rem;
    }

    .pie-title {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--text);
        margin: 0;
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            "Liberation Mono", "Courier New", monospace;
    }

    .pie-svg {
        filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.1));
    }

    .legend {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        width: 100%;
        max-width: 240px;
    }

    .legend-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.75rem;
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            "Liberation Mono", "Courier New", monospace;
    }

    .legend-color {
        width: 12px;
        height: 12px;
        border-radius: 2px;
        flex-shrink: 0;
    }

    .legend-label {
        flex: 1;
        color: var(--text-muted);
    }

    .legend-value {
        color: var(--text);
        font-weight: 500;
    }
</style>
