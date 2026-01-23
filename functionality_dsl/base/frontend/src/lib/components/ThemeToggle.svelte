<script lang="ts">
    import { onMount } from "svelte";
    import { Sun, Moon } from "lucide-svelte";

    let theme = $state<"light" | "dark">("light");

    function toggleTheme() {
        theme = theme === "dark" ? "light" : "dark";
        applyTheme(theme);
        localStorage.setItem("fdsl-theme", theme);
    }

    function applyTheme(t: "light" | "dark") {
        if (t === "light") {
            document.documentElement.setAttribute("data-theme", "light");
        } else {
            document.documentElement.removeAttribute("data-theme");
        }
    }

    onMount(() => {
        // Check localStorage first, otherwise default to light
        const stored = localStorage.getItem("fdsl-theme") as "light" | "dark" | null;
        if (stored) {
            theme = stored;
        }
        // Default is already light, no need for system preference check
        applyTheme(theme);
    });
</script>

<button
    onclick={toggleTheme}
    class="theme-toggle"
    title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
    aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
>
    {#if theme === "dark"}
        <Sun size={18} />
    {:else}
        <Moon size={18} />
    {/if}
</button>

<style>
    .theme-toggle {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        padding: 0;
        border: 2px solid var(--edge-soft);
        border-radius: 10px;
        background: var(--card);
        color: var(--text-muted);
        cursor: pointer;
        transition: all 0.15s linear;
    }

    .theme-toggle:hover {
        border: 3px solid var(--edge-light);
        color: var(--text);
    }

    .theme-toggle:focus-visible {
        outline: 2px solid var(--accent);
        outline-offset: 2px;
    }
</style>
