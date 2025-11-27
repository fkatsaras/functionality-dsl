<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { spring } from "svelte/motion";

    import Card from "$lib/primitives/Card.svelte";
    import LiveIndicator from "$lib/primitives/LiveIndicator.svelte";
    import { subscribe } from "$lib/ws";
    import { extractValue, clamp } from "$lib/utils/gaugeData";

    const {
        wsPath = null,
        valueKey = "value",
        min = 0,
        max = 100,
        name = "Gauge",
        unit = "",
        label = "",
        initial = 0,
        height = 200
    } = $props();

    // connection + error state
    let connected = $state(false);
    let error = $state<string | null>(null);

    // numeric coercions
    const minN = $derived(Number(min) || 0);
    const maxN = $derived(Number(max) || 100);

    // initial clamped value
    const initialN = clamp(Number(initial) || 0, minN, maxN);

    // reactive numeric needle value
    let value = $state(initialN);

    // spring animation
    const valueSpring = spring(initialN, {
        stiffness: 0.4,
        damping: 0.07,
        precision: 0.0001
    });

    //analog vibration
    let jitterTimer: number = 0;
    let lastTarget = initialN;

    function animateTo(next: number) {
        lastTarget = next;
        
        // trigger the main spring wiggle
        valueSpring.set(next);
    }


    // feed spring back into rune state
    $effect.pre(() => {
        valueSpring.subscribe(v => {
            value = v;

            if (jitterTimer != 0 ) clearTimeout(jitterTimer);

            const remaining = Math.abs(v - lastTarget);

            if (remaining < 0.1) {
                jitterTimer = setTimeout(() => {
                    const microJitter = (Math.random() - 0.5) * 0.24;

                    valueSpring.set(lastTarget + microJitter);
                }, 30);
            }
        });
    });

    // -----------------------
    // Arc geometry and length
    // -----------------------
    const ARC_PATH_D = "M -90 0 A 90 90 0 0 1 90 0";
    let arcLengthRaw = $state(1);

    const pct = $derived(
        maxN <= minN ? 0 :
        Math.min(1, Math.max(0, (value - minN) / (maxN - minN)))
    );

    const ARC_LEN = $derived(arcLengthRaw);

    const derivedDash = $derived(`${ARC_LEN * pct} ${ARC_LEN}`);

    const derivedAngle = $derived(-90 + pct * 180);

    const derivedArcColor = $derived(
      pct >= 0.9 ? "var(--red-text)" :
      pct >= 0.6 ? "var(--warning)" :
      "var(--accent)"
    );

    onMount(() => {
        // measure SVG arc length at runtime
        const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
        p.setAttribute("d", ARC_PATH_D);
        arcLengthRaw = p.getTotalLength();


        if (!wsPath) {
            error = "No wsPath provided";
            return;
        }

        unsub = subscribe(wsPath, (msg: any) => {
            if (msg?.__meta === "open") { connected = true; return; }
            if (msg?.__meta === "close") { connected = false; return; }

            connected = true;

            try {
                const num = extractValue(msg, valueKey);
                if (num == null) return;

                const next = clamp(Number(num), minN, maxN);

                if (Number.isFinite(next))
                    animateTo(next);

            } catch (e: any) {
                error = e?.message ?? "Parse error";
            }
        });
    });

    let unsub: null | (() => void) = null;

    onDestroy(() => {
        try { unsub?.(); } catch {}
        unsub = null;
        connected = false;
    });

</script>

<Card>
    <svelte:fragment slot="header">
        <div class="flex justify-between items-center w-full">
            <span class="font-approachmono text-xl">{name}</span>
            <LiveIndicator connected={connected} />
        </div>

        {#if error}
            <div class="mt-2 text-xs text-dag-danger font-approachmono bg-red-50/10 px-2 py-1 rounded">
                {error}
            </div>
        {/if}
    </svelte:fragment>

    <svelte:fragment slot="children">
            <div class="gauge">
            
                <div class="label-min">{minN}</div>
                <div class="label-max">{maxN}</div>
            
                <svg viewBox="-100 -90 200 140">
                    <!-- Background -->
                    <path
                        d={ARC_PATH_D}
                        stroke="var(--edge)"
                        stroke-width="14"
                        stroke-linecap="round"
                        fill="none"
                        opacity="0.3"
                    />
                
                    <!-- Animated arc -->
                    <path
                        d={ARC_PATH_D}
                        stroke={derivedArcColor}
                        stroke-width="14"
                        stroke-linecap="round"
                        fill="none"
                        stroke-dasharray={derivedDash}
                        class="arc-fill"
                    />
                </svg>
            
                <!-- Needle -->
                <svg
                    class="needle-svg"
                    viewBox="0 0 200 200"
                    style:transform={`rotate(${derivedAngle}deg)`}>
                        
                    <!-- tapered needle -->
                    <polygon
                        points="96,100 104,100 102,10 98,10"
                        fill="var(--accent)"
                    />
                        
                    <!-- pivot -->
                    <circle
                        cx="100" cy="100"
                        r="12"
                        fill="black"
                    />
                </svg>
            
            </div>
        
            <div class="text-center mt-4">
                <div class="text-3xl font-approachmono font-bold">
                    {value.toFixed(2)}{unit ? ` ${unit}` : ""}
                </div>
                {#if label}
                    <div class="text-sm text-text-muted font-approachmono">{label}</div>
                {/if}
            </div>
    </svelte:fragment>
</Card>

<style>
    .font-approachmono {
        font-family: "Approach Mono", ui-monospace, monospace;
    }

    .gauge {
        position: relative;
        display: flex;
        justify-content: center;
        align-items: flex-end;
        width: 100%;
        transform: translateY(70px);
    }

    svg {
        position: relative;
        z-index: 30;
        overflow: visible;
        pointer-events: none;
        margin-top: 20px;
    }

    .label-min,
    .label-max {
        position: absolute;
        bottom: 20px;
        font-size: 1rem;
        font-weight: 400;
        font-family: "Approach Mono", monospace;
        color: var(--text-muted);
    }
    .label-min { left: 5%; transform: translateY(-20px); }
    .label-max { right: 5%; transform: translateY(-20px); }

    .needle-svg {
        position: absolute;
        width: 200px;
        height: 200px;
        transform-origin: 100px 100px;
        border-radius: 2px;
        transition: transform 0.25s cubic-bezier(0.3, 1.4, 0.4, 1.0);
    }

    .arc-fill {
        transition:
            stroke-dasharray 0.35s cubic-bezier(0.3, 1.4, 0.4, 1.0),
            stroke 0.25s ease-out;
    }
</style>
